import numpy as np
import pandas as pd
import pandapower as pn

# ── Category → SimBench profile code ─────────────────────────────────────────
# These match the exact column-name prefixes found in net.profiles["load"],
# e.g. "H0-A_pload", "G0-A_pload", "L0-A_pload".
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

# Reference SimBench scenario — the complete mixed dataset contains all
# standard profile families: H0 (household), G0-G6 (commercial/industry), L0-L2 (agriculture).
_SIMBENCH_SCENARIO = "1-complete_data-mixed-all-0-sw"

# Fallback chains: if the preferred code is absent, try the next one in the list.
_PROFILE_FALLBACK_CHAINS = {
    "H0-A": ["H0-A", "H0-B", "H0-C"],
    "G0-A": ["G0-A", "G0-B", "G1-A", "G2-A", "H0-A"],
    "G3-A": ["G3-A", "G3-B", "G4-A", "G0-A", "H0-A"],
    "L0-A": ["L0-A", "L1-A", "L2-A", "H0-A"],
}


def _classify_load(name: str) -> str:
    """Map a load name string to a category."""
    name_lower = name.lower()
    for keywords, category in _KEYWORD_MAP:
        if any(kw in name_lower for kw in keywords):
            return category
    return "Residential"


def _get_real_simbench_profiles(day_index: int = 0) -> dict:
    """
    Load genuine SimBench load profiles for one day (96 × 15-min timesteps).

    Uses ``simbench.get_simbench_net()`` to retrieve a reference network whose
    ``net.profiles["load"]`` DataFrame contains the full annual timeseries for
    every standard profile type (H0-A, G0-A, G3-A, L0-A, …).

    Each returned profile is normalised so that its daily **peak equals 1.0**,
    guaranteeing multipliers stay in (0, 1] and loads never exceed base p_mw.

    Parameters
    ----------
    day_index : int
        Which day of the year to extract (0 = Jan 1, 364 = Dec 31).

    Returns
    -------
    dict
        {profile_code: np.ndarray shape (96,)} — normalised multipliers.

    Raises
    ------
    RuntimeError
        If the simbench package or the required profile data cannot be loaded.
    """
    try:
        import simbench as sb
    except ImportError:
        raise RuntimeError(
            "The 'simbench' package is required but not installed. "
            "Install it with:  pip install simbench"
        )

    net_ref = sb.get_simbench_net(_SIMBENCH_SCENARIO)

    # SimBench stores profiles in net["profiles"]["load"] — a DataFrame with
    # 35 040 rows (full year at 15-min resolution) and one column per profile
    # code + suffix, e.g. "H0-A_pload", "G0-A_pload", "G3-A_pload", …
    try:
        load_df = net_ref["profiles"]["load"]
    except (KeyError, TypeError):
        raise RuntimeError(
            f"No 'load' profiles found in SimBench network '{_SIMBENCH_SCENARIO}'. "
            "The network may not contain time-series profile data."
        )

    if load_df is None or load_df.empty:
        raise RuntimeError(
            f"SimBench network '{_SIMBENCH_SCENARIO}' has an empty load-profile table."
        )

    # Extract exactly one day
    start = day_index * 96
    end = start + 96
    if end > len(load_df):
        raise RuntimeError(
            f"day_index={day_index} is out of range for the available profile data "
            f"({len(load_df)} rows = {len(load_df) // 96} days)."
        )
    day = load_df.iloc[start:end].reset_index(drop=True)

    # Drop the optional "time" column if present
    if "time" in day.columns:
        day = day.drop(columns=["time"])

    available_cols = set(day.columns)
    result = {}

    for code in set(_CATEGORY_PROFILE.values()):
        # Walk the fallback chain and use the first available variant
        chain = _PROFILE_FALLBACK_CHAINS.get(code, [code])
        resolved = None
        for candidate in chain:
            if f"{candidate}_pload" in available_cols:
                resolved = candidate
                break

        if resolved is None:
            raise RuntimeError(
                f"No profile found for code '{code}' (tried: {chain}). "
                f"Available columns: {sorted(available_cols)}"
            )

        arr = day[f"{resolved}_pload"].values.astype(float)
        if arr.max() < 1e-9:
            raise RuntimeError(
                f"Profile '{resolved}_pload' has near-zero peak for "
                f"day_index={day_index}. Cannot normalise."
            )
        result[code] = arr / arr.max()  # normalise → peak = 1.0, values in (0, 1]

    return result


def get_load_profile_assignments(net) -> pd.DataFrame:
    """
    Return a DataFrame showing each base load's name, category, and assigned
    SimBench profile code.  Intended for display in the UI.

    Returns columns: Load Name | Category | SimBench Profile
    Index: load index from net.load
    """
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
            "Load Name":       name,
            "Category":        category,
            "SimBench Profile": profile_code,
        })

    return pd.DataFrame(rows, index=load_names.index)



def Simbench_multiplier(net, base_profile_name="H0-A", amplitude=0.35,
                        phase_shift=0, day_index=0):
    """
    Build a 96-step (15-min resolution, one day) multiplier table for every
    base load in *net* using **real** SimBench load profiles.

    Each load is classified by its name into one of:
        EV, HeatPump, Industry, Commercial, Agricultural, Residential

    and assigned the corresponding genuine SimBench profile:
        Residential / EV / HeatPump → H0-A (household)
        Commercial                  → G0-A (general commerce)
        Industry                    → G3-A (continuous / shift industry)
        Agricultural                → L0-A (agriculture)

    Parameters
    ----------
    net               : pandapowerNet
    base_profile_name : kept for API compatibility (unused)
    amplitude         : kept for API compatibility (unused)
    phase_shift       : kept for API compatibility (unused)
    day_index         : int — which day of the year to use (0 = Jan 1)

    Returns
    -------
    pd.DataFrame
        Shape (96, n_loads) — columns are load indices from net.load.index.
    """
    if net is None or not hasattr(net, "load") or net.load.empty:
        return pd.DataFrame()

    time_index = pd.RangeIndex(0, 96, name="timestep")

    # 1. Classify every load by name
    load_names = (
        net.load["name"].fillna("").astype(str)
        if "name" in net.load.columns
        else pd.Series(net.load.index.astype(str), index=net.load.index)
    )
    category_map = {idx: _classify_load(name) for idx, name in load_names.items()}

    # 2. Load real SimBench profiles (raises RuntimeError on failure)
    profiles = _get_real_simbench_profiles(day_index)

    # 3. Build multiplier table — one column per load index
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


# ── SimBench dtype fixer ───────────────────────────────────────────────────────
def fix_simbench_dtypes(net):
    """Fix all dtype issues that SimBench introduces (object/float columns that should be bool/numeric).

    SimBench loads some boolean columns (e.g. 'controllable', 'in_service') as object dtype
    and some min/max constraint columns as object instead of float.  This causes pandapower's
    runpp / runopp to raise TypeErrors.  Call this immediately after sb.get_simbench_net().
    """
    for element in ['bus', 'line', 'trafo', 'trafo3w', 'load', 'sgen', 'gen',
                    'ext_grid', 'shunt', 'ward', 'xward', 'storage', 'switch']:
        if element not in net or net[element] is None or len(net[element]) == 0:
            continue
        df = net[element]

        # Fix 'controllable' and 'in_service' to bool
        for col in ['controllable', 'in_service']:
            if col in df.columns and df[col].dtype != bool:
                net[element][col] = df[col].fillna(False).astype(bool)

        # Fix min/max constraint columns that are object type with NaN to float
        for col in df.columns:
            if any(col.startswith(p) for p in ['min_p', 'max_p', 'min_q', 'max_q']):
                if df[col].dtype == 'object':
                    net[element][col] = pd.to_numeric(df[col], errors='coerce')