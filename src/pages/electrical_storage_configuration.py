"""Electrical storage configuration page for VISE-D dashboard.

This page provides configuration and simulation for electrical energy storage systems.

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
from vpplib import ElectricalEnergyStorage
from vpplib.environment import Environment
from src.ui.components import electrical_storage
from src.ui.components.netzmittimeseries import get_normalized_pv_output

try:
    import osmnx as ox
    _HAS_OSMNX = True
except Exception:
    _HAS_OSMNX = False


@st.cache_data
def _geocode(city: str) -> tuple[float, float]:
    lat, lon = ox.geocode(city)
    return float(lat), float(lon)


def electrical_storage_configuration():
    """Configure and simulate electrical energy storage systems.
    
    This function sets up electrical storage configuration including capacity,
    power rating, charge/discharge efficiency, and C-rate.
    Simulates storage operation with PV generation and baseload consumption.
    
    Returns:
        None: Updates session state and displays simulation results.
    """
    st.title("🔋 Elektrischer Speicher Konfiguration")
    from src.content.page_descriptions import render_page_description
    render_page_description("electrical_storage")
    st.markdown("Konfigurieren Sie Ihren Batteriespeicher und simulieren Sie den Betrieb mit PV-Erzeugung.")

    # ── Standort ──────────────────────────────────────────────────────────────
    st.subheader("Standort")
    if not _HAS_OSMNX:
        st.error("osmnx ist nicht installiert — Geocoding nicht verfügbar.")
        return

    city_input = st.text_input("Ort (Stadtname)", value="Köln", key="storage_cfg_city")
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
    date_start = col_s.date_input("Von", value=default_start, key="storage_cfg_start")
    date_end = col_e.date_input("Bis", value=default_end, key="storage_cfg_end")
    n_days = (pd.Timestamp(date_end) - pd.Timestamp(date_start)).days + 1
    if n_days < 1:
        st.error("Enddatum muss nach dem Startdatum liegen.")
        return
    st.caption(f"{n_days} Tag(e) × 96 Schritte = {n_days * 96} Zeitschritte (15-min-Raster)")

    # Für die Simulation benötigte datetime-Werte (voller Tagesbereich)
    start_date = datetime.combine(date_start, datetime.min.time())
    end_date = datetime.combine(date_end, datetime.max.time())

    # ── PV-Anlage ─────────────────────────────────────────────────────────────
    # Vereinfachtes 1-kWp-Referenzmodell (PVlib + DWD), skaliert auf die
    # installierte Leistung — identisch zur Seite "PV-Konfiguration".
    st.subheader("PV-Anlage")
    pv_capacity_kwp = st.number_input(
        "Installierte Leistung (kWp)",
        min_value=0.1,
        max_value=100_000.0,
        value=10.0,
        key="storage_cfg_pv_cap",
        help="Nennleistung der PV-Anlage unter Standardbedingungen. Hausdach typ. 5–15 kWp; ~6–7 m² Modulfläche je kWp.",
    )

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
            help="Konstante elektrische Grundlast des Haushalts. Richtwert: 0,3–0,8 kW Dauerlast (Jahresverbrauch 3.500 kWh ≈ 0,4 kW im Mittel)."
        )
    
    with st.form(key="electrical_storage_simulation_form"):
        # Electrical Storage simulation button
        electrical_storage_simulation_button = st.form_submit_button("🚀 Speicher Simulation starten")
           
        if electrical_storage_simulation_button:
            with st.spinner("Wetterdaten werden abgerufen, PV-Erzeugung und Speicher werden simuliert..."):
                try:
                    start_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
                    end_str = end_date.strftime("%Y-%m-%d %H:%M:%S")

                    # Minimal environment for the storage model (only timebase is used).
                    env = Environment(
                        timebase=15,
                        start=start_str,
                        end=end_str,
                        surpress_output_globally=False
                    )

                    # ── Simplified PV model (same as the "PV-Konfiguration" page) ──
                    # 1-kWp reference yield from PVlib + DWD, scaled to installed capacity.
                    raw_pv = get_normalized_pv_output(
                        lat, lon,
                        pd.Timestamp(date_start),
                        pd.Timestamp(date_end) + pd.Timedelta(days=1),
                    )
                    normalized_pv = pd.to_numeric(
                        raw_pv, errors="coerce"
                    ).fillna(0.0).reset_index(drop=True)
                    pv_values = normalized_pv.values * pv_capacity_kwp

                    st.success("✅ Wetterdaten abgerufen und PV-Erzeugung berechnet!")
                    with st.expander("ℹ️ Wetterdaten-Information"):
                        st.write(f"**Koordinaten:** {lat:.4f}°N, {lon:.4f}°E")
                        st.write(f"**Angefragt:** {start_date.date()} bis {end_date.date()}")
                        st.write(f"**Installierte Leistung:** {pv_capacity_kwp:.1f} kWp")
                        st.write(f"**Datenpunkte:** {len(normalized_pv)}")

                    # Initialize Electrical Storage with form inputs
                    name = f"bus_{lat:.2f}_{lon:.2f}"
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

                    # Build the 15-min load profiles (baseload, PV generation, residual load).
                    time_index = pd.date_range(start=start_str, end=end_str, freq="15min")

                    # Align the PV generation to the baseload index positionally.
                    n = min(len(time_index), len(pv_values))
                    house_loadshape = pd.DataFrame(index=time_index)
                    house_loadshape["baseload"] = float(baseload_power)
                    house_loadshape["pv_gen"] = 0.0
                    house_loadshape.iloc[:n, house_loadshape.columns.get_loc("pv_gen")] = pv_values[:n]
                    house_loadshape["residual_load"] = (
                        house_loadshape["baseload"] - house_loadshape["pv_gen"]
                    ).fillna(0.0)

                    # Assign residual load to storage
                    st.session_state["es"].residual_load = house_loadshape.residual_load

                    # Prepare time series data for Electrical Storage
                    st.session_state["es"].prepare_time_series()

                    storage_ts = st.session_state["es"].timeseries
                    if isinstance(storage_ts, pd.DataFrame):
                        storage_power = storage_ts["residual_load"] if "residual_load" in storage_ts.columns else storage_ts.iloc[:, 0]
                        storage_soc = storage_ts["state_of_charge"] if "state_of_charge" in storage_ts.columns else None
                    else:
                        storage_power = pd.to_numeric(storage_ts, errors="coerce").fillna(0.0)
                        storage_soc = None
                    
                    st.markdown("### 📊 Simulationsergebnisse")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        total_charged = storage_power[storage_power > 0].sum()
                        st.metric(
                            "Gesamt geladen",
                            f"{float(total_charged):.2f} kWh"
                        )
                    with col2:
                        total_discharged = abs(storage_power[storage_power < 0].sum())
                        st.metric(
                            "Gesamt entladen",
                            f"{float(total_discharged):.2f} kWh"
                        )
                    with col3:
                        max_power_val = storage_power.abs().max()
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
                        preview_data = {
                            'PV Generation': house_loadshape["pv_gen"],
                            'Grundlast': house_loadshape["baseload"],
                            'Residuallast': house_loadshape["residual_load"],
                            'Speicher': storage_power
                        }
                        if storage_soc is not None:
                            preview_data['Speicher SOC'] = storage_soc

                        preview_df = pd.DataFrame(preview_data)
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
                    storage_power.plot(ax=ax2, color='green')
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
