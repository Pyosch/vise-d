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
    
    grid_type = ['Standard']
    ev_diffusion = [30, 50, 70]
    hp_diffusion = ['Standard']
    pv_storage_diffusion = ['Standard']
    curtailment = ['Keine']
    wholesale_tariff = ['Real-time-tariff', 'Time-of-use-tariff', 'Fixed-tariff']
    grid_usage_fees = ['Fixed', 'Variabel']
    
    selected_grid_type = st.selectbox('Netz Typ', grid_type)
    selected_ev_diffusion = st.selectbox('EV Diffusion', ev_diffusion)
    selected_hp_diffusion = st.selectbox('WP Diffusion', hp_diffusion)
    selected_pv_storage_diffusion = st.selectbox('PV Speicher Diffusion', pv_storage_diffusion)
    selected_curtailment = st.selectbox('Curtailment', curtailment)
    selected_wholesale_tariff = st.selectbox('Wholesale Tariff', wholesale_tariff)
    selected_grid_usage_fees = st.selectbox('Netznutzungsgebühren', grid_usage_fees)
    
