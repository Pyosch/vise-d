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

from mastr_preprocessing import fetch_solar, df_to_gdf, add_centroids, revise_power_values
from mastr_preprocessing import pick_pvsystem_mastr, prepare_time_series_mastr, aggregate_time_series
from private import mapbox_token

import pvlib
from vpplib import Environment, Photovoltaic
import logging
px.set_mapbox_access_token(mapbox_token)
location = 'Troisdorf'

df_solar = fetch_solar(Ort=location)
gdf_solar = df_to_gdf(df_solar)
gdf_solar = add_centroids(gdf_solar)

city_district = ox.geocode_to_gdf([location])

start_pv = "2015-07-07 00:00:00"
end_pv = "2015-07-07 23:45:00"

ref_env = Environment(start=start_pv, end=end_pv)
ref_env.get_dwd_pv_data(lat=city_district.centroid.y, 
                        lon=city_district.centroid.x)

# gdf_solar.explore()


#%%Plot map

city_district = ox.geocode_to_gdf([location])
city_district.set_index('name', inplace=True)

fig = px.scatter_mapbox(gdf_solar,
                        lat='Breitengrad',
                        lon='Laengengrad',
                        # color='Bruttoleistung',
                        # size='Bruttoleistung',
                        size_max=15,
                        color_continuous_scale='Viridis',
                        zoom=10,
                        center={"lat": city_district.centroid[location].y,  
                                "lon": city_district.centroid[location].x},
                        mapbox_style='open-street-map',
                        # title='Solaranlagen in Troisdorf'
                        )

choropleth = px.choropleth_mapbox(city_district,
                                  geojson=city_district.geometry,
                                  locations=city_district.index,
                                  color=None,
                                  opacity=0.3,
                                  labels={location: 'City District'},
                                 )

fig.add_trace(choropleth.data[0])

# Move the choropleth trace to the background
fig.data = fig.data[::-1]

fig.update_layout(
    margin={"r":0,"t":0,"l":0,"b":0},
    # legend=dict(
    #     yanchor="top",
    #     y=1.1,
    #     xanchor="left",
    #     x=0.01,
        # title="City District"
    # )
)
fig.show()

gdf_solar = revise_power_values(gdf_solar)

# %% Create PV systems

# pv_systems_dict = pick_pvsystem_mastr(gdf_solar.head(1000), ref_env)

# pickle.dump(pv_systems_dict, open('pv_systems_dict.pkl', 'wb'))

#%% Prepare time series

# pv_systems_dict = pickle.load(open('pv_systems_dict.pkl', 'rb'))
            

# prepare_time_series_mastr(pv_systems_dict)

#%% Aggregate time series

# pv_systems_aggregated = aggregate_time_series(pv_systems_dict)

#%% Plot time series
# fig, ax = plt.subplots()
# for name, pv_system in pv_systems_aggregated.items():
#     pv_system.plot(ax=ax, label=name)

# plt.show()
# %%
