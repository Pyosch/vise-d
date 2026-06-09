"""
Thermal storage settings and simulation page.

Provides configuration form and simulation for thermal energy storage systems.
The thermal demand is derived from DWD temperatures via
``UserProfile.get_thermal_energy_demand()`` (vpplib), analogous to the heat pump
page and the vpplib example ``demo_thermal_energy_storage.py``.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Opus 4.8)
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Opus 4.8)"]

from datetime import date, timedelta

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from vpplib.environment import Environment
from vpplib.user_profile import UserProfile
from vpplib.thermal_energy_storage import ThermalEnergyStorage
from vpplib.heat_pump import HeatPump

try:
    import osmnx as ox
    _HAS_OSMNX = True
except Exception:
    _HAS_OSMNX = False


@st.cache_data
def _geocode(city: str) -> tuple[float, float]:
    lat, lon = ox.geocode(city)
    return float(lat), float(lon)


@st.cache_data(show_spinner=False)
def _reference_consumerfactor(
    lat: float, lon: float, yearly_demand: float, building_type: str, t_0: float
) -> float:
    """Kalibriert den consumerfactor über ein volles Referenzjahr.

    Die SigLinDe-Methodik skaliert den Bedarf so, dass die Summe über den
    übergebenen Zeitraum dem Jahresbedarf entspricht. Damit ein kurzer
    Simulationszeitraum (z. B. eine Woche) nicht den gesamten Jahresbedarf
    tragen muss, wird der Skalierungsfaktor einmalig über ein ganzes Jahr
    DWD-Beobachtungsdaten bestimmt (vgl. demo_thermal_energy_storage.py) und
    anschließend an das Fenster-Profil übergeben.
    """
    yesterday = date.today() - timedelta(days=1)
    ref_start = yesterday.replace(year=yesterday.year - 1)
    ref_env = Environment(
        timebase=60,
        start=f"{ref_start} 00:00:00",
        end=f"{yesterday} 23:00:00",
        time_freq="60 min",
        surpress_output_globally=True,
    )
    ref_env.get_dwd_mean_temp_hours(lat=lat, lon=lon, min_quality_per_parameter=10)
    ref_env.get_dwd_mean_temp_days(lat=lat, lon=lon, min_quality_per_parameter=10)
    ref_env.mean_temp_quarter_hours = ref_env.mean_temp_hours.resample("15 Min").interpolate()
    ref_profile = UserProfile(
        identifier=None, latitude=lat, longitude=lon,
        thermal_energy_demand_yearly=yearly_demand,
        mean_temp_days=ref_env.mean_temp_days,
        mean_temp_hours=ref_env.mean_temp_hours,
        mean_temp_quarter_hours=ref_env.mean_temp_quarter_hours,
        building_type=building_type, comfort_factor=None, t_0=t_0,
    )
    ref_profile.get_thermal_energy_demand()
    return float(ref_profile.consumerfactor)


# Defaults des Wärmeerzeugers (Wärmepumpe) — entsprechen demo_thermal_energy_storage.py.
_HP_GEN_DEFAULTS = {
    "heat_pump_type": "Air",
    "heat_sys_temp": 60.0,
    "el_power": 5.0,
    "th_power": 8.0,
    "ramp_up_time": 1.0,    # Zeitschritte
    "ramp_down_time": 1.0,  # Zeitschritte
    "min_runtime": 1.0,     # Zeitschritte
    "min_stop_time": 2.0,   # Zeitschritte
}

_BUILDING_TYPES = ["DE_HEF33", "DE_HEF34", "DE_HMF33", "DE_HMF34", "DE_GKO34"]
_BUILDING_HELP = (
    "SigLinDe-Gebäudeklassifikation (BDEW):\n\n"
    "**HEF** = Einfamilienhaus · **HMF** = Mehrfamilienhaus · **GKO** = Gewerbe/Kommunal\n\n"
    "**33** = Altbau (vor WSchVO 1977, schlechte Dämmung)\n\n"
    "**34** = Neubau/modernisiert (nach WSchVO 1984, gute Dämmung)"
)


def thermal_storage_settings() -> None:
    """Configure and simulate thermal energy storage system."""
    if "thermal_storage_settings" not in st.session_state:
        st.session_state["thermal_storage_settings"] = {
            "target temperature": 60,          # 60°C for domestic hot water
            "minimum temperature": 40,         # 40°C minimum usable temperature
            "Current Temperature": 50,         # 50°C starting temperature
            "hysteresis": 5,                   # 5°C control band
            "mass": 300,                       # 300 kg (typical 300L water tank)
            "cp": 4.18,                        # 4.18 kJ/kg°C (specific heat of water)
            "thermal energy loss per day": 0.13,  # Anteil/Tag (vpplib erwartet 0–1)
            "timebase_minutes": 15,            # consistent with other components
        }
    if "thermal_generator_settings" not in st.session_state:
        st.session_state["thermal_generator_settings"] = dict(_HP_GEN_DEFAULTS)

    st.title("🌡️ Thermischer Speicher")
    from src.content.page_descriptions import render_page_description
    render_page_description("thermal_storage")

    # ── Standort ──────────────────────────────────────────────────────────────
    st.subheader("Standort")
    if not _HAS_OSMNX:
        st.error("osmnx ist nicht installiert — Geocoding nicht verfügbar.")
        return

    city_input = st.text_input("Ort (Stadtname)", value="Köln", key="ts_cfg_city")
    lat: float | None = None
    lon: float | None = None
    if city_input:
        try:
            lat, lon = _geocode(city_input)
            st.caption(f"Koordinaten: {lat:.4f}°N, {lon:.4f}°E")
        except Exception as e:
            st.error(f"Geocoding fehlgeschlagen: {e}")
            return
    if lat is None or lon is None:
        return

    # ── Zeitraum ──────────────────────────────────────────────────────────────
    st.subheader("Zeitraum")
    default_end = date.today() - timedelta(days=1)
    default_start = default_end - timedelta(days=6)
    col_s, col_e = st.columns(2)
    date_start = col_s.date_input("Von", value=default_start, key="ts_cfg_start")
    date_end = col_e.date_input("Bis", value=default_end, key="ts_cfg_end")
    if (date_end - date_start).days < 0:
        st.error("Enddatum muss nach dem Startdatum liegen.")
        return

    # ── Gebäude & Wärmebedarf ─────────────────────────────────────────────────
    with st.expander("🏠 Gebäude & Wärmebedarf"):
        yearly_thermal_energy_demand = st.number_input(
            "Jährlicher Wärmebedarf (kWh)",
            min_value=1000.0, max_value=50000.0, value=12500.0, step=500.0,
            key="ts_yearly_demand",
        )
        building_type = st.selectbox(
            "Gebäudetyp", options=_BUILDING_TYPES, index=0,
            help=_BUILDING_HELP, key="ts_building_type",
        )
        t_0 = st.number_input(
            "Heizgrenztemperatur (°C)",
            min_value=0.0, max_value=70.0, value=40.0, step=0.5,
            help="Referenztemperatur des SigLinDe-Modells für den Wärmebedarf.",
            key="ts_t_0",
        )

    # ── Speicher-Einstellungen ────────────────────────────────────────────────
    with st.container():
        st.header("Einstellungen Thermischer Speicher")

        st.markdown("**Zieltemperatur**")
        target_temperature = st.number_input(
            "Zieltemperatur eingeben (°C)",
            min_value=0.0,
            value=float(st.session_state["thermal_storage_settings"]["target temperature"]),
            placeholder="z. B. 60 °C",
            key="target_temperature",
        )

        st.markdown("**Minimale Temperatur**")
        minimum_temperature = st.number_input(
            "Minimale Temperatur eingeben (°C)",
            min_value=0.0,
            value=float(st.session_state["thermal_storage_settings"]["minimum temperature"]),
            placeholder="z. B. 40 °C",
            key="minimum_temperature",
        )

        st.markdown("**Hysterese**")
        hysteresis = st.number_input(
            "Hysterese eingeben (°C)",
            min_value=0.0,
            value=float(st.session_state["thermal_storage_settings"]["hysteresis"]),
            placeholder="z. B. 5 °C",
            key="hysteresis",
        )

        st.markdown("**Aktuelle Temperatur**")
        current_temperature = st.number_input(
            "Aktuelle Temperatur eingeben (°C)",
            min_value=0.0,
            value=float(target_temperature - hysteresis),
            placeholder="z. B. 50 °C",
            key="current_temperature",
        )

        st.markdown("**Masse**")
        mass = st.number_input(
            "Masse eingeben (kg)",
            min_value=0.0,
            value=float(st.session_state["thermal_storage_settings"]["mass"]),
            placeholder="z. B. 300 kg",
            key="mass",
        )

        st.markdown("**Spezifische Wärmekapazität**")
        cp = st.number_input(
            "Spezifische Wärmekapazität eingeben (kJ/kg°C)",
            min_value=0.0,
            value=float(st.session_state["thermal_storage_settings"]["cp"]),
            placeholder="z. B. 4,18 kJ/kg°C",
            key="cp",
        )

        st.markdown("**Thermischer Energieverlust pro Tag**")
        thermal_energy_loss_per_day = st.number_input(
            "Thermischer Energieverlust pro Tag (Anteil 0–1)",
            min_value=0.0,
            max_value=1.0,
            value=float(st.session_state["thermal_storage_settings"]["thermal energy loss per day"]),
            step=0.01,
            help="Anteil der gespeicherten Energie, der pro Tag verloren geht (z. B. 0.13 = 13 %/Tag).",
            key="thermal_energy_loss_per_day",
        )

        st.markdown("**Zeitbasis (Minuten)**")
        timebase_minutes = st.number_input(
            "Zeitbasis eingeben (Minuten)",
            min_value=1.0,
            value=float(st.session_state["thermal_storage_settings"]["timebase_minutes"]),
            placeholder="z. B. 15 Minuten",
            key="timebase_minutes",
        )

        if st.button("Einstellungen speichern", key="submit_thermal_storage_settings"):
            st.session_state["thermal_storage_settings"] = {
                "target temperature": target_temperature,
                "minimum temperature": minimum_temperature,
                "Current Temperature": current_temperature,
                "hysteresis": hysteresis,
                "mass": mass,
                "cp": cp,
                "thermal energy loss per day": thermal_energy_loss_per_day,
                "timebase_minutes": timebase_minutes,
            }
            st.success("Einstellungen des thermischen Speichers erfolgreich aktualisiert!")

    # ── Wärmeerzeuger (Wärmepumpe) ────────────────────────────────────────────
    # Der Speicher wird – wie im vpplib-Beispiel demo_thermal_energy_storage.py –
    # von einer Wärmepumpe beladen (kompatibel mit ThermalEnergyStorage.operate_storage).
    _ts_help = "In Zeitschritten (1 Zeitschritt = Zeitbasis)."
    with st.expander("♨️ Wärmeerzeuger (Wärmepumpe)"):
        gen = st.session_state["thermal_generator_settings"]
        hp_type_label = st.selectbox(
            "Wärmepumpentyp", options=["Luft", "Erde"],
            index=0 if gen["heat_pump_type"] == "Air" else 1, key="ts_hp_type",
        )
        hp_type = {"Luft": "Air", "Erde": "Ground"}[hp_type_label]
        hp_heat_sys_temp = st.number_input(
            "Vorlauftemperatur (°C)", min_value=0.0, max_value=100.0,
            value=float(gen["heat_sys_temp"]), step=1.0, key="ts_hp_sys_temp",
        )
        hp_el_power = st.number_input(
            "Elektrische Leistung (kW)", min_value=0.0,
            value=float(gen["el_power"]), step=0.5, key="ts_hp_el_power",
        )
        hp_th_power = st.number_input(
            "Thermische Leistung (kW)", min_value=0.0,
            value=float(gen["th_power"]), step=0.5, key="ts_hp_th_power",
        )
        hp_ramp_up = st.number_input(
            "Anlaufzeit (Zeitschritte)", min_value=0.0,
            value=float(gen["ramp_up_time"]), step=0.1, help=_ts_help, key="ts_hp_ramp_up",
        )
        hp_ramp_down = st.number_input(
            "Abschaltzeit (Zeitschritte)", min_value=0.0,
            value=float(gen["ramp_down_time"]), step=0.1, help=_ts_help, key="ts_hp_ramp_down",
        )
        hp_min_run = st.number_input(
            "Mindestlaufzeit (Zeitschritte)", min_value=0.0,
            value=float(gen["min_runtime"]), step=1.0, help=_ts_help, key="ts_hp_min_run",
        )
        hp_min_stop = st.number_input(
            "Mindeststillstandszeit (Zeitschritte)", min_value=0.0,
            value=float(gen["min_stop_time"]), step=1.0, help=_ts_help, key="ts_hp_min_stop",
        )
        if st.button("Einstellungen speichern", key="submit_thermal_generator_settings"):
            st.session_state["thermal_generator_settings"] = {
                "heat_pump_type": hp_type,
                "heat_sys_temp": hp_heat_sys_temp,
                "el_power": hp_el_power,
                "th_power": hp_th_power,
                "ramp_up_time": hp_ramp_up,
                "ramp_down_time": hp_ramp_down,
                "min_runtime": hp_min_run,
                "min_stop_time": hp_min_stop,
            }
            st.success("Wärmeerzeuger-Einstellungen erfolgreich aktualisiert!")

    # ── Tabelle der gespeicherten Einstellungen ───────────────────────────────
    if "thermal_storage_settings" in st.session_state:
        s = st.session_state["thermal_storage_settings"]
        data = {
            "Größe": [
                "Zieltemperatur", "Minimale Temperatur", "Aktuelle Temperatur",
                "Hysterese", "Masse", "Spezifische Wärmekapazität",
                "Thermischer Energieverlust pro Tag", "Zeitbasis (Minuten)",
            ],
            "Wert": [
                s["target temperature"], s["minimum temperature"], s["Current Temperature"],
                s["hysteresis"], s["mass"], s["cp"],
                s["thermal energy loss per day"], s["timebase_minutes"],
            ],
        }
        df = pd.DataFrame(data)
        df["Wert"] = df["Wert"].apply(lambda v: f"{float(v):.1f}")
        st.subheader("Tabelle der Speichereinstellungen")
        styled_df = df.style.set_properties(**{
            'text-align': 'left', 'font-size': '14px', 'padding': '10px',
            'border': '1px solid #ddd', 'background-color': '#f9f9f9',
        }).set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#4CAF50'), ('color', 'white'), ('font-weight', 'bold'), ('text-align', 'left'), ('padding', '10px'), ('border', '1px solid #ddd')]},
            {'selector': 'td', 'props': [('border', '1px solid #ddd')]},
        ])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

    # ── Simulation ────────────────────────────────────────────────────────────
    with st.form(key="thermal_storage_simulation_form"):
        thermal_simulation_button = st.form_submit_button("Thermischen Speicher simulieren")

        if thermal_simulation_button:
            ts_settings = st.session_state["thermal_storage_settings"]
            timebase = int(ts_settings["timebase_minutes"])
            start = f"{date_start} 00:00:00"
            end = f"{date_end} 23:45:00"

            # Wetterbasierter Wärmebedarf (vpplib-Beispielmuster):
            # DWD-Temperaturen → UserProfile.get_thermal_energy_demand().
            with st.spinner("Wetterdaten werden abgerufen…"):
                try:
                    env = Environment(
                        timebase=timebase, start=start, end=end,
                        time_freq=f"{timebase} min", surpress_output_globally=False,
                    )
                    env.get_dwd_mean_temp_hours(lat=lat, lon=lon, min_quality_per_parameter=10)
                    env.get_dwd_mean_temp_days(lat=lat, lon=lon, min_quality_per_parameter=10)
                    env.mean_temp_quarter_hours = (
                        env.mean_temp_hours.resample(f"{timebase} Min").interpolate()
                    )
                except Exception as e:
                    st.error(f"❌ Fehler beim Abrufen der Wetterdaten: {e}")
                    return

            with st.spinner("Referenzjahr wird kalibriert (DWD-Daten, einmalig je Standort)…"):
                try:
                    consumerfactor = _reference_consumerfactor(
                        lat, lon, float(yearly_thermal_energy_demand), building_type, float(t_0)
                    )
                except Exception as e:
                    st.error(f"❌ Fehler bei der Referenzjahr-Kalibrierung: {e}")
                    return

            with st.spinner("Wärmebedarf wird aus Temperaturen berechnet…"):
                try:
                    # consumerfactor aus dem Referenzjahr übergeben, damit der kurze
                    # Zeitraum nicht den gesamten Jahresbedarf tragen muss.
                    user_profile = UserProfile(
                        identifier=None, latitude=lat, longitude=lon,
                        thermal_energy_demand_yearly=yearly_thermal_energy_demand,
                        mean_temp_days=env.mean_temp_days,
                        mean_temp_hours=env.mean_temp_hours,
                        mean_temp_quarter_hours=env.mean_temp_quarter_hours,
                        building_type=building_type, comfort_factor=None, t_0=t_0,
                        consumerfactor=consumerfactor,
                    )
                    user_profile.get_thermal_energy_demand()
                    thermal_demand_series = user_profile.thermal_energy_demand
                except Exception as e:
                    st.error(f"❌ Fehler bei der Wärmebedarfsberechnung: {e}")
                    return

            # Wärmeerzeuger (Wärmepumpe) mit gespeicherten Formular-Parametern
            gen_settings = st.session_state["thermal_generator_settings"]
            generator = HeatPump(
                identifier="heatpump_1", unit="kW", environment=env,
                thermal_energy_demand=thermal_demand_series,
                heat_pump_type=gen_settings["heat_pump_type"],
                heat_sys_temp=gen_settings["heat_sys_temp"],
                el_power=gen_settings["el_power"],
                th_power=gen_settings["th_power"],
                ramp_up_time=gen_settings["ramp_up_time"],
                ramp_down_time=gen_settings["ramp_down_time"],
                min_runtime=gen_settings["min_runtime"],
                min_stop_time=gen_settings["min_stop_time"],
            )

            # Thermischer Speicher mit Formular-Parametern.
            # initial_temperature setzt Temperatur und Ladezustand konsistent;
            # raise_on_undersupply=False lässt die Simulation bei Unterdeckung
            # weiterlaufen (statt Abbruch) und setzt stattdessen ein Flag.
            tes = ThermalEnergyStorage(
                unit="kW", identifier="thermal_storage_1", environment=env,
                target_temperature=ts_settings["target temperature"],
                min_temperature=ts_settings["minimum temperature"],
                hysteresis=ts_settings["hysteresis"],
                mass=ts_settings["mass"],
                cp=ts_settings["cp"],
                thermal_energy_loss_per_day=ts_settings["thermal energy loss per day"],
                initial_temperature=ts_settings["Current Temperature"],
                raise_on_undersupply=False,
            )
            st.session_state["thermal_storage"] = tes

            # Über den Bedarfs-Index iterieren (nicht über generator.timeseries.index):
            # Beim Resampling der stündlichen DWD-Temperaturen auf das Zeitschritt-
            # Raster endet der Wärmebedarf ggf. einige Schritte vor dem env-Raster.
            # Der Bedarfs-Index ist damit maßgeblich; beide Zeitreihen werden darauf
            # ausgerichtet, sodass operate_storage jeden Wert findet (kein KeyError).
            sim_index = thermal_demand_series.index
            generator.timeseries = pd.DataFrame(
                columns=["thermal_energy_output", "cop", "el_demand"], index=sim_index
            )
            tes.timeseries = pd.DataFrame(columns=["temperature"], index=sim_index)

            st.info("⏳ Betrieb des thermischen Speichers wird simuliert…")
            progress_bar = st.progress(0)
            total_steps = len(sim_index)
            for idx, timestamp in enumerate(sim_index):
                tes.operate_storage(timestamp, generator)
                if idx % 50 == 0:
                    progress_bar.progress(idx / total_steps)
            progress_bar.progress(1.0)
            if getattr(tes, "undersupplied", False):
                st.warning(
                    "⚠️ Der Wärmeerzeuger konnte die Mindesttemperatur im gewählten "
                    "Zeitraum nicht durchgehend halten. Die Ergebnisse sind dennoch "
                    "verfügbar — ggf. thermische Leistung erhöhen, den Energieverlust "
                    "senken oder einen wärmeren Zeitraum wählen."
                )
            st.success("✅ Simulation abgeschlossen!")

            # Ergebnisse
            st.write("**Temperatur des thermischen Speichers (erste 10 Zeitschritte):**")
            st.dataframe(st.session_state["thermal_storage"].timeseries.head(10))

            st.write("**Elektrischer Bedarf des Wärmeerzeugers (erste 10 Zeitschritte):**")
            if hasattr(generator.timeseries, 'el_demand'):
                st.dataframe(generator.timeseries[['el_demand']].head(10))
            else:
                st.dataframe(generator.timeseries.head(10))

            # Temperaturverlauf
            fig_temp, ax_temp = plt.subplots(figsize=(16, 6))
            st.session_state["thermal_storage"].timeseries.plot(ax=ax_temp, color='red')
            ax_temp.axhline(y=ts_settings["target temperature"], color='green', linestyle='--', label='Zieltemperatur')
            ax_temp.axhline(y=ts_settings["minimum temperature"], color='blue', linestyle='--', label='Minimale Temperatur')
            ax_temp.set_title("Temperaturverlauf des thermischen Speichers")
            ax_temp.set_xlabel("Zeit")
            ax_temp.set_ylabel("Temperatur (°C)")
            ax_temp.legend()
            ax_temp.grid(True, alpha=0.3)
            plt.tight_layout()
            st.pyplot(fig_temp)

            # Elektrischer Bedarf des Wärmeerzeugers
            fig_demand, ax_demand = plt.subplots(figsize=(16, 6))
            if hasattr(generator.timeseries, 'el_demand'):
                generator.timeseries['el_demand'].plot(ax=ax_demand, color='orange')
            else:
                generator.timeseries.plot(ax=ax_demand, color='orange')
            ax_demand.set_title("Elektrischer Bedarf des Wärmeerzeugers")
            ax_demand.set_xlabel("Zeit")
            ax_demand.set_ylabel("Elektrische Leistung (kW)")
            ax_demand.grid(True, alpha=0.3)
            plt.tight_layout()
            st.pyplot(fig_demand)
