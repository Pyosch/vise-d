"""UI components for technology configuration forms.

Provides Streamlit-based parameter input forms for energy system technologies.
All UI text is in German for end users.

Author: Pyosch
AI Assistance: Claude Code (Claude Opus 4.8)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["Claude Code (Claude Opus 4.8)"]

from src.ui.components.bev import battery_electric_vehicle_settings
from src.ui.components.electrical_storage import electrical_storage
from src.ui.components.heat_pump import heatpump_settings
from src.ui.components.photovoltaics import pv_settings
from src.ui.components.wind_energy import wind

__all__ = [
    "battery_electric_vehicle_settings",
    "electrical_storage",
    "heatpump_settings",
    "pv_settings",
    "wind",
]
