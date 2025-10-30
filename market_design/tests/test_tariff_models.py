"""
Unit tests for tariff_models module.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: October 2025
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

from datetime import datetime

import pandas as pd
import pytest

from market_design.tariff_models import BaseTariff, TOUTariff


# =============================================================================
# Normal Operation Tests
# =============================================================================


def test_tou_tariff_2_period():
    """Test basic 2-period TOU tariff (peak/off-peak)."""
    tou = TOUTariff(
        time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
        prices={"peak": 0.35, "off_peak": 0.15},
        name="Residential TOU 2-Period",
        description="Basic peak/off-peak tariff",
    )

    # Test peak period
    peak_price = tou.calculate_price(datetime(2025, 10, 30, 18, 0))
    assert peak_price == 0.35

    # Test off-peak period (evening)
    off_peak_price = tou.calculate_price(datetime(2025, 10, 30, 22, 0))
    assert off_peak_price == 0.15

    # Test off-peak period (morning)
    morning_price = tou.calculate_price(datetime(2025, 10, 30, 8, 0))
    assert morning_price == 0.15


def test_tou_tariff_3_period():
    """Test 3-period TOU tariff (peak/mid-peak/off-peak)."""
    tou = TOUTariff(
        time_periods={
            "peak": "16:00-20:00",
            "mid_peak": "08:00-16:00",
            "off_peak": "20:00-08:00",
        },
        prices={"peak": 0.35, "mid_peak": 0.25, "off_peak": 0.15},
        name="Residential TOU 3-Period",
    )

    # Test all three periods
    assert tou.calculate_price(datetime(2025, 10, 30, 18, 0)) == 0.35  # peak
    assert tou.calculate_price(datetime(2025, 10, 30, 12, 0)) == 0.25  # mid-peak
    assert tou.calculate_price(datetime(2025, 10, 30, 22, 0)) == 0.15  # off-peak
    assert tou.calculate_price(datetime(2025, 10, 30, 3, 0)) == 0.15  # off-peak night


def test_calculate_bill_simple():
    """Test bill calculation with uniform load profile."""
    tou = TOUTariff(
        time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
        prices={"peak": 0.35, "off_peak": 0.15},
        name="Test TOU",
    )

    # 24 hours at 2.5 kW constant load
    # 4 hours peak (16:00-20:00): 4 * 2.5 * 0.35 = 3.50
    # 20 hours off-peak: 20 * 2.5 * 0.15 = 7.50
    # Total: 11.00 euros
    load_df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-10-30", periods=24, freq="h"),
            "load_kw": [2.5] * 24,
        }
    )

    bill = tou.calculate_bill(load_df)
    expected = 4 * 2.5 * 0.35 + 20 * 2.5 * 0.15
    assert abs(bill - expected) < 0.01  # Allow small floating point error


# =============================================================================
# Edge Cases Tests
# =============================================================================


def test_midnight_boundary():
    """Test time period crossing midnight (e.g., '22:00-06:00')."""
    tou = TOUTariff(
        time_periods={"night": "22:00-06:00", "day": "06:00-22:00"},
        prices={"night": 0.12, "day": 0.25},
        name="Day/Night Tariff",
    )

    # Test times around midnight
    assert tou.calculate_price(datetime(2025, 10, 30, 23, 59)) == 0.12  # night
    assert tou.calculate_price(datetime(2025, 10, 31, 0, 0)) == 0.12  # night
    assert tou.calculate_price(datetime(2025, 10, 31, 0, 1)) == 0.12  # night
    assert tou.calculate_price(datetime(2025, 10, 31, 5, 59)) == 0.12  # night
    assert tou.calculate_price(datetime(2025, 10, 31, 6, 0)) == 0.25  # day
    assert tou.calculate_price(datetime(2025, 10, 31, 21, 59)) == 0.25  # day


def test_single_period_flat_rate():
    """Test tariff with single period (equivalent to flat rate)."""
    tou = TOUTariff(
        time_periods={"flat": "00:00-23:59"},
        prices={"flat": 0.20},
        name="Flat Rate",
    )

    # All times should return same price
    assert tou.calculate_price(datetime(2025, 10, 30, 0, 0)) == 0.20
    assert tou.calculate_price(datetime(2025, 10, 30, 12, 0)) == 0.20
    assert tou.calculate_price(datetime(2025, 10, 30, 23, 0)) == 0.20


def test_weekday_only_flag():
    """Test weekday_only behavior on Saturday/Sunday."""
    tou = TOUTariff(
        time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
        prices={"peak": 0.35, "off_peak": 0.15},
        name="Weekday TOU",
        weekday_only=True,
    )

    # Thursday (weekday) - should use normal periods
    assert tou.calculate_price(datetime(2025, 10, 30, 18, 0)) == 0.35  # peak
    assert tou.calculate_price(datetime(2025, 10, 30, 22, 0)) == 0.15  # off-peak

    # Saturday (weekend) - should use off-peak for all times
    assert tou.calculate_price(datetime(2025, 11, 1, 18, 0)) == 0.15  # would be peak
    assert tou.calculate_price(datetime(2025, 11, 1, 22, 0)) == 0.15  # off-peak

    # Sunday (weekend) - should use off-peak for all times
    assert tou.calculate_price(datetime(2025, 11, 2, 18, 0)) == 0.15  # would be peak


def test_bill_calculation_multi_day():
    """Test bill calculation over multiple days."""
    tou = TOUTariff(
        time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
        prices={"peak": 0.35, "off_peak": 0.15},
        name="Test TOU",
    )

    # 3 days of hourly data (72 hours)
    load_df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-10-30", periods=72, freq="h"),
            "load_kw": [2.0] * 72,
        }
    )

    bill = tou.calculate_bill(load_df)

    # Each day: 4 hours peak @ 0.35, 20 hours off-peak @ 0.15
    # Daily cost: 4 * 2.0 * 0.35 + 20 * 2.0 * 0.15 = 2.80 + 6.00 = 8.80
    # 3 days: 8.80 * 3 = 26.40
    expected = 3 * (4 * 2.0 * 0.35 + 20 * 2.0 * 0.15)
    assert abs(bill - expected) < 0.01


# =============================================================================
# Error Cases Tests
# =============================================================================


def test_negative_price_raises_error():
    """Test that negative price raises ValueError."""
    with pytest.raises(ValueError, match="Price must be positive"):
        TOUTariff(
            time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
            prices={"peak": -0.35, "off_peak": 0.15},
            name="Invalid Tariff",
        )


def test_zero_price_raises_error():
    """Test that zero price raises ValueError."""
    with pytest.raises(ValueError, match="Price must be positive"):
        TOUTariff(
            time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
            prices={"peak": 0.0, "off_peak": 0.15},
            name="Invalid Tariff",
        )


def test_invalid_time_format_raises_error():
    """Test that invalid time format raises ValueError."""
    with pytest.raises(ValueError, match="Invalid time format"):
        TOUTariff(
            time_periods={"peak": "16-20", "off_peak": "20:00-16:00"},
            prices={"peak": 0.35, "off_peak": 0.15},
            name="Invalid Tariff",
        )

    with pytest.raises(ValueError, match="Invalid time format"):
        TOUTariff(
            time_periods={"peak": "16:00-20:00", "off_peak": "25:00-16:00"},
            prices={"peak": 0.35, "off_peak": 0.15},
            name="Invalid Tariff",
        )


def test_mismatched_period_names():
    """Test that mismatched period names raise ValueError."""
    with pytest.raises(ValueError, match="Period names.*must match"):
        TOUTariff(
            time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
            prices={"Peak": 0.35, "off_peak": 0.15},  # Case mismatch
            name="Invalid Tariff",
        )


def test_missing_load_profile_columns():
    """Test that missing DataFrame columns raise ValueError."""
    tou = TOUTariff(
        time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
        prices={"peak": 0.35, "off_peak": 0.15},
        name="Test TOU",
    )

    # DataFrame missing 'load_kw' column
    load_df = pd.DataFrame(
        {"timestamp": pd.date_range("2025-10-30", periods=24, freq="h")}
    )

    with pytest.raises(ValueError, match="missing required columns"):
        tou.calculate_bill(load_df)


def test_empty_load_profile():
    """Test handling of empty DataFrame."""
    tou = TOUTariff(
        time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
        prices={"peak": 0.35, "off_peak": 0.15},
        name="Test TOU",
    )

    load_df = pd.DataFrame({"timestamp": [], "load_kw": []})
    bill = tou.calculate_bill(load_df)
    assert bill == 0.0


# =============================================================================
# Method Tests (add_time_period, remove_time_period, etc.)
# =============================================================================


def test_add_time_period():
    """Test adding a new time period."""
    tou = TOUTariff(
        time_periods={"off_peak": "00:00-23:59"},
        prices={"off_peak": 0.15},
        name="Flat Rate",
    )

    tou.add_time_period("peak", "16:00-20:00", 0.35)

    assert "peak" in tou.time_periods
    assert tou.prices["peak"] == 0.35


def test_add_time_period_updates_existing():
    """Test updating an existing time period."""
    tou = TOUTariff(
        time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
        prices={"peak": 0.35, "off_peak": 0.15},
        name="Test TOU",
    )

    tou.add_time_period("peak", "15:00-19:00", 0.40)

    assert tou.time_periods["peak"] == "15:00-19:00"
    assert tou.prices["peak"] == 0.40


def test_add_time_period_invalid_price():
    """Test that add_time_period rejects negative prices."""
    tou = TOUTariff(
        time_periods={"off_peak": "00:00-23:59"},
        prices={"off_peak": 0.15},
        name="Test TOU",
    )

    with pytest.raises(ValueError, match="Price must be positive"):
        tou.add_time_period("peak", "16:00-20:00", -0.35)


def test_remove_time_period():
    """Test removing a time period."""
    tou = TOUTariff(
        time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
        prices={"peak": 0.35, "off_peak": 0.15},
        name="Test TOU",
    )

    tou.remove_time_period("peak")

    assert "peak" not in tou.time_periods
    assert "peak" not in tou.prices
    assert "off_peak" in tou.time_periods


def test_remove_last_period_raises_error():
    """Test that removing the last period raises ValueError."""
    tou = TOUTariff(
        time_periods={"flat": "00:00-23:59"},
        prices={"flat": 0.20},
        name="Flat Rate",
    )

    with pytest.raises(ValueError, match="Cannot remove the last time period"):
        tou.remove_time_period("flat")


def test_remove_nonexistent_period_raises_error():
    """Test that removing a nonexistent period raises ValueError."""
    tou = TOUTariff(
        time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
        prices={"peak": 0.35, "off_peak": 0.15},
        name="Test TOU",
    )

    with pytest.raises(ValueError, match="does not exist"):
        tou.remove_time_period("mid_peak")


def test_validate_periods_no_overlap():
    """Test validate_periods with non-overlapping periods."""
    tou = TOUTariff(
        time_periods={
            "morning": "06:00-12:00",
            "afternoon": "12:00-18:00",
            "evening": "18:00-00:00",
            "night": "00:00-06:00",
        },
        prices={"morning": 0.20, "afternoon": 0.25, "evening": 0.30, "night": 0.15},
        name="Test TOU",
    )

    assert tou.validate_periods() is True


def test_validate_periods_single_period():
    """Test validate_periods with single period."""
    tou = TOUTariff(
        time_periods={"flat": "00:00-23:59"},
        prices={"flat": 0.20},
        name="Flat Rate",
    )

    assert tou.validate_periods() is True


def test_get_period_at_time():
    """Test get_period_at_time method."""
    tou = TOUTariff(
        time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
        prices={"peak": 0.35, "off_peak": 0.15},
        name="Test TOU",
    )

    assert tou.get_period_at_time(datetime(2025, 10, 30, 18, 0)) == "peak"
    assert tou.get_period_at_time(datetime(2025, 10, 30, 22, 0)) == "off_peak"
    assert tou.get_period_at_time(datetime(2025, 10, 30, 8, 0)) == "off_peak"


def test_get_price_schedule():
    """Test get_price_schedule method."""
    tou = TOUTariff(
        time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
        prices={"peak": 0.35, "off_peak": 0.15},
        name="Test TOU",
    )

    schedule = tou.get_price_schedule(datetime(2025, 10, 30), days=1)

    assert len(schedule) == 24
    assert list(schedule.columns) == ["timestamp", "period", "price_euro_per_kwh"]
    assert schedule["price_euro_per_kwh"].iloc[18] == 0.35  # 6 PM = peak
    assert schedule["price_euro_per_kwh"].iloc[22] == 0.15  # 10 PM = off-peak


def test_get_price_schedule_multi_day():
    """Test get_price_schedule for multiple days."""
    tou = TOUTariff(
        time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
        prices={"peak": 0.35, "off_peak": 0.15},
        name="Test TOU",
    )

    schedule = tou.get_price_schedule(datetime(2025, 10, 30), days=3)

    assert len(schedule) == 72  # 24 hours * 3 days
    assert schedule["timestamp"].min() == pd.Timestamp("2025-10-30 00:00:00")
    assert schedule["timestamp"].max() == pd.Timestamp("2025-11-01 23:00:00")


# =============================================================================
# Additional Coverage Tests
# =============================================================================


def test_tariff_inherits_from_base():
    """Test that TOUTariff properly inherits from BaseTariff."""
    tou = TOUTariff(
        time_periods={"flat": "00:00-23:59"},
        prices={"flat": 0.20},
        name="Test",
    )

    assert isinstance(tou, BaseTariff)


def test_tariff_attributes():
    """Test that tariff attributes are properly set."""
    tou = TOUTariff(
        time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
        prices={"peak": 0.35, "off_peak": 0.15},
        name="Test Tariff",
        description="A test tariff for unit tests",
        weekday_only=True,
    )

    assert tou.name == "Test Tariff"
    assert tou.description == "A test tariff for unit tests"
    assert tou.weekday_only is True
    assert tou.time_periods == {"peak": "16:00-20:00", "off_peak": "20:00-16:00"}
    assert tou.prices == {"peak": 0.35, "off_peak": 0.15}


def test_tariff_copies_input_dicts():
    """Test that tariff creates copies of input dictionaries."""
    time_periods = {"peak": "16:00-20:00", "off_peak": "20:00-16:00"}
    prices = {"peak": 0.35, "off_peak": 0.15}

    tou = TOUTariff(
        time_periods=time_periods,
        prices=prices,
        name="Test",
    )

    # Modify original dicts
    time_periods["peak"] = "15:00-19:00"
    prices["peak"] = 0.40

    # Tariff should be unchanged
    assert tou.time_periods["peak"] == "16:00-20:00"
    assert tou.prices["peak"] == 0.35


def test_validate_periods_with_overlap_raises_error():
    """Test that overlapping periods raise ValueError."""
    # Create tariff with overlapping periods
    # This will be detected during validation
    tou = TOUTariff(
        time_periods={
            "morning": "06:00-14:00",  # Overlaps with afternoon at 12:00
            "afternoon": "12:00-18:00",
            "evening": "18:00-00:00",
            "night": "00:00-06:00",
        },
        prices={"morning": 0.20, "afternoon": 0.25, "evening": 0.30, "night": 0.15},
        name="Overlapping Tariff",
    )

    # validate_periods should detect the overlap
    with pytest.raises(ValueError, match="Time period overlap detected"):
        tou.validate_periods()


def test_validate_periods_with_gap_raises_error():
    """Test that gaps in time coverage raise ValueError."""
    # Create tariff with a gap (missing 14:00-16:00)
    tou = TOUTariff(
        time_periods={
            "morning": "06:00-14:00",
            "afternoon": "16:00-18:00",  # Gap from 14:00-16:00
            "evening": "18:00-00:00",
            "night": "00:00-06:00",
        },
        prices={"morning": 0.20, "afternoon": 0.25, "evening": 0.30, "night": 0.15},
        name="Gap Tariff",
    )

    # validate_periods should detect the gap
    with pytest.raises(ValueError, match="Time period gap detected"):
        tou.validate_periods()


def test_validate_periods_with_midnight_crossing():
    """Test validate_periods with midnight-crossing period."""
    tou = TOUTariff(
        time_periods={
            "day": "06:00-22:00",
            "night": "22:00-06:00",  # Crosses midnight
        },
        prices={"day": 0.25, "night": 0.15},
        name="Day/Night Tariff",
    )

    assert tou.validate_periods() is True


def test_bill_calculation_with_varying_loads():
    """Test bill calculation with varying load profile."""
    tou = TOUTariff(
        time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
        prices={"peak": 0.35, "off_peak": 0.15},
        name="Test TOU",
    )

    # Create load profile with varying loads
    loads = [1.0] * 16 + [5.0] * 4 + [2.0] * 4  # Low load, then high peak, then medium
    load_df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-10-30", periods=24, freq="h"),
            "load_kw": loads,
        }
    )

    bill = tou.calculate_bill(load_df)

    # 16 hours @ 1.0 kW @ 0.15 = 2.40
    # 4 hours @ 5.0 kW @ 0.35 = 7.00 (peak period 16:00-20:00)
    # 4 hours @ 2.0 kW @ 0.15 = 1.20
    # Total = 10.60
    expected = 16 * 1.0 * 0.15 + 4 * 5.0 * 0.35 + 4 * 2.0 * 0.15
    assert abs(bill - expected) < 0.01
