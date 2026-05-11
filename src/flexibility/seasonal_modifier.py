"""
seasonal_modifier.py
====================
Season-aware load profile scaling.

Three seasons are defined following the German meteorological calendar:
    * ``winter``     – December, January, February
    * ``transition`` – March–May and September–November
    * ``summer``     – June, July, August

For households with a **heat pump** or **Durchlauferhitzer**, this module
optionally queries DWD (Deutscher Wetterdienst) temperature data via vpplib's
``UserProfile`` / ``dwd_client`` to derive a temperature-dependent scaling
factor.  For all other households, simple multiplicative factors from
``APPLIANCE_DEFAULTS`` are used.

DWD integration
---------------
vpplib exposes a ``UserProfile`` class that can fetch hourly temperature
profiles for any German station.  If vpplib is installed and a station ID
is provided, ``get_temperature_factor()`` returns a physic-based scaling
factor; otherwise it falls back to the static season table.
"""

from __future__ import annotations

import warnings
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd

from src.flexibility.appliance_defaults import APPLIANCE_DEFAULTS

# ---------------------------------------------------------------------------
# Season table (month → season key)
# ---------------------------------------------------------------------------

MONTH_TO_SEASON: dict[int, str] = {
    12: "winter", 1: "winter", 2: "winter",
    3: "transition", 4: "transition", 5: "transition",
    6: "summer", 7: "summer", 8: "summer",
    9: "transition", 10: "transition", 11: "transition",
}

SEASON_KEYS = ("winter", "transition", "summer")


def get_season_for_date(d: date) -> str:
    """Return the season key for a given calendar date.

    Parameters
    ----------
    d : date
        Any Python date object.

    Returns
    -------
    str
        ``"winter"``, ``"transition"``, or ``"summer"``.
    """
    return MONTH_TO_SEASON[d.month]


def get_season_for_month(month: int) -> str:
    """Return the season key for a calendar month (1–12).

    Parameters
    ----------
    month : int
        Calendar month.

    Returns
    -------
    str
        Season key.
    """
    if month not in MONTH_TO_SEASON:
        raise ValueError(f"Month must be 1–12, got {month}.")
    return MONTH_TO_SEASON[month]


# ---------------------------------------------------------------------------
# Static multiplicative season modifier
# ---------------------------------------------------------------------------

def apply_static_season_factor(
    profile: pd.DataFrame,
    appliance: str,
    season: str,
) -> pd.DataFrame:
    """Scale a load profile by the static season factor for an appliance.

    Parameters
    ----------
    profile : pd.DataFrame
        DataFrame with ``"power_kw"`` column.
    appliance : str
        Key in ``APPLIANCE_DEFAULTS``.
    season : str
        Season key.

    Returns
    -------
    pd.DataFrame
        Scaled copy of the profile.
    """
    defaults = APPLIANCE_DEFAULTS.get(appliance, {})
    sf = defaults.get("season_factor", {}).get(season, 1.0)
    result = profile.copy()
    result["power_kw"] *= sf
    return result


# ---------------------------------------------------------------------------
# DWD-based temperature factor (vpplib integration)
# ---------------------------------------------------------------------------

def get_temperature_factor(
    season: str,
    dwd_station_id: Optional[str] = None,
    base_temp_c: float = 15.0,
    delta_temp_c: Optional[float] = None,
    cop: float = 3.0,
) -> float:
    """Compute a temperature-dependent factor for heat-pump / water-heater loads.

    If ``dwd_station_id`` is provided and vpplib is available, fetch actual
    mean temperature for the season from DWD and compute the factor from
    the COP relationship.

    Otherwise fall back to hardcoded season averages:
        winter     → 3 °C
        transition → 12 °C
        summer     → 20 °C

    Parameters
    ----------
    season : str
        Season key.
    dwd_station_id : str, optional
        DWD station ID string (e.g. ``"00433"`` for Berlin Tempelhof).
        If None, use hardcoded averages.
    base_temp_c : float
        Reference outdoor temperature at which the heat pump operates at its
        rated power.  Default 15 °C.
    delta_temp_c : float, optional
        If provided, override the DWD / hardcoded temperature with this value.
    cop : float
        Coefficient of Performance of the heat pump at reference temperature.

    Returns
    -------
    float
        Multiplicative scaling factor for heat-pump power consumption.
    """
    # Season average temperatures (°C) – fallback values
    SEASON_TEMPS: dict[str, float] = {
        "winter": 3.0,
        "transition": 12.0,
        "summer": 20.0,
    }

    if delta_temp_c is not None:
        mean_temp = delta_temp_c
    elif dwd_station_id is not None:
        mean_temp = _fetch_dwd_mean_temp(dwd_station_id, season)
        if mean_temp is None:
            mean_temp = SEASON_TEMPS.get(season, 12.0)
    else:
        mean_temp = SEASON_TEMPS.get(season, 12.0)

    # Simple linear COP model: COP ∝ T_condenser / (T_condenser - T_outdoor)
    # relative to base temperature.  Hotter outside → better COP → less electricity.
    if mean_temp >= base_temp_c:
        # No heating needed or minimal
        return 0.1
    factor = (base_temp_c - mean_temp) / (base_temp_c - SEASON_TEMPS["winter"])
    return float(np.clip(factor, 0.1, 3.0))


def _fetch_dwd_mean_temp(station_id: str, season: str) -> Optional[float]:
    """Attempt to fetch mean season temperature from DWD via vpplib.

    Returns None if vpplib is not available or the fetch fails.

    Parameters
    ----------
    station_id : str
        DWD station ID.
    season : str
        Season key.

    Returns
    -------
    float or None
        Mean temperature in °C.
    """
    try:
        from vpplib.user_profile import UserProfile  # type: ignore

        # Map season to representative month
        SEASON_MONTHS = {"winter": 1, "transition": 4, "summer": 7}
        month = SEASON_MONTHS.get(season, 4)

        # vpplib uses yearly temperature profiles; we extract the mean for
        # the representative month
        up = UserProfile(
            identifier=station_id,
            latitude=None,
            longitude=None,
        )
        # vpplib stores temperature as a Series or DataFrame attribute
        if hasattr(up, "heat_demand") or hasattr(up, "temp"):
            temp_series = getattr(up, "temp", None)
            if temp_series is None:
                return None
            if isinstance(temp_series, pd.Series):
                # Filter to the representative month
                month_mask = temp_series.index.month == month
                return float(temp_series[month_mask].mean())
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# High-level seasonal profile modifier
# ---------------------------------------------------------------------------

class SeasonalModifier:
    """Apply season-aware scaling to household load profiles.

    Parameters
    ----------
    season : str
        Active season (``"winter"``, ``"transition"``, ``"summer"``).
    dwd_station_id : str, optional
        DWD station ID for temperature-based scaling of thermal loads.
    """

    def __init__(
        self,
        season: str = "transition",
        dwd_station_id: Optional[str] = None,
    ) -> None:
        if season not in SEASON_KEYS:
            raise ValueError(f"season must be one of {SEASON_KEYS}, got '{season}'.")
        self.season = season
        self.dwd_station_id = dwd_station_id
        self._temp_factor: Optional[float] = None

    def _get_thermal_factor(self) -> float:
        if self._temp_factor is None:
            self._temp_factor = get_temperature_factor(
                season=self.season,
                dwd_station_id=self.dwd_station_id,
            )
        return self._temp_factor

    def modify_profile(
        self,
        profile: pd.DataFrame,
        owned_appliances: list[str],
    ) -> pd.DataFrame:
        """Apply season scaling to a combined household load profile.

        Because the profile is already a sum of individual appliance profiles,
        this method applies a *weighted average* of appliance-level season
        factors to the total.

        Parameters
        ----------
        profile : pd.DataFrame
            Weekly load profile with ``"power_kw"`` column.
        owned_appliances : list[str]
            List of appliances owned by the household.

        Returns
        -------
        pd.DataFrame
            Seasonally adjusted profile.
        """
        # Compute a representative aggregate factor
        factors = []
        for app in owned_appliances:
            defaults = APPLIANCE_DEFAULTS.get(app, {})
            if app in ("Heatpump", "Durchlauferhitzer"):
                # Use temperature-based factor
                f = self._get_thermal_factor()
            else:
                f = defaults.get("season_factor", {}).get(self.season, 1.0)
            factors.append(f)

        if not factors:
            return profile

        mean_factor = float(np.mean(factors))
        result = profile.copy()
        result["power_kw"] *= mean_factor
        return result

    def get_season_label(self) -> str:
        """Return the current season label string."""
        return self.season
