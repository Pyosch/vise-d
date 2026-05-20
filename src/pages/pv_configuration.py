"""Photovoltaic (PV) configuration page for VISE-D dashboard.

This page provides configuration and simulation for PV systems.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime
from vpplib.photovoltaic import Photovoltaic
from vpplib.environment import Environment
from src.ui.components import pv_settings
from src.ui.components.location_weather import location_weather_selector


def pv_configuration():
    """Configure and simulate photovoltaic systems.
    
    This function sets up PV system configuration including module selection,
    inverter selection, tilt angle, azimuth, and string configuration.
    Simulates PV generation using vpplib and DWD weather data.
    
    Returns:
        None: Updates session state and displays simulation results.
    """
    st.title("☀️ PV Konfiguration")
    st.markdown("Konfigurieren Sie Ihr Photovoltaik-System und simulieren Sie die Energieerzeugung.")
    
    # Location and weather station selection
    location_data = location_weather_selector(
        form_key_suffix="pv_config",
        parameters=['solar', 'temperature', 'wind', 'pressure'],
        show_date_range=True,
        default_lat=51.4,
        default_lon=6.97
        # Date defaults: None = past 7 days (today - 7 days to today)
    )
    
    if not location_data:
        st.warning("⚠️ Bitte wählen Sie einen Standort und Zeitraum aus.")
        return

    # Persist the currently selected location/date from Auswahl-Zusammenfassung
    # so other tabs (e.g. network timeseries) can use the exact same coordinates.
    st.session_state["pv_location_data"] = {
        "latitude": float(location_data["latitude"]),
        "longitude": float(location_data["longitude"]),
        "start_date": location_data.get("start_date"),
        "end_date": location_data.get("end_date"),
        "method": location_data.get("method"),
    }
    
    st.markdown("---")
    
    # PV system settings form
    pv_settings(form_key_suffix="pv1")
           
    with st.form(key="pv_simulation_form"):
        # PV simulation button
        pv_simulation_button = st.form_submit_button("🚀 PV Simulation starten")
           
        if pv_simulation_button:
            with st.spinner("Wetterdaten werden abgerufen und PV-System wird simuliert..."):
                try:
                    env = Environment(
                        start=location_data['start_date'].strftime("%Y-%m-%d %H:%M:%S"),
                        end=location_data['end_date'].strftime("%Y-%m-%d %H:%M:%S"),
                        use_timezone_aware_time_index=True,
                        surpress_output_globally=False
                    )
                    station_meta = env.get_dwd_pv_data(
                        lat=location_data['latitude'],
                        lon=location_data['longitude'],
                    )

                    st.success("✅ Wetterdaten erfolgreich abgerufen!")
                    with st.expander("ℹ️ Wetterdaten-Information"):
                        if location_data['method'] == 'station':
                            st.write(f"**Station:** {location_data['station_id']}")
                        st.write(f"**Koordinaten:** {location_data['latitude']:.4f}°N, {location_data['longitude']:.4f}°E")
                        st.write(f"**Angefragt:** {location_data['start_date'].date()} bis {location_data['end_date'].date()}")
                        st.write(f"**Datenpunkte:** {len(env.pv_data)}")
                        if not station_meta.empty:
                            row = station_meta.iloc[0]
                            st.write(f"**Station:** {row.get('name', '—')} (ID {row.get('station_id', '?')}, {row.get('distance', 0):.1f} km)")

                except Exception as e:
                    st.error(f"❌ Fehler beim Abrufen der Wetterdaten: {e}")
                    return
            
                    # Initialize PV with form inputs
                    st.session_state["pv"] = Photovoltaic(
                        identifier=f"PV_{location_data['latitude']:.2f}_{location_data['longitude']:.2f}",
                        unit="kW",
                        latitude=location_data['latitude'],
                        longitude=location_data['longitude'],
                        environment=env,
                        module_lib=st.session_state["pv_settings"]["PV Module Library"],
                        module=st.session_state["pv_settings"]["PV Module"],
                        inverter_lib=st.session_state["pv_settings"]["PV Inverter Library"],
                        inverter=st.session_state["pv_settings"]["PV Inverter"],
                        surface_tilt=st.session_state["pv_settings"]["PV Surface Tilt"],
                        surface_azimuth=st.session_state["pv_settings"]["PV Surface Azimuth"],
                        modules_per_string=st.session_state["pv_settings"]["PV Modules per String"],
                        strings_per_inverter=st.session_state["pv_settings"]["PV Strings per Inverter"],
                        temp_lib='sapm',
                        temp_model='open_rack_glass_glass'
                    )
                
                    st.success("✅ PV-System erfolgreich konfiguriert!")
                    
                    # Prepare and display time series
                    st.session_state["pv"].prepare_time_series()
                    
                    st.markdown("### 📊 Simulationsergebnisse")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        total_generation = st.session_state['pv'].timeseries.sum()
                        if hasattr(total_generation, 'iloc'):
                            total_generation = total_generation.iloc[0]
                        st.metric(
                            "Gesamterzeugung",
                            f"{float(total_generation):.2f} kWh"
                        )
                    with col2:
                        max_power = st.session_state['pv'].timeseries.max()
                        if hasattr(max_power, 'iloc'):
                            max_power = max_power.iloc[0]
                        st.metric(
                            "Maximale Leistung",
                            f"{float(max_power):.2f} kW"
                        )
                    
                    # Show data preview
                    with st.expander("📋 Zeitreihen-Daten (Vorschau)"):
                        st.dataframe(st.session_state["pv"].timeseries.head(20))
                    
                    # Create a Matplotlib figure
                    st.markdown("### 📈 Zeitreihen-Visualisierung")
                    fig, ax = plt.subplots(figsize=(16, 9))
                    st.session_state["pv"].timeseries.plot(ax=ax)
                    ax.set_title("PV Energieerzeugung")
                    ax.set_xlabel("Zeit")
                    ax.set_ylabel("Leistung (kW)")
                    ax.grid(True, alpha=0.3)
                    plt.tight_layout()
                    st.pyplot(fig)
                    plt.close(fig)
                    
                except Exception as e:
                    st.error(f"❌ Fehler bei der PV-Simulation: {e}")
                    import traceback
                    with st.expander("🔍 Fehlerdetails"):
                        st.code(traceback.format_exc())
