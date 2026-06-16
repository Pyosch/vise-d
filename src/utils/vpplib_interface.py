"""
Interface to vpplib network functions.

These two functions were written for the vpplib dev_refactor branch and
were never released to PyPI.  They are implemented here so the project
works with the standard PyPI vpplib package.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    import pandapower


def assign_assets_to_buses(
    net: "pandapower.pandapowerNet",
    gdf,
    id_col: str | None = None,
) -> dict:
    """Assign each DER asset in *gdf* to the geographically nearest bus in *net*.

    The assignment is done by Euclidean distance in (latitude, longitude) space.
    Bus geodata is taken from ``net.bus_geodata`` when available; otherwise buses
    are placed on a regular grid for a fallback assignment.

    Parameters
    ----------
    net:
        A pandapower network object.
    gdf:
        A GeoDataFrame (or plain DataFrame) whose rows represent individual
        assets.  It must contain latitude / longitude columns or a ``geometry``
        column from which lat/lon can be extracted.  An optional *id_col* column
        is used as the dict key; if absent the DataFrame index is used.
    id_col:
        Name of the column to use as the dictionary key.  Auto-detected from
        common MaStR column names when *None*.

    Returns
    -------
    dict
        ``{asset_id: bus_index}`` mapping.
    """
    import pandapower as pp  # local import so the module stays importable w/o pp

    # ------------------------------------------------------------------ #
    # 1.  Resolve the key column
    # ------------------------------------------------------------------ #
    if id_col is None:
        for candidate in ("EinheitMastrNummer", "MastrNummer", "id", "ID"):
            if candidate in gdf.columns:
                id_col = candidate
                break

    # ------------------------------------------------------------------ #
    # 2.  Extract asset lat/lon
    # ------------------------------------------------------------------ #
    asset_lat: pd.Series | None = None
    asset_lon: pd.Series | None = None

    # Try explicit columns first
    for lat_name in ("Breitengrad", "lat", "latitude", "Latitude"):
        if lat_name in gdf.columns:
            asset_lat = pd.to_numeric(gdf[lat_name], errors="coerce")
            break
    for lon_name in ("Laengengrad", "lon", "longitude", "Longitude"):
        if lon_name in gdf.columns:
            asset_lon = pd.to_numeric(gdf[lon_name], errors="coerce")
            break

    # Fall back to shapely geometry column
    if (asset_lat is None or asset_lon is None) and hasattr(gdf, "geometry"):
        try:
            asset_lat = gdf.geometry.y
            asset_lon = gdf.geometry.x
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # 3.  Extract bus lat/lon from net.bus_geodata
    # ------------------------------------------------------------------ #
    bus_lat: pd.Series | None = None
    bus_lon: pd.Series | None = None

    if hasattr(net, "bus_geodata") and len(net.bus_geodata) > 0:
        geo = net.bus_geodata
        # bus_geodata uses (x, y) == (lon, lat) in pandapower conventions
        if "x" in geo.columns and "y" in geo.columns:
            bus_lon = geo["x"]
            bus_lat = geo["y"]

    # ------------------------------------------------------------------ #
    # 4.  Build the assignment
    # ------------------------------------------------------------------ #
    bus_indices = net.bus.index.tolist()

    if not bus_indices:
        return {}

    assignments: dict = {}

    if (
        asset_lat is not None
        and asset_lon is not None
        and bus_lat is not None
        and bus_lon is not None
        and len(bus_lat) > 0
    ):
        # Vectorised nearest-bus lookup
        b_lat = bus_lat.values.astype(float)
        b_lon = bus_lon.values.astype(float)
        b_idx = bus_lat.index.tolist()

        for row_idx, row in gdf.iterrows():
            a_lat = float(asset_lat.loc[row_idx]) if row_idx in asset_lat.index else np.nan
            a_lon = float(asset_lon.loc[row_idx]) if row_idx in asset_lon.index else np.nan

            if np.isnan(a_lat) or np.isnan(a_lon):
                # No geodata → assign to first candidate bus
                nearest = bus_indices[0]
            else:
                dists = (b_lat - a_lat) ** 2 + (b_lon - a_lon) ** 2
                nearest = b_idx[int(np.argmin(dists))]

            key = row[id_col] if id_col and id_col in gdf.columns else row_idx
            assignments[key] = nearest
    else:
        # Fallback: distribute assets round-robin across all buses
        # (used when neither assets nor buses have geodata)
        for i, (row_idx, row) in enumerate(gdf.iterrows()):
            key = row[id_col] if id_col and id_col in gdf.columns else row_idx
            assignments[key] = bus_indices[i % len(bus_indices)]

    return assignments


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


__all__ = ["assign_assets_to_buses", "build_timeseries_net"]
