#%%
import pandas as pd
import geopandas as gpd
import osmnx as ox
import logging
from thefuzz import fuzz, process
import plotly.express as px

import windpowerlib as wpl
import pvlib
from vpplib import UserProfile, Environment, WindPower

from mastr_preprocessing import fetch_wind, df_to_gdf

logging.basicConfig(level=logging.INFO)

location = ['Jüchen']
start = "2015-07-07 00:00:00"
end = "2015-07-07 23:45:00"

city_district = ox.geocode_to_gdf(location)
df_wind = fetch_wind(Ort=location)
gdf_wind = df_to_gdf(df_wind)

# gdf_wind.explore()

ref_env = Environment(start=start, end=end)
# ref_env.get_dwd_wind_data(lat=city_district.centroid.y,
#                           lon=city_district.centroid.x)

test_data, meta, inputs = pvlib.iotools.get_pvgis_hourly(city_district.centroid.y, 
                                                         city_district.centroid.x, 
                                                         start=2015, 
                                                         end=2015, 
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

#%%

def wind_turbine_matching(gdf):
    
    wind_turbine_mapping = {}
    
    turbine_database = wpl.data.store_turbine_data_from_oedb()
    
    for mastr_turbine in gdf['Typenbezeichnung']:
        best_match = None
        closest_match = -1
        
        for index, row in turbine_database.iterrows():
            aktuelle_ähnlichkeit_turbine_type = 0
            aktuelle_ähnlichkeit_name = 0
            
            if pd.notnull(row["turbine_type"]):
                aktuelle_ähnlichkeit_turbine_type = fuzz.ratio(mastr_turbine, row["turbine_type"])
            if pd.notnull(row["name"]):
                aktuelle_ähnlichkeit_name = fuzz.ratio(mastr_turbine, row["name"])
            
            if aktuelle_ähnlichkeit_turbine_type == 0 or aktuelle_ähnlichkeit_name == 0:
                aktuelle_ähnlichkeit = (aktuelle_ähnlichkeit_turbine_type + aktuelle_ähnlichkeit_name)
            else:
                aktuelle_ähnlichkeit = (aktuelle_ähnlichkeit_turbine_type + aktuelle_ähnlichkeit_name)/2
            
            if aktuelle_ähnlichkeit > closest_match:
                closest_match = aktuelle_ähnlichkeit
                best_match = row["turbine_type"]
        
        wind_turbine_mapping[mastr_turbine] = best_match
        
    print(wind_turbine_mapping)
    
    return gdf.assign(WPLTurbine=gdf['Typenbezeichnung'].map(wind_turbine_mapping))

gdf_wind = wind_turbine_matching(gdf_wind)

#%% Create dict with windturbines
#ToDo: Adjust to new vpplib sturcture once completed
def init_windturbines_mastr(gdf,
                            wind_speed_model = "logarithmic",
                            density_model = "ideal_gas",
                            temperature_model = "linear_gradient",
                            power_output_model = "power_curve", # "power_coefficient_curve"or 'power_curve'
                            density_correction = True,
                            obstacle_height = 0,
                            hellman_exp = None):
    
    windturbines_dict = {}
    
    for i in gdf.index:
        windturbines_dict[gdf.loc[i, 'EinheitMastrNummer']] = WindPower(
            unit="kW",
            identifier=gdf.loc[i, 'EinheitMastrNummer'],
            environment=ref_env,
            # user_profile=UserProfile(identifier=gdf.loc[i, 'EinheitMastrNummer'], 
            #                         latitude=gdf.loc[i, 'Breitengrad'],
            #                         longitude=gdf.loc[i, 'Laengengrad'],
            #                         ),
            turbine_type=gdf.loc[i, 'WPLTurbine'],
            hub_height=gdf.loc[i, 'Nabenhoehe'],
            rotor_diameter=gdf.loc[i, 'Rotordurchmesser'],
            fetch_curve="power_curve",
            data_source="oedb",
            wind_speed_model=wind_speed_model,
            density_model=density_model,
            temperature_model=temperature_model,
            power_output_model=power_output_model,
            density_correction=density_correction,
            obstacle_height=obstacle_height,
            hellman_exp=hellman_exp,
            )
        
    return windturbines_dict
    
windturbines_dict = init_windturbines_mastr(gdf_wind)

#%% Create time series for wind power generation

def prepare_time_series_mastr(gen_dict):
        
        for key, value in gen_dict.items():
            value.prepare_time_series()

prepare_time_series_mastr(windturbines_dict)
#%% aggregate time series

def aggregate_time_series(gen_dict):
    
    time_series = pd.DataFrame()
    
    for key, value in gen_dict.items():
        if time_series.empty:
            time_series = value.timeseries
        else:
            time_series = time_series.add(value.timeseries, fill_value=0)
    
    return time_series

aggregated_time_series = aggregate_time_series(windturbines_dict)

print(aggregated_time_series.head())

#%%
fig = px.line(pd.DataFrame({key: windturbines_dict[key].timeseries for key in windturbines_dict.keys()}), 
        title="Wind Power Generation", 
        labels={"index": "Time", "value": "Power [kW]"})

fig.show()

#%%
# city_district = ox.geocode_to_gdf(['Jüchen', 'Bedburg', 'Erkelenz', 'Titz'])
# city_district.explore()

# city_district.explore(column='name', colormap='viridis', legend=True)
# %%
