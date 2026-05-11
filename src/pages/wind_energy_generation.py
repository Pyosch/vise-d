"""
Wind energy generation simulation page.

Simulates wind energy generation using MaStR data and vpplib/windpowerlib models.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import logging
import pandas as pd
import pvlib
import streamlit as st
import plotly.express as px
from vpplib.environment import Environment
from src.data_layer.cache import get_cached_unique_locations, get_cached_mastr_data
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


def wind_energy_generation() -> None:
    """Simulate and visualize wind energy generation from MaStR installations."""
    st.title("Energy Generation from Wind Installations")

    unique_locations = get_cached_unique_locations("wind", str(MASTR_DB_PATH))
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
                st.write("Loading MaStR wind data…")
                gdf_wind, city_district = get_cached_mastr_data(location, "wind", str(MASTR_DB_PATH))
                progress_bar.progress(10)

                st.write(f"Matching turbine types for {len(gdf_wind)} installations…")
                gdf_wind = wind_turbine_matching(gdf_wind)
                progress_bar.progress(30)

                st.write("Fetching PVGIS weather data…")
                ref_env = Environment(start=start, end=end)
                test_data, _meta, _inputs = pvlib.iotools.get_pvgis_hourly(
                    city_district.centroid.y,
                    city_district.centroid.x,
                    start=pd.to_datetime(start),
                    end=pd.to_datetime(end),
                    raddatabase="PVGIS-SARAH2",
                    components=True,
                    surface_tilt=0,
                    surface_azimuth=0,
                    outputformat="json",
                    usehorizon=True,
                    userhorizon=None,
                    pvcalculation=False,
                    peakpower=None,
                    pvtechchoice="crystSi",
                    mountingplace="free",
                    loss=0,
                    trackingtype=0,
                    optimal_surface_tilt=False,
                    optimalangles=False,
                    url="https://re.jrc.ec.europa.eu/api/v5_2/",
                    map_variables=True,
                    timeout=30,
                )
                progress_bar.progress(50)

                st.write("Transforming weather data to 15-min resolution…")
                filtered = test_data[["wind_speed", "temp_air"]].copy()
                filtered["temp_air"] = filtered["temp_air"] + 273.15
                filtered["roughness_length"] = 0.15
                filtered["pressure"] = 101325
                filtered = filtered[["wind_speed", "pressure", "temp_air", "roughness_length"]]
                filtered = filtered.rename(columns={"temp_air": "temperature"})
                filtered.columns = pd.MultiIndex.from_arrays(
                    [filtered.columns, ["10", "0", "2", "0"]]
                )
                ref_env.wind_data = filtered.resample("15T").mean().interpolate(limit_direction="both")
                progress_bar.progress(65)

                st.write(f"Initialising {len(gdf_wind)} wind turbine models…")
                windturbines_dict = init_windturbines_mastr(gdf_wind, environment=ref_env)
                progress_bar.progress(80)

                st.write(f"Running time series simulation for {len(windturbines_dict)} turbines…")
                prepare_wind_time_series_mastr(windturbines_dict)
                progress_bar.progress(90)

                st.write("Aggregating results…")
                all_series = [wt.timeseries for wt in windturbines_dict.values()]
                total_kw: pd.Series = pd.concat(all_series, axis=1).sum(axis=1)
                progress_bar.progress(100)

                sim_status.update(label="✅ Simulation complete!", state="complete", expanded=False)

            # --- Summary metrics ---
            total_capacity_kw = float(gdf_wind["Nettonennleistung"].sum())
            peak_gen_kw = float(total_kw.max())

            col1, col2, col3 = st.columns(3)
            col1.metric("Wind Turbines", len(windturbines_dict))
            col2.metric("Total Capacity", f"{total_capacity_kw:.1f} kW")
            col3.metric("Peak Generation", f"{peak_gen_kw:.2f} kW")

            # --- Aggregated generation time series ---
            fig_ts = px.line(
                x=total_kw.index,
                y=total_kw.values,
                labels={"x": "Time", "y": "Power (kW)"},
                title=f"Aggregated Wind Generation – {location} ({start[:10]})",
            )
            fig_ts.update_layout(xaxis_title="Time", yaxis_title="Power (kW)")
            st.plotly_chart(fig_ts, use_container_width=True)

            # --- Distribution charts ---
            fig_cap = px.histogram(
                gdf_wind["Nettonennleistung"],
                nbins=20,
                labels={"value": "Rated power (kW)"},
                title="Distribution of Wind Turbine Capacities",
            )
            fig_cap.update_layout(yaxis_title="Number of turbines", showlegend=False)

            fig_hub = px.histogram(
                gdf_wind,
                x="Nabenhoehe",
                nbins=20,
                labels={"Nabenhoehe": "Hub height (m)"},
                title="Wind Turbine Hub Height Distribution",
            )
            fig_hub.update_layout(yaxis_title="Number of turbines")

            col_a, col_b = st.columns(2)
            with col_a:
                st.plotly_chart(fig_cap, use_container_width=True)
            with col_b:
                st.plotly_chart(fig_hub, use_container_width=True)

            # --- Simulation log ---
            if log_handler.records:
                with st.expander(f"⚙️ Simulation log ({len(log_handler.records)} entries)", expanded=False):
                    for msg in log_handler.records:
                        st.text(msg)

        except Exception as e:
            st.error(f"Simulation failed: {e}")
        finally:
            root_logger.removeHandler(log_handler)
