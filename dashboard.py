"""VISE-D Dashboard - Main Application Entry Point.

Virtuelles Institut Smart Energy - Smart Data
Interactive energy system analysis dashboard for German distribution grids.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import streamlit as st

# Import page functions
from src.pages import (
    research_results,
    bev_settings,
    pv_configuration,
    wind_configuration,
    heatpump_configuration,
    electrical_storage_configuration,
    thermal_storage_settings,
    solar_installation_mastr,
    wind_installation_mastr,
    storage_installation_mastr,
    energy_generation_solar,
    wind_energy_generation,
    flexibility_configurator,
    netzmodell,
    mv_fallstudie,
)
from src.pages.networks import Netzberechnung

# Import configuration
from src.config import MASTR_DB_PATH

# =============================================================================
# Application Configuration
# =============================================================================

# MaStR database path from configuration
mastr_db_path = str(MASTR_DB_PATH)

st.set_page_config(
    page_title='VISE-D Dashboard',
    page_icon=':bar_chart:',
    layout='centered',
    initial_sidebar_state='expanded'
)

# Sidebar: Cache Management
with st.sidebar:
    st.markdown("---")
    st.markdown("**⚡ Performance**")
    if st.button("🗑️ Cache leeren", help="Alle zwischengespeicherten Daten löschen"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("✅ Cache geleert!")
        st.rerun()

st.write('Willkommen beim VISE-D Dashboard! Die Seite befindet sich noch in der Entwicklung.')

# =============================================================================
# Page Navigation
# =============================================================================

# Build page objects for pages that need cross-page navigation references.
_page_network_scenario = st.Page(netzmodell, title="Netzmodell-Szenario")
_page_flex_configurator = st.Page(flexibility_configurator, title="Flexibilitätskonfigurator")

# Store references so other pages can call st.switch_page() with a Page object.
st.session_state["_page_network_scenario"] = _page_network_scenario
st.session_state["_page_flex_configurator"] = _page_flex_configurator

pg = st.navigation({
    "Forschungsergebnisse": [
        st.Page(research_results, title="Integration von E-Fahrzeugen in Verteilnetze"),
        st.Page(mv_fallstudie, title="Fallstudie: MS-Netz Validierung"),
    ],
    "Lastprofilgeneratoren": [
        st.Page(bev_settings, title="E-Mobilität"),
        st.Page(heatpump_configuration, title="Wärmepumpe"),
        st.Page(pv_configuration, title="Photovoltaik"),
        st.Page(wind_configuration, title="Windenergie"),
        st.Page(electrical_storage_configuration, title="Elektrischer Speicher"),
        st.Page(thermal_storage_settings, title="Thermischer Speicher"),
    ],
    "Energiesystemanalysen": [
        _page_network_scenario,
        _page_flex_configurator,
        st.Page(solar_installation_mastr, title="Solaranlagen"),
        st.Page(wind_installation_mastr, title="Windanlagen"),
        st.Page(storage_installation_mastr, title="Speicheranlagen"),
        st.Page(energy_generation_solar, title="Solare Energieerzeugung"),
        st.Page(wind_energy_generation, title="Windenergieerzeugung"),
    ],
})

pg.run()
