"""Device-level flexibility base-load helpers.

Loads the precomputed household base-load profiles (generated offline from the
``household_flexibility_simulation`` model, EV and heat pump excluded) and turns
them into per-load network profiles. Provides:

* season-from-date mapping,
* per-load typology-class assignment (manual or seeded random),
* absolute baseline / shifted curves per load, peak-calibrated to the load's
  nameplate and tiled over an arbitrary simulation horizon,
* a generic energy-conserving window shifter used to shift the separately
  generated EV / heat-pump profiles,
* a shared ``Verschiebungsgrad`` slider for both the network and flexibility
  pages.

The precomputed CSVs (``flex_profiles_{season}.csv``) hold, per typology class,
a ``{class}__baseline_kw`` and a ``{class}__shifted_kw`` column at 15-min
resolution for one representative week (672 steps). Baseline and shifted differ
only by device-level load shifting and carry the same weekly energy.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

from src.config.paths import DATA_DIR

_PROFILES_DIR = DATA_DIR / "flexibility_profiles"

SLOTS_PER_DAY = 96
SLOTS_PER_WEEK = 672

SEASONS = ("winter", "transition", "summer")
SEASON_LABELS_DE = {"winter": "Winter", "transition": "Übergang", "summer": "Sommer"}

# Maximum load-shift window per separately-modelled device, in hours.
# Mirrors ``max_shift_hours`` in the source model's appliance defaults.
SHIFT_WINDOW_H = {"EV": 10.0, "HP": 4.0}


# --------------------------------------------------------------------------- #
# Season mapping
# --------------------------------------------------------------------------- #

def get_season_for_month(month: int) -> str:
    """Map a calendar month (1–12) to a season key."""
    if month in (12, 1, 2):
        return "winter"
    if month in (6, 7, 8):
        return "summer"
    return "transition"


def get_season_for_date(d) -> str:
    """Map a date / Timestamp to a season key."""
    return get_season_for_month(pd.Timestamp(d).month)


def season_label(season: str) -> str:
    return SEASON_LABELS_DE.get(season, season)


# --------------------------------------------------------------------------- #
# Profile loading
# --------------------------------------------------------------------------- #

@lru_cache(maxsize=len(SEASONS))
def load_flex_profiles(season: str) -> pd.DataFrame:
    """Load the precomputed baseline/shifted class curves for one season (kW)."""
    path = _PROFILES_DIR / f"flex_profiles_{season}.csv"
    return pd.read_csv(path, index_col="timestamp", parse_dates=True)


def available_classes(season: str = "transition") -> list[str]:
    """Return the typology classes present in the precomputed profiles."""
    df = load_flex_profiles(season)
    return sorted({c.split("__")[0] for c in df.columns if "__" in c})


# German labels for the household typology-class tokens. The class keys are
# composed as ``<work>_<size>_<automation>`` (e.g.
# ``homeoffice_small_family_semi_automated``); only the display is translated,
# the underlying keys stay unchanged (CSV lookup, assignment, etc.).
_CLASS_WORK_DE = {
    "homeoffice": "Homeoffice",
    "hybrid": "Hybrid",
    "office": "Büro",
}
_CLASS_SIZE_DE = {
    "single": "Single",
    "small_family": "kleine Familie",
    "large_family": "große Familie",
}
# Ordered so that the more specific ``semi_automated`` is matched before the
# ``automated`` suffix it contains.
_CLASS_AUTOMATION_DE = {
    "semi_automated": "teilautomatisiert",
    "time_programmable": "zeitprogrammierbar",
    "automated": "automatisiert",
    "manual": "manuell",
}

# Plain-German explanations of the four automation levels, ordered by load-shift
# potential (cf. ``AUTOMATION_FACTOR_MAP`` in the flexibility model: manuell 0.25
# → teilautomatisiert 0.50 → zeitprogrammierbar 0.75 → automatisiert 1.00).
_AUTOMATION_HELP_DE = {
    "manuell": "Geräte werden von Hand bedient; Lastverschiebung nur durch "
               "aktives Eingreifen (geringstes Potenzial).",
    "teilautomatisiert": "Teils automatische Steuerung einzelner Geräte; "
                         "mittleres Verschiebepotenzial.",
    "zeitprogrammierbar": "Geräte mit Start-/Programmvorwahl (Wasch-/Spülmaschine "
                          "…); gut planbare Verschiebung.",
    "automatisiert": "Vollautomatische Laststeuerung (Smart Home); Geräte "
                     "verschieben selbsttätig (höchstes Potenzial).",
}

# Ready-made tooltip text (markdown) for the "Automatisierung" table column head.
AUTOMATION_COLUMN_HELP_DE = (
    "**Automatisierungsgrad** – bestimmt das Lastverschiebe-Potenzial:\n\n"
    + "\n\n".join(f"- **{lvl}** – {desc}" for lvl, desc in _AUTOMATION_HELP_DE.items())
)


def class_components_de(cls: str) -> tuple[str | None, str | None, str | None]:
    """Split a typology-class key into its three German components.

    Returns ``(Arbeitsweise, Haushaltsgröße, Automatisierungsgrad)``; any
    component that cannot be recognised is ``None``. The raw key is unchanged.
    """
    rest = cls
    work = size = automation = None

    for token, label in _CLASS_WORK_DE.items():
        if rest.startswith(token + "_"):
            work = label
            rest = rest[len(token) + 1:]
            break

    for token, label in _CLASS_AUTOMATION_DE.items():
        if rest.endswith(token):
            automation = label
            rest = rest[: -len(token)].rstrip("_")
            break

    size = _CLASS_SIZE_DE.get(rest)
    return work, size, automation


def class_display_name(cls: str) -> str:
    """Human-readable German label for a household typology-class key.

    Recognised keys are translated component-wise to
    ``"<Arbeitsweise>, <Haushaltsgröße>, <Automatisierungsgrad>"``. Unknown keys
    fall back to a simple title-cased rendering of the raw key.
    """
    work, size, automation = class_components_de(cls)
    if work and size and automation:
        return ", ".join([work, size, automation])
    return cls.replace("_", " ").title()


# Display order of the working-situation groups (commute intensity descending).
_WORK_DISPLAY_ORDER = ("office", "hybrid", "homeoffice")


def group_classes_by_work(classes: list[str]) -> list[tuple[str, list[str]]]:
    """Group class keys by working situation for the UI selector.

    Returns ``[(Arbeitsweise_DE, [class_keys]), ...]`` in canonical display
    order, omitting empty groups. Keys with an unrecognised working-situation
    prefix are collected under ``"Sonstige"``.
    """
    groups: list[tuple[str, list[str]]] = []
    matched: set[str] = set()
    for token in _WORK_DISPLAY_ORDER:
        members = sorted(c for c in classes if c.startswith(token + "_"))
        if members:
            groups.append((_CLASS_WORK_DE[token], members))
            matched.update(members)
    rest = sorted(c for c in classes if c not in matched)
    if rest:
        groups.append(("Sonstige", rest))
    return groups


def household_curves(cls: str, season: str) -> tuple[np.ndarray, np.ndarray]:
    """Return the single-household weekly (baseline, shifted) curve in kW (672)."""
    df = load_flex_profiles(season)
    base = df[f"{cls}__baseline_kw"].to_numpy(dtype=float)
    shifted = df[f"{cls}__shifted_kw"].to_numpy(dtype=float)
    return base, shifted


# --------------------------------------------------------------------------- #
# Class assignment
# --------------------------------------------------------------------------- #

def assign_classes(
    load_ids: list[int],
    allowed_classes: list[str],
    seed: int = 42,
    manual: dict[int, str] | None = None,
) -> dict[int, str]:
    """Assign one typology class to each load id.

    ``manual`` entries take precedence; any remaining loads are assigned
    randomly (reproducibly via ``seed``) from ``allowed_classes``.
    """
    pool = list(allowed_classes) if allowed_classes else available_classes()
    rng = np.random.default_rng(seed)
    result: dict[int, str] = {}
    for lid in load_ids:
        if manual and manual.get(lid):
            result[lid] = manual[lid]
        elif pool:
            result[lid] = pool[int(rng.integers(0, len(pool)))]
    return result


# --------------------------------------------------------------------------- #
# Horizon construction
# --------------------------------------------------------------------------- #

def _horizon_days(start_date, n_steps: int) -> list[pd.Timestamp]:
    n_days = (n_steps + SLOTS_PER_DAY - 1) // SLOTS_PER_DAY
    start = pd.Timestamp(start_date).normalize()
    return [start + pd.Timedelta(days=d) for d in range(n_days)]


def _household_curve_over_horizon(cls: str, start_date, n_steps: int, which: str) -> np.ndarray:
    """Tile a class's weekly curve over the horizon.

    Each calendar day picks the matching season and weekday block (Mon-based) of
    the representative week, so weekday/weekend structure and seasonal level are
    preserved across arbitrarily long horizons.
    """
    idx = 0 if which == "baseline" else 1
    blocks: list[np.ndarray] = []
    for day in _horizon_days(start_date, n_steps):
        season = get_season_for_date(day)
        dow = int(day.dayofweek)  # 0 = Monday
        weekly = household_curves(cls, season)[idx]
        blocks.append(weekly[dow * SLOTS_PER_DAY:(dow + 1) * SLOTS_PER_DAY])
    return np.concatenate(blocks)[:n_steps] if blocks else np.zeros(n_steps)


def build_load_curves(
    load_nameplates_kw: dict[int, float],
    assigned_classes: dict[int, str],
    start_date,
    n_steps: int,
) -> tuple[dict[int, np.ndarray], dict[int, np.ndarray], dict[int, int]]:
    """Build absolute baseline / shifted curves (kW) per load over the horizon.

    For each load the assigned class's weekly curve is tiled over the horizon,
    the household count is derived from the nameplate peak, and a fine scalar
    calibrates the baseline peak exactly to the nameplate. The same household
    count and scalar are applied to the shifted curve, so the baseline/shifted
    energy relationship (energy-conserving shift) is preserved.

    Returns ``(baselines, shifteds, household_counts)`` keyed by load id.
    """
    baselines: dict[int, np.ndarray] = {}
    shifteds: dict[int, np.ndarray] = {}
    counts: dict[int, int] = {}

    for lid, p_kw in load_nameplates_kw.items():
        cls = assigned_classes.get(lid)
        if cls is None:
            continue
        base_hh = _household_curve_over_horizon(cls, start_date, n_steps, "baseline")
        shift_hh = _household_curve_over_horizon(cls, start_date, n_steps, "shifted")
        hh_peak = float(base_hh.max()) if base_hh.size else 0.0
        if hh_peak <= 0:
            baselines[lid] = np.zeros(n_steps)
            shifteds[lid] = np.zeros(n_steps)
            counts[lid] = 0
            continue
        n = max(1, round(float(p_kw) / hh_peak))
        base = n * base_hh
        peak = float(base.max())
        fine = (float(p_kw) / peak) if peak > 0 else 1.0
        baselines[lid] = base * fine
        shifteds[lid] = n * shift_hh * fine
        counts[lid] = n

    return baselines, shifteds, counts


def aggregate_mix(counts: dict[str, int], season: str) -> tuple[np.ndarray, np.ndarray]:
    """Sum baseline / shifted weekly curves (kW, 672) over a household-count mix."""
    base = np.zeros(SLOTS_PER_WEEK)
    shifted = np.zeros(SLOTS_PER_WEEK)
    for cls, n in counts.items():
        if n <= 0:
            continue
        b, s = household_curves(cls, season)
        base = base + n * b
        shifted = shifted + n * s
    return base, shifted


# --------------------------------------------------------------------------- #
# Shifting helpers
# --------------------------------------------------------------------------- #

def interpolate(baseline, shifted, alpha: float) -> np.ndarray:
    """Linear blend ``baseline + alpha * (shifted - baseline)``."""
    baseline = np.asarray(baseline, dtype=float)
    shifted = np.asarray(shifted, dtype=float)
    return baseline + float(alpha) * (shifted - baseline)


def shift_window_slots(device: str) -> int:
    """Number of 15-min slots a device may be shifted (per direction)."""
    return int(round(SHIFT_WINDOW_H.get(device, 0.0) * 4))


def fully_shift_within_window(
    profile, window_slots: int, max_iter: int | None = None, tol: float = 1e-9
) -> np.ndarray:
    """Energy-conserving valley-filling within ``±window_slots``.

    Greedily moves load from the current peak slot to the lowest slot within its
    window until the peak can no longer be reduced. Total energy is preserved;
    the variance (sum of squares) strictly decreases each step, so it converges.
    """
    p = np.asarray(profile, dtype=float).copy()
    n = p.size
    if window_slots <= 0 or n == 0:
        return p
    if max_iter is None:
        max_iter = min(50 * n, 50_000)
    for _ in range(max_iter):
        i = int(np.argmax(p))
        lo = max(0, i - window_slots)
        hi = min(n, i + window_slots + 1)
        j = lo + int(np.argmin(p[lo:hi]))
        gap = p[i] - p[j]
        if gap <= tol:
            break
        transfer = gap / 2.0
        p[i] -= transfer
        p[j] += transfer
    return p


def apply_profile_shift(profile, window_slots: int, alpha: float) -> np.ndarray:
    """Return ``profile`` blended toward its fully-shifted variant by ``alpha``."""
    p = np.asarray(profile, dtype=float)
    if alpha <= 0 or window_slots <= 0:
        return p.copy()
    full = fully_shift_within_window(p, window_slots)
    return p + float(alpha) * (full - p)


def shift_device_profile(profile, device: str, alpha: float) -> np.ndarray:
    """Shift an EV / heat-pump profile within its device window by ``alpha``."""
    return apply_profile_shift(profile, shift_window_slots(device), alpha)


# --------------------------------------------------------------------------- #
# Shared UI
# --------------------------------------------------------------------------- #

def verschiebung_slider(
    key: str,
    default_pct: int = 100,
    label: str = "Verschiebungsgrad der Flexibilität",
) -> float:
    """Render the shared flexibility-shift slider and return alpha in [0, 1]."""
    import streamlit as st

    pct = st.slider(
        label, min_value=0, max_value=100, value=default_pct, step=5,
        format="%d %%", key=key,
        help="0 % = keine Verschiebung, 100 % = volle gerätescharfe Verschiebung.",
    )
    return pct / 100.0
