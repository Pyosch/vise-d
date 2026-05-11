"""
Solar energy generation simulation page.

Simulates solar energy generation using MaStR data and vpplib models.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import logging
import pandas as pd
import streamlit as st
import plotly.express as px
from vpplib.environment import Environment
from src.data_layer.cache import get_cached_unique_locations, get_cached_mastr_data
from src.mastr.simulation import (
    load_or_build_pv_params,
    build_pvsystems_from_params,
    prepare_pv_time_series_mastr,
    aggregate_pv_time_series,
    revise_power_values
)
from src.config import MASTR_DB_PATH, PV_PARAMS_DIR
from src.data_layer.weather_integration import fetch_weather_for_pv


class _StreamlitLogHandler(logging.Handler):
    """Captures log records into a list for display in Streamlit."""

    def __init__(self):
        super().__init__()
        self.records: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(self.format(record))


def energy_generation_solar() -> None:
    """Simulate and visualize solar energy generation from MaStR installations."""
    st.title("Energy Generation from Solar Installations")

    unique_locations = get_cached_unique_locations("solar", str(MASTR_DB_PATH))
    location = st.selectbox(
        "Select city",
        options=unique_locations,
        index=unique_locations.index("Essen") if "Essen" in unique_locations else 0,
    )

    if location and st.button("Simulate Energy Generation"):
        progress_bar = st.progress(0)

        log_handler = _StreamlitLogHandler()
        log_handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S"))
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)

        try:
            start = "2015-07-07 00:00:00"
            end = "2015-07-07 23:45:00"

            with st.status("Running simulation…", expanded=True) as sim_status:
                st.write("Loading MaStR solar data…")
                gdf_solar, city_district = get_cached_mastr_data(location, "solar", str(MASTR_DB_PATH))
                progress_bar.progress(10)

                st.write(f"Correcting power values for {len(gdf_solar)} installations…")
                gdf_solar = revise_power_values(gdf_solar)
                progress_bar.progress(30)

                st.write("Fetching DWD weather data…")
                ref_env = Environment(start=start, end=end)
                start_dt = pd.Timestamp(start).to_pydatetime()
                end_dt = pd.Timestamp(end).to_pydatetime()
                pv_data, _meta = fetch_weather_for_pv(city_district.lat, city_district.lon, start_dt, end_dt)
                ref_env.pv_data = pv_data
                progress_bar.progress(50)

                st.write("Loading / building PV parameters…")
                cache_path = PV_PARAMS_DIR / f"{location}.csv"
                params_df = load_or_build_pv_params(gdf_solar, cache_path)
                progress_bar.progress(60)

                st.write(f"Building {len(params_df)} PV system models…")
                pv_system_mastr = build_pvsystems_from_params(params_df, ref_env)
                progress_bar.progress(75)

                st.write(f"Running time series simulation for {len(params_df)} systems…")
                prepare_pv_time_series_mastr(pv_system_mastr)
                progress_bar.progress(90)

                st.write("Aggregating results…")
                pv_systems_aggregated = aggregate_pv_time_series(pv_system_mastr)
                progress_bar.progress(100)

                sim_status.update(label="✅ Simulation complete!", state="complete", expanded=False)

            # --- Collapse all per-system series into one total ---
            total_series = sum(pv_systems_aggregated.values())
            total_kw: pd.Series = total_series.sum(axis=1)

            # --- Summary metrics ---
            total_capacity_kw = params_df["pdc0_module_W"].sum() / 1000
            peak_gen_kw = float(total_kw.max())

            col1, col2, col3 = st.columns(3)
            col1.metric("PV Systems", len(pv_systems_aggregated))
            col2.metric("Total Capacity", f"{total_capacity_kw:.1f} kW")
            col3.metric("Peak Generation", f"{peak_gen_kw:.2f} kW")

            # --- Aggregated generation time series ---
            fig_ts = px.line(
                x=total_kw.index,
                y=total_kw.values,
                labels={"x": "Time", "y": "Power (kW)"},
                title=f"Aggregated Solar Generation – {location} ({start[:10]})",
            )
            fig_ts.update_layout(xaxis_title="Time", yaxis_title="Power (kW)")
            st.plotly_chart(fig_ts, use_container_width=True)

            # --- Area-level distribution charts ---
            capacity_kw = params_df["pdc0_module_W"] / 1000
            fig_hist = px.histogram(
                capacity_kw,
                nbins=30,
                labels={"value": "System capacity (kW)"},
                title="Distribution of PV System Capacities",
            )
            fig_hist.update_layout(yaxis_title="Number of systems", showlegend=False)

            fig_az = px.histogram(
                params_df,
                x="surface_azimuth",
                nbins=36,
                labels={"surface_azimuth": "Azimuth (°)"},
                title="PV Panel Azimuth Distribution",
            )
            fig_az.update_layout(yaxis_title="Number of systems")

            col_a, col_b = st.columns(2)
            with col_a:
                st.plotly_chart(fig_hist, use_container_width=True)
            with col_b:
                st.plotly_chart(fig_az, use_container_width=True)

            # --- Data corrections log ---
            if log_handler.records:
                with st.expander(f"⚙️ Data corrections ({len(log_handler.records)} log entries)", expanded=False):
                    for msg in log_handler.records:
                        st.text(msg)

        except Exception as e:
            st.error(f"Simulation failed: {e}")
        finally:
            root_logger.removeHandler(log_handler)
