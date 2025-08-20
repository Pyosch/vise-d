import pandas as pd
import os
from sqlite3 import connect

from open_mastr import Mastr
import geopandas
import osmnx as ox
import sqlite3

def download_mastr_data():
    
    db = Mastr()
    db.download()

def fetch_data(table_name, columns, filter_column=None, filter_values=None, mastr_db_path=os.path.join(os.path.dirname(__file__), 'data', 'open-mastr.db')):
    conn = connect(mastr_db_path)
    
    if filter_values is not None:
        # Ensure filter_values is a list
        if isinstance(filter_values, str):
            filter_values = [filter_values]
        # Create a string of placeholders for the query
        placeholders = ', '.join(['?'] * len(filter_values))
        query = f"SELECT {', '.join(columns)} FROM {table_name} WHERE {filter_column} IN ({placeholders})"
        df = pd.read_sql_query(query, conn, params=filter_values)
    else:
        query = f"SELECT {', '.join(columns)} FROM {table_name}"
        df = pd.read_sql_query(query, conn)
    
    conn.close()
    
    return df

def fetch_solar(location=None, solar_columns=None, mastr_db_path=os.path.join(os.path.dirname(__file__), 'data', 'open-mastr.db')):
    
    #Umrechnungswerte für die Ausrichtung und Neigung
    ausrichtung_mapping = {
        'Ost-West': 0,
        'Nord': 0,
        'Nord-Ost': 45,
        'Ost': 90,
        'Süd-Ost': 135,
        'Süd': 180,
        'Süd-West': 225,
        'West': 270,
        'Nord-West': 315   
    }

    neigungswinkel_mapping = {
        '< 20 Grad': 10,
        '20 - 40 Grad': 30,
        '40 - 60 Grad': 50,
        'Fassadenintegriert': 90
    }

    #Define columns to be selected from db
    if solar_columns is None:
        solar_columns = ['EinheitMastrNummer',
                        'NameStromerzeugungseinheit',
                        'LokationMastrNummer',
                        'Gemarkung', 
                        'Leistungsbegrenzung',
                        'ZugeordneteWirkleistungWechselrichter',
                        'Bruttoleistung', 
                        'Lage', 
                        'Bundesland', 
                        'Land', 
                        'Gemeinde', 
                        'Ort', 
                        'Postleitzahl', 
                        'Strasse', 
                        'Hausnummer', 
                        'Nettonennleistung', 
                        'AnzahlModule', 
                        'Laengengrad', 
                        'Breitengrad', 
                        'Hauptausrichtung', 
                        'HauptausrichtungNeigungswinkel',
                        'Nebenausrichtung', 
                        'NebenausrichtungNeigungswinkel',
                        'Inbetriebnahmedatum', 
                        'DatumEndgueltigeStilllegung',
                        'Netzbetreiberzuordnungen',
                        ]
            
    df_solar = fetch_data(table_name='solar_extended', 
                          columns=solar_columns, 
                          filter_column='Ort', 
                          filter_values=location, 
                          mastr_db_path=mastr_db_path
                          )
    
    #Mapping der Ausrichtung und Neigung
    df_solar['Hauptausrichtung'] = df_solar['Hauptausrichtung'].map(ausrichtung_mapping)
    df_solar['HauptausrichtungNeigungswinkel'] = df_solar['HauptausrichtungNeigungswinkel'].map(neigungswinkel_mapping)

    return df_solar

def prepare_solar_data(location='Essen', mastr_db_path=os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'open-mastr.db'))):

    try:
            df_solar = fetch_solar(location=location, mastr_db_path=mastr_db_path)
            df_grid_connections = prepare_grid_connections_data(location=location, mastr_db_path=mastr_db_path)
            df_solar = df_solar.merge(df_grid_connections, 
                                      how='left', 
                                      on='LokationMastrNummer'
                                      )
            
            gdf_solar = df_to_gdf(df_solar)
            gdf_solar = add_centroids(gdf_solar)
            
            city_district = ox.geocode_to_gdf([location])
            
            return gdf_solar, city_district

    except Exception as e:
            raise Exception(f"Error preparing data for {location}: {str(e)}")


def get_unique_solar_locations(mastr_db_path=os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'open-mastr.db'))):
    try:
        # Connect to the database
        conn = sqlite3.connect(mastr_db_path)
        # Query distinct Ort values
        query = "SELECT DISTINCT Ort FROM solar_extended WHERE Ort IS NOT NULL"
        df = pd.read_sql_query(query, conn)
        conn.close()
        # Return sorted unique locations
        return sorted(df['Ort'].tolist())
    except Exception as e:
        raise Exception(f"Failed to fetch unique locations: {str(e)}")

def fetch_wind(location=None, wind_columns=None, mastr_db_path=os.path.join(os.path.dirname(__file__), 'data', 'open-mastr.db')):
    
    if wind_columns is None:
        wind_columns = ['EinheitMastrNummer',
                        'LokationMastrNummer',
                        'NameWindpark', 
                        'NameStromerzeugungseinheit',
                        'Gemarkung', 
                        'Lage',
                        'Hersteller', 
                        'HerstellerId', 
                        'Technologie', 
                        'Typenbezeichnung', 
                        'Rotordurchmesser',
                        'Bundesland', 
                        'Land', 
                        'Gemeinde', 
                        'Ort',
                        'Postleitzahl',
                        'DatumEndgueltigeStilllegung', 
                        'Bruttoleistung', 
                        'Nettonennleistung',
                        'AnschlussAnHoechstOderHochSpannung', 
                        'Nabenhoehe', 
                        'Laengengrad', 
                        'Breitengrad', 
                        'Inbetriebnahmedatum'
                        ]
    
    return fetch_data(table_name='wind_extended', 
                      columns=wind_columns, 
                      filter_column='Ort', 
                      filter_values=location, 
                      mastr_db_path=mastr_db_path
                      )

def prepare_wind_data(location='Essen', mastr_db_path=os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'open-mastr.db'))):

    try:
            df_wind = fetch_wind(location=location, mastr_db_path=mastr_db_path)
            df_grid_connections = prepare_grid_connections_data(location=location, mastr_db_path=mastr_db_path)
            df_wind = df_wind.merge(df_grid_connections, 
                                    how='left', 
                                    on='LokationMastrNummer'
                                    )
            
            gdf_wind = df_to_gdf(df_wind)
            gdf_wind = add_centroids(gdf_wind)
            
            city_district = ox.geocode_to_gdf([location])
            city_district.set_index('name', inplace=True)
            
            return gdf_wind, city_district

    except Exception as e:
            raise Exception(f"Error preparing data for {location}: {str(e)}")

def get_unique_wind_locations(mastr_db_path=os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'open-mastr.db'))):
    try:
        # Connect to the database
        conn = sqlite3.connect(mastr_db_path)
        # Query distinct Ort values
        query = "SELECT DISTINCT Ort FROM wind_extended WHERE Ort IS NOT NULL"
        df = pd.read_sql_query(query, conn)
        conn.close()
        # Return sorted unique locations
        return sorted(df['Ort'].tolist())
    except Exception as e:
        raise Exception(f"Failed to fetch unique locations: {str(e)}")

def read_storage_units(mastr_db_path=os.path.join(os.path.dirname(__file__), 'data', 'open-mastr.db')):
    
    conn = connect(mastr_db_path)

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    
    storage_unit_columns = ['VerknuepfteEinheit',
                            'NutzbareSpeicherkapazitaet'
                            ]
    
    storage_units = pd.read_sql_query(f"SELECT {', '.join(storage_unit_columns)} FROM storage_units", conn)
    
    conn.close()
    
    return storage_units


def fetch_storage(location=None, storage_columns=None, mastr_db_path=os.path.join(os.path.dirname(__file__), 'data', 'open-mastr.db')):
    
    if storage_columns is None:
        storage_columns = ['EinheitMastrNummer',
                        'NameStromerzeugungseinheit',
                        'LokationMastrNummer',
                        'SpeMastrNummer',
                        #    'NutzbareSpeicherkapazitaet', #Column is empty. Data in storage_units
                        'Technologie',
                        'LeistungsaufnahmeBeimEinspeichern',
                        'Bundesland',
                        'Postleitzahl',
                        'Ort',
                        'Strasse',
                        'Hausnummer',
                        'Laengengrad',
                        'Breitengrad',
                        'Meldedatum',
                        'Inbetriebnahmedatum',
                        'EinheitBetriebsstatus',
                        'Bruttoleistung',
                        'Nettonennleistung',
                        'ZugeordneteWirkleistungWechselrichter'
                        ]
    
    df_storage = fetch_data(table_name='storage_extended', 
                            columns=storage_columns, 
                            filter_column='Ort', 
                            filter_values=location, 
                            mastr_db_path=mastr_db_path
                            )
    
    df_storage_units = read_storage_units(mastr_db_path=mastr_db_path)
    
    df_storage = df_storage.merge(df_storage_units, 
                                         how='left', 
                                         left_on='EinheitMastrNummer', 
                                         right_on='VerknuepfteEinheit'
                                         )
    
    return df_storage

def prepare_storage_data(location='Essen', mastr_db_path=os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'open-mastr.db'))):
    
    try:
            df_storage = fetch_storage(location=location, mastr_db_path=mastr_db_path)
            df_grid_connections = prepare_grid_connections_data(location=location, mastr_db_path=mastr_db_path)
            df_storage = df_storage.merge(df_grid_connections, 
                                          how='left', 
                                          on='LokationMastrNummer'
                                          )

            gdf_storage = df_to_gdf(df_storage)
            gdf_storage = add_centroids(gdf_storage)
            
            
            city_district = ox.geocode_to_gdf([location])
            
            return gdf_storage, city_district
            
    except Exception as e:
            raise Exception(f"Error preparing data for {location}: {str(e)}")

def get_unique_storage_locations(mastr_db_path=os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'open-mastr.db'))):
    try:
        # Connect to the database
        conn = sqlite3.connect(mastr_db_path)
        # Query distinct Ort values
        query = "SELECT DISTINCT Ort FROM storage_extended WHERE Ort IS NOT NULL"
        df = pd.read_sql_query(query, conn)
        conn.close()
        # Return sorted unique locations
        return sorted(df['Ort'].tolist())
    except Exception as e:
        raise Exception(f"Failed to fetch unique locations: {str(e)}")


def fetch_grid_connections(grid_connections_columns=None, mastr_db_path=os.path.join(os.path.dirname(__file__), 'data', 'open-mastr.db')):
    conn = connect(mastr_db_path)
    
    if grid_connections_columns is None:
        grid_connections_columns = ['NetzanschlusspunktMastrNummer', 
                        'NetzanschlusspunktBezeichnung',
                        'LetzteAenderung', 
                        'LokationMastrNummer', 
                        'Lokationtyp',
                        'MaximaleEinspeiseleistung', 
                        # 'Gasqualitaet', 
                        'NetzMastrNummer',
                        'NochInPlanung', 
                        'NameDerTechnischenLokation',
                        'MaximaleAusspeiseleistung', 
                        'Messlokation', 
                        'Spannungsebene',
                        # 'BilanzierungsgebietNetzanschlusspunktId', 
                        'Nettoengpassleistung',
                        'Netzanschlusskapazitaet', 
                        # 'DatenQuelle', 
                        # 'DatumDownload'
                        ]
    
    query = f"SELECT {', '.join(grid_connections_columns)} FROM grid_connections"
    df_grid_connections = pd.read_sql_query(query, conn)
    
    conn.close()
    
    return df_grid_connections

def fetch_grids(grid_columns=None, mastr_db_path=os.path.join(os.path.dirname(__file__), 'data', 'open-mastr.db')):
    
    conn = connect(mastr_db_path)
    
    if grid_columns is None:
        grid_columns = ['MastrNummer', 
                        # 'DatumLetzteAktualisierung', 
                        # 'Sparte',
                        # 'KundenAngeschlossen', 
                        # 'GeschlossenesVerteilnetz', 
                        'Bezeichnung',
                        # 'Marktgebiet', 
                        # 'Bundesland', 
                        # 'DatenQuelle', 
                        # 'DatumDownload'
                        ]
        
    
    query = f"SELECT {', '.join(grid_columns)} FROM grids"
        
    df_grids = pd.read_sql_query(query, conn)
    
    df_grids = df_grids.rename(columns={'MastrNummer': 'NetzMastrNummer',
                                        'Bezeichnung': 'Netzbetreiber'}
                               )
    
    conn.close()
    
    return df_grids

def prepare_grid_connections_data(location='Essen', mastr_db_path=os.path.join(os.path.dirname(__file__), 'data', 'open-mastr.db')):
    try:
        df_grid_connections = fetch_grid_connections(mastr_db_path=mastr_db_path).head(20)
        df_grids = fetch_grids(mastr_db_path=mastr_db_path)

        df_grid_connections = df_grid_connections.merge(df_grids, 
                                                         how='left', 
                                                         on='NetzMastrNummer'
                                                         )

        return df_grid_connections

    except Exception as e:
        raise Exception(f"Error preparing data for {location}: {str(e)}")

def df_to_gdf(df):
    gdf = geopandas.GeoDataFrame(
    df, geometry=geopandas.points_from_xy(df.Laengengrad, df.Breitengrad), crs="EPSG:4326"
    )
    return gdf

def add_centroids(gdf):
    city_district = ox.geocode_to_gdf(gdf['Ort'][0])
    city_district = city_district.to_crs("EPSG:4326")
    laengengrad = city_district.centroid.x[0]
    breitengrad = city_district.centroid.y[0]
    gdf['geometry'] = gdf['geometry'].fillna(city_district.centroid[0])
    gdf['Laengengrad'] = gdf['Laengengrad'].fillna(laengengrad)
    gdf['Breitengrad'] = gdf['Breitengrad'].fillna(breitengrad)
    
    return gdf

if __name__ == '__main__':
    location = 'Jüchen'
    # df_solar = fetch_solar(location=location)
    # gdf_solar = df_to_gdf(df_solar)
    
    gdf_solar, city_district = prepare_solar_data(location=location)
    
    # print(gdf_solar.head())
    # gdf_solar.explore()
    
    # df_storage = fetch_storage(location=location)
    # df_storage_units = read_storage_units()
    # gdf_storage = df_to_gdf(df_storage)
    # gdf_storage = add_centroids(gdf_storage)
    
    gdf_storage, city_district = prepare_storage_data(location=location)
    
    # gdf_storage.explore()
    # with open('data/mastr/storage_troisdorf_columns.txt', 'w') as f:
    #     for col in df_storage.columns:
    #         f.write(f"{col}\n")

    # df_wind = fetch_wind(location=location)
    # gdf_wind = df_to_gdf(df_wind)
    # gdf_wind = add_centroids(gdf_wind)
    gdf_wind, city_district = prepare_wind_data(location=location)
    # gdf_wind.explore()