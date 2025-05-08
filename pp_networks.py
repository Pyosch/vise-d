import pandapower as pp
import pandapower.networks as pn

import streamlit as st

def pp_networks():
    
    st.title('Beispielhafte Netzberechnung')
    
    networks = ['Keine Auswahl', 'Einfaches Beispiel', 'Multispannungs-Beispielnetz', '4-Knoten-Stickleitung', 'CIGRE Niederspannungsnetz']
    selected_network = st.selectbox('Select Network', networks)
    
    if selected_network == 'Keine Auswahl':
        st.write('Bitte wählen Sie ein Netzwerk aus der Dropdown-Liste aus.')
        return None
    elif selected_network == 'Einfaches Beispiel':
        net = pn.example_simple()
    elif selected_network == 'Multispannungs-Beispielnetz':
        net = pn.example_multivoltage()
    elif selected_network == '4-Knoten-Stickleitung':
        net = pn.panda_four_load_branch()
    elif selected_network == 'CIGRE Niederspannungsnetz':
        net = pn.create_cigre_network_mv()
    
    # st.write(net)
    
    # Calculate power flow and plot results
    pp.runpp(net)
    st.plotly_chart(pp.plotting.plotly.simple_plotly(net))
    
    
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
    
    return None