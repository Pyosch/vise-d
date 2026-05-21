import os
from functools import lru_cache

import numpy as np
import pandas as pd
import pandapower as pn

# ── Category → SimBench profile code ─────────────────────────────────────────
_CATEGORY_PROFILE = {
    "Residential":  "H0-A",
    "Commercial":   "G0-A",
    "Industry":     "G3-A",
    "Agricultural": "L0-A",
    "EV":           "H0-A",
    "HeatPump":     "H0-A",
}

# ── Load-name keywords → category ─────────────────────────────────────────────
_KEYWORD_MAP = [
    (["ev", "bev", "car", "elektro"],                     "EV"),
    (["heat", "hp", "pump", "wärmepumpe"],                "HeatPump"),
    (["industry", "industrial", "industrie", "g3", "g4"], "Industry"),
    (["office", "commerce", "shop", "store", "gewerbe",
      "handel", "g0", "g1", "g2"],                        "Commercial"),
    (["agri", "farm", "landwirt", "rural", "l0", "l1"],   "Agricultural"),
]

_SIMBENCH_SCENARIO = "1-complete_data-mixed-all-0-sw"

_PROFILE_FALLBACK_CHAINS = {
    "H0-A": ["H0-A", "H0-B", "H0-C"],
    "G0-A": ["G0-A", "G0-B", "G1-A", "G2-A", "H0-A"],
    "G3-A": ["G3-A", "G3-B", "G4-A", "G0-A", "H0-A"],
    "L0-A": ["L0-A", "L1-A", "L2-A", "H0-A"],
}


def _classify_load(name: str) -> str:
    name_lower = name.lower()
    for keywords, category in _KEYWORD_MAP:
        if any(kw in name_lower for kw in keywords):
            return category
    return "Residential"


@lru_cache(maxsize=1)
def _loadprofile_csv_path() -> str:
    """Return the path to LoadProfile.csv (resolved once per process)."""
    try:
        import simbench as sb
    except ImportError:
        raise RuntimeError(
            "The 'simbench' package is required but not installed. "
            "Install it with:  pip install simbench"
        )
    path = os.path.join(
        os.path.dirname(sb.__file__),
        "networks", _SIMBENCH_SCENARIO, "LoadProfile.csv",
    )
    if not os.path.isfile(path):
        raise RuntimeError(f"LoadProfile.csv not found at: {path}")
    return path


@lru_cache(maxsize=1)
def _profile_col_map() -> dict:
    """Read the CSV header once and resolve {code: column_name}."""
    path = _loadprofile_csv_path()
    header = pd.read_csv(path, sep=";", nrows=0)
    available = set(header.columns)
    mapping = {}
    for code in set(_CATEGORY_PROFILE.values()):
        chain = _PROFILE_FALLBACK_CHAINS.get(code, [code])
        for candidate in chain:
            col = f"{candidate}_pload"
            if col in available:
                mapping[code] = col
                break
        if code not in mapping:
            raise RuntimeError(
                f"No profile found for code '{code}' (tried: {chain}). "
                f"Available columns: {sorted(available)}"
            )
    return mapping


def _read_profile_slice(start_day_index: int, n_days: int) -> pd.DataFrame:
    """Read exactly n_days*96 rows and only the needed profile columns from the CSV.

    Uses skiprows + nrows + usecols so pandas touches the minimum amount of data.
    """
    path = _loadprofile_csv_path()
    col_map = _profile_col_map()
    needed_cols = list(set(col_map.values()))

    skip_start = start_day_index * 96  # data rows to skip before the window
    df = pd.read_csv(
        path,
        sep=";",
        skiprows=range(1, skip_start + 1),  # keep header row, skip data rows before window
        nrows=n_days * 96,
        usecols=needed_cols,
        index_col=False,
    )
    if len(df) < n_days * 96:
        raise RuntimeError(
            f"Requested {n_days} days starting at day_index={start_day_index} "
            f"but only {len(df)} rows available in LoadProfile.csv."
        )
    return df.reset_index(drop=True)


def _get_real_simbench_profiles(day_index: int = 0) -> dict:
    """Return normalised 96-step multipliers for one day, keyed by profile code."""
    col_map = _profile_col_map()
    df = _read_profile_slice(day_index, 1)
    result = {}
    for code, col in col_map.items():
        arr = df[col].values.astype(float)
        peak = arr.max()
        if peak < 1e-9:
            raise RuntimeError(
                f"Profile '{col}' has near-zero peak for day_index={day_index}."
            )
        result[code] = arr / peak
    return result


def get_load_profile_assignments(net) -> pd.DataFrame:
    """Return a DataFrame showing each load's name, category, and SimBench profile code."""
    if net is None or not hasattr(net, "load") or net.load.empty:
        return pd.DataFrame()

    load_names = (
        net.load["name"].fillna("").astype(str)
        if "name" in net.load.columns
        else pd.Series(net.load.index.astype(str), index=net.load.index)
    )

    rows = []
    for idx, name in load_names.items():
        category = _classify_load(name)
        profile_code = _CATEGORY_PROFILE.get(category, "H0-A")
        rows.append({
            "Load Name":        name,
            "Category":         category,
            "SimBench Profile": profile_code,
        })

    return pd.DataFrame(rows, index=load_names.index)


def Simbench_multiplier_range(net, start_day_index: int, n_days: int) -> pd.DataFrame:
    """Build a (n_days * 96)-step multiplier table by reading only the needed CSV rows.

    Reads exactly ``n_days * 96`` rows and ~4 profile columns from LoadProfile.csv
    instead of loading the full SimBench network, making it fast regardless of how
    large the annual file is.

    Returns
    -------
    pd.DataFrame
        Shape (n_days * 96, n_loads) with a RangeIndex.
    """
    if net is None or not hasattr(net, "load") or net.load.empty:
        return pd.DataFrame()

    col_map = _profile_col_map()
    df = _read_profile_slice(start_day_index, n_days)

    normalised: dict[str, np.ndarray] = {}
    for code, col in col_map.items():
        arr = df[col].values.astype(float).copy()
        for d in range(n_days):
            s, e = d * 96, d * 96 + 96
            peak = arr[s:e].max()
            if peak > 1e-9:
                arr[s:e] /= peak
        normalised[code] = arr

    load_names = (
        net.load["name"].fillna("").astype(str)
        if "name" in net.load.columns
        else pd.Series(net.load.index.astype(str), index=net.load.index)
    )
    multiplier_table = pd.DataFrame(index=range(n_days * 96))
    for load_idx, name in load_names.items():
        code = _CATEGORY_PROFILE.get(_classify_load(name), "H0-A")
        multiplier_table[load_idx] = normalised[code]

    return multiplier_table


def Simbench_multiplier(net, base_profile_name="H0-A", amplitude=0.35,
                        phase_shift=0, day_index=0):
    """Build a 96-step multiplier table for one day using real SimBench load profiles."""
    if net is None or not hasattr(net, "load") or net.load.empty:
        return pd.DataFrame()

    time_index = pd.RangeIndex(0, 96, name="timestep")
    load_names = (
        net.load["name"].fillna("").astype(str)
        if "name" in net.load.columns
        else pd.Series(net.load.index.astype(str), index=net.load.index)
    )
    category_map = {idx: _classify_load(name) for idx, name in load_names.items()}
    profiles = _get_real_simbench_profiles(day_index)

    multiplier_table = pd.DataFrame(index=time_index)
    for load_idx in net.load.index:
        category = category_map.get(load_idx, "Residential")
        code = _CATEGORY_PROFILE.get(category, "H0-A")
        multiplier_table[load_idx] = pd.Series(profiles[code], index=time_index)

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
