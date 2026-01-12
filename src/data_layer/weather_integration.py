"""Weather data integration module for vpplib compatibility.

Fetches weather data from DWD using dwd_fetcher and formats it for vpplib components.
Handles data resampling, unit conversions, and format transformations.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

from datetime import datetime
from typing import Optional, Tuple, Dict, List
import pandas as pd
from dwd_fetcher import DWDFetcher
from src.config import DWD, DATA_DIR


def get_dwd_fetcher() -> DWDFetcher:
    """
    Create configured DWD fetcher instance.
    
    Returns:
        Configured DWDFetcher instance with VISE-D settings
    """
    cache_dir = DATA_DIR / ".." / DWD.CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    return DWDFetcher(
        cache_dir=str(cache_dir),
        cache_expiry_hours=DWD.CACHE_EXPIRY_HOURS,
        timezone=DWD.TIMEZONE,
        ranking_strategy=DWD.RANKING_STRATEGY
    )


def fetch_weather_for_pv(
    latitude: float,
    longitude: float,
    start_date: datetime,
    end_date: datetime,
    resolution: str = "15min"
) -> Tuple[pd.DataFrame, Dict]:
    """
    Fetch and format weather data for photovoltaic simulations.
    
    This function retrieves DWD weather data and formats it for vpplib's Photovoltaic
    component. The data is automatically resampled to match vpplib's expected temporal
    resolution (default 15 minutes).
    
    Args:
        latitude: Location latitude in decimal degrees
        longitude: Location longitude in decimal degrees
        start_date: Start of data period
        end_date: End of data period
        resolution: Target resolution ("15min", "hourly", or "10min")
    
    Returns:
        Tuple containing:
        - DataFrame: Weather data formatted for vpplib Environment.pv_data
        - Dict: Metadata about the data source (station info, quality metrics)
    
    vpplib Environment.pv_data Expected Format:
        The returned DataFrame is directly assignable to vpplib's Environment.pv_data
        attribute and must contain the following columns:
        
        - 'ghi': Global Horizontal Irradiance in W/m² (float)
            Solar radiation on a horizontal surface
        - 'temp_air': Air temperature in degrees Celsius (float)
            Ambient air temperature at 2m height
        - 'wind_speed': Wind speed in m/s (float, optional)
            Wind speed at 10m height, used for thermal modeling
        - 'pressure': Atmospheric pressure in hPa (float, optional)
            Surface pressure, affects air density calculations
        
        Index: DatetimeIndex with timezone information (Europe/Berlin)
        Frequency: Must match vpplib component expectations (typically 15min)
        
        Example structure:
        ```
                                   ghi  temp_air  wind_speed  pressure
        2024-01-01 00:00:00+01:00   0.0     5.2         3.1    1013.2
        2024-01-01 00:15:00+01:00   0.0     5.1         3.2    1013.1
        2024-01-01 00:30:00+01:00   0.0     5.0         3.0    1013.0
        ```
    
    Usage Example:
        ```python
        from vpplib.environment import Environment
        from src.data_layer.weather_integration import fetch_weather_for_pv
        
        # Fetch formatted weather data
        weather_data, metadata = fetch_weather_for_pv(
            latitude=51.4,
            longitude=6.97,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            resolution="15min"
        )
        
        # Create vpplib Environment and inject data
        env = Environment(start="2024-01-01 00:00:00", end="2024-12-31 23:45:00")
        env.pv_data = weather_data  # Direct assignment
        
        # Now env.pv_data is ready for PV simulations
        pv = Photovoltaic(identifier="PV1", environment=env, ...)
        pv.prepare_time_series()
        ```
    
    Raises:
        ValueError: If no suitable DWD station found within search radius
        RuntimeError: If data fetching or transformation fails
    """
    fetcher = get_dwd_fetcher()
    
    try:
        # Fetch 10-minute data from DWD (highest resolution available)
        # Use single station to avoid column overlap issues
        data, metadata = fetcher.get_observations(
            latitude=latitude,
            longitude=longitude,
            parameters=['solar', 'temperature', 'wind', 'pressure'],
            start_date=start_date,
            end_date=end_date,
            resolution='10_minutes',
            max_distance_km=DWD.MAX_STATION_DISTANCE_KM,
            n_stations=1,  # Use single best station to avoid merge conflicts
            for_pvlib=True,  # Auto-format for pvlib compatibility
            allow_multi_station=False  # Disable multi-station merging
        )
        
        # Resample to target resolution if needed
        if resolution != "10min":
            if resolution == "15min":
                data = data.resample('15T').interpolate(method='linear')
            elif resolution == "hourly":
                data = data.resample('H').interpolate(method='linear')
        
        return data, metadata
        
    except Exception as e:
        raise RuntimeError(f"Failed to fetch PV weather data: {e}") from e


def fetch_weather_for_wind(
    latitude: float,
    longitude: float,
    start_date: datetime,
    end_date: datetime,
    resolution: str = "15min",
    wind_height: float = 10.0
) -> Tuple[pd.DataFrame, Dict]:
    """
    Fetch and format weather data for wind turbine simulations.
    
    This function retrieves DWD weather data and formats it for vpplib's WindPower
    component using windpowerlib conventions. The data includes wind speed at
    specified height, temperature, and pressure.
    
    Args:
        latitude: Location latitude in decimal degrees
        longitude: Location longitude in decimal degrees
        start_date: Start of data period
        end_date: End of data period
        resolution: Target resolution ("15min", "hourly", or "10min")
        wind_height: Wind measurement height in meters (default 10m)
    
    Returns:
        Tuple containing:
        - DataFrame: Weather data formatted for vpplib Environment.wind_data
        - Dict: Metadata about the data source
    
    vpplib Environment.wind_data Expected Format:
        The returned DataFrame is directly assignable to vpplib's Environment.wind_data
        attribute and must follow windpowerlib's MultiIndex column structure:
        
        MultiIndex Columns (parameter, height):
        - ('wind_speed', '10'): Wind speed at 10m height in m/s (float)
        - ('wind_speed', '100'): Wind speed at 100m height in m/s (float, if available)
        - ('temperature', '2'): Air temperature at 2m height in Kelvin (float)
        - ('pressure', '0'): Surface pressure in Pa (float)
        - ('roughness_length', '0'): Surface roughness in m (float, optional)
        
        Index: DatetimeIndex with timezone information (Europe/Berlin)
        Frequency: Must match windpowerlib expectations (typically 15min or hourly)
        
        Example structure:
        ```
                                  wind_speed       temperature  pressure  roughness_length
                                          10      2             0          0
        2024-01-01 00:00:00+01:00        3.5  278.15      101325.0       0.15
        2024-01-01 00:15:00+01:00        3.7  278.10      101320.0       0.15
        2024-01-01 00:30:00+01:00        3.6  278.05      101315.0       0.15
        ```
        
        Note: windpowerlib expects:
        - Temperature in Kelvin (not Celsius)
        - Pressure in Pa (not hPa)
        - Wind speed extrapolated to hub height using logarithmic wind profile
    
    Usage Example:
        ```python
        from vpplib.environment import Environment
        from windpowerlib import WindTurbine
        from src.data_layer.weather_integration import fetch_weather_for_wind
        
        # Fetch formatted weather data
        weather_data, metadata = fetch_weather_for_wind(
            latitude=51.2,
            longitude=6.43,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            resolution="15min",
            wind_height=10.0
        )
        
        # Create vpplib Environment and inject data
        env = Environment(start="2024-01-01 00:00:00", end="2024-12-31 23:45:00")
        env.wind_data = weather_data  # Direct assignment
        
        # Now env.wind_data is ready for wind turbine simulations
        wind_turbine = WindTurbine(...)
        wind = WindPower(identifier="Wind1", environment=env, ...)
        wind.prepare_time_series()
        ```
    
    Raises:
        ValueError: If no suitable DWD station found within search radius
        RuntimeError: If data fetching or transformation fails
    """
    fetcher = get_dwd_fetcher()
    
    try:
        # Fetch 10-minute data from DWD with windpowerlib formatting
        # Use single station to avoid column overlap issues
        data, metadata = fetcher.get_observations(
            latitude=latitude,
            longitude=longitude,
            parameters=['wind', 'temperature', 'pressure'],
            start_date=start_date,
            end_date=end_date,
            resolution='10_minutes',
            max_distance_km=DWD.MAX_STATION_DISTANCE_KM,
            n_stations=1,
            for_windpowerlib=True,  # Auto-format for windpowerlib
            allow_multi_station=False
        )
        
        # Resample to target resolution if needed
        if resolution != "10min":
            if resolution == "15min":
                data = data.resample('15T').interpolate(method='linear')
            elif resolution == "hourly":
                data = data.resample('H').interpolate(method='linear')
        
        # Add roughness length if not present (typical value for open terrain)
        if ('roughness_length', '0') not in data.columns:
            data[('roughness_length', '0')] = 0.15  # meters, open terrain
        
        return data, metadata
        
    except Exception as e:
        raise RuntimeError(f"Failed to fetch wind weather data: {e}") from e


def fetch_weather_for_heatpump(
    latitude: float,
    longitude: float,
    start_date: datetime,
    end_date: datetime,
    resolution: str = "hourly"
) -> Tuple[pd.DataFrame, Dict]:
    """
    Fetch and format weather data for heat pump simulations.
    
    Heat pumps primarily need temperature data for COP (Coefficient of Performance)
    calculations, which depend on ambient temperature.
    
    Args:
        latitude: Location latitude in decimal degrees
        longitude: Location longitude in decimal degrees
        start_date: Start of data period
        end_date: End of data period
        resolution: Target resolution ("hourly" or "daily")
    
    Returns:
        Tuple containing:
        - DataFrame: Temperature data formatted for heat pump simulations
        - Dict: Metadata about the data source
    
    Expected Format:
        Simple DataFrame with temperature column:
        
        - 'temp_air': Air temperature in degrees Celsius (float)
        
        Index: DatetimeIndex with timezone information (Europe/Berlin)
        Frequency: Hourly or daily depending on use case
        
        Example structure:
        ```
                                   temp_air
        2024-01-01 00:00:00+01:00      5.2
        2024-01-01 01:00:00+01:00      5.1
        2024-01-01 02:00:00+01:00      5.0
        ```
    
    Usage Example:
        ```python
        from vpplib.environment import Environment
        from src.data_layer.weather_integration import fetch_weather_for_heatpump
        
        # Fetch formatted temperature data
        temp_data, metadata = fetch_weather_for_heatpump(
            latitude=50.94,
            longitude=6.96,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            resolution="hourly"
        )
        
        # Use with vpplib heat pump
        env = Environment(start="2024-01-01 00:00:00", end="2024-12-31 23:00:00")
        # Temperature data can be extracted and used for COP calculations
        temperatures = temp_data['temp_air']
        ```
    
    Raises:
        ValueError: If no suitable DWD station found within search radius
        RuntimeError: If data fetching or transformation fails
    """
    fetcher = get_dwd_fetcher()
    
    try:
        # Determine DWD resolution based on target
        dwd_resolution = 'hourly' if resolution in ['hourly', '15min'] else 'daily'
        
        # Fetch temperature data from DWD
        # Use single station to avoid column overlap issues
        data, metadata = fetcher.get_observations(
            latitude=latitude,
            longitude=longitude,
            parameters=['temperature'],
            start_date=start_date,
            end_date=end_date,
            resolution=dwd_resolution,
            max_distance_km=DWD.MAX_STATION_DISTANCE_KM,
            n_stations=1,
            for_pvlib=True,  # Uses pvlib format for consistent column naming
            allow_multi_station=False
        )
        
        # Resample if needed
        if resolution == "15min" and dwd_resolution == "hourly":
            data = data.resample('15T').interpolate(method='linear')
        
        return data, metadata
        
    except Exception as e:
        raise RuntimeError(f"Failed to fetch heat pump weather data: {e}") from e


def find_nearest_stations(
    latitude: float,
    longitude: float,
    parameters: List[str],
    n_stations: int = 5
) -> Dict:
    """
    Find nearest DWD weather stations for given location and parameters.
    
    Args:
        latitude: Location latitude in decimal degrees
        longitude: Location longitude in decimal degrees
        parameters: List of weather parameters needed
            Options: 'solar', 'wind', 'temperature', 'pressure'
        n_stations: Number of nearest stations to return
    
    Returns:
        Dict mapping parameter names to lists of station info dicts.
        Each station dict contains:
        - station_id: 5-digit DWD station ID
        - name: Station name
        - latitude, longitude: Station coordinates
        - elevation: Station elevation in meters
        - distance_km: Distance from query location
        - is_active: Whether station is currently active
        - quality_score: Data quality score (0.0-1.0)
    
    Usage Example:
        ```python
        from src.data_layer.weather_integration import find_nearest_stations
        
        # Find stations for solar data near Cologne
        stations = find_nearest_stations(
            latitude=51.4,
            longitude=6.97,
            parameters=['solar', 'temperature'],
            n_stations=3
        )
        
        # Display found stations
        for param, station_list in stations.items():
            print(f"\\n{param.upper()} stations:")
            for station in station_list:
                print(f"  {station['station_id']}: {station['name']} "
                      f"({station['distance_km']:.1f} km)")
        ```
    """
    fetcher = get_dwd_fetcher()
    
    stations = fetcher.find_stations(
        latitude=latitude,
        longitude=longitude,
        parameters=parameters,
        n=n_stations,
        max_distance_km=DWD.MAX_STATION_DISTANCE_KM,
        resolution='hourly',  # Use hourly for broadest station availability
        active_only=False  # Don't filter by metadata end_date (often outdated)
    )
    
    return stations
