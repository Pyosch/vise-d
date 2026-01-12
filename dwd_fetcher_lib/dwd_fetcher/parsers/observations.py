"""
Observation data parser for DWD ZIP/CSV files.
"""

import io
import zipfile
import pandas as pd
import re
from typing import Optional, Tuple, Dict
from datetime import datetime
from pathlib import Path

from ..config import DWDConfig
from ..downloader import Downloader


class ObservationParser:
    """Parses DWD observation data from ZIP archives."""
    
    def __init__(self, downloader: Optional[Downloader] = None):
        """
        Initialize observation parser.
        
        Args:
            downloader: Downloader instance
        """
        self.downloader = downloader or Downloader()
    
    def fetch_observations(self, station_id: str, parameter: str,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          resolution: str = "hourly",
                          prefer_recent: bool = True,
                          force_refresh: bool = False) -> Tuple[pd.DataFrame, Dict]:
        """
        Fetch observation data for a station and parameter.
        
        Args:
            station_id: Station ID
            parameter: Parameter name ('solar', 'wind', 'temperature', 'pressure')
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            resolution: Time resolution ('hourly', 'daily', '10_minutes')
            prefer_recent: Prefer recent file over historical when overlap exists
            force_refresh: Force re-download
            
        Returns:
            Tuple of (DataFrame with data, metadata dict with boundary info)
        """
        base_url = DWDConfig.get_obs_url(parameter, resolution)
        param_code = DWDConfig.get_param_code(parameter, resolution)
        
        metadata = {
            'station_id': station_id,
            'parameter': parameter,
            'sources': [],
            'boundary_date': None
        }
        
        dfs = []
        
        # Strategy: Always try recent data first, then check if we need historical data
        # This avoids guessing and handles the actual data coverage
        
        # Step 1: Try to fetch recent data
        recent_df = None
        try:
            recent_df = self._fetch_recent_data(
                base_url, station_id, param_code, parameter, resolution, force_refresh
            )
            if recent_df is not None and not recent_df.empty:
                dfs.append(recent_df)
                metadata['sources'].append('recent')
                metadata['recent_start'] = recent_df.index.min()
                metadata['recent_end'] = recent_df.index.max()
            else:
                if 'warnings' not in metadata:
                    metadata['warnings'] = []
                metadata['warnings'].append(f"Station {station_id}: Recent data file not found or empty")
        except Exception as e:
            if 'warnings' not in metadata:
                metadata['warnings'] = []
            metadata['warnings'].append(f"Station {station_id}: Could not fetch recent data - {e}")
            print(f"Warning: Could not fetch recent data: {e}")
        
        # Step 2: Determine if we need historical data
        need_historical = False
        if start_date is not None and recent_df is not None and not recent_df.empty:
            # Check if requested start_date is before recent data coverage
            if start_date < recent_df.index.min():
                need_historical = True
        elif start_date is not None and (recent_df is None or recent_df.empty):
            # No recent data available, try historical
            need_historical = True
        elif start_date is None and end_date is None:
            # Fetch all data - include historical if it exists
            need_historical = True
        
        # Step 3: Fetch historical data if needed
        if need_historical:
            try:
                historical_df = self._fetch_historical_data(
                    base_url, station_id, param_code, parameter, resolution, force_refresh
                )
                if historical_df is not None and not historical_df.empty:
                    dfs.append(historical_df)
                    metadata['sources'].append('historical')
                    metadata['historical_start'] = historical_df.index.min()
                    metadata['historical_end'] = historical_df.index.max()
                else:
                    if 'warnings' not in metadata:
                        metadata['warnings'] = []
                    metadata['warnings'].append(f"Station {station_id}: Historical data file not found or empty")
            except Exception as e:
                if 'warnings' not in metadata:
                    metadata['warnings'] = []
                metadata['warnings'].append(f"Station {station_id}: Could not fetch historical data - {e}")
                print(f"Warning: Could not fetch historical data: {e}")
        
        # Merge dataframes
        if not dfs:
            return pd.DataFrame(), metadata
        
        if len(dfs) == 1:
            combined = dfs[0]
        else:
            # Merge and handle overlap
            combined = pd.concat(dfs)
            combined = combined[~combined.index.duplicated(keep='first' if prefer_recent else 'last')]
            combined = combined.sort_index()
            
            # Document boundary
            if 'recent_start' in metadata and 'historical_end' in metadata:
                metadata['boundary_date'] = metadata['recent_start']
        
        # Track available date range before filtering
        if not combined.empty:
            metadata['available_start'] = combined.index.min()
            metadata['available_end'] = combined.index.max()
        
        # Filter by date range if specified
        data_before_filter = len(combined)
        if start_date is not None:
            combined = combined[combined.index >= start_date]
        if end_date is not None:
            combined = combined[combined.index <= end_date]
        
        # Warn if filtering removed all data
        if data_before_filter > 0 and combined.empty:
            if 'warnings' not in metadata:
                metadata['warnings'] = []
            date_range_str = f"{metadata.get('available_start')} to {metadata.get('available_end')}"
            requested_range_str = f"{start_date or 'earliest'} to {end_date or 'latest'}"
            metadata['warnings'].append(
                f"Station {station_id}: Data available ({date_range_str}) is outside requested range ({requested_range_str})"
            )
        
        return combined, metadata
    
    def _fetch_recent_data(self, base_url: str, station_id: str,
                          param_code: str, parameter: str, resolution: str,
                          force_refresh: bool = False) -> Optional[pd.DataFrame]:
        """Fetch recent observation data."""
        # Build URL for recent data
        # Special handling for 10-minute data (different naming conventions)
        if resolution == "10_minutes":
            if param_code == "ST":
                # Solar 10-minute data uses "10minutenwerte_SOLAR" format
                filename = f"10minutenwerte_SOLAR_{station_id:0>5}_akt.zip"
            elif param_code == "FF":
                # Wind 10-minute data uses "10minutenwerte_wind" format
                filename = f"10minutenwerte_wind_{station_id:0>5}_akt.zip"
            else:
                # Other 10-minute parameters use standard format
                filename = f"10minutenwerte_{param_code}_{station_id:0>5}_akt.zip"
        else:
            # Standard naming for hourly and daily data
            if resolution == "hourly":
                time_str = "stundenwerte"
            elif resolution == "daily":
                time_str = "tageswerte"
            else:
                time_str = "stundenwerte"
            
            filename = f"{time_str}_{param_code}_{station_id:0>5}_akt.zip"
        
        url = f"{base_url}/recent/{filename}"
        
        try:
            zip_content = self.downloader.download(url, binary=True, force_refresh=force_refresh)
            return self._parse_zip_data(zip_content, param_code, parameter)
        except Exception as e:
            print(f"Could not fetch recent data from {url}: {e}")
            return None
    
    def _fetch_historical_data(self, base_url: str, station_id: str,
                              param_code: str, parameter: str, resolution: str,
                              force_refresh: bool = False) -> Optional[pd.DataFrame]:
        """Fetch historical observation data."""
        # List directory to find historical file
        try:
            files = self.downloader.list_directory(f"{base_url}/historical/")
        except Exception as e:
            print(f"Could not list historical directory: {e}")
            return None
        
        # Find matching file
        # Special handling for 10-minute data (different naming conventions)
        if resolution == "10_minutes":
            if param_code == "ST":
                # Solar 10-minute data uses "10minutenwerte_SOLAR" format
                pattern = f"10minutenwerte_SOLAR_{station_id:0>5}_.*_hist\\.zip"
            elif param_code == "FF":
                # Wind 10-minute data uses "10minutenwerte_wind" format
                pattern = f"10minutenwerte_wind_{station_id:0>5}_.*_hist\\.zip"
            else:
                # Other 10-minute parameters use standard format
                pattern = f"10minutenwerte_{param_code}_{station_id:0>5}_.*_hist\\.zip"
        else:
            # Standard naming for hourly and daily data
            if resolution == "hourly":
                time_str = "stundenwerte"
            elif resolution == "daily":
                time_str = "tageswerte"
            else:
                time_str = "stundenwerte"
            
            pattern = f"{time_str}_{param_code}_{station_id:0>5}_.*_hist\\.zip"
        
        matching_files = [f for f in files if re.match(pattern, f)]
        
        if not matching_files:
            return None
        
        # Use the first matching file (should only be one)
        filename = matching_files[0]
        url = f"{base_url}/historical/{filename}"
        
        try:
            zip_content = self.downloader.download(url, binary=True, force_refresh=force_refresh)
            return self._parse_zip_data(zip_content, param_code, parameter)
        except Exception as e:
            print(f"Could not fetch historical data from {url}: {e}")
            return None
    
    def _parse_zip_data(self, zip_content: bytes, param_code: str, parameter: str) -> pd.DataFrame:
        """
        Parse ZIP archive containing observation data.
        
        Args:
            zip_content: ZIP file content as bytes
            param_code: Parameter code
            parameter: Parameter name ('solar', 'wind', 'temperature', 'pressure')
            
        Returns:
            DataFrame with parsed data
        """
        with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
            # Find data file (usually named produkt_*)
            data_files = [f for f in zf.namelist() if f.startswith('produkt_')]
            
            if not data_files:
                raise ValueError("No data file found in ZIP archive")
            
            # Read first data file
            with zf.open(data_files[0]) as f:
                # DWD files use semicolon delimiter and may have -999 for missing values
                df = pd.read_csv(
                    f,
                    sep=';',
                    encoding='latin-1',
                    na_values=['-999', -999, '-999.0'],
                    skipinitialspace=True
                )
        
        # Parse timestamp column
        # Column name is typically 'MESS_DATUM' (measurement date)
        if 'MESS_DATUM' in df.columns:
            # Try different timestamp formats (10-minute data has YYYYMMDDHHMM, hourly has YYYYMMDDHH)
            # First try with minutes
            df['datetime'] = pd.to_datetime(df['MESS_DATUM'], format='%Y%m%d%H%M', errors='coerce')
            # If all NaT, try without minutes
            if df['datetime'].isna().all():
                df['datetime'] = pd.to_datetime(df['MESS_DATUM'], format='%Y%m%d%H', errors='coerce')
            df.set_index('datetime', inplace=True)
            df.drop('MESS_DATUM', axis=1, inplace=True, errors='ignore')
        elif 'MESS_DATUM_BEGINN' in df.columns:
            # Try different timestamp formats
            df['datetime'] = pd.to_datetime(df['MESS_DATUM_BEGINN'], format='%Y%m%d%H%M', errors='coerce')
            if df['datetime'].isna().all():
                df['datetime'] = pd.to_datetime(df['MESS_DATUM_BEGINN'], format='%Y%m%d%H', errors='coerce')
            df.set_index('datetime', inplace=True)
            df.drop('MESS_DATUM_BEGINN', axis=1, inplace=True, errors='ignore')
        
        # Drop metadata columns that shouldn't be part of the data
        meta_cols = ['STATIONS_ID', 'eor', 'MESS_DATUM_ENDE']
        df.drop(meta_cols, axis=1, inplace=True, errors='ignore')
        
        # Rename quality flag columns to be parameter-specific (e.g., QN -> QN_temperature)
        # This prevents column overlap when joining multiple parameters while preserving quality info
        qn_cols = [col for col in df.columns if col.startswith('QN')]
        if qn_cols:
            rename_dict = {col: f"{col}_{parameter}" for col in qn_cols}
            df.rename(columns=rename_dict, inplace=True)
        
        # Convert numeric columns to proper types
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Clean column names (strip whitespace)
        df.columns = df.columns.str.strip()
        
        return df
