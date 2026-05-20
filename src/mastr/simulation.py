"""MaStR-based energy generation simulation utilities.

Provides functions for simulating energy generation from photovoltaic and wind power
systems using data from Germany's Marktstammdatenregister (MaStR) and vpplib models.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import logging
from pathlib import Path
from tqdm import tqdm
import numpy as np
import pandas as pd
import pvlib
import windpowerlib as wpl
from fuzzywuzzy import fuzz
import math
import random
import matplotlib.pyplot as plt
from windpowerlib import WindTurbine, ModelChain

from vpplib import Photovoltaic, WindPower, UserProfile, Environment
from src.mastr.preprocessing import prepare_solar_data, prepare_wind_data
from src.config import PROJECT_ROOT, DATA_DIR, PV_PARAMS_DIR

# Path to median wind power curve
path_to_power_curve = DATA_DIR / "median_windpower_curve.csv"

def revise_power_values(gdf):
    """
    Revises and corrects power-related values in a GeoDataFrame for energy generation units.
    This function iterates over each row in the provided GeoDataFrame and performs the following operations:
    - If the 'ZugeordneteWirkleistungWechselrichter' value is NaN, it is set to the value of 'Nettonennleistung'.
    - Checks the ratio between the maximum and minimum values among 'Bruttoleistung', 'Nettonennleistung', and 'ZugeordneteWirkleistungWechselrichter'.
      - If the ratio is >= 100:
        - If the minimum value is below 0.01, it is multiplied by 100.
        - Otherwise, the maximum value is divided by 1000.
        - The minimum value is checked and potentially corrected again.
      - If the ratio is >= 50:
        - The maximum value is divided by 100.
      - If the ratio is >= 10:
        - If the minimum value is below 0.1, it is multiplied by 10.
        - Otherwise, the maximum value is divided by 10.
        - The minimum value is checked and potentially corrected again.
    - Logs all corrections and relevant information to 'mastr_preprocessing.log'.
    Parameters
    ----------
    gdf : pandas.DataFrame or geopandas.GeoDataFrame
        The DataFrame containing columns 'Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter',
        'EinheitMastrNummer', and 'NameStromerzeugungseinheit'.
    Returns
    -------
    gdf : pandas.DataFrame or geopandas.GeoDataFrame
        The DataFrame with revised power values.
    Notes
    -----
    - The function modifies the input DataFrame in place.
    - Logging is configured within the function and outputs to 'mastr_preprocessing.log'.
    - The function is designed to handle common data inconsistencies in power values for energy generation units.
    """
    
    # Configure logging
    logging.basicConfig(filename='mastr_preprocessing.log', level=logging.INFO, 
                        format='%(asctime)s - %(levelname)s - %(message)s')
    
    for i in gdf.index:
        
        if np.isnan(gdf.loc[i, 'ZugeordneteWirkleistungWechselrichter']):
            gdf.loc[i, 'ZugeordneteWirkleistungWechselrichter'] = gdf.loc[i, 'Nettonennleistung']
        
        if (gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].max() 
                    / gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].min()) >=100:
            logging.info(f"Einheit {gdf.loc[i, 'EinheitMastrNummer']} - {gdf.loc[i, 'NameStromerzeugungseinheit']}:")
            
            if gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].min() < 0.01:
                old_min = gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].min()
                min_col = gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].idxmin()
                gdf.loc[i, min_col] = old_min * 100
                logging.info(f"Value for '{min_col}' is below 0.01. Increasing value to {old_min * 100}.")
            else:
                old_max = gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].max()
                max_col = gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].idxmax()
                gdf.loc[i, max_col] = old_max / 1000
                logging.info(f"Value for '{max_col}' is above 100. Decreasing value to {old_max / 1000}.")
            
            # Data shows that oftentimes two values are out of range for min, so we need to check again
            if gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].min() < 0.01:
                old_min = gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].min()
                min_col = gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].idxmin()
                gdf.loc[i, min_col] = old_min * 100
                logging.info(f"Value for '{min_col}' is below 0.01. Increasing value to {old_min * 100}.")
                
            
        elif (gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].max()
                / gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].min()) >=50:
            logging.info(f"Einheit {gdf.loc[i, 'EinheitMastrNummer']} - {gdf.loc[i, 'NameStromerzeugungseinheit']}:")
            
            old_max = gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].max()
            max_col = gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].idxmax()
            gdf.loc[i, max_col] = old_max / 100
            logging.info(f"Value for '{max_col}' is above 50. Decreasing value to {old_max / 100}.")
            
        elif (gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].max()
                / gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].min()) >=10:
            logging.info(f"Einheit {gdf.loc[i, 'EinheitMastrNummer']} - {gdf.loc[i, 'NameStromerzeugungseinheit']}:")
            
            if gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].min() < 0.1:
                old_min = gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].min()
                min_col = gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].idxmin()
                gdf.loc[i, min_col] = old_min * 10
                logging.info(f"Value for '{min_col}' is below 0.1. Increasing value to {old_min * 10}.")
            else:
                old_max = gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].max()
                max_col = gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].idxmax()
                min_col = gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].idxmin()
                gdf.loc[i, max_col] = old_max / 10
                logging.info(f"Value for '{min_col} / {max_col}' is above 10. Decreasing value to {old_max / 10}.")
                
            if gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].min() < 0.1:
                old_min = gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].min()
                min_col = gdf.loc[i, ['Bruttoleistung', 'Nettonennleistung', 'ZugeordneteWirkleistungWechselrichter']].idxmin()
                gdf.loc[i, min_col] = old_min * 10
                logging.info(f"Value for '{min_col}' is below 0.1. Increasing value to {old_min * 10}.")
                
        # else:
        #     raise Exception(f"Values for '{gdf.loc[i, 'NameStromerzeugungseinheit']}' are not within the expected range.")
                

    return gdf

class SimplePVSystem:
    """Thin pvlib-based PV system with the same interface as vpplib's Photovoltaic.

    Uses the PVWatts model so that only power ratings from MaStR are needed —
    no SAM component library look-up required.
    """

    def __init__(self, identifier, row, environment):
        self.identifier = identifier
        self.environment = environment
        self.timeseries = None

        module_parameters = {
            'pdc0': row['pdc0_module_W'],
            'gamma_pdc': row['gamma_pdc'],
        }
        inverter_parameters = {
            'pdc0': row['pdc0_inverter_W'],
            'eta_inv_nom': row['eta_inv_nom'],
        }
        system = pvlib.pvsystem.PVSystem(
            surface_tilt=row['surface_tilt'],
            surface_azimuth=row['surface_azimuth'],
            module_parameters=module_parameters,
            inverter_parameters=inverter_parameters,
            racking_model='open_rack',
            module_type='glass_polymer',
        )
        location = pvlib.location.Location(
            latitude=row['latitude'],
            longitude=row['longitude'],
        )
        self.modelchain = pvlib.modelchain.ModelChain(
            system,
            location,
            dc_model='pvwatts',
            ac_model='pvwatts',
            aoi_model='no_loss',
            spectral_model='no_loss',
            temperature_model='sapm',
            name=identifier,
        )

    def prepare_time_series(self):
        if len(self.environment.pv_data) == 0:
            raise ValueError("self.environment.pv_data is empty.")

        weather = self.environment.pv_data.loc[
            self.environment.start: self.environment.end
        ]
        if 'poa_global' in weather.columns:
            self.modelchain.run_model_from_poa(data=weather)
        else:
            self.modelchain.run_model(weather=weather)

        timeseries = pd.DataFrame(self.modelchain.results.ac / 1000)
        timeseries.rename(columns={0: self.identifier}, inplace=True)
        timeseries.index = pd.to_datetime(timeseries.index)
        self.timeseries = timeseries.fillna(0)
        return self.timeseries


def build_pvsystem_params_from_mastr(gdf):
    """Derive PVWatts-compatible parameters directly from MaStR GeoDataFrame.

    Parameters
    ----------
    gdf : GeoDataFrame
        Solar installations with MaStR fields (after revise_power_values).

    Returns
    -------
    pd.DataFrame
        One row per system with columns:
        EinheitMastrNummer, pdc0_module_W, gamma_pdc,
        pdc0_inverter_W, eta_inv_nom,
        surface_tilt, surface_azimuth, latitude, longitude
    """
    records = []
    for i in gdf.index:
        inv_pwr = (
            gdf.loc[i, 'Nettonennleistung']
            if np.isnan(gdf.loc[i, 'ZugeordneteWirkleistungWechselrichter'])
            else gdf.loc[i, 'ZugeordneteWirkleistungWechselrichter']
        )
        records.append({
            'EinheitMastrNummer': gdf.loc[i, 'EinheitMastrNummer'],
            'pdc0_module_W': gdf.loc[i, 'Bruttoleistung'] * 1000,
            'gamma_pdc': -0.004,
            'pdc0_inverter_W': inv_pwr * 1000,
            'eta_inv_nom': 0.96,
            'surface_tilt': gdf.loc[i, 'HauptausrichtungNeigungswinkel'],
            'surface_azimuth': gdf.loc[i, 'Hauptausrichtung'],
            'latitude': gdf.loc[i, 'Breitengrad'],
            'longitude': gdf.loc[i, 'Laengengrad'],
        })
    return pd.DataFrame(records).set_index('EinheitMastrNummer')


def load_or_build_pv_params(gdf, cache_path):
    """Load PV parameters from CSV cache or build them from MaStR data.

    New systems found in *gdf* that are not yet in the cache are appended
    so that subsequent runs for the same location skip re-derivation.

    Parameters
    ----------
    gdf : GeoDataFrame
        Solar installations (after revise_power_values).
    cache_path : Path or str
        Path to the CSV cache file for this location.

    Returns
    -------
    pd.DataFrame
        Parameters for all systems in gdf (index: EinheitMastrNummer).
    """
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists():
        cached = pd.read_csv(cache_path, index_col='EinheitMastrNummer')
        known_ids = set(cached.index)
        new_ids = [i for i in gdf.index if gdf.loc[i, 'EinheitMastrNummer'] not in known_ids]
        if new_ids:
            new_gdf = gdf.loc[new_ids]
            new_params = build_pvsystem_params_from_mastr(new_gdf)
            cached = pd.concat([cached, new_params])
            cached.to_csv(cache_path)
        current_ids = gdf['EinheitMastrNummer'].tolist()
        return cached.loc[cached.index.isin(current_ids)]
    else:
        params = build_pvsystem_params_from_mastr(gdf)
        params.to_csv(cache_path)
        return params


def build_pvsystems_from_params(params_df, ref_env):
    """Build SimplePVSystem objects from a parameters DataFrame.

    Replaces pick_pvsystem_mastr — no SAM library search, no iteration.

    Parameters
    ----------
    params_df : pd.DataFrame
        Output of load_or_build_pv_params (index: EinheitMastrNummer).
    ref_env : Environment
        vpplib Environment with loaded weather data.

    Returns
    -------
    dict
        {EinheitMastrNummer: [SimplePVSystem]} — same format as pick_pvsystem_mastr.
    """
    pv_systems_dict = {}
    for mastr_nr, row in tqdm(params_df.iterrows()):
        pv = SimplePVSystem(identifier=mastr_nr, row=row, environment=ref_env)
        pv_systems_dict[mastr_nr] = [pv]
    return pv_systems_dict


def pick_pvsystem_mastr(gdf, ref_env, av_module_pwr=300, module_lib_name='SandiaMod', inverter_lib_name='cecinverter'):
    """
    Selects and configures photovoltaic (PV) system components for each entry in a GeoDataFrame based on system parameters.
    For each row in the input GeoDataFrame `gdf`, this function:
        - Determines the required number of PV modules and inverters based on the system's gross power and available module power.
        - Selects appropriate PV modules from the specified module library (`module_lib_name`) whose rated power matches the calculated average module power.
        - Selects appropriate inverters from the specified inverter library (`inverter_lib_name`) whose AC power matches the assigned inverter power.
        - Calculates the number of modules per string and strings per inverter based on the configuration.
        - Instantiates `Photovoltaic` objects for each inverter and aggregates them in a dictionary keyed by the system's unique identifier.
    Parameters
    ----------
    gdf : pandas.DataFrame or geopandas.GeoDataFrame
        DataFrame containing PV system data, including columns such as 'Bruttoleistung', 'AnzahlModule', 'Nettonennleistung',
        'ZugeordneteWirkleistungWechselrichter', 'NameStromerzeugungseinheit', 'EinheitMastrNummer', 'Breitengrad', 'Laengengrad',
        'HauptausrichtungNeigungswinkel', and 'Hauptausrichtung'.
    ref_env : object
        Reference environment object to be passed to the Photovoltaic system.
    av_module_pwr : float, optional
        Average module power in Watts to use when 'AnzahlModule' is not specified (default is 300).
    module_lib_name : str, optional
        Name of the PV module library to use with pvlib (default is 'SandiaMod').
    inverter_lib_name : str, optional
        Name of the inverter library to use with pvlib (default is 'cecinverter').
    Returns
    -------
    pv_systems_dict : dict
        Dictionary mapping each system's unique identifier ('EinheitMastrNummer') to a list of configured Photovoltaic objects.
    Notes
    -----
    - The function prints messages when it cannot find a suitable module or inverter and increases the number of modules/inverters accordingly.
    - The function assumes the existence of a `Photovoltaic` class for system instantiation.
    - The function uses random selection when multiple suitable modules or inverters are found.
    """
    
    pv_systems_dict = {} 
    
    for i in tqdm(range(len(gdf))):
        module_lib = pvlib.pvsystem.retrieve_sam(module_lib_name)
        inverter_lib = pvlib.pvsystem.retrieve_sam(inverter_lib_name)
        
        n_inverter = 1
        
        # if gdf.loc[i, 'Bruttoleistung'] > 1.0:
        #     system_brutto_power = gdf.loc[i, 'Bruttoleistung']
        # else:
        system_brutto_power = gdf.loc[i, 'Bruttoleistung'] * 1000 # in W

        if np.isnan(gdf.loc[i, 'AnzahlModule']):
            # 'AnzahlModule' is nan
            n_modules = math.ceil(system_brutto_power/ av_module_pwr) # 300 W per module
            module_av_power = system_brutto_power / n_modules
        else:
            # 'AnzahlModule' not nan
            n_modules = gdf.loc[i, 'AnzahlModule']
            module_av_power = ((system_brutto_power
                                / n_modules)
                                )
        # if module_av_power > (module_lib.loc['Impo',:] * module_lib.loc['Vmpo',:]).max():
        #     n_inverter += 1
        #     module_av_power = module_av_power / n_inverter
            
        module_list = []
        while len(module_list) == 0:
            for module in module_lib.columns:
                if (module_av_power * 0.95 
                    < (module_lib[module].Impo
                       * module_lib[module].Vmpo)
                    < module_av_power * 1.05):
                    module_list.append(module)
                    
            n_modules += 1
            module_av_power = ((system_brutto_power
                                / n_modules)
                                )
            print(f"No sufficient module found for '{gdf.loc[i, 'NameStromerzeugungseinheit']}'. Increasing module number to {n_modules}.")

        module = module_list[random.randint(0, len(module_list) - 1)]
        # print(f"Module '{module}' selected for '{gdf.loc[i, 'NameStromerzeugungseinheit']}'.")
        
        inverter_list = []
        
        if np.isnan(gdf.loc[i, 'ZugeordneteWirkleistungWechselrichter']):
            inv_assigned_pwr = gdf.loc[i, 'Nettonennleistung'] *1000
        else:
            inv_assigned_pwr = gdf.loc[i, 'ZugeordneteWirkleistungWechselrichter'] *1000
            
        while len(inverter_list) == 0:
            inv_ac_pwr = (inv_assigned_pwr
                          / n_inverter) # in W
            for inverter in inverter_lib.columns:
                    if inv_ac_pwr * 1.05 > inverter_lib[inverter].Paco > inv_ac_pwr * 0.95:
                        inverter_list.append(inverter)
            
            n_inverter += 1
            print(f"No sufficient inverter found for '{gdf.loc[i, 'NameStromerzeugungseinheit']}'. Increasing inverter number to {n_inverter}.")

        inverter = inverter_list[random.randint(0, len(inverter_list) - 1)]
        modules_per_inverter = n_modules / n_inverter
        # print(f"Inverter '{inverter}' with {modules_per_inverter} modules selected for '{gdf.loc[i, 'NameStromerzeugungseinheit']}'.")
        # Function needs to be adjusted so that the modules are not only assigned to one inverter, 
        # depending on the largest inverter in the inverter_lib
        # run = True
        # while run:
        if (round(modules_per_inverter, 0) % 3 == 0 
            and (module_lib[module].Impo 
                    * module_lib[module].Vmpo 
                    * modules_per_inverter)):
            modules_per_string = round(modules_per_inverter, 0) / 3
            strings_per_inverter = 3
            # run = False
        elif (round(modules_per_inverter, 0) % 4 == 0 and 
                (module_lib[module].Impo 
                * module_lib[module].Vmpo 
                * modules_per_inverter)):
            modules_per_string = round(modules_per_inverter, 0) / 4
            strings_per_inverter = 4
            # run = False
        else:
            modules_per_string = round(modules_per_inverter, 0) / 2
            strings_per_inverter = 2
            # run = False
        # else:
        #     # n_inverter += 1
        #     # modules_per_inverter = n_modules / n_inverter
        #     # run = True
        #     raise Exception(f"No sufficient inverter found for '{gdf.loc[i, 'NameStromerzeugungseinheit']}'.")
        
        pv_system_lst = []
        for _ in range(n_inverter):
            pv = Photovoltaic(
                unit='kW',
                identifier=gdf.loc[i, 'EinheitMastrNummer'],
                latitude=gdf.loc[i, 'Breitengrad'],
                longitude=gdf.loc[i, 'Laengengrad'],
                environment=ref_env,
                module_lib="SandiaMod",
                module= module,
                inverter_lib="cecinverter",
                inverter= inverter,
                surface_tilt=gdf.loc[i, 'HauptausrichtungNeigungswinkel'],
                surface_azimuth=gdf.loc[i, 'Hauptausrichtung'],
                modules_per_string= modules_per_string,
                strings_per_inverter= strings_per_inverter,
                temp_lib='sapm',
                temp_model='open_rack_glass_glass'
            )
            
            pv_system_lst.append(pv)
            
        pv_systems_dict[gdf.loc[i, 'EinheitMastrNummer']] = pv_system_lst
    
    return pv_systems_dict


def prepare_pv_time_series_mastr(pv_systems_dict):
    """
    Prepares time series data for multiple PV systems.
    Iterates over a dictionary of PV systems, where each key corresponds to a group name and each value is a list of PV system objects.
    For each PV system in the list, calls its `prepare_time_series()` method to generate or process its time series data.
    Args:
        pv_systems_dict (dict): A dictionary mapping group names (str) to lists of PV system objects. Each PV system object must implement a `prepare_time_series()` method.
    Returns:
        None
    """
    for name, pv_system_lst in tqdm(pv_systems_dict.items()):
        for pv_system in pv_system_lst:

            pv_system.prepare_time_series()
            


def aggregate_pv_time_series(pv_systems_dict):
    """
    Aggregates the time series data of multiple PV systems by summing their time series for each system name.
    Args:
        pv_systems_dict (dict): A dictionary where each key is a PV system name (str) and each value is a list of PV system objects.
                                Each PV system object is expected to have a 'timeseries' attribute (e.g., a list or numpy array).
    Returns:
        dict: A dictionary with the same keys as `pv_systems_dict`, where each value is the aggregated (summed) time series for that system name.
    Note:
        - The function assumes that the 'timeseries' attribute of each PV system object is of a type that supports the '+=' operator (e.g., list or numpy array).
        - The function uses tqdm to display a progress bar during aggregation.
    """
    pv_systems_aggregated = {k: [] for k in pv_systems_dict.keys()}

    for name, pv_system_lst in tqdm(pv_systems_dict.items()):
        for pv_system in pv_system_lst:
            if len(pv_systems_aggregated[name])==0:
                pv_systems_aggregated[name] = pv_system.timeseries
            else:
                pv_systems_aggregated[name] += pv_system.timeseries
            
    return pv_systems_aggregated

### WINDENERGY ###
df_efficiency_curve = pd.read_csv(DATA_DIR / 'median_windpower_curve.csv')
def wind_turbine_matching(gdf):
    """
    Matches wind turbine types from a GeoDataFrame to the closest entries in a turbine database using fuzzy string matching.
    Parameters:
        gdf (pandas.DataFrame or geopandas.GeoDataFrame): 
            A DataFrame containing a column 'Typenbezeichnung' with wind turbine type names to be matched.
    Returns:
        pandas.DataFrame or geopandas.GeoDataFrame:
            The input DataFrame with an additional column 'WPLTurbine' containing the best-matched turbine type from the database.
    Notes:
        - Uses fuzzy string matching (fuzz.ratio) to compare 'Typenbezeichnung' values with 'turbine_type' and 'name' fields in the turbine database.
        - The turbine database is retrieved via wpl.data.store_turbine_data_from_oedb().
        - Prints a mapping of original turbine types to their best matches.
    """
    
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

def init_windturbines_mastr(gdf,
                            environment,
                            wind_speed_model = "logarithmic",
                            density_model = "ideal_gas",
                            temperature_model = "linear_gradient",
                            power_output_model = "power_curve", # "power_coefficient_curve"or 'power_curve'
                            density_correction = True,
                            obstacle_height = 0,
                            hellman_exp = None):
    """
    Initializes a dictionary of WindPower objects for wind turbines based on a GeoDataFrame.
    Parameters:
        gdf (pandas.DataFrame or geopandas.GeoDataFrame): 
            DataFrame containing wind turbine data. Must include columns:
            'EinheitMastrNummer', 'Breitengrad', 'Laengengrad', 'WPLTurbine', 
            'Nabenhoehe', and 'Rotordurchmesser'.
        environment (object): 
            The environment object to be passed to each WindPower instance.
        wind_speed_model (str, optional): 
            Model to use for wind speed calculation. Default is "logarithmic".
        density_model (str, optional): 
            Model to use for air density calculation. Default is "ideal_gas".
        temperature_model (str, optional): 
            Model to use for temperature calculation. Default is "linear_gradient".
        power_output_model (str, optional): 
            Model to use for power output calculation. Options are "power_curve" or "power_coefficient_curve". Default is "power_curve".
        density_correction (bool, optional): 
            Whether to apply air density correction. Default is True.
        obstacle_height (float, optional): 
            Height of obstacles affecting wind profile. Default is 0.
        hellman_exp (float or None, optional): 
            Hellman exponent for wind profile calculation. Default is None.
    Returns:
        dict: 
            Dictionary mapping 'EinheitMastrNummer' to WindPower objects, each representing a wind turbine.
    """
    
    windturbines_dict = {}
    turbine_database = wpl.data.store_turbine_data_from_oedb()
    
    for i in gdf.index:
        if turbine_database.loc[turbine_database.turbine_type == gdf.loc[i, 'WPLTurbine']].has_power_curve.item() == True:
            windturbines_dict[gdf.loc[i, 'EinheitMastrNummer']] = WindPower(
                unit="kW",
                identifier=gdf.loc[i, 'EinheitMastrNummer'],
                environment=environment,
                turbine_type=gdf.loc[i, 'WPLTurbine'],
                hub_height=gdf.loc[i, 'Nabenhoehe'],
                rotor_diameter=gdf.loc[i, 'Rotordurchmesser'],
                fetch_curve = 'power_curve',
                data_source="oedb",
                wind_speed_model=wind_speed_model,
                density_model=density_model,
                temperature_model=temperature_model,
                power_output_model=power_output_model,
                density_correction=density_correction,
                obstacle_height=obstacle_height,
                hellman_exp=hellman_exp,
                )
        else:
            windturbines_dict[gdf.loc[i, 'EinheitMastrNummer']] = WindPower(
                unit="kW",
                identifier=gdf.loc[i, 'EinheitMastrNummer'],
                environment=environment,
                turbine_type=gdf.loc[i, 'WPLTurbine'],
                hub_height=gdf.loc[i, 'Nabenhoehe'],
                rotor_diameter=gdf.loc[i, 'Rotordurchmesser'],
                fetch_curve = 'power_curve',
                data_source=path_to_power_curve, # Uses the median wind power curve instead of oedb data
                wind_speed_model=wind_speed_model,
                density_model=density_model,
                temperature_model=temperature_model,
                power_output_model=power_output_model,
                density_correction=density_correction,
                obstacle_height=obstacle_height,
                hellman_exp=hellman_exp,
                )
            

        
    return windturbines_dict

def prepare_wind_time_series_mastr(gen_dict):
        """
        Prepares wind generation time series for each generator in the provided dictionary.
        Iterates over the given dictionary of generator objects and calls the `prepare_time_series`
        method on each generator to initialize or update its time series data.
        Args:
            gen_dict (dict): A dictionary where keys are generator identifiers and values are
                generator objects that implement a `prepare_time_series` method.
        Returns:
            None
        """
        
        for key, value in gen_dict.items():
            if value.data_source == 'oedb':
                value.prepare_time_series()
            else:
                # Check if norm_power_curve exists in the current scope
                if 'norm_power_curve' not in locals() and 'norm_power_curve' not in globals():
                    norm_power_curve = pd.read_csv(path_to_power_curve)
                if 'turbine_database' not in locals() and 'turbine_database' not in globals():
                    turbine_database = wpl.data.store_turbine_data_from_oedb()
                    
                nom_power = turbine_database.loc[turbine_database.turbine_type == value.turbine_type].nominal_power.item()
                
                turbine_data = {
                    'nominal_power': nom_power,
                    'hub_height': value.hub_height,
                    'rotor_diameter': value.rotor_diameter,
                    'power_curve': wpl.create_power_curve(
                        wind_speed=norm_power_curve['wind_speed'],
                        power=norm_power_curve['value'] * nom_power, # windpowerlib works with Watt
                    )
                }
                
                value.WindTurbine = WindTurbine(**turbine_data)
                value.ModelChain = ModelChain(
                    power_plant=value.WindTurbine,
                    wind_speed_model=value.wind_speed_model,
                    density_model=value.density_model,
                    temperature_model=value.temperature_model,
                    power_output_model=value.power_output_model,
                    density_correction=value.density_correction,
                    obstacle_height=value.obstacle_height,
                    hellman_exp=value.hellman_exp
                )
                value.ModelChain.run_model(value.environment.wind_data)
                value.timeseries = value.ModelChain.power_output / 1000  # Convert from W to kW

def aggregate_wind_time_series(gen_dict):
    """
    Aggregates wind generation time series data from a dictionary of generator objects.
    Parameters:
        gen_dict (dict): A dictionary where each value is an object with a 'timeseries' attribute,
                         which is a pandas Series or DataFrame representing wind generation over time.
    Returns:
        pandas.DataFrame: A DataFrame containing the aggregated wind generation time series,
                          where each time step is the sum of all input time series.
    Notes:
        - Assumes that all 'timeseries' attributes are aligned on the same time index.
        - If 'gen_dict' is empty, returns an empty DataFrame.
    """
    
    time_series = pd.DataFrame()
    
    for key, value in gen_dict.items():
        if time_series.empty:
            time_series = value.timeseries
        else:
            time_series = time_series.add(value.timeseries, fill_value=0)
    
    return time_series


if __name__ == "__main__":
    
    #mastr_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'open-mastr.db'))
    location = 'Aachen'
    start = "2015-07-07 00:00:00"
    end = "2015-07-07 23:45:00"
    mastr_db_path = r'C:\Users\mashu\.open-MaStR\data\sqlite\open-mastr.db'

    gdf_solar, city_district = prepare_solar_data(location=location, mastr_db_path=mastr_db_path)
    gdf_solar = revise_power_values(gdf_solar)
    ref_env = Environment(start=start, end=end)
    ref_env.get_dwd_pv_data(lat=city_district.lat[0], lon=city_district.lon[0])

    pv_systems_dict = pick_pvsystem_mastr(gdf_solar.head(), ref_env) # Change to choose all PV systems later
    prepare_pv_time_series_mastr(pv_systems_dict)
    pv_systems_aggregated = aggregate_pv_time_series(pv_systems_dict)

    fig, ax = plt.subplots()
    for name, pv_system in pv_systems_aggregated.items():
        pv_system.plot(ax=ax, label=name)

    plt.show()


    ### Windenergie ###
    mastr_db_path = r'C:\Users\mashu\.open-MaStR\data\sqlite\open-mastr.db'
    gdf_wind, city_district = prepare_wind_data(location=location, mastr_db_path=mastr_db_path)
    gdf_wind = wind_turbine_matching(gdf_wind)

    ref_env.get_dwd_wind_data(lat=city_district.centroid.y, lon=city_district.centroid.x)
    
    windturbines_dict = init_windturbines_mastr(gdf_wind, environment=ref_env)
    prepare_wind_time_series_mastr(windturbines_dict)
    windturbines_aggregated = aggregate_wind_time_series(windturbines_dict)
    
    pd.DataFrame({key: windturbines_dict[key].timeseries for key in windturbines_dict.keys()}).plot()
    plt.title('Wind Energy Generation Time Series')
    plt.xlabel('Time')
    plt.ylabel('Power (kW)')
    plt.legend(title='Wind Turbines', loc='lower center', bbox_to_anchor=(0.5, -0.8), ncol=3)
        
    plt.show()
    