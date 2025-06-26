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

from mastr_preprocessing import fetch_storage, df_to_gdf, add_centroids,read_storage_units
#from mastr_preprocessing import pick_pvsystem_mastr, prepare_time_series_mastr, aggregate_time_series

import pvlib
from vpplib import Environment, Photovoltaic
import logging
#location = 'Troisdorf'
location = 'Essen'

"""
This code prepares storage data for a specified location, fetching thermal energy storage data,
converting it to a GeoDataFrame, and adding centroids for geographical reference.
It also sets up an environment for energy storage analysis.
It includes error handling to manage exceptions during data preparation.

"""


def prepare_storage_data(location='Essen', start_storage="2015-07-07 00:00:00", end_storage="2015-07-07 23:45:00"):
    
    try:
            df_storage = fetch_storage(Ort=location)
            df_storage_units = read_storage_units()
            gdf_storage = df_to_gdf(df_storage)
            gdf_storage = add_centroids(gdf_storage)
            gdf_storage.explore()
            
            city_district = ox.geocode_to_gdf([location])

            
            return gdf_storage, city_district
    except Exception as e:
            raise Exception(f"Error preparing data for {location}: {str(e)}")
        
        

if __name__ == "__main__":
    gdf_storage, city_district = prepare_storage_data()