"""
household_profile.py
====================
``HouseholdProfile`` – the core modelling class.

One instance represents a single survey participant and exposes:
* the list of owned appliances
* a probabilistically-generated weekly schedule
* a synthesised 15-min weekly load profile
* calibration to the participant's self-reported annual consumption
* a pandapower-ready export dictionary
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from src.flexibility.appliance_defaults import APPLIANCE_DEFAULTS, COLUMN_TO_APPLIANCE
from src.flexibility.appliance_model import ShiftableAppliance, SLOTS_PER_DAY, SLOTS_PER_WEEK

# Default reference Monday for DatetimeIndex
REFERENCE_START = pd.Timestamp("2024-01-01 00:00")  # Monday

# Assumed power factor
COS_PHI = 0.95


class HouseholdProfile:
    """Model of a single household's weekly electricity consumption.

    Parameters
    ----------
    participant_data : pd.Series
        One row from the feature-engineered DataFrame.
    appliance_defaults : dict
        Dictionary of appliance parameter dicts (from ``APPLIANCE_DEFAULTS``).
    season : str
        Active season: ``"winter"``, ``"transition"``, or ``"summer"``.

    Attributes
    ----------
    participant_id : int
        Participant identifier used as RNG seed for reproducibility.
    rng : np.random.Generator
        Seeded random number generator.
    season : str
        Active season.
    """

    def __init__(
        self,
        participant_data: pd.Series,
        appliance_defaults: Optional[dict] = None,
        season: str = "transition",
    ) -> None:
        self._data = participant_data
        self._defaults = appliance_defaults if appliance_defaults is not None else APPLIANCE_DEFAULTS
        self.season = season

        # Robust participant ID extraction
        pid = participant_data.get("participant.id_in_session", 0)
        try:
            self.participant_id = int(pid) if not pd.isna(pid) else 0
        except (TypeError, ValueError):
            self.participant_id = 0

        self.rng = np.random.default_rng(self.participant_id)

        # Cache
        self._owned_appliances: Optional[list[str]] = None
        self._weekly_schedule: Optional[dict[str, list[int]]] = None
        self._load_profile_df: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------
    # 1. Owned appliances
    # ------------------------------------------------------------------

    def get_owned_appliances(self) -> list[str]:
        """Return list of appliance names owned by this household.

        Returns
        -------
        list[str]
            Appliance keys matching ``APPLIANCE_DEFAULTS``.
        """
        if self._owned_appliances is not None:
            return self._owned_appliances

        owned = []
        for col_name, app_key in COLUMN_TO_APPLIANCE.items():
            has_col = f"Has_{col_name}"
            val = self._data.get(has_col, 0)
            try:
                if int(val) == 1:
                    owned.append(app_key)
            except (TypeError, ValueError):
                pass
        self._owned_appliances = owned
        return owned

    # ------------------------------------------------------------------
    # 2. Weekly schedule
    # ------------------------------------------------------------------

    def get_weekly_schedule(self) -> dict[str, list[int]]:
        """Generate a probabilistic weekly schedule for all owned appliances.

        For each appliance the participant's stated frequency (uses per week)
        and preferred time-of-day slot window are used to distribute events
        across the 7-day horizon.

        The start slot for each event is sampled uniformly within the
        time-of-day window.  A seeded RNG ensures reproducibility.

        Returns
        -------
        dict[str, list[int]]
            Mapping ``appliance_name → [start_slot_in_week, ...]``.
            Slot index is in the range [0, 672).
        """
        if self._weekly_schedule is not None:
            return self._weekly_schedule

        schedule: dict[str, list[int]] = {}

        for appliance in self.get_owned_appliances():
            col = appliance  # column prefix equals appliance key
            freq = self._data.get(f"{col}_frequency", 1.0)
            try:
                freq = float(freq)
                if np.isnan(freq) or freq <= 0:
                    freq = 1.0
            except (TypeError, ValueError):
                freq = 1.0

            slot_start = self._data.get(f"{col}_slot_start", 48)
            slot_end = self._data.get(f"{col}_slot_end", 68)
            try:
                slot_start = int(slot_start) if not pd.isna(slot_start) else 48
                slot_end = int(slot_end) if not pd.isna(slot_end) else 68
            except (TypeError, ValueError):
                slot_start, slot_end = 48, 68

            n_events = max(1, round(freq))

            # Distribute events evenly across 7 days with jitter
            day_slots = []
            for event_idx in range(n_events):
                # Pick a day: spread events quasi-uniformly, add noise
                day = int(self.rng.integers(0, 7))

                # Pick a start slot within the preferred time window
                if slot_start < slot_end:
                    # Normal window (e.g. 48–68 for Nachmittags)
                    intraday_slot = int(self.rng.integers(slot_start, max(slot_start + 1, slot_end)))
                elif slot_start > slot_end:
                    # Overnight window wraps (e.g. 88–24 for Über Nacht)
                    # Build wrap-around range
                    window = list(range(slot_start, SLOTS_PER_DAY)) + list(range(0, slot_end))
                    intraday_slot = int(self.rng.choice(window)) if window else slot_start
                else:
                    # Baseload (0, 96) → full day
                    intraday_slot = int(self.rng.integers(0, SLOTS_PER_DAY))

                week_slot = day * SLOTS_PER_DAY + intraday_slot
                day_slots.append(int(week_slot))

            schedule[appliance] = sorted(day_slots)

        self._weekly_schedule = schedule
        return schedule

    # ------------------------------------------------------------------
    # 3. Load profile
    # ------------------------------------------------------------------

    def get_load_profile(self) -> pd.DataFrame:
        """Synthesise the weekly 15-min power profile.

        Each appliance event is placed at its scheduled start slot using the
        ``ShiftableAppliance.get_timeseries()`` method, then all profiles are
        summed.

        Returns
        -------
        pd.DataFrame
            DataFrame with DatetimeIndex (15-min, 7 days = 672 rows) and
            column ``"power_kw"``.
        """
        if self._load_profile_df is not None:
            return self._load_profile_df

        index = pd.date_range(start=REFERENCE_START, periods=SLOTS_PER_WEEK, freq="15min")
        total_power = pd.Series(np.zeros(SLOTS_PER_WEEK), index=index)

        schedule = self.get_weekly_schedule()

        for appliance, start_slots in schedule.items():
            if appliance not in self._defaults:
                continue
            defaults = self._defaults[appliance]

            for start_slot in start_slots:
                appliance_obj = ShiftableAppliance.from_defaults(
                    name=appliance,
                    defaults=defaults,
                    scheduled_start_slot=start_slot % SLOTS_PER_DAY,
                    season=self.season,
                )
                # Build single-event series for this start slot
                ts = appliance_obj.get_timeseries(
                    start_slot=start_slot,
                    n_slots=SLOTS_PER_WEEK,
                    start_datetime=REFERENCE_START,
                )
                total_power = total_power.add(ts["power_kw"], fill_value=0.0)

        self._load_profile_df = pd.DataFrame({"power_kw": total_power})
        return self._load_profile_df

    # ------------------------------------------------------------------
    # 4. Calibration
    # ------------------------------------------------------------------

    def calibrate(self, target_kwh: Optional[float] = None) -> pd.DataFrame:
        """Scale the weekly load profile to match ``target_kwh``.

        If ``target_kwh`` is not provided, uses ``weekly_kwh_target`` from
        the participant data (= ``Estimated_Consumption_kWh / 52``).

        Parameters
        ----------
        target_kwh : float, optional
            Target weekly energy consumption in kWh.

        Returns
        -------
        pd.DataFrame
            Calibrated load profile.
        """
        profile = self.get_load_profile().copy()

        if target_kwh is None:
            target_kwh = self._data.get("weekly_kwh_target", None)
            try:
                target_kwh = float(target_kwh) if target_kwh is not None and not pd.isna(target_kwh) else None
            except (TypeError, ValueError):
                target_kwh = None

        if target_kwh is None or target_kwh <= 0:
            return profile

        # Current weekly energy: each slot is 0.25 h
        current_kwh = profile["power_kw"].sum() * 0.25
        if current_kwh <= 0:
            return profile

        scale = target_kwh / current_kwh
        profile["power_kw"] *= scale
        self._load_profile_df = profile  # update cache
        return profile

    # ------------------------------------------------------------------
    # 5. pandapower export
    # ------------------------------------------------------------------

    def to_pandapower_load(self) -> dict[str, float]:
        """Return a pandapower-compatible load dictionary.

        Active power is the mean over the weekly profile (time-averaged
        equivalent steady-state load).  Reactive power is derived assuming
        cos φ = 0.95.

        Returns
        -------
        dict[str, float]
            ``{"p_mw": ..., "q_mvar": ...}``
        """
        profile = self.get_load_profile()
        p_kw = profile["power_kw"].mean()
        p_mw = p_kw / 1000.0
        # tan(φ) = sin(φ) / cos(φ); cos φ = 0.95 → sin φ ≈ 0.3122
        tan_phi = np.sqrt(1 - COS_PHI**2) / COS_PHI
        q_mvar = p_mw * tan_phi
        return {"p_mw": round(p_mw, 6), "q_mvar": round(q_mvar, 6)}

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"HouseholdProfile(id={self.participant_id}, "
            f"season={self.season!r}, "
            f"appliances={self.get_owned_appliances()})"
        )
