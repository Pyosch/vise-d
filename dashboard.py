import pandas as pd
import plotly.express as px


import datetime
import streamlit as st
from st_files_connection import FilesConnection
import os

from paper_figures import fig_5, fig_7, fig_8, fig_9, fig_5_plotly
from pp_networks import pp_networks
import matplotlib.pyplot as plt
from vpplib.battery_electric_vehicle import BatteryElectricVehicle
from vpplib.environment import Environment
from vpplib.heat_pump import HeatPump
from vpplib.user_profile import UserProfile
from vpplib.environment import Environment
from vpplib.photovoltaic import Photovoltaic
from vpplib.wind_power import WindPower
from vpplib import ElectricalEnergyStorage
st.set_page_config(page_title='VISE-D Dashboard', 
                    page_icon=':bar_chart:',
                    layout='centered',
                    initial_sidebar_state='expanded'
                    )

st.title('VISE-D Dashboard')

st.write('Willkommen beim VISE-D Dashboard! Die Seite befindet sich noch in der Entwicklung.')

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

# Page title


def battery_electric_vehicle_settings():
    st.title("Battery Electric Vehicle (BEV) Settings")

    # Form layout
    with st.sidebar:
        with st.form(key="bev_settings_form"):
            # Max Battery Capacity
            st.markdown("**Max. Battery Capacity**")
            max_battery_capacity = st.number_input(
                "Enter max battery capacity (kWh)",
                min_value=0.0,
                value=float(st.session_state.bev_settings["max_battery_capacity"]),
                placeholder="e.g. 100 kWh",
                key="max_battery_capacity"
            )

            # Min Battery Capacity
            st.markdown("**Min. Battery Capacity**")
            min_battery_capacity = st.number_input(
                "Enter min battery capacity (kWh)",
                min_value=0.0,
                value=float(st.session_state.bev_settings["min_battery_capacity"]),
                placeholder="e.g. 15 kWh",
                key="min_battery_capacity"
            )

            # Battery Usage
            st.markdown("**Battery Usage**")
            battery_usage = st.number_input(
                "Enter battery usage",
                min_value=0.0,
                value=float(st.session_state.bev_settings["battery_usage"]),
                placeholder="e.g. ???",
                key="battery_usage"
            )
            st.markdown("*Note: Battery usage definition may need clarification.*")

            # Charging Power
            st.markdown("**Charging Power**")
            charging_power = st.number_input(
                "Enter charging power (kW)",
                min_value=0.0,
                value=float(st.session_state.bev_settings["charging_power"]),
                placeholder="e.g. 11 kW",
                key="charging_power"
            )

            # Charging Efficiency
            st.markdown("**Charging Efficiency**")
            charging_efficiency = st.number_input(
                "Enter charging efficiency (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.bev_settings["charging_efficiency"] * 100),
                placeholder="e.g. 90%",
                key="charging_efficiency"
            )
            
            st.markdown("**load_degradation_begin**")
            load_degradation_begin = st.number_input(
            "Enter load degradation begin",
                min_value=0.0,
                value=float(st.session_state.bev_settings["load_degradation_begin"]),
                placeholder="e.g. ???",
                key="load_degradation_begin"
            )
            
            st.markdown("**user_profile**")
            user_profile = st.selectbox(
                "Select user profile",
                options=["None", "Profile 1", "Profile 2"],
                index=0 if st.session_state.bev_settings["user_profile"] == "None" else 1 if st.session_state.bev_settings["user_profile"] == "Profile 1" else 2,
                key="user_profile"
            )
            
        #    st.markdown("**environment**")
        #    selected_environment = st.selectbox(
        #        "Select environment",
        #        options=["None", "Environment 1", "Environment 2"],
        #        index=0 if st.session_state.bev_settings["selected_environment"] == "None" else 1 if st.session_state.bev_settings["selected_environment"] == "Environment 1" else 2,
        #        key="environment"
        #    )
            
            st.markdown("**Start Time**")
            start_time = st.time_input(
                "Enter Start Time HH:MM:SS",
                datetime.time(0,0,0)
                
            )
            
            st.markdown("**End Time**")
            end_time = st.time_input(
                "Enter End Time HH:MM:SS",
                datetime.time(0,0,0)
                
            )
            
            st.markdown("**Timebase**")
            timebase = st.number_input(
                "Enter Timebase (minutes)",
                min_value=1,
                max_value=60,
                value=15,
                step=1,
                key="timebase"
            )
            
            

            # Submit button
            submit_button = st.form_submit_button("Submit Settings")

        # Handle form submission
        if submit_button:
            
        # Update session state with new settings
            st.session_state.bev_settings = {
                "max_battery_capacity": max_battery_capacity,
                "min_battery_capacity": min_battery_capacity,
                "battery_usage": battery_usage,
                "charging_power": charging_power,
                "charging_efficiency": charging_efficiency / 100,
                "load_degradation_begin":load_degradation_begin,
                "user_profile": user_profile,
                #   "environment": selected_environment,
                "start_time": start_time,
                "end_time": end_time,
                "timebase": timebase
            }
           
            # start = "2015-06-01 00:00:00"
            # end = "2015-06-01 23:45:00"
            # timestamp_int = 48
            # timestamp_str = "2015-06-01 12:00:00"
            # env = Environment(start=start, end=end, timebase=timebase)
            
            # # Initialize BEV with form inputs
            # bev = BatteryElectricVehicle(
            #     unit="kW",
            #     identifier="bev_1",
            #     environment=env,
            #     battery_max=max_battery_capacity,
            #     battery_min=min_battery_capacity,
            #     battery_usage=battery_usage,
            #     charging_power=charging_power,
            #     load_degradation_begin=load_degradation_begin,
            #     charge_efficiency=charging_efficiency / 100
            # )
           
        st.success("BEV settings updated successfully!")
            # Display the updated settings for user confirmation
    #    st.json(st.session_state.bev_settings)

        # Optional: Display current settings
    #    st.markdown("### Current BEV Settings")
    #    st.json(st.session_state.bev_settings)
    import pandas as pd

 # Create DataFrame for table
    data = {
    "Metric": ["Max Battery Capacity", "Min Battery Capacity", "Battery Usage", "Charging Power", "Charging Efficiency", "Load Degradation Begin", "User Profile","start_time","end_time","timebase"],
    "Value": [max_battery_capacity, min_battery_capacity, battery_usage, charging_power, charging_efficiency, load_degradation_begin, user_profile,start_time,end_time,timebase],
    "Unit": ["kWh", "kWh", "kWh", "kW", "%", "kWh", "","HH:MM:SS", "HH:MM:SS", "minutes"]
}
    df = pd.DataFrame(data)

    # Display table
    st.subheader("Current BEV Settings")
    st.dataframe(
    df.style.format(
        {
            "Value": lambda x: "{:.1f}".format(x) if isinstance(x, (int, float)) else x
        }
    ).set_properties(**{
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
    with st.form(key="bev_simulation_form"):
        # BEV simulation button
        bev_simulation_button = st.form_submit_button("Simulate BEV")
           
        if bev_simulation_button:
            start = "2015-06-01 00:00:00"
            end = "2015-06-01 23:45:00"
            timestamp_int = 48
            timestamp_str = "2015-06-01 12:00:00"
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
    st.title("Hydrogen Electrolyzer Settings")
    # Layout Section
    with st.sidebar:
        st.subheader("Hydrogen Electrolyzer Settings")

        # Power Electrolyzer Input
 #       col1, col2 = st.columns([3, 2])
 #       with col1:
 #           st.write("Power Electrolyzer")
 #       with col2:
 #           power = st.number_input(
 #               "Power (kW)",
 #               value=15000.0,
 #               placeholder="e.g. 100 kW",
 #               key="input_electrolyzer_power",
 #               step=100.0
 #           )

        # Pressure Input
 #       col3, col4 = st.columns([3, 2])
 #       with col3:
 #           st.write("Pressure")
 #       with col4:
 #           pressure = st.number_input(
 #               "Pressure (bar)",
 #               value=30.0,
 #               placeholder="e.g. 150 bar",
 #               key="input_electrolyzer_pressure",
 #               step=1.0
 #           )

        # Submit Button
        col5, _ = st.columns([2, 3])
        with col5:
            submit = st.button("Submit", key="submit_hydrogen_settings")

        # Callback Logic (Simulated)
        if "hydrogen_settings" not in st.session_state:
            st.session_state.hydrogen_settings = {"Power_Electrolyzer": 15000.0, "Pressure_Hydrogen": 30.0}

        if submit:
            st.session_state.hydrogen_settings = {
                "Power_Electrolyzer": power,
                "Pressure_Hydrogen": pressure
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

#import streamlit as st
import plotly.graph_objects as go


def heatpump_settings():
    # Set page configuration
    # Title
    st.title("Heat Pump Configuration")
    if heatpump_settings not in st.session_state:
        st.session_state.heatpump_settings = {
            "identifier": "None",
        #    "Environment": "None",
            "user_profile": "None",
            "heat_pump_type": "Air",
            "Heat System Temperature": 0.0,
            "el_power": 0.0,
            "th_power":0.0,
            "Ramp Up Time" : datetime.time(0,0),
            "Ramp Down Time":datetime.time(0,0),
            "Minimum Run Time": datetime.time(0,0),
            "Minimum Stop Time": datetime.time(0,0) 
            
            
        }
    with st.sidebar:
        # Input Section
        st.header("Enter Heat Pump Settings")

        identifier = st.selectbox(
        "Select Identifier",
        options=["None", "hp1", "hp2"],
        index=0 if st.session_state.heatpump_settings["identifier"] == "None" else 1 if st.session_state.heatpump_settings["identifier"] == "hp1" else 2,
        key="identifier"
        )
        
        # Environment = st.selectbox(
        # "Select Environment",
        # options=["None", "Environment 1", "Environment 2"],
        # index=0 if st.session_state.heatpump_settings["Environment"] == "None" else 1 if st.session_state.heatpump_settings["Environment"] == "Environment 1" else 2,
        # key="Environment"
        # )
        
        user_profile = st.selectbox(
            "user Profile",
            options = ["None","Profile1","Profile2"],
            index = 0 if st.session_state.heatpump_settings["user_profile"]=="None" else 1 if st.session_state.heatpump_settings["user_profile"]=="Profile1" else 2,
            key = "user_profile"
        ) 

    # Dropdown for Heat Pump Type
        heat_pump_type = st.selectbox(
        "Type of Heat Pump",
        options=["Air", "Ground"],
        index=0,
            placeholder="Select heat pump type"
    )

    # Number input for Heat System Temperature
        system_temperature = st.number_input(
        "Heat System Temperature (°C)",
        min_value=-50.0,
        max_value=100.0,
        value=0.0,
        step=0.1,
        placeholder="e.g. 20.5"
    )

    # Number input for Electrical Power
        el_power = st.number_input(
        "el_power (kW)",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=0.1,
        placeholder="e.g. 5"
    )
        
        th_power = st.number_input(
            "th_power (KW)",
            min_value = 0.0,
            max_value = 100.0,
            value = 0.0,
            step = 0.1,
            placeholder = "e.g. 5"
        )
        
        
        ramp_up_time = st.time_input(
            "Enter ramp up time (HH:MM)",
                value=datetime.time(0,0)
                
            )
            
        ramp_down_time = st.time_input(
            "Enter ramp down time (HH:MM)",
                value=datetime.time(0,0)
                
            )
        
        min_run_time = st.time_input(
            "Enter run time (HH:MM)",
                value=datetime.time(0,0)
            )
        
        min_stop_time = st.time_input(
            "Enter stop time (HH:MM)",
                value=datetime.time(0,0)
                
            )
        
        
        

    # Submit button
        if st.button("Submit Settings",key="submit_heatpump_settings"):
        # Store settings in session state
            st.session_state.heatpump_settings = {
                "identifier": identifier,
                "heat_pump_type": heat_pump_type,
                "Heat System Temperature": system_temperature,
                "el_power": el_power,
        #        "Environment": Environment,
                "user_profile": user_profile,
                "th_power":th_power,
                "Ramp Up Time" : ramp_up_time,
                "Ramp Down Time":ramp_down_time,
                "Minimum Run Time": min_run_time,
                "Minimum Stop Time": min_stop_time  
            
        }

    # Display stored settings if available
    if "heatpump_settings" in st.session_state:
        st.header("Current Heat Pump Settings")
        # Create a DataFrame for the table
        settings_df = pd.DataFrame([
            {"Setting": key, "Value": value}
            for key, value in st.session_state.heatpump_settings.items()
        ])
        
        # Style the DataFrame for better presentation
        st.dataframe(
            settings_df,
            use_container_width=True,
            column_config={
                "Setting": st.column_config.TextColumn("Setting", width="medium"),
                "Value": st.column_config.TextColumn("Value", width="large")
            }
        )
   #     st.json(st.session_state.heatpump_settings)

    # # Create a pie chart to visualize the settings
    #     st.header("Settings Visualization")
    #     labels = ["Heat System Temperature (°C)", "Electrical Power (kW)"]
    #     values = [
    #     abs(st.session_state.heatpump_settings["Heat System Temperature"]),  # Use abs to handle negative values
    #     st.session_state.heatpump_settings["Power"]
    # ]
 
    # # Create pie chart using Plotly
    #     fig = go.Figure(
    #         data=[
    #             go.Pie(
    #             labels=labels,
    #             values=values,
    #             textinfo="label+percent",
    #             hoverinfo="label+value",
    #             marker=dict(colors=["#1f77b4", "#ff7f0e"])
    #         )
    #     ]
    #  )
    #     fig.update_layout(
    #         title=f"Heat Pump Settings ({st.session_state.heatpump_settings['Type Heatpump']} Type)",
    #         showlegend=True
    # )
    
    #     # Display the pie chart
    #     st.plotly_chart(fig, use_container_width=True)   




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
            
            # if isinstance(env.mean_temp_hours, list):
            # # Create a datetime index for the year 2015 at hourly frequency
            #     date_range = pd.date_range(start=start, end=end, freq="H")
            # if len(env.mean_temp_hours) == len(date_range):
            #     env.mean_temp_hours = pd.Series(env.mean_temp_hours, index=date_range)
            # else:
            #     st.error("Length of mean_temp_hours does not match expected hourly range.")
            #     return
            
            
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
            
            
            # Convert mean_temp_hours to a pandas Series if it's a list
            
        
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
            
            
            # def test_get_thermal_energy_demand(user_profile):

            
            #user_profile.thermal_energy_demand.plot()
            #plt.show()


            # test_get_thermal_energy_demand(user_profile)  
            
            
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





def pv_settings():
    # Initialize session state for PV settings if not already set
    if "pv_settings" not in st.session_state:
        st.session_state.pv_settings = {
            "PV Module Library": "SandiaMod",
            "PV Module": "Canadian_Solar_CS5P_220M___2009_",
            "PV Inverter Library": "cecinverter",
            "PV Inverter": "ABB__MICRO_0_25_I_OUTD_US_208__208V_",
            "PV Surface Tilt": 0.0,
            "PV Surface Azimuth": 0.0,
            "PV Modules per String": 0,
            "PV Strings per Inverter": 0
        }

    st.title("Photovoltaic (PV) Settings")

    # Input Section in Sidebar
    with st.sidebar:
        st.header("Enter PV Settings")

        module_library = st.selectbox(
            "Module Library",
            options=["SandiaMod", "CECMod"],
            index=0 if st.session_state.pv_settings["PV Module Library"] == "SandiaMod" else 1,
            key="pv_module_library"
        )

        module = st.selectbox(
            "Module",
            options=["Canadian_Solar_CS5P_220M___2009_"],
            index=0,
            key="pv_module"
        )

        inverter_library = st.selectbox(
            "Inverter Library",
            options=["cecinverter"],
            index=0,
            key="pv_inverter_library"
        )

        inverter = st.selectbox(
            "Inverter",
            options=["ABB__MICRO_0_25_I_OUTD_US_208__208V_"],
            index=0,
            key="pv_inverter"
        )

        surface_tilt = st.number_input(
            "Surface Tilt (°)",
            min_value=0.0,
            max_value=90.0,
            value=float(st.session_state.pv_settings["PV Surface Tilt"]),
            step=1.0,
            key="pv_surface_tilt"
        )

        surface_azimuth = st.number_input(
            "Surface Azimuth (°)",
            min_value=0.0,
            max_value=360.0,
            value=float(st.session_state.pv_settings["PV Surface Azimuth"]),
            step=1.0,
            key="pv_surface_azimuth"
        )

        modules_per_string = st.number_input(
            "Modules per String",
            min_value=0,
            value=int(st.session_state.pv_settings["PV Modules per String"]),
            step=1,
            key="pv_modules_per_string"
        )

        strings_per_inverter = st.number_input(
            "Strings per Inverter",
            min_value=0,
            value=int(st.session_state.pv_settings["PV Strings per Inverter"]),
            step=1,
            key="pv_strings_per_inverter"
        )

        if st.button("Submit Settings", key="submit_pv_settings"):
            st.session_state.pv_settings = {
                "PV Module Library": module_library,
                "PV Module": module,
                "PV Inverter Library": inverter_library,
                "PV Inverter": inverter,
                "PV Surface Tilt": surface_tilt,
                "PV Surface Azimuth": surface_azimuth,
                "PV Modules per String": modules_per_string,
                "PV Strings per Inverter": strings_per_inverter
            }
            st.success("PV settings updated successfully!")

    # Display stored settings
    if "pv_settings" in st.session_state:
      #  st.header("Current PV Settings")
      #  st.json(st.session_state.pv_settings)

        # Create DataFrame for table
        data = {
            "Metric": [
                "PV Module Library",
                "PV Module",
                "PV Inverter Library",
                "PV Inverter",
                "PV Surface Tilt",
                "PV Surface Azimuth",
                "PV Modules per String",
                "PV Strings per Inverter"
            ],
            "Value": [
                st.session_state.pv_settings["PV Module Library"],
                st.session_state.pv_settings["PV Module"],
                st.session_state.pv_settings["PV Inverter Library"],
                st.session_state.pv_settings["PV Inverter"],
                st.session_state.pv_settings["PV Surface Tilt"],
                st.session_state.pv_settings["PV Surface Azimuth"],
                st.session_state.pv_settings["PV Modules per String"],
                st.session_state.pv_settings["PV Strings per Inverter"]
            ],
            "Unit": ["", "", "", "", "°", "°", "", ""]
        }
        df = pd.DataFrame(data)

        # Define numeric metrics for formatting
        numeric_metrics = ["PV Surface Tilt", "PV Surface Azimuth", "PV Modules per String", "PV Strings per Inverter"]

        # Pre-format the 'Value' column
        df['Value'] = df.apply(
            lambda row: f"{float(row['Value']):.1f}" if row['Metric'] in numeric_metrics else str(row['Value']),
            axis=1
        )

        # Display table
        st.subheader("PV Settings Table")
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

        # # Pie chart visualization
        # st.header("Settings Visualization")
        # labels = ["Surface Tilt (°)", "Surface Azimuth (°)", "Modules per String", "Strings per Inverter"]
        # values = [
        #     st.session_state.pv_settings["PV Surface Tilt"],
        #     st.session_state.pv_settings["PV Surface Azimuth"],
        #     st.session_state.pv_settings["PV Modules per String"],
        #     st.session_state.pv_settings["PV Strings per Inverter"]
        # ]
        # filtered_labels = [label for label, value in zip(labels, values) if value > 0]
        # filtered_values = [value for value in values if value > 0]

        # if filtered_values:
        #     fig = go.Figure(
        #         data=[go.Pie(
        #             labels=filtered_labels,
        #             values=filtered_values,
        #             textinfo="label+percent",
        #             hoverinfo="label+value",
        #             marker=dict(colors=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"])
        #         )]
        #     )
        #     fig.update_layout(title="PV Numeric Settings Distribution", showlegend=True)
        #     st.plotly_chart(fig, use_container_width=True)
        # else:
        #     st.warning("No valid numeric values to display in the pie chart.")

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
    
def wind():
    if "wind_settings" not in st.session_state:
        st.session_state.wind_settings = {
            "Turbine Type": "E-140",
            "Hub Height" : 0,
            "Rotor Diameter" : 0,
            "Comfort Factor": 0,
            "Data Source": "Wind Turbines",
            "Wind Speed Model": "logarithmic",
            "Density Model" : "Barometric",
            "Temperature Model" : "Linear Gradient",
            "power_output_model": "power_curve",
            "Density Correction": False,
            "Obstacle Height": 0.0,
            "hellman_exp": 0.2
            
        }
        
    with st.sidebar:
        st.header("Wind Turbine Settings")
        
        turbine_type = st.selectbox(
            "Turbine Type",
            options=["E-140/4200", "E-141/4200","E-126/4200"],
            index=0 if "Turbine Type"=="E-140/4200" else 1 if "Turbine Type"=="E-141/4200" else 2,
            key="Turbine Type"
        )
        
        hub_height= st.number_input(
            "Hub Height",
            min_value = 0,
            max_value = 100,
            value = int(st.session_state.wind_settings["Hub Height"]),
            step = 1
        )
        
        rotor_diameter = st.number_input(
            "Rotor Diameter",
            min_value = 0,
            max_value = 100,
            value = int(st.session_state.wind_settings["Rotor Diameter"]),
            step = 1
        )
        
        comfort_factor = st.number_input(
            "Comfort Factor",
            min_value = 0.0,
            max_value = 1.0,
            value = float(st.session_state.wind_settings["Comfort Factor"]),
            step = 1.0
        )  
        
        data_source= st.selectbox(
            "Data Source",
            "Wind Turbines",
            index = 0,
            key = "Data Sources"
        )
        
        wind_speed_model = st.selectbox(
            "Wind Speed Model",
            options = ["logarithmic","hellmann","interpolation_extrapolation"],
            index = 0 if "Wind Speed Model"=="logarithmic" else 1 if "Wind Speed Model"=="hellmann" else 2,
            key = "Wind Speed Model"
        )
        
        density_model= st.selectbox(
            "Density Model",
            options = ['barometric', 'ideal_gas', 'interpolation_extrapolation'],
            index = 0 if "Density Model"=="barometric" else 1 if "Density Model" == "ideal_gas" else 2,
            key = "Density Model"
        )
        
        temperature_model= st.selectbox(
            "Temperature Model",
            options = ['linear_gradient', 'interpolation_extrapolation'],
            index = 0 if "Temperature Model" == "linear_gradient" else 1 ,
            key = "Temperature Model"
        )
        
        power_output_model= st.selectbox(
            "power_output_model",
            options = ['power_curve', 'power_coefficient_curve'],
            index = 0 if "power_output_model"=="power_curve" else 1,
            key = "power_output_model"
        )   
         
        density_correction= st.selectbox(
            "Density Correction",
            options = [True, False], 
            index = 0 if "Density Correction"==True else 1,
            key = "Density Correction"
            
        ) 
        
        obstacle_height= st.number_input(
            "Obstacle Height",
            min_value = 0.0,
            max_value = 100.0,
            value = float(st.session_state.wind_settings["Obstacle Height"]),
            step = 1.0
        )
        
        hellman_exp = st.number_input(
            "hellman_exp",
            min_value = 0.0,
            max_value = 1.0,
            value = float(st.session_state.wind_settings["hellman_exp"]),
            step = 1.0  
        )

        if st.button("Submit Settings", key="submit_wind_settings"):
            st.session_state.wind_settings = {
                "Turbine Type": turbine_type,
                "Hub Height": hub_height,
                "Rotor Diameter": rotor_diameter,
                "Comfort Factor": comfort_factor,
                "Data Source": data_source,
                "Wind Speed Model": wind_speed_model,
                "Density Model": density_model,
                "Temperature Model": temperature_model,
                "power_output_model": power_output_model,
                "Density Correction": density_correction,
                "Obstacle Height": obstacle_height,
                "hellman_exp": hellman_exp
            }
            st.success("Wind settings updated successfully!")
            
    # Display stored settings
    if "wind_settings" in st.session_state:
        st.header("Current Wind Settings")
       # st.json(st.session_state.wind)
        # Create DataFrame for table
        data = {
            "Metric": [
                "Turbine Type",
                "Hub Height",
                "Rotor Diameter",
                "Comfort Factor",
                "Data Source",
                "Wind Speed Model",
                "Density Model",
                "Temperature Model",
                "power_output_model",
                "Density Correction",
                "Obstacle Height",
                "hellman_exp"
            ],
            "Value": [
                st.session_state.wind_settings["Turbine Type"],
                st.session_state.wind_settings["Hub Height"],
                st.session_state.wind_settings["Rotor Diameter"],
                st.session_state.wind_settings["Comfort Factor"],
                st.session_state.wind_settings["Data Source"],
                st.session_state.wind_settings["Wind Speed Model"],
                st.session_state.wind_settings["Density Model"],
                st.session_state.wind_settings["Temperature Model"],
                st.session_state.wind_settings["power_output_model"],
                st.session_state.wind_settings["Density Correction"],
                st.session_state.wind_settings["Obstacle Height"],
                st.session_state.wind_settings["hellman_exp"]
            ]
            
        }
        
        df = pd.DataFrame(data)
        
    # Define numeric metrics for formatting
    numeric_metrics = ["Hub Height", "Rotor Diameter", "Comfort Factor","Obstacle Height", "hellman_exp"]
    # Pre-format the 'Value' column
    df['Value'] = df.apply(
    lambda row: f"{float(row['Value']):.1f}" if row['Metric'] in numeric_metrics else str(row['Value']),
            axis=1
    )
        
            
    # Display table
    st.subheader("Wind Settings Table")
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

    with st.form(key="wind_simulation_form"):
        # Wind simulation button
        wind_simulation_button = st.form_submit_button("Simulate Wind Turbine")
           
        if wind_simulation_button:
            latitude = 51.200001
            longitude = 6.433333
            timestamp_int = 12
            timestamp_str = "2015-01-09 12:00:00"
            env = Environment(
            start = "2015-01-01 00:00:00", 
            end = "2015-12-31 23:45:00", 
            use_timezone_aware_time_index = True, 
            surpress_output_globally = False
            )
            env.get_dwd_wind_data(lat=latitude, lon=longitude)
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
    
    
    
    
    
    
    

def electrical_storage():
    if "electrical_storage" not in st.session_state:
        st.session_state.electrical_storage={
            "Charge Efficiency": 0,
            "Discharge Efficiency": 0,
            "Max Power" : 0,
            "Max Capacity": 0,
            "max_c":0
            
        }
    st.title("Electrical_Storage")
    
    with st.sidebar:
        st.header("Enter Electrical Storage settings")
        
        st.markdown("**Charging Efficiency**")
        charging_efficiency = st.number_input(
                "Enter charging efficiency (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.electrical_storage["Charge Efficiency"] * 100),
                placeholder="e.g. 90%",
                key="charging_efficiency"
            )
        st.markdown("**Discharging Efficiency**")
        discharging_efficiency = st.number_input(
                "Enter discharging efficiency (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.electrical_storage["Discharge Efficiency"] * 100),
                placeholder="e.g. 90%",
                key="discharging_efficiency"
            )
        
        st.markdown("**Max Power**")
        max_power = st.number_input(
                "Enter max power (kW)",
                min_value=0.0,
                value=float(st.session_state.electrical_storage["Max Power"]),
                placeholder="e.g. 100 kW",
                key="max_power"
            )
        
        st.markdown("**Max Capacity**")
        max_capacity = st.number_input(
        "Enter max capacity (kWh)",
        min_value=0.0,
        value=float(st.session_state.electrical_storage["Max Capacity"]),  # Use "max_c" and provide default
        placeholder="e.g. 100 kWh",
        key="max_capacity"
        )

        st.markdown("**Max Charge Rate**")
        max_c = st.number_input(
        "Enter max charge rate",
        min_value=0.0,
        value=float(st.session_state.electrical_storage.get("max_c", 0.5)),  # Provide default value
        placeholder="e.g. 0.5",
        key="max_c"
        )
        
        # Submit button
        if st.button("Submit Settings", key="submit_electrical_storage_settings"):
            st.session_state.electrical_storage = {
                 "Charge Efficiency": charging_efficiency/100,
                 "Discharge Efficiency": discharging_efficiency / 100,
                 "Max Power": max_power,
                 "Max Capacity": max_capacity,
                 "max_c": max_c
                 }
            st.success("Electrical Storage settings updated successfully!")
        
    # Display stored settings
    if "electrical_storage" in st.session_state:
        st.header("Current Electrical Storage Settings")
        st.json(st.session_state.electrical_storage)

        # Create DataFrame for table
        data = {
            "Metric": [
                "Charge Efficiency",
                "Discharge Efficiency",
                "Max Power",
                "Max Capacity",
                "max_c"
            ],
            "Value": [
                st.session_state.electrical_storage["Charge Efficiency"],
                st.session_state.electrical_storage["Discharge Efficiency"],
                st.session_state.electrical_storage["Max Power"],
                st.session_state.electrical_storage["Max Capacity"],
                st.session_state.electrical_storage["max_c"]
            ],
            "Unit": [",", ",", "kW", "kWh","."]
        }
        df = pd.DataFrame(data)

        # Display table
        st.subheader("Electrical Storage Settings Table")
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
            # PhotoV = Photovoltaic(
            #     unit="KW",
            #     latitude=50.941357,
            #     longitude=6.958307,
            #     identifier=(name + "_pv"),
            #     environment=env,
            #     module_lib=st.session_state.pv_settings["PV Module Library"],
            #     module=st.session_state.pv_settings["PV Module"],
            #     inverter_lib=st.session_state.pv_settings["PV Inverter Library"],
            #     inverter=st.session_state.pv_settings["PV Inverter"],
            #     surface_tilt=20,
            #     surface_azimuth=200,
            #     modules_per_string=4,
            #     strings_per_inverter=2,
            #     temp_lib= 'sapm',
            #     temp_model='open_rack_glass_glass'
            # )
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
        #    PhotoV.timeseries.bus_pv = PhotoV.timeseries.bus_pv.groupby(PhotoV.timeseries.bus_pv.index).mean()
            
            baseload = pd.read_csv("./input/baseload/df_S_15min.csv")
            baseload.drop(columns=["Time"], inplace=True)
            
            
            baseload.set_index(env.pv_data.index, inplace=True)
        
            # # combine baseload and pv timeseries to get residual load
            # baseload["0"] = baseload["0"].tz_localize(None)  # Add this
            # PhotoV.timeseries.bus_pv = PhotoV.timeseries.bus_pv.tz_localize(None)
            
            
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
        
        





pg = st.navigation([st.Page(Forschungsergebnisse), 
                    st.Page(Netzberechnungen), 
                    st.Page(Violinplot), 
                    st.Page(battery_electric_vehicle_settings),
                    st.Page(hydrogen_electrolyzer_settings),
                    st.Page(heatpump_settings),
                    st.Page(pv_settings),
                    st.Page(wind),
                    st.Page(electrical_storage),
                    st.Page(thermal_storage_settings)],)
pg.run()
