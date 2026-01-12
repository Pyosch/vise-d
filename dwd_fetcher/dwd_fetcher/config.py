"""
Configuration module for DWD Data Fetcher.
Contains URL patterns, parameter mappings, and configurable options.
"""

from enum import Enum
from typing import Dict


class WeightingStrategy(Enum):
    """Strategy for combining data from multiple stations."""
    INVERSE_DISTANCE = "inverse_distance"
    SIMPLE_AVERAGE = "simple_average"
    NEAREST_ONLY = "nearest_only"
    DATA_COMPLETENESS = "data_completeness"


class DWDConfig:
    """Configuration settings for DWD data fetching."""
    
    # Base URLs
    BASE_URL = "https://opendata.dwd.de"
    CDC_BASE = f"{BASE_URL}/climate_environment/CDC"
    WEATHER_BASE = f"{BASE_URL}/weather"
    
    # Observation data paths
    OBS_BASE = f"{CDC_BASE}/observations_germany/climate"
    OBS_HOURLY = f"{OBS_BASE}/hourly"
    OBS_DAILY = f"{OBS_BASE}/daily"
    OBS_10MIN = f"{OBS_BASE}/10_minutes"
    
    # Forecast data paths
    MOSMIX_BASE = f"{WEATHER_BASE}/local_forecasts/mos"
    MOSMIX_S = f"{MOSMIX_BASE}/MOSMIX_S/all_stations/kml"
    MOSMIX_L = f"{MOSMIX_BASE}/MOSMIX_L/single_stations"
    
    # Metadata and documentation
    HELP_URL = f"{CDC_BASE}/help"
    MET_ELEMENT_DEF_URL = f"{WEATHER_BASE}/lib/MetElementDefinition.xml"
    
    # Parameter directory names (DWD naming)
    # Note: Pressure location depends on resolution (see get_obs_url)
    PARAM_DIRS = {
        'solar': 'solar',
        'wind': 'wind',
        'temperature': 'air_temperature',
        'pressure': 'pressure',  # Hourly/daily only; 10-minute is in air_temperature
    }
    
    # Parameter codes for observations
    # Note: Pressure codes depend on resolution (see get_param_code)
    OBS_PARAM_CODES = {
        'solar': 'ST',  # Solar radiation (Stundenwerte)
        'wind': 'FF',  # Wind speed
        'temperature': 'TU',  # Temperature
        'pressure': 'P0',  # Hourly/daily; 10-minute uses TU (in air_temperature)
    }
    
    # MOSMIX parameter codes (will be enhanced by MetElementDefinition.xml)
    MOSMIX_PARAM_CODES = {
        'temperature': 'TTT',  # Temperature 2m above surface (K)
        'wind_speed': 'FF',  # Wind speed (m/s)
        'wind_direction': 'DD',  # Wind direction (degrees)
        'pressure': 'PPPP',  # Pressure reduced (Pa)
        'radiation_global': 'Rad1h',  # Global radiation last hour (kJ/m²)
        'radiation_sky': 'RadS3',  # Short wave radiation (kJ/m²)
        'radiation_long': 'RadL3',  # Long wave radiation (kJ/m²)
    }
    
    # Cache settings
    DEFAULT_CACHE_DIR = ".dwd_cache"
    DEFAULT_CACHE_EXPIRY_HOURS = 24
    METADATA_CACHE_EXPIRY_DAYS = 7
    
    # Station search settings
    DEFAULT_SEARCH_RADIUS_KM = 50
    MAX_STATIONS_TO_COMBINE = 5
    
    # Data quality settings
    MISSING_VALUE_INDICATOR = -999
    QUALITY_FLAG_THRESHOLD = 1  # Minimum quality level to accept
    
    # Multi-station settings
    DEFAULT_WEIGHTING_STRATEGY = WeightingStrategy.INVERSE_DISTANCE
    DISTANCE_WEIGHT_POWER = 2  # For inverse distance weighting (1/d^p)
    
    # File patterns
    OBS_RECENT_SUFFIX = "_akt"
    OBS_HISTORICAL_SUFFIX = "_hist"
    
    # MOSMIX files
    MOSMIX_LATEST_FILE = "MOSMIX_S_LATEST_240.kmz"
    
    # Timezone
    DWD_TIMEZONE = "UTC"
    
    @classmethod
    def get_obs_url(cls, parameter: str, resolution: str = "10_minutes") -> str:
        """
        Get observation data URL for a parameter.
        
        Args:
            parameter: Parameter name ('solar', 'wind', 'temperature', 'pressure')
            resolution: Time resolution ('hourly', 'daily', '10_minutes')
            
        Returns:
            URL string for the parameter directory
        """
        # Special case: 10-minute pressure data is in air_temperature directory
        if parameter == 'pressure' and resolution == '10_minutes':
            param_dir = 'air_temperature'
        else:
            param_dir = cls.PARAM_DIRS.get(parameter)
            if not param_dir:
                raise ValueError(f"Unknown parameter: {parameter}")
        
        if resolution == "hourly":
            base = cls.OBS_HOURLY
        elif resolution == "daily":
            base = cls.OBS_DAILY
        elif resolution == "10_minutes":
            base = cls.OBS_10MIN
        else:
            raise ValueError(f"Unknown resolution: {resolution}")
        
        return f"{base}/{param_dir}"
    
    @classmethod
    def get_station_description_filename(cls, parameter: str, resolution: str = "hourly") -> str:
        """
        Get station description filename for a parameter.
        
        Args:
            parameter: Parameter name
            resolution: Time resolution
            
        Returns:
            Filename for station description file
        """
        # Special cases for 10-minute data (uses "zehn_min" prefix with different codes)
        if resolution == '10_minutes':
            special_codes = {
                'solar': 'sd',      # Solar data
                'wind': 'fx',       # Extreme wind
                'temperature': 'tu', # Temperature
                'pressure': 'tu'    # 10-minute pressure uses same file as temperature
            }
            if parameter in special_codes:
                return f"zehn_min_{special_codes[parameter]}_Beschreibung_Stationen.txt"
        
        # Map parameters to their station file codes (actual DWD naming)
        param_to_code = {
            'solar': 'ST',
            'wind': 'FF',  # Wind speed
            'temperature': 'TU',  # Temperature
            'pressure': 'P0'  # Hourly/daily pressure has separate files
        }
        
        code = param_to_code.get(parameter, parameter.upper())
        
        if resolution == "hourly":
            time_str = "Stundenwerte"
        elif resolution == "daily":
            time_str = "Tageswerte"
        elif resolution == "10_minutes":
            time_str = "10minutenwerte"
        else:
            time_str = "Stundenwerte"
        
        # DWD naming: [CODE]_[Resolution]_Beschreibung_Stationen.txt
        return f"{code}_{time_str}_Beschreibung_Stationen.txt"
    
    @classmethod
    def get_param_code(cls, parameter: str, resolution: str) -> str:
        """
        Get the parameter code for data files based on resolution.
        
        For pressure, the code differs by resolution:
        - 10-minute: Uses 'TU' (in air_temperature files)
        - Hourly/daily: Uses 'P0' (separate pressure files)
        
        Args:
            parameter: Parameter name
            resolution: Time resolution
            
        Returns:
            Parameter code string
        """
        # Special case: 10-minute pressure uses TU code (air_temperature files)
        if parameter == 'pressure' and resolution == '10_minutes':
            return 'TU'
        
        # Default mapping
        return cls.OBS_PARAM_CODES.get(parameter, parameter.upper())
