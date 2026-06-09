"""Tests for the device-level flexibility base-load helpers."""

import numpy as np
import pandas as pd
import pytest

from src.utils import flex_baseload as fb


# --------------------------------------------------------------------------- #
# Season mapping
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("month,expected", [
    (1, "winter"), (2, "winter"), (12, "winter"),
    (6, "summer"), (7, "summer"), (8, "summer"),
    (3, "transition"), (5, "transition"), (9, "transition"), (11, "transition"),
])
def test_season_for_month(month, expected):
    assert fb.get_season_for_month(month) == expected


def test_season_for_date():
    assert fb.get_season_for_date(pd.Timestamp("2024-01-15")) == "winter"
    assert fb.get_season_for_date(pd.Timestamp("2024-07-15")) == "summer"


# --------------------------------------------------------------------------- #
# Profile loading
# --------------------------------------------------------------------------- #

def test_load_profiles_shape_and_classes():
    df = fb.load_flex_profiles("transition")
    assert len(df) == fb.SLOTS_PER_WEEK
    classes = fb.available_classes("transition")
    assert len(classes) == 10
    # every class has both a baseline and a shifted column
    for cls in classes:
        assert f"{cls}__baseline_kw" in df.columns
        assert f"{cls}__shifted_kw" in df.columns


def test_baseline_shifted_energy_conserved():
    """The device-level shift moves energy in time but conserves the weekly total."""
    for cls in fb.available_classes("winter"):
        base, shifted = fb.household_curves(cls, "winter")
        assert base.sum() == pytest.approx(shifted.sum(), rel=1e-6)


# --------------------------------------------------------------------------- #
# Class assignment
# --------------------------------------------------------------------------- #

def test_assign_classes_is_seeded_and_deterministic():
    classes = fb.available_classes()
    a = fb.assign_classes([0, 1, 2, 3], classes, seed=42)
    b = fb.assign_classes([0, 1, 2, 3], classes, seed=42)
    assert a == b
    assert set(a.values()) <= set(classes)


def test_assign_classes_manual_override():
    classes = fb.available_classes()
    manual = {1: classes[0]}
    out = fb.assign_classes([0, 1, 2], classes, seed=7, manual=manual)
    assert out[1] == classes[0]


# --------------------------------------------------------------------------- #
# Horizon construction + nameplate calibration
# --------------------------------------------------------------------------- #

def test_build_load_curves_peak_calibrated_to_nameplate():
    classes = fb.available_classes()
    assigned = {0: classes[0], 1: classes[1]}
    nameplates = {0: 30.0, 1: 12.0}  # kW
    base, shifted, counts = fb.build_load_curves(
        nameplates, assigned, start_date=pd.Timestamp("2024-03-04"), n_steps=672
    )
    for lid, p_kw in nameplates.items():
        assert base[lid].shape == (672,)
        assert float(base[lid].max()) == pytest.approx(p_kw, rel=1e-6)
        assert counts[lid] >= 1


def test_build_load_curves_preserves_shift_relationship():
    """Baseline and shifted share the same per-load scalar → equal energy."""
    classes = fb.available_classes()
    assigned = {0: classes[0]}
    base, shifted, _ = fb.build_load_curves(
        {0: 25.0}, assigned, start_date=pd.Timestamp("2024-03-04"), n_steps=672
    )
    assert base[0].sum() == pytest.approx(shifted[0].sum(), rel=1e-6)


def test_build_load_curves_arbitrary_horizon_length():
    classes = fb.available_classes()
    assigned = {0: classes[0]}
    for n_steps in (96, 672, 1000, 2688):
        base, shifted, _ = fb.build_load_curves(
            {0: 10.0}, assigned, start_date=pd.Timestamp("2024-06-01"), n_steps=n_steps
        )
        assert base[0].shape == (n_steps,)
        assert shifted[0].shape == (n_steps,)


# --------------------------------------------------------------------------- #
# Interpolation + window shifting
# --------------------------------------------------------------------------- #

def test_interpolate_endpoints():
    base = np.array([1.0, 2.0, 3.0])
    shifted = np.array([3.0, 2.0, 1.0])
    np.testing.assert_allclose(fb.interpolate(base, shifted, 0.0), base)
    np.testing.assert_allclose(fb.interpolate(base, shifted, 1.0), shifted)
    np.testing.assert_allclose(fb.interpolate(base, shifted, 0.5), [2.0, 2.0, 2.0])


def test_shift_window_slots():
    assert fb.shift_window_slots("EV") == 40   # 10 h
    assert fb.shift_window_slots("HP") == 16    # 4 h
    assert fb.shift_window_slots("unknown") == 0


def test_fully_shift_conserves_energy_and_lowers_peak():
    rng = np.random.default_rng(0)
    profile = np.zeros(96)
    profile[40:48] = 10.0  # a tall midday block
    shifted = fb.fully_shift_within_window(profile, window_slots=16)
    assert shifted.sum() == pytest.approx(profile.sum(), rel=1e-9)
    assert shifted.max() < profile.max()
    assert np.all(shifted >= -1e-9)


def test_apply_profile_shift_alpha_zero_is_identity():
    profile = np.array([0.0, 5.0, 0.0, 0.0, 5.0, 0.0])
    out = fb.apply_profile_shift(profile, window_slots=2, alpha=0.0)
    np.testing.assert_allclose(out, profile)


def test_shift_device_profile_partial_between_endpoints():
    profile = np.zeros(96)
    profile[44:48] = 8.0
    full = fb.shift_device_profile(profile, "EV", alpha=1.0)
    half = fb.shift_device_profile(profile, "EV", alpha=0.5)
    # half-shift peak lies between original and full-shift peak
    assert full.max() <= half.max() <= profile.max()
    assert half.sum() == pytest.approx(profile.sum(), rel=1e-9)
