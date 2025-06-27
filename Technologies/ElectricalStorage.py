import datetime
import streamlit as st
from st_files_connection import FilesConnection
import os

from paper_figures import fig_5, fig_7, fig_8, fig_9, fig_5_plotly
from pp_networks import pp_networks
import matplotlib.pyplot as plt
from vpplib.environment import Environment
import pandas as pd




def electrical_storage(form_key_suffix=""):
    if "electrical_storage" not in st.session_state:
        st.session_state.electrical_storage={
            "Charge Efficiency": 0,
            "Discharge Efficiency": 0,
            "Max Power" : 0,
            "Max Capacity": 0,
            "max_c":0
            
        }
    st.title("Electrical_Storage")
    
    with st.sidebar:
        st.header("Enter Electrical Storage settings")
        
        st.markdown("**Charging Efficiency**")
        charging_efficiency = st.number_input(
                "Enter charging efficiency (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.electrical_storage["Charge Efficiency"] * 100),
                placeholder="e.g. 90%",
                key="charging_efficiency"
            )
        st.markdown("**Discharging Efficiency**")
        discharging_efficiency = st.number_input(
                "Enter discharging efficiency (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.electrical_storage["Discharge Efficiency"] * 100),
                placeholder="e.g. 90%",
                key="discharging_efficiency"
            )
        
        st.markdown("**Max Power**")
        max_power = st.number_input(
                "Enter max power (kW)",
                min_value=0.0,
                value=float(st.session_state.electrical_storage["Max Power"]),
                placeholder="e.g. 100 kW",
                key="max_power"
            )
        
        st.markdown("**Max Capacity**")
        max_capacity = st.number_input(
        "Enter max capacity (kWh)",
        min_value=0.0,
        value=float(st.session_state.electrical_storage["Max Capacity"]),  # Use "max_c" and provide default
        placeholder="e.g. 100 kWh",
        key="max_capacity"
        )

        st.markdown("**Max Charge Rate**")
        max_c = st.number_input(
        "Enter max charge rate",
        min_value=0.0,
        value=float(st.session_state.electrical_storage.get("max_c", 0.5)),  # Provide default value
        placeholder="e.g. 0.5",
        key="max_c"
        )
        
        # Submit button
        if st.button("Submit Settings", key="submit_electrical_storage_settings"):
            st.session_state.electrical_storage = {
                 "Charge Efficiency": charging_efficiency/100,
                 "Discharge Efficiency": discharging_efficiency / 100,
                 "Max Power": max_power,
                 "Max Capacity": max_capacity,
                 "max_c": max_c
                 }
            st.success("Electrical Storage settings updated successfully!")
        
    # Display stored settings
    if "electrical_storage" in st.session_state:
        st.header("Current Electrical Storage Settings")
        st.json(st.session_state.electrical_storage)

        # Create DataFrame for table
        data = {
            "Metric": [
                "Charge Efficiency",
                "Discharge Efficiency",
                "Max Power",
                "Max Capacity",
                "max_c"
            ],
            "Value": [
                st.session_state.electrical_storage["Charge Efficiency"],
                st.session_state.electrical_storage["Discharge Efficiency"],
                st.session_state.electrical_storage["Max Power"],
                st.session_state.electrical_storage["Max Capacity"],
                st.session_state.electrical_storage["max_c"]
            ],
            "Unit": [",", ",", "kW", "kWh","."]
        }
        df = pd.DataFrame(data)

        # Display table
        st.subheader("Electrical Storage Settings Table")
        styled_df = df.style.set_properties(**{
            'text-align': 'left',
            'font-size': '14px',
            'padding': '10px',
            'border': '1px solid #ddd',
            'background-color': '#f9f9f9'
        }).set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('font-weight', 'bold'), ('text-align', 'left'), ('padding', '10px'), ('border', '1px solid #ddd')]},
            {'selector': 'td', 'props': [('border', '1px solid #ddd')]}
        ])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)