"""
Solar energy generation simulation page.

Simulates solar energy generation using MaStR data and vpplib models.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import logging
import streamlit as st
import matplotlib.pyplot as plt
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
                ref_env.get_dwd_pv_data(lat=city_district.lat, lon=city_district.lon)
                progress_bar.progress(50)

                st.write("Loading / building PV parameters…")
                cache_path = PV_PARAMS_DIR / f"{location}.csv"
                params_df = load_or_build_pv_params(gdf_solar, cache_path)
                progress_bar.progress(60)

                st.write(f"Building {len(params_df)} PV system models…")
                pv_system_mastr = build_pvsystems_from_params(params_df, ref_env)
                progress_bar.progress(75)

                st.write("Running time series simulation…")
                prepare_pv_time_series_mastr(pv_system_mastr)
                progress_bar.progress(90)

                st.write("Aggregating results…")
                pv_systems_aggregated = aggregate_pv_time_series(pv_system_mastr)
                progress_bar.progress(100)

                sim_status.update(label="✅ Simulation complete!", state="complete", expanded=False)

            # --- Summary metrics ---
            total_capacity_kw = params_df["pdc0_module_W"].sum() / 1000
            all_series = [ts for ts in pv_systems_aggregated.values() if hasattr(ts, "max")]
            peak_gen_kw = max((ts.max().max() for ts in all_series), default=0.0)

            col1, col2, col3 = st.columns(3)
            col1.metric("PV Systems", len(pv_systems_aggregated))
            col2.metric("Total Capacity", f"{total_capacity_kw:.1f} kW")
            col3.metric("Peak Generation", f"{peak_gen_kw:.2f} kW")

            # --- Chart ---
            fig, ax = plt.subplots(figsize=(10, 6))
            for name, pv_system in pv_systems_aggregated.items():
                if hasattr(pv_system, "plot"):
                    pv_system.plot(ax=ax, label=name)
                else:
                    try:
                        ax.plot(pv_system, label=name)
                    except Exception as plot_error:
                        st.warning(f"Could not plot {name}: {plot_error}")
            ax.set_title(f"Solar Energy Generation in {location} ({start} to {end})")
            ax.set_xlabel("Time")
            ax.set_ylabel("Power (kW)")
            ax.legend()
            ax.grid(True)
            st.pyplot(fig)
            plt.close(fig)

            # --- Data corrections log ---
            if log_handler.records:
                with st.expander(f"⚙️ Data corrections ({len(log_handler.records)} log entries)", expanded=False):
                    for msg in log_handler.records:
                        st.text(msg)

        except Exception as e:
            st.error(f"Simulation failed: {e}")
        finally:
            root_logger.removeHandler(log_handler)
