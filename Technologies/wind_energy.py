import datetime
import streamlit as st
from st_files_connection import FilesConnection
import os

from src.visualization import fig_5, fig_7, fig_8, fig_9, fig_5_plotly
from src.network import pp_networks
import matplotlib.pyplot as plt
from vpplib.environment import Environment
import pandas as pd

def wind(form_key_suffix=""):
    if "wind_settings" not in st.session_state:
        st.session_state.wind_settings = {
            "Turbine Type": "E-140",
            "Hub Height" : 0,
            "Rotor Diameter" : 0,
            # "Comfort Factor": 0,
            "Data Source": "Wind Turbines",
            "Wind Speed Model": "logarithmic",
            "Density Model" : "Barometric",
            "Temperature Model" : "Linear Gradient",
            "power_output_model": "power_curve",
            "Density Correction": False,
            "Obstacle Height": 0.0,
            "hellman_exp": 0.2
            
        }
        
    with st.sidebar:
        st.header("Wind Turbine Settings")
        
        turbine_type = st.selectbox(
            "Turbine Type",
            options=["E-140/4200", "E-141/4200","E-126/4200"],
            index=0 if "Turbine Type"=="E-140/4200" else 1 if "Turbine Type"=="E-141/4200" else 2,
            key="Turbine Type"
        )
        
        hub_height= st.number_input(
            "Hub Height",
            min_value = 0,
            max_value = 500,
            value = int(st.session_state.wind_settings["Hub Height"]),
            step = 1
        )
        
        rotor_diameter = st.number_input(
            "Rotor Diameter",
            min_value = 0,
            max_value = 500,
            value = int(st.session_state.wind_settings["Rotor Diameter"]),
            step = 1
        )
        
        # comfort_factor = st.number_input(
        #     "Comfort Factor",
        #     min_value = 0.0,
        #     max_value = 1.0,
        #     value = float(st.session_state.wind_settings["Comfort Factor"]),
        #     step = 1.0
        # )  
        
        data_source= st.selectbox(
            "Wind Turbines",
            "oedb",
            index = 0,
            key = "Data Sources"
        )
        
        wind_speed_model = st.selectbox(
            "Wind Speed Model",
            options = ["logarithmic","hellmann","interpolation_extrapolation"],
            index = 0 if "Wind Speed Model"=="logarithmic" else 1 if "Wind Speed Model"=="hellmann" else 2,
            key = "Wind Speed Model"
        )
        
        density_model= st.selectbox(
            "Density Model",
            options = ['barometric', 'ideal_gas', 'interpolation_extrapolation'],
            index = 0 if "Density Model"=="barometric" else 1 if "Density Model" == "ideal_gas" else 2,
            key = "Density Model"
        )
        
        temperature_model= st.selectbox(
            "Temperature Model",
            options = ['linear_gradient', 'interpolation_extrapolation'],
            index = 0 if "Temperature Model" == "linear_gradient" else 1 ,
            key = "Temperature Model"
        )
        
        power_output_model= st.selectbox(
            "power_output_model",
            options = ['power_curve', 'power_coefficient_curve'],
            index = 0 if "power_output_model"=="power_curve" else 1,
            key = "power_output_model"
        )   
         
        density_correction= st.selectbox(
            "Density Correction",
            options = [True, False], 
            index = 0 if "Density Correction"==True else 1,
            key = "Density Correction"
            
        ) 
        
        obstacle_height= st.number_input(
            "Obstacle Height",
            min_value = 0.0,
            max_value = 100.0,
            value = float(st.session_state.wind_settings["Obstacle Height"]),
            step = 1.0
        )
        
        hellman_exp = st.number_input(
            "hellman_exp",
            min_value = 0.0,
            max_value = 1.0,
            value = float(st.session_state.wind_settings["hellman_exp"]),
            step = 1.0  
        )

        if st.button("Submit Settings", key="submit_wind_settings"):
            st.session_state.wind_settings = {
                "Turbine Type": turbine_type,
                "Hub Height": hub_height,
                "Rotor Diameter": rotor_diameter,
                # "Comfort Factor": comfort_factor,
                "Data Source": data_source,
                "Wind Speed Model": wind_speed_model,
                "Density Model": density_model,
                "Temperature Model": temperature_model,
                "power_output_model": power_output_model,
                "Density Correction": density_correction,
                "Obstacle Height": obstacle_height,
                "hellman_exp": hellman_exp
            }
            st.success("Wind settings updated successfully!")
            
    # Display stored settings
    if "wind_settings" in st.session_state:
        st.header("Current Wind Settings")
       # st.json(st.session_state.wind)
        # Create DataFrame for table
        data = {
            "Metric": [
                "Turbine Type",
                "Hub Height",
                "Rotor Diameter",
                # "Comfort Factor",
                "Data Source",
                "Wind Speed Model",
                "Density Model",
                "Temperature Model",
                "power_output_model",
                "Density Correction",
                "Obstacle Height",
                "hellman_exp"
            ],
            "Value": [
                st.session_state.wind_settings["Turbine Type"],
                st.session_state.wind_settings["Hub Height"],
                st.session_state.wind_settings["Rotor Diameter"],
                # st.session_state.wind_settings["Comfort Factor"],
                st.session_state.wind_settings["Data Source"],
                st.session_state.wind_settings["Wind Speed Model"],
                st.session_state.wind_settings["Density Model"],
                st.session_state.wind_settings["Temperature Model"],
                st.session_state.wind_settings["power_output_model"],
                st.session_state.wind_settings["Density Correction"],
                st.session_state.wind_settings["Obstacle Height"],
                st.session_state.wind_settings["hellman_exp"]
            ]
            
        }
        
        df = pd.DataFrame(data)
        
    # Define numeric metrics for formatting
    numeric_metrics = ["Hub Height", "Rotor Diameter", "Obstacle Height", "hellman_exp"] #"Comfort Factor",
    # Pre-format the 'Value' column
    df['Value'] = df.apply(
    lambda row: f"{float(row['Value']):.1f}" if row['Metric'] in numeric_metrics else str(row['Value']),
            axis=1
    )
        
            
    # Display table
    st.subheader("Wind Settings Table")
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
