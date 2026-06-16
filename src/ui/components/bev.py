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
    "identifier": "bev_1",
    "max_battery_capacity": 75.0,
    "min_battery_capacity": 15.0,
    "battery_usage": 50.0,
    "charging_power": 11.0,
    "charging_efficiency": 0.95,
    "load_degradation_begin": 0.8,
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
    st.header("Einstellungen Elektrofahrzeug (BEV)")
    # Form layout
    # Technology parameters in main content area
    with st.container():
        with st.form(key=f"bev_settings_form_{form_key_suffix}"):
            st.markdown("**Bezeichner**")
            identifier = st.text_input(
                "Bezeichner",
                value=str(st.session_state["bev_settings"]["identifier"]),
                label_visibility="collapsed",
                key="bev_identifier",
            )

            # Max Battery Capacity
            st.markdown("**Max. Batteriekapazität**")
            max_battery_capacity = st.number_input(
                "Maximale Batteriekapazität eingeben (kWh)",
                min_value=0.0,
                value=float(st.session_state["bev_settings"]["max_battery_capacity"]),
                placeholder="z. B. 100 kWh",
                key="max_battery_capacity",
                help="Nutzbare Kapazität der Fahrzeugbatterie. Typisch: Kleinwagen 20–40 kWh, Mittelklasse 50–80 kWh, Oberklasse/SUV 80–110 kWh.",
            )

            # Min Battery Capacity
            st.markdown("**Min. Batteriekapazität**")
            min_battery_capacity = st.number_input(
                "Minimale Batteriekapazität eingeben (kWh)",
                min_value=0.0,
                value=float(st.session_state["bev_settings"]["min_battery_capacity"]),
                placeholder="z. B. 15 kWh",
                key="min_battery_capacity",
                help="Untere Ladegrenze (Reserve), die nicht unterschritten wird. Häufig 10–20 % der Maximalkapazität.",
            )

            # Battery Usage
            st.markdown("**Batterienutzung**")
            battery_usage = st.number_input(
                "Batterienutzung eingeben (kWh/Tag)",
                min_value=0.0,
                value=float(st.session_state["bev_settings"]["battery_usage"]),
                placeholder="z. B. 50",
                key="battery_usage",
                help="Täglicher Fahrenergiebedarf (Entladung). Richtwert ~15–20 kWh je 100 km; bei 40 km/Tag also ca. 6–8 kWh.",
            )
            st.markdown("*Hinweis: Der tägliche Energieverbrauch der Fahrt (Entladung).*")

            # Charging Power
            st.markdown("**Ladeleistung**")
            charging_power = st.number_input(
                "Ladeleistung eingeben (kW)",
                min_value=0.0,
                value=float(st.session_state["bev_settings"]["charging_power"]),
                placeholder="z. B. 11 kW",
                key="charging_power",
                help="Anschlussleistung des Ladepunkts. Typisch: 3,7 kW (Haushaltssteckdose), 11/22 kW (Wallbox), 50–350 kW (Schnelllader).",
            )

            # Charging Efficiency
            st.markdown("**Ladewirkungsgrad**")
            charging_efficiency = st.number_input(
                "Ladewirkungsgrad eingeben (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state["bev_settings"]["charging_efficiency"] * 100),
                placeholder="z. B. 90 %",
                key="charging_efficiency",
                help="Anteil der zugeführten Energie, der in der Batterie ankommt. Typisch 85–95 % (AC-Laden inkl. Ladeverluste).",
            )

            st.markdown("**Beginn der Ladeleistungsreduktion**")
            load_degradation_begin = st.number_input(
            "Beginn der Ladeleistungsreduktion eingeben (SoC-Anteil 0–1)",
                min_value=0.0,
                value=float(st.session_state["bev_settings"]["load_degradation_begin"]),
                placeholder="z. B. 0,8",
                key="load_degradation_begin",
                help="Ladezustand, ab dem die Ladeleistung gedrosselt wird, um die Batterie zu schonen. Üblich ~0,8 (= 80 % SoC).",
            )

            st.markdown("**Startzeit**")
            start_time = st.time_input(
                "Startzeit eingeben (HH:MM:SS)",
                value=st.session_state["bev_settings"]["start_time"],
                help="Zeitpunkt, ab dem das Fahrzeug angeschlossen ist und geladen werden kann (z. B. Ankunft zu Hause)"

            )

            st.markdown("**Endzeit**")
            end_time = st.time_input(
                "Endzeit eingeben (HH:MM:SS)",
                value=st.session_state["bev_settings"]["end_time"],
                help="Zeitpunkt, zu dem das Fahrzeug vollständig geladen sein muss (z. B. Abfahrt zur Arbeit)"

            )

            st.markdown("**Zeitbasis**")
            timebase = st.number_input(
                "Zeitbasis eingeben (Minuten)",
                min_value=1,
                max_value=60,
                value=15,
                step=1,
                key="timebase",
                help="Zeitliche Auflösung der Simulation. Standard 15 Minuten (96 Schritte/Tag).",
            )



            # Submit button
            submit_button = st.form_submit_button("Einstellungen speichern")

        # Handle form submission
        if submit_button:
            
        # Update session state with new settings
            st.session_state["bev_settings"] = {
                "identifier": identifier,
                "max_battery_capacity": max_battery_capacity,
                "min_battery_capacity": min_battery_capacity,
                "battery_usage": battery_usage,
                "charging_power": charging_power,
                "charging_efficiency": charging_efficiency / 100,
                "load_degradation_begin":load_degradation_begin,
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
           
            st.success("BEV-Einstellungen erfolgreich aktualisiert!")
            # Display the updated settings for user confirmation
    #    st.json(st.session_state.bev_settings)

        # Optional: Display current settings
    #    st.markdown("### Current BEV Settings")
    #    st.json(st.session_state.bev_settings)
    import pandas as pd

 # Create DataFrame for table
    data = {
    "Größe": ["Bezeichner", "Max. Batteriekapazität", "Min. Batteriekapazität", "Batterienutzung", "Ladeleistung", "Ladewirkungsgrad", "Beginn Ladeleistungsreduktion","Startzeit","Endzeit","Zeitbasis"],
    "Wert": [identifier, max_battery_capacity, min_battery_capacity, battery_usage, charging_power, charging_efficiency, load_degradation_begin,start_time,end_time,timebase],
    "Einheit": ["", "kWh", "kWh", "kWh/Tag", "kW", "%", "","HH:MM:SS", "HH:MM:SS", "Minuten"]
}
    df = pd.DataFrame(data)

    # Display table
    st.subheader("Aktuelle BEV-Einstellungen")
    st.dataframe(
    df.style.format(
        {
            "Wert": lambda x: "{:.1f}".format(x) if isinstance(x, (int, float)) else x
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

