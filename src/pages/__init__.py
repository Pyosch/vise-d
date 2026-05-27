"""Pages module for VISE-D dashboard.

This module provides all page functions for the Streamlit navigation system.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

from src.pages.research_results import research_results
from src.pages.bev_settings import bev_settings
from src.pages.pv_configuration import pv_configuration
from src.pages.wind_configuration import wind_configuration
from src.pages.heatpump_configuration import heatpump_configuration
from src.pages.electrical_storage_configuration import electrical_storage_configuration
from src.pages.thermal_storage_settings import thermal_storage_settings
from src.pages.solar_installation_mastr import solar_installation_mastr
from src.pages.wind_installation_mastr import wind_installation_mastr
from src.pages.storage_installation_mastr import storage_installation_mastr
from src.pages.energy_generation_solar import energy_generation_solar
from src.pages.wind_energy_generation import wind_energy_generation
from src.pages.flexibility_configurator import flexibility_configurator
from src.pages.netzmodell import netzmodell
from src.pages.mv_fallstudie import mv_fallstudie

__all__ = [
    'research_results',
    'bev_settings',
    'pv_configuration',
    'wind_configuration',
    'heatpump_configuration',
    'electrical_storage_configuration',
    'thermal_storage_settings',
    'solar_installation_mastr',
    'wind_installation_mastr',
    'storage_installation_mastr',
    'energy_generation_solar',
    'wind_energy_generation',
    'flexibility_configurator',
    'netzmodell',
    'mv_fallstudie',
]
