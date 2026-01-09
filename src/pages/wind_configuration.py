"""Wind turbine configuration page for VISE-D dashboard.

This page provides configuration and simulation for wind turbines.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import streamlit as st
import matplotlib.pyplot as plt
from vpplib.wind_power import WindPower
from vpplib.environment import Environment
from src.ui.components import wind


def wind_configuration(key_suffix="wind1"):
    """Configure and simulate wind turbine power generation.
    
    This function sets up wind turbine configuration including hub height,
    rotor diameter, turbine type, and various modeling parameters.
    Simulates wind power generation using vpplib and DWD weather data.
    
    Args:
        key_suffix: Suffix for form keys to ensure uniqueness.
    
    Returns:
        None: Updates session state and displays simulation results.
    """
    wind(form_key_suffix=key_suffix)
    
    with st.form(key="wind_simulation_form"):
        # Wind simulation button
        wind_simulation_button = st.form_submit_button("Simulate Wind Turbine")
           
        if wind_simulation_button:
            latitude = 51.200001
            longitude = 6.433333
            env = Environment(start="2015-01-01 00:00:00", end="2015-12-31 23:45:00")
            env.get_dwd_wind_data(lat=latitude, lon=longitude)
            
            # Initialize Wind Turbine with form inputs
            st.session_state["wind_turbine"] = WindPower(
                identifier=None,
                unit="kW",
                environment=env,
                hub_height=st.session_state["wind_settings"]["Hub Height"],
                rotor_diameter=st.session_state["wind_settings"]["Rotor Diameter"],
                data_source="oedb",
                wind_speed_model=st.session_state["wind_settings"]["Wind Speed Model"],
                density_model=st.session_state["wind_settings"]["Density Model"],
                temperature_model=st.session_state["wind_settings"]["Temperature Model"],
                power_output_model=st.session_state["wind_settings"]["power_output_model"],
                density_correction=st.session_state["wind_settings"]["Density Correction"],
                obstacle_height=st.session_state["wind_settings"]["Obstacle Height"],
                hellman_exp=st.session_state["wind_settings"]["hellman_exp"],
                fetch_curve="power_curve",
                turbine_type=st.session_state["wind_settings"]["Turbine Type"]
            )
        
            st.success("Wind settings updated successfully!")
            
            st.session_state["wind_turbine"].prepare_time_series()
            st.write("**Time Series Data (First 5 Rows):**")
            st.dataframe(st.session_state["wind_turbine"].timeseries.head(5))

            # Create a Matplotlib figure
            fig, ax = plt.subplots(figsize=(16, 9))
            st.session_state["wind_turbine"].timeseries.plot(ax=ax)  # Plot the timeseries on the provided axes
            ax.set_title("Wind Time Series")
            ax.set_xlabel("Time")
            ax.set_ylabel("Month")
            plt.tight_layout()

            # Display the plot in Streamlit
            st.pyplot(fig)
