"""Windkraft-Konfiguration — Standortbasierte und Anlagenbasierte Simulation.

Zwei Modi:
  Standortbasiert: Ort per Stadtname (Geocoding) oder Koordinaten, Nabenhöhe, Nennleistung.
  Anlagenbasiert:  MaStR-Windanlagen auswählen (Stadt + Namensfilter), Mehrfachauswahl.

Vereinfachte Berechnung:
  DWD-Windgeschwindigkeit (10 m) + Hellman-Korrektur auf Nabenhöhe
  + normierte Leistungskurve aus data/median_windpower_curve.csv.
  Für den Anlagenbasiert-Modus wird eine einzige DWD-Anfrage für die Stadt
  verwendet; jede Turbine erhält ihre eigene Nabenhöhenkorrektur.
"""

from __future__ import annotations

import io
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from vpplib.environment import Environment

try:
    import osmnx as ox
    _HAS_OSMNX = True
except Exception:
    _HAS_OSMNX = False

from src.config.paths import MASTR_DB_PATH
from src.mastr.preprocessing import (
    get_unique_wind_locations,
    geocode_query_for_location,
    prepare_wind_data,
)
from src.data_layer.mastr_source import render_mastr_location_input
from src.ui.components.netzmittimeseries import get_normalized_wind_output, _get_wind_curve


# ---------------------------------------------------------------------------
# Cached helpers
# ---------------------------------------------------------------------------

@st.cache_data
def _wind_locations() -> list[str]:
    try:
        return get_unique_wind_locations(str(MASTR_DB_PATH)) or []
    except Exception:
        return []


@st.cache_data
def _wind_mastr(city: str) -> pd.DataFrame:
    """Load MaStR wind data for city and return as plain DataFrame."""
    try:
        gdf, _ = prepare_wind_data(city, str(MASTR_DB_PATH))
        cols = [
            "EinheitMastrNummer", "NameStromerzeugungseinheit", "NameWindpark",
            "Nettonennleistung", "Bruttoleistung", "Nabenhoehe", "Typenbezeichnung",
            "Breitengrad", "Laengengrad",
        ]
        available = [c for c in cols if c in gdf.columns]
        return pd.DataFrame(gdf[available]).reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


@st.cache_data
def _geocode(city: str) -> tuple[float, float]:
    lat, lon = ox.geocode(city)
    return float(lat), float(lon)


# ---------------------------------------------------------------------------
# Internal wind profile computation (reusable for multi-turbine Anlagenbasiert)
# ---------------------------------------------------------------------------

def _compute_wind_profiles_from_data(
    wind_speed_10m: pd.Series,
    turbines: list[dict],  # each: {label, hub_height_m, rated_kw}
    target_index: pd.DatetimeIndex,
    hellman_exp: float = 0.2,
) -> dict[str, pd.Series]:
    """Apply Hellman correction + median power curve for each turbine."""
    # Ensure wind_data index is timezone-naive for compatibility
    ws = wind_speed_10m.copy()
    if hasattr(ws.index, 'tz') and ws.index.tz is not None:
        ws.index = ws.index.tz_localize(None)

    curve = _get_wind_curve()
    profiles: dict[str, pd.Series] = {}

    for turbine in turbines:
        hub_h   = float(turbine.get("hub_height_m") or 100.0)
        cap_kw  = float(turbine.get("rated_kw")     or 0.0)
        label   = turbine["label"]

        v_hub = ws * (hub_h / 10.0) ** hellman_exp
        normalized = np.interp(v_hub.values, curve['wind_speed'].values, curve['value'].values)
        norm_series = pd.Series(normalized, index=ws.index, dtype=float)

        # Resample to 15-min
        norm_15 = (
            norm_series
            .reindex(norm_series.index.union(target_index))
            .interpolate(method='time')
            .reindex(target_index)
            .ffill()
            .fillna(0.0)
            .clip(0.0, 1.0)
        )
        profiles[label] = norm_15 * cap_kw

    return profiles


def _fetch_dwd_wind_speed(
    lat: float, lon: float, start_date, end_date
) -> pd.Series:
    """Fetch DWD wind speed at 10 m height for the full date range."""
    start_str = pd.Timestamp(start_date).strftime("%Y-%m-%d %H:%M:%S")
    end_str   = pd.Timestamp(end_date).strftime("%Y-%m-%d %H:%M:%S")
    env = Environment(start=start_str, end=end_str)
    env.get_dwd_wind_data(lat=float(lat), lon=float(lon))
    if env.wind_data is None or (hasattr(env.wind_data, 'empty') and env.wind_data.empty):
        raise ValueError("Keine Winddaten für den gewählten Standort/Zeitraum gefunden.")
    return pd.to_numeric(env.wind_data[('wind_speed', 10)], errors='coerce').fillna(0.0)


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _profile_chart(profiles: dict[str, pd.Series], key: str) -> None:
    fig = go.Figure()
    for label, series in profiles.items():
        x = series.index.tolist() if hasattr(series.index, 'tolist') else list(range(len(series)))
        fig.add_trace(go.Scatter(x=x, y=series.values, mode="lines", name=label, line=dict(width=2)))
    fig.update_layout(
        xaxis_title="Zeit", yaxis_title="Leistung (kW)", height=320,
        margin=dict(l=0, r=0, t=10, b=0), hovermode="x unified",
        showlegend=len(profiles) > 1,
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


def _metrics(series: pd.Series, rated_kw: float) -> None:
    peak     = float(series.max())
    total_kwh = float(series.sum()) * 0.25
    cf = (total_kwh / (rated_kw * len(series) * 0.25) * 100) if rated_kw > 0 else 0.0
    c1, c2, c3 = st.columns(3)
    c1.metric("Spitzenleistung", f"{peak:.1f} kW")
    c2.metric("Energie", f"{total_kwh:.0f} kWh")
    c3.metric("Kapazitätsfaktor", f"{cf:.1f} %")


def _csv_download(profiles: dict[str, pd.Series], key: str) -> None:
    df = pd.DataFrame(profiles)
    buf = io.BytesIO()
    df.to_csv(buf, encoding="utf-8")
    st.download_button(
        "CSV herunterladen", data=buf.getvalue(),
        file_name="wind_profile.csv", mime="text/csv", key=key,
    )


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------

def wind_configuration(key_suffix: str = "wind1") -> None:
    st.title("Windkraft-Konfiguration")
    from src.content.page_descriptions import render_page_description
    render_page_description("wind")

    # ── Mode ────────────────────────────────────────────────────────────────
    mode = st.radio(
        "Simulationstyp",
        ["Standortbasierte Simulation", "Anlagenbasierte Simulation"],
        horizontal=True,
        key="wind_cfg_mode",
        help="Standortbasiert: freie Anlagenangabe für einen Ort. Anlagenbasiert: reale MaStR-Windanlagen einer Stadt auswählen.",
    )

    lat: float | None = None
    lon: float | None = None
    hellman_exp: float = 0.2
    turbines_standort: dict | None = None  # used in Standortbasiert mode
    selected_turbines: list[dict] = []     # used in Anlagenbasiert mode

    # ── Location / turbine config ────────────────────────────────────────────
    if mode == "Standortbasierte Simulation":
        st.subheader("Standort & Anlagenparameter")
        if not _HAS_OSMNX:
            st.error("osmnx ist nicht installiert — Geocoding nicht verfügbar.")
            return

        city_input = st.text_input("Ort (Stadtname)", value="Aachen", key="wind_cfg_city")
        c1, c2 = st.columns(2)
        hub_height_m = c1.number_input(
            "Nabenhöhe (m)", min_value=10.0, max_value=300.0, value=100.0, key="wind_cfg_hub",
            help="Höhe der Rotornabe über Grund. Moderne Onshore-Anlagen 80–160 m; größere Höhe = mehr Ertrag.",
        )
        rated_kw = c2.number_input(
            "Nennleistung (kW)", min_value=1.0, max_value=20_000.0, value=2000.0, key="wind_cfg_cap",
            help="Nennleistung bei Nennwindgeschwindigkeit. Onshore typ. 2.000–6.000 kW; Kleinwind <100 kW.",
        )
        hellman_exp = st.number_input(
            "Hellman-Exponent",
            min_value=0.05, max_value=0.50, value=0.20, step=0.01,
            key="wind_cfg_hellman",
            help="0.10 = Küste/Offshore · 0.20 = offenes Gelände · 0.30-0.40 = Wald/Bebauung",
        )

        if city_input:
            try:
                lat, lon = _geocode(city_input)
                st.caption(f"Koordinaten: {lat:.4f}°N, {lon:.4f}°E")
            except Exception as e:
                st.error(f"Geocoding fehlgeschlagen: {e}")
                return

        turbines_standort = {
            "label": f"{city_input} ({rated_kw:.0f} kW, {hub_height_m:.0f} m)",
            "hub_height_m": hub_height_m,
            "rated_kw": rated_kw,
        }

    else:  # Anlagenbasierte Simulation
        st.subheader("MaStR-Windanlagen auswählen")
        if not _HAS_OSMNX:
            st.error("osmnx ist nicht installiert — Geocoding nicht verfügbar.")
            return

        locations = _wind_locations()
        city = render_mastr_location_input(
            locations, label="Stadt", key="wind_cfg_mastr_city", default="Aachen"
        )
        if not city:
            st.info("Bitte einen Ort oder eine PLZ eingeben.")
            return

        df_mastr = _wind_mastr(city)
        if df_mastr.empty:
            st.warning(f"Keine MaStR-Windanlagen für {city} gefunden.")
            return

        name_col  = "NameStromerzeugungseinheit"
        park_col  = "NameWindpark"
        cap_col   = "Nettonennleistung"
        hub_col   = "Nabenhoehe"
        type_col  = "Typenbezeichnung"

        name_filter = st.text_input(
            "Namensfilter (Anlagenname oder Windpark enthält…)", key="wind_cfg_namefilter"
        )
        filtered = df_mastr.copy()
        if name_filter:
            mask = (
                filtered.get(name_col, pd.Series(dtype=str)).fillna("").str.contains(name_filter, case=False, na=False)
                | filtered.get(park_col, pd.Series(dtype=str)).fillna("").str.contains(name_filter, case=False, na=False)
            )
            filtered = filtered[mask]

        if filtered.empty:
            st.info("Kein Treffer — Filter anpassen.")
            return

        hellman_exp = st.number_input(
            "Hellman-Exponent",
            min_value=0.05, max_value=0.50, value=0.20, step=0.01,
            key="wind_cfg_hellman_mastr",
            help="0.10 = Küste/Offshore · 0.20 = offenes Gelände · 0.30-0.40 = Wald/Bebauung",
        )

        def _label(row: pd.Series) -> str:
            name = str(row.get(name_col, "—"))
            cap  = row.get(cap_col, 0)
            hub  = row.get(hub_col, "?")
            try:
                cap_str = f"{float(cap):.0f} kW"
            except (ValueError, TypeError):
                cap_str = "? kW"
            try:
                hub_str = f"{float(hub):.0f} m"
            except (ValueError, TypeError):
                hub_str = "? m"
            return f"{name} ({cap_str}, {hub_str})"

        filtered["_label"] = filtered.apply(_label, axis=1)
        all_labels = filtered["_label"].tolist()

        selected_labels = st.multiselect(
            f"Anlagen auswählen ({len(filtered)} verfügbar)",
            options=all_labels,
            key="wind_cfg_multiselect",
        )

        if not selected_labels:
            st.info("Bitte mindestens eine Anlage auswählen.")
            return

        selected_rows = filtered[filtered["_label"].isin(selected_labels)]
        preview_cols = [c for c in [name_col, park_col, cap_col, hub_col, type_col] if c in selected_rows.columns]
        st.dataframe(selected_rows[preview_cols].reset_index(drop=True), use_container_width=True)

        try:
            lat, lon = _geocode(geocode_query_for_location(city, "wind", str(MASTR_DB_PATH)))
        except Exception as e:
            st.error(f"Geocoding fehlgeschlagen: {e}")
            return

        for _, row in selected_rows.iterrows():
            try:
                cap = float(row.get(cap_col, 0) or 0)
            except (ValueError, TypeError):
                cap = 0.0
            try:
                hub = float(row.get(hub_col, 100) or 100)
            except (ValueError, TypeError):
                hub = 100.0
            selected_turbines.append({
                "label": row["_label"],
                "hub_height_m": hub,
                "rated_kw": cap,
            })

    # ── Time range ───────────────────────────────────────────────────────────
    st.subheader("Zeitraum")
    default_end   = date.today() - timedelta(days=1)
    default_start = default_end - timedelta(days=6)
    col_s, col_e = st.columns(2)
    date_start = col_s.date_input("Von", value=default_start, key="wind_cfg_start")
    date_end   = col_e.date_input("Bis", value=default_end,   key="wind_cfg_end")
    n_days = (pd.Timestamp(date_end) - pd.Timestamp(date_start)).days + 1

    if n_days < 1:
        st.error("Enddatum muss nach dem Startdatum liegen.")
        return

    st.caption(f"{n_days} Tag(e) x 96 Schritte = {n_days * 96} Zeitschritte (15-min-Raster)")

    # ── Generate ─────────────────────────────────────────────────────────────
    if lat is None or lon is None:
        return

    if st.button("Profil generieren", type="primary", key="wind_cfg_run"):
        profiles: dict[str, pd.Series] = {}

        target_index = pd.date_range(
            start=pd.Timestamp(date_start),
            end=pd.Timestamp(date_end) + pd.Timedelta(days=1),
            freq="15min",
            inclusive="left",
        )

        if mode == "Standortbasierte Simulation":
            with st.spinner("DWD-Winddaten abrufen und Profil berechnen…"):
                series = get_normalized_wind_output(
                    lat=lat, lon=lon,
                    start_date=date_start,
                    end_date=pd.Timestamp(date_end) + pd.Timedelta(days=1),
                    hub_height_m=turbines_standort["hub_height_m"],
                    hellman_exp=hellman_exp,
                )
                series = series.reindex(target_index, fill_value=0.0) * turbines_standort["rated_kw"]
                profiles[turbines_standort["label"]] = series

        else:  # Anlagenbasiert — one DWD call, per-turbine hub correction
            with st.spinner("DWD-Winddaten abrufen (eine Anfrage für alle Anlagen)…"):
                wind_speed_10m = _fetch_dwd_wind_speed(
                    lat, lon,
                    start_date=date_start,
                    end_date=pd.Timestamp(date_end) + pd.Timedelta(days=1),
                )

            with st.spinner(f"Profile für {len(selected_turbines)} Anlage(n) berechnen…"):
                profiles = _compute_wind_profiles_from_data(
                    wind_speed_10m=wind_speed_10m,
                    turbines=selected_turbines,
                    target_index=target_index,
                    hellman_exp=hellman_exp,
                )

        total_rated_kw = (
            turbines_standort["rated_kw"]
            if mode == "Standortbasierte Simulation"
            else sum(t["rated_kw"] for t in selected_turbines)
        )

        st.session_state["wind_cfg_profiles"]      = profiles
        st.session_state["wind_cfg_total_rated_kw"] = total_rated_kw
        st.success(f"Profil(e) erzeugt: {len(profiles)} Anlage(n), {len(target_index)} Zeitschritte.")

    # ── Results ───────────────────────────────────────────────────────────────
    profiles = st.session_state.get("wind_cfg_profiles")
    if not profiles:
        return

    total_rated_kw = st.session_state.get("wind_cfg_total_rated_kw", 1.0)

    if len(profiles) == 1:
        label, series = next(iter(profiles.items()))
        st.subheader(label)
        _profile_chart({label: series}, key="wind_res_chart_single")
        _metrics(series, total_rated_kw)
        _csv_download({label: series}, key="wind_res_dl_single")

    else:
        agg = sum(profiles.values())
        agg.name = "Gesamt"

        tab_labels = list(profiles.keys()) + ["Gesamt (aggregiert)"]
        tabs = st.tabs(tab_labels)

        for tab, (label, series) in zip(tabs[:-1], profiles.items()):
            with tab:
                inst_rated = next(
                    (t["rated_kw"] for t in selected_turbines if t["label"] == label),
                    series.max() or 1.0,
                )
                _profile_chart({label: series}, key=f"wind_res_chart_{label[:30]}")
                _metrics(series, inst_rated)

        with tabs[-1]:
            _profile_chart({"Gesamt": agg}, key="wind_res_chart_agg")
            _metrics(agg, total_rated_kw)

        all_df = dict(profiles)
        all_df["Gesamt"] = agg
        _csv_download(all_df, key="wind_res_dl_multi")
