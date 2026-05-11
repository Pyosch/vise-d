"""Network Scenario page.

Wires together a pandapower network, MaStR generation assets, household
load profiles and the vpplib time-series power-flow interface.
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pandapower as pp
import pandapower.networks as pn
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    from pandapower.plotting.plotly import simple_plotly
    _HAS_PLOTLY_NET = True
except Exception:
    _HAS_PLOTLY_NET = False

import osmnx as ox
from vpplib.environment import Environment

from src.config.paths import DATA_DIR, MASTR_DB_PATH, PV_PARAMS_DIR
from src.data_layer.environment import get_cached_environment
from src.data_layer.weather_integration import fetch_weather_for_pv, fetch_weather_for_wind
from src.mastr.preprocessing import prepare_solar_data, prepare_wind_data
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
from src.utils.vpplib_interface import assign_assets_to_buses, build_timeseries_net


_NETWORKS: dict[str, callable] = {
    "4-Knoten-Stichleitung": pn.panda_four_load_branch,
    "CIGRE Mittelspannung": pn.create_cigre_network_mv,
    "Kerber Freileitung": pn.create_kerber_landnetz_freileitung_1,
}


def _fresh_net(name: str):
    return _NETWORKS[name]()


@st.cache_data
def _geocode(location: str) -> tuple[float, float]:
    lat, lon = ox.geocode(location)
    return float(lat), float(lon)


def _align_to_index(series_kw: pd.Series, target_index: pd.DatetimeIndex) -> pd.Series:
    """Resample/tile a timeseries to match target_index (assumes 15-min freq)."""
    if series_kw.index.tz != target_index.tz:
        try:
            series_kw = series_kw.tz_convert(target_index.tz) if series_kw.index.tz else series_kw.tz_localize(target_index.tz)
        except Exception:
            series_kw = series_kw.tz_localize(None)
            target_index = target_index.tz_localize(None)
    return series_kw.reindex(target_index, method="nearest", tolerance="30min").fillna(0.0)


def _tile_weekly_to_index(weekly_values: np.ndarray, target_index: pd.DatetimeIndex) -> pd.Series:
    """Tile a 672-slot weekly profile to fill target_index length."""
    n = len(target_index)
    repeats = (n // len(weekly_values)) + 2
    tiled = np.tile(weekly_values, repeats)[:n]
    return pd.Series(tiled, index=target_index)


def network_scenario():
    st.title("Netzmodell-Szenario")
    st.write(
        "Analysieren Sie Netzauslastung und Engpässe unter Berücksichtigung "
        "von MaStR-Erzeugungsanlagen und Haushaltsflexibilität."
    )

    # ------------------------------------------------------------------ #
    # Step 1: Network selection                                            #
    # ------------------------------------------------------------------ #
    st.subheader("1. Netzauswahl")
    net_name = st.selectbox("Pandapower-Testnetz", options=list(_NETWORKS.keys()))
    net_display = _fresh_net(net_name)

    if _HAS_PLOTLY_NET:
        try:
            fig_net = simple_plotly(net_display, figsize=(6, 4))
            st.plotly_chart(fig_net, use_container_width=True)
        except Exception as e:
            st.caption(f"Netz-Visualisierung nicht verfügbar: {e}")
    else:
        st.info(f"Netz: {len(net_display.bus)} Knoten, {len(net_display.line)} Leitungen, {len(net_display.load)} Lasten")

    # ------------------------------------------------------------------ #
    # Step 2: Region and time period                                       #
    # ------------------------------------------------------------------ #
    st.subheader("2. Region und Zeitraum")
    col_loc, col_dates = st.columns([1, 2])
    with col_loc:
        location = st.text_input("Ort (MaStR-Filterung)", value="Aachen")
    with col_dates:
        c1, c2 = st.columns(2)
        default_start = datetime(2023, 7, 3)
        default_end = datetime(2023, 7, 9, 23, 45)
        start_date = c1.date_input("Von", value=default_start)
        end_date = c2.date_input("Bis", value=default_end)

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time().replace(second=0, microsecond=0))
    start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")

    # ------------------------------------------------------------------ #
    # Step 3: Asset simulation                                             #
    # ------------------------------------------------------------------ #
    st.subheader("3. MaStR-Anlagen laden und simulieren")

    if st.button("MaStR-Anlagen laden", type="primary"):
        net = _fresh_net(net_name)

        with st.spinner("Geocoding..."):
            try:
                lat, lon = _geocode(location)
            except Exception as e:
                st.error(f"Geocoding fehlgeschlagen: {e}")
                return

        with st.spinner("Wetterdaten abrufen..."):
            try:
                pv_env = get_cached_environment(start_str, end_str, lat, lon)
                if pv_env is None:
                    st.error("PV-Umgebung konnte nicht erstellt werden.")
                    return

                wind_weather, _ = fetch_weather_for_wind(lat, lon, start_dt, end_dt)
                wind_env = Environment(start=start_str, end=end_str)
                wind_env.wind_data = wind_weather
            except Exception as e:
                st.error(f"Fehler beim Wetterdatenabruf: {e}")
                return

        pv_sgen_map: dict[str, int] = {}
        wind_sgen_map: dict[str, int] = {}
        sgen_timeseries: dict[int, pd.Series] = {}
        pv_info = {"count": 0, "with_coords": 0}
        wind_info = {"count": 0}

        with st.spinner("PV-Anlagen laden..."):
            try:
                gdf_solar, _ = prepare_solar_data(location, str(MASTR_DB_PATH))
                gdf_solar = revise_power_values(gdf_solar)
                pv_info["count"] = len(gdf_solar)
                pv_info["with_coords"] = int(gdf_solar[["Breitengrad", "Laengengrad"]].notna().all(axis=1).sum())

                if not gdf_solar.empty:
                    pv_bus_assignments = assign_assets_to_buses(net, gdf_solar)
                    params_df = load_or_build_pv_params(gdf_solar, PV_PARAMS_DIR / f"params_{location.lower()}.csv")
                    pv_systems = build_pvsystems_from_params(params_df, pv_env)
                    prepare_pv_time_series_mastr(pv_systems)
                    pv_aggregated = aggregate_pv_time_series(pv_systems)

                    for mastr_nr, ts in pv_aggregated.items():
                        bus_idx = pv_bus_assignments.get(mastr_nr)
                        if bus_idx is None:
                            continue
                        ts_series = ts.iloc[:, 0] if isinstance(ts, pd.DataFrame) else ts
                        peak_mw = float(ts_series.max()) / 1000.0
                        sgen_idx = pp.create_sgen(
                            net, bus=bus_idx, p_mw=max(peak_mw, 0.001),
                            name=f"PV_{mastr_nr}", type="PV", in_service=True
                        )
                        pv_sgen_map[mastr_nr] = sgen_idx
                        sgen_timeseries[sgen_idx] = ts_series
            except Exception as e:
                st.warning(f"PV-Anlagen konnten nicht geladen werden: {e}")

        with st.spinner("Windkraftanlagen laden..."):
            try:
                gdf_wind, _ = prepare_wind_data(location, str(MASTR_DB_PATH))
                wind_info["count"] = len(gdf_wind)

                if not gdf_wind.empty:
                    gdf_wind = wind_turbine_matching(gdf_wind)
                    wind_bus_assignments = assign_assets_to_buses(net, gdf_wind)
                    wind_dict = init_windturbines_mastr(gdf_wind, wind_env)
                    prepare_wind_time_series_mastr(wind_dict)
                    wind_agg = aggregate_wind_time_series(wind_dict)

                    # One aggregate wind sgen at the most common bus
                    if wind_bus_assignments:
                        from collections import Counter
                        dominant_bus = Counter(wind_bus_assignments.values()).most_common(1)[0][0]
                        wind_ts = wind_agg.iloc[:, 0] if isinstance(wind_agg, pd.DataFrame) else wind_agg
                        peak_wind_mw = float(wind_ts.max()) / 1000.0
                        wind_sgen_idx = pp.create_sgen(
                            net, bus=dominant_bus, p_mw=max(peak_wind_mw, 0.001),
                            name="Wind_aggregiert", type="WKA", in_service=True
                        )
                        wind_sgen_map["wind_agg"] = wind_sgen_idx
                        sgen_timeseries[wind_sgen_idx] = wind_ts
            except Exception as e:
                st.warning(f"Windkraftanlagen konnten nicht geladen werden: {e}")

        # Build sgen_df with common simulation index
        if sgen_timeseries:
            # Find common index from first sgen
            first_ts = next(iter(sgen_timeseries.values()))
            sim_index = first_ts.index if hasattr(first_ts, 'index') else pd.date_range(start_str, end_str, freq='15min')

            sgen_df = pd.DataFrame(index=sim_index)
            for sgen_idx, ts in sgen_timeseries.items():
                aligned = _align_to_index(ts, sim_index)
                sgen_df[sgen_idx] = aligned / 1000.0  # kW → MW
        else:
            sim_index = pd.date_range(start_str, periods=672, freq='15min')
            sgen_df = pd.DataFrame(index=sim_index)
            st.warning("Keine Erzeugungsanlagen gefunden. Verwende leeren Sgen-DataFrame.")

        # Store in session state
        st.session_state["_net"] = net
        st.session_state["_sgen_df"] = sgen_df
        st.session_state["_sim_index"] = sim_index
        st.session_state["selected_net"] = net

        m1, m2, m3 = st.columns(3)
        m1.metric("PV-Anlagen gefunden", pv_info["count"])
        m2.metric("davon mit Koordinaten", pv_info.get("with_coords", 0))
        m3.metric("Windkraftanlagen gefunden", wind_info["count"])
        st.success("Anlagen geladen und simuliert.")

    # ------------------------------------------------------------------ #
    # Step 4: Load configuration                                           #
    # ------------------------------------------------------------------ #
    st.subheader("4. Lastkonfiguration")
    has_flex = "baseline_load_df" in st.session_state

    if has_flex:
        baseline_mean_mw = float(st.session_state["baseline_load_df"]["p_mw"].mean())
        flex_mean_mw = float(st.session_state["flex_scenario_load_df"]["p_mw"].mean())
        rate = st.session_state.get("participation_rate", 0.0)
        st.info(
            f"Lastprofil vom Flexibilitätskonfigurator: "
            f"Basis {baseline_mean_mw*1000:.1f} kW, "
            f"Flex {flex_mean_mw*1000:.1f} kW "
            f"(Flexquote {rate*100:.0f} %)"
        )
    else:
        total_load_kw = st.slider(
            "Gesamtlast (kW, gleichmäßig auf Lastknoten verteilt)",
            min_value=10,
            max_value=5000,
            value=500,
            step=10,
        )
        baseline_mean_mw = total_load_kw / 1000.0
        flex_mean_mw = baseline_mean_mw * 0.9

    # ------------------------------------------------------------------ #
    # Step 5: Run scenario                                                 #
    # ------------------------------------------------------------------ #
    st.subheader("5. Szenario berechnen")

    if "_net" not in st.session_state:
        st.info("Bitte zuerst MaStR-Anlagen laden (Schritt 3).")
        return

    net: pp.pandapowerNet = st.session_state["_net"]
    sgen_df: pd.DataFrame = st.session_state["_sgen_df"]
    sim_index: pd.DatetimeIndex = st.session_state["_sim_index"]

    def _build_load_df(mean_mw: float) -> pd.DataFrame:
        load_indices = net.load.index.tolist()
        if not load_indices:
            return pd.DataFrame(index=sim_index)
        p_per_load = mean_mw / len(load_indices)

        if has_flex:
            if net.load.index[0] == 0:
                profile_key = "baseline_load_df" if mean_mw == baseline_mean_mw else "flex_scenario_load_df"
                profile_df = st.session_state.get(profile_key, st.session_state["baseline_load_df"])
                weekly_vals = profile_df["p_mw"].values / len(load_indices)
                load_data = {
                    idx: _tile_weekly_to_index(weekly_vals, sim_index).values
                    for idx in load_indices
                }
            else:
                load_data = {idx: np.full(len(sim_index), p_per_load) for idx in load_indices}
        else:
            load_data = {idx: np.full(len(sim_index), p_per_load) for idx in load_indices}

        return pd.DataFrame(load_data, index=sim_index)

    c1, c2 = st.columns(2)
    run_baseline = c1.button("Basis-Szenario berechnen", use_container_width=True)
    run_flex = c2.button("Flexibilitäts-Szenario berechnen", use_container_width=True, disabled=not has_flex)

    def _run_scenario(mean_mw: float) -> dict:
        """Build load df, reset indices to integer (required by DFData), run timeseries."""
        load_df = _build_load_df(mean_mw)
        # DFData.get_time_step_value uses integer loc — reset index before passing
        sgen_int = sgen_df.reset_index(drop=True)
        load_int = load_df.reset_index(drop=True)
        results = build_timeseries_net(copy.deepcopy(net), sgen_int, load_int)
        # Re-attach DatetimeIndex to results for display
        for key, df in results.items():
            if len(df) == len(sim_index):
                df.index = sim_index
        return results

    if run_baseline:
        with st.spinner("Basis-Szenario wird berechnet..."):
            try:
                results_b = _run_scenario(baseline_mean_mw)
                st.session_state["_results_baseline"] = results_b
                st.session_state["scenario_results"] = results_b
                st.success("Basis-Szenario berechnet.")
            except Exception as e:
                st.error(f"Fehler bei der Berechnung: {e}")

    if run_flex:
        with st.spinner("Flexibilitäts-Szenario wird berechnet..."):
            try:
                results_f = _run_scenario(flex_mean_mw)
                st.session_state["_results_flex"] = results_f
                st.success("Flexibilitäts-Szenario berechnet.")
            except Exception as e:
                st.error(f"Fehler bei der Berechnung: {e}")

    # ------------------------------------------------------------------ #
    # Step 6: Results                                                      #
    # ------------------------------------------------------------------ #
    has_baseline_res = "_results_baseline" in st.session_state
    has_flex_res = "_results_flex" in st.session_state

    if not has_baseline_res:
        return

    st.subheader("6. Ergebnisse")

    def _render_results(results: dict, title: str):
        res_line = results.get("res_line", pd.DataFrame())
        res_bus = results.get("res_bus", pd.DataFrame())

        st.markdown(f"**{title}**")

        # Leitungsauslastung heatmap
        if not res_line.empty:
            loading_cols = [c for c in res_line.columns if "loading" in str(c).lower()]
            if loading_cols:
                heat_df = res_line[loading_cols]
                heat_df.columns = [str(c) for c in heat_df.columns]
                heat_df.index = [str(t) for t in heat_df.index]
                fig_heat = px.imshow(
                    heat_df.T,
                    color_continuous_scale=[[0, "#22c55e"], [0.8, "#facc15"], [1.0, "#ef4444"]],
                    zmin=0, zmax=120,
                    labels={"x": "Zeitstempel", "y": "Leitung", "color": "Auslastung (%)"},
                    title="Leitungsauslastung (%)",
                )
                st.plotly_chart(fig_heat, use_container_width=True)

                # Engpass-Zeitpunkte
                congestion_mask = (heat_df > 80).any(axis=1)
                congestion_df = res_line.loc[congestion_mask, loading_cols]
                if not congestion_df.empty:
                    st.markdown(f"**Engpass-Zeitpunkte (> 80 %):** {len(congestion_df)}")
                    display_df = congestion_df.head(20).copy()
                    display_df.index = display_df.index.astype(str)
                    display_df.columns = [str(c) for c in display_df.columns]
                    st.dataframe(display_df.style.format("{:.1f}"), height=200)

        # Spannungsband
        if not res_bus.empty:
            vm_cols = [c for c in res_bus.columns if "vm" in str(c).lower()]
            if vm_cols:
                vm_df = res_bus[vm_cols]
                vm_min = vm_df.min(axis=1)
                vm_max = vm_df.max(axis=1)
                fig_vm = go.Figure()
                fig_vm.add_trace(go.Scatter(
                    x=vm_df.index.astype(str), y=vm_max, name="Max U (p.u.)",
                    line=dict(color="#2563eb"), fill=None,
                ))
                fig_vm.add_trace(go.Scatter(
                    x=vm_df.index.astype(str), y=vm_min, name="Min U (p.u.)",
                    line=dict(color="#dc2626"), fill="tonexty", fillcolor="rgba(239,68,68,0.1)",
                ))
                fig_vm.add_hline(y=1.05, line_dash="dot", line_color="gray", annotation_text="1.05 p.u.")
                fig_vm.add_hline(y=0.95, line_dash="dot", line_color="gray", annotation_text="0.95 p.u.")
                fig_vm.update_layout(title="Spannungsband (p.u.)", height=300, showlegend=True)
                st.plotly_chart(fig_vm, use_container_width=True)

    col_b, col_f = st.columns(2)
    with col_b:
        _render_results(st.session_state["_results_baseline"], "Basis-Szenario")

    with col_f:
        if has_flex_res:
            _render_results(st.session_state["_results_flex"], "Flexibilitäts-Szenario")
        else:
            st.info("Flexibilitäts-Szenario noch nicht berechnet.")

    # Summary metric
    if has_baseline_res and has_flex_res:
        st.divider()
        res_b = st.session_state["_results_baseline"].get("res_line", pd.DataFrame())
        res_f = st.session_state["_results_flex"].get("res_line", pd.DataFrame())

        if not res_b.empty and not res_f.empty:
            loading_cols_b = [c for c in res_b.columns if "loading" in str(c).lower()]
            loading_cols_f = [c for c in res_f.columns if "loading" in str(c).lower()]
            if loading_cols_b and loading_cols_f:
                congestion_b = int((res_b[loading_cols_b] > 80).any(axis=1).sum())
                congestion_f = int((res_f[loading_cols_f] > 80).any(axis=1).sum())
                resolved = max(0, congestion_b - congestion_f)
                st.metric(
                    "Engpässe beseitigt",
                    f"{resolved} von {congestion_b} Zeitpunkten",
                    delta=f"-{resolved}" if resolved > 0 else "0",
                    delta_color="normal" if resolved > 0 else "off",
                )


network_scenario()
