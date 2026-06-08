"""Startseite des VISE-D Dashboards.

Bietet einen Überblick über alle Unterseiten – gruppiert nach Kategorie, mit
Kurzbeschreibung und klickbarem Navigationslink. Die Beschreibungen stammen aus
``src.content.page_descriptions`` (Single Source of Truth) und erscheinen
identisch auf den jeweiligen Unterseiten.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Opus 4.8)
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Opus 4.8)"]

import streamlit as st

from src.content.page_descriptions import PAGE_DESCRIPTIONS, PAGE_OVERVIEW


def startseite() -> None:
    """Zeigt die Startseite mit Überblick und Navigation zu allen Seiten."""
    st.title("Willkommen beim VISE-D Dashboard")
    st.write(
        "Virtuelles Institut Smart Energy – Smart Data. Dieses Dashboard "
        "bündelt Werkzeuge zur Analyse von Energiesystemen in deutschen "
        "Verteilnetzen: von Lastprofilgeneratoren über Netzberechnungen bis hin "
        "zu Auswertungen des Marktstammdatenregisters."
    )
    st.caption(
        "Wählen Sie unten oder in der Seitenleiste eine Seite aus. Jede Seite "
        "enthält oben einen ausklappbaren Hinweis mit derselben Erläuterung."
    )

    # st.Page-Objekte werden in dashboard.py aufgebaut und hier referenziert,
    # damit st.page_link direkt zur jeweiligen Seite navigieren kann.
    pages = st.session_state.get("_pages", {})

    for category, entries in PAGE_OVERVIEW.items():
        st.header(category)
        for key, title in entries:
            page_obj = pages.get(key)
            if page_obj is not None:
                st.page_link(page_obj, label=f"**{title}**", icon="➡️")
            else:
                st.markdown(f"**{title}**")
            st.caption(PAGE_DESCRIPTIONS.get(key, ""))
        st.divider()
