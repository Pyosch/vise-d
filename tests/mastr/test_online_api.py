"""Unit tests for the online MaStR fallback (``src.mastr.online_api``).

Fully mocked — no network access. Covers the .NET date parsing, filter assembly
(including the silently-ignored-field hazard guard), pagination, the result-size
safety cap, and the per-technology REST→app column mapping.
"""

import numpy as np
import pandas as pd
import pytest

from src.mastr import online_api as oa

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- #
# .NET date parsing
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("value,expected", [
    ("/Date(1548892800000)/", "2019-01-31"),
    ("/Date(1548892800000+0100)/", "2019-01-31"),  # trailing tz offset ignored
    ("/Date(-2208988800000)/", "1900-01-01"),
    (None, None),
    ("", None),
    ("not-a-date", None),
    (12345, None),
])
def test_dotnet_date_to_iso(value, expected):
    assert oa._dotnet_date_to_iso(value) == expected


# --------------------------------------------------------------------------- #
# Filter assembly — only validated FilterNames, with correct precedence
# --------------------------------------------------------------------------- #
def test_build_filter_prefers_ags():
    f = oa._build_filter(2495, ort="Aachen", plz="52078", ags="05334002")
    assert "Gemeindeschlüssel~eq~05334002" in f
    assert "Postleitzahl" not in f and "Ort~eq~" not in f
    assert "Energieträger~eq~2495" in f
    assert "Betriebs-Status~eq~35" in f


def test_build_filter_plz_then_ort():
    assert "Postleitzahl~eq~52078" in oa._build_filter(2495, ort="Aachen", plz="52078")
    f = oa._build_filter(2497, ort="Aachen", gemeinde="Aachen")
    assert "Ort~eq~Aachen" in f and "Gemeinde~eq~Aachen" in f


def test_build_filter_requires_geo():
    with pytest.raises(ValueError):
        oa._build_filter(2495)


def test_build_filter_status_optional():
    assert "Betriebs-Status" not in oa._build_filter(2495, ort="Aachen", betriebsstatus=None)


# --------------------------------------------------------------------------- #
# resolved-dict → query_units kwargs
# --------------------------------------------------------------------------- #
def test_request_kwargs_uses_ags_when_present():
    assert oa._request_kwargs({"ags": "05334002", "ort": "Aachen"}) == {"ags": "05334002"}


def test_request_kwargs_detects_plz():
    assert oa._request_kwargs({"ags": "", "ort": "52062"}) == {"plz": "52062"}


def test_request_kwargs_bare_ort():
    assert oa._request_kwargs({"ags": "", "ort": "Aachen", "gemeinde": "Aachen"}) == {
        "ort": "Aachen", "gemeinde": "Aachen",
    }


# --------------------------------------------------------------------------- #
# Pagination + safety guards (HTTP layer mocked)
# --------------------------------------------------------------------------- #
def test_query_units_paginates(monkeypatch):
    pages = {
        1: {"Total": 3, "Data": [{"i": 1}, {"i": 2}], "Errors": None},
        2: {"Total": 3, "Data": [{"i": 3}], "Errors": None},
    }
    monkeypatch.setattr(oa, "_get_json", lambda session, params: pages[params["page"]])
    records = oa.query_units(2495, ort="Aachen", page_size=2)
    assert [r["i"] for r in records] == [1, 2, 3]


def test_query_units_aborts_on_huge_total(monkeypatch):
    monkeypatch.setattr(
        oa, "_get_json",
        lambda session, params: {"Total": oa._MAX_SAFE_TOTAL + 1, "Data": [], "Errors": None},
    )
    with pytest.raises(RuntimeError, match="did not bind"):
        oa.query_units(2495, ort="Aachen")


def test_query_units_raises_on_server_error(monkeypatch):
    monkeypatch.setattr(
        oa, "_get_json",
        lambda session, params: {"Total": 0, "Data": None, "Errors": "Die Anfrage ist Null."},
    )
    with pytest.raises(RuntimeError, match="error"):
        oa.query_units(2495, ort="Aachen")


# --------------------------------------------------------------------------- #
# Column mapping per technology
# --------------------------------------------------------------------------- #
_SOLAR_REC = {
    "MaStRNummer": "SEE001", "EinheitName": "PV Test", "LokationMastrNr": "SEL001",
    "Bruttoleistung": 180.42, "Nettonennleistung": 165.6, "AnzahlSolarModule": 582,
    "HauptausrichtungSolarModuleBezeichnung": "Süd",
    "HauptneigungswinkelSolarmoduleBezeichnung": "21 - 40 Grad",
    "Ort": "Aachen", "Plz": "52078", "Gemeindeschluessel": "05334002",
    "Laengengrad": 6.15, "Breitengrad": 50.75,
    "InbetriebnahmeDatum": "/Date(1548892800000)/",
}


def test_fetch_solar_online_maps_columns(monkeypatch):
    monkeypatch.setattr(oa, "query_units", lambda *a, **k: [_SOLAR_REC])
    df = oa.fetch_solar_online({"ags": "05334002"})
    row = df.iloc[0]
    assert row["EinheitMastrNummer"] == "SEE001"
    assert row["NameStromerzeugungseinheit"] == "PV Test"
    assert row["Postleitzahl"] == "52078"
    assert row["AnzahlModule"] == 582
    assert row["Hauptausrichtung"] == 180          # "Süd" → azimuth
    assert row["HauptausrichtungNeigungswinkel"] == 30  # REST "21 - 40 Grad" → tilt
    assert row["Inbetriebnahmedatum"] == "2019-01-31"
    # Column present but unprovided by the endpoint → NaN (revise_power_values backfills it).
    assert "ZugeordneteWirkleistungWechselrichter" in df.columns
    assert np.isnan(row["ZugeordneteWirkleistungWechselrichter"])
    assert pd.api.types.is_numeric_dtype(df["Bruttoleistung"])


def test_fetch_wind_online_maps_columns(monkeypatch):
    rec = {
        "MaStRNummer": "SEE9", "HerstellerWindenergieanlageBezeichnung": "Vestas",
        "Typenbezeichnung": "V112", "NabenhoeheWindenergieanlage": 140.0,
        "RotordurchmesserWindenergieanlage": 112.0, "Bruttoleistung": 3300.0,
        "Laengengrad": 6.16, "Breitengrad": 50.67, "InbetriebnahmeDatum": "/Date(1537315200000)/",
    }
    monkeypatch.setattr(oa, "query_units", lambda *a, **k: [rec])
    row = oa.fetch_wind_online({"ags": "05334002"}).iloc[0]
    assert row["Hersteller"] == "Vestas"
    assert row["Nabenhoehe"] == 140.0 and row["Rotordurchmesser"] == 112.0
    assert row["Inbetriebnahmedatum"] == "2018-09-19"


def test_fetch_storage_online_includes_capacity(monkeypatch):
    rec = {
        "MaStRNummer": "SEE5", "SpeicherEinheitMastrNummer": "SSE5",
        "StromspeichertechnologieBezeichnung": "Batterie",
        "NutzbareSpeicherkapazitaet": 10.0, "Bruttoleistung": 2.5,
        "Laengengrad": None, "Breitengrad": None,
    }
    monkeypatch.setattr(oa, "query_units", lambda *a, **k: [rec])
    row = oa.fetch_storage_online({"ags": "05334002"}).iloc[0]
    assert row["NutzbareSpeicherkapazitaet"] == 10.0
    assert row["SpeMastrNummer"] == "SSE5"
    assert row["Technologie"] == "Batterie"


def test_fetch_solar_online_empty_keeps_schema(monkeypatch):
    monkeypatch.setattr(oa, "query_units", lambda *a, **k: [])
    df = oa.fetch_solar_online({"ags": "05334002"})
    assert len(df) == 0
    for col in ("EinheitMastrNummer", "Bruttoleistung", "Hauptausrichtung",
                "ZugeordneteWirkleistungWechselrichter", "Inbetriebnahmedatum"):
        assert col in df.columns
