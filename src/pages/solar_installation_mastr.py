"""
Solar installation MaStR dashboard page.

Visualizes solar installations from German MaStR database and simulates energy generation.

Author: Pyosch
AI Assistance: Claude Code (Claude Opus 4.8)
"""

__author__ = "Pyosch"
__credits__ = ["Claude Code (Claude Opus 4.8)"]

import logging
from datetime import date, timedelta
import pandas as pd
import streamlit as st
import plotly.express as px
from vpplib.environment import Environment
from src.data_layer.cache import get_cached_unique_locations, get_cached_mastr_data, create_cached_scatter_map
from src.data_layer.mastr_source import render_mastr_location_input
from src.mastr.simulation import (
    load_or_build_pv_params,
    build_pvsystems_from_params,
    prepare_pv_time_series_mastr,
    aggregate_pv_time_series,
    revise_power_values,
)
from src.config import MASTR_DB_PATH, PV_PARAMS_DIR


class _StreamlitLogHandler(logging.Handler):
    """Captures log records into a list for display in Streamlit."""

    def __init__(self):
        super().__init__()
        self.records: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(self.format(record))


def solar_installation_mastr() -> None:
    """Display solar installations and simulate energy generation from MaStR data."""
    st.title("☀️ Solaranlagen")
    from src.content.page_descriptions import render_page_description
    render_page_description("solar_mastr")

    with st.spinner("Standorte werden geladen…"):
        unique_locations = get_cached_unique_locations("solar", str(MASTR_DB_PATH))

    location = render_mastr_location_input(
        unique_locations, label="Stadt", key="solar_loc", default="Essen"
    )

    if not location:
        return

    # ── Anlagenübersicht ─────────────────────────────────────────────────────
    st.subheader("Anlagenübersicht")

    if st.button("Anlagen anzeigen", key="show_solar"):
        st.session_state["solar_map_location"] = location

    if st.session_state.get("solar_map_location") == location:
        try:
            gdf_solar, city_district = get_cached_mastr_data(location, "solar", str(MASTR_DB_PATH))

            if gdf_solar is None or len(gdf_solar) == 0:
                st.warning(f"Keine Solaranlagen für {location} gefunden.")
            else:
                fig = create_cached_scatter_map(
                    gdf_solar,
                    lat_col="Breitengrad",
                    lon_col="Laengengrad",
                    hover_data=["NameStromerzeugungseinheit", "Bruttoleistung", "Nettonennleistung"],
                    center_lat=city_district.lat.item(),
                    center_lon=city_district.lon.item(),
                    color="red",
                    title=f"Solaranlagen in {location}",
                )
                try:
                    choropleth = px.choropleth_mapbox(
                        city_district,
                        geojson=city_district.geometry,
                        locations=city_district.index,
                        color=None,
                        opacity=0.3,
                    )
                    fig.add_trace(choropleth.data[0])
                    # Move choropleth to index 0 so scatter dots render on top
                    fig.data = (fig.data[-1],) + fig.data[:-1]
                except Exception:
                    pass

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Anlagen", f"{len(gdf_solar):,}")
                col2.metric("Bruttoleistung", f"{gdf_solar['Bruttoleistung'].sum() / 1000:.1f} MW")
                col3.metric("Nettoleistung", f"{gdf_solar['Nettonennleistung'].sum() / 1000:.1f} MW")
                col4.metric("Ø Leistung", f"{gdf_solar['Bruttoleistung'].mean():.1f} kW")

                st.plotly_chart(fig, use_container_width=True)

                with st.expander("Detaillierte Statistiken"):
                    fig_cap = px.histogram(
                        gdf_solar,
                        x="Bruttoleistung",
                        nbins=20,
                        labels={"Bruttoleistung": "Bruttoleistung (kW)"},
                        title="Leistungsverteilung",
                    )
                    st.plotly_chart(fig_cap, use_container_width=True)

                    st.subheader("Tabelle der 10 größten Anlagen nach Bruttoleistung")
                    display_cols = ["NameStromerzeugungseinheit", "Bruttoleistung", "Nettonennleistung", "Breitengrad", "Laengengrad"]
                    top10 = gdf_solar[display_cols].sort_values("Bruttoleistung", ascending=False).head(10)
                    st.dataframe(top10, use_container_width=True)

                    csv_all = gdf_solar.drop(columns=["geometry"], errors="ignore").to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label=f"Alle {len(gdf_solar):,} Anlagen herunterladen (CSV)",
                        data=csv_all,
                        file_name=f"solaranlagen_{location}.csv",
                        mime="text/csv",
                    )

        except Exception as e:
            st.error(f"Fehler beim Laden der Anlagendaten: {e}")

    # ── Erzeugungssimulation ─────────────────────────────────────────────────
    st.divider()
    st.subheader("Erzeugungssimulation")

    default_end = date.today() - timedelta(days=1)
    default_start = default_end - timedelta(days=6)
    col_s, col_e = st.columns(2)
    date_start = col_s.date_input("Von", value=default_start, key="solar_energy_start")
    date_end = col_e.date_input("Bis", value=default_end, key="solar_energy_end")
    n_days = (pd.Timestamp(date_end) - pd.Timestamp(date_start)).days + 1

    if n_days < 1:
        st.error("Enddatum muss nach dem Startdatum liegen.")
        return

    st.caption(f"{n_days} Tag(e) × 96 Schritte = {n_days * 96} Zeitschritte (15-min-Raster)")

    sim_key = f"solar_sim_{location}_{date_start}_{date_end}"
    sim_result = st.session_state.get(sim_key)

    if st.button("Erzeugung berechnen", key="solar_sim_btn"):
        progress_bar = st.progress(0)
        log_handler = _StreamlitLogHandler()
        log_handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S"))
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)

        try:
            start = f"{date_start} 00:00:00"
            end = f"{date_end} 23:45:00"

            with st.status("Simulation läuft…", expanded=True) as sim_status:
                st.write("MaStR-Solardaten werden geladen…")
                gdf_sim, city_dist_sim = get_cached_mastr_data(location, "solar", str(MASTR_DB_PATH))
                progress_bar.progress(10)

                st.write(f"Leistungswerte für {len(gdf_sim)} Anlagen werden korrigiert…")
                gdf_sim = revise_power_values(gdf_sim)
                progress_bar.progress(30)

                st.write("DWD-Wetterdaten werden geladen…")
                ref_env = Environment(start=start, end=end)
                ref_env.get_dwd_pv_data(lat=city_dist_sim.lat, lon=city_dist_sim.lon)
                progress_bar.progress(50)

                st.write("PV-Parameter werden geladen / berechnet…")
                cache_path = PV_PARAMS_DIR / f"{location}.csv"
                params_df = load_or_build_pv_params(gdf_sim, cache_path)
                progress_bar.progress(60)

                st.write(f"{len(params_df)} PV-Systemmodelle werden erstellt…")
                pv_systems = build_pvsystems_from_params(params_df, ref_env)
                progress_bar.progress(75)

                st.write(f"Zeitreihensimulation für {len(params_df)} Systeme…")
                prepare_pv_time_series_mastr(pv_systems)
                progress_bar.progress(90)

                st.write("Ergebnisse werden aggregiert…")
                pv_systems_agg = aggregate_pv_time_series(pv_systems)
                progress_bar.progress(100)

                sim_status.update(label="✅ Simulation abgeschlossen!", state="complete", expanded=False)

            total_kw: pd.Series = sum(pv_systems_agg.values()).sum(axis=1)
            st.session_state[sim_key] = {
                "total_kw": total_kw,
                "params_df": params_df,
                "pv_systems_agg": pv_systems_agg,
                "start": start,
                "end": end,
                "log": log_handler.records.copy(),
            }
            sim_result = st.session_state[sim_key]

        except Exception as e:
            st.error(f"Simulation fehlgeschlagen: {e}")
        finally:
            root_logger.removeHandler(log_handler)
            progress_bar.empty()

    if sim_result:
        total_kw = sim_result["total_kw"]
        params_df = sim_result["params_df"]

        col1, col2, col3 = st.columns(3)
        col1.metric("PV-Systeme", len(params_df))
        col2.metric("Installierte Leistung", f"{params_df['pdc0_module_W'].sum() / 1000:.1f} kW")
        col3.metric("Spitzenleistung", f"{float(total_kw.max()):.2f} kW")

        fig_ts = px.line(
            x=total_kw.index,
            y=total_kw.values,
            labels={"x": "Zeit", "y": "Leistung (kW)"},
            title=f"Aggregierte Solareinspeisung - {location} ({sim_result['start'][:10]} bis {sim_result['end'][:10]})",
        )
        fig_ts.update_layout(xaxis_title="Zeit", yaxis_title="Leistung (kW)")
        st.plotly_chart(fig_ts, use_container_width=True)

        st.subheader("Zeitreihendaten herunterladen")
        date_label = f"{sim_result['start'][:10]}_{sim_result['end'][:10]}"
        col_dl1, col_dl2 = st.columns(2)
        csv_agg = total_kw.rename("Leistung_kW").to_frame().to_csv().encode("utf-8")
        col_dl1.download_button(
            label="Aggregierte Zeitreihe (CSV)",
            data=csv_agg,
            file_name=f"solar_aggregiert_{location}_{date_label}.csv",
            mime="text/csv",
        )
        pv_agg = sim_result["pv_systems_agg"]
        df_systems = pd.DataFrame({
            str(k): (v.sum(axis=1) if hasattr(v, "columns") else v)
            for k, v in pv_agg.items()
        })
        df_systems.insert(0, "Gesamt_kW", total_kw)
        csv_systems = df_systems.to_csv().encode("utf-8")
        col_dl2.download_button(
            label="Alle Systemzeitreihen (CSV)",
            data=csv_systems,
            file_name=f"solar_alle_systeme_{location}_{date_label}.csv",
            mime="text/csv",
        )

        if sim_result["log"]:
            with st.expander(f"⚙️ Datenkorrekturen ({len(sim_result['log'])} Einträge)", expanded=False):
                for msg in sim_result["log"]:
                    st.text(msg)
