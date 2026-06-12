"""Netzmodell-Szenario v2 — WP1–WP4.

Section 1: Network source (predefined / upload) with persistent state.
Section 2: Time range.
Section 3: DER configuration — Szenario (penetration), Gezielt (name-search), MaStR.
Section 3.5: Inline profile generation — PV, EV, HP, Storage, Basislast.
Section 4: Timeseries PF simulation + voltage band & line loading results.
"""

from __future__ import annotations

import copy
import logging
import os
import tempfile
from collections import Counter
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pandapower as pp
import pandapower.networks as pn
import streamlit as st

try:
    import osmnx as ox
    _HAS_OSMNX = True
except Exception:
    _HAS_OSMNX = False

try:
    from pandapower.plotting.plotly import simple_plotly
    _HAS_PLOTLY_NET = True
except Exception:
    _HAS_PLOTLY_NET = False

try:
    from pandapower.converter import from_cim as _pp_from_cim
    _HAS_CIM = True
except Exception:
    _HAS_CIM = False

try:
    from vpplib.environment import Environment
    from vpplib.battery_electric_vehicle import BatteryElectricVehicle
    from vpplib.heat_pump import HeatPump
    from vpplib.user_profile import UserProfile
    _HAS_VPPLIB = True
except Exception:
    _HAS_VPPLIB = False

try:
    import simbench as sb
    _HAS_SIMBENCH = True
except Exception:
    _HAS_SIMBENCH = False

import plotly.express as px
import plotly.graph_objects as go
from pandapower.control import ConstControl
from pandapower.timeseries import DFData

from src.config.paths import MASTR_DB_PATH, PV_PARAMS_DIR
from src.data_layer.environment import get_cached_environment
from src.data_layer.mastr_source import render_mastr_location_input
from src.mastr.preprocessing import (
    get_unique_solar_locations,
    get_unique_wind_locations,
    geocode_query_for_location,
    mastr_data_available,
    prepare_solar_data,
    prepare_wind_data,
)
from src.mastr.simulation import (
    aggregate_pv_time_series,
    aggregate_wind_time_series,
    build_pvsystems_from_params,
    init_windturbines_mastr,
    load_or_build_pv_params,
    prepare_pv_time_series_mastr,
    prepare_wind_time_series_mastr,
    revise_power_values,
    wind_turbine_matching,
)
from src.utils.vpplib_interface import assign_assets_to_buses
from src.utils.simbench_profiles import Simbench_multiplier, Simbench_multiplier_range, fix_simbench_dtypes
from src.ui.components.netzmittimeseries import get_normalized_pv_output
from src.utils import flex_baseload as fb


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_NETWORKS: dict[str, callable] = {
    "Einfaches Beispiel": pn.example_simple,
    "Multispannungs-Beispielnetz": pn.example_multivoltage,
    "4-Knoten-Stichleitung": pn.panda_four_load_branch,
    "CIGRE Mittelspannung": pn.create_cigre_network_mv,
    "Kerber Freileitung": pn.create_kerber_landnetz_freileitung_1,
    "Dickert LV Networks": pn.create_dickert_lv_network,
    "IEEE European LV (3-Phase)": pn.ieee_european_lv_asymmetric,
    "MV-Oberrhein": pn.mv_oberrhein,
}

if _HAS_SIMBENCH:
    def _sb(code: str):
        def _load():
            net = sb.get_simbench_net(code)
            fix_simbench_dtypes(net)
            return net
        return _load

    _NETWORKS.update({
        "SimBench LV Ländlich (15 Knoten)":        _sb("1-LV-rural1--0-sw"),
        "SimBench LV Halbstädtisch (44 Knoten)":   _sb("1-LV-semiurb4--0-sw"),
        "SimBench LV Städtisch (59 Knoten)":        _sb("1-LV-urban6--0-sw"),
        "SimBench MV Ländlich (97 Knoten)":         _sb("1-MV-rural--0-sw"),
        "SimBench MV Halbstädtisch (117 Knoten)":   _sb("1-MV-semiurb--0-sw"),
        "SimBench MV Städtisch (144 Knoten)":       _sb("1-MV-urban--0-sw"),
    })

_DER_DEFAULTS = {
    "PV":       {"kw": 10.0,  "label": "PV-Anlagen",          "pen": 30},
    "EV":       {"kw": 11.0,  "label": "Elektrofahrzeuge (EV)", "pen": 20},
    "HP":       {"kw": 7.0,   "label": "Wärmepumpen",          "pen": 15},
    "Storage":  {"kw": 5.0,   "label": "Batteriespeicher",     "pen": 10,
                 "kwh": 10.0},
}


# ---------------------------------------------------------------------------
# Helper classes
# ---------------------------------------------------------------------------

class _StreamlitLogHandler(logging.Handler):
    """Captures log records into a list for display in Streamlit."""

    def __init__(self):
        super().__init__()
        self.records: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(self.format(record))


# ---------------------------------------------------------------------------
# Helper functions — network display
# ---------------------------------------------------------------------------

def _show_network(net: pp.pandapowerNet) -> None:
    """Render summary metrics, geodata indicator, and plotly visualization."""
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Knoten", len(net.bus))
    c2.metric("Leitungen", len(net.line))
    c3.metric("Lasten", len(net.load))
    c4.metric("Transformatoren", len(net.trafo))

    has_geodata = hasattr(net, "bus_geodata") and len(net.bus_geodata) > 0
    st.session_state["nsv2_has_geodata"] = has_geodata
    if has_geodata:
        st.success("Geodaten vorhanden — MaStR-Zuweisung geografisch möglich")
    else:
        st.info("Keine Geodaten — automatisches Knotenlayout für Visualisierung")

    if _HAS_PLOTLY_NET:
        try:
            fig = simple_plotly(net, auto_open=False)
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.caption(f"Netzvisualisierung nicht verfügbar: {e}")
            st.dataframe(net.bus, use_container_width=True)
    else:
        st.dataframe(net.bus, use_container_width=True)


def _load_cim_net(uploaded_files, cgmes_version: str) -> pp.pandapowerNet:
    """Schreibt hochgeladene CIM/CGMES-Dateien (XML/RDF/ZIP) in ein Temp-Verzeichnis
    und konvertiert sie via pandapower from_cim in ein pandapower-Netz."""
    with tempfile.TemporaryDirectory() as tmpdir:
        paths = []
        for uf in uploaded_files:
            p = os.path.join(tmpdir, uf.name)
            with open(p, "wb") as fh:
                fh.write(uf.getvalue())
            paths.append(p)
        return _pp_from_cim(file_list=paths, cgmes_version=cgmes_version)


@st.cache_data
def _pandapower_xlsx_template() -> bytes:
    """Erzeugt eine vorformatierte pandapower-Excel-Vorlage zum Download.

    Enthält ein minimales Beispielnetz (Slack, 10-kV-Knoten, zwei Trafo-Schalter
    MV-/LV-seitig, Trafo 10/0,4 kV, zwei 0,4-kV-Knoten, eine Last, eine PV),
    damit alle Element-Tabellen mit korrekten Spalten und std_types vorhanden
    sind. Ein komplett leeres Netz würde diese Tabellen nicht in die Datei
    schreiben. Nutzer können das Beispiel befüllen/erweitern und wieder hochladen.
    """
    net = pp.create_empty_network()
    b_hv = pp.create_bus(net, vn_kv=10.0, name="10-kV-Knoten")
    b_lv1 = pp.create_bus(net, vn_kv=0.4, name="0,4-kV-Knoten 1")
    b_lv2 = pp.create_bus(net, vn_kv=0.4, name="0,4-kV-Knoten 2")
    pp.create_ext_grid(net, bus=b_hv, vm_pu=1.0, name="Slack")
    trafo = pp.create_transformer(
        net, hv_bus=b_hv, lv_bus=b_lv1,
        std_type="0.4 MVA 10/0.4 kV", name="Trafo 10/0,4 kV",
    )
    # Trafo-Schalter beidseitig (MV/LV) — Excel-tauglich, im Gegensatz zu Fuses
    pp.create_switch(net, bus=b_hv, element=trafo, et="t", closed=True,
                     name="Schalter MV-seitig")
    pp.create_switch(net, bus=b_lv1, element=trafo, et="t", closed=True,
                     name="Schalter LV-seitig")
    pp.create_line(
        net, from_bus=b_lv1, to_bus=b_lv2, length_km=0.1,
        std_type="NAYY 4x50 SE", name="Leitung 1",
    )
    pp.create_load(net, bus=b_lv2, p_mw=0.1, q_mvar=0.05, name="Last 1")
    pp.create_sgen(net, bus=b_lv1, p_mw=0.05, name="PV 1")

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        pp.to_excel(net, tmp_path)
        with open(tmp_path, "rb") as fh:
            return fh.read()
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Helper functions — DER placement
# ---------------------------------------------------------------------------

def _candidate_buses(net: pp.pandapowerNet) -> list[int]:
    """Return load-bus indices as DER placement candidates.

    Falls back to all non-slack buses if no load buses exist.
    """
    load_buses = net.load["bus"].unique().tolist() if len(net.load) > 0 else []
    if load_buses:
        return load_buses
    slack = set(net.ext_grid["bus"].values) if len(net.ext_grid) > 0 else set()
    return [b for b in net.bus.index.tolist() if b not in slack]


def _select_buses(
    candidates: list[int],
    n: int,
    strategy: str,
    net: pp.pandapowerNet,
) -> list[int]:
    """Select n buses from candidates by strategy.

    'Zufällig': reproducible random selection (seed=42).
    'Kritischste Knoten': buses with largest voltage deviation after a warm PF;
    falls back to random if PF fails.
    """
    n = min(n, len(candidates))
    if n == 0:
        return []

    if strategy == "Zufällig":
        rng = np.random.default_rng(42)
        return rng.choice(candidates, size=n, replace=False).tolist()

    # Worst-case: voltage deviation from warm-up PF
    try:
        pp.runpp(net, verbose=False)
        slack = set(net.ext_grid["bus"].values) if len(net.ext_grid) > 0 else set()
        deviation = (net.res_bus["vm_pu"] - 1.0).abs()
        deviation = deviation.drop(
            index=[b for b in slack if b in deviation.index], errors="ignore"
        )
        # Filter to candidates only
        deviation = deviation[deviation.index.isin(candidates)]
        return deviation.nlargest(n).index.tolist()
    except Exception:
        rng = np.random.default_rng(42)
        return rng.choice(candidates, size=n, replace=False).tolist()


def _bus_labels(net: pp.pandapowerNet) -> pd.DataFrame:
    """Return a DataFrame with a human-readable label column for each bus."""
    df = net.bus[["vn_kv"]].copy()
    if "name" in net.bus.columns:
        df["_name"] = net.bus["name"].fillna("").astype(str)
    else:
        df["_name"] = ""
    df["label"] = (
        df.index.astype(str)
        + " — "
        + df["_name"].where(df["_name"] != "", other="Bus " + df.index.astype(str))
        + " ("
        + df["vn_kv"].astype(str)
        + " kV)"
    )
    return df


# ---------------------------------------------------------------------------
# Helper functions — MaStR
# ---------------------------------------------------------------------------

@st.cache_data
def _load_mastr_locations() -> list[str]:
    try:
        solar = get_unique_solar_locations(mastr_db_path=str(MASTR_DB_PATH)) or []
        wind = get_unique_wind_locations(mastr_db_path=str(MASTR_DB_PATH)) or []
        # Empty when neither the DB nor the shipped location CSVs are available; the
        # caller then offers free-text Ort/PLZ entry (online-only tier 3).
        return sorted(set(solar) | set(wind))
    except Exception:
        return []


@st.cache_data
def _geocode(location: str) -> tuple[float, float]:
    lat, lon = ox.geocode(location)
    return float(lat), float(lon)


def _reset_der_state() -> None:
    """Remove all DER-related session state.

    Called whenever a different network is loaded (or the network is reset) so
    that no DER timeseries or MaStR selection state survive the switch — the
    freshly loaded ``net`` already carries no sgen/load/storage DER.
    """
    for key in (
        "nsv2_mastr_sgen_ts",
        "nsv2_mastr_gdf_solar",
        "nsv2_mastr_gdf_wind",
        "nsv2_mastr_city_district",
        "nsv2_mastr_list_loc",
        "nsv2_mastr_sel",
        "nsv2_mastr_plz",
        "nsv2_mastr_filter",
        "nsv2_mastr_filter_prev",
    ):
        st.session_state.pop(key, None)


def _azimuth_label(deg: float) -> str:
    """Map a pvlib azimuth (0=N, 90=E, 180=S, 270=W) to an 8-point compass label."""
    dirs = ["Nord", "Nordost", "Ost", "Südost", "Süd", "Südwest", "West", "Nordwest"]
    return dirs[int((deg % 360) / 45 + 0.5) % 8]


# ---------------------------------------------------------------------------
# DER overview expander
# ---------------------------------------------------------------------------

def _show_der_overview(net: pp.pandapowerNet) -> None:
    """Show current DER elements in a collapsible expander."""
    total = (
        len(net.sgen)
        + (len(net.load[net.load["name"].str.contains("EV|HP|Szenario|Gezielt", na=False)])
           if len(net.load) > 0 else 0)
        + (len(net.storage) if hasattr(net, "storage") else 0)
    )
    with st.expander(f"Aktuelle DER im Netz ({total} Elemente)", expanded=False):
        col_sg, col_ld, col_st = st.columns(3)

        with col_sg:
            st.caption("Einspeiser (PV / Wind)")
            if len(net.sgen) > 0:
                cols = [c for c in ["name", "bus", "p_mw", "type"] if c in net.sgen.columns]
                st.dataframe(net.sgen[cols], use_container_width=True)
            else:
                st.info("Keine Einspeiser")

        with col_ld:
            st.caption("Lasten (EV / WP)")
            if len(net.load) > 0:
                der_mask = net.load["name"].str.contains(
                    "EV|HP|Szenario|Gezielt", na=False, case=False
                )
                der_loads = net.load[der_mask]
                if len(der_loads) > 0:
                    st.dataframe(der_loads[["name", "bus", "p_mw"]], use_container_width=True)
                else:
                    st.info("Keine DER-Lasten")
            else:
                st.info("Keine DER-Lasten")

        with col_st:
            st.caption("Speicher")
            if hasattr(net, "storage") and len(net.storage) > 0:
                s_cols = [c for c in ["name", "bus", "p_mw", "max_e_mwh"]
                          if c in net.storage.columns]
                st.dataframe(net.storage[s_cols], use_container_width=True)
            else:
                st.info("Keine Speicher")


# ---------------------------------------------------------------------------
# Tab 1: Szenario (Penetration)
# ---------------------------------------------------------------------------

def _tab_szenario(net: pp.pandapowerNet) -> None:
    candidates = _candidate_buses(net)
    st.caption(
        f"{len(candidates)} Kandidatenknoten (Lastknoten) für die Verteilung gefunden."
    )
    if not candidates:
        st.warning("Keine geeigneten Knoten gefunden.")
        return

    # Per-DER configuration
    cfg: dict[str, dict] = {}
    for key, defaults in _DER_DEFAULTS.items():
        enabled = st.checkbox(defaults["label"], value=True, key=f"nsv2_sz_{key}_on")
        if enabled:
            with st.expander(f"{defaults['label']} — Einstellungen", expanded=False):
                pen = st.slider(
                    "Penetrationsrate (%)", 0, 100, defaults["pen"],
                    key=f"nsv2_sz_{key}_pen",
                )
                kw = st.number_input(
                    "Leistung pro Einheit (kW)", 0.1, 5000.0, defaults["kw"],
                    key=f"nsv2_sz_{key}_kw",
                )
                kwh = None
                if key == "Storage":
                    kwh = st.number_input(
                        "Energie pro Einheit (kWh)", 0.1, 10000.0, defaults["kwh"],
                        key=f"nsv2_sz_{key}_kwh",
                    )
                strat = st.radio(
                    "Platzierung",
                    ["Zufällig", "Kritischste Knoten (Spannungsabweichung)"],
                    key=f"nsv2_sz_{key}_strat",
                    horizontal=True,
                )
            cfg[key] = {"pen": pen, "kw": kw, "kwh": kwh, "strat": strat}

    if not cfg:
        st.info("Bitte mindestens einen DER-Typ auswählen.")
        return

    if st.button("DER zum Netz hinzufügen", type="primary", key="nsv2_sz_add"):
        summary = []
        for key, params in cfg.items():
            n = max(1, round(len(candidates) * params["pen"] / 100))
            buses = _select_buses(candidates, n, params["strat"], net)
            p_mw = params["kw"] / 1000.0

            for i, bus in enumerate(buses):
                if key == "PV":
                    pp.create_sgen(
                        net, bus=bus, p_mw=p_mw,
                        name=f"PV_Szenario_{i}", type="PV", in_service=True,
                    )
                elif key == "EV":
                    pp.create_load(net, bus=bus, p_mw=p_mw, name=f"EV_Szenario_{i}")
                elif key == "HP":
                    pp.create_load(net, bus=bus, p_mw=p_mw, name=f"HP_Szenario_{i}")
                elif key == "Storage":
                    pp.create_storage(
                        net, bus=bus, p_mw=0.0,
                        max_e_mwh=params["kwh"] / 1000.0,
                        min_p_mw=-p_mw, max_p_mw=p_mw,
                        name=f"Storage_Szenario_{i}",
                    )

            summary.append(f"{len(buses)}× {_DER_DEFAULTS[key]['label']}")

        st.session_state["nsv2_net"] = net
        st.success("Hinzugefügt: " + ", ".join(summary))


# ---------------------------------------------------------------------------
# Tab 2: Gezielt (Name-Search)
# ---------------------------------------------------------------------------

def _tab_targeted(net: pp.pandapowerNet) -> None:
    der_type = st.selectbox(
        "DER-Typ",
        ["PV", "EV", "Wärmepumpe", "Batteriespeicher"],
        key="nsv2_gz_type",
    )

    bus_df = _bus_labels(net)
    search = st.text_input("Knotenname / -index (Filter)", key="nsv2_gz_search")
    if search:
        mask = bus_df["label"].str.contains(search, case=False, na=False)
        bus_df = bus_df[mask]

    if bus_df.empty:
        st.warning("Keine Knoten gefunden — Filter anpassen.")
        return

    selected_label = st.selectbox(
        f"Zielknoten ({len(bus_df)} verfügbar)",
        bus_df["label"].tolist(),
        key="nsv2_gz_bus",
    )
    # Parse bus index from "idx — ..." label
    selected_bus = int(selected_label.split(" — ")[0].strip())

    type_key = {"PV": "PV", "EV": "EV", "Wärmepumpe": "HP", "Batteriespeicher": "Storage"}[der_type]
    default_kw = _DER_DEFAULTS[type_key]["kw"]
    kw = st.number_input("Leistung (kW)", 0.1, 5000.0, default_kw, key="nsv2_gz_kw")
    kwh = None
    if type_key == "Storage":
        kwh = st.number_input("Energie (kWh)", 0.1, 10000.0, _DER_DEFAULTS["Storage"]["kwh"],
                               key="nsv2_gz_kwh")

    if st.button("Hinzufügen", key="nsv2_gz_add"):
        p_mw = kw / 1000.0
        suffix = f"Gezielt_{selected_bus}"
        if type_key == "PV":
            pp.create_sgen(net, bus=selected_bus, p_mw=p_mw, name=f"PV_{suffix}", type="PV")
        elif type_key == "EV":
            pp.create_load(net, bus=selected_bus, p_mw=p_mw, name=f"EV_{suffix}")
        elif type_key == "HP":
            pp.create_load(net, bus=selected_bus, p_mw=p_mw, name=f"HP_{suffix}")
        elif type_key == "Storage":
            pp.create_storage(
                net, bus=selected_bus, p_mw=0.0,
                max_e_mwh=kwh / 1000.0,
                min_p_mw=-p_mw, max_p_mw=p_mw,
                name=f"Storage_{suffix}",
            )
        st.session_state["nsv2_net"] = net
        st.success(f"{der_type} ({kw:.1f} kW) an Knoten {selected_bus} hinzugefügt.")


# ---------------------------------------------------------------------------
# Tab 3: MaStR-Anlagen
# ---------------------------------------------------------------------------

def _mastr_selection_table(gdf_solar, gdf_wind):
    """Build a unified selection table for the loaded MaStR plant lists.

    Returns the display DataFrame (one row per plant) and a position-aligned
    list of ``(tech, EinheitMastrNummer)`` tuples to map selected rows back to
    the underlying gdf rows.
    """
    cols = ["Technologie", "Name", "PLZ", "Leistung (kW)", "Inbetriebnahme", "MaStR-Nr"]
    frames = []
    mapping: list[tuple[str, str]] = []
    for gdf, tech_label in ((gdf_solar, "PV"), (gdf_wind, "Wind")):
        if gdf is None or len(gdf) == 0:
            continue
        nrs = gdf["EinheitMastrNummer"].astype(str)
        sub = pd.DataFrame({
            "Technologie": tech_label,
            "Name": (gdf["NameStromerzeugungseinheit"].astype(str).values
                     if "NameStromerzeugungseinheit" in gdf.columns else ""),
            "PLZ": (gdf["Postleitzahl"].astype(str).values
                    if "Postleitzahl" in gdf.columns else ""),
            "Leistung (kW)": (pd.to_numeric(gdf["Bruttoleistung"], errors="coerce").values
                              if "Bruttoleistung" in gdf.columns else np.nan),
            "Inbetriebnahme": (gdf["Inbetriebnahmedatum"].astype(str).values
                               if "Inbetriebnahmedatum" in gdf.columns else ""),
            "MaStR-Nr": nrs.values,
        })
        frames.append(sub)
        mapping.extend((tech_label, nr) for nr in nrs.tolist())
    if not frames:
        return pd.DataFrame(columns=cols), mapping
    return pd.concat(frames, ignore_index=True)[cols], mapping


def _plz_series(gdf) -> pd.Series:
    """Clean, non-empty Postleitzahl values from a MaStR gdf (empty Series if none)."""
    if gdf is None or len(gdf) == 0 or "Postleitzahl" not in gdf.columns:
        return pd.Series(dtype=str)
    s = gdf["Postleitzahl"].astype(str).str.strip()
    return s[~s.isin(("", "nan", "None"))]


def _collect_plz(gdf_solar, gdf_wind) -> list[str]:
    """Sorted union of postal codes across the loaded PV and wind gdfs."""
    return sorted(set(_plz_series(gdf_solar)) | set(_plz_series(gdf_wind)))


def _filter_by_plz(gdf, plz_choice: str):
    """Restrict a gdf to a single Postleitzahl ('Alle PLZ' → unchanged)."""
    if (gdf is None or len(gdf) == 0 or plz_choice == "Alle PLZ"
            or "Postleitzahl" not in gdf.columns):
        return gdf
    return gdf[gdf["Postleitzahl"].astype(str).str.strip() == plz_choice]


def _mastr_overview_map(gdf_solar, gdf_wind, city_district, selected_nrs):
    """Scatter map of all loaded MaStR plants (city / PLZ scope), coloured by tech.

    Currently-selected plants (``selected_nrs`` = EinheitMastrNummer) are drawn as
    a green overlay. Centre and a faint boundary polygon come from the geocoded
    ``city_district`` when available, else the plants' mean coordinates. Returns a
    plotly Figure, or ``None`` if no usable coordinates exist.
    """
    frames = []
    for gdf, tech_label in ((gdf_solar, "PV"), (gdf_wind, "Wind")):
        if gdf is None or len(gdf) == 0:
            continue
        if "Breitengrad" not in gdf.columns or "Laengengrad" not in gdf.columns:
            continue
        frames.append(pd.DataFrame({
            "lat": pd.to_numeric(gdf["Breitengrad"], errors="coerce").values,
            "lon": pd.to_numeric(gdf["Laengengrad"], errors="coerce").values,
            "Technologie": tech_label,
            "Name": (gdf["NameStromerzeugungseinheit"].astype(str).values
                     if "NameStromerzeugungseinheit" in gdf.columns else ""),
            "Leistung (kW)": (pd.to_numeric(gdf["Bruttoleistung"], errors="coerce").values
                              if "Bruttoleistung" in gdf.columns else np.nan),
            "PLZ": (gdf["Postleitzahl"].astype(str).values
                    if "Postleitzahl" in gdf.columns else ""),
            "MaStR-Nr": gdf["EinheitMastrNummer"].astype(str).values,
        }))
    if not frames:
        return None
    pts = pd.concat(frames, ignore_index=True).dropna(subset=["lat", "lon"])
    if pts.empty:
        return None

    center = None
    if city_district is not None:
        try:
            center = {"lat": float(city_district.lat.item()),
                      "lon": float(city_district.lon.item())}
        except Exception:
            center = None
    if center is None:
        center = {"lat": float(pts["lat"].mean()), "lon": float(pts["lon"].mean())}

    fig = px.scatter_mapbox(
        pts, lat="lat", lon="lon", color="Technologie",
        hover_name="Name",
        hover_data={"Leistung (kW)": ":.1f", "PLZ": True, "MaStR-Nr": True,
                    "lat": False, "lon": False},
        color_discrete_map={"PV": "#f59e0b", "Wind": "#2563eb"},
        zoom=10, center=center, mapbox_style="open-street-map",
    )
    if city_district is not None:
        try:
            choro = px.choropleth_mapbox(
                city_district, geojson=city_district.geometry,
                locations=city_district.index, color=None, opacity=0.25,
            )
            fig.add_trace(choro.data[0])
            # keep scatter dots on top of the boundary polygon
            fig.data = (fig.data[-1],) + fig.data[:-1]
        except Exception:
            pass

    sel = pts[pts["MaStR-Nr"].isin({str(n) for n in selected_nrs})]
    if len(sel):
        fig.add_trace(go.Scattermapbox(
            lat=sel["lat"], lon=sel["lon"], mode="markers",
            marker=dict(size=15, color="#16a34a"),
            name="ausgewählt", hoverinfo="skip",
        ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.01),
    )
    return fig


def _tab_mastr(net: pp.pandapowerNet) -> None:
    if not _HAS_OSMNX:
        st.error("osmnx ist nicht installiert — MaStR-Geocoding nicht verfügbar.")
        return
    if not _HAS_VPPLIB:
        st.error("vpplib ist nicht installiert — MaStR-Simulation nicht verfügbar.")
        return

    # Datenquelle wählen: lokale MaStR-Datenbank oder Online-Abruf. Ohne lokale DB wird
    # der Schalter ausgeblendet und fest auf Online-Abruf gestellt.
    if mastr_data_available():
        use_online = st.toggle(
            "Anlagen online vom MaStR-Register abrufen",
            key="nsv2_mastr_online",
            help="Statt der lokalen MaStR-Datenbank werden die Anlagen für den gewählten "
                 "Ort live aus dem öffentlichen MaStR-Online-Register geladen "
                 "(nur Anlagen „In Betrieb“).",
        )
        if use_online:
            st.caption("🌐 Online-Abruf aktiv – Anlagen werden live aus dem öffentlichen "
                       "MaStR-Register geladen (nur Anlagen „In Betrieb“).")
    else:
        use_online = True
        st.info("Keine lokale MaStR-Datenbank gefunden – Anlagen werden online aus dem "
                "öffentlichen MaStR-Register abgerufen (nur Anlagen „In Betrieb“).")

    locations = _load_mastr_locations()
    location = render_mastr_location_input(
        locations, label="Ort", key="nsv2_mastr_loc", default="Aachen", online_banner=False
    )
    if not location:
        st.info("Bitte einen Ort oder eine PLZ eingeben.")
        return

    tech = st.multiselect(
        "Technologie",
        ["PV", "Wind"],
        default=["PV"],
        key="nsv2_mastr_tech",
    )

    time_start = st.session_state.get("nsv2_time_start")
    time_end = st.session_state.get("nsv2_time_end")
    if time_start is None or time_end is None:
        st.warning("Bitte zuerst den Zeitraum in Abschnitt 2 festlegen.")
        return

    start_dt = datetime.combine(time_start, datetime.min.time())
    end_dt = datetime.combine(time_end, datetime.max.time().replace(second=0, microsecond=0))
    start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")

    # --- Schritt 1: Anlagenliste laden (nur DB-Query, keine Simulation) -----
    list_loaded = (
        st.session_state.get("nsv2_mastr_list_loc") == location
        and (
            st.session_state.get("nsv2_mastr_gdf_solar") is not None
            or st.session_state.get("nsv2_mastr_gdf_wind") is not None
        )
    )
    load_label = "Anlagenliste neu laden" if list_loaded else "Anlagenliste laden"
    if st.button(load_label, type="primary", key="nsv2_mastr_load", disabled=not tech):
        log_handler = _StreamlitLogHandler()
        log_handler.setFormatter(
            logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S")
        )
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)
        try:
            with st.status("MaStR-Anlagenliste wird geladen…", expanded=True) as status:
                city_district = None
                if "PV" in tech:
                    st.write(f"MaStR-Solardaten laden ({location})…")
                    try:
                        gdf_solar, city_district = prepare_solar_data(
                            location, str(MASTR_DB_PATH), force_online=use_online
                        )
                        gdf_solar = revise_power_values(gdf_solar)
                        st.session_state["nsv2_mastr_gdf_solar"] = gdf_solar
                        st.write(f"  → {len(gdf_solar)} PV-Anlagen gefunden.")
                    except Exception as e:
                        st.warning(f"PV-Daten konnten nicht geladen werden: {e}")
                        st.session_state.pop("nsv2_mastr_gdf_solar", None)
                else:
                    st.session_state.pop("nsv2_mastr_gdf_solar", None)

                if "Wind" in tech:
                    st.write(f"MaStR-Winddaten laden ({location})…")
                    try:
                        gdf_wind, cd_wind = prepare_wind_data(
                            location, str(MASTR_DB_PATH), force_online=use_online
                        )
                        if city_district is None:
                            city_district = cd_wind
                        st.session_state["nsv2_mastr_gdf_wind"] = gdf_wind
                        st.write(f"  → {len(gdf_wind)} Windkraftanlagen gefunden.")
                    except Exception as e:
                        st.warning(f"Winddaten konnten nicht geladen werden: {e}")
                        st.session_state.pop("nsv2_mastr_gdf_wind", None)
                else:
                    st.session_state.pop("nsv2_mastr_gdf_wind", None)

                st.session_state["nsv2_mastr_city_district"] = city_district
                st.session_state["nsv2_mastr_list_loc"] = location
                st.session_state.pop("nsv2_mastr_sel", None)  # stale Auswahl verwerfen
                status.update(
                    label="✅ Anlagenliste geladen", state="complete", expanded=False
                )
        finally:
            root_logger.removeHandler(log_handler)

        if log_handler.records:
            with st.expander(f"Datenkorrektur-Log ({len(log_handler.records)} Einträge)"):
                for msg in log_handler.records:
                    st.text(msg)

    if not tech:
        st.caption("Bitte mindestens eine Technologie auswählen, um die Liste zu laden.")

    # --- Schritt 2: Anlagen auswählen und Netzknoten zuweisen ---------------
    if st.session_state.get("nsv2_mastr_list_loc") != location:
        st.info("Bitte zuerst die Anlagenliste für den gewählten Ort laden.")
        return

    gdf_solar = st.session_state.get("nsv2_mastr_gdf_solar")
    gdf_wind = st.session_state.get("nsv2_mastr_gdf_wind")

    # PLZ-Filter (optional) — schränkt Tabelle und Karte auf eine Postleitzahl ein.
    plz_values = _collect_plz(gdf_solar, gdf_wind)
    plz_choice = st.selectbox(
        "Postleitzahl", ["Alle PLZ"] + plz_values, key="nsv2_mastr_plz",
    )
    gdf_solar_f = _filter_by_plz(gdf_solar, plz_choice)
    gdf_wind_f = _filter_by_plz(gdf_wind, plz_choice)

    display_df, mapping = _mastr_selection_table(gdf_solar_f, gdf_wind_f)
    if display_df.empty:
        st.info(
            "Keine Anlagen in der geladenen Liste."
            if plz_choice == "Alle PLZ"
            else f"Keine Anlagen mit PLZ {plz_choice}."
        )
        return

    total_count = len(display_df)
    search_plants = st.text_input(
        "Anlagen filtern (Name oder MaStR-Nr.)", key="nsv2_mastr_filter"
    )
    if search_plants:
        s = search_plants.strip()
        mask = (
            display_df["Name"].str.contains(s, case=False, na=False)
            | display_df["MaStR-Nr"].str.contains(s, case=False, na=False)
        )
        keep = [i for i, hit in enumerate(mask.tolist()) if hit]
        display_df = display_df.iloc[keep].reset_index(drop=True)
        mapping = [mapping[i] for i in keep]

    # Zeilenauswahl ist positionsbasiert → bei geänderter Filterung (PLZ oder
    # Namensfilter) verwerfen, damit markierte Zeilen nicht verrutschen.
    filter_key = f"{plz_choice}||{search_plants}"
    if st.session_state.get("nsv2_mastr_filter_prev") != filter_key:
        st.session_state["nsv2_mastr_filter_prev"] = filter_key
        st.session_state.pop("nsv2_mastr_sel", None)

    st.markdown(
        f"**Anlagen auswählen** (Mehrfachauswahl möglich · "
        f"{len(display_df)}/{total_count})"
    )
    if display_df.empty:
        st.caption("Keine Treffer — Filter anpassen.")
    event = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        key="nsv2_mastr_sel",
        column_config={"Leistung (kW)": st.column_config.NumberColumn(format="%.1f")},
    )
    selected_rows = list(getattr(getattr(event, "selection", None), "rows", []) or [])
    selected_nrs = [mapping[r][1] for r in selected_rows if 0 <= r < len(mapping)]

    # ── Karte: alle Anlagen im Ort / PLZ-Gebiet (Auswahl hervorgehoben) ─────
    city_district = st.session_state.get("nsv2_mastr_city_district")
    map_fig = _mastr_overview_map(gdf_solar_f, gdf_wind_f, city_district, selected_nrs)
    if map_fig is not None:
        n_total = sum(0 if g is None else len(g) for g in (gdf_solar_f, gdf_wind_f))
        scope = "Ort" if plz_choice == "Alle PLZ" else f"PLZ {plz_choice}"
        st.caption(
            f"Karte — {n_total} Anlage(n) im gewählten {scope} · "
            f"{len(selected_nrs)} ausgewählt"
        )
        st.plotly_chart(map_fig, use_container_width=True, key="nsv2_mastr_map")

    # Zielknoten wählen (Muster wie im Tab "Gezielt"; Default = erster Knoten)
    bus_df = _bus_labels(net)
    search = st.text_input("Knotenname / -index (Filter)", key="nsv2_mastr_bus_search")
    if search:
        bus_df = bus_df[bus_df["label"].str.contains(search, case=False, na=False)]
    if bus_df.empty:
        st.warning("Keine Knoten gefunden — Filter anpassen.")
        return
    selected_label = st.selectbox(
        f"Zielknoten ({len(bus_df)} verfügbar)",
        bus_df["label"].tolist(),
        key="nsv2_mastr_bus",
    )
    selected_bus = int(selected_label.split(" — ")[0].strip())

    sel_pv = [mapping[r][1] for r in selected_rows if mapping[r][0] == "PV"]
    sel_wind = [mapping[r][1] for r in selected_rows if mapping[r][0] == "Wind"]

    if st.button(
        f"Ausgewählte Anlagen hinzufügen ({len(selected_rows)})",
        type="primary",
        key="nsv2_mastr_add",
        disabled=len(selected_rows) == 0,
    ):
        log_handler = _StreamlitLogHandler()
        log_handler.setFormatter(
            logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S")
        )
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)
        added = 0
        try:
            with st.status("Ausgewählte Anlagen werden simuliert…", expanded=True) as status:
                st.write(f"Geocoding: {location}…")
                _geo_type = "solar" if "PV" in tech else "wind"
                lat, lon = _geocode(
                    geocode_query_for_location(location, _geo_type, str(MASTR_DB_PATH))
                )

                # je Anlage eine eigene Zeitreihe — vorhandene Einträge erhalten
                sgen_ts = dict(st.session_state.get("nsv2_mastr_sgen_ts", {}))

                if sel_pv:
                    st.write("DWD-Wetterdaten abrufen (PV)…")
                    pv_env = get_cached_environment(start_str, end_str, lat, lon)
                    if pv_env is None:
                        st.error("PV-Umgebung konnte nicht erstellt werden.")
                        return
                    subset = gdf_solar[
                        gdf_solar["EinheitMastrNummer"].astype(str).isin(sel_pv)
                    ]
                    st.write(f"PV-Parameter & Zeitreihen ({len(subset)} Anlagen)…")
                    params_df = load_or_build_pv_params(
                        subset, PV_PARAMS_DIR / f"params_{location.lower()}.csv"
                    )
                    pv_systems = build_pvsystems_from_params(params_df, pv_env)
                    prepare_pv_time_series_mastr(pv_systems)
                    pv_agg = aggregate_pv_time_series(pv_systems)
                    for mastr_nr, ts in pv_agg.items():
                        ts_s = ts.iloc[:, 0] if isinstance(ts, pd.DataFrame) else ts
                        peak_mw = float(ts_s.max()) / 1000.0
                        sgen_idx = pp.create_sgen(
                            net, bus=selected_bus, p_mw=max(peak_mw, 0.001),
                            name=f"PV_{mastr_nr}", type="PV", in_service=True,
                        )
                        sgen_ts[sgen_idx] = ts_s  # eigene Zeitreihe je sgen
                        added += 1

                if sel_wind:
                    st.write("DWD-Wetterdaten abrufen (Wind)…")
                    wind_env = Environment(start=start_str, end=end_str)
                    wind_env.get_dwd_wind_data(lat=lat, lon=lon)
                    subset = gdf_wind[
                        gdf_wind["EinheitMastrNummer"].astype(str).isin(sel_wind)
                    ]
                    st.write(f"Windturbinen-Matching & Zeitreihen ({len(subset)} Anlagen)…")
                    subset = wind_turbine_matching(subset)
                    wind_dict = init_windturbines_mastr(subset, wind_env)
                    prepare_wind_time_series_mastr(wind_dict)
                    for mastr_nr, wp in wind_dict.items():
                        ts = wp.timeseries
                        ts_s = ts.iloc[:, 0] if isinstance(ts, pd.DataFrame) else ts
                        peak_mw = float(ts_s.max()) / 1000.0
                        sgen_idx = pp.create_sgen(
                            net, bus=selected_bus, p_mw=max(peak_mw, 0.001),
                            name=f"Wind_{mastr_nr}", type="WKA", in_service=True,
                        )
                        sgen_ts[sgen_idx] = ts_s  # eigene Zeitreihe je sgen
                        added += 1

                st.session_state["nsv2_net"] = net
                st.session_state["nsv2_mastr_sgen_ts"] = sgen_ts
                status.update(
                    label=f"✅ {added} Anlage(n) hinzugefügt",
                    state="complete", expanded=False,
                )
        except Exception as e:
            st.error(f"Fehler beim Hinzufügen: {e}")
            return
        finally:
            root_logger.removeHandler(log_handler)

        if log_handler.records:
            with st.expander(f"Datenkorrektur-Log ({len(log_handler.records)} Einträge)"):
                for msg in log_handler.records:
                    st.text(msg)

        st.success(f"{added} Anlage(n) an Knoten {selected_bus} hinzugefügt.")


# ---------------------------------------------------------------------------
# Section 3.5: Profile Generation
# ---------------------------------------------------------------------------

def _profile_chart(
    profile: pd.Series, ylabel: str, chart_key: str
) -> None:
    """Profile preview chart with a datetime x-axis derived from Section 2's time range."""
    time_start = st.session_state.get("nsv2_time_start")
    if time_start is not None:
        x = pd.date_range(
            start=pd.Timestamp(time_start),
            periods=len(profile),
            freq="15min",
        )
    else:
        x = [i * 0.25 for i in range(len(profile))]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=profile.values, mode="lines",
                             line=dict(width=2), showlegend=False))
    fig.update_layout(
        xaxis_title="Zeit", yaxis_title=ylabel,
        height=220, margin=dict(l=0, r=0, t=10, b=0), hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True, key=chart_key)


def _normalize_ts(ts) -> pd.Series:
    """Extract a clean 96-step numeric Series from various timeseries formats."""
    if isinstance(ts, pd.DataFrame):
        ts = ts.iloc[:, 0]
    return pd.to_numeric(ts, errors="coerce").fillna(0.0).iloc[:96].reset_index(drop=True)


# Load-name pattern identifying DER (non-base) loads.
_DER_NAME_PATTERN = "EV|HP|Wärme|Szenario|Gezielt"


def _horizon_n_steps() -> int:
    """Canonical simulation horizon in 15-min steps, driven by Section 2's range."""
    ts = st.session_state.get("nsv2_time_start")
    te = st.session_state.get("nsv2_time_end", ts)
    if ts and te:
        n_days = (pd.Timestamp(te) - pd.Timestamp(ts)).days + 1
        return max(1, n_days) * 96
    return 96


def _base_load_ids(net: pp.pandapowerNet) -> list[int]:
    """Load indices treated as conventional base load (not EV/HP/scenario DER)."""
    if len(net.load) == 0:
        return []
    mask = ~net.load["name"].str.contains(_DER_NAME_PATTERN, na=False, case=False)
    return net.load[mask].index.tolist()


def _render_basislast_simbench(net, time_start, time_end, n_days) -> None:
    """SimBench normalised load-profile multipliers (relative shapes per load)."""
    st.markdown("**SimBench-Normlastprofile**")
    st.caption(
        "Automatisch aus dem SimBench-Datensatz erzeugt. "
        "Klassifizierung nach Lastname (Haushalt, Gewerbe, Industrie, Landwirtschaft)."
    )
    if time_start and time_end:
        st.caption(f"Zeitraum aus Abschnitt 2: {time_start} – {time_end} ({n_days} Tag(e))")

    if st.button("Basislastprofil erzeugen", key="nsv2_bl_gen") \
            or "nsv2_profile_base" not in st.session_state:
        if len(net.load) == 0:
            st.info("Keine Lastknoten im Netz — Basislastprofil nicht erforderlich.")
        else:
            with st.spinner(f"SimBench-Profile laden ({n_days} Tag(e))…"):
                try:
                    if time_start and time_end:
                        start_day = (
                            pd.Timestamp(time_start).date()
                            - datetime(2020, 1, 1).date()
                        ).days % 365
                        multiplier_df = Simbench_multiplier_range(
                            net, start_day_index=start_day, n_days=n_days
                        )
                    else:
                        multiplier_df = Simbench_multiplier(net, day_index=0)
                    st.session_state["nsv2_profile_base"] = multiplier_df
                    st.success(
                        f"Profile erzeugt: {len(multiplier_df.columns)} Lastknoten, "
                        f"{len(multiplier_df)} Schritte ({n_days} Tag(e))."
                    )
                except Exception as e:
                    st.error(f"SimBench-Profile konnten nicht geladen werden: {e}")

    if "nsv2_profile_base" in st.session_state:
        base_df = st.session_state["nsv2_profile_base"]
        _profile_chart(base_df.mean(axis=1), "Mittlerer Multiplikator", "nsv2_chart_bl")
        st.caption(f"Mittelwert über {len(base_df.columns)} Lastknoten")


def _select_allowed_classes(classes: list[str]) -> list[str]:
    """Grouped checkbox-table selector for the household typology classes.

    Renders one expander per working situation, each holding a data_editor with
    a checkbox column plus read-only Haushaltsgröße / Automatisierung columns
    (the latter carries the automation-level tooltip on its header). Returns the
    sorted list of selected class keys — same format the multiselect produced.
    """
    if "nsv2_flex_selected" not in st.session_state:
        st.session_state["nsv2_flex_selected"] = set(classes)
    selected = {c for c in st.session_state["nsv2_flex_selected"] if c in classes}

    c_all, c_none, _ = st.columns([1, 1, 6])
    if c_all.button("Alle", key="nsv2_flex_all"):
        st.session_state["nsv2_flex_selected"] = set(classes)
        st.session_state["nsv2_flex_ver"] = st.session_state.get("nsv2_flex_ver", 0) + 1
        st.rerun()
    if c_none.button("Keine", key="nsv2_flex_none"):
        st.session_state["nsv2_flex_selected"] = set()
        st.session_state["nsv2_flex_ver"] = st.session_state.get("nsv2_flex_ver", 0) + 1
        st.rerun()

    ver = st.session_state.get("nsv2_flex_ver", 0)
    new_selected: set[str] = set()

    for work_label, group in fb.group_classes_by_work(classes):
        with st.expander(f"{work_label} ({len(group)} Klassen)", expanded=False):
            comps = {c: fb.class_components_de(c) for c in group}
            df = pd.DataFrame(
                {
                    "Aktiv": [c in selected for c in group],
                    "Haushaltsgröße": [comps[c][1] or "?" for c in group],
                    "Automatisierung": [comps[c][2] or "?" for c in group],
                },
                index=group,
            )
            edited = st.data_editor(
                df,
                hide_index=True,
                use_container_width=True,
                key=f"nsv2_flex_tbl_{work_label}_{ver}",
                column_config={
                    "Aktiv": st.column_config.CheckboxColumn("✓"),
                    "Haushaltsgröße": st.column_config.TextColumn(disabled=True),
                    "Automatisierung": st.column_config.TextColumn(
                        disabled=True, help=fb.AUTOMATION_COLUMN_HELP_DE
                    ),
                },
            )
            new_selected.update(edited.index[edited["Aktiv"].astype(bool)].tolist())

    st.session_state["nsv2_flex_selected"] = new_selected
    st.caption(f"{len(new_selected)} von {len(classes)} Klassen ausgewählt")
    return sorted(new_selected)


def _render_basislast_flex(net, time_start, time_end, n_days) -> None:
    """Device-level household base load (EV & heat pump handled separately)."""
    st.markdown("**Flexibilitäts-Haushaltsmodell** *(gerätescharf, EV & Wärmepumpe separat)*")
    base_ids = _base_load_ids(net)
    if not base_ids:
        st.info("Keine konventionellen Basislasten im Netz.")
        return
    if time_start is None:
        st.warning("Bitte zuerst den Zeitraum in Abschnitt 2 festlegen.")
        return

    season = fb.get_season_for_date(time_start)
    st.caption(
        f"Zeitraum: {time_start} – {time_end} ({n_days} Tag(e)) · "
        f"Saison aus Datum: **{fb.season_label(season)}**"
    )
    st.caption(f"{len(base_ids)} konventionelle Basislast(en) erkannt.")

    classes = fb.available_classes(season)
    st.markdown("**Erlaubte Haushaltsklassen**")
    allowed = _select_allowed_classes(classes)
    if not allowed:
        st.warning("Bitte mindestens eine Klasse auswählen.")
        return

    mode = st.radio(
        "Zuweisung der Klassen", ["Zufällig (Seed)", "Manuell pro Last"],
        horizontal=True, key="nsv2_flex_mode",
    )
    manual: dict[int, str] | None = None
    seed = 42
    if mode == "Zufällig (Seed)":
        seed = st.number_input("Seed", min_value=0, value=42, step=1, key="nsv2_flex_seed")
    else:
        manual = {}
        with st.expander(f"Klasse je Last ({len(base_ids)})", expanded=False):
            for lid in base_ids:
                lbl = (str(net.load.at[lid, "name"])
                       if "name" in net.load.columns else f"Last {lid}")
                manual[lid] = st.selectbox(
                    f"{lid} — {lbl}", options=allowed,
                    format_func=fb.class_display_name, key=f"nsv2_flex_cls_{lid}",
                )

    alpha = fb.verschiebung_slider(key="nsv2_flex_alpha_slider", default_pct=100)
    st.session_state["nsv2_flex_alpha"] = alpha

    if st.button("Flex-Basislast erzeugen", key="nsv2_flex_gen", type="primary"):
        assignment = fb.assign_classes(base_ids, allowed, seed=int(seed), manual=manual)
        st.session_state["nsv2_flex_assignment"] = assignment
        st.session_state["nsv2_base_source"] = "flex"
        st.success(
            f"Flex-Basislast konfiguriert: {len(assignment)} Last(en), "
            f"Saison {fb.season_label(season)}."
        )

    assignment = st.session_state.get("nsv2_flex_assignment")
    if assignment:
        n_steps = _horizon_n_steps()
        nameplates = {
            lid: float(net.load.at[lid, "p_mw"]) * 1000.0
            for lid in assignment if lid in net.load.index
        }
        baselines, shifteds, counts = fb.build_load_curves(
            nameplates, assignment, time_start, n_steps
        )
        if baselines:
            agg_base = np.sum(list(baselines.values()), axis=0)
            agg_shift = np.sum(list(shifteds.values()), axis=0)
            agg_flex = fb.interpolate(agg_base, agg_shift, alpha)

            x = pd.date_range(start=pd.Timestamp(time_start), periods=n_steps, freq="15min")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=x, y=agg_base, name="Ohne Verschiebung",
                                     line=dict(color="#2563eb", width=1.5)))
            fig.add_trace(go.Scatter(
                x=x, y=agg_flex, name=f"Mit Verschiebung ({alpha*100:.0f} %)",
                line=dict(color="#16a34a", width=1.5, dash="dash")))
            fig.update_layout(
                title="Aggregierte Netz-Basislast (Haushaltsmodell)",
                xaxis_title="Zeit", yaxis_title="Leistung (kW)",
                height=300, margin=dict(l=0, r=0, t=40, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True, key="nsv2_chart_flexbl")

            table = pd.DataFrame({
                "Last": list(assignment.keys()),
                "Klasse": [fb.class_display_name(c) for c in assignment.values()],
                "Haushalte": [counts.get(lid, 0) for lid in assignment.keys()],
            })
            with st.expander("Klassen-Zuweisung je Last", expanded=False):
                st.dataframe(table, use_container_width=True, hide_index=True)


def _render_basislast_tab(net: pp.pandapowerNet) -> None:
    """Basislast tab: choose SimBench profiles or the device-level household model."""
    time_start = st.session_state.get("nsv2_time_start")
    time_end = st.session_state.get("nsv2_time_end", time_start)
    n_days = (
        (pd.Timestamp(time_end) - pd.Timestamp(time_start)).days + 1
        if time_start and time_end else 1
    )

    source_opts = ["SimBench-Normlastprofile", "Flexibilitäts-Haushaltsmodell"]
    stored = st.session_state.get("nsv2_base_source_ui", source_opts[0])
    idx = source_opts.index(stored) if stored in source_opts else 0
    source_ui = st.radio(
        "Basislast-Quelle", options=source_opts, index=idx, horizontal=True,
        key="nsv2_base_source_radio",
    )
    st.session_state["nsv2_base_source_ui"] = source_ui

    if source_ui == source_opts[0]:
        st.session_state["nsv2_base_source"] = "simbench"
        _render_basislast_simbench(net, time_start, time_end, n_days)
    else:
        st.session_state["nsv2_base_source"] = "flex"
        _render_basislast_flex(net, time_start, time_end, n_days)


def _section_profile_generation(net: pp.pandapowerNet) -> None:
    st.subheader("3.5 Profil-Generierung")
    st.caption(
        "Zeitreihenprofile (96 Schritte × 15 min = 24 h) für die konfigurierten DER. "
        "Werden in WP4 als ConstControl-Quellen verwendet."
    )

    time_start = st.session_state.get("nsv2_time_start")
    time_end   = st.session_state.get("nsv2_time_end", time_start)
    n_days = (
        (pd.Timestamp(time_end) - pd.Timestamp(time_start)).days + 1
        if time_start and time_end else 1
    )

    tab_pv, tab_ev, tab_hp, tab_st, tab_bl = st.tabs(
        ["☀️ PV", "🚗 EV / BEV", "♨️ Wärmepumpe", "🔋 Speicher", "📊 Basislast"]
    )

    # ------------------------------------------------------------------ #
    # PV                                                                   #
    # ------------------------------------------------------------------ #
    with tab_pv:
        st.markdown("**Schnellkonfiguration via DWD-Wetterdaten**")
        if not _HAS_OSMNX:
            st.warning("osmnx nicht installiert — Geocoding nicht verfügbar.")
        else:
            pv_loc = st.text_input("Ort", value="Aachen", key="nsv2_pv_loc",
                                   help="Stadtname für DWD-Wetterdaten")
            time_end = st.session_state.get("nsv2_time_end", time_start)
            if time_start and time_end:
                n_days = (pd.Timestamp(time_end) - pd.Timestamp(time_start)).days + 1
                st.caption(f"Zeitraum aus Abschnitt 2: {time_start} – {time_end} ({n_days} Tag(e))")
            else:
                st.caption("Bitte Zeitraum in Abschnitt 2 festlegen.")

            surface_azimuth = float(st.slider(
                "Ausrichtung (Azimut)", min_value=0, max_value=360, value=180, step=5,
                format="%d°", key="nsv2_pv_azimuth",
                help="Himmelsrichtung, in die die Module zeigen. "
                     "0°/360° = Nord, 90° = Ost, 180° = Süd, 270° = West.",
            ))
            st.caption(
                "🧭 0°/360° = Nord · 90° = Ost · 180° = Süd · 270° = West — "
                f"aktuell: **{surface_azimuth:.0f}° ({_azimuth_label(surface_azimuth)})**"
            )
            surface_tilt = st.number_input(
                "Neigungswinkel (°)", min_value=0.0, max_value=90.0, value=30.0,
                step=5.0, key="nsv2_pv_tilt",
                help="Modulneigung zur Horizontalen (0° = flach, 90° = senkrecht).",
            )

            if st.button("PV-Profil generieren", key="nsv2_pv_gen", disabled=time_start is None):
                with st.spinner(f"DWD-Wetterdaten abrufen und PV-Profil berechnen ({n_days} Tag(e))…"):
                    try:
                        lat, lon = _geocode(pv_loc)
                        day0_naive = pd.Timestamp(time_start).tz_localize(None)

                        # Capture station metadata from vpplib using the first day.
                        # The DWD cache should absorb this extra lookup before the
                        # per-day calls to get_normalized_pv_output().
                        preview_env = Environment(
                            start=day0_naive.strftime("%Y-%m-%d %H:%M:%S"),
                            end=(day0_naive + pd.Timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
                            use_timezone_aware_time_index=True,
                        )
                        station_meta = preview_env.get_dwd_pv_data(
                            lat=float(lat),
                            lon=float(lon),
                        )
                        if preview_env.pv_data is None or (
                            hasattr(preview_env.pv_data, "empty") and preview_env.pv_data.empty
                        ):
                            raise ValueError("Keine PV-Wetterdaten fuer den gewaehlten Standort gefunden.")

                        station_info = None
                        if station_meta is not None and hasattr(station_meta, "empty") and not station_meta.empty:
                            row = station_meta.iloc[0]
                            station_info = {
                                "name": row.get("name", "-"),
                                "station_id": row.get("station_id", "?"),
                                "distance_km": float(row.get("distance_km", row.get("distance", 0.0)) or 0.0),
                                "latitude": float(row.get("latitude", 0.0) or 0.0),
                                "longitude": float(row.get("longitude", 0.0) or 0.0),
                            }
                        st.session_state["nsv2_profile_pv_station"] = station_info

                        # One 96-step call per day, then concatenate into the full profile.
                        daily = []
                        current = pd.Timestamp(time_start)
                        end_ts = pd.Timestamp(time_end)
                        while current <= end_ts:
                            day_ts = get_normalized_pv_output(
                                lat, lon, current, current + pd.Timedelta(days=1),
                                surface_tilt=surface_tilt,
                                surface_azimuth=surface_azimuth,
                            )
                            daily.append(
                                pd.to_numeric(day_ts, errors="coerce").fillna(0.0).reset_index(drop=True)
                            )
                            current += pd.Timedelta(days=1)

                        full_profile = pd.concat(daily, ignore_index=True)
                        st.session_state["nsv2_profile_pv"] = full_profile
                        st.success(
                            f"PV-Profil erzeugt: {len(daily)} Tag(e) "
                            f"({time_start} – {time_end}) für {pv_loc}, "
                            f"Ausrichtung {surface_azimuth:.0f}° ({_azimuth_label(surface_azimuth)}), "
                            f"{surface_tilt:.0f}° Neigung."
                        )
                    except Exception as e:
                        st.error(f"PV-Profilgenerierung fehlgeschlagen: {e}")

        if "nsv2_profile_pv" in st.session_state:
            station = st.session_state.get("nsv2_profile_pv_station")
            if station:
                st.caption(
                    f"DWD-Wetterstation: **{station.get('name', '—')}** "
                    f"(ID {station.get('station_id', '?')}, "
                    f"{station.get('distance_km', 0):.1f} km Entfernung, "
                    f"{station.get('latitude', 0):.3f}°N {station.get('longitude', 0):.3f}°E)"
                )
            _profile_chart(st.session_state["nsv2_profile_pv"], "kW / kWp", "nsv2_chart_pv")

    # ------------------------------------------------------------------ #
    # EV / BEV                                                             #
    # ------------------------------------------------------------------ #
    with tab_ev:
        bev_obj = st.session_state.get("bev")
        if bev_obj is not None:
            st.success("BEV-Konfiguration erkannt — Profil kann direkt importiert werden.")
            if st.button("Profil importieren (BEV-Einstellungen)", key="nsv2_ev_import"):
                st.session_state["nsv2_profile_ev"] = _normalize_ts(bev_obj.timeseries).abs()
                st.success("EV-Profil importiert.")
            st.divider()

        if not _HAS_VPPLIB:
            st.warning("vpplib nicht installiert — EV-Schnellkonfiguration nicht verfügbar.")
        else:
            st.markdown("**Schnellkonfiguration** *(kein Wetterdatenabruf erforderlich)*")
            if time_start and time_end:
                st.caption(f"Zeitraum aus Abschnitt 2: {time_start} – {time_end} ({n_days} Tag(e))")
            c1, c2 = st.columns(2)
            bat_max  = c1.number_input("Akkukapazität max (kWh)", 5.0,  200.0, 75.0, key="nsv2_ev_batmax")
            bat_min  = c1.number_input("Akkukapazität min (kWh)", 0.0,   50.0, 15.0, key="nsv2_ev_batmin")
            bat_use  = c2.number_input("Täglicher Verbrauch (kWh)", 1.0, 150.0, 50.0, key="nsv2_ev_batuse")
            charge_p = c2.number_input("Ladeleistung (kW)", 1.0, 150.0, 11.0, key="nsv2_ev_cp")
            eff = st.slider("Ladeeffizienz", 0.80, 1.00, 0.95, 0.01, key="nsv2_ev_eff")

            if st.button("EV-Profil generieren", key="nsv2_ev_gen", disabled=time_start is None):
                with st.spinner(f"EV-Profil berechnen ({n_days} Tag(e))…"):
                    try:
                        env = Environment(
                            start=f"{time_start} 00:00:00",
                            end=f"{time_end} 23:45:00",
                            timebase=15,
                        )
                        bev = BatteryElectricVehicle(
                            unit="kW", identifier="bev_quick", environment=env,
                            battery_max=bat_max, battery_min=bat_min,
                            battery_usage=bat_use, charging_power=charge_p,
                            charge_efficiency=eff, load_degradation_begin=0.8,
                        )
                        bev.prepare_time_series()
                        ts = bev.timeseries
                        if isinstance(ts, pd.DataFrame):
                            ts = ts.iloc[:, 0]
                        st.session_state["nsv2_profile_ev"] = (
                            pd.to_numeric(ts, errors="coerce").fillna(0.0).abs().reset_index(drop=True)
                        )
                        st.success(
                            f"EV-Profil erzeugt: {len(st.session_state['nsv2_profile_ev'])} "
                            f"Schritte ({n_days} Tag(e))."
                        )
                    except Exception as e:
                        st.error(f"EV-Profilgenerierung fehlgeschlagen: {e}")

        if "nsv2_profile_ev" in st.session_state:
            _profile_chart(st.session_state["nsv2_profile_ev"], "kW", "nsv2_chart_ev")

    # ------------------------------------------------------------------ #
    # Wärmepumpe                                                           #
    # ------------------------------------------------------------------ #
    with tab_hp:
        hp_obj = st.session_state.get("hp")
        if hp_obj is not None:
            st.success("Wärmepumpen-Konfiguration erkannt — Profil kann direkt importiert werden.")
            if st.button("Profil importieren (WP-Konfigurationsseite)", key="nsv2_hp_import"):
                st.session_state["nsv2_profile_hp"] = _normalize_ts(hp_obj.timeseries).abs()
                st.success("WP-Profil importiert.")
            st.divider()

        st.markdown("**Schnellkonfiguration via DWD-Wetterdaten**")
        if not _HAS_OSMNX or not _HAS_VPPLIB:
            st.warning("osmnx und vpplib erforderlich — bitte installieren.")
        else:
            hp_loc = st.text_input("Ort", value="Aachen", key="nsv2_hp_loc",
                                   help="Stadtname für DWD-Wetterdaten")
            time_end = st.session_state.get("nsv2_time_end", time_start)
            if time_start and time_end:
                n_days = (pd.Timestamp(time_end) - pd.Timestamp(time_start)).days + 1
                st.caption(f"Zeitraum aus Abschnitt 2: {time_start} – {time_end} ({n_days} Tag(e))")
            else:
                st.caption("Bitte Zeitraum in Abschnitt 2 festlegen.")

            c1, c2, c3 = st.columns(3)
            hp_el_power   = c1.number_input("Elektrische Leistung (kW)", 1.0, 100.0, 7.0,   key="nsv2_hp_el")
            hp_th_power   = c2.number_input("Thermische Leistung (kW)",  1.0, 150.0, 18.0,  key="nsv2_hp_th")
            _hp_type_label = c3.selectbox("Typ", ["Luft", "Erde"], key="nsv2_hp_type")
            hp_type = {"Luft": "Air", "Erde": "Ground"}[_hp_type_label]
            hp_sys_temp   = c1.number_input("Systemtemperatur (°C)", 30.0, 75.0, 60.0,      key="nsv2_hp_stemp")
            yearly_demand = c2.number_input("Jährl. Wärmebedarf (kWh)", 1000.0, 50000.0, 12500.0, key="nsv2_hp_demand")
            building_type = c3.selectbox(
                "Gebäudetyp",
                ["DE_HEF33", "DE_HEF34", "DE_HMF33", "DE_HMF34", "DE_GKO34"],
                key="nsv2_hp_btype",
                help=(
                    "SigLinDe-Gebäudeklassifikation (BDEW):\n\n"
                    "**HEF** = Einfamilienhaus · **HMF** = Mehrfamilienhaus · **GKO** = Gewerbe/Kommunal\n\n"
                    "**33** = Altbau (vor WSchVO 1977, schlechte Dämmung)\n\n"
                    "**34** = Neubau/modernisiert (nach WSchVO 1984, gute Dämmung)"
                ),
            )
            t_0           = st.number_input("Heizgrenztemperatur (°C)", 0.0, 70.0, 40.0,    key="nsv2_hp_t0")

            if st.button("WP-Profil generieren (DWD)", key="nsv2_hp_gen_dwd",
                         disabled=time_start is None):
                with st.spinner(f"Referenzjahr und Simulationszeitraum abrufen ({n_days} Tag(e))…"):
                    try:
                        lat, lon = _geocode(hp_loc)
                        import datetime as _dt

                        # Step 1: full reference year to calibrate consumerfactor
                        yesterday = _dt.date.today() - _dt.timedelta(days=1)
                        ref_start = yesterday.replace(year=yesterday.year - 1)
                        ref_env = Environment(
                            timebase=15,
                            start=f"{ref_start} 00:00:00",
                            end=f"{yesterday} 23:45:00",
                            time_freq="15 min",
                            surpress_output_globally=True,
                        )
                        ref_env.get_dwd_mean_temp_hours(lat=float(lat), lon=float(lon),
                                                        min_quality_per_parameter=10)
                        ref_env.get_dwd_mean_temp_days(lat=float(lat), lon=float(lon),
                                                       min_quality_per_parameter=10)
                        ref_env.mean_temp_quarter_hours = (
                            ref_env.mean_temp_hours.resample("15 Min").interpolate()
                        )
                        ref_profile = UserProfile(
                            identifier=None,
                            latitude=float(lat),
                            longitude=float(lon),
                            thermal_energy_demand_yearly=yearly_demand,
                            mean_temp_days=ref_env.mean_temp_days,
                            mean_temp_hours=ref_env.mean_temp_hours,
                            mean_temp_quarter_hours=ref_env.mean_temp_quarter_hours,
                            building_type=building_type,
                            comfort_factor=None,
                            t_0=t_0,
                        )
                        ref_profile.get_thermal_energy_demand()

                        # Step 2: actual simulation period with calibrated consumerfactor
                        sim_env = Environment(
                            timebase=15,
                            start=f"{time_start} 00:00:00",
                            end=f"{time_end} 23:45:00",
                            time_freq="15 min",
                            surpress_output_globally=True,
                        )
                        sim_env.get_dwd_mean_temp_hours(lat=float(lat), lon=float(lon),
                                                        min_quality_per_parameter=10)
                        sim_env.get_dwd_mean_temp_days(lat=float(lat), lon=float(lon),
                                                       min_quality_per_parameter=10)
                        sim_env.mean_temp_quarter_hours = (
                            sim_env.mean_temp_hours.resample("15 Min").interpolate()
                        )
                        sim_profile = UserProfile(
                            identifier=None,
                            latitude=float(lat),
                            longitude=float(lon),
                            thermal_energy_demand_yearly=yearly_demand,
                            mean_temp_days=sim_env.mean_temp_days,
                            mean_temp_hours=sim_env.mean_temp_hours,
                            mean_temp_quarter_hours=sim_env.mean_temp_quarter_hours,
                            building_type=building_type,
                            comfort_factor=None,
                            t_0=t_0,
                            consumerfactor=ref_profile.consumerfactor,
                        )
                        sim_profile.get_thermal_energy_demand()

                        hp_vpp = HeatPump(
                            identifier="hp_quick",
                            unit="kW",
                            thermal_energy_demand=sim_profile.thermal_energy_demand,
                            environment=sim_env,
                            heat_pump_type=hp_type,
                            heat_sys_temp=hp_sys_temp,
                            el_power=hp_el_power,
                            th_power=hp_th_power,
                            ramp_up_time=1 / 15,
                            ramp_down_time=1 / 15,
                            min_runtime=1,
                            min_stop_time=2,
                        )
                        hp_vpp.get_cop()
                        hp_vpp.prepare_time_series()

                        ts = hp_vpp.timeseries
                        if isinstance(ts, pd.DataFrame):
                            ts = ts.iloc[:, 0]
                        st.session_state["nsv2_profile_hp"] = (
                            pd.to_numeric(ts, errors="coerce").fillna(0.0).reset_index(drop=True)
                        )
                        st.success(
                            f"WP-Profil erzeugt: {len(st.session_state['nsv2_profile_hp'])} "
                            f"Schritte ({n_days} Tag(e)) für {hp_loc}."
                        )
                    except Exception as e:
                        st.error(f"WP-Profilgenerierung fehlgeschlagen: {e}")
                        import traceback
                        with st.expander("Fehlerdetails"):
                            st.code(traceback.format_exc())

        st.divider()
        st.markdown("**Parametrisches Tagesganglinienprofil** *(vereinfacht, ohne Wetterdaten)*")
        st.caption("Für ein wettergetriebenes Profil bitte den Button oben verwenden.")
        c1, c2 = st.columns(2)
        hp_kw = c1.number_input("Elektrische Leistung (kW)", 1.0, 100.0, 7.0, key="nsv2_hp_kw")
        hp_season = c2.selectbox("Jahreszeit", ["Winter", "Übergang", "Sommer"], key="nsv2_hp_season")
        season_factor = {"Winter": 1.0, "Übergang": 0.55, "Sommer": 0.20}[hp_season]

        if st.button("WP-Profil generieren", key="nsv2_hp_gen"):
            x = np.arange(96)
            morning = np.exp(-0.5 * ((x - 28) / 10) ** 2)  # peak ~7:00
            evening = np.exp(-0.5 * ((x - 74) / 8)  ** 2)  # peak ~18:30
            profile = (morning + 0.8 * evening).clip(0.05, 1.0)
            profile = profile / profile.max() * hp_kw * season_factor
            st.session_state["nsv2_profile_hp"] = pd.Series(profile)
            st.success("WP-Profil (parametrisch) erzeugt.")

        if "nsv2_profile_hp" in st.session_state:
            _profile_chart(st.session_state["nsv2_profile_hp"], "kW (elektrisch)", "nsv2_chart_hp")

    # ------------------------------------------------------------------ #
    # Speicher                                                              #
    # ------------------------------------------------------------------ #
    with tab_st:
        es_obj = st.session_state.get("es")
        if es_obj is not None:
            st.success("Speicher-Konfiguration erkannt — Profil kann direkt importiert werden.")
            if st.button("Profil importieren (Speicher-Konfigurationsseite)", key="nsv2_st_import"):
                st.session_state["nsv2_profile_storage"] = _normalize_ts(es_obj.timeseries)
                st.success("Speicher-Profil importiert.")
            st.divider()

        strategy = st.radio(
            "Betriebsstrategie",
            ["PV-Überschuss speichern", "Feste Lade-/Entladezeiten"],
            key="nsv2_st_strat", horizontal=True,
        )

        if time_start and time_end:
            st.caption(f"Zeitraum aus Abschnitt 2: {time_start} – {time_end} ({n_days} Tag(e))")

        if strategy == "PV-Überschuss speichern":
            pv_profile = st.session_state.get("nsv2_profile_pv")
            if pv_profile is None:
                st.warning("Bitte zuerst ein PV-Profil im Tab '☀️ PV' generieren.")
            else:
                st.caption("Ladung bei PV-Erzeugung > Schwellwert; Entladung in den Abendstunden.")
                threshold = st.slider("Lademindest-PV (kW/kWp)", 0.05, 1.0, 0.20, 0.05,
                                      key="nsv2_st_thresh")
                max_p = st.number_input("Max. Lade-/Entladeleistung (kW)", 0.5, 100.0, 5.0,
                                        key="nsv2_st_maxp")
                if st.button("Speicher-Profil generieren", key="nsv2_st_gen_pv"):
                    n_steps = len(pv_profile)
                    storage = np.zeros(n_steps)
                    for i in range(n_steps):
                        pv_val = float(pv_profile.iloc[i])
                        step_in_day = i % 96
                        if pv_val >= threshold:
                            storage[i] = -max_p          # charging (pp: negative p_mw)
                        elif 60 <= step_in_day <= 84:    # 15:00–21:00: discharge
                            storage[i] = max_p
                    charge_e = abs(storage[storage < 0].sum())
                    disch_e  = storage[storage > 0].sum()
                    if disch_e > 0 and charge_e > 0:
                        storage[storage > 0] *= min(1.0, charge_e / disch_e)
                    st.session_state["nsv2_profile_storage"] = pd.Series(storage)
                    st.success(f"Speicher-Profil (PV-Überschuss) erzeugt: {n_steps} Schritte.")

        else:
            c1, c2 = st.columns(2)
            charge_start = c1.time_input("Ladebeginn",
                                         value=datetime(2000, 1, 1, 22, 0).time(), key="nsv2_st_cs")
            charge_end   = c1.time_input("Ladeende",
                                         value=datetime(2000, 1, 1,  6, 0).time(), key="nsv2_st_ce")
            max_p = c2.number_input("Ladeleistung (kW)",    0.5, 100.0, 5.0, key="nsv2_st_fixp")
            dis_p = c2.number_input("Entladeleistung (kW)", 0.5, 100.0, 5.0, key="nsv2_st_disp")
            if st.button("Speicher-Profil generieren", key="nsv2_st_gen_fix"):
                cs = charge_start.hour * 4 + charge_start.minute // 15
                ce = charge_end.hour   * 4 + charge_end.minute   // 15
                storage_day = np.zeros(96)
                for i in range(96):
                    in_window = (cs <= ce and cs <= i < ce) or (cs > ce and (i >= cs or i < ce))
                    storage_day[i] = -max_p if in_window else dis_p
                charge_e = abs(storage_day[storage_day < 0].sum())
                disch_steps = (storage_day > 0).sum()
                if disch_steps > 0 and charge_e > 0:
                    storage_day[storage_day > 0] *= min(1.0, charge_e / (dis_p * disch_steps))
                storage = np.tile(storage_day, n_days)
                st.session_state["nsv2_profile_storage"] = pd.Series(storage)
                st.success(f"Speicher-Profil (feste Zeiten) erzeugt: {len(storage)} Schritte.")

        if "nsv2_profile_storage" in st.session_state:
            _profile_chart(st.session_state["nsv2_profile_storage"],
                           "kW (−=Laden, +=Entladen)", "nsv2_chart_st")

    # ------------------------------------------------------------------ #
    # Basislast                                                             #
    # ------------------------------------------------------------------ #
    with tab_bl:
        _render_basislast_tab(net)


# ---------------------------------------------------------------------------
# Section 4: Simulation helpers
# ---------------------------------------------------------------------------

def _tile_to(series: pd.Series, n: int) -> np.ndarray:
    """Tile a Series to exactly n elements."""
    vals = np.asarray(series.values, dtype=float)
    reps = (n // len(vals)) + 2
    return np.tile(vals, reps)[:n]


def _build_sim_profiles(
    net: pp.pandapowerNet, n_steps: int, variant: str = "baseline"
) -> dict[str, pd.DataFrame]:
    """Build integer-indexed MW DataFrames for all DER elements.

    Columns = pandapower element indices (int), values = MW.
    Single-day (96-step) profiles are tiled to fill n_steps.
    Elements with no matching profile are omitted; pandapower uses their static p_mw.

    ``variant`` selects the flexibility scenario:
    ``"baseline"`` = no shifting; ``"flex"`` = household base load, EV and heat
    pump shifted by the configured Verschiebungsgrad (alpha). PV / storage /
    MaStR feed-in are identical in both variants.
    """
    pv_profile  = st.session_state.get("nsv2_profile_pv")
    ev_profile  = st.session_state.get("nsv2_profile_ev")
    hp_profile  = st.session_state.get("nsv2_profile_hp")
    st_profile  = st.session_state.get("nsv2_profile_storage")
    base_mult   = st.session_state.get("nsv2_profile_base")
    mastr_ts    = st.session_state.get("nsv2_mastr_sgen_ts", {})

    base_source = st.session_state.get("nsv2_base_source", "simbench")
    flex_assignment = st.session_state.get("nsv2_flex_assignment")
    alpha = float(st.session_state.get("nsv2_flex_alpha", 1.0))
    is_flex = variant == "flex"

    sgen_df    = pd.DataFrame(index=range(n_steps))
    load_df    = pd.DataFrame(index=range(n_steps))
    storage_df = pd.DataFrame(index=range(n_steps))

    # PV sgens — scenario/targeted (not already in mastr_ts)
    if pv_profile is not None and len(net.sgen) > 0:
        pv_arr = _tile_to(pv_profile, n_steps)
        pv_mask = net.sgen["name"].str.contains("PV", na=False, case=False)
        for idx in net.sgen[pv_mask].index:
            if idx not in mastr_ts:
                p_mwp = float(net.sgen.at[idx, "p_mw"])
                sgen_df[idx] = pv_arr * p_mwp  # kW/kWp → MW/MWp → MW

    # MaStR sgens — individual timeseries in kW
    for sgen_idx, ts_kw in mastr_ts.items():
        if sgen_idx in net.sgen.index:
            arr = _tile_to(pd.Series(np.asarray(ts_kw.values, dtype=float)), n_steps)
            sgen_df[sgen_idx] = arr / 1000.0

    # EV loads — shiftable within their 10 h window in the flex variant
    if ev_profile is not None and len(net.load) > 0:
        ev_arr = _tile_to(ev_profile, n_steps)
        if is_flex:
            ev_arr = fb.shift_device_profile(ev_arr, "EV", alpha)
        ev_mask = net.load["name"].str.contains("EV", na=False, case=False)
        for idx in net.load[ev_mask].index:
            load_df[idx] = ev_arr / 1000.0

    # HP loads — shiftable within their 4 h window in the flex variant
    if hp_profile is not None and len(net.load) > 0:
        hp_arr = _tile_to(hp_profile, n_steps)
        if is_flex:
            hp_arr = fb.shift_device_profile(hp_arr, "HP", alpha)
        hp_mask = net.load["name"].str.contains("HP|Wärme", na=False, case=False)
        for idx in net.load[hp_mask].index:
            load_df[idx] = hp_arr / 1000.0

    # Base loads (all loads not EV/HP/scenario DER)
    if base_source == "flex" and flex_assignment and len(net.load) > 0:
        # Device-level household model: absolute per-load curves (kW), peak-
        # calibrated to nameplate. baseline vs flex differ by the wet-appliance shift.
        start_date = st.session_state.get("nsv2_time_start")
        nameplates = {
            lid: float(net.load.at[lid, "p_mw"]) * 1000.0
            for lid in flex_assignment if lid in net.load.index
        }
        baselines, shifteds, _ = fb.build_load_curves(
            nameplates, flex_assignment, start_date, n_steps
        )
        for idx, base_curve in baselines.items():
            curve = fb.interpolate(base_curve, shifteds[idx], alpha) if is_flex else base_curve
            load_df[idx] = np.asarray(curve, dtype=float) / 1000.0
    elif base_mult is not None and len(net.load) > 0:
        der_pattern = _DER_NAME_PATTERN
        base_mask = ~net.load["name"].str.contains(der_pattern, na=False, case=False)
        for idx in net.load[base_mask].index:
            if idx in base_mult.columns:
                mult_arr = _tile_to(pd.Series(base_mult[idx].values), n_steps)
                load_df[idx] = mult_arr * float(net.load.at[idx, "p_mw"])

    # Storage
    if st_profile is not None and hasattr(net, "storage") and len(net.storage) > 0:
        st_arr = _tile_to(st_profile, n_steps)
        for idx in net.storage.index:
            storage_df[idx] = st_arr / 1000.0

    return {"sgen": sgen_df, "load": load_df, "storage": storage_df}


def _run_timeseries_pf(
    net: pp.pandapowerNet,
    n_steps: int,
    profiles: dict[str, pd.DataFrame],
    progress_bar=None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run per-timestep pandapower PF using ConstControl/DFData.

    Returns (voltage_df [n_steps × buses], loading_df [n_steps × lines]).
    Uses the manual loop rather than run_timeseries() to stay OPF-compatible.
    """
    # Clear any controllers left from previous runs
    if hasattr(net, "controller") and len(net.controller) > 0:
        net.controller.drop(net.controller.index, inplace=True)

    # One DFData + one ConstControl per element
    for element, df in [
        ("sgen",    profiles["sgen"]),
        ("load",    profiles["load"]),
        ("storage", profiles["storage"]),
    ]:
        if df.empty:
            continue
        ds = DFData(df)
        for col in df.columns:
            try:
                ConstControl(
                    net, element=element, element_index=int(col),
                    variable="p_mw", data_source=ds, profile_name=col,
                )
            except Exception:
                pass

    controllers = (
        net.controller["object"].tolist()
        if hasattr(net, "controller") and len(net.controller) > 0
        else []
    )

    voltage_rows: list = []
    loading_rows: list = []
    update_every = max(1, n_steps // 50)

    for t in range(n_steps):
        for ctrl in controllers:
            try:
                ctrl.time_step(net, t)
                ctrl.control_step(net, t)
            except Exception:
                pass

        try:
            pp.runpp(net, verbose=False)
            voltage_rows.append(net.res_bus["vm_pu"].values.copy())
            if len(net.res_line) > 0:
                loading_rows.append(net.res_line["loading_percent"].values.copy())
        except Exception:
            voltage_rows.append(np.full(len(net.bus), np.nan))
            if len(net.res_line) > 0:
                loading_rows.append(np.full(len(net.res_line), np.nan))

        if progress_bar is not None and t % update_every == 0:
            progress_bar.progress((t + 1) / n_steps)

    if progress_bar is not None:
        progress_bar.progress(1.0)

    voltage_df = pd.DataFrame(voltage_rows, columns=net.bus.index)
    loading_df = (
        pd.DataFrame(loading_rows, columns=net.line.index)
        if loading_rows else pd.DataFrame()
    )
    return voltage_df, loading_df


def _render_sim_results(
    voltage_df: pd.DataFrame,
    loading_df: pd.DataFrame,
    dt_index,
) -> None:
    """Render voltage band and line loading results in two tabs."""
    x_labels = [str(t) for t in dt_index]

    tab_v, tab_l = st.tabs(["⚡ Spannungsband", "📈 Leitungsauslastung"])

    # ---- Voltage ---- #
    with tab_v:
        vm_min = voltage_df.min(axis=1)
        vm_max = voltage_df.max(axis=1)
        violations = int(((vm_min < 0.95) | (vm_max > 1.05)).sum())

        c1, c2, c3 = st.columns(3)
        c1.metric("Min. Spannung", f"{vm_min.min():.4f} p.u.")
        c2.metric("Max. Spannung", f"{vm_max.max():.4f} p.u.")
        c3.metric("Zeitschritte außerhalb 0.95–1.05", violations,
                  delta="Verletzungen" if violations > 0 else "OK",
                  delta_color="inverse" if violations > 0 else "off")

        fig_v = go.Figure()
        fig_v.add_trace(go.Scatter(
            x=x_labels, y=vm_max.values, name="Max U (p.u.)",
            line=dict(color="#2563eb"), fill=None,
        ))
        fig_v.add_trace(go.Scatter(
            x=x_labels, y=vm_min.values, name="Min U (p.u.)",
            line=dict(color="#dc2626"), fill="tonexty",
            fillcolor="rgba(239,68,68,0.1)",
        ))
        fig_v.add_hline(y=1.05, line_dash="dot", line_color="gray",
                        annotation_text="1.05 p.u.")
        fig_v.add_hline(y=0.95, line_dash="dot", line_color="gray",
                        annotation_text="0.95 p.u.")
        fig_v.update_layout(
            title="Spannungsband (p.u.)", height=350,
            xaxis_title="Zeit", yaxis_title="Spannung (p.u.)",
            showlegend=True, hovermode="x unified",
        )
        st.plotly_chart(fig_v, use_container_width=True, key="nsv2_res_voltage")

    # ---- Line loading ---- #
    with tab_l:
        if loading_df.empty:
            st.info("Keine Leitungsdaten vorhanden.")
            return

        max_load = loading_df.max().max()
        warn_steps = int((loading_df > 80).any(axis=1).sum())
        over_steps = int((loading_df > 100).any(axis=1).sum())

        c1, c2, c3 = st.columns(3)
        c1.metric("Max. Leitungsauslastung", f"{max_load:.1f} %")
        c2.metric("Zeitschritte > 80 %", warn_steps)
        c3.metric("Zeitschritte > 100 % (Überlast)", over_steps,
                  delta_color="inverse" if over_steps > 0 else "off")

        heat_df = loading_df.copy()
        heat_df.columns = [str(c) for c in heat_df.columns]
        heat_df.index = x_labels[:len(heat_df)]
        fig_h = px.imshow(
            heat_df.T,
            color_continuous_scale=[[0, "#22c55e"], [0.667, "#facc15"], [1.0, "#ef4444"]],
            zmin=0, zmax=120,
            labels={"x": "Zeit", "y": "Leitung", "color": "Auslastung (%)"},
            title="Leitungsauslastung (%)",
        )
        fig_h.update_layout(height=max(250, len(loading_df.columns) * 20 + 100))
        st.plotly_chart(fig_h, use_container_width=True, key="nsv2_res_loading")

        congested = loading_df[(loading_df > 80).any(axis=1)]
        if not congested.empty:
            st.markdown(f"**Engpass-Zeitpunkte (> 80 %):** {len(congested)}")
            disp = congested.copy()
            disp.index = x_labels[:len(disp)]
            disp.columns = [str(c) for c in disp.columns]
            st.dataframe(disp.head(20).style.format("{:.1f}"), height=200)


def _render_comparison_results(vb, lb, vf, lf, dt_index, alpha) -> None:
    """Minimal first-iteration comparison: no-shift vs flex-shift scenarios."""
    x = [str(t) for t in dt_index]
    flex_label = f"Mit Verschiebung ({alpha * 100:.0f} %)"

    def _vstats(v):
        vmn, vmx = v.min(axis=1), v.max(axis=1)
        return vmn, vmx, int(((vmn < 0.95) | (vmx > 1.05)).sum())

    vb_min, vb_max, vb_viol = _vstats(vb)
    vf_min, vf_max, vf_viol = _vstats(vf)
    lb_max = lb.max(axis=1) if not lb.empty else pd.Series(dtype=float)
    lf_max = lf.max(axis=1) if not lf.empty else pd.Series(dtype=float)
    lb_over = int((lb > 100).any(axis=1).sum()) if not lb.empty else 0
    lf_over = int((lf > 100).any(axis=1).sum()) if not lf.empty else 0

    st.markdown("#### Gegenüberstellung")
    metrics = pd.DataFrame(
        {
            "Ohne Verschiebung": [
                f"{vb_min.min():.4f}", f"{vb_max.max():.4f}", vb_viol,
                f"{(lb_max.max() if len(lb_max) else float('nan')):.1f}", lb_over,
            ],
            flex_label: [
                f"{vf_min.min():.4f}", f"{vf_max.max():.4f}", vf_viol,
                f"{(lf_max.max() if len(lf_max) else float('nan')):.1f}", lf_over,
            ],
        },
        index=[
            "Min. Spannung (p.u.)", "Max. Spannung (p.u.)",
            "Schritte außerhalb 0.95–1.05", "Max. Leitungsauslastung (%)",
            "Schritte > 100 %",
        ],
    )
    st.dataframe(metrics, use_container_width=True)

    c1, c2 = st.columns(2)
    c1.metric("Δ Spannungsverletzungen", vf_viol - vb_viol, delta_color="inverse")
    if len(lb_max) and len(lf_max):
        c2.metric("Δ Max. Auslastung", f"{lf_max.max() - lb_max.max():.1f} %",
                  delta_color="inverse")

    tab_v, tab_l = st.tabs(["⚡ Spannungsband", "📈 Leitungsauslastung"])
    with tab_v:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=vb_max.values, name="Max U – ohne",
                                 line=dict(color="#93c5fd")))
        fig.add_trace(go.Scatter(x=x, y=vb_min.values, name="Min U – ohne",
                                 line=dict(color="#1d4ed8")))
        fig.add_trace(go.Scatter(x=x, y=vf_max.values, name="Max U – mit",
                                 line=dict(color="#86efac", dash="dash")))
        fig.add_trace(go.Scatter(x=x, y=vf_min.values, name="Min U – mit",
                                 line=dict(color="#15803d", dash="dash")))
        fig.add_hline(y=1.05, line_dash="dot", line_color="gray")
        fig.add_hline(y=0.95, line_dash="dot", line_color="gray")
        fig.update_layout(title="Spannungsband: ohne vs. mit Verschiebung", height=380,
                          xaxis_title="Zeit", yaxis_title="Spannung (p.u.)",
                          hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True, key="nsv2_cmp_voltage")
    with tab_l:
        if lb.empty and lf.empty:
            st.info("Keine Leitungsdaten vorhanden.")
        else:
            fig = go.Figure()
            if len(lb_max):
                fig.add_trace(go.Scatter(x=x, y=lb_max.values, name="Max Auslastung – ohne",
                                         line=dict(color="#1d4ed8")))
            if len(lf_max):
                fig.add_trace(go.Scatter(x=x, y=lf_max.values, name="Max Auslastung – mit",
                                         line=dict(color="#15803d", dash="dash")))
            fig.add_hline(y=100, line_dash="dot", line_color="#ef4444",
                          annotation_text="100 %")
            fig.update_layout(title="Max. Leitungsauslastung über die Zeit", height=350,
                              xaxis_title="Zeit", yaxis_title="Auslastung (%)",
                              hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True, key="nsv2_cmp_loading")
    st.caption("Erste Iteration der Vergleichsdarstellung — wird noch verfeinert.")


def _section_simulation(net: pp.pandapowerNet) -> None:
    n_steps = _horizon_n_steps()
    base_source = st.session_state.get("nsv2_base_source", "simbench")
    flex_assignment = st.session_state.get("nsv2_flex_assignment")
    alpha = float(st.session_state.get("nsv2_flex_alpha", 1.0))

    has_ev = st.session_state.get("nsv2_profile_ev") is not None
    has_hp = st.session_state.get("nsv2_profile_hp") is not None
    flex_base = base_source == "flex" and bool(flex_assignment)
    flex_available = flex_base or has_ev or has_hp

    # Profile status
    mastr_ts = st.session_state.get("nsv2_mastr_sgen_ts", {})
    pv_profile_set = st.session_state.get("nsv2_profile_pv") is not None
    profiles_info = {
        "EV":         ("nsv2_profile_ev",      "kW"),
        "Wärmepumpe": ("nsv2_profile_hp",      "kW"),
        "Speicher":   ("nsv2_profile_storage", "kW"),
    }
    with st.expander("Profil-Status", expanded=True):
        # Einspeiser (PV/Wind): MaStR-Anlagen bringen ihr Erzeugungsprofil bereits
        # beim Hinzufügen mit; synthetische PV-Anlagen brauchen das PV-Profil aus 3.5.
        if len(net.sgen) > 0:
            s_name = net.sgen["name"].astype(str)
            s_type = (net.sgen["type"].astype(str)
                      if "type" in net.sgen.columns else s_name)
            is_wind = (s_type.str.contains("WKA", case=False, na=False)
                       | s_name.str.contains("Wind", case=False, na=False))
            pv_mask = (~is_wind) & s_name.str.contains("PV", case=False, na=False)
            pv_idx = net.sgen.index[pv_mask.to_numpy()]
            wind_idx = net.sgen.index[is_wind.to_numpy()]

            if len(pv_idx) > 0:
                pv_total = len(pv_idx)
                pv_with = sum(1 for i in pv_idx if (i in mastr_ts) or pv_profile_set)
                if pv_with == pv_total:
                    st.caption(f"✅ PV: {pv_with}/{pv_total} Anlagen mit Erzeugungsprofil")
                elif pv_with == 0:
                    st.caption(
                        f"⚠️ PV: 0/{pv_total} Anlagen mit Erzeugungsprofil → bleiben "
                        f"statisch (PV-Profil in Abschnitt 3.5 erzeugen)"
                    )
                else:
                    st.caption(
                        f"⚠️ PV: {pv_with}/{pv_total} Anlagen mit Erzeugungsprofil — "
                        f"die übrigen benötigen das PV-Profil aus Abschnitt 3.5"
                    )

            if len(wind_idx) > 0:
                wind_total = len(wind_idx)
                wind_with = sum(1 for i in wind_idx if i in mastr_ts)
                icon = "✅" if wind_with == wind_total else "⚠️"
                st.caption(
                    f"{icon} Wind: {wind_with}/{wind_total} Anlagen mit Erzeugungsprofil"
                )

        for label, (key, unit) in profiles_info.items():
            val = st.session_state.get(key)
            if val is None:
                st.caption(f"⚠️ {label}: nicht gesetzt → Elemente bleiben statisch")
            else:
                steps = len(val)
                tiled = f" → wird auf {n_steps} Schritte gestreckt" if steps != n_steps else ""
                st.caption(f"✅ {label}: {steps} Schritte ({unit}){tiled}")
        if flex_base:
            st.caption(
                f"✅ Basislast: Flexibilitäts-Haushaltsmodell, "
                f"{len(flex_assignment)} Last(en) (gerätescharf verschiebbar)"
            )
        elif base_source == "simbench" and st.session_state.get("nsv2_profile_base") is not None:
            bdf = st.session_state["nsv2_profile_base"]
            st.caption(f"✅ Basislast: SimBench-Normlastprofile, {len(bdf.columns)} Lastknoten")
        else:
            st.caption("⚠️ Basislast: nicht gesetzt → Lasten bleiben statisch")

    time_start = st.session_state.get("nsv2_time_start")
    dt_index = (
        pd.date_range(str(time_start), periods=n_steps, freq="15min")
        if time_start else pd.RangeIndex(n_steps)
    )
    st.caption(
        f"Simulationsschritte: {n_steps} ({n_steps * 0.25:.0f} Stunden, 15-min-Raster)"
    )

    if flex_available:
        st.info(
            f"Flexibilität aktiv → Vergleich **ohne** vs. **mit Verschiebung** "
            f"(Verschiebungsgrad {alpha * 100:.0f} %). Es werden zwei Läufe gerechnet."
        )
        if st.button("Zeitreihensimulation starten (Vergleich)", type="primary",
                     key="nsv2_sim_run"):
            results: dict[str, tuple] = {}
            progress_bar = st.progress(0)
            with st.spinner("Simulation läuft (2 Szenarien)…"):
                for variant in ("baseline", "flex"):
                    net_copy = copy.deepcopy(net)
                    profiles = _build_sim_profiles(net_copy, n_steps, variant=variant)
                    v_df, l_df = _run_timeseries_pf(net_copy, n_steps, profiles, progress_bar)
                    v_df.index = dt_index
                    if not l_df.empty:
                        l_df.index = dt_index[: len(l_df)]
                    results[variant] = (v_df, l_df)
            st.session_state.update({
                "nsv2_cmp_voltage_base": results["baseline"][0],
                "nsv2_cmp_loading_base": results["baseline"][1],
                "nsv2_cmp_voltage_flex": results["flex"][0],
                "nsv2_cmp_loading_flex": results["flex"][1],
                "nsv2_cmp_dt_index": dt_index,
                "nsv2_cmp_alpha": alpha,
            })
            st.session_state.pop("nsv2_results_voltage", None)
            st.success(f"Vergleich abgeschlossen ({n_steps} Schritte × 2 Szenarien).")

        if "nsv2_cmp_voltage_base" in st.session_state:
            _render_comparison_results(
                st.session_state["nsv2_cmp_voltage_base"],
                st.session_state["nsv2_cmp_loading_base"],
                st.session_state["nsv2_cmp_voltage_flex"],
                st.session_state["nsv2_cmp_loading_flex"],
                st.session_state.get("nsv2_cmp_dt_index", dt_index),
                st.session_state.get("nsv2_cmp_alpha", alpha),
            )
    else:
        if st.button("Zeitreihensimulation starten", type="primary", key="nsv2_sim_run"):
            net_copy = copy.deepcopy(net)
            profiles = _build_sim_profiles(net_copy, n_steps)
            progress_bar = st.progress(0)
            with st.spinner("Simulation läuft…"):
                voltage_df, loading_df = _run_timeseries_pf(
                    net_copy, n_steps, profiles, progress_bar
                )
            voltage_df.index = dt_index
            if not loading_df.empty:
                loading_df.index = dt_index[: len(loading_df)]
            st.session_state.update({
                "nsv2_results_voltage": voltage_df,
                "nsv2_results_loading": loading_df,
                "nsv2_results_dt_index": dt_index,
            })
            st.session_state.pop("nsv2_cmp_voltage_base", None)
            st.success(f"Simulation abgeschlossen ({n_steps} Schritte).")

        if "nsv2_results_voltage" in st.session_state:
            _render_sim_results(
                st.session_state["nsv2_results_voltage"],
                st.session_state["nsv2_results_loading"],
                st.session_state.get("nsv2_results_dt_index", pd.RangeIndex(n_steps)),
            )


# ---------------------------------------------------------------------------
# Main page function
# ---------------------------------------------------------------------------

def netzmodell():
    st.title("Netzmodell-Szenario")
    from src.content.page_descriptions import render_page_description
    render_page_description("netzmodell")
    st.caption("Entwicklungsversion — WP1–WP4")

    # ------------------------------------------------------------------ #
    # Section 1: Netzauswahl                                               #
    # ------------------------------------------------------------------ #
    st.subheader("1. Netzauswahl")

    # Use index= driven from explicit session state rather than key=.
    # Streamlit deletes widget state (key=) when navigating away from a page,
    # which would reset the radio/selectbox and trigger a spurious network reload.
    # Explicit session state (set via st.session_state[...] = ...) survives navigation.
    _source_opts = ["Vordefiniertes Netz", "Netz hochladen"]
    _stored_source = st.session_state.get("nsv2_net_source_ui", _source_opts[0])
    _source_idx = _source_opts.index(_stored_source) if _stored_source in _source_opts else 0
    source = st.radio("Netzquelle", options=_source_opts, index=_source_idx, horizontal=True)
    st.session_state["nsv2_net_source_ui"] = source

    net: pp.pandapowerNet | None = None

    if source == "Vordefiniertes Netz":
        _net_opts = list(_NETWORKS.keys())
        _stored_name = st.session_state.get("nsv2_net_name", _net_opts[2])
        _name_idx = _net_opts.index(_stored_name) if _stored_name in _net_opts else 0
        net_name = st.selectbox("Netz auswählen", options=_net_opts, index=_name_idx)

        _needs_load = (
            "nsv2_net" not in st.session_state
            or st.session_state.get("nsv2_net_source") != "predefined"
        )
        _selection_changed = net_name != st.session_state.get("nsv2_net_name")

        if _needs_load:
            try:
                net = _NETWORKS[net_name]()
                st.session_state.update({
                    "nsv2_net": net,
                    "nsv2_net_name": net_name,
                    "nsv2_net_source": "predefined",
                })
                _reset_der_state()
            except Exception as e:
                st.error(f"Netz konnte nicht geladen werden: {e}")
                return
        elif _selection_changed:
            loaded = st.session_state["nsv2_net_name"]
            st.warning(
                f"Geladenes Netz: **{loaded}** (mit ggf. hinzugefügten DER). "
                f"Zu **{net_name}** wechseln?"
            )
            if st.button("Ja, Netz wechseln (DER werden verworfen)", key="nsv2_switch_btn"):
                try:
                    net = _NETWORKS[net_name]()
                    st.session_state.update({
                        "nsv2_net": net,
                        "nsv2_net_name": net_name,
                        "nsv2_net_source": "predefined",
                    })
                    _reset_der_state()
                    st.rerun()
                except Exception as e:
                    st.error(f"Netz konnte nicht geladen werden: {e}")
                    return

        net = st.session_state.get("nsv2_net")

    else:
        st.session_state["nsv2_net_source"] = "upload"

        _fmt_opts = ["pandapower (JSON/Excel)", "CIM/CGMES"]
        upload_fmt = st.radio(
            "Format", options=_fmt_opts, horizontal=True, key="nsv2_upload_fmt"
        )

        if upload_fmt == "pandapower (JSON/Excel)":
            st.download_button(
                "Excel-Vorlage herunterladen",
                data=_pandapower_xlsx_template(),
                file_name="pandapower_netz_vorlage.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help=(
                    "Vorformatierte .xlsx mit einem minimalen Beispielnetz "
                    "(Knoten, Leitung, Last, PV). Befüllen/erweitern und wieder hochladen."
                ),
                key="nsv2_xlsx_template",
            )
            uploaded = st.file_uploader(
                "Pandapower-Netz hochladen (.json oder .xlsx)",
                type=["json", "xlsx"],
                key="nsv2_file_upload",
            )

            if uploaded is None:
                if "nsv2_net" in st.session_state and st.session_state.get("nsv2_net_source") == "upload":
                    net = st.session_state["nsv2_net"]
                    st.caption(
                        f"Zuletzt geladenes Netz: {st.session_state.get('nsv2_net_name', 'Unbekannt')}"
                    )
                else:
                    st.info(
                        "Bitte eine Netzdatei hochladen "
                        "(pandapower JSON- oder Excel-Export via `pp.to_json()` / `pp.to_excel()`)."
                    )
            else:
                try:
                    if uploaded.name.endswith(".json"):
                        net = pp.from_json_string(uploaded.getvalue().decode("utf-8"))
                    else:
                        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                            tmp.write(uploaded.getvalue())
                            tmp_path = tmp.name
                        try:
                            net = pp.from_excel(tmp_path)
                        finally:
                            os.unlink(tmp_path)

                    st.session_state["nsv2_net"] = net
                    st.session_state["nsv2_net_name"] = uploaded.name
                    st.session_state["nsv2_net_source"] = "upload"
                    _reset_der_state()
                    st.success(
                        f"Netz geladen: {len(net.bus)} Knoten, {len(net.line)} Leitungen"
                    )
                except Exception as e:
                    st.error(f"Datei konnte nicht als pandapower-Netz geladen werden: {e}")
                    return

        else:  # CIM/CGMES
            if not _HAS_CIM:
                st.error(
                    "CIM/CGMES-Converter nicht verfügbar (pandapower.converter.cim fehlt)."
                )
                return

            cgmes_version = st.selectbox(
                "CGMES-Version", options=["2.4.15", "3.0"], key="nsv2_cgmes_version"
            )
            cim_files = st.file_uploader(
                "CIM/CGMES-Dateien hochladen (.xml/.rdf-Profile EQ/SSH/TP/SV oder ein .zip-Bundle)",
                type=["xml", "rdf", "zip"],
                accept_multiple_files=True,
                key="nsv2_cim_upload",
            )

            if not cim_files:
                if "nsv2_net" in st.session_state and st.session_state.get("nsv2_net_source") == "upload":
                    net = st.session_state["nsv2_net"]
                    st.caption(
                        f"Zuletzt geladenes Netz: {st.session_state.get('nsv2_net_name', 'Unbekannt')}"
                    )
                else:
                    st.info(
                        "Bitte CIM/CGMES-Profil-Dateien (EQ/SSH/TP/SV) oder ein "
                        "ZIP-Bundle hochladen."
                    )
            else:
                try:
                    with st.spinner("CIM-Netz wird konvertiert …"):
                        net = _load_cim_net(cim_files, cgmes_version)

                    st.session_state["nsv2_net"] = net
                    st.session_state["nsv2_net_name"] = ", ".join(f.name for f in cim_files)
                    st.session_state["nsv2_net_source"] = "upload"
                    _reset_der_state()
                    st.success(
                        f"CIM-Netz geladen: {len(net.bus)} Knoten, {len(net.line)} Leitungen"
                    )
                except Exception as e:
                    st.error(f"CIM/CGMES-Datei konnte nicht konvertiert werden: {e}")
                    return

    if net is not None:
        _show_network(net)
        if st.button(
            "Netz zurücksetzen",
            help="Entfernt alle DER und lädt das Netz neu.",
            key="nsv2_reset",
        ):
            st.session_state.pop("nsv2_net", None)
            st.session_state.pop("nsv2_net_name", None)
            st.session_state.pop("nsv2_net_source", None)
            _reset_der_state()
            st.rerun()

    # ------------------------------------------------------------------ #
    # Section 2: Zeitraum                                                  #
    # ------------------------------------------------------------------ #
    st.subheader("2. Zeitraum")
    st.caption("Wird in WP4 für die Zeitreihensimulation verwendet.")

    col_start, col_end = st.columns(2)
    default_end = datetime.today().date() - timedelta(days=1)
    default_start = default_end - timedelta(days=6)
    time_start = col_start.date_input("Von", value=default_start, key="nsv2_date_start")
    time_end = col_end.date_input("Bis", value=default_end, key="nsv2_date_end")
    st.session_state["nsv2_time_start"] = time_start
    st.session_state["nsv2_time_end"] = time_end

    # ------------------------------------------------------------------ #
    # Section 3: DER-Konfiguration                                         #
    # ------------------------------------------------------------------ #
    st.subheader("3. DER-Konfiguration")

    if net is None:
        st.info("Bitte zuerst ein Netz in Abschnitt 1 laden.")
    else:
        tab_sz, tab_gz, tab_ms = st.tabs(
            ["Szenario (Penetration)", "Gezielt (Namenssuche)", "MaStR-Anlagen"]
        )
        with tab_sz:
            _tab_szenario(net)
        with tab_gz:
            _tab_targeted(net)
        with tab_ms:
            _tab_mastr(net)

        _show_der_overview(net)

    # ------------------------------------------------------------------ #
    # Section 3.5: Profil-Generierung                                      #
    # ------------------------------------------------------------------ #
    if net is not None:
        _section_profile_generation(net)

    # ------------------------------------------------------------------ #
    # Section 4: Simulation & Ergebnisse                                   #
    # ------------------------------------------------------------------ #
    # Section 4: Simulation & Ergebnisse                                   #
    # ------------------------------------------------------------------ #
    st.subheader("4. Simulation & Ergebnisse")
    if net is None:
        st.info("Bitte zuerst ein Netz in Abschnitt 1 laden.")
    else:
        _section_simulation(net)


# ROADMAP: OPF (Optimale Lastflussberechnung)
# - Deprioritized; do not implement until PF pipeline is stable.
# - When implemented: offer PF | OPF->PF (fix dispatch from OPF, run PF for
#   physically consistent results). Do NOT use a silent PF fallback on OPF failure.
# - Before any OPF work: remove the 0.85-1.15 p.u. voltage limit hack and
#   the post-hoc loading normalization from the intern's netzmittimeseries.py.
