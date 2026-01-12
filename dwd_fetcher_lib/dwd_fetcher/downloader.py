"""
Downloader module for fetching files from DWD Open Data portal.
"""

import requests
import time
from typing import Optional, Callable
from pathlib import Path

from .cache import CacheManager


class Downloader:
    """Handles HTTP downloads with retry logic and caching."""
    
    def __init__(self, cache_manager: Optional[CacheManager] = None,
                 timeout: int = 30,
                 max_retries: int = 3,
                 retry_delay: float = 1.0):
        """
        Initialize downloader.
        
        Args:
            cache_manager: Cache manager instance
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.cache_manager = cache_manager or CacheManager()
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def download(self, url: str, 
                binary: bool = True,
                force_refresh: bool = False,
                expiry_hours: Optional[float] = None,
                progress_callback: Optional[Callable[[int, int], None]] = None) -> bytes:
        """
        Download file from URL with caching.
        
        Args:
            url: URL to download
            binary: Whether to return binary data
            force_refresh: Force download even if cached
            expiry_hours: Cache expiry time
            progress_callback: Optional callback(bytes_downloaded, total_bytes)
            
        Returns:
            Downloaded content as bytes or string
        """
        # Determine file extension from URL
        extension = Path(url).suffix
        
        # Try cache first
        if not force_refresh:
            cached = self.cache_manager.get(url, expiry_hours=expiry_hours, binary=binary)
            if cached is not None:
                return cached
        
        # Download with retries
        content = self._download_with_retry(url, binary, progress_callback)
        
        # Cache the result
        self.cache_manager.set(url, content, extension=extension, binary=binary)
        
        return content
    
    def _download_with_retry(self, url: str, binary: bool = True,
                            progress_callback: Optional[Callable[[int, int], None]] = None) -> bytes:
        """
        Download with automatic retry on failure.
        
        Args:
            url: URL to download
            binary: Whether to return binary data
            progress_callback: Optional progress callback
            
        Returns:
            Downloaded content
            
        Raises:
            RuntimeError: If download fails after all retries
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, timeout=self.timeout, stream=True)
                response.raise_for_status()
                
                # Get total size if available
                total_size = int(response.headers.get('content-length', 0))
                
                # Download in chunks
                chunks = []
                downloaded = 0
                
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        chunks.append(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)
                
                content = b''.join(chunks)
                
                if not binary:
                    # Try to decode as UTF-8, fall back to Latin-1
                    try:
                        return content.decode('utf-8')
                    except UnicodeDecodeError:
                        return content.decode('latin-1')
                
                return content
                
            except requests.RequestException as e:
                last_error = e
                
                if attempt < self.max_retries - 1:
                    # Wait before retry
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
        
        raise RuntimeError(f"Failed to download {url} after {self.max_retries} attempts: {last_error}")
    
    def download_to_file(self, url: str, filepath: str,
                        force_refresh: bool = False,
                        progress_callback: Optional[Callable[[int, int], None]] = None):
        """
        Download URL directly to file.
        
        Args:
            url: URL to download
            filepath: Destination file path
            force_refresh: Force download even if file exists
            progress_callback: Optional progress callback
        """
        file_path = Path(filepath)
        
        if file_path.exists() and not force_refresh:
            return
        
        content = self.download(url, binary=True, force_refresh=force_refresh,
                              progress_callback=progress_callback)
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'wb') as f:
            f.write(content)
    
    def list_directory(self, url: str) -> list:
        """
        List files in a directory on DWD server.
        
        Args:
            url: URL of directory
            
        Returns:
            List of filenames in directory
        """
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse HTML directory listing
            # DWD uses Apache-style directory listings
            content = response.text
            files = []
            
            import re
            # Look for href links
            pattern = r'<a href="([^"]+)"'
            matches = re.findall(pattern, content)
            
            for match in matches:
                # Skip parent directory and absolute URLs
                if match.startswith('..') or match.startswith('/') or '://' in match:
                    continue
                files.append(match)
            
            return files
            
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to list directory {url}: {e}")
    
    def get_file_info(self, url: str) -> dict:
        """
        Get file information without downloading.
        
        Args:
            url: URL to check
            
        Returns:
            Dictionary with file metadata
        """
        try:
            response = requests.head(url, timeout=self.timeout)
            response.raise_for_status()
            
            return {
                'url': url,
                'size': int(response.headers.get('content-length', 0)),
                'last_modified': response.headers.get('last-modified'),
                'content_type': response.headers.get('content-type')
            }
            
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to get file info for {url}: {e}")
    
    def check_file_exists(self, url: str) -> bool:
        """
        Check if a file exists on DWD server without downloading.
        
        Uses HEAD request to verify file availability. Handles 404 and
        other errors gracefully.
        
        Args:
            url: URL to check
            
        Returns:
            True if file exists and is accessible, False otherwise
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.head(url, timeout=self.timeout, allow_redirects=True)
                # File exists if we get 200 OK
                return response.status_code == 200
                
            except requests.RequestException:
                # On connection errors, retry
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                # Final attempt failed
                return False
        
        return False
