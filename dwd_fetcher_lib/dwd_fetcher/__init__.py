"""
DWD Data Fetcher
================

A Python module for fetching meteorological data from the Deutscher Wetterdienst (DWD)
Open Data portal. Provides access to observations (historical and recent) and forecasts
(MOSMIX) for solar irradiance, wind speed, temperature, and air pressure.

Main Components:
- Station search and metadata management
- Observation data fetching (historical/recent)
- MOSMIX forecast data fetching
- Data transformation for pvlib and windpowerlib compatibility
"""

__version__ = "0.1.0"
__author__ = "DWD Data Fetcher Contributors"

from .fetcher import DWDFetcher
from .config import WeightingStrategy

__all__ = ["DWDFetcher", "WeightingStrategy"]
