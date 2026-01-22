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
from src.ui.components.location_weather import location_weather_selector
from src.data_layer.weather_integration import fetch_weather_for_pv


def electrical_storage_configuration():
    """Configure and simulate electrical energy storage systems.
    
    This function sets up electrical storage configuration including capacity,
    power rating, charge/discharge efficiency, and C-rate.
    Simulates storage operation with PV generation and baseload consumption.
    
    Returns:
        None: Updates session state and displays simulation results.
    """
    st.title("🔋 Elektrischer Speicher Konfiguration")
    st.markdown("Konfigurieren Sie Ihren Batteriespeicher und simulieren Sie den Betrieb mit PV-Erzeugung.")
    
    # Location and weather station selection
    location_data = location_weather_selector(
        form_key_suffix="storage_config",
        parameters=['solar', 'temperature', 'wind', 'pressure'],
        show_date_range=True,
        default_lat=51.2,
        default_lon=6.43
    )
    
    if not location_data:
        st.warning("⚠️ Bitte wählen Sie einen Standort und Zeitraum aus.")
        return
    
    st.markdown("---")
    
    # Electrical storage settings form
    electrical_storage(form_key_suffix="electrical_storage1")
    
    # Additional configuration
    with st.expander("⚡ Lastprofil Einstellungen"):
        baseload_power = st.number_input(
            "Grundlast (kW)",
            min_value=0.0,
            max_value=10.0,
            value=1.5,
            step=0.1,
            help="Konstante elektrische Grundlast des Haushalts"
        )
    
    with st.form(key="electrical_storage_simulation_form"):
        # Electrical Storage simulation button
        electrical_storage_simulation_button = st.form_submit_button("🚀 Speicher Simulation starten")
           
        if electrical_storage_simulation_button:
            with st.spinner("Wetterdaten werden abgerufen..."):
                try:
                    # Fetch weather data using DWD fetcher
                    weather_data, metadata = fetch_weather_for_pv(
                        latitude=location_data['latitude'],
                        longitude=location_data['longitude'],
                        start_date=location_data['start_date'],
                        end_date=location_data['end_date'],
                        resolution="15min"
                    )
                    
                    st.success("✅ Wetterdaten erfolgreich abgerufen!")
                    
                    # Display metadata
                    with st.expander("ℹ️ Wetterdaten-Information"):
                        if location_data['method'] == 'station':
                            st.write(f"**Station:** {location_data['station_id']}")
                        st.write(f"**Koordinaten:** {location_data['latitude']:.4f}°N, {location_data['longitude']:.4f}°E")
                        st.write(f"**Angefragt:** {location_data['start_date'].date()} bis {location_data['end_date'].date()}")
                        st.write(f"**Verfügbar:** {weather_data.index[0]} bis {weather_data.index[-1]}")
                        st.write(f"**Datenpunkte:** {len(weather_data)}")
                        
                        if metadata.get('warnings'):
                            st.warning("⚠️ Hinweise:")
                            for warning in metadata['warnings']:
                                st.write(f"- {warning}")
                    
                except Exception as e:
                    st.error(f"❌ Fehler beim Abrufen der Wetterdaten: {e}")
                    return
            
            with st.spinner("PV-System und Speicher werden simuliert..."):
                try:
                    # Create environment with pre-fetched weather data
                    env = Environment(
                        timebase=15,
                        start=location_data['start_date'].strftime("%Y-%m-%d %H:%M:%S"),
                        end=location_data['end_date'].strftime("%Y-%m-%d %H:%M:%S"),
                        surpress_output_globally=False
                    )
                    
                    # Inject pre-fetched weather data
                    env.pv_data = weather_data
                    
                    # Check if PV system is configured
                    if "pv" not in st.session_state:
                        st.error("❌ Bitte konfigurieren Sie zuerst ein PV-System auf der 'PV Konfiguration' Seite.")
                        return
                    
                    # Configure PV system
                    PhotoV = st.session_state["pv"]
                    name = f"bus_{location_data['latitude']:.2f}_{location_data['longitude']:.2f}"
                    PhotoV.identifier = (name + "_pv")
                    PhotoV.environment = env
                    
                    # Prepare PV time series
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
                
                    st.success("✅ Speichersystem erfolgreich konfiguriert!")
                    
                    # Create baseload profile
                    start_str = location_data['start_date'].strftime("%Y-%m-%d %H:%M:%S")
                    end_str = location_data['end_date'].strftime("%Y-%m-%d %H:%M:%S")
                    time_index = pd.date_range(start=start_str, end=end_str, freq="15min")
                    baseload = pd.DataFrame({
                        "0": [baseload_power] * len(time_index)
                    }, index=time_index)
                    
                    # Calculate residual load (consumption - generation)
                    house_loadshape = pd.DataFrame()
                    house_loadshape["baseload"] = baseload["0"].loc[start_str:end_str]
                    house_loadshape["pv_gen"] = PhotoV.timeseries.loc[start_str:end_str]
                    house_loadshape["residual_load"] = (
                        house_loadshape["baseload"] - house_loadshape["pv_gen"]
                    )
                    
                    # Assign residual load to storage
                    st.session_state["es"].residual_load = house_loadshape.residual_load
                    
                    # Prepare time series data for Electrical Storage
                    st.session_state["es"].prepare_time_series()
                    
                    st.markdown("### 📊 Simulationsergebnisse")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        total_charged = st.session_state['es'].timeseries[
                            st.session_state['es'].timeseries > 0
                        ].sum()
                        if hasattr(total_charged, 'iloc'):
                            total_charged = total_charged.iloc[0]
                        st.metric(
                            "Gesamt geladen",
                            f"{float(total_charged):.2f} kWh"
                        )
                    with col2:
                        total_discharged = abs(st.session_state['es'].timeseries[
                            st.session_state['es'].timeseries < 0
                        ].sum())
                        if hasattr(total_discharged, 'iloc'):
                            total_discharged = total_discharged.iloc[0]
                        st.metric(
                            "Gesamt entladen",
                            f"{float(total_discharged):.2f} kWh"
                        )
                    with col3:
                        max_power_val = st.session_state['es'].timeseries.abs().max()
                        if hasattr(max_power_val, 'iloc'):
                            max_power_val = max_power_val.iloc[0]
                        st.metric(
                            "Max. Leistung",
                            f"{float(max_power_val):.2f} kW"
                        )
                    
                    # Display energy balance
                    with st.expander("⚖️ Energiebilanz"):
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            total_pv = house_loadshape["pv_gen"].sum()
                            st.metric("PV-Erzeugung", f"{total_pv:.2f} kWh")
                        with col_b:
                            total_consumption = house_loadshape["baseload"].sum()
                            st.metric("Verbrauch", f"{total_consumption:.2f} kWh")
                        with col_c:
                            self_consumption_ratio = min(100, (total_consumption / total_pv * 100)) if total_pv > 0 else 0
                            st.metric("Eigenverbrauch", f"{self_consumption_ratio:.1f}%")
                    
                    # Show data preview
                    with st.expander("📋 Zeitreihen-Daten (Vorschau)"):
                        preview_df = pd.DataFrame({
                            'PV Generation': house_loadshape["pv_gen"],
                            'Grundlast': house_loadshape["baseload"],
                            'Residuallast': house_loadshape["residual_load"],
                            'Speicher': st.session_state["es"].timeseries
                        })
                        st.dataframe(preview_df.head(20))
                    
                    # Create visualization
                    st.markdown("### 📈 Zeitreihen-Visualisierung")
                    
                    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12))
                    
                    # Plot 1: PV, Load, and Residual Load
                    house_loadshape[["pv_gen", "baseload", "residual_load"]].plot(ax=ax1)
                    ax1.set_title("PV-Erzeugung, Grundlast und Residuallast")
                    ax1.set_xlabel("Zeit")
                    ax1.set_ylabel("Leistung (kW)")
                    ax1.legend(["PV-Erzeugung", "Grundlast", "Residuallast"])
                    ax1.grid(True, alpha=0.3)
                    ax1.axhline(y=0, color='k', linestyle='-', linewidth=0.5)
                    
                    # Plot 2: Storage Operation
                    st.session_state["es"].timeseries.plot(ax=ax2, color='green')
                    ax2.set_title("Speicher-Betrieb (positiv = laden, negativ = entladen)")
                    ax2.set_xlabel("Zeit")
                    ax2.set_ylabel("Leistung (kW)")
                    ax2.grid(True, alpha=0.3)
                    ax2.axhline(y=0, color='k', linestyle='-', linewidth=0.5)
                    
                    plt.tight_layout()
                    st.pyplot(fig)
                    plt.close(fig)
                    
                except Exception as e:
                    st.error(f"❌ Fehler bei der Speicher-Simulation: {e}")
                    import traceback
                    with st.expander("🔍 Fehlerdetails"):
                        st.code(traceback.format_exc())
