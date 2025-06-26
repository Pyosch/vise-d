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

from mastr_preprocessing import fetch_solar, df_to_gdf, add_centroids
#from mastr_preprocessing import pick_pvsystem_mastr, prepare_time_series_mastr, aggregate_time_series

import pvlib
from vpplib import Environment, Photovoltaic
import logging
location = 'Troisdorf'
#location = 'Essen'


'''

This code prepares solar data for a specified location, fetching solar power generation data, 
converting it to a GeoDataFrame, and adding centroids for geographical reference. 
It also sets up an environment for photovoltaic data analysis.

'''
def prepare_solar_data(location='Essen', start_pv="2015-07-07 00:00:00", end_pv="2015-07-07 23:45:00"):
    

    try:
            df_solar = fetch_solar(Ort=location)
            gdf_solar = df_to_gdf(df_solar)
            gdf_solar = add_centroids(gdf_solar)
            
            city_district = ox.geocode_to_gdf([location])
            
        #     ref_env = Environment(start=start_pv, end=end_pv)
        #     ref_env.get_dwd_pv_data(lat=city_district.centroid.y, 
        #                             lon=city_district.centroid.x)
            
            # Commenting out revise_power_values since it's undefined
            # If it exists in your setup, uncomment and ensure it's accessible
            # gdf_solar = revise_power_values(gdf_solar)
            
            return gdf_solar, city_district
    except Exception as e:
            
            
            raise Exception(f"Error preparing data for {location}: {str(e)}")





if __name__ == "__main__":
    gdf_solar, city_district = prepare_solar_data()