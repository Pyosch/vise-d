"""
Wind installation MaStR dashboard page.

Visualizes wind installations from German MaStR database and simulates energy generation.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import logging
from datetime import date, datetime, timedelta
import pandas as pd
import streamlit as st
import plotly.express as px
from vpplib.environment import Environment
from src.data_layer.cache import get_cached_unique_locations, get_cached_mastr_data, create_cached_scatter_map
from src.mastr.simulation import (
    wind_turbine_matching,
    init_windturbines_mastr,
    prepare_wind_time_series_mastr,
)
from src.config import MASTR_DB_PATH


class _StreamlitLogHandler(logging.Handler):
    """Captures log records into a list for display in Streamlit."""

    def __init__(self):
        super().__init__()
        self.records: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(self.format(record))


def wind_installation_mastr() -> None:
    """Display wind installations and simulate energy generation from MaStR data."""
    st.title("💨 Windanlagen")

    try:
        with st.spinner("Standorte werden geladen…"):
            unique_locations = get_cached_unique_locations("wind", str(MASTR_DB_PATH))
        if not unique_locations:
            st.error("Keine Standorte in der Datenbank gefunden.")
            st.info("Bitte prüfen, ob die MaStR-Datenbankdatei vorhanden ist und Daten enthält.")
            return
    except Exception as e:
        st.error("Datenbankverbindung fehlgeschlagen.")
        with st.expander("Technische Details"):
            st.code(str(e))
        return

    location = st.selectbox(
        "Stadt",
        options=unique_locations,
        index=unique_locations.index("Essen") if "Essen" in unique_locations else 0,
    )

    if not location:
        return

    # ── Anlagenübersicht ─────────────────────────────────────────────────────
    st.subheader("Anlagenübersicht")

    if st.button("Anlagen anzeigen", key="show_wind"):
        st.session_state["wind_map_location"] = location

    if st.session_state.get("wind_map_location") == location:
        try:
            gdf_wind, city_district = get_cached_mastr_data(location, "wind", str(MASTR_DB_PATH))

            if gdf_wind is None or len(gdf_wind) == 0:
                st.warning(f"Keine Windanlagen für {location} gefunden.")
            else:
                fig = create_cached_scatter_map(
                    gdf_wind,
                    lat_col="Breitengrad",
                    lon_col="Laengengrad",
                    hover_data=["NameStromerzeugungseinheit", "Bruttoleistung", "Nettonennleistung"],
                    center_lat=city_district.lat.item(),
                    center_lon=city_district.lon.item(),
                    color="brown",
                    title=f"Windanlagen in {location}",
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
                except Exception:
                    pass

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Anlagen", f"{len(gdf_wind):,}")
                col2.metric("Bruttoleistung", f"{gdf_wind['Bruttoleistung'].sum() / 1000:.1f} MW")
                col3.metric("Nettoleistung", f"{gdf_wind['Nettonennleistung'].sum() / 1000:.1f} MW")
                col4.metric("Ø Leistung", f"{gdf_wind['Bruttoleistung'].mean():.1f} kW")

                st.plotly_chart(fig, use_container_width=True)

                with st.expander("Detaillierte Statistiken"):
                    fig_cap = px.histogram(
                        gdf_wind,
                        x="Bruttoleistung",
                        nbins=20,
                        labels={"Bruttoleistung": "Bruttoleistung (kW)"},
                        title="Leistungsverteilung",
                    )
                    st.plotly_chart(fig_cap, use_container_width=True)

                    st.subheader("Tabelle der 10 größten Anlagen nach Bruttoleistung")
                    display_cols = ["NameStromerzeugungseinheit", "Bruttoleistung", "Nettonennleistung", "Breitengrad", "Laengengrad"]
                    top10 = gdf_wind[display_cols].sort_values("Bruttoleistung", ascending=False).head(10)
                    st.dataframe(top10, use_container_width=True)

                    csv_all = gdf_wind.drop(columns=["geometry"], errors="ignore").to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label=f"Alle {len(gdf_wind):,} Anlagen herunterladen (CSV)",
                        data=csv_all,
                        file_name=f"windanlagen_{location}.csv",
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
    date_start = col_s.date_input("Von", value=default_start, key="wind_energy_start")
    date_end = col_e.date_input("Bis", value=default_end, key="wind_energy_end")
    n_days = (pd.Timestamp(date_end) - pd.Timestamp(date_start)).days + 1

    if n_days < 1:
        st.error("Enddatum muss nach dem Startdatum liegen.")
        return

    st.caption(f"{n_days} Tag(e) x 96 Schritte = {n_days * 96} Zeitschritte (15-min-Raster)")

    sim_key = f"wind_sim_{location}_{date_start}_{date_end}"
    sim_result = st.session_state.get(sim_key)

    if st.button("Erzeugung berechnen", key="wind_sim_btn"):
        progress_bar = st.progress(0)
        log_handler = _StreamlitLogHandler()
        log_handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S"))
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)

        try:
            start_dt = datetime.combine(date_start, datetime.min.time())
            end_dt = datetime.combine(date_end, datetime.min.time()) + timedelta(days=1)

            with st.status("Simulation läuft…", expanded=True) as sim_status:
                st.write("MaStR-Winddaten werden geladen…")
                gdf_sim, city_dist_sim = get_cached_mastr_data(location, "wind", str(MASTR_DB_PATH))
                progress_bar.progress(10)

                st.write(f"Turbinentypen für {len(gdf_sim)} Anlagen werden abgeglichen…")
                gdf_sim = wind_turbine_matching(gdf_sim)
                progress_bar.progress(30)

                st.write("DWD-Wetterdaten werden geladen…")
                ref_env = Environment(
                    start=start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    end=end_dt.strftime("%Y-%m-%d %H:%M:%S"),
                )
                ref_env.get_dwd_wind_data(
                    lat=city_dist_sim.centroid.y,
                    lon=city_dist_sim.centroid.x,
                )
                progress_bar.progress(65)

                st.write(f"{len(gdf_sim)} Windturbinenmodelle werden initialisiert…")
                windturbines_dict = init_windturbines_mastr(gdf_sim, environment=ref_env)
                progress_bar.progress(80)

                st.write(f"Zeitreihensimulation für {len(windturbines_dict)} Turbinen…")
                prepare_wind_time_series_mastr(windturbines_dict)
                progress_bar.progress(90)

                st.write("Ergebnisse werden aggregiert…")
                all_series = [wt.timeseries for wt in windturbines_dict.values()]
                total_kw: pd.Series = pd.concat(all_series, axis=1).sum(axis=1)
                progress_bar.progress(100)

                sim_status.update(label="✅ Simulation abgeschlossen!", state="complete", expanded=False)

            st.session_state[sim_key] = {
                "total_kw": total_kw,
                "gdf": gdf_sim,
                "windturbines_dict": windturbines_dict,
                "date_start": date_start,
                "date_end": date_end,
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
        gdf_sim = sim_result["gdf"]
        windturbines_dict = sim_result["windturbines_dict"]

        col1, col2, col3 = st.columns(3)
        col1.metric("Windturbinen", len(windturbines_dict))
        col2.metric("Installierte Leistung", f"{float(gdf_sim['Nettonennleistung'].sum()):.1f} kW")
        col3.metric("Spitzenleistung", f"{float(total_kw.max()):.2f} kW")

        fig_ts = px.line(
            x=total_kw.index,
            y=total_kw.values,
            labels={"x": "Zeit", "y": "Leistung (kW)"},
            title=f"Aggregierte Windeinspeisung - {location} ({sim_result['date_start']} bis {sim_result['date_end']})",
        )
        fig_ts.update_layout(xaxis_title="Zeit", yaxis_title="Leistung (kW)")
        st.plotly_chart(fig_ts, use_container_width=True)

        st.subheader("Zeitreihendaten herunterladen")
        date_label = f"{sim_result['date_start']}_{sim_result['date_end']}"
        col_dl1, col_dl2 = st.columns(2)
        csv_agg = total_kw.rename("Leistung_kW").to_frame().to_csv().encode("utf-8")
        col_dl1.download_button(
            label="Aggregierte Zeitreihe (CSV)",
            data=csv_agg,
            file_name=f"wind_aggregiert_{location}_{date_label}.csv",
            mime="text/csv",
        )
        df_turbines = pd.DataFrame({
            name: wt.timeseries for name, wt in windturbines_dict.items()
        })
        df_turbines.insert(0, "Gesamt_kW", total_kw)
        csv_turbines = df_turbines.to_csv().encode("utf-8")
        col_dl2.download_button(
            label="Alle Turbinenzeitreihen (CSV)",
            data=csv_turbines,
            file_name=f"wind_alle_turbinen_{location}_{date_label}.csv",
            mime="text/csv",
        )

        if sim_result["log"]:
            with st.expander(f"⚙️ Simulationsprotokoll ({len(sim_result['log'])} Einträge)", expanded=False):
                for msg in sim_result["log"]:
                    st.text(msg)
