# Installing Relevant libraries
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import datetime
import streamlit as st
from st_files_connection import FilesConnection
import os
import osmnx as ox

from src.visualization import fig_5, fig_7, fig_8, fig_9, fig_5_plotly
from src.network import pp_networks
import matplotlib.pyplot as plt
from vpplib.battery_electric_vehicle import BatteryElectricVehicle
from vpplib.environment import Environment
from vpplib.heat_pump import HeatPump
from vpplib.user_profile import UserProfile
from vpplib.photovoltaic import Photovoltaic
from vpplib.wind_power import WindPower
from vpplib import ElectricalEnergyStorage

from technologies.bev import battery_electric_vehicle_settings
from technologies.heat_pump_settings import heatpump_settings
from technologies.photovoltaics import pv_settings
from technologies.wind_energy import wind
from technologies.electrical_storage import electrical_storage

from src.mastr import prepare_solar_data, prepare_wind_data, prepare_storage_data, prepare_grid_connections_data
from src.mastr import fetch_solar, fetch_wind, fetch_storage



# Import validation and error handling utilities with fallback
try:
    from src.utils.validation import InputValidator, validate_energy_system_inputs, display_validation_results, validate_location_selection
    from src.utils.error_handling import (
        handle_database_errors, handle_api_errors, handle_data_processing_errors, 
        safe_file_operation, log_user_action, show_loading_with_progress
    )
    ADVANCED_VALIDATION_AVAILABLE = True
except ImportError:
    # Fallback if utils are not available
    st.warning("⚠️ Advanced validation and error handling features not fully available")
    ADVANCED_VALIDATION_AVAILABLE = False
    
    # Define minimal fallback functions
    def log_user_action(action, details=None):
        pass
    
    def handle_database_errors(func):
        return func
    
    def handle_api_errors(func):
        return func
    
    def handle_data_processing_errors(func):
        return func

from src.mastr import get_unique_solar_locations, get_unique_wind_locations, get_unique_storage_locations
from src.config import MASTR_DB_PATH

# Use centralized config path (can be overridden if needed)
# IMPORTANT: Update this path to match your open-MaStR database location
# Default open-MaStR location: 'C:/Users/<username>/.open-MaStR/data/sqlite/open-mastr.db'
mastr_db_path = str(MASTR_DB_PATH)
# Alternative: Uncomment and update the line below with your actual database path
# mastr_db_path = 'C:/Users/mashu/.open-MaStR/data/sqlite/open-mastr.db'

# =============================================================================
# PERFORMANCE CONFIGURATION
# =============================================================================
# Configure caching TTL (Time To Live) values for different operations
CACHE_CONFIG = {
    'DATA_LOAD_TTL': 3600,      # 1 hour for static data files
    'DATABASE_TTL': 1800,       # 30 minutes for database queries  
    'VISUALIZATION_TTL': 600,   # 10 minutes for plots and maps
    'ENVIRONMENT_TTL': 3600,    # 1 hour for vpplib Environment objects
}

st.set_page_config(page_title='VISE-D Dashboard', 
                    page_icon=':bar_chart:',
                    layout='centered',
                    initial_sidebar_state='expanded'
                    )

# Add cache management in sidebar
with st.sidebar:
    st.markdown("---")
    st.markdown("**⚡ Performance**")
    if st.button("🗑️ Cache leeren", help="Alle zwischengespeicherten Daten l\u00f6schen"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("✅ Cache geleert!")
        st.rerun()

st.write('Willkommen beim VISE-D Dashboard! Die Seite befindet sich noch in der Entwicklung.')

# =============================================================================
# CACHED DATA LOADING FUNCTIONS
# =============================================================================

@st.cache_data(ttl=CACHE_CONFIG['DATA_LOAD_TTL'])
def load_example_data():
    """Load example data with caching for performance"""
    try:
        return pd.read_csv('./data/figures/example_data_10000.csv')
    except FileNotFoundError:
        st.error("❌ Example data file not found. Please check the file path.")
        return pd.DataFrame()  # Return empty DataFrame as fallback

@st.cache_data(ttl=CACHE_CONFIG['DATABASE_TTL'])
def get_cached_unique_locations(location_type: str, mastr_db_path: str):
    """Get unique locations with caching to avoid repeated database queries"""
    try:
        if location_type == "solar":
            return get_unique_solar_locations(mastr_db_path=mastr_db_path)
        elif location_type == "wind":
            return get_unique_wind_locations(mastr_db_path=mastr_db_path)
        elif location_type == "storage":
            return get_unique_storage_locations(mastr_db_path=mastr_db_path)
        else:
            return []
    except Exception as e:
        st.error(f"❌ Failed to load {location_type} locations: {str(e)}")
        return []

@st.cache_data(ttl=CACHE_CONFIG['DATABASE_TTL'])
def get_cached_mastr_data(location: str, data_type: str, mastr_db_path: str):
    """Cache expensive MaStR database operations"""
    try:
        if data_type == "solar":
            return prepare_solar_data(location=location, mastr_db_path=mastr_db_path)
        elif data_type == "wind":
            return prepare_wind_data(location=location, mastr_db_path=mastr_db_path)
        elif data_type == "storage":
            return prepare_storage_data(location=location, mastr_db_path=mastr_db_path)
        else:
            return None, None
    except Exception as e:
        st.error(f"❌ Failed to load {data_type} data for {location}: {str(e)}")
        return None, None

@st.cache_data(ttl=CACHE_CONFIG['VISUALIZATION_TTL'])
def create_wind_simulation_display(results):
    """Display wind simulation results in a formatted way"""
    st.subheader("Kreisinformationen")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"Kreiszentrum (Längengrad, Breitengrad): {results['kreiszentrum']}")
    with col2:
        st.write(f"Kreisradius: {results['radius']}")

    st.subheader("Simulationsergebnisse")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Anzahl von Windturbinen", results['num_turbines'])
    with col2:
        st.metric("Gesamtenergierzeugung pro Jahr", results['annual_energy'])
    with col3:
        st.metric("Volllastunden", results['full_load_hours'])

    st.subheader("Stromproduktion der Windturbinen im Jahresverlauf (MW)")
    st.plotly_chart(results['timeline_fig'], use_container_width=True)

@st.cache_data(ttl=CACHE_CONFIG['VISUALIZATION_TTL'])
def create_cached_violin_plot(df, ev_penetration, curtailment, selected_grid_type, 
                             selected_hp_diffusion, selected_pv_storage_diffusion,
                             selected_wholesale_tariff, selected_grid_usage_fees):
    """Cache violin plot generation for better performance"""
    df_selected = df[(df['diffusion_evs'] == ev_penetration) 
                    & (df['curtailment'] == curtailment) 
                    & (df['grid_type'] == selected_grid_type)
                    & (df['diffusion_hps'] == selected_hp_diffusion)
                    & (df['diffusion_pv_storage'] == selected_pv_storage_diffusion)
                    & (df['tariff_wholesale'] == selected_wholesale_tariff)
                    & (df['tariff_grid_usage_fee'] == selected_grid_usage_fees)
                    ]
    
    return px.violin(df_selected, 
                    y='value', 
                    box=True, 
                    points="all"
                    )

@st.cache_resource(ttl=CACHE_CONFIG['ENVIRONMENT_TTL'])
def get_cached_environment(start: str, end: str, lat: float = None, lon: float = None):
    """Cache expensive Environment operations"""
    try:
        env = Environment(start=start, end=end)
        if lat is not None and lon is not None:
            env.get_dwd_pv_data(lat=lat, lon=lon)
        return env
    except Exception as e:
        st.error(f"❌ Failed to create environment: {str(e)}")
        return None

@st.cache_data(ttl=CACHE_CONFIG['VISUALIZATION_TTL'])
def create_cached_scatter_map(_gdf_data, lat_col: str, lon_col: str, hover_data: list, 
                             center_lat: float, center_lon: float, color: str = 'red',
                             title: str = "Installation Map"):
    """Cache expensive map creation operations"""
    try:
        fig = px.scatter_mapbox(
            _gdf_data,
            lat=lat_col,
            lon=lon_col,
            size_max=45,
            color_discrete_sequence=[color],
            zoom=10,
            center={"lat": center_lat, "lon": center_lon},
            mapbox_style='open-street-map',
            hover_data=hover_data,
            title=title
        )
        return fig
    except Exception as e:
        st.error(f"❌ Failed to create map: {str(e)}")
        return None

# Load cached data
df = load_example_data()


def update_violin_plot(df,
                       ev_penetration, 
                       curtailment,
                       selected_grid_type, 
                       selected_hp_diffusion, 
                       selected_pv_storage_diffusion,
                       selected_wholesale_tariff, 
                       selected_grid_usage_fees):
    """Updated to use cached plotting function"""           
    return create_cached_violin_plot(
        df, ev_penetration, curtailment, selected_grid_type,
        selected_hp_diffusion, selected_pv_storage_diffusion,
        selected_wholesale_tariff, selected_grid_usage_fees
    )


def research_results():
    st.write('## Integration von E-Fahrzeugen in Verteilnetze - Untersuchung der Auswirkungen \
        verschiedener DSO-Eingriffsstrategien auf optimiertes Laden')
    st.write('### Kurzfassung')
    st.write(
        'Die Einführung von Elektrofahrzeugen (EVs) und die Einführung variabler Stromtarife erhöhen die \
        Spitzennachfrage und das Risiko von Überlastungen in den Verteilnetzen. Um kritische Netzsituationen \
        abzuwenden und teure Netzerweiterungen zu vermeiden, müssen Verteilnetzbetreiber (DSOs) über \
        Eingriffsrechte verfügen, die es ihnen ermöglichen, Ladevorgänge zu drosseln. Es sind verschiedene \
        Drosselungsstrategien möglich, die sich in der räumlich-zeitlichen Differenzierung und der möglichen \
        Diskriminierung unterscheiden. Die Bewertung verschiedener Strategien ist jedoch \
        aufgrund des Zusammenspiels von wirtschaftlichen Faktoren, technischen Anforderungen und regulatorischen \
        Beschränkungen komplex – eine Komplexität, die in der aktuellen Literatur nicht vollständig behandelt \
        wird. Unsere Studie stellt ein ausgeklügeltes Modell zur Optimierung von Ladestrategien für Elektrofahrzeuge \
        vor, um diese Lücke zu schließen. Dieses Modell berücksichtigt verschiedene Tarifmodelle (Festpreis, \
        Time-of-Use und Real-Time) und bezieht (grundlegende, variable und intelligente) DSO Interventionen in seinen Optimierungsrahmen \
        ein. Basierend auf dem Modell analysieren wir den Flexibilitätsbedarf und die Gesamtstromkosten aus der Sicht \
        der Nutzer. Bei der Anwendung unseres Modells auf ein synthetisches Verteilernetz stellen wir fest, dass \
        flexible Tarife den Verbrauchern nur marginale wirtschaftliche Vorteile bieten und das Risiko von Netzengpässen \
        aufgrund von Herdenverhalten erhöhen. Alle Kürzungsstrategien verringern Engpässe effektiv, wobei variable \
        Kürzungen eine räumlich-zeitliche Differenzierung aufweisen und sich der Optimalität in Bezug auf den \
        Flexibilitätsbedarf annähern. Bemerkenswert ist, dass die Anwendung von Kürzungen aus der Sicht der Nutzer \
        die Kosteneinsparungen nicht wesentlich senkt.'
    )
    st.write('*Die Veröffentlichung finden Sie [hier](https://www.sciencedirect.com/science/article/pii/S0306261924021585?dgcid=author) (Englisch).*')

    st.write('### Großhandelspreise und abgeleitete durchschnittliche Verbraucherpreise für Festtarif und ToU-Tarif')
    st.pyplot(fig=fig_5(), clear_figure=True)
    # st.plotly_chart(fig_5_plotly())
    st.write(
        'Hier sind die Strompreise für die Kumulierte Verteilung der angenommenen Stromgroßhandelspreise \
        für 2030 (links) und die endgültige Zusammensetzung der Strompreise für den Fix- und ToU-Tarif \
        für 2030 (rechts) dargestellt. Der ToU-Tarif besteht aus drei Acht-Stunden-Zeitfenstern \
        mit unterschiedlichen Preisen. Der erste ToU-Zeitraum (0–8) umfasst die ersten acht Stunden des Tages. \
        Beim RT-Tarif werden die Netznutzungsgebühr, Abgaben und Steuern zum Großhandelspreis addiert, \
        was zu unterschiedlichen Preisen für jedes Intervall führt.'
    )

    st.write('### Wirtschaftliche Auswirkungen unterschiedlicher Tarifstrukturen für das Laden von Elektrofahrzeugen')
    st.pyplot(fig=fig_7(), clear_figure=True)
    st.write(
        'In der Abbildung sind die Auswirkungen von Tarifstrukturen auf optimale Ladestrategien \
        und damit verbundene Ladekosten ohne Drosselung dargestellt. \
        Das linke Segment der Abbildung zeigt konkret die Nachfragemuster, die an einen einzelnen Transformator für drei \
        Tage angelegt sind. Die rechts dargestellte Verteilung der Ladekosten wird jährlich berechnet und umfasst alle \
        Fahrzeuge, die auf die zwölf Netze verteilt sind. Jede Zeile spiegelt die Ergebnisse für eine bestimmte \
        Durchdringungsrate wider.'
    )

    st.write('### Flexibilität durch Elektrofahrzeuge')
    st.pyplot(fig=fig_8(), clear_figure=True)
    st.write(
        'Die obige Abbildung zeigt einen signifikanten Trend: Die Einführung zeitvariabler \
        Tarife, wie ToU- und RT-Tarife, korreliert direkt mit einem erhöhten \
        Flexibilitätsbedarf zur Vermeidung von Engpässen. Wenn man eine 30%ige oder \
        sogar 50%ige EV-Durchdringungsrate betrachtet, ist eine Einschränkung bei festen Tarifen nicht erforderlich. \
        Mit der Einführung dynamischer Tarife wird dies jedoch notwendig. \
        Das Ausmaß des Anstiegs des Flexibilitätsbedarfs aufgrund der Einführung \
        der dynamischen Tarife ist nicht konstant, sondern hängt vom \
        Verbreitungsgrad von Elektrofahrzeugen ab.'
    )

    st.write('### Vergleich der Kostendeltas')
    st.pyplot(fig=fig_9(), clear_figure=True)
    st.write(
        'Die Abbildung veranschaulicht eine vergleichende Analyse der jährlichen Schwankungen der \
        Stromkosten unter Berücksichtigung der ToU- und RT-Tarife, der EV-Durchdringung \
        und die drei verschiedenen Abregelungsstrategien. Der Vergleich wird durchgeführt \
        mit dem Szenario mit festem Tarif ohne Drosselung. Dabei \
        werden die Kostenunterschiede für den Festtarif nicht dargestellt, da diese \
        Tarifstruktur unabhängig von der eingesetzten Strategie gleichbleibende Kosten verursacht. /n \
        Anmerkung: "before" bezieht sich auf den hypothetischen Fall, dass die Abrechnung ausschließlich \
        auf der Grundlage von Preissignalen erfolgt, bevor Drosselungsstrategien eingesetzt werden.'
    )

    # Footer with Logos
    footer_cols = st.columns(2)

    with footer_cols[0]:
        st.markdown(
            """
            <div style="background-color: white; padding: 10px; text-align: center; border-radius: 15px;">
                <img src="https://smart-energy-nrw.web.th-koeln.de/wp-content/uploads/2023/10/VISE_D_neu-1024x470.png" \
                    alt="VISE-D Logo" style="width: auto; height: 100px;">
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with footer_cols[1]:
        st.markdown(
            """
            <div style="background-color: white; padding: 10px; text-align: center; border-radius: 15px;">
                <img src="https://smart-energy-nrw.web.th-koeln.de/wp-content/uploads/2023/01/Logo_MWIKEPixel.png" \
                    alt="MWIKE Logo" style="width: auto; height: 70px;">
            </div>
            """,
            unsafe_allow_html=True
        )

   
    
def network_calculations():
    pp_networks()
    

# Initialize session state for BEV settings if not already present
if "bev_settings" not in st.session_state:
        st.session_state.bev_settings = {
        "max_battery_capacity": 0.0,
        "min_battery_capacity": 0.0,
        "battery_usage": 0.0,
        "charging_power": 0.0,
        "charging_efficiency": 0.0,
        "load_degradation_begin": 0.0,
        "user_profile": "None",
        "selected_environment": "None",
        "start_time": datetime.time(0, 0,0),
        "end_time": datetime.time(0, 0,0),
        "timebase": 15
    }


def bev_settings():
   
    """_summary_
    This function sets up the settings for the Battery Electric Vehicle (BEV) simulation.
    It includes a form for user inputs such as maximum and minimum battery capacity, battery usage,
    charging power, charging efficiency, load degradation begin, and user profile.
    It also initializes the BEV object with these settings and prepares the time series data for simulation.
    The function displays the time series data and plots it using Matplotlib.
    The function is designed to be used within a Streamlit application.
    
    Args:
        form_key_suffix (str): A suffix to be added to the form key for uniqueness.
        
    Returns:
        None: The function does not return any value. It updates the session state and displays data in the Streamlit app.
        
    """
   
   
   
   
   # with st.expander("Battery Electric Vehicle (BEV)"):
   
    battery_electric_vehicle_settings(form_key_suffix="bev1")
    
    with st.form(key="bev_simulation_form_1"):
                    # BEV simulation button
                    bev_simulation_button = st.form_submit_button("Simulate BEV")
                    
                    if bev_simulation_button:
                        start = "2015-06-01 00:00:00"
                        end = "2015-06-01 23:45:00"
                        timestamp_int = 48
                        timestamp_str = "2015-06-01 12:00:00"
                        timebase = 15
                        env = Environment(start=start, end=end, timebase=timebase)
                        
                        # Initialize BEV with form inputs
                        st.session_state.bev = BatteryElectricVehicle(
                            unit="kW",
                            identifier="bev_1",
                            environment=env,
                            battery_max=st.session_state.bev_settings["max_battery_capacity"],
                            battery_min=st.session_state.bev_settings["min_battery_capacity"],
                            battery_usage=st.session_state.bev_settings["battery_usage"],
                            charging_power=st.session_state.bev_settings["charging_power"],
                            load_degradation_begin=st.session_state.bev_settings["load_degradation_begin"],
                            charge_efficiency=st.session_state.bev_settings["charging_efficiency"]
                        )
                    
                        st.session_state.bev.prepare_time_series()
                        st.write("**Time Series Data (First 5 Rows):**")
                        st.dataframe(st.session_state.bev.timeseries)  # Display the timeseries data for debugging

                        # Create a Matplotlib figure
                        fig, ax = plt.subplots(figsize=(16, 9))
                        st.session_state.bev.timeseries.plot(ax=ax)  # Plot the timeseries on the provided axes
                        ax.set_title("BEV Time Series")
                        ax.set_xlabel("Time")
                        ax.set_ylabel("Value (kW)")
                        plt.tight_layout()

                        # Display the plot in Streamlit
                        st.pyplot(fig)

                # # # Rest of the functions remain unchanged
                # def test_value_for_timestamp(bev, timestamp):
                #     timestepvalue = bev.value_for_timestamp(timestamp)
                #     st.write("**Value for Timestamp:**")
                #     st.write(timestepvalue)

                # def test_observations_for_timestamp(bev, timestamp):
                #     observation = bev.observations_for_timestamp(timestamp)
                #     st.write("**Observations for Timestamp:**")
                #     st.write(observation)

        
        


def hydrogen_electrolyzer_settings():   
    
    """_summary_
    This function sets up the settings for the Hydrogen Electrolyzer simulation.
    It includes a sidebar for user inputs such as power and pressure settings.
    It initializes the Hydrogen Electrolyzer settings in the session state and updates them based on user input.
    It displays the current settings in a styled DataFrame and provides gauges for visualizing the power and pressure values.
    The function is designed to be used within a Streamlit application.
    Args:
        Inputs etc.
    Returns
        None: The function does not return any value. It updates the session state and displays data in the Streamlit app.
        """ 
    st.title("Hydrogen Electrolyzer Settings")
    # Layout Section
    with st.sidebar:
        st.subheader("Hydrogen Electrolyzer Settings")

        # Submit Button
        col5, _ = st.columns([2, 3])
        with col5:
            submit = st.button("Submit", key="submit_hydrogen_settings")

        # Callback Logic (Simulated)
        if "hydrogen_settings" not in st.session_state:
            st.session_state.hydrogen_settings = {"Power_Electrolyzer": 15000.0, "Pressure_Hydrogen": 30.0}

        if submit:
            st.session_state.hydrogen_settings = {
                "Power_Electrolyzer": power_electrolyzer,
                "Pressure_Hydrogen": pressure_hydrogen
            }

    data = {
            "Metric": ["Power Electrolyzer", "Pressure Hydrogen"],
            "Value": [
                st.session_state.hydrogen_settings["Power_Electrolyzer"],
                st.session_state.hydrogen_settings["Pressure_Hydrogen"]
            ],
            "Unit": ["kW", "bar"]
        }        
    df = pd.DataFrame(data)
    st.dataframe(
            df.style.format({"Value": "{:.1f}"}).set_properties(**{
                'text-align': 'left',
                'font-size': '14px',
                'padding': '10px',
        'border': '1px solid #ddd',
                'background-color': '#f9f9f9'
            }).set_table_styles([
                {'selector': 'th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('font-weight', 'bold'), ('text-align', 'left'), ('padding', '10px'), ('border', '1px solid #ddd')]},
                {'selector': 'td', 'props': [('border', '1px solid #ddd')]}
            ]),
            use_container_width=True,
            hide_index=True
        )



    # Sidebar for input values
    st.sidebar.header("Electrolyzer Settings Input")
    power_electrolyzer = st.sidebar.number_input("Power Electrolyzer (kW)", step=100.0, key="input_electrolyzer_power")
    pressure_hydrogen = st.sidebar.number_input("Pressure Hydrogen (Pa)", step=1.0, key="input_electrolyzer_pressure")

    # Gauge for Power Electrolyzer
    fig_power = go.Figure(go.Indicator(
    mode="gauge+number",
    value=power_electrolyzer,
    title={'text': "Power Electrolyzer (kW)"},
    gauge={
        'axis': {'range': [0, max(power_electrolyzer * 1.5, 1000)]},  # Dynamic range
        'bar': {'color': "#FF4B4B"},
        'steps': [
            {'range': [0, power_electrolyzer * 0.5], 'color': "#4BFF4B"},
            {'range': [power_electrolyzer * 0.5, power_electrolyzer * 0.8], 'color': "#FFFF4B"},
            {'range': [power_electrolyzer * 0.8, max(power_electrolyzer * 1.5, 1000)], 'color': "#FF4B4B"}
        ]
    }
))

    # Gauge for Pressure Hydrogen
    fig_pressure = go.Figure(go.Indicator(
    mode="gauge+number",
    value=pressure_hydrogen,
    title={'text': "Pressure Hydrogen (Pa)"},
    gauge={
        'axis': {'range': [0, max(pressure_hydrogen * 1.5, 100)]},  # Dynamic range
        'bar': {'color': "#FF4B4B"},
        'steps': [
            {'range': [0, pressure_hydrogen * 0.5], 'color': "#4BFF4B"},
            {'range': [pressure_hydrogen * 0.5, pressure_hydrogen * 0.8], 'color': "#FFFF4B"},
            {'range': [pressure_hydrogen * 0.8, max(pressure_hydrogen * 1.5, 100)], 'color': "#FF4B4B"}
        ]
    }
))


def heatpump_configuration():
    
    """_summary_
    This function sets up the settings for the Heat Pump simulation.
    It includes a form for user inputs such as heat pump type, heat system temperature, electrical
    power, thermal power, ramp up time, ramp down time, minimum run time, and minimum stop time.
    It initializes the Heat Pump object with these settings and prepares the time series data for simulation.
    The function displays the time series data and plots it using Matplotlib.
    The function is designed to be used within a Streamlit application.
    Args:
        form_key_suffix (str): A suffix to be added to the form key for uniqueness.
    Returns:
        None: The function does not return any value. It updates the session state and displays data
    """
    
    heatpump_settings(form_key_suffix="hp1")
    
    with st.form(key="heatpump_simulation_form"):
        # Heat Pump simulation button
        heatpump_simulation_button = st.form_submit_button("Simulate Heat Pump")
           
        if heatpump_simulation_button:
            # Values for environment
            start = "2015-01-01 00:00:00"
            end = "2015-12-31 23:45:00"
            year = "2015"
            time_freq = "15 min"
            timestamp_int = 48
            timestamp_str = "2015-12-07 12:00:00"
            timebase = 15
            latitude = 50.941357
            longitude = 6.958307

            # Values for user_profile
            yearly_thermal_energy_demand = 12500
            building_type = "DE_HEF33"
            t_0 = 40
            env = Environment(
                timebase=timebase, 
                start=start, 
                end=end, 
                year=year, 
                time_freq=time_freq, 
                surpress_output_globally=False
            )
            
            
            
            env.get_dwd_mean_temp_hours(lat=latitude,lon=longitude)
            env.get_dwd_mean_temp_days(lat=latitude,lon=longitude)
            user_profile = UserProfile(
             identifier=None,
             latitude=None,
             longitude=None,
             thermal_energy_demand_yearly=yearly_thermal_energy_demand,
             mean_temp_days=env.mean_temp_days,
             mean_temp_hours=env.mean_temp_hours,
             mean_temp_quarter_hours=env.mean_temp_hours.resample("15 Min").interpolate(),
             building_type=building_type,
             comfort_factor=None,
             t_0=t_0,
         )
            
            
            
            
        
            user_profile.get_thermal_energy_demand()
            # Initialize Heat Pump with form inputs
            st.session_state.hp = HeatPump(
                identifier=st.session_state.heatpump_settings["identifier"],
                unit = "kW",
                thermal_energy_demand = user_profile.thermal_energy_demand,
                environment=env,
            #   user_profile=st.session_state.heatpump_settings["user_profile"],
                heat_pump_type=st.session_state.heatpump_settings["heat_pump_type"],
                heat_sys_temp = st.session_state.heatpump_settings["Heat System Temperature"],
                el_power=st.session_state.heatpump_settings["el_power"],
                th_power=st.session_state.heatpump_settings["th_power"],
                ramp_up_time=st.session_state.heatpump_settings["Ramp Up Time"],
                ramp_down_time=st.session_state.heatpump_settings["Ramp Down Time"],
                min_runtime=st.session_state.heatpump_settings["Minimum Run Time"],
                min_stop_time=st.session_state.heatpump_settings["Minimum Stop Time"]
            )
        
            st.success("Heat Pump settings updated successfully!")
            
            print("get_cop:")
            st.session_state.hp.get_cop()
            st.session_state.hp.cop.plot(figsize=(16, 9))
            plt.show() 
            st.session_state.hp.prepare_time_series()
            st.write("**Time Series Data (First 5 Rows):**")
            st.dataframe(st.session_state.hp.timeseries)  # Display the timeseries data for debugging

            # Create a Matplotlib figure
            fig, ax = plt.subplots(figsize=(16, 9))
            st.session_state.hp.timeseries.plot(ax=ax)  # Plot the timeseries on the provided axes
            ax.set_title("Heat Pump Time Series")
            ax.set_xlabel("Time")
            ax.set_ylabel("Value (kW)")
            plt.tight_layout()

            # Display the plot in Streamlit
            st.pyplot(fig)


 
    
def pv_configuration(): 
    
    pv_settings(form_key_suffix="pv1")
           
    with st.form(key="pv_simulation_form"):
        # PV simulation button
        pv_simulation_button = st.form_submit_button("Simulate PV")
           
        if pv_simulation_button:
            latitude = 51.4
            longitude = 6.97
            identifier = "Cologne"
            timestamp_int = 48
            timestamp_str = "2015-11-09 12:00:00"
            env = Environment(
            start = "2015-01-01 00:00:00", 
            end = "2015-12-31 23:45:00", 
            use_timezone_aware_time_index = True, 
            surpress_output_globally = False)
            env.get_dwd_pv_data(lat=latitude, lon=longitude)    
            # Initialize PV with form inputs
            
            st.session_state.pv = Photovoltaic(
                identifier="Cologne",
                unit="kW",
                latitude = 51.4,
                longitude = 6.97,
                environment=env,
                module_lib=st.session_state.pv_settings["PV Module Library"],
                module=st.session_state.pv_settings["PV Module"],
                inverter_lib=st.session_state.pv_settings["PV Inverter Library"],
                inverter=st.session_state.pv_settings["PV Inverter"],
                surface_tilt=st.session_state.pv_settings["PV Surface Tilt"],
                surface_azimuth=st.session_state.pv_settings["PV Surface Azimuth"],
                modules_per_string=st.session_state.pv_settings["PV Modules per String"],
                strings_per_inverter=st.session_state.pv_settings["PV Strings per Inverter"],
                temp_lib='sapm',
                temp_model='open_rack_glass_glass'
            )
        
            st.success("PV settings updated successfully!")
            
            # st.session_state.pv.prepare_time_series()
            # st.write("**Time Series Data (First 5 Rows):**")
            # st.dataframe(st.session_state.pv.timeseries.head(5))
            # print("prepare_time_series:") 
            # st.session_state.pv.timeseries.plot(figsize=(16, 9))
            # plt.show()
            
            st.session_state.pv.prepare_time_series()
            st.write("**Time Series Data (First 5 Rows):**")
            st.dataframe(st.session_state.pv.timeseries.head(5))  # Display the timeseries data for debugging

            # Create a Matplotlib figure
            fig, ax = plt.subplots(figsize=(16, 9))
            st.session_state.pv.timeseries.plot(ax=ax)  # Plot the timeseries on the provided axes
            ax.set_title("PV Time Series")
            ax.set_xlabel("Time")
            ax.set_ylabel("Month")
            plt.tight_layout()

            # Display the plot in Streamlit
            st.pyplot(fig)

 
def wind_configuration(key_suffix="wind1"):
    
    wind(form_key_suffix=key_suffix)
    with st.form(key="wind_simulation_form"):
        # Wind simulation button
        wind_simulation_button = st.form_submit_button("Simulate Wind Turbine")
           
        if wind_simulation_button:
            # env = Environment(
            # start = "2015-01-01 00:00:00", 
            # end = "2015-12-31 23:45:00", 
            # use_timezone_aware_time_index = True, 
            # surpress_output_globally = False
            # )
            # env.get_dwd_wind_data(lat=latitude, lon=longitude)
            # Values for environment
            latitude = 51.200001
            longitude = 6.433333
            timestamp_int = 12


            timestamp_str = "2015-11-09 12:00:00"
            env = Environment(start="2015-01-01 00:00:00", end="2015-12-31 23:45:00")
            env.get_wind_data(
                file="./input/wind/dwd_wind_data_2015.csv", utc=False
)
            
            # Initialize Wind Turbine with form inputs
            st.session_state.wind_turbine = WindPower(
                identifier=None,
                unit="kW",
                environment = env,
                hub_height=st.session_state.wind_settings["Hub Height"],
                rotor_diameter=st.session_state.wind_settings["Rotor Diameter"],
        #       comfort_factor=st.session_state.wind["Comfort Factor"],
                data_source="oedb",
                wind_speed_model=st.session_state.wind_settings["Wind Speed Model"],
                density_model=st.session_state.wind_settings["Density Model"],
                temperature_model=st.session_state.wind_settings["Temperature Model"],
                power_output_model=st.session_state.wind_settings["power_output_model"],
                density_correction=st.session_state.wind_settings["Density Correction"],
                obstacle_height=st.session_state.wind_settings["Obstacle Height"],
                hellman_exp=st.session_state.wind_settings["hellman_exp"],
                fetch_curve= "power_curve",
                turbine_type=st.session_state.wind_settings["Turbine Type"]
                
            )
        
            st.success("Wind settings updated successfully!")
            
            st.session_state.wind_turbine.prepare_time_series()
            st.write("**Time Series Data (First 5 Rows):**")
            st.dataframe(st.session_state.wind_turbine.timeseries.head(5))

                # Create a Matplotlib figure
            fig, ax = plt.subplots(figsize=(16, 9))
            st.session_state.wind_turbine.timeseries.plot(ax=ax)  # Plot the timeseries on the provided axes
            ax.set_title("Wind Time Series")
            ax.set_xlabel("Time")
            ax.set_ylabel("Month")
            plt.tight_layout()

            # Display the plot in Streamlit
            st.pyplot(fig)
            
   
        
def electrical_storage_configuration():
    
    electrical_storage(form_key_suffix="electrical_storage1")
    with st.form(key="electrical_storage_simulation_form"):
        # Electrical Storage simulation button
        electrical_storage_simulation_button = st.form_submit_button("Simulate Electrical Storage")
           
        if electrical_storage_simulation_button:
            start = "2015-06-01 00:00:00"
            end = "2015-06-07 23:45:00"
            year = "2015"
            timebase = 15
            timestamp_int = 48
            timestamp_str = "2015-06-01 12:00:00"
            name = "bus"
            max_c = 1
            env = Environment(timebase=timebase, start=start, end=end, year=year)
            env.get_pv_data(file="./input/pv/dwd_pv_data_2015.csv")
            PhotoV = st.session_state.pv
            PhotoV.identifier = (name + "_pv")
            PhotoV.environment = env    
            PhotoV.inverter = "Connect_Renewable_Energy__CE_4000__240V_"
            
            
            PhotoV.prepare_time_series()
            # Initialize Electrical Storage with form inputs
            st.session_state.es = ElectricalEnergyStorage(
                environment = env,
                identifier=(name + "_storage"),
                unit="kW",
                charge_efficiency=st.session_state.electrical_storage["Charge Efficiency"],
                discharge_efficiency=st.session_state.electrical_storage["Discharge Efficiency"],
                max_power=st.session_state.electrical_storage["Max Power"],
                max_c=st.session_state.electrical_storage["max_c"],
                capacity = st.session_state.electrical_storage["Max Capacity"]
            )
        
            st.success("Electrical Storage settings updated successfully!")
            
            PhotoV.prepare_time_series()
        
            
            baseload = pd.read_csv("./input/baseload/df_S_15min.csv")
            baseload.drop(columns=["Time"], inplace=True)
            
            
            baseload.set_index(env.pv_data.index, inplace=True)
        
           
            
            
            house_loadshape = pd.DataFrame(baseload["0"].loc[start:end] / 1000)
            house_loadshape["pv_gen"] = PhotoV.timeseries.loc[start:end]
            house_loadshape["residual_load"] = (
                 baseload["0"].loc[start:end] / 1000 - PhotoV.timeseries.bus_pv
            )
            # assign residual load to storage
            st.session_state.es.residual_load = house_loadshape.residual_load
            
            # Prepare time series data for Electrical Storage
            st.session_state.es.prepare_time_series()
            st.write("**Time Series Data (First 5 Rows):**")
            st.dataframe(st.session_state.es.timeseries.head(5))
            
            # Create a Matplotlib figure
            fig, ax = plt.subplots(figsize=(16, 9))
            st.session_state.es.timeseries.plot(ax=ax)
            plt.tight_layout()
            st.pyplot(fig)




def thermal_storage_settings():
    if "thermal_storage_settings" not in st.session_state:
        st.session_state.thermal_storage_settings={
            "target temperature": 0,
            "minimum temperature" : 0,
            "Current Temperature": 0,
            "hysteresis": 0,
            "mass":0,
            "cp":0,
            "thermal energy loss per day":0,
            "State of Charge":0,
            "start_time": 0,
            "end_time": 0,
            "frequency": 0,
            "timebase_minutes":0
    
        }
    st.title("Thermal Storage Configuarations")
    
    with st.sidebar:
        st.header("Thermal Storage Settings")
        
        st.markdown("**Target Temperature**")
        target_temperature = st.number_input(
                "Enter target temperature (°C)",
                min_value=0.0,
                value=float(st.session_state.thermal_storage_settings["target temperature"]),
                placeholder="e.g. 20 °C",
                key="target_temperature"
            )
        
        st.markdown("**Minimum Temperature**")
        minimum_temperature = st.number_input(
                "Enter minimum temperature (°C)",
                min_value=0.0,
                value=float(st.session_state.thermal_storage_settings["minimum temperature"]),
                placeholder="e.g. 15 °C",
                key="minimum_temperature"
            )
        
        st.markdown("**Hysteresis**")
        hysteresis = st.number_input(
                "Enter hysteresis (°C)",
                min_value=0.0,
                value=float(st.session_state.thermal_storage_settings["hysteresis"]),
                placeholder="e.g. 5 °C",
                key="hysteresis"
            )
        
        st.markdown("**Current Temperature**")
        current_temperature = st.number_input(
            "Enter current temperature (°C)",
            min_value=0.0,
            value = float(target_temperature - hysteresis),
            placeholder="e.g. 20 °C",
            key="current_temperature"
        )

        st.markdown("**Mass**")
        mass = st.number_input(
                "Enter mass (kg)",
                min_value=0.0,
                value=float(st.session_state.thermal_storage_settings["mass"]),
                placeholder="e.g. 100 kg",
                key="mass"
            )
        
        st.markdown("**Specific Heat Capacity**")
        cp = st.number_input(
                "Enter specific heat capacity (kJ/kg°C)",
                min_value=0.0,
                value=float(st.session_state.thermal_storage_settings["cp"]),
                placeholder="e.g. 4.18 kJ/kg°C",
                key="cp"
            )
        st.markdown("**State of Charge**")
        
        # Calculate initial state of charge in joules and convert to kWh
        initial_state_of_charge = mass * cp * (current_temperature + 273.15) / 3.6e6   # J to kWh
        state_of_charge = st.number_input(
        "Enter state of charge (kWh)",
        min_value=0.0,
        value=initial_state_of_charge,
        placeholder="e.g. 100 kWh",
        key="state_of_charge"
        )
        st.markdown("**Thermal Energy Loss per Day**")
        thermal_energy_loss_per_day = st.number_input(
                "Enter thermal energy loss per day (kWh)",
                min_value=0.0,
                value=float(st.session_state.thermal_storage_settings["thermal energy loss per day"]),
                placeholder="e.g. 10 kWh",
                key="thermal_energy_loss_per_day"
            )
        
        
        st.markdown("**Start Time**")
        start_time = st.number_input(
                "Enter start time (HH:MM)",
                value=0,
                placeholder="e.g. 08:00",
                key="start_time"
            )
        
        st.markdown("**End Time**")
        end_time = st.number_input(
                "Enter end time (HH:MM)",
                value=0,
                placeholder="e.g. 18:00",
                key="end_time"
            )
        
        st.markdown("**Frequency**")
        frequency = st.number_input(
                "Enter frequency (Hz)",
                min_value=0.0,
                value=float(st.session_state.thermal_storage_settings["frequency"]),
                placeholder="e.g. 50 Hz",
                key="frequency"
            )
        
        st.markdown("**Timebase Minutes**")
        timebase_minutes = st.number_input(
                "Enter timebase minutes",
                min_value=0.0,
                value=float(st.session_state.thermal_storage_settings["timebase_minutes"]),
                placeholder="e.g. 15 minutes",
                key="timebase_minutes"
            )
        if st.button("Submit Settings", key="submit_thermal_storage_settings"):
            st.session_state.thermal_storage_settings = {
                "target temperature": target_temperature,
                "minimum temperature": minimum_temperature,
                "Current Temperature": current_temperature,
                "hysteresis": hysteresis,
                "mass": mass,
                "cp": cp,
                "thermal energy loss per day": thermal_energy_loss_per_day,
                "State of Charge": state_of_charge,
                "start_time": start_time,
                "end_time": end_time,
                "frequency": frequency,
                "timebase_minutes": timebase_minutes
            }
            st.success("Thermal Storage settings updated successfully!")
            
    # Display stored settings
    if "thermal_storage_settings" in st.session_state:
        st.header("Current Thermal Storage Settings")
        st.json(st.session_state.thermal_storage_settings)

        # Create DataFrame for table
        data = {
            "Metric": [
                "Target Temperature",
                "Minimum Temperature",
                "Current Temperature",
                "Hysteresis",
                "Mass",
                "Specific Heat Capacity",
                "Thermal Energy Loss per Day",
                "State of Charge",
                "Start Time",
                "End Time",
                "Frequency",
                "Timebase Minutes"
            ],
            "Value": [
                st.session_state.thermal_storage_settings["target temperature"],
                st.session_state.thermal_storage_settings["minimum temperature"],
                st.session_state.thermal_storage_settings["Current Temperature"],
                st.session_state.thermal_storage_settings["hysteresis"],
                st.session_state.thermal_storage_settings["mass"],
                st.session_state.thermal_storage_settings["cp"],
                st.session_state.thermal_storage_settings["thermal energy loss per day"],
                st.session_state.thermal_storage_settings["State of Charge"],
                st.session_state.thermal_storage_settings["start_time"],
                st.session_state.thermal_storage_settings["end_time"],
                st.session_state.thermal_storage_settings["frequency"],
                st.session_state.thermal_storage_settings["timebase_minutes"]
            ]
            
        }
        
        df = pd.DataFrame(data)
        # Define numeric metrics for formatting
        numeric_metrics = ["Target Temperature", "Minimum Temperature", "Current Temperature", "Hysteresis", "Mass", "Specific Heat Capacity", "Thermal Energy Loss per Day", "State of Charge"]
        # Pre-format the 'Value' column
        df['Value'] = df.apply(
            lambda row: f"{float(row['Value']):.1f}" if row['Metric'] in numeric_metrics else str(row['Value']),
            axis=1
        )
        # Display table
        st.subheader("Thermal Storage Settings Table")
        styled_df = df.style.set_properties(**{
            'text-align': 'left',
            'font-size': '14px',
            'padding': '10px',
            'border': '1px solid #ddd',
            'background-color': '#f9f9f9'
        }).set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('font-weight', 'bold'), ('text-align', 'left'), ('padding', '10px'), ('border', '1px solid #ddd')]},
            {'selector': 'td', 'props': [('border', '1px solid #ddd')]}
        ])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        



def solar_installation_mastr():
    st.title("☀️ Solar Installations Dashboard")
    
    st.markdown("""
    **Explore solar installations from the German MaStR (Market Master Data Register)**
    
    This dashboard visualizes real solar power installations registered in Germany, 
    showing their locations, capacity, and technical specifications.
    """)

    # Enhanced error handling for database operations with caching
    try:
        with st.spinner("🔄 Loading available locations from database..."):
            unique_locations = get_cached_unique_locations("solar", mastr_db_path)
        
        if not unique_locations:
            st.error("❌ No locations available in the database")
            st.info("💡 Please check if the MaStR database file exists and contains data.")
            return
            
    except Exception as e:
        st.error("🗄️ **Database Connection Error**")
        st.error("Unable to load location data from the MaStR database.")
        
        with st.expander("🔧 **Troubleshooting Steps**"):
            st.markdown("""
            1. **Check database file**: Ensure `data/open-mastr.db` exists
            2. **Verify file permissions**: Make sure the database file is readable
            3. **Database integrity**: The database file may be corrupted
            4. **Restart application**: Try refreshing the page
            """)
        
        with st.expander("🔍 **Technical Details**"):
            st.code(str(e))
        return

    # Input validation for location selection
    st.markdown("### 📍 **Location Selection**")
    location = st.selectbox(
        "Select city", 
        options=unique_locations, 
        index=unique_locations.index("Essen") if "Essen" in unique_locations else 0,
        help="Choose a city to visualize its solar installations"
    )
    
    # Validate location selection
    if not location:
        st.warning("⚠️ Please select a location from the dropdown")
        return
    
    if location not in unique_locations:
        st.error(f"❌ Selected location '{location}' is not available in the database")
        return

    # Enhanced visualization button with progress tracking
    if st.button("🗺️ Visualize Solar Installations", key="visualize_solar"):
        if location:
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Step 1: Load data with caching
                status_text.text("🔄 Loading solar installation data...")
                progress_bar.progress(20)
                
                gdf_solar, city_district = get_cached_mastr_data(location, "solar", mastr_db_path)
                
                # Validate loaded data
                if gdf_solar is None or len(gdf_solar) == 0:
                    st.error(f"❌ No solar installations found for {location}")
                    st.info("💡 Try selecting a different location or check if the database contains data for this city.")
                    return
                
                progress_bar.progress(40)
                status_text.text("🗺️ Creating interactive map...")
                
                # Step 2: Create visualization with caching
                fig = create_cached_scatter_map(
                    gdf_solar,
                    lat_col='Breitengrad',
                    lon_col='Laengengrad',
                    hover_data=['NameStromerzeugungseinheit', 'Bruttoleistung', 'Nettonennleistung'],
                    center_lat=city_district.lat.item(),
                    center_lon=city_district.lon.item(),
                    color='red',
                    title=f"Solar Installations in {location}"
                )
                
                progress_bar.progress(60)
                status_text.text("🏘️ Adding district boundaries...")

                # Step 3: Create choropleth map with error handling
                try:
                    choropleth = px.choropleth_mapbox(
                        city_district,
                        geojson=city_district.geometry,
                        locations=city_district.index,
                        color=None,
                        opacity=0.3,
                        labels={location: 'City District'},
                    )
                    
                    # Add choropleth trace to the figure
                    fig.add_trace(choropleth.data[0])
                    
                except Exception as choropleth_error:
                    st.warning("⚠️ Could not load district boundaries, showing installations only")
                    st.write("District boundary error:", str(choropleth_error))
                
                progress_bar.progress(80)
                status_text.text("📊 Generating statistics...")
                
                # Step 4: Calculate and display statistics
                total_installations = len(gdf_solar)
                total_capacity_brutto = gdf_solar['Bruttoleistung'].sum() / 1000  # Convert to MW
                total_capacity_netto = gdf_solar['Nettonennleistung'].sum() / 1000  # Convert to MW
                avg_capacity = gdf_solar['Bruttoleistung'].mean()
                
                progress_bar.progress(100)
                status_text.text("✅ Visualization complete!")
                
                # Display results
                st.success(f"✅ Successfully loaded {total_installations} solar installations for {location}")
                
                # Key metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Installations", f"{total_installations:,}")
                with col2:
                    st.metric("Total Capacity (Gross)", f"{total_capacity_brutto:.1f} MW")
                with col3:
                    st.metric("Total Capacity (Net)", f"{total_capacity_netto:.1f} MW")
                with col4:
                    st.metric("Average Capacity", f"{avg_capacity:.1f} kW")
                
                # Display the map
                st.plotly_chart(fig, use_container_width=True)
                
                # Additional data insights
                with st.expander("📊 **Detailed Statistics**"):
                    st.subheader("Capacity Distribution")
                    capacity_hist = px.histogram(
                        gdf_solar, 
                        x='Bruttoleistung',
                        nbins=20,
                        title="Distribution of Solar Installation Capacities",
                        labels={'Bruttoleistung': 'Gross Capacity (kW)', 'count': 'Number of Installations'}
                    )
                    st.plotly_chart(capacity_hist, use_container_width=True)
                    
                    st.subheader("Installation Details")
                    st.dataframe(
                        gdf_solar[['NameStromerzeugungseinheit', 'Bruttoleistung', 'Nettonennleistung', 'Breitengrad', 'Laengengrad']].head(10),
                        use_container_width=True
                    )
                
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
                
            except Exception as e:
                st.error("❌ **Visualization Failed**")
                st.error(f"An error occurred while creating the visualization: {str(e)}")
                
                with st.expander("🔧 **Troubleshooting Steps**"):
                    st.markdown("""
                    1. **Check location data**: Verify the selected location has solar installations
                    2. **Database connectivity**: Ensure the MaStR database is accessible
                    3. **Data integrity**: The location data may be corrupted
                    4. **Try another location**: Some cities may have incomplete data
                    """)
                
                with st.expander("🔍 **Technical Details**"):
                    st.code(str(e))
                
                # Clear progress indicators on error
                progress_bar.empty()
                status_text.empty()
    
    # Information panel
    with st.expander("ℹ️ **About This Dashboard**"):
        st.markdown("""
        **Data Source**: German Market Master Data Register (MaStR)
        
        **What you can see**:
        - 📍 Exact locations of registered solar installations
        - ⚡ Power capacity (gross and net) for each installation
        - 🏘️ District boundaries and administrative divisions
        - 📊 Statistical distribution of installation sizes
        
        **Technical Notes**:
        - Red dots represent individual solar installations
        - Hover over installations to see detailed information
        - District boundaries show administrative divisions
        - Capacity values are from official registry data
        """)
        
    # Show data source information
    st.markdown("---")
    st.markdown("**📊 Data source**: German Market Master Data Register (Marktstammdatenregister - MaStR)")
    st.markdown("**🗓️ Last updated**: Based on available database content")

def wind_installation_mastr():
    st.title("Wind Installations Dashboard")
    
        # Fetch unique locations for dropdown
    unique_locations = get_unique_wind_locations(mastr_db_path=mastr_db_path)

    # Dropdown for location selection
    location = st.selectbox("Select city", options=unique_locations, index=unique_locations.index("Essen") if "Essen" in unique_locations else 0)

    # Button to trigger visualization
    if st.button("Visualize"):
        if location:
            # try:
                # Get data 
            with st.spinner("Loading data..."):
                gdf_wind, city_district = prepare_wind_data(location=location, mastr_db_path=mastr_db_path)

            # Create scatter map
            fig = px.scatter_mapbox(
                gdf_wind,
                lat='Breitengrad',
                lon='Laengengrad',
                size_max=15,
                color_discrete_sequence=['brown'],
                zoom=10,
                center={"lat": city_district.lat.item(),  
                        "lon": city_district.lon.item()},
                mapbox_style='open-street-map',
                hover_data=['NameStromerzeugungseinheit', 'Bruttoleistung', 'Nettonennleistung'],
            )

            # Create choropleth map
            choropleth = px.choropleth_mapbox(
                city_district,
                geojson=city_district.geometry,
                locations=city_district.index,
                color=None,
                opacity=0.3,
                labels={location: 'City District'},
            )

            # Add choropleth trace to the figure
            fig.add_trace(choropleth.data[0])

            # Move the choropleth trace to the background
            fig.data = fig.data[::-1]

            # Update layout
            fig.update_layout(
                margin={"r":0, "t":0, "l":0, "b":0},
            )

            # Display the plot in Streamlit
            st.plotly_chart(fig, use_container_width=True)
            
            
                # Display DataFrame below map
            st.subheader("Plotted Wind Installations")
            st.dataframe(
                gdf_wind[['NameStromerzeugungseinheit', 'Bruttoleistung', 'Nettonennleistung', 'Breitengrad', 'Laengengrad']]
                )

            # except Exception as e:
            #     st.error(f"Failed to visualize data for {location}: {str(e)}")
        else:
            st.warning("Please enter a city name.")
    # Key Features in dashboard.py



def storage_installation_mastr():
    st.title("Storage Installations Dashboard")
    
        # Fetch unique locations for dropdown
    unique_locations = get_unique_storage_locations(mastr_db_path=mastr_db_path)

    # Dropdown for location selection
    location = st.selectbox("Select city", options=unique_locations, index=unique_locations.index("Essen") if "Essen" in unique_locations else 0)

    # Button to trigger visualization
    if st.button("Visualize"):
        if location:
            # try:
            # Get data from matr_main
            with st.spinner("Loading data..."):
                gdf_storage, city_district = prepare_storage_data(location=location, mastr_db_path=mastr_db_path)

            # Create scatter map
            fig = px.scatter_mapbox(
                gdf_storage,
                lat='Breitengrad',
                lon='Laengengrad',
                size_max=15,
                color_discrete_sequence=['purple'],
                zoom=10,
                center={"lat": city_district.lat.item(),  
                        "lon": city_district.lon.item()},
                mapbox_style='open-street-map',
                hover_data=['NameStromerzeugungseinheit', 'Bruttoleistung', 'Nettonennleistung'],
            )

            # Create choropleth map
            choropleth = px.choropleth_mapbox(
                city_district,
                geojson=city_district.geometry,
                locations=city_district.index,
                color=None,
                opacity=0.3,
                labels={location: 'City District'},
            )

            # Add choropleth trace to the figure
            fig.add_trace(choropleth.data[0])

            # Move the choropleth trace to the background
            fig.data = fig.data[::-1]

            # Update layout
            fig.update_layout(
                margin={"r":0, "t":0, "l":0, "b":0},
            )

            # Display the plot in Streamlit
            st.plotly_chart(fig, use_container_width=True)
            
            # Display the filtered data as a DataFrame and Pie Chart side by side
            st.subheader("Plotted Storage Installations")
            
            # Display DataFrame
            st.dataframe(
                    gdf_storage[['NameStromerzeugungseinheit', 'Bruttoleistung', 'Nettonennleistung', 'Breitengrad', 'Laengengrad', 'Ort']]
                )

            # Create Pie Chart for Operating Status Distribution
            tech_counts = gdf_storage['EinheitBetriebsstatus'].value_counts()
            pie_fig = px.pie(
                    values=tech_counts.values,
                    names=tech_counts.index,
                    title="Distribution by Technology",
                    hole=0.3  # Optional: Make it a donut chart for aesthetics
                )
            pie_fig.update_layout(
                    margin={"r":0, "t":50, "l":0, "b":0},  # Adjust margins for compact display
                    height=300  # Set height to align with DataFrame
                )
            st.plotly_chart(pie_fig, use_container_width=True)
            
            st.subheader("Bar Graph for Storage Installations")
            # Define bins and sort them
            bins = [0, 50, 200, 1000, gdf_storage['Nettonennleistung'].max()]
            bins = sorted(bins)  # Ensure increasing order for pd.cut internally
            labels = ['<50 kW', '50–200 kW', '200–1000 kW', '>1000 kW']

            # Create a temporary column with binned data
            gdf_storage['Capacity_Range'] = pd.cut(gdf_storage['Nettonennleistung'], bins=bins, labels=labels, ordered=False)

            # Plot bar chart using value counts
            capacity_fig = px.bar(
                gdf_storage['Capacity_Range'].value_counts(),
                labels={'index': 'Capacity Range', 'value': 'Number of Installations'},
                title="Storage Installations by Net Capacity Range"
            )

            st.plotly_chart(capacity_fig, use_container_width=True)
                
            # except Exception as e:
            #     st.error(f"Failed to visualize data for {location}: {str(e)}")

        else:
            st.warning("Please enter a city name.")
    
from src.mastr.simulation import pick_pvsystem_mastr, prepare_pv_time_series_mastr, aggregate_pv_time_series, revise_power_values, wind_turbine_matching


def energy_generation_solar():
    st.title("Energy Generation from Solar Installations")
    
    # Fetch unique locations for dropdown with caching
    unique_locations = get_cached_unique_locations("solar", mastr_db_path)

    # Dropdown for location selection
    location = st.selectbox("Select city", options=unique_locations, index=unique_locations.index("Essen") if "Essen" in unique_locations else 0)
    if location:
        if st.button("Simulate Energy Generation"):
            with st.spinner("Preparing and simulating PV systems..."):
                try:
                    start = "2015-07-07 00:00:00"
                    end = "2015-07-07 23:45:00"
                    gdf_solar, city_district = get_cached_mastr_data(location, "solar", mastr_db_path)
                    gdf_solar = revise_power_values(gdf_solar)
                    ref_env = Environment(start=start, end=end)
                    ref_env.get_dwd_pv_data(lat=city_district.lat, 
                        lon=city_district.lon)
                    pv_system_mastr = pick_pvsystem_mastr(gdf_solar.head(10), ref_env)
                    prepare_pv_time_series_mastr(pv_system_mastr)
                    pv_systems_aggregated = aggregate_pv_time_series(pv_system_mastr)
                    # Plotting code
                    fig, ax = plt.subplots(figsize=(10, 6))
                    for name, pv_system in pv_systems_aggregated.items():
                        if hasattr(pv_system, 'plot'):
                            pv_system.plot(ax=ax, label=name)
                        else:
                            # Fallback for non-plottable objects (e.g., if pv_system is a string or list)
                            st.warning(f"System {name} is not directly plottable ({type(pv_system)}), attempting manual plotting")
                            try:
                                # Assume pv_system is a list or array-like (e.g., time series data)
                                ax.plot(pv_system, label=name)
                            except Exception as plot_error:
                                st.error(f"Failed to plot {name}: {plot_error}")
                    ax.set_title(f"Solar Energy Generation in {location} ({start} to {end})")
                    ax.set_xlabel("Time")
                    ax.set_ylabel("Power (kW)")
                    ax.legend()
                    ax.grid(True)
                    st.pyplot(fig)
                    plt.close(fig) 

                except Exception as e:
                    st.error(f"Simulation failed: {e}")

import pvlib
from src.mastr.simulation import init_windturbines_mastr, prepare_wind_time_series_mastr, aggregate_wind_time_series

def wind_energy_generation():
    st.title("Energy Generation from Wind Installations")
    
    # Fetch unique locations for dropdown
    unique_locations = get_unique_wind_locations(mastr_db_path=mastr_db_path)

    # Dropdown for location selection
    location = st.selectbox("Select city", options=unique_locations, index=unique_locations.index("Essen") if "Essen" in unique_locations else 0)
    
    if location:
        if st.button("Simulate Energy Generation"):
            with st.spinner("Preparing and simulating Wind systems..."):
                try:
                    start = "2015-07-07 00:00:00"
                    end = "2015-07-07 23:45:00"
                    ref_env = Environment(start=start, end=end)
                    gdf_wind, city_district = prepare_wind_data(location=location, mastr_db_path=mastr_db_path)
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
                    
@st.dialog("Anleitung und Hinweise", width="large")
def show_instructions():
    st.markdown(
        """
        **Anleitung:**  
        1. Wählen Sie die Art der Anlage, die Sie planen möchten (FFPV, WEA oder Hybrid).  
        2. Geben Sie einen Ort oder eine Adresse ein, um die Karte zu zentrieren. Alternativ können Sie die Karte manuell verschieben und zoomen.  
        3. Klicken Sie auf das Kreissymbol oben rechts auf der Karte und ziehen Sie den Kreis auf der Karte auf, indem Sie auf eine Stelle auf der Karte klicken und nach außen ziehen. Lassen Sie die Maus los und das Programm wird automatisch durchgeführt. Der Kreis stellt das zu beplanende Gebiet dar.  
        4. Scrollen Sie nach unten, um die Ergebnisse der Simulation zu sehen.  
        5. Um einen neuen Kreis zu zeichnen, klicken Sie zunächst auf das Mülleimersymbol auf der rechten Seite der Karte unter dem Kreissymbol. Klicken Sie dann auf „Alles löschen“, um den aktuellen Kreis zu löschen.  
        6. Zeichnen Sie einen neuen Kreis, indem Sie erneut auf das Kreissymbol klicken und den Kreis auf der Karte ziehen.  

        **Hinweise:**  
        *Dieses Programm funktioniert derzeit nur für Regionen innerhalb Deutschlands.*  
        *Eine Infobox unterhalb der Karte zeigt den Fortschritt der Simulation an. Alternativ bedeutet ein „RUNNING...“-Symbol oben rechts im Browser, dass das Programm gerade läuft.*  
        *In der Infobox wird „Erfolgreich“ angezeigt, wenn der Vorgang abgeschlossen ist.*  
        *Sie können im Diagramm verschieben und zoomen. Klicken Sie auf das Symbol oben rechts im Diagramm, um es als Vollbild anzuzeigen. Klicken Sie auf die drei Punkte oben rechts, um das Diagramm zu exportieren.*  
        *Sie können ebenfalls die Karte verschieben und zoomen. Oben rechts auf der Karte können Sie die Layers ein- oder ausblenden.*  
        *Klicken Sie auf die Schaltfläche „Karte als HTML herunterladen“, um die Karte als HTML-Datei herunterzuladen.*  

        *Die in diesem Tool erstellten Darstellungen und Simulationen stellen keine vollständige Planung realer Solar- oder Windparks dar*.  
        *Vielmehr handelt es sich um eine theoretische Abschätzung des Flächenpotenzials und der potenziellen Energieerzeugung in einem definierten Gebiet*.  
        *Die Positionierung der Solarmodule und Windturbinen basiert ausschließlich auf öffentlich zugänglichen Geodaten (z.B. OpenStreetMap) und standardisierten Ausschlusskriterien,  
        *ohne Prüfung standortbezogener Genehmigungsbedingungen, Netzanschlussoptionen oder detaillierter Umweltverträglichkeitsprüfungen*.  
        *Dieses Werkzeug dient daher in erster Linie der automatisierten Potenzialanalyse und nicht der Erstellung genehmigungsfähiger Planungsunterlagen*.
        """
    )
    
from streamlit_folium import st_folium
from streamlit.components.v1 import html
import folium
import time
from folium.plugins import Draw, MousePosition
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from pyproj import CRS, Transformer

# Solar panel specifications (in meters)
solar_panel_width = 1.96
solar_panel_height = 3.66 #Für 4 module
row_spacing = 3.5

# Wind turbines specifications (in meters)
min_spacing_x = 1270
min_spacing_y = 762
hub_height = 135

def get_local_crs(lon, lat):
    return CRS.from_proj4(
        f"+proj=tmerc +lat_0={lat} +lon_0={lon} +k=1 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs"
    )

def find_circle_markers(obj):
    markers = []
    if isinstance(obj, folium.CircleMarker):
        markers.append(obj)
    if hasattr(obj, '_children'):
        for child in obj._children.values():
            markers.extend(find_circle_markers(child))
    return markers



def FFPV_WEA():
    
    st.title("Programm zur Planung von Solar- und Windkraftanlagen")
    
    if st.button("Anleitung und Hinweise"):
        show_instructions()
    
    option = st.radio(
    "Welche Art von Anlage möchten Sie planen?",
    ("FFPV", "WEA", "Hybrid (FFPV + WEA)")
    )

    # Search functionality
    # Search functionality
    geolocator = Nominatim(user_agent="solar-farm-planner")
    location_input = st.text_input("Suchen Sie nach einem Ort oder einer Adresse:", "")

    # Step 2: Initialize session state to avoid repeated queries
    if 'geocoded_results' not in st.session_state:
        st.session_state['geocoded_results'] = None
    if 'last_query' not in st.session_state:
        st.session_state['last_query'] = ""

    # Default center
    map_center = [51.1657, 10.4515]
    zoom_level = 6
    location = None

    # Step 4: Perform geocoding only when query is new
    if location_input and location_input != st.session_state['last_query']:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                locations = geolocator.geocode(location_input, exactly_one=False, addressdetails=True, limit=5)
                if locations:
                    st.session_state['geocoded_results'] = locations
                    st.session_state['last_query'] = location_input
                else:
                    st.warning("Keine Adresse gefunden")
                    st.session_state['geocoded_results'] = None
            except (GeocoderTimedOut, GeocoderServiceError) as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    st.error(f"Geocoding error: {e}")
                    st.session_state['geocoded_results'] = None

    # Step 5: Show dropdown and update map if results exist
    if st.session_state['geocoded_results']:
        locations = st.session_state['geocoded_results']
        location_options = [f"{loc.address} ({loc.latitude:.4f}, {loc.longitude:.4f})" for loc in locations]
        selection = st.selectbox("Ausgewählte Adresse:", location_options)

        selected_index = location_options.index(selection)
        selected_location = locations[selected_index]
        st.session_state["selected_location"] = selected_location
        map_center = [selected_location.latitude, selected_location.longitude]
        zoom_level = 15

    m = folium.Map(location=map_center, zoom_start=zoom_level)
    mouse_position = MousePosition(position='bottomright', separator=' | ', prefix="Coordinates:", num_digits=6)
    m.add_child(mouse_position)

    # drop marker at the searched location
    if "selected_location" in st.session_state:
        folium.Marker(
            location=[st.session_state["selected_location"].latitude, st.session_state["selected_location"].longitude],
            icon=folium.Icon(color="blue", icon="search")
        ).add_to(m)

    # Add a draw tool to the map (for drawing circles only)
    draw = Draw(
        export=False,  # Enable exporting to GeoJSON
        draw_options={
            'polyline': False,    # Disable lines
            'polygon': True,     # Enable polygons
            'rectangle': False,   # Disable rectangles
            'circle': False,       # Disable circles
            'marker': False,      # Disable markers
            'circlemarker': False # Disable circle markers
        },
        edit_options={
            'edit': False,        # Disable editing
            'remove': True        # Enable deleting
        }
    )
    draw.add_to(m)

    # Display the map and get draw data
    with st.container():
        output = st_folium(m, width=700, height=500, key="map_draw")

    status_box = st.empty()

    if "last_polygon_coords" not in st.session_state:
        st.session_state["last_polygon_coords"] = []

    if "num_panels" not in st.session_state:
        st.session_state["num_panels"] = None

    if "num_turbines" not in st.session_state:
        st.session_state["num_turbines"] = None

    if "second_map" not in st.session_state:
        st.session_state["second_map"] = None

    if "results_df" not in st.session_state:
        st.session_state["results_df"] = None

    if "total_energy" not in st.session_state:
        st.session_state["total_energy"] = None

    if "results_ac" not in st.session_state:
        st.session_state["results_ac"] = None

    if "rated_power_solar" not in st.session_state:
        st.session_state["rated_power_solar"] = None

    if "rated_power_wind" not in st.session_state:
        st.session_state["rated_power_wind"] = None

    # Initialize variables
    current_polygon_coords = None
    radius_meters = 0
    
    # Check if the user has drawn a shape
    # Initialize map
    m2 = None
    lat_center = None
    lon_center = None

    if output and output.get('last_active_drawing'):
        if output.get('last_circle_polygon'):
            try:
                # Circle mode
                circle_data = output['last_circle_polygon']
                # Get radius and center from circle properties
                lat_center = circle_data['properties']['center'][1]
                lon_center = circle_data['properties']['center'][0]
                radius_meters = circle_data['properties']['radius']
                # Store the circle coordinates for reference
                current_polygon_coords = circle_data['coordinates'][0]
                status_box.info("🔄 Kreis erkannt...")
            except (KeyError, TypeError, IndexError) as e:
                status_box.error(f"❌ Fehler beim Verarbeiten des Kreises: {str(e)}")
                st.stop()
                
        elif output['last_active_drawing']['geometry']['type'] == 'Polygon':
            try:
                # Polygon mode
                current_polygon_coords = output['last_active_drawing']['geometry']['coordinates'][0]
                # Calculate centroid for map recentering and further processing
                lat_center = float(np.mean([pt[1] for pt in current_polygon_coords]))
                lon_center = float(np.mean([pt[0] for pt in current_polygon_coords]))
                status_box.info("🔄 Polygon erkannt...")
            except (KeyError, TypeError, IndexError) as e:
                status_box.error(f"❌ Fehler beim Verarbeiten des Polygons: {str(e)}")
                st.stop()
        else:
            status_box.error("❌ Bitte zeichnen Sie einen Kreis oder ein Polygon")
            st.stop()
    else:
        status_box.error("❌ Bitte zeichnen Sie einen Kreis oder ein Polygon")
        st.stop()

    # Store values in output and session state
    output['lat_center'] = lat_center
    output['lon_center'] = lon_center
    st.session_state["last_polygon_coords"] = current_polygon_coords

    # Create base map
    m2 = folium.Map(location=[lat_center, lon_center], zoom_start=20)
    mouse_position = MousePosition(position='bottomright', separator=' | ', prefix="Coordinates:", num_digits=6)
    m2.add_child(mouse_position)

    # Begin simulation based on selected option
    st.session_state["last_polygon_coords"] = current_polygon_coords
    # Calculate centroid for map recentering and further processing
    lats = [pt[1] for pt in current_polygon_coords]
    lons = [pt[0] for pt in current_polygon_coords]
    lat_center = float(np.mean(lats))
    lon_center = float(np.mean(lons))
    # Store in session state for later use
    st.session_state["lat_center"] = lat_center
    st.session_state["lon_center"] = lon_center
    m2 = folium.Map(location=[lat_center, lon_center], zoom_start=20)
    mouse_position = MousePosition(position='bottomright', separator=' | ', prefix="Coordinates:", num_digits=6)
    # Pass polygon coordinates to your simulation functions as needed
    if option == "FFPV":
        from src.planning import fetch_obstacles_solar, packing_solar, simulate_solarfarm_output
        # Removed is_circle parameter - polygon only now
        obstacles = fetch_obstacles_solar(output, current_polygon_coords, status_box)
        
        # Polygon mode only - pass dummy radius (0) and polygon coordinates
        m2_solar, num_panels = packing_solar(lat_center, lon_center, 0,
                                            solar_panel_width, solar_panel_height, row_spacing,
                                            obstacles, status_box, m2,
                                            polygon_coords=current_polygon_coords)
        
        st.session_state["num_panels"] = num_panels
        st.session_state["second_map"] = m2_solar
        st.session_state["second_map_html"] = m2_solar._repr_html_()
        status_box.info("🧮 Solaranlagen simulieren...")
        results_ac, rated_power_solar = simulate_solarfarm_output(lat_center, lon_center, num_panels)
        st.session_state["results_ac"] = results_ac
        st.session_state["rated_power_solar"] = rated_power_solar
    elif option == "WEA":
        from src.planning import fetch_obstacles_wind, packing_wind, get_weather_for_windpowerlib
        # TODO: simulate_windfarm_output function not yet implemented
        # Removed is_circle parameter - polygon only now
        obstacles = fetch_obstacles_wind(output, current_polygon_coords, status_box, min_spacing_x, min_spacing_y)
        status_box.info("☁️ Wetterdaten abrufen...")
        weather_df, main_dir = get_weather_for_windpowerlib(lat_center, lon_center, year=2024)
        
        if weather_df is None:
            st.error("❌ Konnte keine Wetterdaten laden. Bitte stellen Sie sicher, dass der Ordner data/era5_germany_2024_wind existiert und die erforderlichen Dateien enthält.")
            st.stop()
            
        # Polygon mode only - pass dummy radius (0) and polygon coordinates
        m2_wind, num_turbines, access_roads_gdf, crane_pads_gdf = packing_wind(lat_center, lon_center, 0,
                                            min_spacing_x, min_spacing_y, obstacles, 
                                            main_dir, status_box, m2, option,
                                            polygon_coords=current_polygon_coords)
            
        st.session_state["num_turbines"] = num_turbines
        st.session_state["second_map"] = m2_wind
        st.session_state["second_map_html"] = m2_wind._repr_html_()
        # TODO: Wind simulation function not yet implemented
        # status_box.info("🧮 Windturbinen simulieren...")
        # results_df, total_energy, rated_power_wind = simulate_windfarm_output(weather_df, num_turbines, hub_height)
        # st.session_state["results_df"] = results_df
        # st.session_state["total_energy"] = total_energy
        # st.session_state["rated_power_wind"] = rated_power_wind
        
        # Store center coordinates for display
        st.session_state["lat_center"] = lat_center
        st.session_state["lon_center"] = lon_center
        st.session_state["radius_meters"] = radius_meters
        
    elif option == "Hybrid (FFPV + WEA)":
                from src.planning import fetch_obstacles_wind, packing_wind, get_weather_for_windpowerlib
                from src.planning import fetch_obstacles_solar, packing_solar, simulate_solarfarm_output
                # TODO: simulate_windfarm_output not yet implemented
                import geopandas as gpd
                import pandas as pd
                from shapely.geometry import Point
                
                # Fetch wind obstacles
                obstacles_wind = fetch_obstacles_wind(output, current_polygon_coords, status_box, min_spacing_x, min_spacing_y)
                
                # Get weather data and wind direction
                status_box.info("☁️ Wetterdaten abrufen...")
                weather_df, main_dir = get_weather_for_windpowerlib(lat_center, lon_center, year=2024)
                
                # Place wind turbines and generate access roads and crane pads
                m2_wind, num_turbines, access_roads_gdf, crane_pads_gdf = packing_wind(lat_center, lon_center, 0, 
                                                    min_spacing_x, min_spacing_y, obstacles_wind, 
                                                    main_dir, status_box, m2, option,
                                                    polygon_coords=current_polygon_coords)
                
                st.session_state["num_turbines"] = num_turbines
                
                # TODO: Wind simulation function not yet implemented
                # Simulate wind farm output
                # status_box.info("🧮 Windturbinen simulieren...")
                # results_df, total_energy, rated_power_wind = simulate_windfarm_output(weather_df, num_turbines, hub_height)
                # st.session_state["results_df"] = results_df
                # st.session_state["total_energy"] = total_energy
                # st.session_state["rated_power_wind"] = rated_power_wind
                
                # Initialize combined obstacles with wind obstacles
                combined_obstacles = obstacles_wind.copy()
                
                # Merge access roads with wind obstacles for solar placement
                if access_roads_gdf is not None and not access_roads_gdf.empty:
                    combined_obstacles = pd.concat([combined_obstacles, access_roads_gdf], ignore_index=True)
                
                if crane_pads_gdf is not None and not crane_pads_gdf.empty:
                    combined_obstacles = pd.concat([combined_obstacles, crane_pads_gdf], ignore_index=True)
                
                # Fetch solar-specific obstacles and merge with combined wind obstacles
                obstacles_solar = fetch_obstacles_solar(output, current_polygon_coords, status_box)
                final_obstacles = pd.concat([combined_obstacles, obstacles_solar], ignore_index=True)
                
                # Place solar panels with all obstacles (wind + access roads + crane pads + solar)
                status_box.info("☀️ Solarmodule platzieren...")
                m2_combined, num_panels = packing_solar(lat_center, lon_center, 0,
                                                       solar_panel_width, solar_panel_height, row_spacing,
                                                       final_obstacles, status_box, m2_wind,
                                                       polygon_coords=current_polygon_coords)
                
                st.session_state["num_panels"] = num_panels
                st.session_state["second_map"] = m2_combined
                st.session_state["second_map_html"] = m2_combined._repr_html_()
                
                # Simulate solar farm output
                status_box.info("🧮 Solarmodule simulieren...")
                results_ac, rated_power_solar = simulate_solarfarm_output(
                    lat_center, lon_center, num_panels
                )
                st.session_state["results_ac"] = results_ac
                st.session_state["rated_power_solar"] = rated_power_solar
    if st.session_state["second_map"] and "second_map_html" in st.session_state:

        if option == "FFPV":
            st.subheader("Karte mit Solarmodulen")
            status_box.info("🗺️ Karte mit Solarmodulen erstellen...")
            
            # Display energy generation if available
            if "results_ac" in st.session_state and "rated_power_solar" in st.session_state:
                st.subheader("Energieerzeugung")
                results_ac = st.session_state["results_ac"]
                rated_power_solar = st.session_state["rated_power_solar"]
                
                # Display simulation info
                st.write("Kreisinformationen")
                if "lat_center" in st.session_state and "lon_center" in st.session_state:
                    st.write(f"Zentrum (Längengrad, Breitengrad): [{st.session_state['lat_center']:.6f}, {st.session_state['lon_center']:.6f}]")
                
                # Show simulation results
                st.write("Simulationsergebnisse")
                if "num_panels" in st.session_state:
                    st.write(f"Anzahl von Solarmodulen: {st.session_state['num_panels']}")
                yearly_energy = results_ac.sum() / 1e9  # Convert to GWh
                st.write(f"Gesamtenergieerzeugung pro Jahr: {yearly_energy:.2f} GWh")
                specific_yield = (yearly_energy * 1e6) / (rated_power_solar / 1000)  # kWh/kWp
                st.write(f"kWh/kWp: {specific_yield:.2f} kWh/kWp/a")

                # Create figures for energy generation
                # Yearly profile
                fig1 = plt.figure(figsize=(10, 6))
                plt.plot(results_ac.index, results_ac.values)
                plt.title(f'Stromproduktion der Solaranlagen im Jahresverlauf (W)')
                plt.xlabel('2024')
                plt.ylabel('Leistung (W)')
                plt.grid(True)
                st.pyplot(fig1)
                plt.close(fig1)

                # Daily profile (use July 1st as example)
                july_1st = results_ac['2024-07-01']
                fig2 = plt.figure(figsize=(10, 6))
                plt.plot(july_1st.index.hour, july_1st.values)
                plt.title(f'Tägliche Energieerzeugung (Nennleistung: {rated_power_solar/1000:.2f} MW)')
                plt.xlabel('Stunde des Tages')
                plt.ylabel('Leistung (W)')
                plt.grid(True)
                st.pyplot(fig2)
                plt.close(fig2)
            
            with st.container():
                legend_template = """
                    <style>
                        @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro&display=swap');

                        .legend-container {
                            position: absolute;
                            top: 520px;
                            left: 0px;
                            width: 700px;
                            padding: 10px;
                        }
                            
                        .legend-box {
                            font-family: 'Source Sans Pro', sans-serif;
                            font-size: 16px;
                            color: rgb(0, 0, 0);
                        }
                        .legend-grid {
                            display: grid;
                            grid-template-columns: repeat(3, 1fr);
                            gap: 8px 15px;
                            margin-top: 10px;
                        }

                        .legend-icon {
                            width: 16px;
                            height: 16px;
                            display: inline-block;
                            border: 1px solid white;
                            margin-right: 6px;
                            vertical-align: middle;
                            border-radius: 2px;
                        }
                    </style>

                    <div class="legend-container">
                        <div class="legend-box">
                            <strong>Hindernis-Legende</strong>
                            <div class="legend-grid">
                                <div><i style="background: gray;" class="legend-icon"></i> Verkehr</div>
                                <div><i style="background: green;" class="legend-icon"></i> Landnutzung</div>
                                <div><i style="background: red;" class="legend-icon"></i> Gebäude</div>
                                <div><i style="background: blue;" class="legend-icon"></i> Gewässer</div>
                                <div><i style="background: purple;" class="legend-icon"></i> Schutzgebiet</div>
                                <div><i style="background: orange;" class="legend-icon"></i> Stromleitung</div>
                            </div>
                        </div>
                    </div>
                """
                map_with_legend = f"""
                    <style>
                        /* Remove all margin/padding from the outer container */
                        .map-wrapper {{
                            margin: 0;
                            padding: 0;
                            width: 700px;
                            height: 500px;
                        }}

                        /* Force the iframe Folium uses to render map */
                        .map-wrapper iframe {{
                            width: 700px !important;
                            height: 500px !important;
                            margin: 0 !important;
                            padding: 0 !important;
                            border: none !important;
                            display: block;
                            position: relative;
                        }}
                    </style>

                    <div class="map-wrapper">
                        {st.session_state["second_map_html"]}
                        {legend_template}
                    </div>
                """
                html(map_with_legend, height=700)

        elif option == "WEA":
            # Display wind simulation results first
            if "results_df" in st.session_state and "total_energy" in st.session_state and "rated_power_wind" in st.session_state:
                st.subheader("Kreisinformationen")
                if "lat_center" in st.session_state and "lon_center" in st.session_state:
                    st.write(f"Kreiszentrum (Längengrad, Breitengrad): [{st.session_state['lon_center']:.6f}, {st.session_state['lat_center']:.6f}]")
                if "radius_meters" in st.session_state:
                    st.write(f"Kreisradius: {st.session_state['radius_meters']:.2f} meter")
                
                st.subheader("Simulationsergebnisse")
                st.write(f"Anzahl von Windturbinen: {st.session_state['num_turbines']}")
                
                total_gwh = st.session_state["total_energy"] / 1000  # Convert MWh to GWh
                st.write(f"Gesamtenergieerzeugung pro Jahr: {total_gwh:.2f} GWh")
                
                # Calculate full load hours
                if st.session_state["rated_power_wind"] > 0:
                    full_load_hours = (st.session_state["total_energy"] * 1000) / st.session_state["rated_power_wind"]
                    st.write(f"Volllaststunden: {full_load_hours:.2f} h")
                
                # Create monthly power generation chart
                st.write("Stromproduktion der Windturbinen im Jahresverlauf (MW)")
                results_df = st.session_state["results_df"]
                if not results_df.empty:
                    # Group by month and calculate monthly averages
                    monthly_power = results_df["power_output_MW"].groupby(results_df.index.month).mean()
                    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                    
                    # Create the chart
                    import plotly.graph_objects as go
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=month_names[:len(monthly_power)],
                        y=monthly_power.values,
                        mode='lines+markers',
                        name='Wind Power',
                        line=dict(color='blue', width=2)
                    ))
                    fig.update_layout(
                        xaxis_title='Month',
                        yaxis_title='Power (MW)',
                        showlegend=False,
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("Karte mit Windturbinen")
            status_box.info("🗺️ Karte mit Windturbinen erstellen...")
            with st.container():
                legend_template = """
                    <style>
                        @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro&display=swap');

                        .legend-container {
                            position: absolute;
                            top: 520px;
                            color: rgb(0, 0, 0);
                            left: 0px;
                            width: 700px;
                            padding: 10px;
                        }
                            
                        .legend-box {
                            font-family: 'Source Sans Pro', sans-serif;
                            font-size: 16px;
                            color: rgb(0, 0, 0);
                        }
                        .legend-grid {
                            display: grid;
                            grid-template-columns: repeat(3, 1fr);
                            gap: 8px 15px;
                            margin-top: 10px;
                        }

                        .legend-icon {
                            width: 16px;
                            height: 16px;
                            display: inline-block;
                            border: 1px solid white;
                            margin-right: 6px;
                            vertical-align: middle;
                            border-radius: 2px;
                        }
                    </style>

                    <div class="legend-container">
                        <div class="legend-box">
                            <strong>Hindernis-Legende</strong>
                            <div class="legend-grid">
                                <div><i style="background: rgb(128, 128, 128);" class="legend-icon"></i> Verkehr</div>
                                <div><i style="background: rgb(34, 139, 34);" class="legend-icon"></i> Landnutzung</div>
                                <div><i style="background: rgb(220, 20, 60);" class="legend-icon"></i> Infrastruktur</div>
                                <div><i style="background: rgb(255, 140, 0);" class="legend-icon"></i> Militär</div>
                                <div><i style="background: rgb(128, 0, 128);" class="legend-icon"></i> Artenschutz</div>
                                <div><i style="background: rgb(30, 144, 255);" class="legend-icon"></i> Natur & Landschaft</div>
                                <div><i style="background: rgb(107, 142, 35);" class="legend-icon"></i> Wald</div>
                                <div><i style="background: rgb(32, 178, 170);" class="legend-icon"></i> Gewässer</div>
                                <div><i style="background: rgb(139, 69, 19);" class="legend-icon"></i> Sonstiges</div>
                            </div>
                        </div>
                    </div>
                """
                map_with_legend = f"""
                    <style>
                        /* Remove all margin/padding from the outer container */
                        .map-wrapper {{
                            margin: 0;
                            padding: 0;
                            width: 700px;
                            height: 500px;
                        }}

                        /* Force the iframe Folium uses to render map */
                        .map-wrapper iframe {{
                            width: 700px !important;
                            height: 500px !important;
                            margin: 0 !important;
                            padding: 0 !important;
                            border: none !important;
                            display: block;
                            position: relative;
                        }}
                    </style>

                    <div class="map-wrapper">
                        {st.session_state["second_map_html"]}
                        {legend_template}
                    </div>
                """
                html(map_with_legend, height=700)
        
        elif option == "Hybrid (FFPV + WEA)":
            st.subheader("Karte mit Solarmodulen und Windturbinen")
            status_box.info("🗺️ Karte mit Windturbinen erstellen...")
            with st.container():
                legend_template = """
                    <style>
                        @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro&display=swap');

                        .legend-container {
                            position: relative;
                            margin-top: 100px;
                            width: 700px;
                            padding: 10px;
                            background: none;
                            color: rgb(0, 0, 0);
                        }
                            
                        .legend-box {
                            font-family: 'Source Sans Pro', sans-serif;
                            font-size: 16px;
                            color: rgb(0, 0, 0);
                            margin-bottom: 30px;
                        }
                        .legend-grid {
                            display: grid;
                            grid-template-columns: repeat(3, 1fr);
                            gap: 8px 15px;
                            margin-top: 10px;
                        }

                        .legend-icon {
                            width: 16px;
                            height: 16px;
                            display: inline-block;
                            border: 1px solid white;
                            margin-right: 6px;
                            vertical-align: middle;
                            border-radius: 2px;
                        }
                    </style>

                    <div class="legend-container">
                        <div class="legend-box">
                            <div class="legend-title">Hindernisse-Legende für Solar ☀️</div>
                            <div class="legend-grid">
                                <div><i style="background: gray;" class="legend-icon"></i> Verkehr</div>
                                <div><i style="background: green;" class="legend-icon"></i> Landnutzung</div>
                                <div><i style="background: red;" class="legend-icon"></i> Gebäude</div>
                                <div><i style="background: blue;" class="legend-icon"></i> Gewässer</div>
                                <div><i style="background: purple;" class="legend-icon"></i> Schutzgebiet</div>
                                <div><i style="background: orange;" class="legend-icon"></i> Stromleitung</div>
                                <div><i style="background: #FF00FF;" class="legend-icon"></i> Zufahrtswege</div>
                                <div><i style="background: #8B4513;" class="legend-icon"></i> Kranstellplätze</div>
                            </div>
                        </div>

                        <div class="legend-box">
                            <div class="legend-title">Hindernisse-Legende für Wind 💨</div>
                            <div class="legend-grid">
                                <div><i style="background: rgb(128, 128, 128);" class="legend-icon"></i> Verkehr</div>
                                <div><i style="background: rgb(34, 139, 34);" class="legend-icon"></i> Landnutzung</div>
                                <div><i style="background: rgb(220, 20, 60);" class="legend-icon"></i> Infrastruktur</div>
                                <div><i style="background: rgb(255, 140, 0);" class="legend-icon"></i> Militär</div>
                                <div><i style="background: rgb(128, 0, 128);" class="legend-icon"></i> Artenschutz</div>
                                <div><i style="background: rgb(30, 144, 255);" class="legend-icon"></i> Natur & Landschaft</div>
                                <div><i style="background: rgb(107, 142, 35);" class="legend-icon"></i> Wald</div>
                                <div><i style="background: rgb(32, 178, 170);" class="legend-icon"></i> Gewässer</div>
                                <div><i style="background: rgb(139, 69, 19);" class="legend-icon"></i> Sonstiges</div>
                            </div>
                        </div>
                    </div>
                """
                map_with_legend = f"""
                    <style>
                        .map-wrapper {{
                            margin: 0;
                            padding: 0;
                            width: 700px;
                        }}

                        .map-wrapper iframe {{
                            width: 700px !important;
                            height: 500px !important;
                            margin: 0 !important;
                            padding: 0 !important;
                            border: none !important;
                            display: block;
                            position: relative;
                        }}
                    </style>

                    <div class="map-wrapper">
                        {st.session_state["second_map_html"]}
                    </div>

                    {legend_template}
                """
                html(map_with_legend, height=1000)

        st.download_button(
            "Karte als HTML herunterladen",
            data=st.session_state["second_map_html"],
            file_name="map_fragment.html",
            mime="text/html",
        )

        status_box.info("✅ Erfolgreich!")

def OpenSTEF():
    st.title("Energy Forecasting with OpenSTEF")
        # Fetch unique locations for dropdown with caching
    unique_locations = get_cached_unique_locations("solar", mastr_db_path)

    # Dropdown for location selection
    location = st.selectbox("Select city", options=unique_locations, index=unique_locations.index("Essen") if "Essen" in unique_locations else 0)
    
    return 0       
    


pg = st.navigation([
    st.Page(research_results, title="Forschungsergebnisse"),
    st.Page(network_calculations, title="Netzberechnungen"),
    st.Page(bev_settings, title="BEV Einstellungen"),
    st.Page(hydrogen_electrolyzer_settings, title="Wasserstoff-Elektrolyseur"),
    st.Page(heatpump_configuration, title="Wärmepumpe"),
    st.Page(pv_configuration, title="PV Konfiguration"),
    st.Page(wind_configuration, title="Windkonfiguration"),
    st.Page(electrical_storage_configuration, title="Elektrischer Speicher"),
    st.Page(thermal_storage_settings, title="Thermischer Speicher"),
    st.Page(solar_installation_mastr, title="Solaranlagen"),
    st.Page(wind_installation_mastr, title="Windanlagen"),
    st.Page(storage_installation_mastr, title="Speicheranlagen"),
    st.Page(energy_generation_solar, title="Solare Energieerzeugung"),
    st.Page(wind_energy_generation, title="Windenergieerzeugung"),
    st.Page(FFPV_WEA, title="FFPV & WEA Planung"),
    st.Page(OpenSTEF, title="Kurzfristige Energieprognose (OpenSTEF)"),
])
pg.run()
