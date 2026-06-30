"""Photovoltaic (PV) system configuration UI component.

Streamlit form for configuring PV parameters including module selection,
inverter selection, tilt angle, azimuth, and array configuration.

Author: Pyosch
AI Assistance: Claude Code (Claude Opus 4.8)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["Claude Code (Claude Opus 4.8)"]

import datetime
import streamlit as st
from st_files_connection import FilesConnection
import os
import pvlib
from pvlib import iam

from src.visualization import fig_5, fig_7, fig_8, fig_9, fig_5_plotly
from src.network import pp_networks
import matplotlib.pyplot as plt
from vpplib.environment import Environment
import pandas as pd


SAM_MODULE_LIBRARY_NAMES = {
    "cecmod": "CECMod",
    "sandiamod": "SandiaMod",
}


def _supports_any_aoi_model(module_parameters: pd.Series) -> bool:
    """Return True if module parameters can support at least one pvlib AOI model."""
    param_keys = set(module_parameters.index)
    for model_name in ("physical", "sapm", "ashrae", "martin_ruiz", "interp"):
        required_params = iam._IAM_MODEL_PARAMS.get(model_name, set())
        if required_params and set(required_params).issubset(param_keys):
            return True
    return False


@st.cache_data(show_spinner=False)
def _get_aoi_compatible_modules(module_library_key: str) -> list[str]:
    """Load module names from SAM library that contain valid AOI model parameters."""
    sam_name = SAM_MODULE_LIBRARY_NAMES.get(module_library_key.lower(), "SandiaMod")
    module_db = pvlib.pvsystem.retrieve_sam(sam_name)
    compatible = [
        module_name
        for module_name in module_db.columns
        if _supports_any_aoi_model(module_db[module_name])
    ]
    return sorted(compatible)

def pv_settings(form_key_suffix=""):
    # Initialize session state for PV settings if not already set
    if "pv_settings" not in st.session_state:
        st.session_state.pv_settings = {
            "PV Module Library": "sandiamod",
            "PV Module": "Canadian_Solar_CS5P_220M___2009_",
            "PV Inverter Library": "cecinverter",
            "PV Inverter": "ABB__MICRO_0_25_I_OUTD_US_208__208V_",
            "PV Surface Tilt": 30.0,  # degrees - optimal for Germany
            "PV Surface Azimuth": 180.0,  # degrees - south-facing
            "PV Modules per String": 10,  # typical string size
            "PV Strings per Inverter": 2  # typical residential
        }

    st.title("Photovoltaic (PV) Settings")

    # Input Section in Sidebar
    # Technology parameters in main content area
    with st.container():
        st.header("Enter PV Settings")

        module_library_options = ["cecmod", "sandiamod"]
        module_library_default = str(st.session_state.pv_settings.get("PV Module Library", "sandiamod")).lower()
        module_library_index = (
            module_library_options.index(module_library_default)
            if module_library_default in module_library_options
            else 1
        )
        module_library = st.selectbox(
            "Module Library",
            options=module_library_options,
            index=module_library_index,
            key="pv_module_library"
        )

        module_options = _get_aoi_compatible_modules(module_library)

        if not module_options:
            st.error(
                "No AOI-compatible PV modules were found for this module library. "
                "Please select a different module library."
            )
            return

        module_default = str(st.session_state.pv_settings.get("PV Module", module_options[0]))
        module_index = module_options.index(module_default) if module_default in module_options else 0

        module = st.selectbox(
            "Module",
            options=module_options,
            index=module_index,
            key="pv_module"
        )

        inverter_library_options = ["adrinverter", "cecinverter", "sandiainverter"]
        inverter_library_default = str(st.session_state.pv_settings.get("PV Inverter Library", "cecinverter")).lower().replace("_", "")
        inverter_library_index = (
            inverter_library_options.index(inverter_library_default)
            if inverter_library_default in inverter_library_options
            else 0
        )
        inverter_library = st.selectbox(
            "Inverter Library",
            options=inverter_library_options,
            index=inverter_library_index,
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
        
        
        