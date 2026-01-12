"""
Main API interface for DWD Data Fetcher.
"""

import warnings
from typing import List, Optional, Dict, Tuple
from datetime import datetime
import pandas as pd

from .config import DWDConfig, WeightingStrategy
from .cache import CacheManager
from .downloader import Downloader
from .stations import StationManager, Station
from .parsers import MOSMIXParameterManager, ObservationParser, ForecastParser
from .transformers import DataTransformer


class DWDFetcher:
    """
    Main interface for fetching DWD meteorological data.
    
    This class provides high-level methods for fetching both observation and
    forecast data from DWD's Open Data portal, with support for multiple stations,
    automatic data merging, and output formatting for pvlib/windpowerlib.
    """
    
    def __init__(self, cache_dir: str = ".dwd_cache",
                 cache_expiry_hours: float = 24,
                 timezone: str = "Europe/Berlin",
                 weighting_strategy: WeightingStrategy = WeightingStrategy.INVERSE_DISTANCE,
                 ranking_strategy: str = "distance_only",
                 quality_check_limit: int = 5):
        """
        Initialize DWD data fetcher.
        
        Args:
            cache_dir: Directory for cache storage
            cache_expiry_hours: Default cache expiration time
            timezone: Timezone for datetime conversion
            weighting_strategy: Default strategy for multi-station merging
            ranking_strategy: Strategy for ranking stations:
                - "distance_only": Sort by distance only (default, fastest)
                - "quality_weighted": Score by quality/distance² (best balance)
                - "quality_first": Sort by quality, then distance (prioritize data availability)
            quality_check_limit: Number of closest stations to check for quality (default: 5)
        """
        self.cache_manager = CacheManager(cache_dir, cache_expiry_hours)
        self.downloader = Downloader(self.cache_manager)
        self.station_manager = StationManager(self.cache_manager, self.downloader)
        self.param_manager = MOSMIXParameterManager(self.cache_manager)
        self.obs_parser = ObservationParser(self.downloader)
        self.forecast_parser = ForecastParser(self.downloader, self.param_manager)
        self.transformer = DataTransformer(timezone)
        self.weighting_strategy = weighting_strategy
        self.ranking_strategy = ranking_strategy
        self.quality_check_limit = quality_check_limit
    
    def get_observations(self, latitude: float, longitude: float,
                        parameters: List[str],
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None,
                        resolution: str = "hourly",
                        max_distance_km: float = 50,
                        n_stations: int = 3,
                        force_refresh: bool = False,
                        for_pvlib: bool = False,
                        for_windpowerlib: bool = False,
                        allow_multi_station: bool = True,
                        active_only: bool = False) -> Tuple[pd.DataFrame, Dict]:
        """
        Get observation data for a location.
        
        Args:
            latitude: Latitude in degrees
            longitude: Longitude in degrees
            parameters: List of parameters ('solar', 'wind', 'temperature', 'pressure')
            start_date: Start date (None = earliest available)
            end_date: End date (None = latest available)
            resolution: Time resolution ('hourly', 'daily', '10_minutes')
            max_distance_km: Maximum station distance
            n_stations: Number of stations to use per parameter
            force_refresh: Force re-download
            for_pvlib: Format output for pvlib
            for_windpowerlib: Format output for windpowerlib
            allow_multi_station: Allow combining data from multiple stations
            active_only: Only use stations active at current date (False = use all stations)
            
        Returns:
            Tuple of (DataFrame with data, metadata dict)
        """
        metadata = {
            'location': {'latitude': latitude, 'longitude': longitude},
            'parameters': parameters,
            'stations_used': {},
            'data_sources': {},
            'warnings': []
        }
        
        # Find stations for each parameter
        stations_by_param = {}
        for param in parameters:
            # Use the resolution specified by user
            stations = self.station_manager.find_nearest_stations(
                latitude, longitude, param,
                n=n_stations if allow_multi_station else 1,
                max_distance_km=max_distance_km,
                resolution=resolution,
                active_only=active_only,
                ranking_strategy=self.ranking_strategy,
                quality_check_limit=self.quality_check_limit,
                start_date=start_date,
                end_date=end_date
            )
            
            if not stations:
                metadata['warnings'].append(
                    f"No stations found for parameter '{param}' within {max_distance_km}km"
                )
                continue
            
            stations_by_param[param] = stations
            
            # Record station info including quality scores
            metadata['stations_used'][param] = [
                {
                    'station_id': s.station_id,
                    'name': s.name,
                    'distance_km': s.distance_km,
                    'latitude': s.latitude,
                    'longitude': s.longitude,
                    'quality_score': getattr(s, 'quality_score', None),
                    'combined_score': getattr(s, 'combined_score', None)
                }
                for s in stations
            ]
        
        # Check parameter completeness
        availability_report = self._check_parameter_completeness(
            stations_by_param, parameters
        )
        metadata['parameter_availability'] = availability_report
        
        # Fetch data for each parameter
        param_data = {}
        
        for param, stations in stations_by_param.items():
            # Use the resolution specified by user (no automatic override)
            station_dataframes = {}
            
            for station in stations:
                try:
                    df, obs_meta = self.obs_parser.fetch_observations(
                        station.station_id, param,
                        start_date, end_date,
                        resolution, force_refresh=force_refresh
                    )
                    
                    # Propagate warnings from observation parser
                    if 'warnings' in obs_meta and obs_meta['warnings']:
                        metadata['warnings'].extend(obs_meta['warnings'])
                    
                    if not df.empty:
                        station_dataframes[station] = df
                        
                        # Record data source info
                        if param not in metadata['data_sources']:
                            metadata['data_sources'][param] = []
                        
                        metadata['data_sources'][param].append({
                            'station_id': station.station_id,
                            'sources': obs_meta.get('sources', []),
                            'boundary_date': obs_meta.get('boundary_date'),
                            'available_start': obs_meta.get('available_start'),
                            'available_end': obs_meta.get('available_end')
                        })
                    else:
                        # Data was fetched but is empty (e.g., outside date range)
                        if obs_meta.get('sources'):
                            metadata['warnings'].append(
                                f"Station {station.station_id} ({param}): Data exists but no records in requested date range. "
                                f"Available: {obs_meta.get('available_start')} to {obs_meta.get('available_end')}"
                            )
                
                except Exception as e:
                    metadata['warnings'].append(
                        f"Failed to fetch {param} data from station {station.station_id}: {e}"
                    )
            
            # Merge data from multiple stations if needed
            if station_dataframes:
                if len(station_dataframes) > 1 and allow_multi_station:
                    metadata['warnings'].append(
                        f"Parameter '{param}': Combining data from {len(station_dataframes)} stations "
                        f"using {self.weighting_strategy.value} strategy"
                    )
                    
                    merged_df = self.transformer.merge_multi_station_data(
                        station_dataframes, self.weighting_strategy
                    )
                    param_data[param] = merged_df
                else:
                    # Use only first station
                    param_data[param] = list(station_dataframes.values())[0]
        
        # Combine all parameters into single DataFrame
        if not param_data:
            return pd.DataFrame(), metadata
        
        # All parameters now use the same user-specified resolution
        # (No more automatic per-parameter resolution override)
        
        # Merge all parameter dataframes
        combined_df = pd.DataFrame()
        for param, df in param_data.items():
            if combined_df.empty:
                combined_df = df
            else:
                # Handle overlapping columns intelligently:
                # Keep existing columns with valid data, only add new columns
                overlapping_cols = combined_df.columns.intersection(df.columns)
                
                if len(overlapping_cols) > 0:
                    # For overlapping columns, keep existing valid data, only fill missing/zero values
                    for col in overlapping_cols:
                        # Create mask: True where we want to update (NaN or zero in existing data)
                        mask = combined_df[col].isna() | (combined_df[col] == 0)
                        # Update only those positions with new data
                        combined_df.loc[mask, col] = df.loc[mask, col]
                    
                    # Add only non-overlapping columns from new dataframe
                    new_cols = df.columns.difference(combined_df.columns)
                    if len(new_cols) > 0:
                        combined_df = combined_df.join(df[new_cols], how='outer')
                else:
                    # No overlap, simple join
                    combined_df = combined_df.join(df, how='outer')
        
        # Apply transformations
        if for_pvlib:
            combined_df = self.transformer.transform_for_pvlib(combined_df)
        elif for_windpowerlib:
            combined_df = self.transformer.transform_for_windpowerlib(combined_df)
        
        return combined_df, metadata
    
    def get_forecast(self, latitude: float, longitude: float,
                    parameters: Optional[List[str]] = None,
                    force_refresh: bool = False,
                    for_pvlib: bool = False,
                    for_windpowerlib: bool = False) -> Tuple[pd.DataFrame, Dict]:
        """
        Get MOSMIX forecast data for a location.
        
        Args:
            latitude: Latitude in degrees
            longitude: Longitude in degrees
            parameters: Parameter codes (None = relevant parameters)
            force_refresh: Force re-download
            for_pvlib: Format output for pvlib
            for_windpowerlib: Format output for windpowerlib
            
        Returns:
            Tuple of (DataFrame with forecast, metadata dict)
        """
        metadata = {
            'location': {'latitude': latitude, 'longitude': longitude},
            'data_type': 'MOSMIX forecast',
            'warnings': []
        }
        
        # Get forecast data
        df = self.forecast_parser.get_forecast_for_location(
            latitude, longitude,
            parameters=parameters,
            force_refresh=force_refresh
        )
        
        if df.empty:
            metadata['warnings'].append("No forecast data available for location")
            return df, metadata
        
        # Record station info
        if 'station_id' in df.columns:
            metadata['station_id'] = df['station_id'].iloc[0] if not df.empty else None
        
        # Apply transformations
        if for_pvlib:
            df = self.transformer.transform_for_pvlib(df)
        elif for_windpowerlib:
            df = self.transformer.transform_for_windpowerlib(df)
        
        return df, metadata
    
    def get_combined_data(self, latitude: float, longitude: float,
                         parameters: List[str],
                         historical_start: Optional[datetime] = None,
                         historical_end: Optional[datetime] = None,
                         include_forecast: bool = True,
                         **kwargs) -> Tuple[pd.DataFrame, Dict]:
        """
        Get combined historical observations and forecast data.
        
        Args:
            latitude: Latitude in degrees
            longitude: Longitude in degrees
            parameters: List of parameters
            historical_start: Start date for historical data
            historical_end: End date for historical data (None = latest)
            include_forecast: Include forecast data
            **kwargs: Additional arguments passed to get_observations
            
        Returns:
            Tuple of (Combined DataFrame, metadata dict)
        """
        metadata = {'components': {}}
        
        # Get historical data
        obs_df, obs_meta = self.get_observations(
            latitude, longitude, parameters,
            start_date=historical_start,
            end_date=historical_end,
            **kwargs
        )
        
        metadata['components']['observations'] = obs_meta
        
        if not include_forecast:
            return obs_df, metadata
        
        # Get forecast data
        forecast_df, forecast_meta = self.get_forecast(
            latitude, longitude,
            for_pvlib=kwargs.get('for_pvlib', False),
            for_windpowerlib=kwargs.get('for_windpowerlib', False),
            force_refresh=kwargs.get('force_refresh', False)
        )
        
        metadata['components']['forecast'] = forecast_meta
        
        # Combine observations and forecast
        if not obs_df.empty and not forecast_df.empty:
            # Remove any overlap (forecast takes precedence)
            if obs_df.index.max() >= forecast_df.index.min():
                obs_df = obs_df[obs_df.index < forecast_df.index.min()]
            
            combined = pd.concat([obs_df, forecast_df])
            combined = combined.sort_index()
            
            metadata['transition_point'] = forecast_df.index.min()
        elif not obs_df.empty:
            combined = obs_df
        elif not forecast_df.empty:
            combined = forecast_df
        else:
            combined = pd.DataFrame()
        
        return combined, metadata
    
    def find_stations(self, latitude: float, longitude: float,
                     parameters: Optional[List[str]] = None,
                     n: int = 5,
                     max_distance_km: Optional[float] = None,
                     resolution: str = "10_minutes",
                     active_only: bool = False) -> Dict[str, List[Dict]]:
        """
        Find nearest weather stations for location.
        
        Args:
            latitude: Latitude in degrees
            longitude: Longitude in degrees
            parameters: Parameters to search for (None = all)
            n: Number of stations per parameter
            max_distance_km: Maximum distance
            resolution: Time resolution ('hourly', '10_minutes', 'daily')
            active_only: Only return currently active stations
            
        Returns:
            Dictionary mapping parameters to station lists
        """
        if parameters is None:
            parameters = ['solar', 'wind', 'temperature', 'pressure']
        
        result = {}
        
        for param in parameters:
            stations = self.station_manager.find_nearest_stations(
                latitude, longitude, param, n, max_distance_km, 
                resolution=resolution, active_only=active_only
            )
            
            result[param] = [
                {
                    'station_id': s.station_id,
                    'name': s.name,
                    'latitude': s.latitude,
                    'longitude': s.longitude,
                    'elevation': s.elevation,
                    'distance_km': s.distance_km,
                    'is_active': s.is_active()
                }
                for s in stations
            ]
        
        return result
    
    def clear_cache(self):
        """Clear all cached data."""
        self.cache_manager.clear_all(confirm=True)
    
    def get_cache_info(self) -> Dict:
        """Get information about cache status."""
        return self.cache_manager.get_cache_info()
    
    def update_mosmix_parameters(self):
        """Update MOSMIX parameter definitions from DWD."""
        return self.param_manager.update_from_dwd()
    
    def _check_parameter_completeness(self, stations_by_param: Dict[str, List[Station]],
                                     required_params: List[str]) -> Dict:
        """
        Check completeness of parameter coverage across stations.
        
        Args:
            stations_by_param: Dictionary mapping parameters to station lists
            required_params: List of required parameters
            
        Returns:
            Availability report dictionary
        """
        report = {
            'complete': True,
            'missing_parameters': [],
            'partial_coverage': []
        }
        
        for param in required_params:
            if param not in stations_by_param or not stations_by_param[param]:
                report['complete'] = False
                report['missing_parameters'].append(param)
            elif len(stations_by_param[param]) < 1:
                report['partial_coverage'].append(param)
        
        return report
