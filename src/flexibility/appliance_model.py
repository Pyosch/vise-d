"""
appliance_model.py
==================
``ShiftableAppliance`` – a vpplib-compatible appliance model.

vpplib convention: every component exposes ``get_timeseries(...)`` which returns
a ``pd.DataFrame`` with a ``DatetimeIndex`` and a ``"power_kw"`` column.

This class stores the *default* scheduled start slot and can return a
shifted copy for flexibility analysis.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Optional

import numpy as np
import pandas as pd


# Number of 15-min slots in one day / week
SLOTS_PER_DAY = 96
SLOTS_PER_WEEK = 672


class ShiftableAppliance:
    """Model of a single household appliance with optional load-shifting capability.

    Parameters
    ----------
    name : str
        Human-readable appliance name (e.g. ``"Washing_machine"``).
    power_kw : float
        Rated power in kW.
    runtime_hours : float
        Total cycle duration in hours.
    load_curve : list[float]
        Normalised power profile (relative, 0–1) at 15-min resolution for
        one cycle.  Length must equal ``ceil(runtime_hours * 4)``.
    is_shiftable : bool
        Whether the appliance can be time-shifted.
    max_shift_hours : float
        Maximum allowable time-shift in hours.
    scheduled_start_slot : int
        Default start slot within a day (0–95) for the appliance event.
    season_factor : dict[str, float]
        Multiplicative scaling per season key
        (``"winter"``, ``"transition"``, ``"summer"``).
    season : str
        Active season for this instance.
    """

    def __init__(
        self,
        name: str,
        power_kw: float,
        runtime_hours: float,
        load_curve: list[float],
        is_shiftable: bool,
        max_shift_hours: float,
        scheduled_start_slot: int,
        season_factor: Optional[dict[str, float]] = None,
        season: str = "transition",
    ) -> None:
        self.name = name
        self.power_kw = power_kw
        self.runtime_hours = runtime_hours
        self.load_curve = list(load_curve)
        self.is_shiftable = is_shiftable
        self.max_shift_hours = max_shift_hours
        self.scheduled_start_slot = scheduled_start_slot
        self.season_factor: dict[str, float] = season_factor or {
            "winter": 1.0,
            "transition": 1.0,
            "summer": 1.0,
        }
        self.season = season

        # Validate / pad load_curve length
        expected_slots = max(1, round(runtime_hours * 4))
        if len(self.load_curve) < expected_slots:
            # Pad with last value
            self.load_curve += [self.load_curve[-1]] * (expected_slots - len(self.load_curve))
        elif len(self.load_curve) > expected_slots:
            self.load_curve = self.load_curve[:expected_slots]

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def n_slots(self) -> int:
        """Number of 15-min slots for one complete cycle."""
        return len(self.load_curve)

    @property
    def effective_power_kw(self) -> float:
        """Peak power scaled by the active season factor."""
        sf = self.season_factor.get(self.season, 1.0)
        return self.power_kw * sf

    # ------------------------------------------------------------------
    # Core interface (vpplib-compatible)
    # ------------------------------------------------------------------

    def get_timeseries(
        self,
        start_slot: Optional[int] = None,
        n_slots: int = SLOTS_PER_WEEK,
        start_datetime: Optional[pd.Timestamp] = None,
    ) -> pd.DataFrame:
        """Build a power time series for the appliance over ``n_slots`` slots.

        A single cycle is placed at ``start_slot`` (default:
        ``self.scheduled_start_slot``).  All other slots are zero.

        Parameters
        ----------
        start_slot : int, optional
            Slot index at which the cycle begins (0-based).  Defaults to
            ``self.scheduled_start_slot``.
        n_slots : int
            Total length of the output time series in 15-min slots.
            Defaults to one week (672 slots).
        start_datetime : pd.Timestamp, optional
            Reference timestamp for the DatetimeIndex.  Defaults to
            ``2024-01-01 00:00`` (arbitrary Monday).

        Returns
        -------
        pd.DataFrame
            DataFrame with DatetimeIndex (15-min frequency) and column
            ``"power_kw"``.
        """
        if start_slot is None:
            start_slot = self.scheduled_start_slot
        if start_datetime is None:
            start_datetime = pd.Timestamp("2024-01-01 00:00")

        power = np.zeros(n_slots)
        sf = self.season_factor.get(self.season, 1.0)

        for i, frac in enumerate(self.load_curve):
            slot = (start_slot + i) % n_slots
            power[slot] += frac * self.power_kw * sf

        index = pd.date_range(start=start_datetime, periods=n_slots, freq="15min")
        return pd.DataFrame({"power_kw": power}, index=index)

    # ------------------------------------------------------------------
    # Flexibility helpers
    # ------------------------------------------------------------------

    def shift(self, delta_slots: int) -> "ShiftableAppliance":
        """Return a new ``ShiftableAppliance`` with a shifted start slot.

        Parameters
        ----------
        delta_slots : int
            Number of 15-min slots to shift (positive = later, negative = earlier).

        Returns
        -------
        ShiftableAppliance
            Copy of this appliance with ``scheduled_start_slot`` shifted.

        Raises
        ------
        ValueError
            If the requested shift exceeds ``max_shift_hours`` or the appliance
            is not shiftable.
        """
        if not self.is_shiftable:
            raise ValueError(f"Appliance '{self.name}' is not shiftable.")

        max_slots = int(self.max_shift_hours * 4)
        if abs(delta_slots) > max_slots:
            raise ValueError(
                f"Requested shift of {delta_slots} slots exceeds max "
                f"{max_slots} slots ({self.max_shift_hours} h) for '{self.name}'."
            )

        new_app = deepcopy(self)
        new_app.scheduled_start_slot = (self.scheduled_start_slot + delta_slots) % SLOTS_PER_DAY
        return new_app

    def get_flexibility_window(self) -> tuple[int, int]:
        """Return the earliest and latest possible start slots.

        Returns
        -------
        tuple[int, int]
            ``(earliest_slot, latest_slot)`` within a single day (0–95).
            Wraps around midnight using modulo arithmetic.
        """
        max_delta = int(self.max_shift_hours * 4)
        earliest = (self.scheduled_start_slot - max_delta) % SLOTS_PER_DAY
        latest = (self.scheduled_start_slot + max_delta) % SLOTS_PER_DAY
        return earliest, latest

    def get_shiftable_energy_kwh(self) -> float:
        """Return the total energy [kWh] of one cycle.

        Returns
        -------
        float
            Energy per cycle in kWh, scaled by season factor.
        """
        sf = self.season_factor.get(self.season, 1.0)
        # Each slot is 15 min = 0.25 h
        return sum(f * self.power_kw * sf * 0.25 for f in self.load_curve)

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"ShiftableAppliance(name={self.name!r}, "
            f"power_kw={self.power_kw}, "
            f"runtime_h={self.runtime_hours}, "
            f"shiftable={self.is_shiftable}, "
            f"start_slot={self.scheduled_start_slot})"
        )

    # ------------------------------------------------------------------
    # Factory from defaults dict
    # ------------------------------------------------------------------

    @classmethod
    def from_defaults(
        cls,
        name: str,
        defaults: dict,
        scheduled_start_slot: int = 0,
        season: str = "transition",
    ) -> "ShiftableAppliance":
        """Construct a ``ShiftableAppliance`` from an ``APPLIANCE_DEFAULTS`` entry.

        Parameters
        ----------
        name : str
            Appliance key in ``APPLIANCE_DEFAULTS``.
        defaults : dict
            The nested dict from ``APPLIANCE_DEFAULTS[name]``.
        scheduled_start_slot : int
            Start slot derived from the participant's preferred time-of-day.
        season : str
            Active season.

        Returns
        -------
        ShiftableAppliance
        """
        return cls(
            name=name,
            power_kw=defaults["power_kw"],
            runtime_hours=defaults["runtime_hours"],
            load_curve=list(defaults["load_curve"]),
            is_shiftable=defaults.get("is_shiftable", False),
            max_shift_hours=defaults.get("max_shift_hours", 0),
            scheduled_start_slot=scheduled_start_slot,
            season_factor=defaults.get(
                "season_factor", {"winter": 1.0, "transition": 1.0, "summer": 1.0}
            ),
            season=season,
        )
