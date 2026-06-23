"""VISE-D Dashboard - Main Application Entry Point.

Virtuelles Institut Smart Energy - Smart Data
Interactive energy system analysis dashboard for German distribution grids.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import streamlit as st

# Import configuration
from src.config import MASTR_DB_PATH

# =============================================================================
# Lazy page wrappers
# Each function imports its page module on first call, so no heavy library
# loads at dashboard startup.
# =============================================================================

def _startseite():
    from src.pages.startseite import startseite
    startseite()

def _research_results():
    from src.pages.research_results import research_results
    research_results()

def _grid_expansion_research():
    from src.pages.grid_expansion_research import grid_expansion_research
    grid_expansion_research()

def _bev_settings():
    from src.pages.bev_settings import bev_settings
    bev_settings()

def _heatpump_configuration():
    from src.pages.heatpump_configuration import heatpump_configuration
    heatpump_configuration()

def _pv_configuration():
    from src.pages.pv_configuration import pv_configuration
    pv_configuration()

def _wind_configuration():
    from src.pages.wind_configuration import wind_configuration
    wind_configuration()

def _electrical_storage_configuration():
    from src.pages.electrical_storage_configuration import electrical_storage_configuration
    electrical_storage_configuration()

def _thermal_storage_settings():
    from src.pages.thermal_storage_settings import thermal_storage_settings
    thermal_storage_settings()

def _netzmodell():
    from src.pages.netzmodell import netzmodell
    netzmodell()

def _flexibility_configurator():
    from src.pages.flexibility_configurator import flexibility_configurator
    flexibility_configurator()

def _solar_installation_mastr():
    from src.pages.solar_installation_mastr import solar_installation_mastr
    solar_installation_mastr()

def _wind_installation_mastr():
    from src.pages.wind_installation_mastr import wind_installation_mastr
    wind_installation_mastr()

def _storage_installation_mastr():
    from src.pages.storage_installation_mastr import storage_installation_mastr
    storage_installation_mastr()



# =============================================================================
# Application Configuration
# =============================================================================

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
    if st.button("🔄 Stadtlisten aktualisieren", help="Stadtlisten aus MaStR-Datenbank neu laden (einmalig langsam)"):
        with st.spinner("Stadtlisten werden neu aufgebaut…"):
            try:
                from src.mastr.preprocessing import rebuild_location_caches
                rebuild_location_caches()
                st.cache_data.clear()
                st.success("✅ Stadtlisten aktualisiert!")
            except Exception as e:
                st.error(f"Fehler: {e}")

# =============================================================================
# Page Navigation
# =============================================================================

# Build all page objects once, keyed by the same identifiers used in
# src/content/page_descriptions.py. The start page references these objects via
# st.page_link, and other pages use them for st.switch_page() navigation.
_page_startseite = st.Page(_startseite, title="Startseite", icon="🏠", default=True)

pages = {
    "research_results": st.Page(_research_results, title="Integration von E-Fahrzeugen in Verteilnetze"),
    "grid_expansion": st.Page(_grid_expansion_research, title="Flexibilität in Groß- und Verteilnetzen"),
    "bev_settings": st.Page(_bev_settings, title="E-Mobilität"),
    "heatpump": st.Page(_heatpump_configuration, title="Wärmepumpe"),
    "pv": st.Page(_pv_configuration, title="Photovoltaik"),
    "wind": st.Page(_wind_configuration, title="Windenergie"),
    "electrical_storage": st.Page(_electrical_storage_configuration, title="Elektrischer Speicher"),
    "thermal_storage": st.Page(_thermal_storage_settings, title="Thermischer Speicher"),
    "netzmodell": st.Page(_netzmodell, title="Netzmodell-Szenario"),
    "flexibility": st.Page(_flexibility_configurator, title="Flexibilitätskonfigurator"),
    "solar_mastr": st.Page(_solar_installation_mastr, title="Solaranlagen"),
    "wind_mastr": st.Page(_wind_installation_mastr, title="Windanlagen"),
    "storage_mastr": st.Page(_storage_installation_mastr, title="Speicheranlagen"),
}

# Store references so other pages can call st.switch_page() / st.page_link.
st.session_state["_pages"] = pages
st.session_state["_page_network_scenario"] = pages["netzmodell"]
st.session_state["_page_flex_configurator"] = pages["flexibility"]

pg = st.navigation({
    "Übersicht": [_page_startseite],
    "Energiesystemanalysen": [
        pages["netzmodell"],
        pages["flexibility"],
    ],
    "Marktstammdatenregister": [
        pages["solar_mastr"],
        pages["wind_mastr"],
        pages["storage_mastr"],
    ],
    "Forschungsergebnisse": [
        pages["research_results"],
        pages["grid_expansion"],
    ],
    "Lastprofilgeneratoren": [
        pages["bev_settings"],
        pages["heatpump"],
        pages["pv"],
        pages["wind"],
        pages["electrical_storage"],
        pages["thermal_storage"],
    ],
})

pg.run()
