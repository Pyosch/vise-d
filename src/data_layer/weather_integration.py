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
import numpy as np
from dwd_fetcher import DWDFetcher
from src.config import DWD, DATA_DIR

try:
    from pvlib import location, clearsky, irradiance
    PVLIB_AVAILABLE = True
except ImportError:
    PVLIB_AVAILABLE = False


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
    resolution: str = "15min",
    n_stations: int = 3,
    allow_multi_station: bool = True
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
        n_stations: Number of stations to check (default 3)
        allow_multi_station: Whether to combine data from multiple stations (default True)
    
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
        # Use allow_multi_station to combine data from multiple stations if needed
        # This ensures we get solar data even if nearest station lacks it
        data, metadata = fetcher.get_observations(
            latitude=latitude,
            longitude=longitude,
            parameters=['solar', 'temperature', 'wind', 'pressure'],
            start_date=start_date,
            end_date=end_date,
            resolution='10_minutes',
            max_distance_km=DWD.MAX_STATION_DISTANCE_KM,
            n_stations=n_stations,
            for_pvlib=True,  # Auto-format for pvlib compatibility
            allow_multi_station=allow_multi_station
        )
        
        # Check if data is empty
        if data.empty:
            # Provide helpful error message with details
            error_msg = f"Keine PV-Wetterdaten verfügbar.\n"
            error_msg += f"Standort: {latitude:.4f}°N, {longitude:.4f}°E\n"
            error_msg += f"Zeitraum: {start_date.date()} bis {end_date.date()}\n"
            if metadata.get('warnings'):
                error_msg += "Hinweise:\n" + "\n".join(f"  • {w}" for w in metadata['warnings'])
            raise ValueError(error_msg)
        
        # Ensure DatetimeIndex for resampling
        if not isinstance(data.index, pd.DatetimeIndex):
            raise ValueError(f"Expected DatetimeIndex but got {type(data.index).__name__}")
        
        # Clean up quality flag columns to fix Arrow serialization issues
        # These columns are metadata and not needed for vpplib
        qn_cols = [col for col in data.columns if col.startswith('QN_')]
        if qn_cols:
            data = data.drop(columns=qn_cols)
        
        # Validate that required solar radiation columns are present
        required_cols = ['ghi', 'dni', 'dhi']
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            # Try to generate synthetic clearsky solar data as fallback
            if PVLIB_AVAILABLE and 'temp_air' in data.columns:
                warning_msg = (
                    f"⚠️ Station hat keine Solarstrahlungsdaten. "
                    f"Verwende synthetische Clearsky-Daten als Ersatz.\n"
                    f"Fehlende Spalten: {missing_cols}\n"
                )
                if metadata.get('station_name'):
                    warning_msg = f"Station: {metadata['station_name']}\n" + warning_msg
                
                # Add warning to metadata
                if 'warnings' not in metadata:
                    metadata['warnings'] = []
                metadata['warnings'].append(warning_msg)
                
                # Generate clearsky solar data
                data = _generate_clearsky_solar(
                    data=data,
                    latitude=latitude,
                    longitude=longitude,
                    timezone='Europe/Berlin'
                )
            else:
                # No fallback available - raise error
                available_cols = list(data.columns)
                error_msg = (
                    f"Keine Solardaten verfügbar für den gewählten Standort.\n"
                    f"Fehlende Spalten: {missing_cols}\n"
                    f"Verfügbare Spalten: {available_cols}\n\n"
                    f"Die gewählte DWD-Station hat keine Solarstrahlungsdaten für den Zeitraum.\n"
                )
                if not PVLIB_AVAILABLE:
                    error_msg += "\nPvlib ist nicht installiert - kann keine synthetischen Daten generieren.\n"
                    error_msg += "Installieren Sie pvlib mit: pip install pvlib\n\n"
                error_msg += (
                    f"Bitte wählen Sie:\n"
                    f"  • Eine andere DWD-Station mit Solar-Messungen, oder\n"
                    f"  • Nutzen Sie die Koordinaten-Methode für eine andere Station"
                )
                if metadata.get('station_name'):
                    error_msg = f"Station: {metadata['station_name']}\n" + error_msg
                raise ValueError(error_msg)
        
        # Resample to target resolution if needed
        if resolution != "10min":
            if resolution == "15min":
                data = data.resample('15min').interpolate(method='linear')
            elif resolution == "hourly":
                data = data.resample('h').interpolate(method='linear')
        
        return data, metadata
        
    except Exception as e:
        raise RuntimeError(f"Failed to fetch PV weather data: {e}") from e


def fetch_weather_for_wind(
    latitude: float,
    longitude: float,
    start_date: datetime,
    end_date: datetime,
    resolution: str = "15min",
    wind_height: float = 10.0,
    n_stations: int = 1,
    allow_multi_station: bool = False
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
        n_stations: Number of stations to check (default 1)
        allow_multi_station: Whether to combine data from multiple stations (default False)
    
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
        data, metadata = fetcher.get_observations(
            latitude=latitude,
            longitude=longitude,
            parameters=['wind', 'temperature', 'pressure'],
            start_date=start_date,
            end_date=end_date,
            resolution='10_minutes',
            max_distance_km=DWD.MAX_STATION_DISTANCE_KM,
            n_stations=n_stations,
            for_windpowerlib=True,  # Auto-format for windpowerlib
            allow_multi_station=allow_multi_station
        )
        
        # Check if data is empty
        if data.empty:
            # Provide helpful error message with details
            error_msg = f"Keine Wind-Wetterdaten verfügbar.\n"
            error_msg += f"Standort: {latitude:.4f}°N, {longitude:.4f}°E\n"
            error_msg += f"Zeitraum: {start_date.date()} bis {end_date.date()}\n"
            if metadata.get('warnings'):
                error_msg += "Hinweise:\n" + "\n".join(f"  • {w}" for w in metadata['warnings'])
            raise ValueError(error_msg)
        
        # Ensure DatetimeIndex for resampling
        if not isinstance(data.index, pd.DatetimeIndex):
            raise ValueError(f"Expected DatetimeIndex but got {type(data.index).__name__}")
        
        # Clean up quality flag columns to fix Arrow serialization issues
        qn_cols = [col for col in data.columns if col.startswith('QN_')]
        if qn_cols:
            # For windpowerlib MultiIndex, need to check all column levels
            cols_to_drop = [col for col in data.columns if isinstance(col, tuple) and any(str(level).startswith('QN_') for level in col)]
            if cols_to_drop:
                data = data.drop(columns=cols_to_drop)
            else:
                # Fallback for simple index
                data = data.drop(columns=qn_cols)
        
        # Resample to target resolution if needed
        if resolution != "10min":
            if resolution == "15min":
                data = data.resample('15min').interpolate(method='linear')
            elif resolution == "hourly":
                data = data.resample('h').interpolate(method='linear')
        
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
    resolution: str = "hourly",
    n_stations: int = 1,
    allow_multi_station: bool = False
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
        n_stations: Number of stations to check (default 1)
        allow_multi_station: Whether to combine data from multiple stations (default False)
    
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
        data, metadata = fetcher.get_observations(
            latitude=latitude,
            longitude=longitude,
            parameters=['temperature'],
            start_date=start_date,
            end_date=end_date,
            resolution=dwd_resolution,
            max_distance_km=DWD.MAX_STATION_DISTANCE_KM,
            n_stations=n_stations,
            for_pvlib=True,  # Uses pvlib format for consistent column naming
            allow_multi_station=allow_multi_station
        )
        
        # Check if data is empty
        if data.empty:
            # Provide helpful error message with details
            error_msg = f"Keine Temperaturdaten verfügbar.\n"
            error_msg += f"Standort: {latitude:.4f}°N, {longitude:.4f}°E\n"
            error_msg += f"Zeitraum: {start_date.date()} bis {end_date.date()}\n"
            if metadata.get('stations_used'):
                if 'temperature' in metadata['stations_used'] and metadata['stations_used']['temperature']:
                    station = metadata['stations_used']['temperature'][0]
                    error_msg += f"Nächste Station: {station.get('station_id')} - {station.get('name')}\n"
                    error_msg += f"Entfernung: {station.get('distance_km', 0):.1f} km\n"
            if metadata.get('warnings'):
                error_msg += "Hinweise:\n" + "\n".join(f"  • {w}" for w in metadata['warnings'])
            raise ValueError(error_msg)
        
        # Ensure DatetimeIndex for resampling
        if not isinstance(data.index, pd.DatetimeIndex):
            raise ValueError(f"Expected DatetimeIndex but got {type(data.index).__name__}")
        
        # Clean up quality flag columns to fix Arrow serialization issues
        qn_cols = [col for col in data.columns if col.startswith('QN_')]
        if qn_cols:
            data = data.drop(columns=qn_cols)
        
        # Resample if needed
        if resolution == "15min" and dwd_resolution == "hourly":
            data = data.resample('15min').interpolate(method='linear')
        
        return data, metadata
        
    except Exception as e:
        raise RuntimeError(f"Failed to fetch heat pump weather data: {e}") from e


def _generate_clearsky_solar(
    data: pd.DataFrame,
    latitude: float,
    longitude: float,
    timezone: str = 'Europe/Berlin'
) -> pd.DataFrame:
    """
    Generate clearsky solar irradiance data using pvlib.
    
    This is a fallback when DWD station doesn't have measured solar data.
    Uses the simplified Ineichen clearsky model to estimate GHI, DNI, DHI.
    
    Args:
        data: Existing weather DataFrame with DatetimeIndex
        latitude: Location latitude in decimal degrees
        longitude: Location longitude in decimal degrees
        timezone: Timezone string (default: 'Europe/Berlin')
    
    Returns:
        DataFrame: Original data with added solar columns (ghi, dni, dhi)
    
    Note:
        Clearsky models provide theoretical solar radiation under ideal
        (cloudless) conditions. Real measurements would show reduced values
        due to clouds, pollution, etc. Use for planning/estimation only.
    """
    if not PVLIB_AVAILABLE:
        raise ImportError("pvlib required for clearsky solar generation")
    
    result = data.copy()
    
    # Create pvlib Location object
    loc = location.Location(
        latitude=latitude,
        longitude=longitude,
        tz=timezone,
        altitude=0  # Use sea level if elevation unknown
    )
    
    # Get solar position for all timestamps
    times = result.index
    solpos = loc.get_solarposition(times)
    
    # Generate clearsky irradiance using simplified Ineichen model
    clearsky_data = loc.get_clearsky(times, model='simplified_solis')
    
    # Add solar columns to result
    result['ghi'] = clearsky_data['ghi']
    result['dni'] = clearsky_data['dni']
    result['dhi'] = clearsky_data['dhi']
    
    # Set negative or NaN values to zero (happens at night)
    for col in ['ghi', 'dni', 'dhi']:
        result[col] = result[col].fillna(0).clip(lower=0)
    
    return result


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
    
    # Clean up station data to ensure Streamlit/Arrow compatibility
    # Convert any pandas Timestamps or complex types to simple Python types
    cleaned_stations = {}
    for param, station_list in stations.items():
        cleaned_list = []
        for station in station_list:
            cleaned_station = {}
            for key, value in station.items():
                # Convert pandas Timestamps to strings for Arrow compatibility
                if isinstance(value, pd.Timestamp):
                    cleaned_station[key] = value.isoformat()
                elif isinstance(value, (pd.DataFrame, pd.Series)):
                    # Convert DataFrames/Series to dict/list
                    cleaned_station[key] = value.to_dict() if hasattr(value, 'to_dict') else str(value)
                else:
                    cleaned_station[key] = value
            cleaned_list.append(cleaned_station)
        cleaned_stations[param] = cleaned_list
    
    return cleaned_stations
