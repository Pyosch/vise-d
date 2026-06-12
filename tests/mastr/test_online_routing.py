"""Tests for DB-presence routing in ``preprocessing.prepare_*_data``.

Verifies that the prepare functions dispatch to the online register when no local
SQLite database exists and to the SQLite path when it does, and that probing the
location cache without a database never *creates* an empty ``open-mastr.db`` (which
would poison the DB-presence check the fallback relies on).
"""

import pandas as pd
import pytest

from src.mastr import preprocessing as pp
from src.mastr import online_api as oa

pytestmark = pytest.mark.unit


def _boom(*_a, **_k):
    raise AssertionError("wrong data source used")


def test_prepare_solar_routes_online_when_db_absent(monkeypatch):
    monkeypatch.setattr(pp, "mastr_data_available", lambda *_a, **_k: False)
    monkeypatch.setattr(pp, "_resolve_location", lambda *a, **k: {
        "ort": "Aachen", "ags": "05334002", "gemeinde": "Aachen",
        "bundesland": "Nordrhein-Westfalen", "landkreis": "", "geocode_query": "Aachen, NRW",
    })
    seen = {}
    online_df = pd.DataFrame(
        {"EinheitMastrNummer": ["X"], "Laengengrad": [6.1], "Breitengrad": [50.7]}
    )

    def fake_online(resolved, **_k):
        seen["resolved"] = resolved
        return online_df

    monkeypatch.setattr(oa, "fetch_solar_online", fake_online)
    monkeypatch.setattr(pp, "fetch_solar", _boom)  # DB path must not run
    monkeypatch.setattr(pp, "add_centroids", lambda gdf, q=None: gdf)
    monkeypatch.setattr(pp.ox, "geocode_to_gdf", lambda q: "CITY")

    gdf, city = pp.prepare_solar_data("Aachen", mastr_db_path="/nonexistent.db")

    assert city == "CITY"
    assert list(gdf["EinheitMastrNummer"]) == ["X"]
    assert seen["resolved"]["ags"] == "05334002"  # precise AGS handed to the online fetch


def test_prepare_wind_routes_online_when_db_absent(monkeypatch):
    monkeypatch.setattr(pp, "mastr_data_available", lambda *_a, **_k: False)
    monkeypatch.setattr(pp, "_resolve_location", lambda *a, **k: {
        "ort": "Aachen", "ags": "", "gemeinde": "", "bundesland": "",
        "landkreis": "", "geocode_query": "Aachen",
    })
    online_df = pd.DataFrame(
        {"EinheitMastrNummer": ["W"], "Laengengrad": [6.1], "Breitengrad": [50.7]}
    )
    monkeypatch.setattr(oa, "fetch_wind_online", lambda resolved, **k: online_df)
    monkeypatch.setattr(pp, "fetch_wind", _boom)
    monkeypatch.setattr(pp, "add_centroids", lambda gdf, q=None: gdf)

    class _City(dict):
        def set_index(self, *_a, **_k):
            return self

    monkeypatch.setattr(pp.ox, "geocode_to_gdf", lambda q: _City())

    gdf, _city = pp.prepare_wind_data("Aachen", mastr_db_path="/nonexistent.db")
    assert list(gdf["EinheitMastrNummer"]) == ["W"]


def test_prepare_solar_uses_db_when_present(monkeypatch):
    monkeypatch.setattr(pp, "mastr_data_available", lambda *_a, **_k: True)
    monkeypatch.setattr(pp, "_resolve_location", lambda *a, **k: {
        "ort": "Aachen", "ags": "", "gemeinde": "", "bundesland": "",
        "landkreis": "", "geocode_query": "Aachen",
    })
    monkeypatch.setattr(oa, "fetch_solar_online", _boom)  # online must not run
    db_df = pd.DataFrame({
        "EinheitMastrNummer": ["Y"], "LokationMastrNummer": ["L"],
        "Laengengrad": [6.1], "Breitengrad": [50.7],
    })
    monkeypatch.setattr(pp, "fetch_solar", lambda *a, **k: db_df.copy())
    monkeypatch.setattr(
        pp, "prepare_grid_connections_data",
        lambda *a, **k: pd.DataFrame({"LokationMastrNummer": ["L"]}),
    )
    monkeypatch.setattr(pp, "add_centroids", lambda gdf, q=None: gdf)
    monkeypatch.setattr(pp.ox, "geocode_to_gdf", lambda q: "CITY")

    gdf, _city = pp.prepare_solar_data("Aachen", mastr_db_path=str(pp.MASTR_DB_PATH))
    assert list(gdf["EinheitMastrNummer"]) == ["Y"]


def test_location_cache_does_not_create_db(tmp_path):
    """Probing the cache with no CSV and no DB must raise, not create an empty DB."""
    missing_db = tmp_path / "nope.db"
    missing_csv = tmp_path / "loc.csv"
    with pytest.raises(FileNotFoundError):
        pp._ensure_location_cache(str(missing_csv), "solar_extended", str(missing_db))
    assert not missing_db.exists()


def test_get_unique_locations_returns_empty_without_db_or_csv(tmp_path):
    """When neither DB nor CSV exists the location list is empty (UI → free text)."""
    missing_db = tmp_path / "nope.db"
    # Point the cache dir at an empty tmp dir so no shipped CSV is found.
    import src.mastr.preprocessing as _pp
    orig = _pp._LOCATION_CACHE_DIR
    _pp._LOCATION_CACHE_DIR = tmp_path
    try:
        assert _pp.get_unique_solar_locations(mastr_db_path=str(missing_db)) == []
    finally:
        _pp._LOCATION_CACHE_DIR = orig
