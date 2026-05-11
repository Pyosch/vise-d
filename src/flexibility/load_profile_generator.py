"""
load_profile_generator.py
=========================
Orchestrates ``HouseholdProfile`` creation for all participants in a given
typology class and aggregates individual profiles into a representative
class-level mean ± std band.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from src.flexibility.appliance_defaults import APPLIANCE_DEFAULTS
from src.flexibility.household_profile import HouseholdProfile, REFERENCE_START, SLOTS_PER_WEEK
from src.flexibility.flexibility_model import FlexibilityAssessor
from src.flexibility.seasonal_modifier import SeasonalModifier, SEASON_KEYS

# DatetimeIndex template (7 days, 15-min resolution)
_WEEKLY_INDEX = pd.date_range(start=REFERENCE_START, periods=SLOTS_PER_WEEK, freq="15min")


class LoadProfileGenerator:
    """Generate representative load profiles for household typology classes.

    Parameters
    ----------
    appliance_defaults : dict, optional
        Override for ``APPLIANCE_DEFAULTS``.
    dwd_station_id : str, optional
        DWD station ID passed to ``SeasonalModifier`` for thermal loads.
    """

    def __init__(
        self,
        appliance_defaults: Optional[dict] = None,
        dwd_station_id: Optional[str] = None,
    ) -> None:
        self._defaults = appliance_defaults or APPLIANCE_DEFAULTS
        self._dwd_station_id = dwd_station_id

    # ------------------------------------------------------------------
    # Per-class generation
    # ------------------------------------------------------------------

    def generate_class_profile(
        self,
        typology_class: str,
        df: pd.DataFrame,
        season: str = "transition",
        n_samples: Optional[int] = None,
        calibrate: bool = True,
    ) -> pd.DataFrame:
        """Generate a representative load profile for one typology class.

        Each participant in the class is modelled individually; then the
        class profile is summarised as mean ± 1 std band.

        Parameters
        ----------
        typology_class : str
            Class label (e.g. ``"office_single_manual"``).
        df : pd.DataFrame
            Full feature-engineered + classified DataFrame (must contain
            ``"typology_class"`` column).
        season : str
            Season key.
        n_samples : int, optional
            If provided, randomly sample at most ``n_samples`` participants
            from the class (for large classes).
        calibrate : bool
            Whether to apply ``HouseholdProfile.calibrate()`` to each profile.

        Returns
        -------
        pd.DataFrame
            DataFrame with DatetimeIndex and columns:
            ``mean_power_kw``, ``std_power_kw``, ``min_power_kw``,
            ``max_power_kw``, ``n_households``.

        Raises
        ------
        ValueError
            If ``typology_class`` has no members in ``df``.
        """
        if season not in SEASON_KEYS:
            raise ValueError(f"season must be one of {SEASON_KEYS}, got '{season}'.")

        members = df[df["typology_class"] == typology_class]
        if members.empty:
            raise ValueError(f"No participants found for typology class '{typology_class}'.")

        if n_samples is not None and n_samples < len(members):
            members = members.sample(n=n_samples, random_state=42)

        modifier = SeasonalModifier(season=season, dwd_station_id=self._dwd_station_id)
        all_profiles: list[np.ndarray] = []

        for _, row in members.iterrows():
            try:
                profile_obj = HouseholdProfile(
                    participant_data=row,
                    appliance_defaults=self._defaults,
                    season=season,
                )
                if calibrate:
                    profile_df = profile_obj.calibrate()
                else:
                    profile_df = profile_obj.get_load_profile()

                # Apply seasonal modification to combined profile
                owned = profile_obj.get_owned_appliances()
                profile_df = modifier.modify_profile(profile_df, owned)
                all_profiles.append(profile_df["power_kw"].values)

            except Exception as exc:  # noqa: BLE001
                # Skip problematic rows and log a warning
                import warnings
                pid = row.get("participant.id_in_session", "?")
                warnings.warn(
                    f"Skipping participant {pid} in class '{typology_class}': {exc}",
                    stacklevel=2,
                )

        if not all_profiles:
            raise RuntimeError(f"All profiles failed for class '{typology_class}'.")

        matrix = np.vstack(all_profiles)  # shape: (n_households, 672)

        result = pd.DataFrame(
            {
                "mean_power_kw": matrix.mean(axis=0),
                "std_power_kw": matrix.std(axis=0),
                "min_power_kw": matrix.min(axis=0),
                "max_power_kw": matrix.max(axis=0),
                "n_households": len(all_profiles),
            },
            index=_WEEKLY_INDEX,
        )
        result.index.name = "timestamp"
        return result

    # ------------------------------------------------------------------
    # All-classes generation
    # ------------------------------------------------------------------

    def generate_all_classes(
        self,
        df: pd.DataFrame,
        season: str = "transition",
        n_samples: Optional[int] = None,
        calibrate: bool = True,
        skip_empty: bool = True,
    ) -> dict[str, pd.DataFrame]:
        """Generate profiles for every typology class present in ``df``.

        Parameters
        ----------
        df : pd.DataFrame
            Full classified DataFrame.
        season : str
            Season key.
        n_samples : int, optional
            Max samples per class.
        calibrate : bool
            Apply self-reported consumption calibration.
        skip_empty : bool
            If True, silently skip classes with no members instead of raising.

        Returns
        -------
        dict[str, pd.DataFrame]
            ``{typology_class: class_profile_df}``.
        """
        if "typology_class" not in df.columns:
            raise ValueError("DataFrame must have a 'typology_class' column.")

        classes = df["typology_class"].dropna().unique().tolist()
        result: dict[str, pd.DataFrame] = {}

        for tc in sorted(classes):
            try:
                result[tc] = self.generate_class_profile(
                    typology_class=tc,
                    df=df,
                    season=season,
                    n_samples=n_samples,
                    calibrate=calibrate,
                )
            except (ValueError, RuntimeError) as exc:
                if skip_empty:
                    import warnings
                    warnings.warn(f"Skipping class '{tc}': {exc}", stacklevel=2)
                else:
                    raise

        return result

    # ------------------------------------------------------------------
    # Multi-season generation
    # ------------------------------------------------------------------

    def generate_all_seasons(
        self,
        df: pd.DataFrame,
        n_samples: Optional[int] = None,
        calibrate: bool = True,
    ) -> dict[str, dict[str, pd.DataFrame]]:
        """Generate profiles for all classes and all three seasons.

        Parameters
        ----------
        df : pd.DataFrame
            Full classified DataFrame.
        n_samples : int, optional
            Max samples per class per season.
        calibrate : bool
            Apply calibration.

        Returns
        -------
        dict[str, dict[str, pd.DataFrame]]
            ``{season: {typology_class: class_profile_df}}``.
        """
        return {
            season: self.generate_all_classes(
                df=df,
                season=season,
                n_samples=n_samples,
                calibrate=calibrate,
            )
            for season in SEASON_KEYS
        }

    # ------------------------------------------------------------------
    # Flexibility summary across a class
    # ------------------------------------------------------------------

    def compute_class_flexibility(
        self,
        typology_class: str,
        df: pd.DataFrame,
        season: str = "transition",
    ) -> pd.DataFrame:
        """Aggregate flexibility summaries for a typology class.

        Returns mean shiftable energy, automation factor, and tariff incentive
        across all class members.

        Parameters
        ----------
        typology_class : str
            Class label.
        df : pd.DataFrame
            Full classified DataFrame.
        season : str
            Season key.

        Returns
        -------
        pd.DataFrame
            Columns: device, mean_shiftable_kwh, std_shiftable_kwh,
            mean_flexibility_score, mean_shift_window_h.
        """
        members = df[df["typology_class"] == typology_class]
        if members.empty:
            raise ValueError(f"No participants found for class '{typology_class}'.")

        summaries: list[pd.DataFrame] = []

        for _, row in members.iterrows():
            try:
                profile_obj = HouseholdProfile(
                    participant_data=row,
                    appliance_defaults=self._defaults,
                    season=season,
                )
                assessor = FlexibilityAssessor(
                    profile=profile_obj,
                    participant_row=row,
                )
                summaries.append(assessor.get_flexibility_summary())
            except Exception:  # noqa: BLE001
                pass

        if not summaries:
            raise RuntimeError(f"No flexibility summaries generated for '{typology_class}'.")

        combined = pd.concat(summaries)
        grouped = combined.groupby("device")

        agg = pd.DataFrame(
            {
                "mean_shiftable_kwh": grouped["shiftable_kwh"].mean(),
                "std_shiftable_kwh": grouped["shiftable_kwh"].std(),
                "mean_flexibility_score": grouped["flexibility_score"].mean(),
                "mean_shift_window_h": grouped["shift_window_h"].mean(),
                "n_members": grouped["shiftable_kwh"].count(),
            }
        )
        return agg.reset_index()
