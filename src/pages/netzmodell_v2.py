"""Netzmodell-Szenario v2 — WP1+WP2: Network source & DER configuration.

Section 1: Network source (predefined / upload) with persistent state.
Section 2: Time range (stored for WP4 simulation pipeline).
Section 3: DER configuration — three tabs:
    - Szenario (penetration-rate placement across load buses)
    - Gezielt  (name-search, targeted single-bus placement)
    - MaStR    (real-world PV/Wind from MaStR database)
Section 4: Simulation stub (WP4).
"""

from __future__ import annotations

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
    from vpplib.environment import Environment
    from vpplib.battery_electric_vehicle import BatteryElectricVehicle
    _HAS_VPPLIB = True
except Exception:
    _HAS_VPPLIB = False

import plotly.graph_objects as go

from src.config.paths import MASTR_DB_PATH, PV_PARAMS_DIR
from src.data_layer.environment import get_cached_environment
from src.data_layer.weather_integration import fetch_weather_for_wind
from src.mastr.preprocessing import (
    get_unique_solar_locations,
    get_unique_wind_locations,
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
from src.utils.simbench_profiles import Simbench_multiplier
from src.ui.components.netzmittimeseries import get_normalized_pv_output


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
        combined = sorted(set(solar) | set(wind))
        return combined if combined else ["Aachen"]
    except Exception:
        return ["Aachen"]


@st.cache_data
def _geocode(location: str) -> tuple[float, float]:
    lat, lon = ox.geocode(location)
    return float(lat), float(lon)


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

def _tab_gezielt(net: pp.pandapowerNet) -> None:
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

def _tab_mastr(net: pp.pandapowerNet) -> None:
    if not _HAS_OSMNX:
        st.error("osmnx ist nicht installiert — MaStR-Geocoding nicht verfügbar.")
        return
    if not _HAS_VPPLIB:
        st.error("vpplib ist nicht installiert — MaStR-Simulation nicht verfügbar.")
        return
    if not MASTR_DB_PATH.exists():
        st.error(f"MaStR-Datenbank nicht gefunden: {MASTR_DB_PATH}")
        return

    locations = _load_mastr_locations()
    default_idx = locations.index("Aachen") if "Aachen" in locations else 0
    location = st.selectbox("Ort", locations, index=default_idx, key="nsv2_mastr_loc")

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

    if not tech:
        st.info("Bitte mindestens eine Technologie auswählen.")
        return

    if st.button("MaStR-Anlagen laden", type="primary", key="nsv2_mastr_load"):
        log_handler = _StreamlitLogHandler()
        log_handler.setFormatter(
            logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S")
        )
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)

        sgen_timeseries: dict[int, pd.Series] = {}
        pv_count = 0
        wind_count = 0

        try:
            with st.status("MaStR-Anlagen werden geladen…", expanded=True) as status:

                st.write(f"Geocoding: {location}…")
                try:
                    lat, lon = _geocode(location)
                except Exception as e:
                    st.error(f"Geocoding fehlgeschlagen: {e}")
                    return

                if "PV" in tech:
                    st.write("DWD-Wetterdaten abrufen (PV)…")
                    try:
                        pv_env = get_cached_environment(start_str, end_str, lat, lon)
                        if pv_env is None:
                            st.error("PV-Umgebung konnte nicht erstellt werden.")
                            return
                    except Exception as e:
                        st.error(f"Fehler beim PV-Wetterdatenabruf: {e}")
                        return

                    st.write(f"MaStR-Solardaten laden ({location})…")
                    try:
                        gdf_solar, _ = prepare_solar_data(location, str(MASTR_DB_PATH))
                        gdf_solar = revise_power_values(gdf_solar)
                        pv_count = len(gdf_solar)
                        st.write(f"  → {pv_count} PV-Anlagen gefunden.")
                    except Exception as e:
                        st.warning(f"PV-Daten konnten nicht geladen werden: {e}")
                        gdf_solar = None

                    if gdf_solar is not None and not gdf_solar.empty:
                        st.write("PV-Anlagen den Netzknoten zuweisen…")
                        pv_bus_assignments = assign_assets_to_buses(net, gdf_solar)

                        st.write("PV-Parameter laden / berechnen…")
                        params_df = load_or_build_pv_params(
                            gdf_solar, PV_PARAMS_DIR / f"params_{location.lower()}.csv"
                        )

                        st.write(f"PV-Zeitreihen simulieren ({len(params_df)} Anlagen)…")
                        pv_systems = build_pvsystems_from_params(params_df, pv_env)
                        prepare_pv_time_series_mastr(pv_systems)
                        pv_agg = aggregate_pv_time_series(pv_systems)

                        st.write("PV-Einspeiser ins Netz eintragen…")
                        for mastr_nr, ts in pv_agg.items():
                            bus_idx = pv_bus_assignments.get(mastr_nr)
                            if bus_idx is None:
                                continue
                            ts_s = ts.iloc[:, 0] if isinstance(ts, pd.DataFrame) else ts
                            peak_mw = float(ts_s.max()) / 1000.0
                            sgen_idx = pp.create_sgen(
                                net, bus=bus_idx, p_mw=max(peak_mw, 0.001),
                                name=f"PV_{mastr_nr}", type="PV", in_service=True,
                            )
                            sgen_timeseries[sgen_idx] = ts_s

                if "Wind" in tech:
                    st.write("DWD-Wetterdaten abrufen (Wind)…")
                    try:
                        wind_weather, _ = fetch_weather_for_wind(lat, lon, start_dt, end_dt)
                        wind_env = Environment(start=start_str, end=end_str)
                        wind_env.wind_data = wind_weather
                    except Exception as e:
                        st.error(f"Fehler beim Wind-Wetterdatenabruf: {e}")
                        return

                    st.write(f"MaStR-Winddaten laden ({location})…")
                    try:
                        gdf_wind, _ = prepare_wind_data(location, str(MASTR_DB_PATH))
                        wind_count = len(gdf_wind)
                        st.write(f"  → {wind_count} Windkraftanlagen gefunden.")
                    except Exception as e:
                        st.warning(f"Winddaten konnten nicht geladen werden: {e}")
                        gdf_wind = None

                    if gdf_wind is not None and not gdf_wind.empty:
                        st.write("Windturbinen-Matching und Zeitreihensimulation…")
                        gdf_wind = wind_turbine_matching(gdf_wind)
                        wind_bus_assignments = assign_assets_to_buses(net, gdf_wind)
                        wind_dict = init_windturbines_mastr(gdf_wind, wind_env)
                        prepare_wind_time_series_mastr(wind_dict)
                        wind_agg = aggregate_wind_time_series(wind_dict)

                        if wind_bus_assignments:
                            dominant_bus = Counter(wind_bus_assignments.values()).most_common(1)[0][0]
                            wind_ts = wind_agg.iloc[:, 0] if isinstance(wind_agg, pd.DataFrame) else wind_agg
                            peak_wind_mw = float(wind_ts.max()) / 1000.0
                            wind_sgen_idx = pp.create_sgen(
                                net, bus=dominant_bus, p_mw=max(peak_wind_mw, 0.001),
                                name="Wind_aggregiert", type="WKA", in_service=True,
                            )
                            sgen_timeseries[wind_sgen_idx] = wind_ts
                            st.write("Wind-Einspeiser (aggregiert) eingetragen.")

                st.session_state["nsv2_net"] = net
                st.session_state["nsv2_mastr_sgen_ts"] = sgen_timeseries
                status.update(label="✅ MaStR-Anlagen geladen!", state="complete", expanded=False)

        finally:
            root_logger.removeHandler(log_handler)

        m1, m2 = st.columns(2)
        m1.metric("PV-Anlagen", pv_count)
        m2.metric("Windkraftanlagen", wind_count)

        if log_handler.records:
            with st.expander(f"Datenkorrektur-Log ({len(log_handler.records)} Einträge)"):
                for msg in log_handler.records:
                    st.text(msg)


# ---------------------------------------------------------------------------
# Section 3.5: Profile Generation
# ---------------------------------------------------------------------------

def _profile_chart(profile: pd.Series, ylabel: str, chart_key: str) -> None:
    """Compact 96-step profile preview."""
    time_h = [i * 0.25 for i in range(len(profile))]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=time_h, y=profile.values, mode="lines",
                             line=dict(width=2), showlegend=False))
    fig.update_layout(
        xaxis_title="Uhrzeit (h)", yaxis_title=ylabel,
        height=220, margin=dict(l=0, r=0, t=10, b=0), hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True, key=chart_key)


def _normalize_ts(ts) -> pd.Series:
    """Extract a clean 96-step numeric Series from various timeseries formats."""
    if isinstance(ts, pd.DataFrame):
        ts = ts.iloc[:, 0]
    return pd.to_numeric(ts, errors="coerce").fillna(0.0).iloc[:96].reset_index(drop=True)


def _section_profile_generation(net: pp.pandapowerNet) -> None:
    st.subheader("3.5 Profil-Generierung")
    st.caption(
        "Zeitreihenprofile (96 Schritte × 15 min = 24 h) für die konfigurierten DER. "
        "Werden in WP4 als ConstControl-Quellen verwendet."
    )

    time_start = st.session_state.get("nsv2_time_start")

    tab_pv, tab_ev, tab_hp, tab_st, tab_bl = st.tabs(
        ["☀️ PV", "🚗 EV / BEV", "♨️ Wärmepumpe", "🔋 Speicher", "📊 Basislast"]
    )

    # ------------------------------------------------------------------ #
    # PV                                                                   #
    # ------------------------------------------------------------------ #
    with tab_pv:
        pv_obj = st.session_state.get("pv")
        if pv_obj is not None:
            st.success("PV-Konfiguration erkannt — Profil kann direkt importiert werden.")
            if st.button("Profil importieren (PV-Konfiguration)", key="nsv2_pv_import"):
                ts = _normalize_ts(pv_obj.timeseries)
                peak = ts.max()
                st.session_state["nsv2_profile_pv"] = ts / peak if peak > 0 else ts
                st.success("PV-Profil importiert und auf 1 kWp normiert.")
            st.divider()

        st.markdown("**Schnellkonfiguration via DWD-Wetterdaten**")
        if not _HAS_OSMNX:
            st.warning("osmnx nicht installiert — Geocoding nicht verfügbar.")
        else:
            pv_loc = st.text_input("Ort", value="Aachen", key="nsv2_pv_loc",
                                   help="Stadtname für DWD-Wetterdaten")
            st.caption(f"Datum aus Abschnitt 2: {time_start}" if time_start
                       else "Bitte Zeitraum in Abschnitt 2 festlegen.")
            if st.button("PV-Profil generieren", key="nsv2_pv_gen", disabled=time_start is None):
                with st.spinner("DWD-Wetterdaten abrufen und PV-Profil berechnen…"):
                    try:
                        lat, lon = _geocode(pv_loc)
                        day = pd.Timestamp(time_start)
                        ts = get_normalized_pv_output(lat, lon, day, day + pd.Timedelta(days=1))
                        st.session_state["nsv2_profile_pv"] = _normalize_ts(ts)
                        st.success(f"PV-Profil erzeugt für {pv_loc} am {time_start}.")
                    except Exception as e:
                        st.error(f"PV-Profilgenerierung fehlgeschlagen: {e}")

        if "nsv2_profile_pv" in st.session_state:
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
            c1, c2 = st.columns(2)
            bat_max  = c1.number_input("Akkukapazität max (kWh)", 5.0,  200.0, 75.0, key="nsv2_ev_batmax")
            bat_min  = c1.number_input("Akkukapazität min (kWh)", 0.0,   50.0, 15.0, key="nsv2_ev_batmin")
            bat_use  = c2.number_input("Täglicher Verbrauch (kWh)", 1.0, 150.0, 50.0, key="nsv2_ev_batuse")
            charge_p = c2.number_input("Ladeleistung (kW)", 1.0, 150.0, 11.0, key="nsv2_ev_cp")
            eff = st.slider("Ladeeffizienz", 0.80, 1.00, 0.95, 0.01, key="nsv2_ev_eff")

            if st.button("EV-Profil generieren", key="nsv2_ev_gen", disabled=time_start is None):
                with st.spinner("EV-Profil berechnen…"):
                    try:
                        day_str = str(time_start)
                        env = Environment(start=f"{day_str} 00:00:00",
                                          end=f"{day_str} 23:45:00", timebase=15)
                        bev = BatteryElectricVehicle(
                            unit="kW", identifier="bev_quick", environment=env,
                            battery_max=bat_max, battery_min=bat_min,
                            battery_usage=bat_use, charging_power=charge_p,
                            charge_efficiency=eff, load_degradation_begin=0.8,
                        )
                        bev.prepare_time_series()
                        st.session_state["nsv2_profile_ev"] = _normalize_ts(bev.timeseries).abs()
                        st.success("EV-Profil erzeugt.")
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

        st.markdown("**Parametrisches Tagesganglinienprofil** *(vereinfacht, ohne Wetterdaten)*")
        st.caption(
            "Für ein wettergetriebenes Profil bitte die Wärmepumpen-Konfigurationsseite "
            "besuchen und das Ergebnis hier importieren."
        )
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
                    storage = np.zeros(96)
                    for i in range(96):
                        pv_val = float(pv_profile.iloc[i]) if i < len(pv_profile) else 0.0
                        if pv_val >= threshold:
                            storage[i] = -max_p          # charging (pp: negative p_mw)
                        elif 60 <= i <= 84:              # 15:00–21:00: discharge
                            storage[i] = max_p
                    charge_e = abs(storage[storage < 0].sum())
                    disch_e  = storage[storage > 0].sum()
                    if disch_e > 0 and charge_e > 0:
                        storage[storage > 0] *= min(1.0, charge_e / disch_e)
                    st.session_state["nsv2_profile_storage"] = pd.Series(storage)
                    st.success("Speicher-Profil (PV-Überschuss) erzeugt.")

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
                storage = np.zeros(96)
                for i in range(96):
                    in_window = (cs <= ce and cs <= i < ce) or (cs > ce and (i >= cs or i < ce))
                    storage[i] = -max_p if in_window else dis_p
                charge_e = abs(storage[storage < 0].sum())
                disch_steps = (storage > 0).sum()
                if disch_steps > 0 and charge_e > 0:
                    storage[storage > 0] *= min(1.0, charge_e / (dis_p * disch_steps))
                st.session_state["nsv2_profile_storage"] = pd.Series(storage)
                st.success("Speicher-Profil (feste Zeiten) erzeugt.")

        if "nsv2_profile_storage" in st.session_state:
            _profile_chart(st.session_state["nsv2_profile_storage"],
                           "kW (−=Laden, +=Entladen)", "nsv2_chart_st")

    # ------------------------------------------------------------------ #
    # Basislast                                                             #
    # ------------------------------------------------------------------ #
    with tab_bl:
        st.markdown("**SimBench-Normlastprofile**")
        st.caption(
            "Automatisch aus dem SimBench-Datensatz erzeugt. "
            "Klassifizierung nach Lastname (Haushalt, Gewerbe, Industrie, Landwirtschaft)."
        )
        if time_start is not None:
            day_index = (time_start - datetime(2020, 1, 1).date()).days % 365
        else:
            day_index = 0
        st.caption(f"Tag im Jahr: {day_index} (aus Abschnitt 2)")

        if st.button("Basislastprofil erzeugen", key="nsv2_bl_gen") \
                or "nsv2_profile_base" not in st.session_state:
            if len(net.load) == 0:
                st.info("Keine Lastknoten im Netz — Basislastprofil nicht erforderlich.")
            else:
                with st.spinner("SimBench-Profile laden…"):
                    try:
                        multiplier_df = Simbench_multiplier(net, day_index=day_index)
                        st.session_state["nsv2_profile_base"] = multiplier_df
                        st.success(
                            f"Profile erzeugt: {len(multiplier_df.columns)} Lastknoten, Tag {day_index}."
                        )
                    except Exception as e:
                        st.error(f"SimBench-Profile konnten nicht geladen werden: {e}")

        if "nsv2_profile_base" in st.session_state:
            base_df = st.session_state["nsv2_profile_base"]
            _profile_chart(base_df.mean(axis=1), "Mittlerer Multiplikator", "nsv2_chart_bl")
            st.caption(f"Mittelwert über {len(base_df.columns)} Lastknoten")


# ---------------------------------------------------------------------------
# Main page function
# ---------------------------------------------------------------------------

def netzmodell_v2():
    st.title("Netzmodell-Szenario")
    st.caption("Entwicklungsversion — WP1+WP2+WP3")

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
        _stored_name = st.session_state.get("nsv2_net_name", _net_opts[0])
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
                st.session_state.pop("nsv2_mastr_sgen_ts", None)
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
                    st.session_state.pop("nsv2_mastr_sgen_ts", None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Netz konnte nicht geladen werden: {e}")
                    return

        net = st.session_state.get("nsv2_net")

    else:
        st.session_state["nsv2_net_source"] = "upload"

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
                st.session_state.pop("nsv2_mastr_sgen_ts", None)
                st.success(
                    f"Netz geladen: {len(net.bus)} Knoten, {len(net.line)} Leitungen"
                )
            except Exception as e:
                st.error(f"Datei konnte nicht als pandapower-Netz geladen werden: {e}")
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
            st.session_state.pop("nsv2_mastr_sgen_ts", None)
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
            _tab_gezielt(net)
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
    st.subheader("4. Simulation & Ergebnisse")
    st.info("Simulationspipeline (Lastfluss / Zeitreihe) folgt in WP4.")


# ROADMAP: OPF (Optimale Lastflussberechnung)
# - Deprioritized; do not implement until PF pipeline is stable.
# - When implemented: offer PF | OPF->PF (fix dispatch from OPF, run PF for
#   physically consistent results). Do NOT use a silent PF fallback on OPF failure.
# - Before any OPF work: remove the 0.85-1.15 p.u. voltage limit hack and
#   the post-hoc loading normalization from the intern's netzmittimeseries.py.
