"""Solar and wind energy planning modules.

Provides tools for site selection, obstacle detection, and energy simulation
for photovoltaic and wind power installations.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

# Solar planning functions
from src.planning.solar import (
    fetch_obstacles_solar,
    packing_solar,
    simulate_solarfarm_output,
)

# Wind planning functions
from src.planning.wind import (
    fetch_obstacles_wind,
    packing_wind,
    # simulate_windfarm_output,  # TODO: Function not yet implemented
    get_weather_for_windpowerlib,
)

# Geographic utilities
from src.planning.geo_utils import (
    get_local_crs,
    find_circle_markers,
)

__all__ = [
    # Solar
    "fetch_obstacles_solar",
    "packing_solar",
    "simulate_solarfarm_output",
    # Wind
    "fetch_obstacles_wind",
    "packing_wind",
    # "simulate_windfarm_output",  # TODO: Not yet implemented
    "get_weather_for_windpowerlib",
    # Geographic utilities
    "get_local_crs",
    "find_circle_markers",
]
