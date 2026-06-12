"""On-demand MaStR data fetching from the public online register.

Fallback data source used when the local ~8 GB ``open-mastr.db`` SQLite file is not
available. Instead of the local database, plant data for a *single location* is fetched
live from the Marktstammdatenregister's public JSON endpoint (the one backing the
"Erweiterte Öffentliche Einheitenübersicht"). No credentials are required.

The functions here return DataFrames in the *exact same column shape* that
``preprocessing.fetch_solar`` / ``fetch_wind`` / ``fetch_storage`` produce, so the
downstream geometry and simulation code is reused unchanged.

Note: this is the public web JSON service, not part of the ``open_mastr`` package and
not a contractual API. Filter field names must match the register's German
``FilterName`` identifiers exactly — unknown filter fields are *silently ignored* by the
server (which would otherwise return the whole register), so we only ever build filters
from the validated names below and guard against runaway result counts.

Author: Pyosch
AI Assistance: Claude Code (Claude Opus 4.8)
Created: June 2026
"""

__author__ = "Pyosch"
__credits__ = ["Claude Code (Claude Opus 4.8)"]

import re
import logging
from typing import Optional

import numpy as np
import pandas as pd
import requests

log = logging.getLogger(__name__)

# Public JSON endpoint for extended public electricity-generation units.
_BASE_URL = (
    "https://www.marktstammdatenregister.de/MaStR/Einheit/EinheitJson/"
    "GetErweiterteOeffentlicheEinheitStromerzeugung"
)
_HEADERS = {
    "User-Agent": "vise-d/online-mastr-fallback (research; +https://github.com/Pyosch)",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/plain, */*",
}

# Energieträger (energy carrier) ``Value`` ids used in the ``filter`` query string.
ENERGIETRAEGER = {"solar": 2495, "wind": 2497, "storage": 2496}
# Betriebs-Status "In Betrieb" (operational). Default so simulations only see live plants.
BETRIEBSSTATUS_IN_BETRIEB = 35

_PAGE_SIZE = 5000
# Backstop against a filter that fails to bind (the register has ~9M units total). No
# single municipality comes close to this many generation units.
_MAX_SAFE_TOTAL = 250_000
_TIMEOUT = 60
_MAX_RETRIES = 3

# Solar orientation text → azimuth degrees. Same labels/values as
# ``preprocessing.fetch_solar`` (the public endpoint uses identical orientation labels).
_AUSRICHTUNG_MAPPING = {
    "Ost-West": 0, "Nord": 0, "Nord-Ost": 45, "Ost": 90, "Süd-Ost": 135,
    "Süd": 180, "Süd-West": 225, "West": 270, "Nord-West": 315,
}
# Tilt text → tilt degrees. The public endpoint bins tilt with *different* labels than the
# bulk database (DB: "< 20 Grad"/"20 - 40 Grad"/...; REST: "5 - 20 Grad"/"21 - 40 Grad"/
# "90 Grad (vertikal)"/...), so this mapping is REST-specific but resolves to the same
# degree scale used downstream. "Nachgeführt" (tracked) stays unmapped → NaN.
_NEIGUNGSWINKEL_MAPPING = {
    "5 - 20 Grad": 10, "21 - 40 Grad": 30, "41 - 60 Grad": 50,
    "61 - 89 Grad": 75, "90 Grad (vertikal)": 90,
}

# REST response field → app column name, per technology. Columns the public endpoint
# does not expose are added as NaN/None afterwards so the shape matches the SQLite path.
_SOLAR_MAP = {
    "MaStRNummer": "EinheitMastrNummer",
    "EinheitName": "NameStromerzeugungseinheit",
    "LokationMastrNr": "LokationMastrNummer",
    "Gemarkung": "Gemarkung",
    "Leistungsbegrenzung": "Leistungsbegrenzung",
    "Bruttoleistung": "Bruttoleistung",
    "Bundesland": "Bundesland",
    "Landkreis": "Landkreis",
    "Gemeinde": "Gemeinde",
    "Gemeindeschluessel": "Gemeindeschluessel",
    "Ort": "Ort",
    "Plz": "Postleitzahl",
    "Strasse": "Strasse",
    "Hausnummer": "Hausnummer",
    "Nettonennleistung": "Nettonennleistung",
    "AnzahlSolarModule": "AnzahlModule",
    "Laengengrad": "Laengengrad",
    "Breitengrad": "Breitengrad",
    "HauptausrichtungSolarModuleBezeichnung": "Hauptausrichtung",
    "HauptneigungswinkelSolarmoduleBezeichnung": "HauptausrichtungNeigungswinkel",
    "NetzbetreiberNamen": "Netzbetreiberzuordnungen",
}
# App columns that fetch_solar returns but the endpoint does not provide.
_SOLAR_MISSING = [
    "ZugeordneteWirkleistungWechselrichter", "Lage", "Land", "Nebenausrichtung",
    "NebenausrichtungNeigungswinkel", "DatumEndgueltigeStilllegung",
]

_WIND_MAP = {
    "MaStRNummer": "EinheitMastrNummer",
    "LokationMastrNr": "LokationMastrNummer",
    "WindparkName": "NameWindpark",
    "EinheitName": "NameStromerzeugungseinheit",
    "Gemarkung": "Gemarkung",
    "HerstellerWindenergieanlageBezeichnung": "Hersteller",
    "HerstellerWindenergieanlage": "HerstellerId",
    "TechnologieStromerzeugung": "Technologie",
    "Typenbezeichnung": "Typenbezeichnung",
    "RotordurchmesserWindenergieanlage": "Rotordurchmesser",
    "Bundesland": "Bundesland",
    "Landkreis": "Landkreis",
    "Gemeinde": "Gemeinde",
    "Gemeindeschluessel": "Gemeindeschluessel",
    "Ort": "Ort",
    "Plz": "Postleitzahl",
    "Bruttoleistung": "Bruttoleistung",
    "Nettonennleistung": "Nettonennleistung",
    "NabenhoeheWindenergieanlage": "Nabenhoehe",
    "Laengengrad": "Laengengrad",
    "Breitengrad": "Breitengrad",
}
_WIND_MISSING = [
    "Lage", "Land", "DatumEndgueltigeStilllegung", "AnschlussAnHoechstOderHochSpannung",
]

_STORAGE_MAP = {
    "MaStRNummer": "EinheitMastrNummer",
    "EinheitName": "NameStromerzeugungseinheit",
    "LokationMastrNr": "LokationMastrNummer",
    "SpeicherEinheitMastrNummer": "SpeMastrNummer",
    "StromspeichertechnologieBezeichnung": "Technologie",
    "Bundesland": "Bundesland",
    "Landkreis": "Landkreis",
    "Gemeinde": "Gemeinde",
    "Gemeindeschluessel": "Gemeindeschluessel",
    "Plz": "Postleitzahl",
    "Ort": "Ort",
    "Strasse": "Strasse",
    "Hausnummer": "Hausnummer",
    "Laengengrad": "Laengengrad",
    "Breitengrad": "Breitengrad",
    "BetriebsStatusName": "EinheitBetriebsstatus",
    "Bruttoleistung": "Bruttoleistung",
    "Nettonennleistung": "Nettonennleistung",
    "NutzbareSpeicherkapazitaet": "NutzbareSpeicherkapazitaet",
}
_STORAGE_MISSING = [
    "LeistungsaufnahmeBeimEinspeichern", "Meldedatum",
    "ZugeordneteWirkleistungWechselrichter",
]

# Date columns to convert from the .NET ``/Date(ms)/`` format to ISO ``YYYY-MM-DD``.
_DATE_SOURCE_COLS = {"InbetriebnahmeDatum": "Inbetriebnahmedatum"}

_PLZ_RE = re.compile(r"^\d{5}$")
_DOTNET_DATE_RE = re.compile(r"/Date\((-?\d+)")


def _dotnet_date_to_iso(value) -> Optional[str]:
    """Convert a .NET ``/Date(ms)/`` JSON timestamp to an ISO ``YYYY-MM-DD`` string."""
    if not value or not isinstance(value, str):
        return None
    m = _DOTNET_DATE_RE.search(value)
    if not m:
        return None
    try:
        return pd.to_datetime(int(m.group(1)), unit="ms", utc=True).date().isoformat()
    except (ValueError, OverflowError):
        return None


def _build_filter(energietraeger_id: int, *, ort=None, plz=None, gemeinde=None,
                  ags=None, betriebsstatus=BETRIEBSSTATUS_IN_BETRIEB) -> str:
    """Assemble the Kendo-grid ``filter`` expression from validated FilterNames only.

    Geographic narrowing precedence: Gemeindeschlüssel (AGS, exact municipality) >
    Postleitzahl > Ort. At least one geographic filter is required.
    """
    clauses = [f"Energieträger~eq~{int(energietraeger_id)}"]
    if ags:
        clauses.append(f"Gemeindeschlüssel~eq~{str(ags).strip()}")
    elif plz:
        clauses.append(f"Postleitzahl~eq~{str(plz).strip()}")
    elif ort:
        clauses.append(f"Ort~eq~{str(ort).strip()}")
    else:
        raise ValueError("A geographic filter (ags, plz or ort) is required.")
    if gemeinde and not ags:
        clauses.append(f"Gemeinde~eq~{str(gemeinde).strip()}")
    if betriebsstatus is not None:
        clauses.append(f"Betriebs-Status~eq~{int(betriebsstatus)}")
    return "~and~".join(clauses)


def query_units(energietraeger_id: int, *, ort=None, plz=None, gemeinde=None,
                ags=None, betriebsstatus=BETRIEBSSTATUS_IN_BETRIEB,
                page_size: int = _PAGE_SIZE, session: Optional[requests.Session] = None
                ) -> list:
    """Fetch all units for one technology at one location, paging through the endpoint.

    Returns the concatenated list of raw record dicts. Raises ``RuntimeError`` on
    transport/server errors or if the reported ``Total`` is implausibly large (a sign the
    filter did not bind), and ``ValueError`` if no geographic filter was supplied.
    """
    filter_expr = _build_filter(
        energietraeger_id, ort=ort, plz=plz, gemeinde=gemeinde, ags=ags,
        betriebsstatus=betriebsstatus,
    )
    owns_session = session is None
    session = session or requests.Session()
    records: list = []
    try:
        page = 1
        while True:
            params = {
                "sort": "", "page": page, "pageSize": page_size, "group": "",
                "filter": filter_expr,
            }
            payload = _get_json(session, params)
            if payload.get("Errors"):
                raise RuntimeError(f"MaStR endpoint returned error: {payload['Errors']}")
            total = payload.get("Total") or 0
            if total > _MAX_SAFE_TOTAL:
                raise RuntimeError(
                    f"MaStR query matched {total} units (> {_MAX_SAFE_TOTAL}); aborting. "
                    "The location filter likely did not bind."
                )
            rows = payload.get("Data") or []
            records.extend(rows)
            if not rows or len(records) >= total:
                break
            page += 1
        return records
    finally:
        if owns_session:
            session.close()


def _get_json(session: requests.Session, params: dict) -> dict:
    """GET the endpoint with light retries, encoding ``~`` and umlauts safely."""
    last_exc = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = session.get(
                _BASE_URL, params=params, headers=_HEADERS, timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:  # network or bad JSON
            last_exc = exc
            log.warning("MaStR request attempt %d/%d failed: %s", attempt, _MAX_RETRIES, exc)
    raise RuntimeError(f"MaStR online request failed after {_MAX_RETRIES} attempts: {last_exc}")


def _records_to_df(records: list, colmap: dict, missing: list) -> pd.DataFrame:
    """Map raw records onto the app column schema; add missing columns as NaN."""
    src = pd.DataFrame(records)
    out = pd.DataFrame(index=src.index)
    for rest_col, app_col in colmap.items():
        out[app_col] = src[rest_col] if rest_col in src.columns else np.nan
    for app_col in missing:
        out[app_col] = np.nan
    for rest_col, app_col in _DATE_SOURCE_COLS.items():
        out[app_col] = src[rest_col].map(_dotnet_date_to_iso) if rest_col in src.columns else None
    # Coordinates and power must be numeric for df_to_gdf / revise_power_values.
    for num_col in ("Laengengrad", "Breitengrad", "Bruttoleistung", "Nettonennleistung"):
        if num_col in out.columns:
            out[num_col] = pd.to_numeric(out[num_col], errors="coerce")
    return out


def _request_kwargs(resolved: dict) -> dict:
    """Translate a ``preprocessing._resolve_location`` dict into query_units filters.

    Uses the unambiguous AGS when available (tier 1/2). For tier-3 free text the resolver
    only yields a bare ``ort``; a 5-digit token is treated as a postal code.
    """
    ags = (resolved.get("ags") or "").strip()
    ort = (resolved.get("ort") or "").strip()
    gemeinde = (resolved.get("gemeinde") or "").strip()
    if ags:
        return {"ags": ags}
    if _PLZ_RE.match(ort):
        return {"plz": ort}
    return {"ort": ort, "gemeinde": gemeinde or None}


def fetch_solar_online(resolved: dict, *, betriebsstatus=BETRIEBSSTATUS_IN_BETRIEB) -> pd.DataFrame:
    """Online equivalent of ``preprocessing.fetch_solar`` (same column shape)."""
    records = query_units(ENERGIETRAEGER["solar"], betriebsstatus=betriebsstatus,
                          **_request_kwargs(resolved))
    df = _records_to_df(records, _SOLAR_MAP, _SOLAR_MISSING)
    if not df.empty:
        df["Hauptausrichtung"] = (
            df["Hauptausrichtung"].astype("string").str.strip().map(_AUSRICHTUNG_MAPPING)
        )
        df["HauptausrichtungNeigungswinkel"] = (
            df["HauptausrichtungNeigungswinkel"].astype("string").str.strip()
            .map(_NEIGUNGSWINKEL_MAPPING)
        )
    return df


def fetch_wind_online(resolved: dict, *, betriebsstatus=BETRIEBSSTATUS_IN_BETRIEB) -> pd.DataFrame:
    """Online equivalent of ``preprocessing.fetch_wind`` (same column shape)."""
    records = query_units(ENERGIETRAEGER["wind"], betriebsstatus=betriebsstatus,
                          **_request_kwargs(resolved))
    return _records_to_df(records, _WIND_MAP, _WIND_MISSING)


def fetch_storage_online(resolved: dict, *, betriebsstatus=BETRIEBSSTATUS_IN_BETRIEB) -> pd.DataFrame:
    """Online equivalent of ``preprocessing.fetch_storage`` (same column shape).

    The public endpoint exposes ``NutzbareSpeicherkapazitaet`` directly, so unlike the
    SQLite path no ``storage_units`` join is needed.
    """
    records = query_units(ENERGIETRAEGER["storage"], betriebsstatus=betriebsstatus,
                          **_request_kwargs(resolved))
    return _records_to_df(records, _STORAGE_MAP, _STORAGE_MISSING)
