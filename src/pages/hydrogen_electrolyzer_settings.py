"""
Hydrogen electrolyzer settings page.

Provides configuration form for hydrogen electrolyzer simulation.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import pandas as pd
import streamlit as st
import plotly.graph_objects as go


def hydrogen_electrolyzer_settings() -> None:
    """Configure hydrogen electrolyzer simulation parameters."""
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
            st.session_state["hydrogen_settings"] = {"Power_Electrolyzer": 15000.0, "Pressure_Hydrogen": 30.0}

        if submit:
            st.session_state["hydrogen_settings"] = {
                "Power_Electrolyzer": power_electrolyzer,
                "Pressure_Hydrogen": pressure_hydrogen
            }

    data = {
            "Metric": ["Power Electrolyzer", "Pressure Hydrogen"],
            "Value": [
                st.session_state["hydrogen_settings"]["Power_Electrolyzer"],
                st.session_state["hydrogen_settings"]["Pressure_Hydrogen"]
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

    st.plotly_chart(fig_power, use_container_width=True)
    st.plotly_chart(fig_pressure, use_container_width=True)
