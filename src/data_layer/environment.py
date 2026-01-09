"""vpplib Environment caching for VISE-D dashboard.

This module provides cached Environment object creation to avoid
repeated expensive weather data fetching operations.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

from typing import Optional
import streamlit as st
from vpplib.environment import Environment

from src.data_layer.cache import CACHE_CONFIG


@st.cache_resource(ttl=CACHE_CONFIG['ENVIRONMENT_TTL'])
def get_cached_environment(
    start: str, 
    end: str, 
    lat: Optional[float] = None, 
    lon: Optional[float] = None
) -> Optional[Environment]:
    """Cache expensive Environment operations.
    
    Creates and caches vpplib Environment objects which contain weather data
    and are used across multiple technology simulations.
    
    Args:
        start: Start date string (format: 'YYYY-MM-DD HH:MM:SS').
        end: End date string (format: 'YYYY-MM-DD HH:MM:SS').
        lat: Optional latitude for PV data fetching.
        lon: Optional longitude for PV data fetching.
    
    Returns:
        Environment object with weather data. Returns None on error.
    
    Note:
        Cached for 1 hour as Environment objects are large and expensive to create.
        Uses @st.cache_resource instead of @st.cache_data because Environment
        objects may not be pickleable.
    
    Example:
        >>> env = get_cached_environment(
        ...     start='2024-01-01 00:00:00',
        ...     end='2024-12-31 23:00:00',
        ...     lat=50.776351,
        ...     lon=6.083862
        ... )
        >>> # Use env for PV, Wind, BEV simulations
    """
    try:
        env = Environment(start=start, end=end)
        if lat is not None and lon is not None:
            try:
                env.get_dwd_pv_data(lat=lat, lon=lon)
            except Exception as e:
                st.error(f"❌ Failed to fetch PV data: {str(e)}")
                return None
        return env
    except Exception as e:
        st.error(f"❌ Failed to create environment: {str(e)}")
        return None
