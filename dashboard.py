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
    network_calculations,
    bev_settings,
    pv_configuration,
    wind_configuration,
    heatpump_configuration,
    electrical_storage_configuration,
    openstef_forecasting,
    hydrogen_research,
    hydrogen_electrolyzer_settings,
    thermal_storage_settings,
    solar_installation_mastr,
    wind_installation_mastr,
    storage_installation_mastr,
    energy_generation_solar,
    wind_energy_generation
)
from src.pages.networks_excel import Netzberechnung_mit_excel_daten
from src.pages.planning_ffpv_wea import planning_ffpv_wea

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

pg = st.navigation([
    st.Page(research_results, title="Forschungsergebnisse"),
    st.Page(network_calculations, title="Netzberechnungen"),
    st.Page(bev_settings, title="BEV Einstellungen"),
    st.Page(hydrogen_research, title="Forschung: E-Fahrzeuge Integration"),
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
    st.Page(planning_ffpv_wea, title="FFPV & WEA Planung"),
    st.Page(openstef_forecasting, title="Kurzfristige Energieprognose (OpenSTEF)"),
    st.Page(Netzberechnung_mit_excel_daten, title="Netzberechnung mit Excel"),
])

pg.run()
