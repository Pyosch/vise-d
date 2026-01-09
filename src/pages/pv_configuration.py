"""Photovoltaic (PV) configuration page for VISE-D dashboard.

This page provides configuration and simulation for PV systems.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import streamlit as st
import matplotlib.pyplot as plt
from vpplib.photovoltaic import Photovoltaic
from vpplib.environment import Environment
from src.ui.components import pv_settings


def pv_configuration():
    """Configure and simulate photovoltaic systems.
    
    This function sets up PV system configuration including module selection,
    inverter selection, tilt angle, azimuth, and string configuration.
    Simulates PV generation using vpplib and DWD weather data.
    
    Returns:
        None: Updates session state and displays simulation results.
    """
    pv_settings(form_key_suffix="pv1")
           
    with st.form(key="pv_simulation_form"):
        # PV simulation button
        pv_simulation_button = st.form_submit_button("Simulate PV")
           
        if pv_simulation_button:
            latitude = 51.4
            longitude = 6.97
            identifier = "Cologne"
            env = Environment(
                start="2015-01-01 00:00:00", 
                end="2015-12-31 23:45:00", 
                use_timezone_aware_time_index=True, 
                surpress_output_globally=False
            )
            env.get_dwd_pv_data(lat=latitude, lon=longitude)    
            
            # Initialize PV with form inputs
            st.session_state["pv"] = Photovoltaic(
                identifier="Cologne",
                unit="kW",
                latitude=51.4,
                longitude=6.97,
                environment=env,
                module_lib=st.session_state["pv_settings"]["PV Module Library"],
                module=st.session_state["pv_settings"]["PV Module"],
                inverter_lib=st.session_state["pv_settings"]["PV Inverter Library"],
                inverter=st.session_state["pv_settings"]["PV Inverter"],
                surface_tilt=st.session_state["pv_settings"]["PV Surface Tilt"],
                surface_azimuth=st.session_state["pv_settings"]["PV Surface Azimuth"],
                modules_per_string=st.session_state["pv_settings"]["PV Modules per String"],
                strings_per_inverter=st.session_state["pv_settings"]["PV Strings per Inverter"],
                temp_lib='sapm',
                temp_model='open_rack_glass_glass'
            )
        
            st.success("PV settings updated successfully!")
            
            st.session_state["pv"].prepare_time_series()
            st.write("**Time Series Data (First 5 Rows):**")
            st.dataframe(st.session_state["pv"].timeseries.head(5))  # Display the timeseries data for debugging

            # Create a Matplotlib figure
            fig, ax = plt.subplots(figsize=(16, 9))
            st.session_state["pv"].timeseries.plot(ax=ax)  # Plot the timeseries on the provided axes
            ax.set_title("PV Time Series")
            ax.set_xlabel("Time")
            ax.set_ylabel("Month")
            plt.tight_layout()

            # Display the plot in Streamlit
            st.pyplot(fig)
