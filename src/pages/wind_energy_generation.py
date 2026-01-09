"""
Wind energy generation simulation page.

Simulates wind energy generation using MaStR data and vpplib/windpowerlib models.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import pvlib
from vpplib.environment import Environment
from src.mastr.preprocessing import get_unique_wind_locations, prepare_wind_data
from src.mastr.simulation import (
    wind_turbine_matching,
    init_windturbines_mastr,
    prepare_wind_time_series_mastr
)
from src.config import MASTR_DB_PATH


def wind_energy_generation() -> None:
    """Simulate and visualize wind energy generation from MaStR installations."""
    st.title("Energy Generation from Wind Installations")
    
    # Fetch unique locations for dropdown
    unique_locations = get_unique_wind_locations(mastr_db_path=str(MASTR_DB_PATH))

    # Dropdown for location selection
    location = st.selectbox("Select city", options=unique_locations, index=unique_locations.index("Essen") if "Essen" in unique_locations else 0)
    
    if location:
        if st.button("Simulate Energy Generation"):
            with st.spinner("Preparing and simulating Wind systems..."):
                try:
                    start = "2015-07-07 00:00:00"
                    end = "2015-07-07 23:45:00"
                    ref_env = Environment(start=start, end=end)
                    gdf_wind, city_district = prepare_wind_data(location=location, mastr_db_path=str(MASTR_DB_PATH))
                    gdf_wind = wind_turbine_matching(gdf_wind)
                    test_data, meta, inputs = pvlib.iotools.get_pvgis_hourly(city_district.centroid.y, 
                                                         city_district.centroid.x, 
                                                         start=pd.to_datetime(start), 
                                                         end=pd.to_datetime(end), 
                                                         raddatabase='PVGIS-SARAH2', 
                                                         components=True, 
                                                         surface_tilt= 0, 
                                                         surface_azimuth= 0, 
                                                         outputformat='json', 
                                                         usehorizon=True, 
                                                         userhorizon=None, 
                                                         pvcalculation=False, 
                                                         peakpower=None, 
                                                         pvtechchoice='crystSi', 
                                                         mountingplace='free', 
                                                         loss=0, 
                                                         trackingtype=0, 
                                                         optimal_surface_tilt=False, 
                                                         optimalangles=False, 
                                                         url='https://re.jrc.ec.europa.eu/api/v5_2/', 
                                                         map_variables=True, 
                                                         timeout=30)
                    filtered_data_wind = test_data[['wind_speed', 'temp_air']]
                    filtered_data_wind['temp_air'] = filtered_data_wind['temp_air'] + 273.15 # in Kelvin
                    filtered_data_wind['roughness_length'] = [0.15 for i in range (8760)]
                    filtered_data_wind['pressure'] = [101325 for i in range (8760)]
                    new_order = ['wind_speed', 'pressure', 'temp_air', 'roughness_length']
                    filtered_data_wind = filtered_data_wind.reindex(columns=new_order)
                    filtered_data_wind = filtered_data_wind.rename(columns={"temp_air": "temperature"})
                    filtered_data_wind.columns = [filtered_data_wind.columns, ['10', '0', '2', '0']]
                    test_data_15min_w = filtered_data_wind.resample('15T').mean().interpolate()
                    
                    ref_env.wind_data = test_data_15min_w
    
                    windturbines_dict = init_windturbines_mastr(gdf_wind, environment=ref_env)
                    prepare_wind_time_series_mastr(windturbines_dict)
                    
                    # Plot simulation results
                    fig, ax = plt.subplots(figsize=(10, 6))
                    for name, windturbine in windturbines_dict.items():

                        try:
                            ax.plot(windturbine.timeseries, label=name)
                        except Exception as plot_error:
                            st.error(f"Failed to plot {name}: {plot_error}")

                    ax.set_title("Wind Power Generation")
                    ax.set_xlabel("Time")
                    ax.set_ylabel("Power (kW)")
                    ax.legend(title='Wind Turbines')
                    plt.tight_layout()
                    st.pyplot(fig)

                except Exception as e:
                    st.error(f"Simulation failed: {e}")
