"""
Solar energy generation simulation page.

Simulates solar energy generation using MaStR data and vpplib models.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import streamlit as st
import matplotlib.pyplot as plt
from vpplib.environment import Environment
from src.data_layer.cache import get_cached_unique_locations, get_cached_mastr_data
from src.mastr.simulation import (
    pick_pvsystem_mastr,
    prepare_pv_time_series_mastr,
    aggregate_pv_time_series,
    revise_power_values
)
from src.config import MASTR_DB_PATH


def energy_generation_solar() -> None:
    """Simulate and visualize solar energy generation from MaStR installations."""
    st.title("Energy Generation from Solar Installations")
    
    # Fetch unique locations for dropdown with caching
    unique_locations = get_cached_unique_locations("solar", str(MASTR_DB_PATH))

    # Dropdown for location selection
    location = st.selectbox("Select city", options=unique_locations, index=unique_locations.index("Essen") if "Essen" in unique_locations else 0)
    if location:
        if st.button("Simulate Energy Generation"):
            with st.spinner("Preparing and simulating PV systems..."):
                try:
                    start = "2015-07-07 00:00:00"
                    end = "2015-07-07 23:45:00"
                    gdf_solar, city_district = get_cached_mastr_data(location, "solar", str(MASTR_DB_PATH))
                    gdf_solar = revise_power_values(gdf_solar)
                    ref_env = Environment(start=start, end=end)
                    ref_env.get_dwd_pv_data(lat=city_district.lat, 
                        lon=city_district.lon)
                    pv_system_mastr = pick_pvsystem_mastr(gdf_solar.head(10), ref_env)
                    prepare_pv_time_series_mastr(pv_system_mastr)
                    pv_systems_aggregated = aggregate_pv_time_series(pv_system_mastr)
                    # Plotting code
                    fig, ax = plt.subplots(figsize=(10, 6))
                    for name, pv_system in pv_systems_aggregated.items():
                        if hasattr(pv_system, 'plot'):
                            pv_system.plot(ax=ax, label=name)
                        else:
                            # Fallback for non-plottable objects (e.g., if pv_system is a string or list)
                            st.warning(f"System {name} is not directly plottable ({type(pv_system)}), attempting manual plotting")
                            try:
                                # Assume pv_system is a list or array-like (e.g., time series data)
                                ax.plot(pv_system, label=name)
                            except Exception as plot_error:
                                st.error(f"Failed to plot {name}: {plot_error}")
                    ax.set_title(f"Solar Energy Generation in {location} ({start} to {end})")
                    ax.set_xlabel("Time")
                    ax.set_ylabel("Power (kW)")
                    ax.legend()
                    ax.grid(True)
                    st.pyplot(fig)
                    plt.close(fig) 

                except Exception as e:
                    st.error(f"Simulation failed: {e}")
