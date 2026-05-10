import numpy as np
import pandas as pd

import pandapower as pn


def Simbench_multiplier(net, base_profile_name="H0-A", amplitude=0.35, phase_shift=0):
    """Create a simple demand multiplier table for the current loads.

    The table is time-indexed and can be applied to the network's base p_mw
    values without mutating the network until the update step.
    """
    if net is None or not hasattr(net, "load") or net.load.empty:
        return pd.DataFrame()

    time_index = pd.RangeIndex(0, 96, name="timestep")
    base_curve = 1.0 + amplitude * np.sin(
        np.linspace(0, 2 * np.pi, len(time_index), endpoint=False) + phase_shift
    )
    base_curve = pd.Series(base_curve, index=time_index, name=base_profile_name)

    load_names = (
        net.load["name"].fillna("").astype(str)
        if "name" in net.load.columns
        else pd.Series(net.load.index.astype(str), index=net.load.index)
    )

    category_lookup = {}
    for idx, load_name in load_names.items():
        name_lower = load_name.lower()
        if any(token in name_lower for token in ["ev", "car"]):
            category_lookup[idx] = "EV"
        elif any(token in name_lower for token in ["heat", "hp", "pump"]):
            category_lookup[idx] = "HeatPump"
        elif any(token in name_lower for token in ["industry", "industrial"]):
            category_lookup[idx] = "Industry"
        elif any(token in name_lower for token in ["office", "commerce", "shop", "store"]):
            category_lookup[idx] = "Commercial"
        else:
            category_lookup[idx] = "Residential"

    profile_shapes = {
        "Residential": base_curve,
        "Commercial": 0.95 + 0.25 * np.cos(
            np.linspace(0, 2 * np.pi, len(time_index), endpoint=False)
        ),
        "Industry": 1.0 + 0.10 * np.sin(
            np.linspace(0, 4 * np.pi, len(time_index), endpoint=False)
        ),
        "EV": 0.7 + 0.55 * np.maximum(
            0,
            np.sin(
                np.linspace(-np.pi / 2, 3 * np.pi / 2, len(time_index), endpoint=False)
            ),
        ),
        "HeatPump": 0.85 + 0.35 * np.maximum(
            0,
            np.cos(np.linspace(0, 2 * np.pi, len(time_index), endpoint=False)),
        ),
    }

    multiplier_table = pd.DataFrame(index=time_index)
    for load_idx in net.load.index:
        category = category_lookup.get(load_idx, "Residential")
        multiplier_table[load_idx] = pd.Series(profile_shapes[category], index=time_index)

    multiplier_table.index.name = "timestep"
    return multiplier_table


def apply_simbench_multiplier_to_loads(net, multiplier_table, timestep, base_p_mw=None):
    """Apply one timestep of multipliers to the current network loads."""
    if net is None or multiplier_table is None or multiplier_table.empty:
        return net, base_p_mw

    if timestep not in multiplier_table.index:
        return net, base_p_mw

    if base_p_mw is None:
        base_p_mw = net.load["p_mw"].copy()

    for load_idx in net.load.index:
        if load_idx not in multiplier_table.columns:
            continue
        factor = float(multiplier_table.loc[timestep, load_idx])
        net.load.at[load_idx, "p_mw"] = float(base_p_mw.loc[load_idx]) * factor

    return net, base_p_mw


def run_simbench_load_timeseries(net, multiplier_table, base_p_mw=None):
    """Run a simple PF timeseries using the current network loads and multipliers."""
    if net is None or multiplier_table is None or multiplier_table.empty:
        return pd.DataFrame(), base_p_mw

    line_history = []
    if base_p_mw is None:
        base_p_mw = net.load["p_mw"].copy()

    for timestep in multiplier_table.index:
        net, base_p_mw = apply_simbench_multiplier_to_loads(
            net, multiplier_table, timestep, base_p_mw=base_p_mw
        )
        pn.runpp(net)

        line_row = (
            net.res_line["loading_percent"].copy()
            if len(net.res_line)
            else pd.Series(dtype=float)
        )
        line_row.name = timestep
        line_history.append(line_row)

    if not line_history:
        net.load["p_mw"] = base_p_mw
        return pd.DataFrame(), base_p_mw

    loading_df = pd.DataFrame(line_history)
    loading_df.index.name = "timestep"
    net.load["p_mw"] = base_p_mw
    return loading_df, base_p_mw