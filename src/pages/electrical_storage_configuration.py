"""Electrical storage configuration page for VISE-D dashboard.

This page provides configuration and simulation for electrical energy storage systems.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from vpplib import ElectricalEnergyStorage
from vpplib.environment import Environment
from src.ui.components import electrical_storage


def electrical_storage_configuration():
    """Configure and simulate electrical energy storage systems.
    
    This function sets up electrical storage configuration including capacity,
    power rating, charge/discharge efficiency, and C-rate.
    Simulates storage operation with PV generation and baseload consumption.
    
    Returns:
        None: Updates session state and displays simulation results.
    """
    electrical_storage(form_key_suffix="electrical_storage1")
    
    with st.form(key="electrical_storage_simulation_form"):
        # Electrical Storage simulation button
        electrical_storage_simulation_button = st.form_submit_button("Simulate Electrical Storage")
           
        if electrical_storage_simulation_button:
            start = "2024-06-01 00:00:00"
            end = "2024-06-07 23:45:00"
            year = "2024"
            timebase = 15
            name = "bus"
            latitude = 51.200001
            longitude = 6.433333
            
            env = Environment(timebase=timebase, start=start, end=end, year=year)
            env.get_dwd_pv_data(lat=latitude, lon=longitude)
            
            PhotoV = st.session_state["pv"]
            PhotoV.identifier = (name + "_pv")
            PhotoV.environment = env    
            PhotoV.inverter = "Connect_Renewable_Energy__CE_4000__240V_"
            
            PhotoV.prepare_time_series()
            
            # Initialize Electrical Storage with form inputs
            st.session_state["es"] = ElectricalEnergyStorage(
                environment=env,
                identifier=(name + "_storage"),
                unit="kW",
                charge_efficiency=st.session_state["electrical_storage"]["Charge Efficiency"],
                discharge_efficiency=st.session_state["electrical_storage"]["Discharge Efficiency"],
                max_power=st.session_state["electrical_storage"]["Max Power"],
                max_c=st.session_state["electrical_storage"]["max_c"],
                capacity=st.session_state["electrical_storage"]["Max Capacity"]
            )
        
            st.success("Electrical Storage settings updated successfully!")
            
            PhotoV.prepare_time_series()
            
            # TODO: Replace with proper baseload data source
            # Creating synthetic baseload profile for demonstration
            time_index = pd.date_range(start=start, end=end, freq=f"{timebase}min")
            baseload = pd.DataFrame({
                "0": [1.5] * len(time_index)  # Constant 1.5 kW baseload
            }, index=time_index)
            
            house_loadshape = pd.DataFrame(baseload["0"].loc[start:end] / 1000)
            house_loadshape["pv_gen"] = PhotoV.timeseries.loc[start:end]
            house_loadshape["residual_load"] = (
                baseload["0"].loc[start:end] / 1000 - PhotoV.timeseries.bus_pv
            )
            
            # Assign residual load to storage
            st.session_state["es"].residual_load = house_loadshape.residual_load
            
            # Prepare time series data for Electrical Storage
            st.session_state["es"].prepare_time_series()
            st.write("**Time Series Data (First 5 Rows):**")
            st.dataframe(st.session_state["es"].timeseries.head(5))
            
            # Create a Matplotlib figure
            fig, ax = plt.subplots(figsize=(16, 9))
            st.session_state["es"].timeseries.plot(ax=ax)
            plt.tight_layout()
            st.pyplot(fig)
