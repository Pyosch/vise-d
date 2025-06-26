#%%
import random
import math
import numpy as np
import geopandas as gpd
import osmnx as ox
import plotly.express as px
import matplotlib.pyplot as plt
from tqdm import tqdm
import pickle

from mastr_preprocessing import fetch_wind, df_to_gdf, add_centroids
#from mastr_preprocessing import pick_pvsystem_mastr, prepare_time_series_mastr, aggregate_time_series

import pvlib
from vpplib import Environment, Photovoltaic
import logging
location = 'Riepsdorf'
#location = 'Essen'

df_wind = fetch_wind(Ort=location)
gdf_wind = df_to_gdf(df_wind)
#gdf_wind = add_centroids(gdf_wind)

city_district = ox.geocode_to_gdf([location])

start_wind = "2015-07-07 00:00:00"
end_wind = "2015-07-07 23:45:00"

# ref_env = Environment(start=start_wind, end=end_wind)
# ref_env.get_dwd_wind_data(lat=city_district.centroid.y, 
#                         lon=city_district.centroid.x)

'''
This code prepares wind data for a specified location, fetching wind power generation data, 
converting it to a GeoDataFrame, and adding centroids for spatial analysis.
It also sets up an environment for wind data analysis.
It includes error handling to manage exceptions during data preparation.

'''


def prepare_wind_data(location=location, start_wind="2015-07-07 00:00:00", end_wind="2015-07-07 23:45:00"):
    
    try:
            df_wind = fetch_wind(Ort=location)
            gdf_wind = df_to_gdf(df_wind)
            gdf_wind = add_centroids(gdf_wind)
            
            city_district = ox.geocode_to_gdf([location])
            city_district.set_index('name', inplace=True)
            
            ref_env = Environment(start=start_wind, end=end_wind)
            ref_env.get_dwd_wind_data(lat=city_district.centroid.y, 
                                    lon=city_district.centroid.x)
            
            return gdf_wind, city_district
    except Exception as e:
            raise Exception(f"Error preparing data for {location}: {str(e)}")
        
        

if __name__ == "__main__":
    gdf_wind, city_district = prepare_wind_data()