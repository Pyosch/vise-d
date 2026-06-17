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


__all__ = ["build_timeseries_net"]
