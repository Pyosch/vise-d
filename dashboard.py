import pandas as pd
import plotly.express as px

import streamlit as st
from st_files_connection import FilesConnection

st.set_page_config(page_title='VISE-D Dashboard', 
                    page_icon=':bar_chart:',
                    layout='centered',
                    initial_sidebar_state='expanded'
                    )

st.title('VISE-D Dashboard')

st.write('Welcome to the VISE-D Dashboard! This is a demo of the tool developed in the VISE-D project.')

# Sidebar
with st.sidebar:
    st.title('VISE-D')
    
    grid_type = ['standard']
    ev_diffusion = [30, 50, 70]
    hp_diffusion = ['standard']
    pv_storage_diffusion = ['standard']
    curtailment = ['none']
    wholesale_tariff = ['rtt', 'tou', 'fix']
    grid_usage_fees = ['fix', 'variable']
    
    selected_grid_type = st.selectbox('Netz Typ', grid_type)
    selected_ev_diffusion = st.selectbox('EV Diffusion', ev_diffusion)
    selected_hp_diffusion = st.selectbox('WP Diffusion', hp_diffusion)
    selected_pv_storage_diffusion = st.selectbox('PV Speicher Diffusion', pv_storage_diffusion)
    selected_curtailment = st.selectbox('Curtailment', curtailment)
    selected_wholesale_tariff = st.selectbox('Wholesale Tariff', wholesale_tariff)
    selected_grid_usage_fees = st.selectbox('Netznutzungsgebühren', grid_usage_fees)
    
conn = st.connection('gcs', type=FilesConnection)
# df = conn.read("vise-d/240912_inputs_online_tool.csv", input_format="csv", ttl=600)
df = conn.read("vise-d/example_data_10000.csv", input_format="csv", ttl=600)
    
def update_violin_plot(df,
                       ev_penetration, 
                       curtailment,
                       selected_grid_type, 
                       selected_hp_diffusion, 
                       selected_pv_storage_diffusion,
                       selected_wholesale_tariff, 
                       selected_grid_usage_fees):
             
    # df = pd.read_csv('data_example.csv', index_col=0)
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

# Footer with Logos
footer_cols = st.columns(2)

with footer_cols[0]:
    st.image("https://smart-energy-nrw.web.th-koeln.de/wp-content/uploads/2023/10/VISE_D_neu-1024x470.png")
    
with footer_cols[1]:
    st.image("https://smart-energy-nrw.web.th-koeln.de/wp-content/uploads/2023/01/Logo_MWIKEPixel.png")