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
    # Der Seitentitel wird von der aufrufenden Seite gesetzt.
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
            st.header("Wärmepumpen-Einstellungen")

            identifier = st.selectbox(
            "Bezeichner auswählen",
            options=["None", "hp1", "hp2"],
            format_func=lambda x: "Kein" if x == "None" else x,
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
                "Nutzerprofil",
                options = ["None","Profile1","Profile2"],
                format_func=lambda x: {"None": "Kein", "Profile1": "Profil 1", "Profile2": "Profil 2"}.get(x, x),
                index = 0 if st.session_state.heatpump_settings["user_profile"]=="None" else 1 if st.session_state.heatpump_settings["user_profile"]=="Profile1" else 2,
                key = "user_profile"
            )

        # Dropdown for Heat Pump Type
            _hp_type_label = st.selectbox(
            "Wärmepumpentyp",
            options=["Luft", "Erde"],
            index=0,
                placeholder="Wärmepumpentyp wählen"
        )
            heat_pump_type = {"Luft": "Air", "Erde": "Ground"}[_hp_type_label]

        # Number input for Heat System Temperature
            system_temperature = st.number_input(
            "Vorlauftemperatur des Heizsystems (°C)",
            min_value=-50.0,
            max_value=100.0,
            value=0.0,
            step=0.1,
            placeholder="z. B. 20,5"
        )

        # Number input for Electrical Power
            el_power = st.number_input(
            "Elektrische Leistung (kW)",
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=0.1,
            placeholder="z. B. 5"
        )

            th_power = st.number_input(
                "Thermische Leistung (kW)",
                min_value = 0.0,
                max_value = 100.0,
                value = 0.0,
                step = 0.1,
                placeholder = "z. B. 5"
            )


            ramp_up_time = st.time_input(
                "Anlaufzeit eingeben (HH:MM)",
                    value=datetime.time(0,0)

                )

            ramp_down_time = st.time_input(
                "Abschaltzeit eingeben (HH:MM)",
                    value=datetime.time(0,0)

                )

            min_run_time = st.time_input(
                "Mindestlaufzeit eingeben (HH:MM)",
                    value=datetime.time(0,0)
                )

            min_stop_time = st.time_input(
                "Mindeststillstandszeit eingeben (HH:MM)",
                    value=datetime.time(0,0)

                )
            
            
        

    # Submit button
            if st.button("Einstellungen speichern",key="submit_heatpump_settings"):
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
        st.header("Aktuelle Wärmepumpen-Einstellungen")
        # Anzeige-Labels für die gespeicherten Schlüssel (Schlüssel selbst bleiben unverändert).
        _labels = {
            "identifier": "Bezeichner",
            "heat_pump_type": "Wärmepumpentyp",
            "Heat System Temperature": "Vorlauftemperatur (°C)",
            "el_power": "Elektrische Leistung (kW)",
            "user_profile": "Nutzerprofil",
            "th_power": "Thermische Leistung (kW)",
            "Ramp Up Time": "Anlaufzeit",
            "Ramp Down Time": "Abschaltzeit",
            "Minimum Run Time": "Mindestlaufzeit",
            "Minimum Stop Time": "Mindeststillstandszeit",
        }
        _values = {"Air": "Luft", "Ground": "Erde", "None": "Kein"}
        # Create a DataFrame for the table
        settings_df = pd.DataFrame([
            {"Einstellung": _labels.get(key, key), "Wert": _values.get(value, value)}
            for key, value in st.session_state.heatpump_settings.items()
        ])

        # Style the DataFrame for better presentation
        st.dataframe(
            settings_df,
            use_container_width=True,
            column_config={
                "Einstellung": st.column_config.TextColumn("Einstellung", width="medium"),
                "Wert": st.column_config.TextColumn("Wert", width="large")
            }
        )
