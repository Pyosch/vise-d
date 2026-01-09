"""OpenSTEF forecasting page for VISE-D dashboard.

This page provides energy forecasting using the OpenSTEF framework.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import streamlit as st
from src.data_layer import get_cached_unique_locations
from src.config import MASTR_DB_PATH


def openstef_forecasting():
    """Display OpenSTEF energy forecasting interface.
    
    Provides short-term energy forecasting functionality using OpenSTEF
    integrated with MaStR location data.
    """
    st.title("Energy Forecasting with OpenSTEF")
    
    # Fetch unique locations for dropdown with caching
    mastr_db_path = str(MASTR_DB_PATH)
    unique_locations = get_cached_unique_locations("solar", mastr_db_path)

    # Dropdown for location selection
    location = st.selectbox(
        "Select city", 
        options=unique_locations, 
        index=unique_locations.index("Essen") if "Essen" in unique_locations else 0
    )
    
    # Placeholder for future OpenSTEF integration
    st.info("📊 OpenSTEF forecasting functionality coming soon...")
    st.write(f"Selected location: **{location}**")
    
    return 0
