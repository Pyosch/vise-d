"""Wind turbine configuration page for VISE-D dashboard.

This page provides configuration and simulation for wind turbines.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime
from vpplib.wind_power import WindPower
from vpplib.environment import Environment
from src.ui.components import wind
from src.ui.components.location_weather import location_weather_selector


def wind_configuration(key_suffix="wind1"):
    """Configure and simulate wind turbine power generation.
    
    This function sets up wind turbine configuration including hub height,
    rotor diameter, turbine type, and various modeling parameters.
    Simulates wind power generation using vpplib and DWD weather data.
    
    Args:
        key_suffix: Suffix for form keys to ensure uniqueness.
    
    Returns:
        None: Updates session state and displays simulation results.
    """
    st.title("🌬️ Windkraft Konfiguration")
    st.markdown("Konfigurieren Sie Ihre Windkraftanlage und simulieren Sie die Energieerzeugung.")
    
    # Location and weather station selection
    location_data = location_weather_selector(
        form_key_suffix="wind_config",
        parameters=['wind', 'temperature', 'pressure'],
        show_date_range=True,
        default_lat=51.2,
        default_lon=6.43
    )
    
    if not location_data:
        st.warning("⚠️ Bitte wählen Sie einen Standort und Zeitraum aus.")
        return
    
    st.markdown("---")
    
    # Wind turbine settings form
    wind(form_key_suffix=key_suffix)
    
    with st.form(key="wind_simulation_form"):
        # Wind simulation button
        wind_simulation_button = st.form_submit_button("🚀 Windkraft Simulation starten")
           
        if wind_simulation_button:
            with st.spinner("Wetterdaten werden abgerufen und Windkraftanlage wird simuliert..."):
                try:
                    env = Environment(
                        start=location_data['start_date'].strftime("%Y-%m-%d %H:%M:%S"),
                        end=location_data['end_date'].strftime("%Y-%m-%d %H:%M:%S"),
                        use_timezone_aware_time_index=True,
                        surpress_output_globally=False
                    )
                    station_meta = env.get_dwd_wind_data(
                        lat=location_data['latitude'],
                        lon=location_data['longitude'],
                    )

                    st.success("✅ Wetterdaten erfolgreich abgerufen!")
                    with st.expander("ℹ️ Wetterdaten-Information"):
                        if location_data['method'] == 'station':
                            st.write(f"**Station:** {location_data['station_id']}")
                        st.write(f"**Koordinaten:** {location_data['latitude']:.4f}°N, {location_data['longitude']:.4f}°E")
                        st.write(f"**Angefragt:** {location_data['start_date'].date()} bis {location_data['end_date'].date()}")
                        st.write(f"**Datenpunkte:** {len(env.wind_data)}")
                        if not station_meta.empty:
                            row = station_meta.iloc[0]
                            st.write(f"**Station:** {row.get('name', '—')} (ID {row.get('station_id', '?')}, {row.get('distance', 0):.1f} km)")

                except Exception as e:
                    st.error(f"❌ Fehler beim Abrufen der Wetterdaten: {e}")
                    return

            with st.spinner("Windkraftanlage wird simuliert..."):
                try:
                    
                    # Initialize Wind Turbine with form inputs
                    st.session_state["wind_turbine"] = WindPower(
                        identifier=f"Wind_{location_data['latitude']:.2f}_{location_data['longitude']:.2f}",
                        unit="kW",
                        environment=env,
                        hub_height=st.session_state["wind_settings"]["Hub Height"],
                        rotor_diameter=st.session_state["wind_settings"]["Rotor Diameter"],
                        turbine_type=st.session_state["wind_settings"]["Turbine Type"],
                        power_coefficient=st.session_state["wind_settings"]["Power Coefficient"],
                    )
                    
                    st.success("✅ Windkraftanlage erfolgreich konfiguriert!")
                    
                    # Prepare and display time series
                    st.session_state["wind_turbine"].prepare_time_series()
                    
                    st.markdown("### 📊 Simulationsergebnisse")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        total_generation = st.session_state['wind_turbine'].timeseries.sum()
                        if hasattr(total_generation, 'iloc'):
                            total_generation = total_generation.iloc[0]
                        st.metric(
                            "Gesamterzeugung",
                            f"{float(total_generation):.2f} kWh"
                        )
                    with col2:
                        max_power = st.session_state['wind_turbine'].timeseries.max()
                        if hasattr(max_power, 'iloc'):
                            max_power = max_power.iloc[0]
                        st.metric(
                            "Maximale Leistung",
                            f"{float(max_power):.2f} kW"
                        )
                    
                    # Show data preview
                    with st.expander("📋 Zeitreihen-Daten (Vorschau)"):
                        st.dataframe(st.session_state["wind_turbine"].timeseries.head(20))
                    
                    # Create visualization
                    st.markdown("### 📈 Zeitreihen-Visualisierung")
                    fig, ax = plt.subplots(figsize=(16, 9))
                    st.session_state["wind_turbine"].timeseries.plot(ax=ax)
                    ax.set_title("Windkraft Energieerzeugung")
                    ax.set_xlabel("Zeit")
                    ax.set_ylabel("Leistung (kW)")
                    ax.grid(True, alpha=0.3)
                    plt.tight_layout()
                    st.pyplot(fig)
                    plt.close(fig)
                    
                except Exception as e:
                    st.error(f"❌ Fehler bei der Windkraft-Simulation: {e}")
                    import traceback
                    with st.expander("🔍 Fehlerdetails"):
                        st.code(traceback.format_exc())
