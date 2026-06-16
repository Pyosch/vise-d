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

import streamlit as st
from st_files_connection import FilesConnection
import os

from src.visualization import fig_5, fig_7, fig_8, fig_9, fig_5_plotly
from src.network import pp_networks
import matplotlib.pyplot as plt
from vpplib.environment import Environment

# Defaults entsprechen dem vpplib-Beispiel (examples/demo_heat_pump.py).
# Ramp-/Min-Zeiten sind in Zeitschritten (1 Zeitschritt = timebase = 15 min).
_HP_DEFAULTS = {
    "identifier": "hp1",
    "heat_pump_type": "Air",
    "Heat System Temperature": 60.0,  # °C
    "el_power": 5.0,  # kW - elektrische Leistung
    "th_power": 8.0,  # kW - thermische Leistung
    "yearly_thermal_energy_demand": 12500.0,  # kWh/Jahr
    "building_type": "DE_HEF33",  # SigLinDe-Gebäudeklassifikation
    "Ramp Up Time": 1.0,    # Zeitschritte
    "Ramp Down Time": 1.0,  # Zeitschritte
    "Minimum Run Time": 1.0,   # Zeitschritte
    "Minimum Stop Time": 2.0,  # Zeitschritte
}

# Auswahloptionen für den Gebäudetyp (SigLinDe / BDEW).
_HP_BUILDING_TYPES = ["DE_HEF33", "DE_HEF34", "DE_HMF33", "DE_HMF34", "DE_GKO34"]

# Numerische Felder, die als float vorliegen müssen.
_HP_NUMERIC_KEYS = (
    "Heat System Temperature", "el_power", "th_power", "yearly_thermal_energy_demand",
    "Ramp Up Time", "Ramp Down Time", "Minimum Run Time", "Minimum Stop Time",
)


def heatpump_settings(form_key_suffix=""):
    # Der Seitentitel wird von der aufrufenden Seite gesetzt.
    if "heatpump_settings" not in st.session_state:
        st.session_state.heatpump_settings = dict(_HP_DEFAULTS)
    else:
        # Bestehende Session reparieren: fehlende Schlüssel ergänzen und
        # veraltete Werte (z. B. datetime.time aus älteren Versionen) auf
        # numerische Zeitschritte zurücksetzen.
        s = st.session_state.heatpump_settings
        for key, default in _HP_DEFAULTS.items():
            s.setdefault(key, default)
        for key in _HP_NUMERIC_KEYS:
            try:
                s[key] = float(s[key])
            except (TypeError, ValueError):
                s[key] = float(_HP_DEFAULTS[key])
    # Technology parameters in main content area
    with st.container():
        # Input Section
            st.header("Wärmepumpen-Einstellungen")

            identifier = st.text_input(
                "Bezeichner",
                value=str(st.session_state.heatpump_settings["identifier"]),
            )

        # Dropdown for Heat Pump Type
            _hp_type_label = st.selectbox(
            "Wärmepumpentyp",
            options=["Luft", "Erde"],
            index=0,
                placeholder="Wärmepumpentyp wählen",
                help="Wärmequelle der Wärmepumpe. Luft (Luft-Wasser): günstiger, JAZ ~3–4. Erde (Sole/Erdwärme): effizienter, JAZ ~4–5, aber aufwendigere Erschließung.",
        )
            heat_pump_type = {"Luft": "Air", "Erde": "Ground"}[_hp_type_label]

        # Number input for Heat System Temperature
            system_temperature = st.number_input(
            "Vorlauftemperatur des Heizsystems (°C)",
            min_value=-50.0,
            max_value=100.0,
            value=float(st.session_state.heatpump_settings["Heat System Temperature"]),
            step=0.1,
            placeholder="z. B. 60",
            help="Benötigte Temperatur des Heizkreises. Fußbodenheizung 30–40 °C, Heizkörper (Neubau) 45–55 °C, Altbau bis 70 °C. Niedriger = effizienter.",
        )

        # Number input for Electrical Power
            el_power = st.number_input(
            "Elektrische Leistung (kW)",
            min_value=0.0,
            max_value=100.0,
            value=float(st.session_state.heatpump_settings["el_power"]),
            step=0.1,
            placeholder="z. B. 5",
            help="Max. elektrische Leistungsaufnahme des Verdichters. Einfamilienhaus typ. 2–5 kW.",
        )

            th_power = st.number_input(
                "Thermische Leistung (kW)",
                min_value = 0.0,
                max_value = 100.0,
                value=float(st.session_state.heatpump_settings["th_power"]),
                step = 0.1,
                placeholder = "z. B. 8",
                help="Max. Heizleistung. Einfamilienhaus typ. 6–12 kW; sollte zur Heizlast des Gebäudes passen.",
            )

            yearly_thermal_energy_demand = st.number_input(
                "Jährlicher Wärmebedarf (kWh)",
                min_value=1000.0,
                max_value=50000.0,
                value=float(st.session_state.heatpump_settings["yearly_thermal_energy_demand"]),
                step=500.0,
                help="Heizenergiebedarf pro Jahr. Richtwert: Neubau ~50–100 kWh/m²·a, Altbau ~150–250 kWh/m²·a; Einfamilienhaus oft 10.000–20.000 kWh/a.",
            )

            _bt_default = st.session_state.heatpump_settings["building_type"]
            building_type = st.selectbox(
                "Gebäudetyp",
                options=_HP_BUILDING_TYPES,
                index=_HP_BUILDING_TYPES.index(_bt_default) if _bt_default in _HP_BUILDING_TYPES else 0,
                help=(
                    "SigLinDe-Gebäudeklassifikation (BDEW):\n\n"
                    "**HEF** = Einfamilienhaus · **HMF** = Mehrfamilienhaus · **GKO** = Gewerbe/Kommunal\n\n"
                    "**33** = Altbau (vor WSchVO 1977, schlechte Dämmung)\n\n"
                    "**34** = Neubau/modernisiert (nach WSchVO 1984, gute Dämmung)"
                ),
            )

            _ts_help = "In Zeitschritten (1 Zeitschritt = 15 min)."

            ramp_up_time = st.number_input(
                "Anlaufzeit (Zeitschritte)",
                min_value=0.0,
                value=float(st.session_state.heatpump_settings["Ramp Up Time"]),
                step=0.1,
                help=_ts_help,
            )

            ramp_down_time = st.number_input(
                "Abschaltzeit (Zeitschritte)",
                min_value=0.0,
                value=float(st.session_state.heatpump_settings["Ramp Down Time"]),
                step=0.1,
                help=_ts_help,
            )

            min_run_time = st.number_input(
                "Mindestlaufzeit (Zeitschritte)",
                min_value=0.0,
                value=float(st.session_state.heatpump_settings["Minimum Run Time"]),
                step=1.0,
                help=_ts_help,
            )

            min_stop_time = st.number_input(
                "Mindeststillstandszeit (Zeitschritte)",
                min_value=0.0,
                value=float(st.session_state.heatpump_settings["Minimum Stop Time"]),
                step=1.0,
                help=_ts_help,
            )
            
            
        

    # Submit button
            if st.button("Einstellungen speichern",key="submit_heatpump_settings"):
            # Store settings in session state
                st.session_state.heatpump_settings = {
                    "identifier": identifier,
                    "heat_pump_type": heat_pump_type,
                    "Heat System Temperature": system_temperature,
                    "el_power": el_power,
                    "th_power":th_power,
                    "yearly_thermal_energy_demand": yearly_thermal_energy_demand,
                    "building_type": building_type,
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
            "th_power": "Thermische Leistung (kW)",
            "yearly_thermal_energy_demand": "Jährlicher Wärmebedarf (kWh)",
            "building_type": "Gebäudetyp",
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
