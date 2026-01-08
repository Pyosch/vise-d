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
    from utils.validation import InputValidator, validate_energy_system_inputs, display_validation_results
    from utils.error_handling import handle_data_processing_errors, log_user_action
except ImportError:
    # Fallback if utils are not available
    st.warning("⚠️ Advanced validation features not available")
    
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
            "Charge Efficiency": 0,
            "Discharge Efficiency": 0,
            "Max Power" : 0,
            "Max Capacity": 0,
            "max_c":0
            
        }
    st.title("Electrical_Storage")
    
    with st.sidebar:
        st.header("Enter Electrical Storage settings")
        
        st.markdown("**Charging Efficiency**")
        charging_efficiency = st.number_input(
                "Enter charging efficiency (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.electrical_storage["Charge Efficiency"] * 100),
                placeholder="e.g. 90%",
                key="charging_efficiency"
            )
        st.markdown("**Discharging Efficiency**")
        discharging_efficiency = st.number_input(
                "Enter discharging efficiency (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.electrical_storage["Discharge Efficiency"] * 100),
                placeholder="e.g. 90%",
                key="discharging_efficiency"
            )
        
        st.markdown("**Max Power**")
        max_power = st.number_input(
                "Enter max power (kW)",
                min_value=0.0,
                value=float(st.session_state.electrical_storage["Max Power"]),
                placeholder="e.g. 100 kW",
                key="max_power",
                help="Maximum power rating for charging/discharging. Typical range: 1-1000 kW"
            )
        
        st.markdown("**Max Capacity**")
        max_capacity = st.number_input(
        "Enter max capacity (kWh)",
        min_value=0.0,
        value=float(st.session_state.electrical_storage["Max Capacity"]),
        placeholder="e.g. 100 kWh",
        key="max_capacity",
        help="Maximum energy storage capacity. Typical range: 1-10000 kWh"
        )

        st.markdown("**Max Charge Rate (C-Rate)**")
        max_c = st.number_input(
        "Enter max charge rate (C-rate)",
        min_value=0.0,
        max_value=5.0,
        value=float(st.session_state.electrical_storage.get("max_c", 0.5)),
        placeholder="e.g. 0.5",
        key="max_c",
        help="C-rate: 1C means full charge/discharge in 1 hour. Typical range: 0.1-2.0"
        )
        
        # Real-time validation
        st.markdown("---")
        st.markdown("**📋 Input Validation**")
        
        # Validate all inputs
        validation_results = []
        validation_results.extend([
            InputValidator.validate_efficiency(charging_efficiency, "Charging Efficiency"),
            InputValidator.validate_efficiency(discharging_efficiency, "Discharging Efficiency"),
            InputValidator.validate_power_rating(max_power, "Max Power", max_reasonable=5000),
            InputValidator.validate_positive_number(max_capacity, "Max Capacity", allow_zero=False),
            InputValidator.validate_numeric_range(max_c, 0.01, 5.0, "Max Charge Rate (C-rate)")
        ])
        
        # Additional custom validations
        if max_power > 0 and max_capacity > 0:
            power_to_capacity_ratio = max_power / max_capacity
            if power_to_capacity_ratio > 2.0:
                validation_results.append((True, f"⚠️ High power-to-capacity ratio ({power_to_capacity_ratio:.2f}). This indicates a high-power, short-duration storage system."))
            elif power_to_capacity_ratio < 0.1:
                validation_results.append((True, f"⚠️ Low power-to-capacity ratio ({power_to_capacity_ratio:.2f}). This indicates a low-power, long-duration storage system."))
        
        # Display validation results
        all_inputs_valid = display_validation_results(validation_results, show_success=False)
        
        # Submit button with validation
        if st.button("Submit Settings", key="submit_electrical_storage_settings"):
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
                st.success("✅ Electrical Storage settings updated successfully!")
                
                # Show calculated metrics
                with st.expander("📊 **Calculated Storage Metrics**"):
                    st.metric("Round-trip Efficiency", f"{(charging_efficiency * discharging_efficiency / 100):.1f}%")
                    if max_capacity > 0:
                        st.metric("Power-to-Energy Ratio", f"{max_power/max_capacity:.2f} kW/kWh")
                        st.metric("Full Charge Time at Max Power", f"{max_capacity/max_power:.1f} hours")
                    
            else:
                st.error("❌ Please correct the validation errors above before submitting.")
        
        # Show input tips
        with st.expander("💡 **Input Guidelines**"):
            st.markdown("""
            **Charging/Discharging Efficiency**: 
            - Lithium-ion batteries: 90-98%
            - Lead-acid batteries: 80-90%
            - Flow batteries: 70-85%
            
            **Max Power Rating**:
            - Residential systems: 1-20 kW
            - Commercial systems: 20-500 kW
            - Utility-scale systems: 500+ kW
            
            **Max Capacity**:
            - Residential systems: 5-100 kWh
            - Commercial systems: 100-10,000 kWh
            - Utility-scale systems: 10+ MWh
            
            **C-Rate Guidelines**:
            - 0.1C: Slow charging (10 hours to full)
            - 0.5C: Standard charging (2 hours to full)
            - 1C: Fast charging (1 hour to full)
            - 2C+: Rapid charging (< 30 minutes to full)
            """)
    
    # Display stored settings with improved formatting
    if "electrical_storage" in st.session_state:
        st.markdown("---")
        st.header("📊 Current Electrical Storage Configuration")
        
        # Create enhanced display
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Charging Efficiency", 
                f"{st.session_state.electrical_storage['Charge Efficiency']*100:.1f}%",
                help="Energy efficiency when charging the battery"
            )
            st.metric(
                "Max Power", 
                f"{st.session_state.electrical_storage['Max Power']:.1f} kW",
                help="Maximum power for charging/discharging"
            )
            st.metric(
                "C-Rate", 
                f"{st.session_state.electrical_storage['max_c']:.2f}",
                help="Maximum charge/discharge rate"
            )
        
        with col2:
            st.metric(
                "Discharging Efficiency", 
                f"{st.session_state.electrical_storage['Discharge Efficiency']*100:.1f}%",
                help="Energy efficiency when discharging the battery"
            )
            st.metric(
                "Max Capacity", 
                f"{st.session_state.electrical_storage['Max Capacity']:.1f} kWh",
                help="Maximum energy storage capacity"
            )
            
            # Calculate and display round-trip efficiency
            round_trip_eff = (st.session_state.electrical_storage['Charge Efficiency'] * 
                             st.session_state.electrical_storage['Discharge Efficiency'] * 100)
            st.metric(
                "Round-trip Efficiency", 
                f"{round_trip_eff:.1f}%",
                help="Overall efficiency for charge-discharge cycle"
            )

        # Create DataFrame for table
        data = {
            "Metric": [
                "Charge Efficiency",
                "Discharge Efficiency",
                "Max Power",
                "Max Capacity",
                "max_c"
            ],
            "Value": [
                st.session_state.electrical_storage["Charge Efficiency"],
                st.session_state.electrical_storage["Discharge Efficiency"],
                st.session_state.electrical_storage["Max Power"],
                st.session_state.electrical_storage["Max Capacity"],
                st.session_state.electrical_storage["max_c"]
            ],
            "Unit": [",", ",", "kW", "kWh","."]
        }
        df = pd.DataFrame(data)

        # Display table
        st.subheader("Electrical Storage Settings Table")
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