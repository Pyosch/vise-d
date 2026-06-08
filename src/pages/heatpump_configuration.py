"""Heat pump configuration page for VISE-D dashboard.

This page provides configuration and simulation for heat pumps.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from vpplib.heat_pump import HeatPump
from vpplib.user_profile import UserProfile
from vpplib.environment import Environment
from src.ui.components import heatpump_settings

try:
    import osmnx as ox
    _HAS_OSMNX = True
except Exception:
    _HAS_OSMNX = False


@st.cache_data
def _geocode(city: str) -> tuple[float, float]:
    lat, lon = ox.geocode(city)
    return float(lat), float(lon)


def heatpump_configuration():
    """Configure and simulate heat pump operation.
    
    This function sets up heat pump configuration including type, electrical power,
    thermal power, system temperature, and operational parameters.
    Simulates heat pump operation using vpplib with thermal demand profiles.
    
    Returns:
        None: Updates session state and displays simulation results.
    """
    st.title("🔥 Wärmepumpe Konfiguration")
    from src.content.page_descriptions import render_page_description
    render_page_description("heatpump")
    st.markdown("Konfigurieren Sie Ihre Wärmepumpe und simulieren Sie den Betrieb.")

    # ── Standort ──────────────────────────────────────────────────────────────
    st.subheader("Standort")
    if not _HAS_OSMNX:
        st.error("osmnx ist nicht installiert — Geocoding nicht verfügbar.")
        return

    city_input = st.text_input("Ort (Stadtname)", value="Köln", key="hp_cfg_city")
    lat: float | None = None
    lon: float | None = None
    if city_input:
        try:
            lat, lon = _geocode(city_input)
            st.caption(f"Koordinaten: {lat:.4f}°N, {lon:.4f}°E")
        except Exception as e:
            st.error(f"Geocoding fehlgeschlagen: {e}")
            return
    if lat is None or lon is None:
        return

    # ── Zeitraum ──────────────────────────────────────────────────────────────
    st.subheader("Zeitraum")
    default_end = date.today() - timedelta(days=1)
    default_start = default_end - timedelta(days=6)
    col_s, col_e = st.columns(2)
    date_start = col_s.date_input("Von", value=default_start, key="hp_cfg_start")
    date_end = col_e.date_input("Bis", value=default_end, key="hp_cfg_end")
    n_days = (pd.Timestamp(date_end) - pd.Timestamp(date_start)).days + 1
    if n_days < 1:
        st.error("Enddatum muss nach dem Startdatum liegen.")
        return
    st.caption(f"{n_days} Tag(e) × 96 Schritte = {n_days * 96} Zeitschritte (15-min-Raster)")

    # Für die Simulation benötigte datetime-Werte (voller Tagesbereich)
    start_date = datetime.combine(date_start, datetime.min.time())
    end_date = datetime.combine(date_end, datetime.max.time())

    st.markdown("---")
    
    # Heat pump settings form
    heatpump_settings(form_key_suffix="hp1")
    
    # Jahreswärmebedarf und Gebäudetyp werden jetzt im Wärmepumpen-Formular
    # erfasst (heatpump_settings) und aus dem session_state gelesen.
    yearly_thermal_energy_demand = st.session_state["heatpump_settings"]["yearly_thermal_energy_demand"]
    building_type = st.session_state["heatpump_settings"]["building_type"]

    # Building and thermal demand settings
    with st.expander("🏠 Gebäude und Wärmebedarf"):
        t_0 = st.number_input(
            "Heizgrenztemperatur (°C)",
            min_value=0.0,
            max_value=70.0,
            value=15.0,
            step=0.5,
            help="Außentemperatur, ab der geheizt wird",
            key="hp_t_0"
        )

    with st.form(key="heatpump_simulation_form"):
        # Heat Pump simulation button
        heatpump_simulation_button = st.form_submit_button("🚀 Wärmepumpe Simulation starten")
           
        if heatpump_simulation_button:
            with st.spinner("Wetterdaten werden abgerufen..."):
                try:
                    _env_temp = Environment(
                        start=start_date.strftime("%Y-%m-%d %H:%M:%S"),
                        end=end_date.strftime("%Y-%m-%d %H:%M:%S"),
                    )
                    station_meta = _env_temp.get_dwd_temp_data(
                        lat=lat,
                        lon=lon,
                    )
                    # temp_data has column 'temperature' in °C; rename for downstream use
                    weather_data = _env_temp.temp_data.rename(columns={'temperature': 'temp_air'})

                    st.success("✅ Wetterdaten erfolgreich abgerufen!")
                    with st.expander("ℹ️ Wetterdaten-Information"):
                        st.write(f"**Koordinaten:** {lat:.4f}°N, {lon:.4f}°E")
                        st.write(f"**Angefragt:** {start_date.date()} bis {end_date.date()}")
                        st.write(f"**Datenpunkte:** {len(weather_data)}")
                        if not station_meta.empty:
                            row = station_meta.iloc[0]
                            st.write(f"**Station:** {row.get('name', '—')} (ID {row.get('station_id', '?')}, {row.get('distance', 0):.1f} km)")

                except Exception as e:
                    st.error(f"❌ Fehler beim Abrufen der Wetterdaten: {e}")
                    return

            with st.spinner("Wärmepumpe wird simuliert..."):
                try:
                    # Determine date range from daily aggregation
                    daily_temp = weather_data['temp_air'].resample('D').mean()
                    
                    # Create full hourly, daily, and 15-min time ranges
                    actual_start = daily_temp.index[0].replace(tzinfo=None, hour=0, minute=0, second=0)
                    actual_end = daily_temp.index[-1].replace(tzinfo=None, hour=23, minute=45, second=0)
                    
                    # Generate complete time indices for vpplib
                    full_hourly_index = pd.date_range(start=actual_start, end=actual_end.replace(minute=0), freq='h', tz='Europe/Berlin')
                    full_daily_index = pd.date_range(start=actual_start, end=actual_end.replace(hour=0, minute=0), freq='D', tz='Europe/Berlin')
                    full_15min_index = pd.date_range(start=actual_start, end=actual_end, freq='15min', tz='Europe/Berlin')
                    
                    # Resample and reindex to complete time ranges
                    mean_temp_hours = weather_data['temp_air'].resample('h').mean().reindex(full_hourly_index, method='nearest').to_frame(name='temperature')
                    mean_temp_days = weather_data['temp_air'].resample('D').mean().reindex(full_daily_index, method='nearest').to_frame(name='temperature')
                    mean_temp_quarter_hours = weather_data['temp_air'].resample('15min').interpolate(method='linear').reindex(full_15min_index, method='nearest').to_frame(name='temperature')
                    
                    # Create environment with full day coverage
                    env = Environment(
                        timebase=15,
                        start=actual_start.strftime("%Y-%m-%d %H:%M:%S"),
                        end=actual_end.strftime("%Y-%m-%d %H:%M:%S"),
                        time_freq="15 min",
                        surpress_output_globally=False
                    )
                    
                    # Set temperature data on environment for HeatPump COP calculation
                    env.mean_temp_hours = mean_temp_hours
                    env.mean_temp_days = mean_temp_days
                    env.mean_temp_quarter_hours = mean_temp_quarter_hours
                    
                    # Create user profile with thermal demand
                    user_profile = UserProfile(
                        identifier=None,
                        latitude=lat,
                        longitude=lon,
                        thermal_energy_demand_yearly=yearly_thermal_energy_demand,
                        mean_temp_days=mean_temp_days,
                        mean_temp_hours=mean_temp_hours,
                        mean_temp_quarter_hours=mean_temp_quarter_hours,
                        building_type=building_type,
                        comfort_factor=None,
                        t_0=t_0,
                    )
                    
                    user_profile.get_thermal_energy_demand()
                    
                    # Initialize Heat Pump with form inputs
                    st.session_state["hp"] = HeatPump(
                        identifier=st.session_state["heatpump_settings"]["identifier"],
                        unit="kW",
                        thermal_energy_demand=user_profile.thermal_energy_demand,
                        environment=env,
                        heat_pump_type=st.session_state["heatpump_settings"]["heat_pump_type"],
                        heat_sys_temp=st.session_state["heatpump_settings"]["Heat System Temperature"],
                        el_power=st.session_state["heatpump_settings"]["el_power"],
                        th_power=st.session_state["heatpump_settings"]["th_power"],
                        ramp_up_time=st.session_state["heatpump_settings"]["Ramp Up Time"],
                        ramp_down_time=st.session_state["heatpump_settings"]["Ramp Down Time"],
                        min_runtime=st.session_state["heatpump_settings"]["Minimum Run Time"],
                        min_stop_time=st.session_state["heatpump_settings"]["Minimum Stop Time"]
                    )
                
                    st.success("✅ Wärmepumpe erfolgreich konfiguriert!")
                    
                    # Calculate and display COP
                    st.markdown("### 📊 Leistungszahl (COP)")
                    st.session_state["hp"].get_cop()
                    
                    with st.expander("📈 COP Verlauf"):
                        fig_cop, ax_cop = plt.subplots(figsize=(16, 9))
                        st.session_state["hp"].cop.plot(ax=ax_cop)
                        ax_cop.set_title("Leistungszahl (COP) über Zeit")
                        ax_cop.set_xlabel("Zeit")
                        ax_cop.set_ylabel("COP")
                        ax_cop.grid(True, alpha=0.3)
                        plt.tight_layout()
                        st.pyplot(fig_cop)
                        plt.close(fig_cop)
                    
                    # Prepare and display time series
                    st.session_state["hp"].prepare_time_series()
                    
                    st.markdown("### 📊 Simulationsergebnisse")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        total_consumption = st.session_state['hp'].timeseries.sum()
                        if hasattr(total_consumption, 'iloc'):
                            total_consumption = total_consumption.iloc[0]
                        st.metric(
                            "Gesamtverbrauch",
                            f"{float(total_consumption):.2f} kWh"
                        )
                    with col2:
                        max_power = st.session_state['hp'].timeseries.max()
                        if hasattr(max_power, 'iloc'):
                            max_power = max_power.iloc[0]
                        st.metric(
                            "Maximale Leistung",
                            f"{float(max_power):.2f} kW"
                        )
                    with col3:
                        avg_cop = st.session_state['hp'].cop.mean()
                        if hasattr(avg_cop, 'iloc'):
                            avg_cop = avg_cop.iloc[0]
                        st.metric(
                            "Durchschnittlicher COP",
                            f"{float(avg_cop):.2f}"
                        )
                    
                    # Show data preview
                    with st.expander("📋 Zeitreihen-Daten (Vorschau)"):
                        st.dataframe(st.session_state["hp"].timeseries.head(20))
                    
                    # Create visualization
                    st.markdown("### 📈 Zeitreihen-Visualisierung")
                    fig, ax = plt.subplots(figsize=(16, 9))
                    st.session_state["hp"].timeseries.plot(ax=ax)
                    ax.set_title("Wärmepumpe Leistungsaufnahme")
                    ax.set_xlabel("Zeit")
                    ax.set_ylabel("Leistung (kW)")
                    ax.grid(True, alpha=0.3)
                    plt.tight_layout()
                    st.pyplot(fig)
                    plt.close(fig)
                    
                except Exception as e:
                    st.error(f"❌ Fehler bei der Wärmepumpen-Simulation: {e}")
                    import traceback
                    with st.expander("🔍 Fehlerdetails"):
                        st.code(traceback.format_exc())
