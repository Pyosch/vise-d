"""VISE-D Dashboard - Main Application Entry Point.

Virtuelles Institut Smart Energy - Smart Data
Interactive energy system analysis dashboard for German distribution grids.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import streamlit as st

import src.utils.preloader  # noqa: F401 — starts background library preload

# Import configuration
from src.config import MASTR_DB_PATH

# =============================================================================
# Lazy page wrappers
# Each function imports its page module on first call, so no heavy library
# loads at dashboard startup.
# =============================================================================

def _research_results():
    from src.pages.research_results import research_results
    research_results()

def _mv_fallstudie():
    from src.pages.mv_fallstudie import mv_fallstudie
    mv_fallstudie()

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

st.write('Willkommen beim VISE-D Dashboard!')

# =============================================================================
# Page Navigation
# =============================================================================

# Build page objects for pages that need cross-page navigation references.
_page_network_scenario = st.Page(_netzmodell, title="Netzmodell-Szenario")
_page_flex_configurator = st.Page(_flexibility_configurator, title="Flexibilitätskonfigurator")

# Store references so other pages can call st.switch_page() with a Page object.
st.session_state["_page_network_scenario"] = _page_network_scenario
st.session_state["_page_flex_configurator"] = _page_flex_configurator

pg = st.navigation({
    "Forschungsergebnisse": [
        st.Page(_research_results, title="Integration von E-Fahrzeugen in Verteilnetze"),
        st.Page(_mv_fallstudie, title="Fallstudie: MS-Netz Validierung"),
    ],
    "Lastprofilgeneratoren": [
        st.Page(_bev_settings, title="E-Mobilität"),
        st.Page(_heatpump_configuration, title="Wärmepumpe"),
        st.Page(_pv_configuration, title="Photovoltaik"),
        st.Page(_wind_configuration, title="Windenergie"),
        st.Page(_electrical_storage_configuration, title="Elektrischer Speicher"),
        st.Page(_thermal_storage_settings, title="Thermischer Speicher"),
    ],
    "Energiesystemanalysen": [
        _page_network_scenario,
        _page_flex_configurator,
    ],
    "Marktstammdatenregister": [
        st.Page(_solar_installation_mastr, title="Solaranlagen"),
        st.Page(_wind_installation_mastr, title="Windanlagen"),
        st.Page(_storage_installation_mastr, title="Speicheranlagen"),
    ],
})

pg.run()
