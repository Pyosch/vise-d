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

from src.config.constants import CACHE_CONFIG


@st.cache_resource(ttl=CACHE_CONFIG['ENVIRONMENT_TTL'])
def get_cached_environment(
    start: str,
    end: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
):
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
    """
    from vpplib.environment import Environment
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
