"""
flexibility_model.py
====================
``FlexibilityAssessor`` – quantifies demand-side flexibility potential
for a single household.

The assessor combines three independent factors:
1. **Device flexibility score** (from survey)  – how willing is the participant
   to shift this specific appliance?
2. **Automation factor** – how capable is the household of actually executing
   a shift (manual vs. automated)?
3. **Tariff incentive** – does the electricity tariff provide a financial
   signal for shifting?

Final shiftable energy per device [kWh/week]:

    E_shift = E_device × score_norm × automation_factor × tariff_incentive
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from src.flexibility.household_profile import HouseholdProfile
from src.flexibility.appliance_model import ShiftableAppliance
from src.flexibility.appliance_defaults import APPLIANCE_DEFAULTS, FLEX_COLUMN_MAP

# ---------------------------------------------------------------------------
# Mapping constants
# ---------------------------------------------------------------------------

# Raw survey scale assumed: 1–5 integer  → normalised 0–1
FLEX_SCORE_MAX = 5.0

# flexibilisierungsart → automation factor
AUTOMATION_FACTOR_MAP: dict[str, float] = {
    "manuell": 0.25,
    "halb_automatisiert": 0.50,
    "zeitprogrammierbar": 0.75,
    "automatisiert": 1.00,
}

# Tariff incentive
TARIFF_INCENTIVE_MAP: dict[str, float] = {
    "static": 0.5,
    "dynamic": 1.0,
    "unknown": 0.5,
}


class FlexibilityAssessor:
    """Assess demand-side flexibility potential for a single household.

    Parameters
    ----------
    profile : HouseholdProfile
        The household's load profile model.
    participant_row : pd.Series
        The raw/feature-engineered survey row for the same participant.
    """

    def __init__(
        self,
        profile: HouseholdProfile,
        participant_row: pd.Series,
    ) -> None:
        self.profile = profile
        self.row = participant_row

    # ------------------------------------------------------------------
    # Factor methods
    # ------------------------------------------------------------------

    def get_device_flexibility_scores(self) -> pd.Series:
        """Extract and normalise per-device flexibility scores (0–1).

        Scores come from ``flexibility.1.player.{device}`` columns.
        Missing scores default to 0 (no flexibility assumed).

        Returns
        -------
        pd.Series
            Index = appliance name (``APPLIANCE_DEFAULTS`` key),
            Values = normalised score [0, 1].
        """
        scores: dict[str, float] = {}
        for appliance, survey_suffix in FLEX_COLUMN_MAP.items():
            col = f"flexibility.1.player.{survey_suffix}"
            raw = self.row.get(col, np.nan)
            try:
                val = float(raw)
                if np.isnan(val):
                    val = 0.0
            except (TypeError, ValueError):
                val = 0.0
            scores[appliance] = min(1.0, max(0.0, val / FLEX_SCORE_MAX))

        # Appliances not in FLEX_COLUMN_MAP get score 0 (not assessed in survey)
        for appliance in APPLIANCE_DEFAULTS:
            if appliance not in scores:
                scores[appliance] = 0.0

        return pd.Series(scores, name="flexibility_score")

    def get_automation_factor(self) -> float:
        """Return the automation factor [0.25–1.0].

        Derived from ``flexibility.1.player.flexibilisierungsart`` (preferred)
        or ``automation_category`` as fallback.

        Returns
        -------
        float
            Automation factor.
        """
        flex_col = "flexibility.1.player.flexibilisierungsart"
        raw = self.row.get(flex_col, None)
        if pd.notna(raw) and str(raw) in AUTOMATION_FACTOR_MAP:
            return AUTOMATION_FACTOR_MAP[str(raw)]

        # Fallback to normalised automation_category
        auto_cat = self.row.get("automation_category", None)
        if pd.notna(auto_cat):
            reverse_map = {
                "manual": "manuell",
                "semi_automated": "halb_automatisiert",
                "time_programmable": "zeitprogrammierbar",
                "automated": "automatisiert",
            }
            german = reverse_map.get(str(auto_cat), "manuell")
            return AUTOMATION_FACTOR_MAP.get(german, 0.25)

        return 0.25  # most conservative fallback

    def get_tariff_incentive(self) -> float:
        """Return the tariff-based incentive factor [0.5–1.0].

        Returns
        -------
        float
            1.0 for dynamic tariff, 0.5 for static or unknown.
        """
        tariff = self.row.get("Electricity_Tariff", "unknown")
        if pd.isna(tariff):
            tariff = "unknown"
        return TARIFF_INCENTIVE_MAP.get(str(tariff), 0.5)

    # ------------------------------------------------------------------
    # Energy computation
    # ------------------------------------------------------------------

    def get_shiftable_energy_kwh(self) -> pd.Series:
        """Compute shiftable energy per device per week [kWh].

        Formula:
            E_shift = E_device × score_norm × automation_factor × tariff_incentive

        ``E_device`` is the total weekly energy of each appliance based on
        the household's schedule and the appliance's load curve.

        Returns
        -------
        pd.Series
            Index = appliance name, values = shiftable energy [kWh/week].
        """
        scores = self.get_device_flexibility_scores()
        af = self.get_automation_factor()
        ti = self.get_tariff_incentive()

        owned = set(self.profile.get_owned_appliances())
        schedule = self.profile.get_weekly_schedule()

        shiftable: dict[str, float] = {}
        for appliance in APPLIANCE_DEFAULTS:
            if appliance not in owned:
                shiftable[appliance] = 0.0
                continue

            defaults = APPLIANCE_DEFAULTS[appliance]
            start_slots = schedule.get(appliance, [])
            n_events = len(start_slots)

            # Energy per cycle
            sf = defaults.get("season_factor", {}).get(self.profile.season, 1.0)
            e_cycle = (
                sum(defaults["load_curve"])
                * defaults["power_kw"]
                * sf
                * 0.25  # 15 min = 0.25 h
            )
            e_weekly = e_cycle * n_events

            score = scores.get(appliance, 0.0)
            shiftable[appliance] = round(e_weekly * score * af * ti, 4)

        return pd.Series(shiftable, name="shiftable_kwh")

    # ------------------------------------------------------------------
    # Summary table
    # ------------------------------------------------------------------

    def get_flexibility_summary(self) -> pd.DataFrame:
        """Return a per-device flexibility summary table.

        Returns
        -------
        pd.DataFrame
            Columns: device, owned, scheduled_time, flexibility_score,
            shiftable_kwh, shift_window_h.
        """
        scores = self.get_device_flexibility_scores()
        shiftable = self.get_shiftable_energy_kwh()
        owned_appliances = set(self.profile.get_owned_appliances())
        schedule = self.profile.get_weekly_schedule()

        rows = []
        for appliance in APPLIANCE_DEFAULTS:
            owned = appliance in owned_appliances
            time_label = self.row.get(f"{appliance}_time", None) if owned else None

            # Scheduled time: first event in week, converted back to hh:mm
            if owned and appliance in schedule and schedule[appliance]:
                first_slot = schedule[appliance][0]
                intraday = first_slot % 96
                hour = intraday // 4
                minute = (intraday % 4) * 15
                scheduled_time = f"{hour:02d}:{minute:02d}"
            else:
                scheduled_time = None

            flex_score = float(scores.get(appliance, 0.0))
            shift_kwh = float(shiftable.get(appliance, 0.0))
            max_shift_h = APPLIANCE_DEFAULTS[appliance].get("max_shift_hours", 0) if owned else 0.0
            is_shiftable = APPLIANCE_DEFAULTS[appliance].get("is_shiftable", False) if owned else False

            rows.append(
                {
                    "device": appliance,
                    "owned": owned,
                    "is_shiftable": is_shiftable,
                    "scheduled_time": scheduled_time,
                    "flexibility_score": flex_score,
                    "shiftable_kwh": shift_kwh,
                    "shift_window_h": max_shift_h if owned else 0.0,
                }
            )

        return pd.DataFrame(rows).set_index("device")

    # ------------------------------------------------------------------
    # Aggregated household flexibility
    # ------------------------------------------------------------------

    def get_total_shiftable_kwh(self) -> float:
        """Return total shiftable energy across all devices [kWh/week].

        Returns
        -------
        float
        """
        return float(self.get_shiftable_energy_kwh().sum())
