"""MaStR (Marktstammdatenregister) data preprocessing utilities.

Provides functions for downloading, fetching, and preparing data from Germany's
Marktstammdatenregister (Market Master Data Register) for solar, wind, and storage
energy systems.

Author: Pyosch
AI Assistance: Claude Code (Claude Opus 4.8)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["Claude Code (Claude Opus 4.8)"]

import pandas as pd
from pathlib import Path
from functools import lru_cache
from sqlite3 import connect
import sqlite3

# geopandas / osmnx are imported lazily inside the functions that use them
# (df_to_gdf, add_centroids, prepare_*_data) so importing this module does not
# pull the heavy geo stack at app startup.

from src.config import MASTR_DB_PATH

_LOCATION_CACHE_DIR = Path(MASTR_DB_PATH).parent / "mastr"

# Tables / cache files / column set used for location disambiguation.
_LOCATION_TABLES = {
    "solar": "solar_extended",
    "wind": "wind_extended",
    "storage": "storage_extended",
}
_LOCATION_CSV = {
    "solar": "solar_locations.csv",
    "wind": "wind_locations.csv",
    "storage": "storage_locations.csv",
}
# Columns carried through the location cache. ``Gemeindeschluessel`` (the 8-digit
# official AGS) is the only globally unique municipality key; ``Ort`` (postal town
# name) is NOT unique — e.g. "Langenfeld" names three different municipalities.
_LOC_COLS = ["Ort", "Gemeindeschluessel", "Gemeinde", "Bundesland", "Landkreis"]


def _build_location_labels(raw: pd.DataFrame) -> pd.DataFrame:
    """Build unique, human-readable selection labels from raw location rows.

    One entry per ``(Ort, AGS)``. An ``Ort`` whose name is unique keeps the bare
    name; a name shared by several municipalities is suffixed with
    ``(Landkreis, Bundesland)`` so the user can tell them apart. AGS is appended
    only if a label would otherwise still collide, guaranteeing uniqueness.
    """
    df = raw.copy()
    for col in _LOC_COLS:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str).str.strip()

    df = df[df["Ort"] != ""]
    # Collapse to one row per (Ort, AGS); arbitrary-but-stable pick for the rest.
    df = (
        df.sort_values(_LOC_COLS, kind="stable")
        .drop_duplicates(subset=["Ort", "Gemeindeschluessel"])
        .reset_index(drop=True)
    )

    # An Ort is ambiguous when it maps to more than one municipality (AGS).
    ambiguous = df.groupby("Ort")["Gemeindeschluessel"].transform("size") > 1
    suffix = df.apply(
        lambda r: ", ".join([p for p in (r["Landkreis"], r["Bundesland"]) if p])
        or r["Gemeindeschluessel"],
        axis=1,
    )
    df["label"] = df["Ort"].where(~ambiguous, df["Ort"] + " (" + suffix + ")")

    # Final safety net: ensure labels are unique.
    dup = df["label"].duplicated(keep=False)
    if dup.any():
        df.loc[dup, "label"] = [
            f"{lbl} [{ags}]"
            for lbl, ags in zip(df.loc[dup, "label"], df.loc[dup, "Gemeindeschluessel"])
        ]

    return df.sort_values("label", kind="stable").reset_index(drop=True)[
        ["label", *_LOC_COLS]
    ]


@lru_cache(maxsize=None)
def _ensure_location_cache(csv_path_str: str, table: str, db_path: str) -> pd.DataFrame:
    """Return the location cache DataFrame, (re)building it from the DB if needed.

    Self-heals legacy caches: a CSV without the ``label`` column (the old
    ``Ort``-only schema) is rebuilt. Read as strings so AGS leading zeros survive.
    """
    csv_path = Path(csv_path_str)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    if csv_path.exists():
        cached = pd.read_csv(csv_path, dtype=str).fillna("")
        if "label" in cached.columns and set(_LOC_COLS).issubset(cached.columns):
            return cached

    # Without a usable CSV we must read the SQLite DB. Guard against sqlite3.connect
    # silently *creating* an empty open-mastr.db (which would poison the DB-presence
    # check that the online fallback relies on) when the DB file does not exist.
    if not Path(db_path).exists():
        raise FileNotFoundError(
            f"MaStR database not found at {db_path} and no usable location cache "
            f"at {csv_path}."
        )
    conn = sqlite3.connect(db_path)
    query = (
        f"SELECT DISTINCT {', '.join(_LOC_COLS)} FROM {table} "
        "WHERE Ort IS NOT NULL AND Gemeindeschluessel IS NOT NULL "
        "AND Gemeindeschluessel <> ''"
    )
    raw = pd.read_sql_query(query, conn, dtype=str)
    conn.close()

    built = _build_location_labels(raw)
    built.to_csv(csv_path, index=False)
    return built


def _resolve_location(location, csv_path, table: str, db_path: str) -> dict:
    """Resolve a selection label (or bare Ort) to its municipality identifiers.

    Returns a dict with ``ort``, ``ags``, ``gemeinde``, ``bundesland``,
    ``landkreis`` and a Nominatim-friendly ``geocode_query``. Falls back to the
    bare ``Ort`` (old behavior, no AGS) for inputs that are not known labels, so
    direct/legacy callers keep working.
    """
    location = "" if location is None else str(location)
    ort, ags, gemeinde, bundesland, landkreis = location, "", "", "", ""

    try:
        df = _ensure_location_cache(str(csv_path), table, db_path)
    except Exception:
        df = None

    if df is not None and len(df):
        hit = df[df["label"] == location]
        if len(hit) == 0:
            hit = df[df["Ort"] == location]  # bare-Ort fallback
        if len(hit) == 1:
            row = hit.iloc[0]
            ort = row["Ort"]
            ags = row["Gemeindeschluessel"]
            gemeinde = row["Gemeinde"]
            bundesland = row["Bundesland"]
            landkreis = row["Landkreis"]
        elif len(hit) > 1:
            # Ambiguous bare Ort passed directly → keep old Ort-only behavior.
            ort = location

    if gemeinde and bundesland:
        geocode_query = f"{gemeinde}, {bundesland}"
    elif bundesland:
        geocode_query = f"{ort}, {bundesland}"
    else:
        geocode_query = ort

    return {
        "ort": ort,
        "ags": ags,
        "gemeinde": gemeinde,
        "bundesland": bundesland,
        "landkreis": landkreis,
        "geocode_query": geocode_query,
    }


def geocode_query_for_location(location, data_type: str = "solar", mastr_db_path=None) -> str:
    """Public helper: clean ``"Gemeinde, Bundesland"`` geocode query for a label.

    Used by pages that geocode a selected MaStR location separately (for weather
    data) so they hit the right municipality instead of the ambiguous bare name.
    """
    if mastr_db_path is None:
        mastr_db_path = str(MASTR_DB_PATH)
    csv_path = _LOCATION_CACHE_DIR / _LOCATION_CSV.get(data_type, _LOCATION_CSV["solar"])
    table = _LOCATION_TABLES.get(data_type, _LOCATION_TABLES["solar"])
    return _resolve_location(location, csv_path, table, mastr_db_path)["geocode_query"]


def download_mastr_data():
    """Download MaStR database using open-mastr library.

    ``open_mastr`` (and its heavy transitive dependencies) is imported lazily so the
    app and the online REST fallback run without it installed; it is only needed to
    build/refresh the local SQLite database.
    """
    from open_mastr import Mastr
    db = Mastr()
    db.download()


def mastr_data_available(mastr_db_path=None) -> bool:
    """Return ``True`` if the local MaStR SQLite database file exists.

    When it does not, callers should fall back to the on-demand online register
    (see :mod:`src.mastr.online_api`).
    """
    return Path(mastr_db_path or MASTR_DB_PATH).exists()


def fetch_data(
    table_name,
    columns,
    filter_column=None,
    filter_values=None,
    mastr_db_path=None,
    extra_equals=None,
):
    """Fetch data from MaStR database with optional filtering.

    Args:
        table_name: Name of the database table to query.
        columns: List of column names to select.
        filter_column: Column name to filter by (optional).
        filter_values: Values to filter for (optional).
        mastr_db_path: Path to MaStR database file (uses config default if None).
        extra_equals: Optional ``{column: value}`` ANDed onto the WHERE clause as
            exact matches — used to pin an ambiguous ``Ort`` to a single
            municipality via ``Gemeindeschluessel`` (AGS).

    Returns:
        DataFrame containing the requested data.
    """
    if mastr_db_path is None:
        mastr_db_path = str(MASTR_DB_PATH)

    conn = connect(str(mastr_db_path))

    where_clauses: list[str] = []
    params: list = []
    if filter_values is not None:
        # Ensure filter_values is a list
        if isinstance(filter_values, str):
            filter_values = [filter_values]
        # Create a string of placeholders for the query
        placeholders = ', '.join(['?'] * len(filter_values))
        where_clauses.append(f"{filter_column} IN ({placeholders})")
        params.extend(filter_values)
    if extra_equals:
        for col, val in extra_equals.items():
            where_clauses.append(f"{col} = ?")
            params.append(val)

    where = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    query = f"SELECT {', '.join(columns)} FROM {table_name}{where}"
    df = pd.read_sql_query(query, conn, params=params or None)

    conn.close()

    return df

# Umrechnungswerte für die Ausrichtung und Neigung der Solarmodule.
# Module-level (not function-local) so the online REST path (src.mastr.online_api) can
# reuse the orientation table. The public REST API uses *identical* orientation labels
# but *different* tilt-bin labels for the same catalogue bins, so the online path keeps
# its own tilt table aligned to these same degrees (see online_api).
AUSRICHTUNG_MAPPING = {
    'Ost-West': 0,
    'Nord': 0,
    'Nord-Ost': 45,
    'Ost': 90,
    'Süd-Ost': 135,
    'Süd': 180,
    'Süd-West': 225,
    'West': 270,
    'Nord-West': 315,
}

NEIGUNGSWINKEL_MAPPING = {
    '< 20 Grad': 10,
    '20 - 40 Grad': 30,
    '40 - 60 Grad': 50,
    'Fassadenintegriert': 90,
}


def fetch_solar(location=None, solar_columns=None, mastr_db_path=None):

    # Define columns to be selected from database
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
                        'Landkreis',
                        'Gemeinde',
                        'Gemeindeschluessel',
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

    resolved = _resolve_location(
        location, _LOCATION_CACHE_DIR / _LOCATION_CSV['solar'],
        'solar_extended', mastr_db_path or str(MASTR_DB_PATH),
    )
    extra = {'Gemeindeschluessel': resolved['ags']} if resolved['ags'] else None
    df_solar = fetch_data(table_name='solar_extended',
                          columns=solar_columns,
                          filter_column='Ort',
                          filter_values=resolved['ort'],
                          mastr_db_path=mastr_db_path,
                          extra_equals=extra,
                          )
    
    # Map orientation and tilt angle values
    df_solar['Hauptausrichtung'] = df_solar['Hauptausrichtung'].map(AUSRICHTUNG_MAPPING)
    df_solar['HauptausrichtungNeigungswinkel'] = df_solar['HauptausrichtungNeigungswinkel'].map(NEIGUNGSWINKEL_MAPPING)

    return df_solar

def prepare_solar_data(location='Essen', mastr_db_path=None, force_online=False):
    import osmnx as ox

    try:
            resolved = _resolve_location(
                location, _LOCATION_CACHE_DIR / _LOCATION_CSV['solar'],
                'solar_extended', mastr_db_path or str(MASTR_DB_PATH),
            )
            geocode_query = resolved['geocode_query']

            if force_online or not mastr_data_available(mastr_db_path):
                # No local DB (or online explicitly requested) → fetch this location's
                # plants live from the online register.
                from src.mastr.online_api import fetch_solar_online
                gdf_solar = add_centroids(df_to_gdf(fetch_solar_online(resolved)), geocode_query)
                return gdf_solar, ox.geocode_to_gdf([geocode_query])

            df_solar = fetch_solar(location=location, mastr_db_path=mastr_db_path)
            df_grid_connections = prepare_grid_connections_data(location=location, mastr_db_path=mastr_db_path)
            df_solar = df_solar.merge(df_grid_connections,
                                      how='left',
                                      on='LokationMastrNummer'
                                      )

            gdf_solar = df_to_gdf(df_solar)
            gdf_solar = add_centroids(gdf_solar, geocode_query)

            city_district = ox.geocode_to_gdf([geocode_query])

            return gdf_solar, city_district

    except Exception as e:
            raise Exception(f"Error preparing data for {location}: {str(e)}")


def get_unique_solar_locations(mastr_db_path=None):
    if mastr_db_path is None:
        mastr_db_path = str(MASTR_DB_PATH)
    try:
        df = _ensure_location_cache(
            str(_LOCATION_CACHE_DIR / _LOCATION_CSV["solar"]),
            "solar_extended", mastr_db_path,
        )
        return df["label"].tolist()
    except Exception:
        # No DB and no shipped location CSV → caller (UI) falls back to free-text entry.
        return []

def fetch_wind(location=None, wind_columns=None, mastr_db_path=None):
    
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
                        'Landkreis',
                        'Gemeinde',
                        'Gemeindeschluessel',
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

    resolved = _resolve_location(
        location, _LOCATION_CACHE_DIR / _LOCATION_CSV['wind'],
        'wind_extended', mastr_db_path or str(MASTR_DB_PATH),
    )
    extra = {'Gemeindeschluessel': resolved['ags']} if resolved['ags'] else None
    return fetch_data(table_name='wind_extended',
                      columns=wind_columns,
                      filter_column='Ort',
                      filter_values=resolved['ort'],
                      mastr_db_path=mastr_db_path,
                      extra_equals=extra,
                      )

def prepare_wind_data(location='Essen', mastr_db_path=None, force_online=False):
    import osmnx as ox

    try:
            resolved = _resolve_location(
                location, _LOCATION_CACHE_DIR / _LOCATION_CSV['wind'],
                'wind_extended', mastr_db_path or str(MASTR_DB_PATH),
            )
            geocode_query = resolved['geocode_query']

            if force_online or not mastr_data_available(mastr_db_path):
                # No local DB (or online explicitly requested) → fetch this location's
                # turbines live from the online register.
                from src.mastr.online_api import fetch_wind_online
                gdf_wind = add_centroids(df_to_gdf(fetch_wind_online(resolved)), geocode_query)
                city_district = ox.geocode_to_gdf([geocode_query])
                city_district.set_index('name', inplace=True)
                return gdf_wind, city_district

            df_wind = fetch_wind(location=location, mastr_db_path=mastr_db_path)
            df_grid_connections = prepare_grid_connections_data(location=location, mastr_db_path=mastr_db_path)
            df_wind = df_wind.merge(df_grid_connections,
                                    how='left',
                                    on='LokationMastrNummer'
                                    )

            gdf_wind = df_to_gdf(df_wind)
            gdf_wind = add_centroids(gdf_wind, geocode_query)

            city_district = ox.geocode_to_gdf([geocode_query])
            city_district.set_index('name', inplace=True)

            return gdf_wind, city_district

    except Exception as e:
            raise Exception(f"Error preparing data for {location}: {str(e)}")

def get_unique_wind_locations(mastr_db_path=None):
    if mastr_db_path is None:
        mastr_db_path = str(MASTR_DB_PATH)
    try:
        df = _ensure_location_cache(
            str(_LOCATION_CACHE_DIR / _LOCATION_CSV["wind"]),
            "wind_extended", mastr_db_path,
        )
        return df["label"].tolist()
    except Exception:
        # No DB and no shipped location CSV → caller (UI) falls back to free-text entry.
        return []

def read_storage_units(mastr_db_path=None):
    if mastr_db_path is None:
        mastr_db_path = str(MASTR_DB_PATH)

    conn = connect(mastr_db_path)

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    
    storage_unit_columns = ['VerknuepfteEinheit',
                            'NutzbareSpeicherkapazitaet'
                            ]
    
    storage_units = pd.read_sql_query(f"SELECT {', '.join(storage_unit_columns)} FROM storage_units", conn)
    
    conn.close()
    
    return storage_units


def fetch_storage(location=None, storage_columns=None, mastr_db_path=None):
    
    if storage_columns is None:
        storage_columns = ['EinheitMastrNummer',
                        'NameStromerzeugungseinheit',
                        'LokationMastrNummer',
                        'SpeMastrNummer',
                        #    'NutzbareSpeicherkapazitaet', #Column is empty. Data in storage_units
                        'Technologie',
                        'LeistungsaufnahmeBeimEinspeichern',
                        'Bundesland',
                        'Landkreis',
                        'Gemeinde',
                        'Gemeindeschluessel',
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

    resolved = _resolve_location(
        location, _LOCATION_CACHE_DIR / _LOCATION_CSV['storage'],
        'storage_extended', mastr_db_path or str(MASTR_DB_PATH),
    )
    extra = {'Gemeindeschluessel': resolved['ags']} if resolved['ags'] else None
    df_storage = fetch_data(table_name='storage_extended',
                            columns=storage_columns,
                            filter_column='Ort',
                            filter_values=resolved['ort'],
                            mastr_db_path=mastr_db_path,
                            extra_equals=extra,
                            )
    
    df_storage_units = read_storage_units(mastr_db_path=mastr_db_path)
    
    df_storage = df_storage.merge(df_storage_units, 
                                         how='left', 
                                         left_on='EinheitMastrNummer', 
                                         right_on='VerknuepfteEinheit'
                                         )
    
    return df_storage

def prepare_storage_data(location='Essen', mastr_db_path=None, force_online=False):
    import osmnx as ox

    try:
            resolved = _resolve_location(
                location, _LOCATION_CACHE_DIR / _LOCATION_CSV['storage'],
                'storage_extended', mastr_db_path or str(MASTR_DB_PATH),
            )
            geocode_query = resolved['geocode_query']

            if force_online or not mastr_data_available(mastr_db_path):
                # No local DB (or online explicitly requested) → fetch this location's
                # storage units live from the register.
                from src.mastr.online_api import fetch_storage_online
                gdf_storage = add_centroids(df_to_gdf(fetch_storage_online(resolved)), geocode_query)
                return gdf_storage, ox.geocode_to_gdf([geocode_query])

            df_storage = fetch_storage(location=location, mastr_db_path=mastr_db_path)
            df_grid_connections = prepare_grid_connections_data(location=location, mastr_db_path=mastr_db_path)
            df_storage = df_storage.merge(df_grid_connections,
                                          how='left',
                                          on='LokationMastrNummer'
                                          )

            gdf_storage = df_to_gdf(df_storage)
            gdf_storage = add_centroids(gdf_storage, geocode_query)

            city_district = ox.geocode_to_gdf([geocode_query])

            return gdf_storage, city_district

    except Exception as e:
            raise Exception(f"Error preparing data for {location}: {str(e)}")

def get_unique_storage_locations(mastr_db_path=None):
    if mastr_db_path is None:
        mastr_db_path = str(MASTR_DB_PATH)
    try:
        df = _ensure_location_cache(
            str(_LOCATION_CACHE_DIR / _LOCATION_CSV["storage"]),
            "storage_extended", mastr_db_path,
        )
        return df["label"].tolist()
    except Exception:
        # No DB and no shipped location CSV → caller (UI) falls back to free-text entry.
        return []


def fetch_grid_connections(grid_connections_columns=None, mastr_db_path=None):
    if mastr_db_path is None:
        mastr_db_path = str(MASTR_DB_PATH)
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

def fetch_grids(grid_columns=None, mastr_db_path=None):
    if mastr_db_path is None:
        mastr_db_path = str(MASTR_DB_PATH)

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

def prepare_grid_connections_data(location='Essen', mastr_db_path=None):
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
    import geopandas
    gdf = geopandas.GeoDataFrame(
    df, geometry=geopandas.points_from_xy(df.Laengengrad, df.Breitengrad), crs="EPSG:4326"
    )
    return gdf

def add_centroids(gdf, geocode_query=None):
    import osmnx as ox
    if geocode_query is None:
        # Derive a precise query from the disambiguating columns; bare Ort is
        # ambiguous and can geocode to the wrong town (e.g. Langenfeld).
        first = gdf.iloc[0]
        gemeinde = str(first.get('Gemeinde', '') or '').strip()
        bundesland = str(first.get('Bundesland', '') or '').strip()
        ort = str(first.get('Ort', '') or '').strip()
        if gemeinde and bundesland:
            geocode_query = f"{gemeinde}, {bundesland}"
        elif ort and bundesland:
            geocode_query = f"{ort}, {bundesland}"
        else:
            geocode_query = ort or gdf['Ort'][0]
    city_district = ox.geocode_to_gdf(geocode_query)
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


def rebuild_location_caches(mastr_db_path=None):
    """Delete and rebuild solar/wind/storage location CSV caches from the SQLite database."""
    if mastr_db_path is None:
        mastr_db_path = str(MASTR_DB_PATH)
    _ensure_location_cache.cache_clear()
    for name in _LOCATION_CSV.values():
        p = _LOCATION_CACHE_DIR / name
        if p.exists():
            p.unlink()
    get_unique_solar_locations(mastr_db_path)
    get_unique_wind_locations(mastr_db_path)
    get_unique_storage_locations(mastr_db_path)
