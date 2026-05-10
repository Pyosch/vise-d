"""Battery Electric Vehicle (BEV) configuration UI component.

Streamlit form for configuring BEV parameters including battery capacity,
charging power, efficiency, and user profiles.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import pandas as pd
import plotly.express as px

import time

import datetime
import streamlit as st
from st_files_connection import FilesConnection
import os

from src.visualization import fig_5, fig_7, fig_8, fig_9, fig_5_plotly
from src.network import pp_networks
import matplotlib.pyplot as plt


from vpplib.battery_electric_vehicle import BatteryElectricVehicle
from vpplib.environment import Environment


DEFAULT_BEV_SETTINGS = {
    "max_battery_capacity": 75.0,
    "min_battery_capacity": 15.0,
    "battery_usage": 50.0,
    "charging_power": 11.0,
    "charging_efficiency": 0.95,
    "load_degradation_begin": 0.8,
    "user_profile": "None",
    "selected_environment": "None",
    "start_time": datetime.time(18, 0, 0),
    "end_time": datetime.time(7, 0, 0),
    "timebase": 15,
}


def _ensure_bev_settings():
    """Guarantee required BEV settings exist in Streamlit session state."""
    if "bev_settings" not in st.session_state or not isinstance(st.session_state["bev_settings"], dict):
        st.session_state["bev_settings"] = DEFAULT_BEV_SETTINGS.copy()
        return

    for key, value in DEFAULT_BEV_SETTINGS.items():
        st.session_state["bev_settings"].setdefault(key, value)


def battery_electric_vehicle_settings(form_key_suffix=""):
    _ensure_bev_settings()
    st.title("Battery Electric Vehicle (BEV) Settings")
    # Form layout
    # Technology parameters in main content area
    with st.container():
        with st.form(key=f"bev_settings_form_{form_key_suffix}"):
            # Max Battery Capacity
            st.markdown("**Max. Battery Capacity**")
            max_battery_capacity = st.number_input(
                "Enter max battery capacity (kWh)",
                min_value=0.0,
                value=float(st.session_state["bev_settings"]["max_battery_capacity"]),
                placeholder="e.g. 100 kWh",
                key="max_battery_capacity"
            )

            # Min Battery Capacity
            st.markdown("**Min. Battery Capacity**")
            min_battery_capacity = st.number_input(
                "Enter min battery capacity (kWh)",
                min_value=0.0,
                value=float(st.session_state["bev_settings"]["min_battery_capacity"]),
                placeholder="e.g. 15 kWh",
                key="min_battery_capacity"
            )

            # Battery Usage
            st.markdown("**Battery Usage**")
            battery_usage = st.number_input(
                "Enter battery usage",
                min_value=0.0,
                value=float(st.session_state["bev_settings"]["battery_usage"]),
                placeholder="e.g. ???",
                key="battery_usage"
            )
            st.markdown("*Note: Battery usage definition may need clarification.*")

            # Charging Power
            st.markdown("**Charging Power**")
            charging_power = st.number_input(
                "Enter charging power (kW)",
                min_value=0.0,
                value=float(st.session_state["bev_settings"]["charging_power"]),
                placeholder="e.g. 11 kW",
                key="charging_power"
            )

            # Charging Efficiency
            st.markdown("**Charging Efficiency**")
            charging_efficiency = st.number_input(
                "Enter charging efficiency (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state["bev_settings"]["charging_efficiency"] * 100),
                placeholder="e.g. 90%",
                key="charging_efficiency"
            )
            
            st.markdown("**load_degradation_begin**")
            load_degradation_begin = st.number_input(
            "Enter load degradation begin",
                min_value=0.0,
                value=float(st.session_state["bev_settings"]["load_degradation_begin"]),
                placeholder="e.g. ???",
                key="load_degradation_begin"
            )
            
            st.markdown("**user_profile**")
            user_profile = st.selectbox(
                "Select user profile",
                options=["None", "Profile 1", "Profile 2"],
                index=0 if st.session_state["bev_settings"]["user_profile"] == "None" else 1 if st.session_state["bev_settings"]["user_profile"] == "Profile 1" else 2,
                key="user_profile"
            )
            
        #    st.markdown("**environment**")
        #    selected_environment = st.selectbox(
        #        "Select environment",
        #        options=["None", "Environment 1", "Environment 2"],
        #        index=0 if st.session_state.bev_settings["selected_environment"] == "None" else 1 if st.session_state.bev_settings["selected_environment"] == "Environment 1" else 2,
        #        key="environment"
        #    )
            
            st.markdown("**Start Time**")
            start_time = st.time_input(
                "Enter Start Time HH:MM:SS",
                value=st.session_state["bev_settings"]["start_time"],
                help="When the vehicle is plugged in and charging can begin (e.g., arriving home)"
                
            )
            
            st.markdown("**End Time**")
            end_time = st.time_input(
                "Enter End Time HH:MM:SS",
                value=st.session_state["bev_settings"]["end_time"],
                help="When the vehicle must be fully charged (e.g., leaving for work)"
                
            )
            
            st.markdown("**Timebase**")
            timebase = st.number_input(
                "Enter Timebase (minutes)",
                min_value=1,
                max_value=60,
                value=15,
                step=1,
                key="timebase"
            )
            
            

            # Submit button
            submit_button = st.form_submit_button("Submit Settings")

        # Handle form submission
        if submit_button:
            
        # Update session state with new settings
            st.session_state["bev_settings"] = {
                "max_battery_capacity": max_battery_capacity,
                "min_battery_capacity": min_battery_capacity,
                "battery_usage": battery_usage,
                "charging_power": charging_power,
                "charging_efficiency": charging_efficiency / 100,
                "load_degradation_begin":load_degradation_begin,
                "user_profile": user_profile,
                "selected_environment": st.session_state["bev_settings"].get("selected_environment", "None"),
                #   "environment": selected_environment,
                "start_time": start_time,
                "end_time": end_time,
                "timebase": timebase
            }
           
            # start = "2015-06-01 00:00:00"
            # end = "2015-06-01 23:45:00"
            # timestamp_int = 48
            # timestamp_str = "2015-06-01 12:00:00"
            # env = Environment(start=start, end=end, timebase=timebase)
            
            # # Initialize BEV with form inputs
            # bev = BatteryElectricVehicle(
            #     unit="kW",
            #     identifier="bev_1",
            #     environment=env,
            #     battery_max=max_battery_capacity,
            #     battery_min=min_battery_capacity,
            #     battery_usage=battery_usage,
            #     charging_power=charging_power,
            #     load_degradation_begin=load_degradation_begin,
            #     charge_efficiency=charging_efficiency / 100
            # )
           
            st.success("BEV settings updated successfully!")
            # Display the updated settings for user confirmation
    #    st.json(st.session_state.bev_settings)

        # Optional: Display current settings
    #    st.markdown("### Current BEV Settings")
    #    st.json(st.session_state.bev_settings)
    import pandas as pd

 # Create DataFrame for table
    data = {
    "Metric": ["Max Battery Capacity", "Min Battery Capacity", "Battery Usage", "Charging Power", "Charging Efficiency", "Load Degradation Begin", "User Profile","start_time","end_time","timebase"],
    "Value": [max_battery_capacity, min_battery_capacity, battery_usage, charging_power, charging_efficiency, load_degradation_begin, user_profile,start_time,end_time,timebase],
    "Unit": ["kWh", "kWh", "kWh", "kW", "%", "kWh", "","HH:MM:SS", "HH:MM:SS", "minutes"]
}
    df = pd.DataFrame(data)

    # Display table
    st.subheader("Current BEV Settings")
    st.dataframe(
    df.style.format(
        {
            "Value": lambda x: "{:.1f}".format(x) if isinstance(x, (int, float)) else x
        }
    ).set_properties(**{
        'text-align': 'left',
        'font-size': '14px',
        'padding': '10px',
        'border': '1px solid #ddd',
        'background-color': '#f9f9f9'
    }).set_table_styles([
        {'selector': 'th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('font-weight', 'bold'), ('text-align', 'left'), ('padding', '10px'), ('border', '1px solid #ddd')]},
        {'selector': 'td', 'props': [('border', '1px solid #ddd')]}
    ]),
    use_container_width=True,
    hide_index=True
)

