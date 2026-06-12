"""UI helper for selecting a MaStR location with a graceful no-database fallback.

Three tiers, transparent to the caller (see ``src.mastr.online_api`` and the plan):

1. Local SQLite DB present  → dropdown from DB, plant data from SQLite.
2. No DB, location CSV present → dropdown from the shipped place-name CSV, plant data
   fetched live from the public online register.
3. Neither → free-text Ort/PLZ entry, plant data fetched live.

Author: Pyosch
AI Assistance: Claude Code (Claude Opus 4.8)
Created: June 2026
"""

__author__ = "Pyosch"
__credits__ = ["Claude Code (Claude Opus 4.8)"]

from typing import List, Optional

import streamlit as st

from src.mastr.preprocessing import mastr_data_available

_ONLINE_BANNER = (
    "Lokale MaStR-Datenbank nicht gefunden — Anlagen werden live aus dem "
    "öffentlichen MaStR-Online-Register geladen (nur Anlagen „In Betrieb“)."
)


def render_mastr_location_input(
    unique_locations: List[str],
    *,
    label: str = "Stadt",
    key: Optional[str] = None,
    default: str = "Essen",
    mastr_db_path: Optional[str] = None,
    online_banner: Optional[bool] = None,
) -> Optional[str]:
    """Render the location selector, adapting to whichever data tier is available.

    Shows an info banner when the local database is missing (data comes from the online
    register). Returns the selected/typed location string, or ``None`` if nothing is
    entered yet.

    ``online_banner`` overrides the banner: ``None`` (default) shows it only when no
    local DB is found; ``False`` suppresses it (e.g. when the caller renders its own
    online/local messaging); ``True`` always shows it.
    """
    show_banner = (not mastr_data_available(mastr_db_path)) if online_banner is None else online_banner
    if show_banner:
        st.info(_ONLINE_BANNER)

    if unique_locations:
        index = unique_locations.index(default) if default in unique_locations else 0
        return st.selectbox(label, options=unique_locations, index=index, key=key)

    # Tier 3: no DB and no shipped location CSV → free-text Ort or PLZ.
    text = st.text_input(
        f"{label} oder PLZ",
        key=key,
        placeholder="z. B. Aachen oder 52062",
        help="Ort (z. B. Aachen) oder fünfstellige Postleitzahl eingeben.",
    )
    return text.strip() or None
