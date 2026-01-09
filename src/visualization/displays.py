"""Display components for visualization results.

Provides formatted display functions for simulation results.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import streamlit as st
from src.data_layer.cache import CACHE_CONFIG


@st.cache_data(ttl=CACHE_CONFIG['VISUALIZATION_TTL'])
def create_wind_simulation_display(results: dict) -> None:
    """Display wind simulation results in a formatted way.
    
    Args:
        results: Dictionary containing simulation results with keys:
            - kreiszentrum: Center coordinates (lon, lat)
            - radius: Circle radius in meters
            - num_turbines: Number of wind turbines
            - annual_energy: Total annual energy generation
            - full_load_hours: Full load hours per year
            - timeline_fig: Plotly figure showing timeline
    """
    st.subheader("Kreisinformationen")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"Kreiszentrum (Längengrad, Breitengrad): {results['kreiszentrum']}")
    with col2:
        st.write(f"Kreisradius: {results['radius']}")

    st.subheader("Simulationsergebnisse")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Anzahl von Windturbinen", results['num_turbines'])
    with col2:
        st.metric("Gesamtenergierzeugung pro Jahr", results['annual_energy'])
    with col3:
        st.metric("Volllastunden", results['full_load_hours'])

    st.subheader("Stromproduktion der Windturbinen im Jahresverlauf (MW)")
    st.plotly_chart(results['timeline_fig'], use_container_width=True)
