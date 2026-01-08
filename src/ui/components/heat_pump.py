"""Heat Pump configuration UI component.

Streamlit form for configuring heat pump parameters including thermal power,
COP (Coefficient of Performance), and temperature settings.

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
from vpplib.environment import Environment

def heatpump_settings(form_key_suffix=""):
    # Set page configuration
    # Title
    st.title("Heat Pump Configuration")
    if heatpump_settings not in st.session_state:
        st.session_state.heatpump_settings = {
            "identifier": "hp1",
        #    "Environment": "None",
            "user_profile": "None",
            "heat_pump_type": "Air",
            "Heat System Temperature": 55.0,  # °C - typical floor heating
            "el_power": 8.0,  # kW - electrical power
            "th_power": 24.0,  # kW - thermal power (COP ~3)
            "Ramp Up Time" : datetime.time(0,30),  # 30 min
            "Ramp Down Time": datetime.time(0,30),  # 30 min
            "Minimum Run Time": datetime.time(1,0),  # 1 hour
            "Minimum Stop Time": datetime.time(0,30)  # 30 min
            
            
        }
    # Technology parameters in main content area
    with st.container():
        # Input Section
            st.header("Enter Heat Pump Settings")

            identifier = st.selectbox(
            "Select Identifier",
            options=["None", "hp1", "hp2"],
            index=0 if st.session_state.heatpump_settings["identifier"] == "None" else 1 if st.session_state.heatpump_settings["identifier"] == "hp1" else 2,
            key="identifier"
            )
            
            # Environment = st.selectbox(
            # "Select Environment",
            # options=["None", "Environment 1", "Environment 2"],
            # index=0 if st.session_state.heatpump_settings["Environment"] == "None" else 1 if st.session_state.heatpump_settings["Environment"] == "Environment 1" else 2,
            # key="Environment"
            # )
            
            user_profile = st.selectbox(
                "user Profile",
                options = ["None","Profile1","Profile2"],
                index = 0 if st.session_state.heatpump_settings["user_profile"]=="None" else 1 if st.session_state.heatpump_settings["user_profile"]=="Profile1" else 2,
                key = "user_profile"
            ) 

        # Dropdown for Heat Pump Type
            heat_pump_type = st.selectbox(
            "Type of Heat Pump",
            options=["Air", "Ground"],
            index=0,
                placeholder="Select heat pump type"
        )

        # Number input for Heat System Temperature
            system_temperature = st.number_input(
            "Heat System Temperature (°C)",
            min_value=-50.0,
            max_value=100.0,
            value=0.0,
            step=0.1,
            placeholder="e.g. 20.5"
        )

        # Number input for Electrical Power
            el_power = st.number_input(
            "el_power (kW)",
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=0.1,
            placeholder="e.g. 5"
        )
            
            th_power = st.number_input(
                "th_power (KW)",
                min_value = 0.0,
                max_value = 100.0,
                value = 0.0,
                step = 0.1,
                placeholder = "e.g. 5"
            )
            
            
            ramp_up_time = st.time_input(
                "Enter ramp up time (HH:MM)",
                    value=datetime.time(0,0)
                    
                )
                
            ramp_down_time = st.time_input(
                "Enter ramp down time (HH:MM)",
                    value=datetime.time(0,0)
                    
                )
            
            min_run_time = st.time_input(
                "Enter run time (HH:MM)",
                    value=datetime.time(0,0)
                )
            
            min_stop_time = st.time_input(
                "Enter stop time (HH:MM)",
                    value=datetime.time(0,0)
                    
                )
            
            
        

    # Submit button
            if st.button("Submit Settings",key="submit_heatpump_settings"):
            # Store settings in session state
                st.session_state.heatpump_settings = {
                    "identifier": identifier,
                    "heat_pump_type": heat_pump_type,
                    "Heat System Temperature": system_temperature,
                    "el_power": el_power,
            #        "Environment": Environment,
                    "user_profile": user_profile,
                    "th_power":th_power,
                    "Ramp Up Time" : ramp_up_time,
                    "Ramp Down Time":ramp_down_time,
                    "Minimum Run Time": min_run_time,
                    "Minimum Stop Time": min_stop_time  
                
            }

    # Display stored settings if available
    if "heatpump_settings" in st.session_state:
        st.header("Current Heat Pump Settings")
        # Create a DataFrame for the table
        settings_df = pd.DataFrame([
            {"Setting": key, "Value": value}
            for key, value in st.session_state.heatpump_settings.items()
        ])
        
        # Style the DataFrame for better presentation
        st.dataframe(
            settings_df,
            use_container_width=True,
            column_config={
                "Setting": st.column_config.TextColumn("Setting", width="medium"),
                "Value": st.column_config.TextColumn("Value", width="large")
            }
        )
