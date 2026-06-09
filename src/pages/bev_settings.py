"""Battery Electric Vehicle (BEV) settings page for VISE-D dashboard.

This page provides configuration and simulation for BEV charging scenarios.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import datetime
from datetime import date, timedelta

import streamlit as st
import matplotlib.pyplot as plt
from vpplib.battery_electric_vehicle import BatteryElectricVehicle
from vpplib.environment import Environment
from src.ui.components import battery_electric_vehicle_settings


# Initialize session state for BEV settings if not already present
if "bev_settings" not in st.session_state:
    st.session_state["bev_settings"] = {
        "identifier": "bev_1",
        "max_battery_capacity": 75.0,  # kWh - typical EV battery
        "min_battery_capacity": 15.0,  # kWh - 20% reserve
        "battery_usage": 50.0,  # kWh - daily usage
        "charging_power": 11.0,  # kW - typical AC wallbox
        "charging_efficiency": 0.95,  # 95% efficiency
        "load_degradation_begin": 0.8,  # 80% SoC
        "start_time": datetime.time(18, 0, 0),  # 6 PM - typical plug-in time
        "end_time": datetime.time(7, 0, 0),  # 7 AM - departure time
        "timebase": 15
    }


def bev_settings():
    """Configure and simulate Battery Electric Vehicle charging.
    
    This function sets up the settings for the Battery Electric Vehicle (BEV) simulation.
    It includes a form for user inputs such as maximum and minimum battery capacity, battery usage,
    charging power, charging efficiency, load degradation begin, and user profile.
    It also initializes the BEV object with these settings and prepares the time series data for simulation.
    The function displays the time series data and plots it using Matplotlib.
    The function is designed to be used within a Streamlit application.
    
    Args:
        None
        
    Returns:
        None: The function does not return any value. It updates the session state and displays data in the Streamlit app.
    """
    st.title("🚗 E-Mobilität")
    from src.content.page_descriptions import render_page_description
    render_page_description("bev_settings")

    # Display BEV configuration form
    battery_electric_vehicle_settings(form_key_suffix="bev1")

    # ── Zeitraum ──────────────────────────────────────────────────────────────
    st.subheader("Zeitraum")
    default_end = date.today() - timedelta(days=1)
    default_start = default_end - timedelta(days=6)
    col_s, col_e = st.columns(2)
    date_start = col_s.date_input("Von", value=default_start, key="bev_cfg_start")
    date_end = col_e.date_input("Bis", value=default_end, key="bev_cfg_end")
    n_days = (date_end - date_start).days + 1
    if n_days < 1:
        st.error("Enddatum muss nach dem Startdatum liegen.")
        return

    settings = st.session_state["bev_settings"]
    timebase = int(settings["timebase"])
    st.caption(
        f"{n_days} Tag(e) × {int(24 * 60 / timebase)} Schritte "
        f"= {n_days * int(24 * 60 / timebase)} Zeitschritte ({timebase}-min-Raster)"
    )

    with st.form(key="bev_simulation_form_1"):
        # BEV simulation button
        bev_simulation_button = st.form_submit_button("BEV simulieren")

        if bev_simulation_button:
            start = f"{date_start} 00:00:00"
            end = f"{date_end} 23:45:00"
            env = Environment(
                start=start, end=end, timebase=timebase, time_freq=f"{timebase} min"
            )

            # Fahrtzeiten: Abfahrt = Endzeit (Auto verlässt das Haus),
            # Ankunft = Startzeit (Anstecken). Doppelte Einträge, da vpplib
            # intern random.randrange(0, len-1) nutzt (stürzt bei Länge 1 ab).
            departure = settings["end_time"].strftime("%H:%M:%S")
            arrival = settings["start_time"].strftime("%H:%M:%S")

            # Initialize BEV with form inputs
            st.session_state["bev"] = BatteryElectricVehicle(
                unit="kW",
                identifier=settings["identifier"],
                environment=env,
                battery_max=settings["max_battery_capacity"],
                battery_min=settings["min_battery_capacity"],
                battery_usage=settings["battery_usage"],
                charging_power=settings["charging_power"],
                load_degradation_begin=settings["load_degradation_begin"],
                charge_efficiency=settings["charging_efficiency"],
                week_trip_start=[departure, departure],
                week_trip_end=[arrival, arrival],
                weekend_trip_start=[departure, departure],
                weekend_trip_end=[arrival, arrival],
            )
        
            st.session_state["bev"].prepare_time_series()
            st.write("**Zeitreihendaten (erste 5 Zeilen):**")
            st.dataframe(st.session_state["bev"].timeseries)  # Display the timeseries data for debugging

            # Create a Matplotlib figure
            fig, ax = plt.subplots(figsize=(16, 9))
            st.session_state["bev"].timeseries.plot(ax=ax)  # Plot the timeseries on the provided axes
            ax.set_title("BEV-Zeitreihe")
            ax.set_xlabel("Zeit")
            ax.set_ylabel("Wert (kW)")
            plt.tight_layout()

            # Display the plot in Streamlit
            st.pyplot(fig)
