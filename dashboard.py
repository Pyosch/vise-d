# Installing Relevant libraries
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import datetime
import streamlit as st
from st_files_connection import FilesConnection
import os
import osmnx as ox

from paper_figures import fig_5, fig_7, fig_8, fig_9, fig_5_plotly
from pp_networks import pp_networks
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

from mastr_preprocessing import prepare_solar_data, prepare_wind_data, prepare_storage_data, prepare_grid_connections_data
from mastr_preprocessing import fetch_solar, fetch_wind, fetch_storage
from mastr_preprocessing import get_unique_solar_locations, get_unique_wind_locations, get_unique_storage_locations

mastr_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'open-mastr.db'))
# mastr_db_path = 'C:/Users/mashu/.open-MaStR/data/sqlite/open-mastr.db'



st.set_page_config(page_title='VISE-D Dashboard', 
                    page_icon=':bar_chart:',
                    layout='centered',
                    initial_sidebar_state='expanded'
                    )

st.write('Willkommen beim VISE-D Dashboard! Die Seite befindet sich noch in der Entwicklung.')


st.cache_data
st.cache_resource
# Load data
#conn = st.connection('gcs', type=FilesConnection)
#df = conn.read("vise-d/240912_inputs_online_tool.csv", input_format="csv", ttl=600)
#df = conn.read("vise-d/example_data_10000.csv", input_format="csv", ttl=600)
df = pd.read_csv('./data/figures/example_data_10000.csv')


def update_violin_plot(df,
                       ev_penetration, 
                       curtailment,
                       selected_grid_type, 
                       selected_hp_diffusion, 
                       selected_pv_storage_diffusion,
                       selected_wholesale_tariff, 
                       selected_grid_usage_fees):
             
    df_selected = df[(df['diffusion_evs'] == ev_penetration) 
                    & (df['curtailment'] == curtailment) 
                    & (df['grid_type'] == selected_grid_type)
                    & (df['diffusion_hps'] == selected_hp_diffusion)
                    & (df['diffusion_pv_storage'] == selected_pv_storage_diffusion)
                    & (df['tariff_wholesale'] == selected_wholesale_tariff)
                    & (df['tariff_grid_usage_fee'] == selected_grid_usage_fees)
                    ]
    
    fig = px.violin(df_selected, 
                    y='value', 
                    box=True, 
                    points="all"
                    )
    return fig


def Violinplot():
    with st.sidebar:
        st.title('VISE-D')
        
        grid_type = df.grid_type.unique()
        ev_diffusion = sorted(df.diffusion_evs.unique())
        hp_diffusion = df.diffusion_hps.unique()
        pv_storage_diffusion = df.diffusion_pv_storage.unique()
        curtailment = df.curtailment.unique()
        wholesale_tariff = df.tariff_wholesale.unique()
        grid_usage_fees = df.tariff_grid_usage_fee.unique()
        
        selected_grid_type = st.selectbox('Netz Typ', grid_type)
        selected_ev_diffusion = st.selectbox('EV Diffusion', ev_diffusion)
        selected_hp_diffusion = st.selectbox('WP Diffusion', hp_diffusion)
        selected_pv_storage_diffusion = st.selectbox('PV Speicher Diffusion', pv_storage_diffusion)
        selected_curtailment = st.selectbox('Curtailment', curtailment)
        selected_wholesale_tariff = st.selectbox('Wholesale Tariff', wholesale_tariff)
        selected_grid_usage_fees = st.selectbox('Netznutzungsgebühren', grid_usage_fees)

    st.write('## Violin Plot')

    st.plotly_chart(update_violin_plot(df,
                                    selected_ev_diffusion, 
                                    selected_curtailment,
                                    selected_grid_type, 
                                    selected_hp_diffusion, 
                                    selected_pv_storage_diffusion,
                                    selected_wholesale_tariff, 
                                    selected_grid_usage_fees)
                    )



def Forschungsergebnisse():
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

   
    
def Netzberechnungen():
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


def BEV_settings():
   
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


def heatpump_configuaration():
    
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


 
    
def PV_configuration(): 
    
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
        



def Solar_Installation_Mastr():
    st.title("Solar Installations Dashboard")

    # Fetch unique locations for dropdown
    unique_locations = get_unique_solar_locations(mastr_db_path=mastr_db_path)

    # Dropdown for location selection
    location = st.selectbox("Select city", options=unique_locations, index=unique_locations.index("Essen") if "Essen" in unique_locations else 0)

    # Button to trigger visualization
    if st.button("Visualize"):
        if location:
            try:
                # Get data from prepare_solar_data
                with st.spinner("Loading data..."):
                    gdf_solar, city_district = prepare_solar_data(location=location, mastr_db_path=mastr_db_path)

                # Create scatter map
                fig = px.scatter_mapbox(
                    gdf_solar,
                    lat='Breitengrad',
                    lon='Laengengrad',
                    size_max=45,
                    color_discrete_sequence=['red'],
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
                st.subheader("Plotted Solar Installations")
                st.dataframe(
                    gdf_solar[['NameStromerzeugungseinheit', 'Bruttoleistung', 'Nettonennleistung', 'Breitengrad', 'Laengengrad']]
                )
                
            except Exception as e:
                st.error(f"Failed to visualize data for {location}: {str(e)}")
        else:
            st.warning("Please select a city.")


def Wind_Installation_Mastr():
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



def Storage_Installation_Mastr():
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
    
from mastr_energy_generation import pick_pvsystem_mastr, prepare_pv_time_series_mastr, aggregate_pv_time_series,revise_power_values,wind_turbine_matching


def energy_generation_solar():
    st.title("Energy Generation from Solar Installations")
    
    # Fetch unique locations for dropdown
    unique_locations = get_unique_solar_locations(mastr_db_path=mastr_db_path)

    # Dropdown for location selection
    location = st.selectbox("Select city", options=unique_locations, index=unique_locations.index("Essen") if "Essen" in unique_locations else 0)
    if location:
        if st.button("Simulate Energy Generation"):
            with st.spinner("Preparing and simulating PV systems..."):
                try:
                    start = "2015-07-07 00:00:00"
                    end = "2015-07-07 23:45:00"
                    gdf_solar, city_district = prepare_solar_data(location=location, mastr_db_path=mastr_db_path)
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
from mastr_energy_generation import init_windturbines_mastr, prepare_wind_time_series_mastr, aggregate_wind_time_series
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


pg = st.navigation([
    st.Page(Forschungsergebnisse, title="Research Results"),
    st.Page(Netzberechnungen, title="Network Calculations"),
    st.Page(Violinplot, title="Violin Plot"), 
    st.Page(BEV_settings, title="BEV Settings"),
    st.Page(hydrogen_electrolyzer_settings, title="Hydrogen Electrolyzer"),
    st.Page(heatpump_configuaration, title="Heat Pump"),
    st.Page(PV_configuration, title="PV Configuration"),
    st.Page(wind_configuration, title="Wind Configuration"),
    st.Page(electrical_storage_configuration, title="Electrical Storage"),
    st.Page(thermal_storage_settings, title="Thermal Storage"),
    st.Page(Solar_Installation_Mastr, title="Solar Installations"),
    st.Page(Wind_Installation_Mastr, title="Wind Installations"),
    st.Page(Storage_Installation_Mastr, title="Storage Installations"),
    st.Page(energy_generation_solar, title="Solar Energy Generation"),
    st.Page(wind_energy_generation, title="Wind Energy Generation"),
])
pg.run()
