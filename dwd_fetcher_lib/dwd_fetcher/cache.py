"""
Cache management for DWD data fetcher.
Handles file caching with expiration, manual refresh, and cache invalidation.
"""

import os
import json
import time
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
import hashlib


class CacheManager:
    """Manages local file cache with expiration and manual refresh capabilities."""
    
    def __init__(self, cache_dir: str = ".dwd_cache", 
                 default_expiry_hours: float = 24):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory for cache storage
            default_expiry_hours: Default cache expiration time in hours
        """
        self.cache_dir = Path(cache_dir)
        self.default_expiry_hours = default_expiry_hours
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        
        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or initialize metadata
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load cache metadata from disk."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def _save_metadata(self):
        """Save cache metadata to disk."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save cache metadata: {e}")
    
    def _get_cache_key(self, url: str, params: Optional[Dict] = None) -> str:
        """
        Generate cache key from URL and parameters.
        
        Args:
            url: URL being cached
            params: Optional parameters
            
        Returns:
            Cache key (hash)
        """
        key_string = url
        if params:
            key_string += json.dumps(params, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str, extension: str = "") -> Path:
        """Get filesystem path for cached item."""
        filename = f"{cache_key}{extension}"
        return self.cache_dir / filename
    
    def is_valid(self, cache_key: str, expiry_hours: Optional[float] = None) -> bool:
        """
        Check if cached item is still valid.
        
        Args:
            cache_key: Cache key to check
            expiry_hours: Custom expiry time (uses default if None)
            
        Returns:
            True if cache is valid and not expired
        """
        if cache_key not in self.metadata:
            return False
        
        metadata = self.metadata[cache_key]
        cached_time = metadata.get('timestamp', 0)
        
        # Check if file exists
        cache_path = self._get_cache_path(cache_key, metadata.get('extension', ''))
        if not cache_path.exists():
            return False
        
        # Check expiration
        if expiry_hours is None:
            expiry_hours = self.default_expiry_hours
        
        # Never expire if expiry_hours is 0 or negative
        if expiry_hours <= 0:
            return True
        
        age_hours = (time.time() - cached_time) / 3600
        return age_hours < expiry_hours
    
    def get(self, url: str, params: Optional[Dict] = None,
            expiry_hours: Optional[float] = None,
            binary: bool = False) -> Optional[Any]:
        """
        Get item from cache if valid.
        
        Args:
            url: URL of cached item
            params: Optional parameters
            expiry_hours: Custom expiry time
            binary: Whether to return binary data
            
        Returns:
            Cached content or None if not found/expired
        """
        cache_key = self._get_cache_key(url, params)
        
        if not self.is_valid(cache_key, expiry_hours):
            return None
        
        metadata = self.metadata[cache_key]
        cache_path = self._get_cache_path(cache_key, metadata.get('extension', ''))
        
        try:
            mode = 'rb' if binary else 'r'
            encoding = None if binary else 'utf-8'
            with open(cache_path, mode, encoding=encoding) as f:
                return f.read()
        except IOError as e:
            print(f"Warning: Could not read cache file: {e}")
            return None
    
    def set(self, url: str, content: Any, params: Optional[Dict] = None,
            extension: str = "", binary: bool = False):
        """
        Store item in cache.
        
        Args:
            url: URL being cached
            content: Content to cache
            params: Optional parameters
            extension: File extension (e.g., '.zip', '.xml')
            binary: Whether content is binary
        """
        cache_key = self._get_cache_key(url, params)
        cache_path = self._get_cache_path(cache_key, extension)
        
        try:
            mode = 'wb' if binary else 'w'
            encoding = None if binary else 'utf-8'
            with open(cache_path, mode, encoding=encoding) as f:
                f.write(content)
            
            # Update metadata
            self.metadata[cache_key] = {
                'url': url,
                'params': params,
                'timestamp': time.time(),
                'extension': extension,
                'size': len(content) if isinstance(content, (str, bytes)) else 0
            }
            self._save_metadata()
            
        except IOError as e:
            print(f"Warning: Could not write to cache: {e}")
    
    def invalidate(self, url: str, params: Optional[Dict] = None):
        """
        Invalidate (remove) cached item.
        
        Args:
            url: URL to invalidate
            params: Optional parameters
        """
        cache_key = self._get_cache_key(url, params)
        
        if cache_key in self.metadata:
            metadata = self.metadata[cache_key]
            cache_path = self._get_cache_path(cache_key, metadata.get('extension', ''))
            
            # Remove file
            if cache_path.exists():
                try:
                    cache_path.unlink()
                except OSError as e:
                    print(f"Warning: Could not delete cache file: {e}")
            
            # Remove metadata
            del self.metadata[cache_key]
            self._save_metadata()
    
    def clear_all(self, confirm: bool = False):
        """
        Clear entire cache.
        
        Args:
            confirm: Must be True to actually clear cache (safety)
        """
        if not confirm:
            raise ValueError("Must set confirm=True to clear entire cache")
        
        try:
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.metadata = {}
            self._save_metadata()
        except OSError as e:
            print(f"Warning: Could not clear cache: {e}")
    
    def clear_expired(self, expiry_hours: Optional[float] = None):
        """
        Remove expired cache entries.
        
        Args:
            expiry_hours: Expiry threshold (uses default if None)
        """
        if expiry_hours is None:
            expiry_hours = self.default_expiry_hours
        
        expired_keys = []
        for cache_key in list(self.metadata.keys()):
            if not self.is_valid(cache_key, expiry_hours):
                expired_keys.append(cache_key)
        
        for cache_key in expired_keys:
            metadata = self.metadata[cache_key]
            self.invalidate(metadata['url'], metadata.get('params'))
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get information about cache status.
        
        Returns:
            Dictionary with cache statistics
        """
        total_size = 0
        valid_count = 0
        expired_count = 0
        
        for cache_key, metadata in self.metadata.items():
            total_size += metadata.get('size', 0)
            if self.is_valid(cache_key):
                valid_count += 1
            else:
                expired_count += 1
        
        return {
            'cache_dir': str(self.cache_dir),
            'total_items': len(self.metadata),
            'valid_items': valid_count,
            'expired_items': expired_count,
            'total_size_bytes': total_size,
            'default_expiry_hours': self.default_expiry_hours
        }
    
    def get_or_fetch(self, url: str, fetch_func: Callable,
                     params: Optional[Dict] = None,
                     expiry_hours: Optional[float] = None,
                     extension: str = "",
                     binary: bool = False,
                     force_refresh: bool = False) -> Any:
        """
        Get from cache or fetch if not available/expired.
        
        Args:
            url: URL to fetch
            fetch_func: Function to call if cache miss (should return content)
            params: Optional parameters
            expiry_hours: Custom expiry time
            extension: File extension for caching
            binary: Whether content is binary
            force_refresh: Force refresh even if cache is valid
            
        Returns:
            Content from cache or fetched
        """
        # Check cache first (unless force refresh)
        if not force_refresh:
            cached = self.get(url, params, expiry_hours, binary)
            if cached is not None:
                return cached
        
        # Fetch new content
        content = fetch_func()
        
        # Cache it
        self.set(url, content, params, extension, binary)
        
        return content
