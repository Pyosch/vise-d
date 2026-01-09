"""
Thermal storage settings and simulation page.

Provides configuration form and simulation for thermal energy storage systems.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from vpplib.environment import Environment
from vpplib.thermal_energy_storage import ThermalEnergyStorage
from vpplib.heating_rod import HeatingRod


def thermal_storage_settings() -> None:
    """Configure and simulate thermal energy storage system."""
    if "thermal_storage_settings" not in st.session_state:
        # Calculate initial state of charge based on current temperature
        # Energy = mass * cp * temperature (convert from kJ to kWh: divide by 3600)
        initial_current_temp = 50  # 50°C starting temperature
        initial_mass = 300  # 300 kg
        initial_cp = 4.18  # 4.18 kJ/kg°C
        initial_soc = (initial_mass * initial_cp * (initial_current_temp + 273.15)) / 3600  # kWh
        
        st.session_state["thermal_storage_settings"]={
            "target temperature": 60,  # 60°C for domestic hot water
            "minimum temperature": 40,  # 40°C minimum usable temperature
            "Current Temperature": initial_current_temp,  # 50°C starting temperature
            "hysteresis": 5,  # 5°C control band
            "mass": initial_mass,  # 300 kg (typical 300L water tank)
            "cp": initial_cp,  # 4.18 kJ/kg°C (specific heat of water)
            "thermal energy loss per day": 2.5,  # 2.5 kWh/day (well-insulated tank)
            "State of Charge": initial_soc,  # Calculated based on current temperature
            "start_time": 6,  # 6:00 - morning heating start
            "end_time": 22,  # 22:00 - evening heating end
            "frequency": 50,  # 50 Hz (Germany)
            "timebase_minutes": 15  # 15 minutes (consistent with other components)
    
        }
    st.title("Thermal Storage Configuarations")
    
    with st.container():
        st.header("Thermal Storage Settings")
        
        st.markdown("**Target Temperature**")
        target_temperature = st.number_input(
                "Enter target temperature (°C)",
                min_value=0.0,
                value=float(st.session_state["thermal_storage_settings"]["target temperature"]),
                placeholder="e.g. 20 °C",
                key="target_temperature"
            )
        
        st.markdown("**Minimum Temperature**")
        minimum_temperature = st.number_input(
                "Enter minimum temperature (°C)",
                min_value=0.0,
                value=float(st.session_state["thermal_storage_settings"]["minimum temperature"]),
                placeholder="e.g. 15 °C",
                key="minimum_temperature"
            )
        
        st.markdown("**Hysteresis**")
        hysteresis = st.number_input(
                "Enter hysteresis (°C)",
                min_value=0.0,
                value=float(st.session_state["thermal_storage_settings"]["hysteresis"]),
                placeholder="e.g. 5 °C",
                key="hysteresis"
            )
        
        st.markdown("**Current Temperature**")
        current_temperature = st.number_input(
            "Enter current temperature (°C)",
            min_value=0.0,
            value = float(target_temperature - hysteresis),
            placeholder="e.g. 20 °C",
            key="current_temperature"
        )

        st.markdown("**Mass**")
        mass = st.number_input(
                "Enter mass (kg)",
                min_value=0.0,
                value=float(st.session_state["thermal_storage_settings"]["mass"]),
                placeholder="e.g. 100 kg",
                key="mass"
            )
        
        st.markdown("**Specific Heat Capacity**")
        cp = st.number_input(
                "Enter specific heat capacity (kJ/kg°C)",
                min_value=0.0,
                value=float(st.session_state["thermal_storage_settings"]["cp"]),
                placeholder="e.g. 4.18 kJ/kg°C",
                key="cp"
            )
        st.markdown("**State of Charge**")
        
        # Calculate initial state of charge in joules and convert to kWh
        initial_state_of_charge = mass * cp * (current_temperature + 273.15) / 3.6e6   # J to kWh
        state_of_charge = st.number_input(
        "Enter state of charge (kWh)",
        min_value=0.0,
        value=initial_state_of_charge,
        placeholder="e.g. 100 kWh",
        key="state_of_charge"
        )
        st.markdown("**Thermal Energy Loss per Day**")
        thermal_energy_loss_per_day = st.number_input(
                "Enter thermal energy loss per day (kWh)",
                min_value=0.0,
                value=float(st.session_state["thermal_storage_settings"]["thermal energy loss per day"]),
                placeholder="e.g. 10 kWh",
                key="thermal_energy_loss_per_day"
            )
        
        
        st.markdown("**Start Time**")
        start_time = st.number_input(
                "Enter start time (HH:MM)",
                value=0,
                placeholder="e.g. 08:00",
                key="start_time"
            )
        
        st.markdown("**End Time**")
        end_time = st.number_input(
                "Enter end time (HH:MM)",
                value=0,
                placeholder="e.g. 18:00",
                key="end_time"
            )
        
        st.markdown("**Frequency**")
        frequency = st.number_input(
                "Enter frequency (Hz)",
                min_value=0.0,
                value=float(st.session_state["thermal_storage_settings"]["frequency"]),
                placeholder="e.g. 50 Hz",
                key="frequency"
            )
        
        st.markdown("**Timebase Minutes**")
        timebase_minutes = st.number_input(
                "Enter timebase minutes",
                min_value=0.0,
                value=float(st.session_state["thermal_storage_settings"]["timebase_minutes"]),
                placeholder="e.g. 15 minutes",
                key="timebase_minutes"
            )
        if st.button("Submit Settings", key="submit_thermal_storage_settings"):
            st.session_state["thermal_storage_settings"] = {
                "target temperature": target_temperature,
                "minimum temperature": minimum_temperature,
                "Current Temperature": current_temperature,
                "hysteresis": hysteresis,
                "mass": mass,
                "cp": cp,
                "thermal energy loss per day": thermal_energy_loss_per_day,
                "State of Charge": state_of_charge,
                "start_time": start_time,
                "end_time": end_time,
                "frequency": frequency,
                "timebase_minutes": timebase_minutes
            }
            st.success("Thermal Storage settings updated successfully!")
    
    # Display stored settings table
    if "thermal_storage_settings" in st.session_state:
        # Create DataFrame for table
        data = {
            "Metric": [
                "Target Temperature",
                "Minimum Temperature",
                "Current Temperature",
                "Hysteresis",
                "Mass",
                "Specific Heat Capacity",
                "Thermal Energy Loss per Day",
                "State of Charge",
                "Start Time",
                "End Time",
                "Frequency",
                "Timebase Minutes"
            ],
            "Value": [
                st.session_state["thermal_storage_settings"]["target temperature"],
                st.session_state["thermal_storage_settings"]["minimum temperature"],
                st.session_state["thermal_storage_settings"]["Current Temperature"],
                st.session_state["thermal_storage_settings"]["hysteresis"],
                st.session_state["thermal_storage_settings"]["mass"],
                st.session_state["thermal_storage_settings"]["cp"],
                st.session_state["thermal_storage_settings"]["thermal energy loss per day"],
                st.session_state["thermal_storage_settings"]["State of Charge"],
                st.session_state["thermal_storage_settings"]["start_time"],
                st.session_state["thermal_storage_settings"]["end_time"],
                st.session_state["thermal_storage_settings"]["frequency"],
                st.session_state["thermal_storage_settings"]["timebase_minutes"]
            ]
            
        }
        
        df = pd.DataFrame(data)
        # Define numeric metrics for formatting
        numeric_metrics = ["Target Temperature", "Minimum Temperature", "Current Temperature", "Hysteresis", "Mass", "Specific Heat Capacity", "Thermal Energy Loss per Day", "State of Charge"]
        # Pre-format the 'Value' column
        df['Value'] = df.apply(
            lambda row: f"{float(row['Value']):.1f}" if row['Metric'] in numeric_metrics else str(row['Value']),
            axis=1
        )
        # Display table
        st.subheader("Thermal Storage Settings Table")
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
    
    # Simulation section (placed after settings table)
    with st.form(key="thermal_storage_simulation_form"):
        thermal_simulation_button = st.form_submit_button("Simulate Thermal Storage")
        
        if thermal_simulation_button:
            start = "2024-06-01 00:00:00"
            end = "2024-06-07 23:45:00"
            timebase = int(st.session_state["thermal_storage_settings"]["timebase_minutes"])
            env = Environment(start=start, end=end, timebase=timebase)
            
            # Create synthetic thermal demand profile for hot water usage
            # Higher demand in morning (6-9) and evening (18-22), lower at night
            time_index = pd.date_range(start=start, end=end, freq=f"{timebase}min")
            thermal_demand = []
            
            for timestamp in time_index:
                hour = timestamp.hour
                # Peak demand: 6-9 AM (morning shower) and 18-22 PM (evening usage)
                if 6 <= hour < 9:
                    base_demand = 2.5  # kW during morning peak
                elif 18 <= hour < 22:
                    base_demand = 2.0  # kW during evening peak
                elif 22 <= hour < 24 or 0 <= hour < 6:
                    base_demand = 0.3  # kW overnight (minimal demand)
                else:
                    base_demand = 0.8  # kW during day (moderate demand)
                
                # Add some random variation (±20%)
                demand = base_demand * (1 + 0.2 * (np.random.random() - 0.5))
                thermal_demand.append(max(0, demand))  # Ensure non-negative
            
            thermal_demand_series = pd.Series(thermal_demand, index=time_index, name="thermal_demand")
            
            # Initialize HeatingRod with thermal demand profile and ramp parameters
            heating_rod = HeatingRod(
                thermal_energy_demand=thermal_demand_series,
                unit="kW",
                identifier="heating_rod_1",
                environment=env,
                el_power=5.0,  # 5 kW electric heating element
                rampUpTime=1/15,  # 1 timestep to ramp up
                rampDownTime=1/15,  # 1 timestep to ramp down
                min_runtime=1,  # Minimum 1 timestep runtime
                min_stop_time=2,  # Minimum 2 timesteps stop time
                efficiency=0.95
            )
            
            # Initialize ThermalEnergyStorage with form inputs
            st.session_state["thermal_storage"] = ThermalEnergyStorage(
                unit="kW",
                identifier="thermal_storage_1",
                environment=env,
                target_temperature=st.session_state["thermal_storage_settings"]["target temperature"],
                min_temperature=st.session_state["thermal_storage_settings"]["minimum temperature"],
                hysteresis=st.session_state["thermal_storage_settings"]["hysteresis"],
                mass=st.session_state["thermal_storage_settings"]["mass"],
                cp=st.session_state["thermal_storage_settings"]["cp"],
                thermal_energy_loss_per_day=st.session_state["thermal_storage_settings"]["thermal energy loss per day"]
            )
            
            # Set initial temperature
            st.session_state["thermal_storage"].current_temperature = st.session_state["thermal_storage_settings"]["Current Temperature"]
            
            # Add snake_case method aliases to HeatingRod for compatibility with ThermalEnergyStorage
            if not hasattr(heating_rod, 'ramp_up'):
                heating_rod.ramp_up = heating_rod.rampUp
            if not hasattr(heating_rod, 'ramp_down'):
                heating_rod.ramp_down = heating_rod.rampDown
            
            # Connect heating rod to thermal storage
            heating_rod.thermal_energy_storage = st.session_state["thermal_storage"]
            
            # Prepare time series for both components
            heating_rod.prepare_time_series()
            st.session_state["thermal_storage"].prepare_time_series()
            
            # Simulate timestep-by-timestep (following vpplib example pattern)
            st.info("⏳ Simulating thermal storage operation over 1 week...")
            progress_bar = st.progress(0)
            
            # Get time index from thermal storage (which should be a DataFrame)
            if hasattr(st.session_state["thermal_storage"].timeseries, 'index'):
                time_index = st.session_state["thermal_storage"].timeseries.index
            else:
                # Fallback to environment time index
                time_index = time_index  # Use the time_index we created earlier
            
            total_steps = len(time_index)
            
            for idx, timestamp in enumerate(time_index):
                st.session_state["thermal_storage"].operate_storage(timestamp, heating_rod)
                # Update progress every 50 timesteps to avoid slowdown
                if idx % 50 == 0:
                    progress_bar.progress(idx / total_steps)
            
            progress_bar.progress(1.0)
            st.success("✅ Simulation completed!")
            
            # Display results
            st.write("**Thermal Storage Temperature (First 10 timesteps):**")
            st.dataframe(st.session_state["thermal_storage"].timeseries.head(10))
            
            st.write("**Heating Rod Electrical Demand (First 10 timesteps):**")
            if hasattr(heating_rod.timeseries, 'el_demand'):
                st.dataframe(heating_rod.timeseries[['el_demand']].head(10))
            else:
                st.dataframe(heating_rod.timeseries.head(10))
            
            # Plot thermal storage temperature
            fig_temp, ax_temp = plt.subplots(figsize=(16, 6))
            st.session_state["thermal_storage"].timeseries.plot(ax=ax_temp, color='red')
            ax_temp.axhline(y=st.session_state["thermal_storage_settings"]["target temperature"], 
                           color='green', linestyle='--', label='Target Temperature')
            ax_temp.axhline(y=st.session_state["thermal_storage_settings"]["minimum temperature"], 
                           color='blue', linestyle='--', label='Minimum Temperature')
            ax_temp.set_title("Thermal Storage Temperature Over Time")
            ax_temp.set_xlabel("Time")
            ax_temp.set_ylabel("Temperature (°C)")
            ax_temp.legend()
            ax_temp.grid(True, alpha=0.3)
            plt.tight_layout()
            st.pyplot(fig_temp)
            
            # Plot heating rod electrical demand
            fig_demand, ax_demand = plt.subplots(figsize=(16, 6))
            if hasattr(heating_rod.timeseries, 'el_demand'):
                heating_rod.timeseries['el_demand'].plot(ax=ax_demand, color='orange')
            else:
                heating_rod.timeseries.plot(ax=ax_demand, color='orange')
            ax_demand.set_title("Heating Rod Electrical Demand")
            ax_demand.set_xlabel("Time")
            ax_demand.set_ylabel("Electrical Power (kW)")
            ax_demand.grid(True, alpha=0.3)
            plt.tight_layout()
            st.pyplot(fig_demand)
