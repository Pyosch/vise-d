"""Electrical Energy Storage configuration UI component.

Streamlit form for configuring electrical storage parameters including capacity,
power ratings, efficiency, and charge/discharge characteristics.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import datetime
import streamlit as st
from st_files_connection import FilesConnection
import os

from src.visualization import fig_5, fig_7, fig_8, fig_9, fig_5_plotly
from src.network import pp_networks
import matplotlib.pyplot as plt
from vpplib.environment import Environment
import pandas as pd

# Import validation and error handling utilities
try:
    from src.utils.validation import InputValidator, validate_energy_system_inputs, display_validation_results
    from src.utils.error_handling import handle_data_processing_errors, log_user_action
except ImportError:
    # Fallback if utils are not available
    st.warning("⚠️ Erweiterte Validierungsfunktionen nicht verfügbar")
    
    class InputValidator:
        @staticmethod
        def validate_efficiency(value, field_name):
            return (True, "")
        @staticmethod
        def validate_power_rating(value, field_name):
            return (True, "")
        @staticmethod
        def validate_positive_number(value, field_name, allow_zero=True):
            return (True, "")
    
    def validate_energy_system_inputs(**kwargs):
        return []
    
    def display_validation_results(results, show_success=True):
        return True
    
    def handle_data_processing_errors(func):
        return func
    
    def log_user_action(action, details=None):
        pass




def electrical_storage(form_key_suffix=""):
    if "electrical_storage" not in st.session_state:
        st.session_state.electrical_storage={
            "Charge Efficiency": 0.95,  # 95% - typical Li-ion
            "Discharge Efficiency": 0.95,  # 95% - typical Li-ion
            "Max Power" : 10.0,  # kW - typical home battery
            "Max Capacity": 10.0,  # kWh - typical home battery
            "max_c": 1.0  # 1C - charge/discharge in 1 hour
            
        }
    # Der Seitentitel wird von der aufrufenden Seite gesetzt.

    # Technology parameters in main content area
    with st.container():
        st.header("Einstellungen Elektrischer Speicher")

        st.markdown("**Ladewirkungsgrad**")
        charging_efficiency = st.number_input(
                "Ladewirkungsgrad eingeben (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.electrical_storage["Charge Efficiency"] * 100),
                placeholder="z. B. 90 %",
                key="charging_efficiency",
                help="Anteil der Energie, der beim Laden in der Batterie ankommt. Li-Ion 90–98 %, Blei-Säure 80–90 %.",
            )
        st.markdown("**Entladewirkungsgrad**")
        discharging_efficiency = st.number_input(
                "Entladewirkungsgrad eingeben (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.electrical_storage["Discharge Efficiency"] * 100),
                placeholder="z. B. 90 %",
                key="discharging_efficiency",
                help="Anteil der gespeicherten Energie, der beim Entladen nutzbar ist. Li-Ion 90–98 %.",
            )

        st.markdown("**Max. Leistung**")
        max_power = st.number_input(
                "Maximale Leistung eingeben (kW)",
                min_value=0.0,
                value=float(st.session_state.electrical_storage["Max Power"]),
                placeholder="z. B. 100 kW",
                key="max_power",
                help="Maximale Lade-/Entladeleistung. Typischer Bereich: 1–1000 kW"
            )

        st.markdown("**Max. Kapazität**")
        max_capacity = st.number_input(
        "Maximale Kapazität eingeben (kWh)",
        min_value=0.0,
        value=float(st.session_state.electrical_storage["Max Capacity"]),
        placeholder="z. B. 100 kWh",
        key="max_capacity",
        help="Maximale Speicherkapazität. Typischer Bereich: 1–10000 kWh"
        )

        st.markdown("**Max. Laderate (C-Rate)**")
        max_c = st.number_input(
        "Maximale Laderate eingeben (C-Rate)",
        min_value=0.0,
        max_value=5.0,
        value=float(st.session_state.electrical_storage.get("max_c", 0.5)),
        placeholder="z. B. 0,5",
        key="max_c",
        help="C-Rate: 1C bedeutet vollständige Ladung/Entladung in 1 Stunde. Typischer Bereich: 0,1–2,0"
        )
        
        # Real-time validation
        st.markdown("---")
        st.markdown("**📋 Eingabevalidierung**")

        # Validate all inputs
        validation_results = []
        validation_results.extend([
            InputValidator.validate_efficiency(charging_efficiency, "Ladewirkungsgrad"),
            InputValidator.validate_efficiency(discharging_efficiency, "Entladewirkungsgrad"),
            InputValidator.validate_power_rating(max_power, "Max. Leistung", max_reasonable=5000),
            InputValidator.validate_positive_number(max_capacity, "Max. Kapazität", allow_zero=False),
            InputValidator.validate_numeric_range(max_c, 0.01, 5.0, "Max. Laderate (C-Rate)")
        ])
        
        # Additional custom validations
        if max_power > 0 and max_capacity > 0:
            power_to_capacity_ratio = max_power / max_capacity
            if power_to_capacity_ratio > 2.0:
                validation_results.append((True, f"⚠️ Hohes Leistungs-Kapazitäts-Verhältnis ({power_to_capacity_ratio:.2f}). Dies deutet auf einen Hochleistungsspeicher mit kurzer Dauer hin."))
            elif power_to_capacity_ratio < 0.1:
                validation_results.append((True, f"⚠️ Niedriges Leistungs-Kapazitäts-Verhältnis ({power_to_capacity_ratio:.2f}). Dies deutet auf einen Speicher mit geringer Leistung und langer Dauer hin."))
        
        # Display validation results
        all_inputs_valid = display_validation_results(validation_results, show_success=False)
        
        # Submit button with validation
        if st.button("Einstellungen speichern", key="submit_electrical_storage_settings"):
            if all_inputs_valid:
                # Log user action
                log_user_action("electrical_storage_settings_submitted", {
                    "charging_efficiency": charging_efficiency,
                    "discharging_efficiency": discharging_efficiency,
                    "max_power": max_power,
                    "max_capacity": max_capacity,
                    "max_c": max_c
                })
                
                # Store validated settings
                st.session_state.electrical_storage = {
                     "Charge Efficiency": charging_efficiency/100,
                     "Discharge Efficiency": discharging_efficiency / 100,
                     "Max Power": max_power,
                     "Max Capacity": max_capacity,
                     "max_c": max_c
                     }
                st.success("✅ Einstellungen des elektrischen Speichers erfolgreich aktualisiert!")

                # Show calculated metrics
                with st.expander("📊 **Berechnete Speicher-Kennzahlen**"):
                    st.metric("Gesamtwirkungsgrad (Zyklus)", f"{(charging_efficiency * discharging_efficiency / 100):.1f}%")
                    if max_capacity > 0:
                        st.metric("Leistungs-Energie-Verhältnis", f"{max_power/max_capacity:.2f} kW/kWh")
                        st.metric("Volle Ladezeit bei max. Leistung", f"{max_capacity/max_power:.1f} Stunden")

            else:
                st.error("❌ Bitte korrigieren Sie die oben genannten Fehler, bevor Sie speichern.")

        # Show input tips
        with st.expander("💡 **Eingabehinweise**"):
            st.markdown("""
            **Lade-/Entladewirkungsgrad**:
            - Lithium-Ionen-Batterien: 90–98 %
            - Blei-Säure-Batterien: 80–90 %
            - Flow-Batterien: 70–85 %

            **Maximale Leistung**:
            - Wohngebäude: 1–20 kW
            - Gewerbe: 20–500 kW
            - Großspeicher: 500+ kW

            **Maximale Kapazität**:
            - Wohngebäude: 5–100 kWh
            - Gewerbe: 100–10.000 kWh
            - Großspeicher: 10+ MWh

            **Hinweise zur C-Rate**:
            - 0,1C: langsames Laden (10 Stunden bis voll)
            - 0,5C: Standardladung (2 Stunden bis voll)
            - 1C: schnelles Laden (1 Stunde bis voll)
            - 2C+: Schnellladung (< 30 Minuten bis voll)
            """)
    
    # Display stored settings with improved formatting
    if "electrical_storage" in st.session_state:
        st.markdown("---")
        st.header("📊 Aktuelle Konfiguration des elektrischen Speichers")

        # Create enhanced display
        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "Ladewirkungsgrad",
                f"{st.session_state.electrical_storage['Charge Efficiency']*100:.1f}%",
                help="Energetischer Wirkungsgrad beim Laden der Batterie"
            )
            st.metric(
                "Max. Leistung",
                f"{st.session_state.electrical_storage['Max Power']:.1f} kW",
                help="Maximale Leistung für Laden/Entladen"
            )
            st.metric(
                "C-Rate",
                f"{st.session_state.electrical_storage['max_c']:.2f}",
                help="Maximale Lade-/Entladerate"
            )

        with col2:
            st.metric(
                "Entladewirkungsgrad",
                f"{st.session_state.electrical_storage['Discharge Efficiency']*100:.1f}%",
                help="Energetischer Wirkungsgrad beim Entladen der Batterie"
            )
            st.metric(
                "Max. Kapazität",
                f"{st.session_state.electrical_storage['Max Capacity']:.1f} kWh",
                help="Maximale Speicherkapazität"
            )

            # Calculate and display round-trip efficiency
            round_trip_eff = (st.session_state.electrical_storage['Charge Efficiency'] *
                             st.session_state.electrical_storage['Discharge Efficiency'] * 100)
            st.metric(
                "Gesamtwirkungsgrad (Zyklus)",
                f"{round_trip_eff:.1f}%",
                help="Gesamtwirkungsgrad über einen Lade-Entlade-Zyklus"
            )

        # Create DataFrame for table
        data = {
            "Größe": [
                "Ladewirkungsgrad",
                "Entladewirkungsgrad",
                "Max. Leistung",
                "Max. Kapazität",
                "Max. Laderate (C-Rate)"
            ],
            "Wert": [
                st.session_state.electrical_storage["Charge Efficiency"],
                st.session_state.electrical_storage["Discharge Efficiency"],
                st.session_state.electrical_storage["Max Power"],
                st.session_state.electrical_storage["Max Capacity"],
                st.session_state.electrical_storage["max_c"]
            ],
            "Einheit": ["", "", "kW", "kWh", ""]
        }
        df = pd.DataFrame(data)

        # Display table
        st.subheader("Tabelle der Speichereinstellungen")
        styled_df = df.style.set_properties(**{
            'text-align': 'left',
            'font-size': '14px',
            'padding': '10px',
            'border': '1px solid #ddd',
            'background-color': '#f9f9f9'
        }).set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('font-weight', 'bold'), ('text-align', 'left'), ('padding', '10px'), ('border', '1px solid #ddd')]},
            {'selector': 'td', 'props': [('border', '1px solid #ddd')]}
        ])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)