"""Caching utilities and data loading functions for VISE-D dashboard.

This module provides cached data loading functions to optimize performance
for expensive operations like database queries, file I/O, and visualizations.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

from typing import Optional, Tuple, List, Any
import pandas as pd
import plotly.express as px
import streamlit as st

from src.config.constants import CACHE_CONFIG


@st.cache_data(ttl=CACHE_CONFIG['DATA_LOAD_TTL'])
def load_example_data() -> pd.DataFrame:
    """Load example data with caching for performance.
    
    Returns:
        pd.DataFrame: Example data for research results visualization.
                     Returns empty DataFrame if file not found.
    
    Note:
        Cached for 1 hour as this is static data that rarely changes.
    """
    try:
        return pd.read_csv('./data/figures/example_data_10000.csv')
    except FileNotFoundError:
        st.error("❌ Example data file not found. Please check the file path.")
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_CONFIG['DATABASE_TTL'])
def get_cached_unique_locations(location_type: str, mastr_db_path: str) -> List[str]:
    """Get unique locations with caching to avoid repeated database queries.
    
    Args:
        location_type: Type of installation ('solar', 'wind', or 'storage').
        mastr_db_path: Path to MaStR database file.
    
    Returns:
        List[str]: List of unique location names (e.g., 'Aachen', 'Berlin').
                   Returns empty list on error.
    
    Note:
        Cached for 30 minutes as MaStR data updates infrequently.
    """
    from src.mastr.preprocessing import (
        get_unique_solar_locations,
        get_unique_wind_locations,
        get_unique_storage_locations,
    )
    try:
        if location_type == "solar":
            return get_unique_solar_locations(mastr_db_path=mastr_db_path)
        elif location_type == "wind":
            return get_unique_wind_locations(mastr_db_path=mastr_db_path)
        elif location_type == "storage":
            return get_unique_storage_locations(mastr_db_path=mastr_db_path)
        else:
            return []
    except Exception as e:
        st.error(f"❌ Failed to load {location_type} locations: {str(e)}")
        return []


@st.cache_data(ttl=CACHE_CONFIG['DATABASE_TTL'])
def get_cached_mastr_data(
    location: str, 
    data_type: str, 
    mastr_db_path: str
) -> Tuple[Optional[Any], Optional[Any]]:
    """Cache expensive MaStR database operations.
    
    Args:
        location: Name of location (e.g., 'Aachen').
        data_type: Type of data ('solar', 'wind', or 'storage').
        mastr_db_path: Path to MaStR database file.
    
    Returns:
        Tuple of (geodataframe, summary_data). Returns (None, None) on error.
    
    Note:
        Cached for 30 minutes as geodataframe creation is expensive.
    """
    from src.mastr.preprocessing import (
        prepare_solar_data,
        prepare_wind_data,
        prepare_storage_data,
    )
    try:
        if data_type == "solar":
            return prepare_solar_data(location=location, mastr_db_path=mastr_db_path)
        elif data_type == "wind":
            return prepare_wind_data(location=location, mastr_db_path=mastr_db_path)
        elif data_type == "storage":
            return prepare_storage_data(location=location, mastr_db_path=mastr_db_path)
        else:
            return None, None
    except Exception as e:
        st.error(f"❌ Failed to load {data_type} data for {location}: {str(e)}")
        return None, None


@st.cache_data(ttl=CACHE_CONFIG['VISUALIZATION_TTL'])
def create_cached_violin_plot(
    df: pd.DataFrame,
    ev_penetration: float,
    curtailment: str,
    selected_grid_type: str,
    selected_hp_diffusion: float,
    selected_pv_storage_diffusion: float,
    selected_wholesale_tariff: str,
    selected_grid_usage_fees: str
) -> Any:
    """Cache violin plot generation for better performance.
    
    Args:
        df: DataFrame with simulation results.
        ev_penetration: EV penetration level.
        curtailment: Curtailment strategy.
        selected_grid_type: Grid type filter.
        selected_hp_diffusion: Heat pump diffusion level.
        selected_pv_storage_diffusion: PV storage diffusion level.
        selected_wholesale_tariff: Wholesale tariff type.
        selected_grid_usage_fees: Grid usage fee type.
    
    Returns:
        Plotly figure object with violin plot.
    
    Note:
        Cached for 10 minutes as plot generation is computationally expensive.
    """
    df_selected = df[
        (df['diffusion_evs'] == ev_penetration)
        & (df['curtailment'] == curtailment)
        & (df['grid_type'] == selected_grid_type)
        & (df['diffusion_hps'] == selected_hp_diffusion)
        & (df['diffusion_pv_storage'] == selected_pv_storage_diffusion)
        & (df['tariff_wholesale'] == selected_wholesale_tariff)
        & (df['tariff_grid_usage_fee'] == selected_grid_usage_fees)
    ]

    return px.violin(df_selected, y='value', box=True, points="all")


@st.cache_data(ttl=CACHE_CONFIG['VISUALIZATION_TTL'])
def create_cached_scatter_map(
    _gdf_data: Any,
    lat_col: str,
    lon_col: str,
    hover_data: list,
    center_lat: float,
    center_lon: float,
    color: str = 'red',
    title: str = "Installation Map"
) -> Optional[Any]:
    """Cache expensive map creation operations.
    
    Args:
        _gdf_data: GeoDataFrame with installation data (underscore prefix to avoid hashing).
        lat_col: Name of latitude column.
        lon_col: Name of longitude column.
        hover_data: List of column names to show on hover.
        center_lat: Map center latitude.
        center_lon: Map center longitude.
        color: Marker color.
        title: Map title.
    
    Returns:
        Plotly figure object with scatter mapbox. Returns None on error.
    
    Note:
        Cached for 10 minutes as mapbox generation is expensive.
    """
    try:
        fig = px.scatter_mapbox(
            _gdf_data,
            lat=lat_col,
            lon=lon_col,
            size_max=45,
            color_discrete_sequence=[color],
            zoom=10,
            center={"lat": center_lat, "lon": center_lon},
            mapbox_style='open-street-map',
            hover_data=hover_data,
            title=title
        )
        return fig
    except Exception as e:
        st.error(f"❌ Failed to create map: {str(e)}")
        return None


def update_violin_plot(
    df: pd.DataFrame,
    ev_penetration: float,
    curtailment: str,
    selected_grid_type: str,
    selected_hp_diffusion: float,
    selected_pv_storage_diffusion: float,
    selected_wholesale_tariff: str,
    selected_grid_usage_fees: str
) -> Any:
    """Wrapper to use cached plotting function.
    
    This function provides a cleaner interface for creating violin plots
    by delegating to the cached implementation.
    
    Args:
        df: DataFrame with simulation results.
        ev_penetration: EV penetration level.
        curtailment: Curtailment strategy.
        selected_grid_type: Grid type filter.
        selected_hp_diffusion: Heat pump diffusion level.
        selected_pv_storage_diffusion: PV storage diffusion level.
        selected_wholesale_tariff: Wholesale tariff type.
        selected_grid_usage_fees: Grid usage fee type.
    
    Returns:
        Plotly figure object with violin plot.
    """
    return create_cached_violin_plot(
        df, ev_penetration, curtailment, selected_grid_type,
        selected_hp_diffusion, selected_pv_storage_diffusion,
        selected_wholesale_tariff, selected_grid_usage_fees
    )
