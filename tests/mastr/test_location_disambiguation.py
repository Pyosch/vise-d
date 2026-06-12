"""Regression tests for MaStR location disambiguation by Gemeindeschluessel (AGS).

Background: the bare ``Ort`` (postal town name) is not unique across Germany.
"Langenfeld" alone names three different municipalities (NRW/Mettmann,
Bayern/Neustadt a.d. Aisch, RLP/Mayen-Koblenz). The old code filtered
``WHERE Ort = 'Langenfeld'`` (mixing all of them) and geocoded the bare name
(Nominatim returned "Kleinlangenfeld", RLP). These tests pin the fix: the
location list disambiguates same-named towns, filtering keys on the unique AGS,
and the geocode query targets the precise municipality.

Uses the real MaStR database (skipped if absent). No network access — geocoding
is only asserted at the query-string level, not executed.
"""

from pathlib import Path

import pandas as pd
import pytest

from src.config.paths import MASTR_DB_PATH

pytestmark = [pytest.mark.integration, pytest.mark.slow]

# Langenfeld (Rhld.), Kreis Mettmann, NRW — the one near Köln.
NRW_AGS = "05158020"


@pytest.fixture(scope="module")
def db_path() -> str:
    if not Path(MASTR_DB_PATH).exists():
        pytest.skip("MaStR database not available")
    return str(MASTR_DB_PATH)


def _nrw_langenfeld_label(labels: list[str]) -> str:
    """Pick the disambiguated label for the NRW (Kreis Mettmann) Langenfeld."""
    cands = [l for l in labels if l.startswith("Langenfeld") and "Mettmann" in l]
    assert cands, (
        "No disambiguated NRW Langenfeld label found. Langenfeld* labels were: "
        f"{[l for l in labels if l.startswith('Langenfeld')]}"
    )
    return cands[0]


def test_langenfeld_is_disambiguated(db_path):
    from src.mastr.preprocessing import get_unique_solar_locations

    labels = get_unique_solar_locations(mastr_db_path=db_path)

    # Labels must be unique (selectbox keys).
    assert len(labels) == len(set(labels))

    langenfelds = [l for l in labels if l.startswith("Langenfeld")]
    # The three real municipalities must each get their own entry.
    assert len(langenfelds) >= 3, langenfelds

    # The ambiguous bare name must NOT be a selectable entry anymore.
    assert "Langenfeld" not in labels


def test_resolve_nrw_langenfeld_to_ags(db_path):
    from src.mastr.preprocessing import (
        _LOCATION_CACHE_DIR,
        _resolve_location,
        get_unique_solar_locations,
    )

    label = _nrw_langenfeld_label(get_unique_solar_locations(mastr_db_path=db_path))
    resolved = _resolve_location(
        label, _LOCATION_CACHE_DIR / "solar_locations.csv", "solar_extended", db_path
    )

    assert resolved["ort"] == "Langenfeld"
    assert resolved["ags"] == NRW_AGS


def test_fetch_solar_filters_to_single_municipality(db_path):
    from src.mastr.preprocessing import fetch_solar, get_unique_solar_locations

    label = _nrw_langenfeld_label(get_unique_solar_locations(mastr_db_path=db_path))
    df = fetch_solar(location=label, mastr_db_path=db_path)

    assert len(df) > 0
    # Only the NRW municipality — no Bayern/RLP bleed-through.
    assert set(df["Gemeindeschluessel"].dropna().unique()) == {NRW_AGS}

    # NRW Langenfeld sits at ~51.0–51.2°N; Bayern (49.6) / RLP (50.4) are excluded.
    lat = pd.to_numeric(df["Breitengrad"], errors="coerce").dropna()
    assert lat.between(50.9, 51.25).mean() > 0.95


def test_geocode_query_targets_correct_town(db_path):
    from src.mastr.preprocessing import (
        geocode_query_for_location,
        get_unique_solar_locations,
    )

    label = _nrw_langenfeld_label(get_unique_solar_locations(mastr_db_path=db_path))
    query = geocode_query_for_location(label, "solar", db_path)

    # Must carry the precise municipality + Bundesland, not the bare ambiguous name.
    assert query != "Langenfeld"
    assert "Langenfeld" in query
    assert "Nordrhein-Westfalen" in query
