"""
Interface to vpplib network functions.

This function was written for the vpplib dev_refactor branch and was never
released to PyPI.  It is implemented here so the project works with the
standard PyPI vpplib package.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    import pandapower


def build_timeseries_net(
    net: "pandapower.pandapowerNet",
    profiles: dict[str, pd.Series | pd.DataFrame],
    time_steps: pd.DatetimeIndex | None = None,
) -> "pandapower.pandapowerNet":
    """Attach time-series profiles to a pandapower network via ConstControl.

    Each key in *profiles* must match either ``net.sgen.name`` or
    ``net.load.name``.  The profile values are expected in MW.

    Parameters
    ----------
    net:
        A pandapower network (modified **in place**).
    profiles:
        ``{element_name: timeseries}`` where the series contains power in MW.
    time_steps:
        Optional explicit time index.  Derived from the first profile when
        *None*.

    Returns
    -------
    pandapower.pandapowerNet
        The same *net* object with controllers attached.
    """
    import pandapower as pp
    from pandapower.control import ConstControl
    from pandapower.timeseries import DFData

    if time_steps is None and profiles:
        first = next(iter(profiles.values()))
        if isinstance(first, pd.DataFrame):
            time_steps = first.index
        else:
            time_steps = first.index

    for name, ts in profiles.items():
        if isinstance(ts, pd.DataFrame):
            ts = ts.iloc[:, 0]

        ts_df = ts.to_frame(name=name)
        ds = DFData(ts_df)

        # Try sgen first, then load
        sgen_mask = net.sgen["name"] == name if len(net.sgen) > 0 else pd.Series([], dtype=bool)
        load_mask = net.load["name"] == name if len(net.load) > 0 else pd.Series([], dtype=bool)

        if sgen_mask.any():
            idx = net.sgen.index[sgen_mask].tolist()
            ConstControl(net, element="sgen", variable="p_mw",
                         element_index=idx, data_source=ds, profile_name=[name])
        elif load_mask.any():
            idx = net.load.index[load_mask].tolist()
            ConstControl(net, element="load", variable="p_mw",
                         element_index=idx, data_source=ds, profile_name=[name])
        # If neither matches, the profile is silently skipped

    return net


def reference_consumerfactor(
    lat: float,
    lon: float,
    yearly_demand: float,
    building_type: str,
    t_0: float,
) -> float:
    """Calibrate the SigLinDe ``consumerfactor`` over a full reference year.

    vpplib's ``UserProfile.get_thermal_energy_demand`` (SigLinDe) scales the
    thermal demand so its sum over the supplied period equals the yearly
    demand.  For a short simulation window (e.g. one week) that would force the
    entire annual demand into a few days and yields an unusable profile.  To
    avoid this, the scaling factor (``consumerfactor``) is calibrated once over
    a full year of DWD observation data and then handed to the window profile
    via ``UserProfile(..., consumerfactor=...)``.

    Mirrors the reference-year step already used by the Netzmodell and
    Thermischer-Speicher pages (cf. ``demo_thermal_energy_storage.py`` in
    vpplib).  vpplib imports are kept inside the function so importing this
    module stays cheap (lazy-import discipline).

    Args:
        lat: Latitude of the location in decimal degrees.
        lon: Longitude of the location in decimal degrees.
        yearly_demand: Yearly thermal energy demand in kWh.
        building_type: SigLinDe building type (e.g. ``"DE_HEF33"``).
        t_0: SigLinDe reference/heating-limit temperature in °C.

    Returns:
        The calibrated ``consumerfactor`` for the location and building type.
    """
    from datetime import date, timedelta

    from vpplib.environment import Environment
    from vpplib.user_profile import UserProfile

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
        identifier=None,
        latitude=lat,
        longitude=lon,
        thermal_energy_demand_yearly=yearly_demand,
        mean_temp_days=ref_env.mean_temp_days,
        mean_temp_hours=ref_env.mean_temp_hours,
        mean_temp_quarter_hours=ref_env.mean_temp_quarter_hours,
        building_type=building_type,
        comfort_factor=None,
        t_0=t_0,
    )
    ref_profile.get_thermal_energy_demand()
    return float(ref_profile.consumerfactor)


__all__ = ["build_timeseries_net", "reference_consumerfactor"]
