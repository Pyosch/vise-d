import datetime
import streamlit as st
from st_files_connection import FilesConnection
import os

from paper_figures import fig_5, fig_7, fig_8, fig_9, fig_5_plotly
from pp_networks import pp_networks
import matplotlib.pyplot as plt
from vpplib.environment import Environment
import pandas as pd

def pv_settings(form_key_suffix=""):
    # Initialize session state for PV settings if not already set
    if "pv_settings" not in st.session_state:
        st.session_state.pv_settings = {
            "PV Module Library": "SandiaMod",
            "PV Module": "Canadian_Solar_CS5P_220M___2009_",
            "PV Inverter Library": "cecinverter",
            "PV Inverter": "ABB__MICRO_0_25_I_OUTD_US_208__208V_",
            "PV Surface Tilt": 0.0,
            "PV Surface Azimuth": 0.0,
            "PV Modules per String": 0,
            "PV Strings per Inverter": 0
        }

    st.title("Photovoltaic (PV) Settings")

    # Input Section in Sidebar
    with st.sidebar:
        st.header("Enter PV Settings")

        module_library = st.selectbox(
            "Module Library",
            options=["SandiaMod", "CECMod"],
            index=0 if st.session_state.pv_settings["PV Module Library"] == "SandiaMod" else 1,
            key="pv_module_library"
        )

        module = st.selectbox(
            "Module",
            options=["Canadian_Solar_CS5P_220M___2009_"],
            index=0,
            key="pv_module"
        )

        inverter_library = st.selectbox(
            "Inverter Library",
            options=["cecinverter"],
            index=0,
            key="pv_inverter_library"
        )

        inverter = st.selectbox(
            "Inverter",
            options=["ABB__MICRO_0_25_I_OUTD_US_208__208V_"],
            index=0,
            key="pv_inverter"
        )

        surface_tilt = st.number_input(
            "Surface Tilt (°)",
            min_value=0.0,
            max_value=90.0,
            value=float(st.session_state.pv_settings["PV Surface Tilt"]),
            step=1.0,
            key="pv_surface_tilt"
        )

        surface_azimuth = st.number_input(
            "Surface Azimuth (°)",
            min_value=0.0,
            max_value=360.0,
            value=float(st.session_state.pv_settings["PV Surface Azimuth"]),
            step=1.0,
            key="pv_surface_azimuth"
        )

        modules_per_string = st.number_input(
            "Modules per String",
            min_value=0,
            value=int(st.session_state.pv_settings["PV Modules per String"]),
            step=1,
            key="pv_modules_per_string"
        )

        strings_per_inverter = st.number_input(
            "Strings per Inverter",
            min_value=0,
            value=int(st.session_state.pv_settings["PV Strings per Inverter"]),
            step=1,
            key="pv_strings_per_inverter"
        )

        if st.button("Submit Settings", key="submit_pv_settings"):
            st.session_state.pv_settings = {
                "PV Module Library": module_library,
                "PV Module": module,
                "PV Inverter Library": inverter_library,
                "PV Inverter": inverter,
                "PV Surface Tilt": surface_tilt,
                "PV Surface Azimuth": surface_azimuth,
                "PV Modules per String": modules_per_string,
                "PV Strings per Inverter": strings_per_inverter
            }
            st.success("PV settings updated successfully!")

    # Display stored settings
    if "pv_settings" in st.session_state:
      #  st.header("Current PV Settings")
      #  st.json(st.session_state.pv_settings)

        # Create DataFrame for table
        data = {
            "Metric": [
                "PV Module Library",
                "PV Module",
                "PV Inverter Library",
                "PV Inverter",
                "PV Surface Tilt",
                "PV Surface Azimuth",
                "PV Modules per String",
                "PV Strings per Inverter"
            ],
            "Value": [
                st.session_state.pv_settings["PV Module Library"],
                st.session_state.pv_settings["PV Module"],
                st.session_state.pv_settings["PV Inverter Library"],
                st.session_state.pv_settings["PV Inverter"],
                st.session_state.pv_settings["PV Surface Tilt"],
                st.session_state.pv_settings["PV Surface Azimuth"],
                st.session_state.pv_settings["PV Modules per String"],
                st.session_state.pv_settings["PV Strings per Inverter"]
            ],
            "Unit": ["", "", "", "", "°", "°", "", ""]
        }
        df = pd.DataFrame(data)

        # Define numeric metrics for formatting
        numeric_metrics = ["PV Surface Tilt", "PV Surface Azimuth", "PV Modules per String", "PV Strings per Inverter"]

        # Pre-format the 'Value' column
        df['Value'] = df.apply(
            lambda row: f"{float(row['Value']):.1f}" if row['Metric'] in numeric_metrics else str(row['Value']),
            axis=1
        )

        # Display table
        st.subheader("PV Settings Table")
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
        
        
        