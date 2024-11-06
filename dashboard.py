import pandas as pd
import plotly.express as px

import streamlit as st

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
    
def update_violin_plot(ev_penetration, 
                       curtailment,
                       selected_grid_type, 
                       selected_hp_diffusion, 
                       selected_pv_storage_diffusion,
                       selected_wholesale_tariff, 
                       selected_grid_usage_fees):
             
    df = pd.read_csv('data_example.csv', index_col=0)
    df_selected = df[(df['ev_penetration'] == ev_penetration) 
                    & (df['curtailment'] == curtailment) 
                    & (df['grid_type'] == selected_grid_type)
                    & (df['hp_diffusion'] == selected_hp_diffusion)
                    & (df['pv_storage_diffusion'] == selected_pv_storage_diffusion)
                    & (df['wholesale_tariff'] == selected_wholesale_tariff)
                    & (df['grid_usage_fees'] == selected_grid_usage_fees)
                    ]
    
    fig = px.violin(df_selected, 
                    y='value', 
                    box=True, 
                    points="all"
                    )
    return fig

st.write('## Violin Plot')

st.plotly_chart(update_violin_plot(selected_ev_diffusion, 
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