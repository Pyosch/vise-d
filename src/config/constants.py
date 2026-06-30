"""Application constants and configuration settings for VISE-D.

Contains cache TTLs, API settings, and other application-wide constants.

Author: Pyosch
AI Assistance: Claude Code (Claude Opus 4.8)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["Claude Code (Claude Opus 4.8)"]

from dataclasses import dataclass
from typing import Final


# Cache time-to-live settings (in seconds)
@dataclass(frozen=True)
class CacheConfig:
    """Cache configuration with TTL values for different data types."""
    
    ENVIRONMENT_TTL: int = 3600  # 1 hour for vpplib Environment objects
    MASTR_DATA_TTL: int = 1800  # 30 minutes for MaStR database queries
    WEATHER_DATA_TTL: int = 3600  # 1 hour for weather data
    NETWORK_ANALYSIS_TTL: int = 900  # 15 minutes for network calculations


# Default cache configuration instance
CACHE: Final[CacheConfig] = CacheConfig()

# Legacy dict used by data_layer modules — keys must match the strings used in
# cache.py, displays.py, and environment.py.
CACHE_CONFIG: Final[dict] = {
    'DATA_LOAD_TTL': 3600,
    'DATABASE_TTL': 1800,
    'VISUALIZATION_TTL': 600,
    'ENVIRONMENT_TTL': 3600,
}


# DWD (Deutscher Wetterdienst) weather service settings
@dataclass(frozen=True)
class DWDConfig:
    """Configuration for DWD weather data integration."""
    
    DEFAULT_STATION: str = "10513"  # Default weather station ID (Düsseldorf)
    REQUEST_TIMEOUT: int = 30  # Timeout for DWD API requests (seconds)
    MAX_RETRIES: int = 3  # Maximum number of retry attempts
    CACHE_DIR: str = "cache/dwd_cache"  # Cache directory for DWD data
    CACHE_EXPIRY_HOURS: int = 24  # Cache expiry time in hours
    DEFAULT_RESOLUTION: str = "10_minutes"  # Default data resolution
    TIMEZONE: str = "Europe/Berlin"  # Timezone for weather data
    RANKING_STRATEGY: str = "quality_weighted"  # Station ranking strategy
    MAX_STATION_DISTANCE_KM: float = 50.0  # Maximum distance for station search
    N_STATIONS: int = 5  # Number of stations to search for


DWD: Final[DWDConfig] = DWDConfig()


# Network analysis settings
@dataclass(frozen=True)
class NetworkConfig:
    """Configuration for pandapower network analysis."""
    
    MAX_ITERATION: int = 10  # Maximum power flow iterations
    TOLERANCE: float = 1e-6  # Convergence tolerance for power flow
    VOLTAGE_LIMITS_PU: tuple[float, float] = (0.9, 1.1)  # Min/max voltage (per unit)


NETWORK: Final[NetworkConfig] = NetworkConfig()


# UI settings
@dataclass(frozen=True)
class UIConfig:
    """Configuration for Streamlit user interface."""
    
    PAGE_ICON: str = "⚡"  # Browser tab icon
    LAYOUT: str = "wide"  # Streamlit layout mode
    INITIAL_SIDEBAR_STATE: str = "expanded"  # Sidebar initial state


UI: Final[UIConfig] = UIConfig()


# Validation limits for technology parameters
@dataclass(frozen=True)
class ValidationLimits:
    """Validation limits for technology parameter inputs."""
    
    # Photovoltaic limits
    PV_POWER_MIN_KW: float = 0.1
    PV_POWER_MAX_KW: float = 10000.0
    PV_EFFICIENCY_MIN: float = 0.05
    PV_EFFICIENCY_MAX: float = 0.30
    
    # Wind turbine limits
    WIND_POWER_MIN_KW: float = 1.0
    WIND_POWER_MAX_KW: float = 10000.0
    WIND_HUB_HEIGHT_MIN_M: float = 10.0
    WIND_HUB_HEIGHT_MAX_M: float = 200.0
    
    # Battery storage limits
    STORAGE_CAPACITY_MIN_KWH: float = 1.0
    STORAGE_CAPACITY_MAX_KWH: float = 100000.0
    STORAGE_POWER_MIN_KW: float = 1.0
    STORAGE_POWER_MAX_KW: float = 50000.0
    
    # Heat pump limits
    HP_THERMAL_POWER_MIN_KW: float = 1.0
    HP_THERMAL_POWER_MAX_KW: float = 100.0
    HP_COP_MIN: float = 2.0
    HP_COP_MAX: float = 6.0
    
    # BEV limits
    BEV_BATTERY_MIN_KWH: float = 10.0
    BEV_BATTERY_MAX_KWH: float = 200.0
    BEV_CHARGE_POWER_MIN_KW: float = 3.7
    BEV_CHARGE_POWER_MAX_KW: float = 350.0


LIMITS: Final[ValidationLimits] = ValidationLimits()
