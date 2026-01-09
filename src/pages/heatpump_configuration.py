"""Heat pump configuration page for VISE-D dashboard.

This page provides configuration and simulation for heat pumps.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import streamlit as st
import matplotlib.pyplot as plt
from vpplib.heat_pump import HeatPump
from vpplib.user_profile import UserProfile
from vpplib.environment import Environment
from src.ui.components import heatpump_settings


def heatpump_configuration():
    """Configure and simulate heat pump operation.
    
    This function sets up heat pump configuration including type, electrical power,
    thermal power, system temperature, and operational parameters.
    Simulates heat pump operation using vpplib with thermal demand profiles.
    
    Returns:
        None: Updates session state and displays simulation results.
    """
    heatpump_settings(form_key_suffix="hp1")
    
    with st.form(key="heatpump_simulation_form"):
        # Heat Pump simulation button
        heatpump_simulation_button = st.form_submit_button("Simulate Heat Pump")
           
        if heatpump_simulation_button:
            # Values for environment
            start = "2015-01-01 00:00:00"
            end = "2015-12-31 23:45:00"
            year = "2015"
            time_freq = "15 min"
            timebase = 15
            latitude = 50.941357
            longitude = 6.958307

            # Values for user_profile
            yearly_thermal_energy_demand = 12500
            building_type = "DE_HEF33"
            t_0 = 40
            
            env = Environment(
                timebase=timebase, 
                start=start, 
                end=end, 
                year=year, 
                time_freq=time_freq, 
                surpress_output_globally=False
            )
            
            env.get_dwd_mean_temp_hours(lat=latitude, lon=longitude)
            env.get_dwd_mean_temp_days(lat=latitude, lon=longitude)
            
            user_profile = UserProfile(
                identifier=None,
                latitude=None,
                longitude=None,
                thermal_energy_demand_yearly=yearly_thermal_energy_demand,
                mean_temp_days=env.mean_temp_days,
                mean_temp_hours=env.mean_temp_hours,
                mean_temp_quarter_hours=env.mean_temp_hours.resample("15 Min").interpolate(),
                building_type=building_type,
                comfort_factor=None,
                t_0=t_0,
            )
            
            user_profile.get_thermal_energy_demand()
            
            # Initialize Heat Pump with form inputs
            st.session_state["hp"] = HeatPump(
                identifier=st.session_state["heatpump_settings"]["identifier"],
                unit="kW",
                thermal_energy_demand=user_profile.thermal_energy_demand,
                environment=env,
                heat_pump_type=st.session_state["heatpump_settings"]["heat_pump_type"],
                heat_sys_temp=st.session_state["heatpump_settings"]["Heat System Temperature"],
                el_power=st.session_state["heatpump_settings"]["el_power"],
                th_power=st.session_state["heatpump_settings"]["th_power"],
                ramp_up_time=st.session_state["heatpump_settings"]["Ramp Up Time"],
                ramp_down_time=st.session_state["heatpump_settings"]["Ramp Down Time"],
                min_runtime=st.session_state["heatpump_settings"]["Minimum Run Time"],
                min_stop_time=st.session_state["heatpump_settings"]["Minimum Stop Time"]
            )
        
            st.success("Heat Pump settings updated successfully!")
            
            print("get_cop:")
            st.session_state["hp"].get_cop()
            st.session_state["hp"].cop.plot(figsize=(16, 9))
            plt.show() 
            
            st.session_state["hp"].prepare_time_series()
            st.write("**Time Series Data (First 5 Rows):**")
            st.dataframe(st.session_state["hp"].timeseries)  # Display the timeseries data for debugging

            # Create a Matplotlib figure
            fig, ax = plt.subplots(figsize=(16, 9))
            st.session_state["hp"].timeseries.plot(ax=ax)  # Plot the timeseries on the provided axes
            ax.set_title("Heat Pump Time Series")
            ax.set_xlabel("Time")
            ax.set_ylabel("Value (kW)")
            plt.tight_layout()

            # Display the plot in Streamlit
            st.pyplot(fig)
