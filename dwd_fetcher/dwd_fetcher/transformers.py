"""
Data transformers for unit conversion and format compatibility.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import pytz

from .config import DWDConfig, WeightingStrategy
from .stations import Station


class DataTransformer:
    """Transforms DWD data for pvlib and windpowerlib compatibility."""
    
    def __init__(self, timezone: str = "Europe/Berlin"):
        """
        Initialize data transformer.
        
        Args:
            timezone: Target timezone for datetime conversion
        """
        self.timezone = timezone
    
    def transform_for_pvlib(self, df: pd.DataFrame,
                           parameter_mapping: Optional[Dict[str, str]] = None) -> pd.DataFrame:
        """
        Transform data for pvlib compatibility.
        
        Args:
            df: Input DataFrame
            parameter_mapping: Map DWD column names to pvlib names
            
        Returns:
            Transformed DataFrame with pvlib-compatible format
        """
        result = df.copy()
        
        # Default parameter mapping
        if parameter_mapping is None:
            parameter_mapping = {
                # Common observation column names to pvlib names
                'ATMO_STRAHL': 'ghi',  # Global Horizontal Irradiance
                'FG_LBERG': 'ghi',     # Alternative GHI name
                'TT_TU': 'temp_air',    # Air temperature
                'FF_10': 'wind_speed',  # Wind speed at 10m
                'P0': 'pressure',       # Pressure (hourly/daily)
                'PP_10': 'pressure',    # Pressure (10-minute)
                'P': 'pressure',        # Alternative pressure name
                # MOSMIX parameter names
                'Rad1h': 'ghi',
                'TTT': 'temp_air',
                'FF': 'wind_speed',
                'PPPP': 'pressure',
            }
        
        # Rename columns
        rename_dict = {}
        for old_name, new_name in parameter_mapping.items():
            if old_name in result.columns:
                rename_dict[old_name] = new_name
        
        if rename_dict:
            result = result.rename(columns=rename_dict)
        
        # Unit conversions
        
        # Convert temperature from Kelvin to Celsius if needed
        if 'temp_air' in result.columns:
            # Check if values are in Kelvin range (> 200)
            if result['temp_air'].dropna().median() > 200:
                result['temp_air'] = result['temp_air'] - 273.15
        
        # Convert radiation from kJ/m² to W/m² if needed
        # MOSMIX Rad1h is in kJ/m² for last hour
        # To convert to W/m²: kJ/m²/h * 1000 / 3600 = W/m²
        if 'ghi' in result.columns:
            # Check if values are in kJ/m² range (typically < 5000)
            median_val = result['ghi'].dropna().median()
            if median_val > 0 and median_val < 5000:
                result['ghi'] = result['ghi'] * 1000 / 3600
        
        # Convert pressure from Pa to hPa if needed
        if 'pressure' in result.columns:
            # Check if values are in Pa range (> 10000)
            # Handle both Series and DataFrame columns
            pressure_col = result['pressure']
            if isinstance(pressure_col, pd.DataFrame):
                # If it's a DataFrame, flatten it
                pressure_values = pressure_col.stack().dropna()
            else:
                pressure_values = pressure_col.dropna()
            
            if len(pressure_values) > 0:
                median_pressure = float(pressure_values.median())
                if median_pressure > 10000:
                    result['pressure'] = result['pressure'] / 100
        
        # Ensure datetime index is timezone-aware
        if isinstance(result.index, pd.DatetimeIndex):
            if result.index.tz is None:
                # Assume UTC and localize
                result.index = result.index.tz_localize('UTC')
            
            # Convert to target timezone
            if self.timezone != 'UTC':
                result.index = result.index.tz_convert(self.timezone)
        
        return result
    
    def transform_for_windpowerlib(self, df: pd.DataFrame,
                                   parameter_mapping: Optional[Dict[str, str]] = None,
                                   wind_height: float = 10.0) -> pd.DataFrame:
        """
        Transform data for windpowerlib compatibility.
        
        Args:
            df: Input DataFrame
            parameter_mapping: Map DWD column names to windpowerlib names
            wind_height: Wind measurement height in meters
            
        Returns:
            Transformed DataFrame with windpowerlib-compatible format
        """
        result = df.copy()
        
        # Default parameter mapping
        if parameter_mapping is None:
            parameter_mapping = {
                'FF_10': 'wind_speed',
                'FF': 'wind_speed',
                'DD': 'wind_direction',
                'TT_TU': 'temperature',
                'TTT': 'temperature',
                'P0': 'pressure',        # Hourly/daily pressure
                'PP_10': 'pressure',     # 10-minute pressure
                'PPPP': 'pressure',
                'TD': 'density',  # If available
            }
        
        # Rename columns
        rename_dict = {}
        for old_name, new_name in parameter_mapping.items():
            if old_name in result.columns:
                rename_dict[old_name] = new_name
        
        if rename_dict:
            result = result.rename(columns=rename_dict)
        
        # Unit conversions
        
        # Convert temperature from Kelvin to Celsius if needed
        if 'temperature' in result.columns:
            if result['temperature'].dropna().median() > 200:
                result['temperature'] = result['temperature'] - 273.15
        
        # Convert pressure from Pa to hPa if needed
        if 'pressure' in result.columns:
            if result['pressure'].dropna().median() > 10000:
                result['pressure'] = result['pressure'] / 100
        
        # Add height column
        result['height'] = wind_height
        
        # Ensure datetime index is timezone-aware
        if isinstance(result.index, pd.DatetimeIndex):
            if result.index.tz is None:
                result.index = result.index.tz_localize('UTC')
            
            if self.timezone != 'UTC':
                result.index = result.index.tz_convert(self.timezone)
        
        return result
    
    def merge_multi_station_data(self, station_data: Dict[Station, pd.DataFrame],
                                 strategy: WeightingStrategy = WeightingStrategy.INVERSE_DISTANCE,
                                 power: float = 2.0) -> pd.DataFrame:
        """
        Merge data from multiple stations using specified weighting strategy.
        
        Args:
            station_data: Dictionary mapping Station objects to their DataFrames
            strategy: Weighting strategy to use
            power: Power for inverse distance weighting
            
        Returns:
            Merged DataFrame
        """
        if not station_data:
            return pd.DataFrame()
        
        if len(station_data) == 1:
            return list(station_data.values())[0]
        
        # Get all timestamps (union of all indices)
        all_indices = []
        for df in station_data.values():
            all_indices.append(df.index)
        
        combined_index = pd.DatetimeIndex(sorted(set().union(*[set(idx) for idx in all_indices])))
        
        # Get all columns
        all_columns = set()
        for df in station_data.values():
            all_columns.update(df.columns)
        
        # Filter to only numeric columns for merging
        numeric_columns = []
        for col in all_columns:
            for df in station_data.values():
                if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                    numeric_columns.append(col)
                    break
        
        # Initialize result DataFrame
        result = pd.DataFrame(index=combined_index, columns=sorted(numeric_columns))
        
        if strategy == WeightingStrategy.NEAREST_ONLY:
            # Use only nearest station
            nearest_station = min(station_data.keys(), key=lambda s: s.distance_km or float('inf'))
            result = station_data[nearest_station].reindex(combined_index)
        
        elif strategy == WeightingStrategy.SIMPLE_AVERAGE:
            # Simple average of all stations
            for col in numeric_columns:
                values_list = []
                for station, df in station_data.items():
                    if col in df.columns:
                        values_list.append(df[col].reindex(combined_index))
                
                if values_list:
                    result[col] = pd.concat(values_list, axis=1).mean(axis=1)
        
        elif strategy == WeightingStrategy.INVERSE_DISTANCE:
            # Inverse distance weighted average
            for col in numeric_columns:
                weighted_sum = pd.Series(0.0, index=combined_index)
                weight_sum = pd.Series(0.0, index=combined_index)
                
                for station, df in station_data.items():
                    if col in df.columns and station.distance_km is not None:
                        # Calculate weight (1 / distance^power)
                        weight = 1.0 / (station.distance_km ** power + 1e-10)
                        
                        series = df[col].reindex(combined_index)
                        valid_mask = series.notna()
                        
                        weighted_sum[valid_mask] += series[valid_mask] * weight
                        weight_sum[valid_mask] += weight
                
                # Calculate weighted average
                result[col] = weighted_sum / weight_sum
        
        elif strategy == WeightingStrategy.DATA_COMPLETENESS:
            # Weight by data completeness
            for col in numeric_columns:
                # Calculate completeness for each station
                completeness = {}
                for station, df in station_data.items():
                    if col in df.columns:
                        completeness[station] = 1.0 - df[col].isna().mean()
                    else:
                        completeness[station] = 0.0
                
                if not completeness:
                    continue
                
                # Weighted average based on completeness
                weighted_sum = pd.Series(0.0, index=combined_index)
                weight_sum = pd.Series(0.0, index=combined_index)
                
                for station, df in station_data.items():
                    if col in df.columns:
                        weight = completeness[station]
                        
                        series = df[col].reindex(combined_index)
                        valid_mask = series.notna()
                        
                        weighted_sum[valid_mask] += series[valid_mask] * weight
                        weight_sum[valid_mask] += weight
                
                result[col] = weighted_sum / weight_sum
        
        return result
    
    def apply_quality_filters(self, df: pd.DataFrame,
                             quality_column: str = 'QN',
                             min_quality: int = 1) -> pd.DataFrame:
        """
        Filter data based on quality flags.
        
        Args:
            df: Input DataFrame
            quality_column: Name of quality flag column
            min_quality: Minimum quality threshold
            
        Returns:
            Filtered DataFrame
        """
        result = df.copy()
        
        if quality_column in result.columns:
            # Mask values below quality threshold
            mask = result[quality_column] >= min_quality
            
            # Apply mask to all numeric columns except quality column
            for col in result.columns:
                if col != quality_column and pd.api.types.is_numeric_dtype(result[col]):
                    result.loc[~mask, col] = np.nan
        
        return result
    
    def handle_missing_data(self, df: pd.DataFrame,
                           method: str = 'interpolate',
                           limit: Optional[int] = 3) -> pd.DataFrame:
        """
        Handle missing data in DataFrame.
        
        Args:
            df: Input DataFrame
            method: Method to use ('interpolate', 'forward_fill', 'drop', 'none')
            limit: Maximum number of consecutive NaNs to fill
            
        Returns:
            DataFrame with missing data handled
        """
        result = df.copy()
        
        if method == 'interpolate':
            # Linear interpolation
            result = result.interpolate(method='linear', limit=limit, limit_direction='both')
        
        elif method == 'forward_fill':
            result = result.fillna(method='ffill', limit=limit)
        
        elif method == 'drop':
            result = result.dropna()
        
        # method == 'none' returns as-is
        
        return result
