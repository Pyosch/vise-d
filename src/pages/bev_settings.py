"""Battery Electric Vehicle (BEV) settings page for VISE-D dashboard.

This page provides configuration and simulation for BEV charging scenarios.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import datetime
import streamlit as st
import matplotlib.pyplot as plt
from vpplib.battery_electric_vehicle import BatteryElectricVehicle
from vpplib.environment import Environment
from src.ui.components import battery_electric_vehicle_settings
from src.utils.pdf_export import generate_pdf_report_matplotlib


# Initialize session state for BEV settings if not already present
if "bev_settings" not in st.session_state:
    st.session_state["bev_settings"] = {
        "max_battery_capacity": 75.0,  # kWh - typical EV battery
        "min_battery_capacity": 15.0,  # kWh - 20% reserve
        "battery_usage": 50.0,  # kWh - daily usage
        "charging_power": 11.0,  # kW - typical AC wallbox
        "charging_efficiency": 0.95,  # 95% efficiency
        "load_degradation_begin": 0.8,  # 80% SoC
        "user_profile": "None",
        "selected_environment": "None",
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
    
    with st.form(key="bev_simulation_form_1"):
        # BEV simulation button
        bev_simulation_button = st.form_submit_button("BEV simulieren")
        
        if bev_simulation_button:
            start = "2024-06-01 00:00:00"
            end = "2024-06-01 23:45:00"
            timebase = 15
            env = Environment(start=start, end=end, timebase=timebase)
            
            # Initialize BEV with form inputs
            st.session_state["bev"] = BatteryElectricVehicle(
                unit="kW",
                identifier="bev_1",
                environment=env,
                battery_max=st.session_state["bev_settings"]["max_battery_capacity"],
                battery_min=st.session_state["bev_settings"]["min_battery_capacity"],
                battery_usage=st.session_state["bev_settings"]["battery_usage"],
                charging_power=st.session_state["bev_settings"]["charging_power"],
                load_degradation_begin=st.session_state["bev_settings"]["load_degradation_begin"],
                charge_efficiency=st.session_state["bev_settings"]["charging_efficiency"]
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

            # Store figure for PDF export (outside the form)
            st.session_state["bev_fig"] = fig

            # Display the plot in Streamlit
            st.pyplot(fig)

    # ── PDF Export ──────────────────────────────────────────────────────
    if "bev_fig" in st.session_state and st.session_state.get("bev") is not None:
        st.markdown("---")
        st.markdown("### 📄 Export Simulation Results")
        if st.button("📄 Generate PDF Report", key="bev_pdf_btn"):
            try:
                bev_obj = st.session_state["bev"]
                bev_cfg = st.session_state.get("bev_settings", {})

                _metadata = {
                    "Max. Kapazität": f"{bev_cfg.get('max_battery_capacity', '-')} kWh",
                    "Min. Kapazität": f"{bev_cfg.get('min_battery_capacity', '-')} kWh",
                    "Batterienutzung": f"{bev_cfg.get('battery_usage', '-')} kWh/Tag",
                    "Ladeleistung": f"{bev_cfg.get('charging_power', '-')} kW",
                    "Wirkungsgrad": f"{bev_cfg.get('charging_efficiency', '-') * 100:.0f} %",
                    "Startzeit": str(bev_cfg.get('start_time', '-')),
                    "Endzeit": str(bev_cfg.get('end_time', '-')),
                    "Zeitbasis": f"{bev_cfg.get('timebase', 15)} min",
                }

                ts = bev_obj.timeseries
                _summary = {
                    "Spitzenlast": f"{float(ts.max().max()):.2f} kW",
                    "Mittellast": f"{float(ts.mean().mean()):.2f} kW",
                    "Energie (Tag)": f"{float(ts.sum().sum()) * (bev_cfg.get('timebase', 15) / 60):.2f} kWh",
                    "Zeitschritte": str(len(ts)),
                }

                with st.spinner("PDF wird erstellt…"):
                    _pdf_bytes = generate_pdf_report_matplotlib(
                        figures=[st.session_state["bev_fig"]],
                        chart_titles=["BEV Ladeprofil (Zeitreihe)"],
                        title="E-Mobilität – BEV Simulationsbericht",
                        metadata=_metadata,
                        summary_stats=_summary,
                    )
                st.download_button(
                    label="⬇️ PDF herunterladen",
                    data=_pdf_bytes,
                    file_name="bev_simulationsbericht.pdf",
                    mime="application/pdf",
                    key="bev_pdf_download"
                )
                st.success("✅ PDF bereit! Oben auf den Button klicken zum Herunterladen.")
            except Exception as _pdf_err:
                st.error(f"❌ PDF-Erstellung fehlgeschlagen: {_pdf_err}")
