"""PV-Konfiguration — Standortbasierte und Anlagenbasierte Simulation.

Zwei Modi:
  Standortbasiert: Ort per Stadtname (Geocoding) oder Koordinaten, beliebige Kapazität.
  Anlagenbasiert:  MaStR-Anlagen auswählen (Stadt + Namensfilter), Mehrfachauswahl.

Vereinfachte Berechnung über get_normalized_pv_output (1-kWp-Referenzsystem + DWD).
"""

from __future__ import annotations

import io
from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    import osmnx as ox
    _HAS_OSMNX = True
except Exception:
    _HAS_OSMNX = False

from src.config.paths import MASTR_DB_PATH
from src.mastr.preprocessing import (
    get_unique_solar_locations,
    geocode_query_for_location,
    prepare_solar_data,
)
from src.data_layer.mastr_source import render_mastr_location_input
from src.ui.components.netzmittimeseries import get_normalized_pv_output


# ---------------------------------------------------------------------------
# Cached helpers
# ---------------------------------------------------------------------------

@st.cache_data
def _solar_locations() -> list[str]:
    try:
        return get_unique_solar_locations(str(MASTR_DB_PATH)) or []
    except Exception:
        return []


@st.cache_data
def _solar_mastr(city: str) -> pd.DataFrame:
    """Load MaStR solar data for city and return as plain DataFrame."""
    try:
        gdf, _ = prepare_solar_data(city, str(MASTR_DB_PATH))
        cols = [
            "EinheitMastrNummer", "NameStromerzeugungseinheit",
            "Nettonennleistung", "Bruttoleistung",
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
# Helpers
# ---------------------------------------------------------------------------

def _profile_chart(profiles: dict[str, pd.Series], key: str) -> None:
    fig = go.Figure()
    for label, series in profiles.items():
        fig.add_trace(go.Scatter(
            x=series.index.tolist() if hasattr(series.index, 'tolist') else list(range(len(series))),
            y=series.values,
            mode="lines",
            name=label,
            line=dict(width=2),
        ))
    fig.update_layout(
        xaxis_title="Zeit",
        yaxis_title="Leistung (kW)",
        height=320,
        margin=dict(l=0, r=0, t=10, b=0),
        hovermode="x unified",
        showlegend=len(profiles) > 1,
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


def _metrics(series: pd.Series, capacity_kwp: float) -> None:
    peak = float(series.max())
    total_kwh = float(series.sum()) * 0.25  # 15-min steps → hours
    cf = (total_kwh / (capacity_kwp * len(series) * 0.25) * 100) if capacity_kwp > 0 else 0.0
    c1, c2, c3 = st.columns(3)
    c1.metric("Spitzenleistung", f"{peak:.2f} kW")
    c2.metric("Energie", f"{total_kwh:.1f} kWh")
    c3.metric("Kapazitätsfaktor", f"{cf:.1f} %")


def _csv_download(profiles: dict[str, pd.Series], key: str) -> None:
    df = pd.DataFrame(profiles)
    buf = io.BytesIO()
    df.to_csv(buf, encoding="utf-8")
    st.download_button(
        "CSV herunterladen",
        data=buf.getvalue(),
        file_name="pv_profile.csv",
        mime="text/csv",
        key=key,
    )


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------

def pv_configuration() -> None:
    st.title("PV-Konfiguration")
    from src.content.page_descriptions import render_page_description
    render_page_description("pv")

    # ── Mode ────────────────────────────────────────────────────────────────
    mode = st.radio(
        "Simulationstyp",
        ["Standortbasierte Simulation", "Anlagenbasierte Simulation"],
        horizontal=True,
        key="pv_cfg_mode",
    )

    lat: float | None = None
    lon: float | None = None
    capacity_kwp: float = 10.0
    selected_installations: list[dict] = []  # list of {label, capacity_kwp, lat, lon}

    # ── Location / installation config ──────────────────────────────────────
    if mode == "Standortbasierte Simulation":
        st.subheader("Standort")
        if not _HAS_OSMNX:
            st.error("osmnx ist nicht installiert — Geocoding nicht verfügbar.")
            return

        city_input = st.text_input("Ort (Stadtname)", value="Aachen", key="pv_cfg_city")
        capacity_kwp = st.number_input(
            "Installierte Leistung (kWp)", min_value=0.1, max_value=100_000.0,
            value=10.0, key="pv_cfg_cap",
        )

        if city_input:
            try:
                lat, lon = _geocode(city_input)
                st.caption(f"Koordinaten: {lat:.4f}°N, {lon:.4f}°E")
            except Exception as e:
                st.error(f"Geocoding fehlgeschlagen: {e}")
                return

    else:  # Anlagenbasierte Simulation
        st.subheader("MaStR-Anlagen auswählen")
        if not _HAS_OSMNX:
            st.error("osmnx ist nicht installiert — Geocoding nicht verfügbar.")
            return

        locations = _solar_locations()
        city = render_mastr_location_input(
            locations, label="Stadt", key="pv_cfg_mastr_city", default="Aachen"
        )
        if not city:
            st.info("Bitte einen Ort oder eine PLZ eingeben.")
            return

        df_mastr = _solar_mastr(city)
        if df_mastr.empty:
            st.warning(f"Keine MaStR-Solardaten für {city} gefunden.")
            return

        name_col = "NameStromerzeugungseinheit"
        cap_col  = "Nettonennleistung"
        lat_col  = "Breitengrad"
        lon_col  = "Laengengrad"

        name_filter = st.text_input(
            "Namensfilter (Anlagenname enthält…)", key="pv_cfg_namefilter"
        )
        filtered = df_mastr.copy()
        if name_filter and name_col in filtered.columns:
            mask = filtered[name_col].fillna("").str.contains(name_filter, case=False, na=False)
            filtered = filtered[mask]

        if filtered.empty:
            st.info("Kein Treffer — Filter anpassen.")
            return

        def _label(row: pd.Series) -> str:
            name = str(row.get(name_col, "—"))
            cap  = row.get(cap_col, 0)
            try:
                cap_str = f"{float(cap):.0f} kW"
            except (ValueError, TypeError):
                cap_str = "? kW"
            return f"{name} ({cap_str})"

        filtered["_label"] = filtered.apply(_label, axis=1)
        all_labels = filtered["_label"].tolist()

        selected_labels = st.multiselect(
            f"Anlagen auswählen ({len(filtered)} verfügbar)",
            options=all_labels,
            key="pv_cfg_multiselect",
        )

        if not selected_labels:
            st.info("Bitte mindestens eine Anlage auswählen.")
            return

        selected_rows = filtered[filtered["_label"].isin(selected_labels)]
        preview_cols = [c for c in [name_col, cap_col, lat_col, lon_col] if c in selected_rows.columns]
        st.dataframe(selected_rows[preview_cols].reset_index(drop=True), use_container_width=True)

        # City centroid for weather data — resolve the ambiguous Ort to its
        # precise municipality so e.g. "Langenfeld" geocodes to NRW, not RLP.
        try:
            lat, lon = _geocode(geocode_query_for_location(city, "solar", str(MASTR_DB_PATH)))
        except Exception as e:
            st.error(f"Geocoding fehlgeschlagen: {e}")
            return

        for _, row in selected_rows.iterrows():
            try:
                cap = float(row.get(cap_col, 0) or 0)
            except (ValueError, TypeError):
                cap = 0.0
            selected_installations.append({
                "label": row["_label"],
                "capacity_kwp": cap,
            })

        capacity_kwp = sum(inst["capacity_kwp"] for inst in selected_installations)

    # ── Time range ───────────────────────────────────────────────────────────
    st.subheader("Zeitraum")
    default_end   = date.today() - timedelta(days=1)
    default_start = default_end - timedelta(days=6)
    col_s, col_e = st.columns(2)
    date_start = col_s.date_input("Von", value=default_start, key="pv_cfg_start")
    date_end   = col_e.date_input("Bis", value=default_end,   key="pv_cfg_end")
    n_days = (pd.Timestamp(date_end) - pd.Timestamp(date_start)).days + 1

    if n_days < 1:
        st.error("Enddatum muss nach dem Startdatum liegen.")
        return

    st.caption(f"{n_days} Tag(e) x 96 Schritte = {n_days * 96} Zeitschritte (15-min-Raster)")

    # ── Generate ─────────────────────────────────────────────────────────────
    if lat is None or lon is None:
        return

    if st.button("Profil generieren", type="primary", key="pv_cfg_run"):
        profiles: dict[str, pd.Series] = {}

        with st.spinner("DWD-Daten abrufen…"):
            raw = get_normalized_pv_output(
                lat, lon,
                pd.Timestamp(date_start),
                pd.Timestamp(date_end) + pd.Timedelta(days=1),
            )
        normalized = pd.to_numeric(raw, errors="coerce").fillna(0.0).reset_index(drop=True)
        dt_index = pd.date_range(
            start=pd.Timestamp(date_start), periods=len(normalized), freq="15min"
        )

        if mode == "Standortbasierte Simulation":
            profile = pd.Series(normalized.values * capacity_kwp, index=dt_index)
            profiles[f"{city_input} ({capacity_kwp:.0f} kWp)"] = profile

        else:  # Anlagenbasiert
            for inst in selected_installations:
                profiles[inst["label"]] = pd.Series(
                    normalized.values * inst["capacity_kwp"], index=dt_index
                )

        st.session_state["pv_cfg_profiles"] = profiles
        st.session_state["pv_cfg_capacity_kwp"] = capacity_kwp
        st.success(f"Profil(e) erzeugt: {len(profiles)} Anlage(n), {n_days * 96} Zeitschritte.")

    # ── Results ───────────────────────────────────────────────────────────────
    profiles = st.session_state.get("pv_cfg_profiles")
    if not profiles:
        return

    capacity_kwp = st.session_state.get("pv_cfg_capacity_kwp", capacity_kwp)

    if len(profiles) == 1:
        label, series = next(iter(profiles.items()))
        st.subheader(label)
        _profile_chart({label: series}, key="pv_res_chart_single")
        _metrics(series, series.max() if series.max() > 0 else 1.0)
        _csv_download({label: series}, key="pv_res_dl_single")

    else:
        # Multiple installations: tabs per installation + aggregated
        agg = sum(profiles.values())
        agg.name = "Gesamt"

        tab_labels = list(profiles.keys()) + ["Gesamt (aggregiert)"]
        tabs = st.tabs(tab_labels)

        for tab, (label, series) in zip(tabs[:-1], profiles.items()):
            with tab:
                inst_cap = series.max() if series.max() > 0 else 1.0
                _profile_chart({label: series}, key=f"pv_res_chart_{label[:30]}")
                _metrics(series, inst_cap)

        with tabs[-1]:
            _profile_chart({"Gesamt": agg}, key="pv_res_chart_agg")
            _metrics(agg, capacity_kwp)

        all_df = dict(profiles)
        all_df["Gesamt"] = agg
        _csv_download(all_df, key="pv_res_dl_multi")
