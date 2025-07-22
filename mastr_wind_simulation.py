import pandas as pd
import geopandas as gpd
import osmnx as ox
import os
import logging
import plotly.express as px

from shapely.geometry import box
from windpowerlib import WindTurbine, ModelChain

from mastr_preprocessing import fetch_wind, df_to_gdf

logging.basicConfig(level=logging.INFO)

location = 'Bedburg'
longitude_min = 6.462683
longitude_max = 6.563602
latitude_min = 51.018799
latitude_max = 51.105300


city_district = ox.geocode_to_gdf(location)
df_wind = fetch_wind(longitude_min=longitude_min, latitude_min=latitude_min, longitude_max=longitude_max, latitude_max=latitude_max)
gdf_wind = df_to_gdf(df_wind)

print(df_wind)

# Bounding Box für den gewünschten Bereich als GeoDataFrame erstellen
bounding_box = gpd.GeoDataFrame(
    {"geometry": [box(longitude_min, latitude_min, longitude_max, latitude_max)]},
    crs="EPSG:4326"  # WGS 84 Koordinatensystem
)
# Scatter-Plot mit Solaranlagen
fig = px.scatter_mapbox(
    gdf_wind,
    lat="Breitengrad",
    lon="Laengengrad",
    size="Bruttoleistung",
    size_max=15,
    color_continuous_scale="Viridis",
    zoom=10,
    mapbox_style="open-street-map",
)

# Choropleth für den Bounding Box Bereich hinzufügen
choropleth = px.choropleth_mapbox(
    bounding_box,
    geojson=bounding_box.geometry,
    locations=bounding_box.index,
    color=None,
    opacity=0.3,
)
fig.add_trace(choropleth.data[0])  # Choropleth zur Karte hinzufügen
# Choropleth in den Hintergrund setzen
fig.data = fig.data[::-1]
fig.update_layout(
    margin={"r": 0, "t": 0, "l": 0, "b": 0},)
#fig.show()


# Wetterdaten einlesen
weather_data = pd.read_csv('weather_data/dwd_data_wind_10min_koeln_2020-2023.csv', sep=';', header=[0, 1], index_col=0, parse_dates=True)
start_pv = "2021-01-01 00:00:00"
end_pv = "2021-12-31 23:50:00"

weather_data = weather_data.loc[start_pv:end_pv]

print(weather_data)
# Normierte Leistungskennlinie einlesen
df_efficiency_curve = pd.read_csv('median_windpower_curve.csv')


def simulate_wind_farms(gdf_wind, weather_data, df_efficiency_curve):
    """
    Simuliert die Stromerzeugung für alle Windkraftanlagen im angegebenen GeoDataFrame.

    Parameters:
    - gdf_wind: GeoDataFrame mit Informationen zu den Windkraftanlagen.
    - weather_data: DataFrame mit Wetterdaten.
    - df_efficiency_curve: DataFrame mit der normierten Leistungskennlinie.

    Returns:
    - DataFrame mit simulierten Leistungen jeder Windkraftanlage.
    """
    # DataFrame zum Speichern der Ergebnisse erstellen
    wind_gen_results = pd.DataFrame(index=weather_data.index)

    # Iteriere über jede Windkraftanlage und simuliere die Energieproduktion
    for index, row in gdf_wind.iterrows():
        einheit_name = row['EinheitMastrNummer']
        bruttoleistung = row['Bruttoleistung']  # in kW

        # Erstellen eines WindTurbine-Objekts mit der skalierten Leistungskennlinie
        turbine = WindTurbine(
            nominal_power=bruttoleistung,
            hub_height=row['Nabenhoehe'],
            rotor_diameter=row['Rotordurchmesser'],
            power_curve=df_efficiency_curve
        )

        # Simuliere die Energieproduktion
        mc = ModelChain(turbine)
        mc.run_model(weather_data)

        # Speichere die simulierte Leistung in einer neuen Spalte
        wind_gen_results[einheit_name] = mc.power_output

    return wind_gen_results

# Beispiel für die Verwendung der Funktion
wea_gen_juechen = simulate_wind_farms(gdf_wind, weather_data, df_efficiency_curve)
print(wea_gen_juechen)
# Speichern der Ergebnisse in einer CSV-Datei
wea_gen_juechen.to_csv('mastdr_exp/wea_gen_juechen.csv', index=True)



print(gdf_wind)


path = os.path.join(os.getcwd(), 'mastdr_exp', 'gdf_wind_jüchen.csv')
#gdf_wind.to_csv(path, index=False)
# %% Create dict with windturbines

