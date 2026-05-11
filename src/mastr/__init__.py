"""MaStR (Marktstammdatenregister) integration package.

Provides data fetching, preprocessing, and simulation utilities for German energy
system data from the Marktstammdatenregister.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

from src.mastr.preprocessing import (
    add_centroids,
    df_to_gdf,
    download_mastr_data,
    fetch_data,
    fetch_grid_connections,
    fetch_grids,
    fetch_solar,
    fetch_storage,
    fetch_wind,
    get_unique_solar_locations,
    get_unique_storage_locations,
    get_unique_wind_locations,
    prepare_grid_connections_data,
    prepare_solar_data,
    prepare_storage_data,
    prepare_wind_data,
    read_storage_units,
)
from src.mastr.simulation import (
    aggregate_pv_time_series,
    aggregate_wind_time_series,
    build_pvsystem_params_from_mastr,
    build_pvsystems_from_params,
    init_windturbines_mastr,
    load_or_build_pv_params,
    pick_pvsystem_mastr,
    prepare_pv_time_series_mastr,
    prepare_wind_time_series_mastr,
    revise_power_values,
    SimplePVSystem,
    wind_turbine_matching,
)

__all__ = [
    # Preprocessing functions
    "add_centroids",
    "df_to_gdf",
    "download_mastr_data",
    "fetch_data",
    "fetch_grid_connections",
    "fetch_grids",
    "fetch_solar",
    "fetch_storage",
    "fetch_wind",
    "get_unique_solar_locations",
    "get_unique_storage_locations",
    "get_unique_wind_locations",
    "prepare_grid_connections_data",
    "prepare_solar_data",
    "prepare_storage_data",
    "prepare_wind_data",
    "read_storage_units",
    # Simulation functions
    "aggregate_pv_time_series",
    "aggregate_wind_time_series",
    "build_pvsystem_params_from_mastr",
    "build_pvsystems_from_params",
    "init_windturbines_mastr",
    "load_or_build_pv_params",
    "pick_pvsystem_mastr",
    "prepare_pv_time_series_mastr",
    "prepare_wind_time_series_mastr",
    "revise_power_values",
    "SimplePVSystem",
    "wind_turbine_matching",
]
