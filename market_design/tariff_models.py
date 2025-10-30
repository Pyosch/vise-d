"""
Tariff model classes for electricity pricing schemes.

Provides abstract base class and concrete implementations for:
- Time-of-Use (TOU) tariffs
- Real-Time Pricing (RTP) tariffs
- Variable grid fees

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: October 2025
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict

import pandas as pd


class BaseTariff(ABC):
    """
    Abstract base class for all tariff types.

    All tariff models must implement methods to calculate prices
    and customer bills based on load profiles.
    """

    @abstractmethod
    def calculate_price(self, timestamp: datetime) -> float:
        """
        Calculate the electricity price at a given timestamp.

        Parameters
        ----------
        timestamp : datetime
            The time for which to calculate the price

        Returns
        -------
        float
            Price in €/kWh
        """
        pass

    @abstractmethod
    def calculate_bill(self, load_profile: pd.DataFrame) -> float:
        """
        Calculate the total bill for a customer's load profile.

        Parameters
        ----------
        load_profile : pd.DataFrame
            DataFrame with columns ['timestamp', 'load_kw']

        Returns
        -------
        float
            Total bill in euros
        """
        pass


# Placeholder classes - to be implemented in subsequent tasks
class TOUTariff(BaseTariff):
    """
    Time-of-Use tariff with defined time periods and fixed prices per period.

    This class implements a Time-of-Use (TOU) electricity tariff where different
    prices apply during different time periods of the day (e.g., peak, off-peak).
    Supports weekday-only pricing and midnight boundary crossing.

    Attributes
    ----------
    name : str
        Tariff name for display (e.g., "Residential TOU 3-Period")
    description : str
        Human-readable description of the tariff
    time_periods : Dict[str, str]
        Maps period names to time ranges in format "HH:MM-HH:MM"
        Example: {"peak": "16:00-20:00", "off_peak": "20:00-16:00"}
    prices : Dict[str, float]
        Maps period names to prices in €/kWh
        Example: {"peak": 0.35, "off_peak": 0.15}
    weekday_only : bool
        If True, peak/off-peak applies only on weekdays (Mon-Fri).
        Weekends use the lowest priced period.

    Examples
    --------
    Create a simple 2-period TOU tariff:

    >>> tou = TOUTariff(
    ...     time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
    ...     prices={"peak": 0.35, "off_peak": 0.15},
    ...     name="Residential TOU 2-Period"
    ... )
    >>> price = tou.calculate_price(datetime(2025, 10, 30, 18, 0))
    >>> print(f"Price at 6 PM: €{price:.2f}/kWh")
    Price at 6 PM: €0.35/kWh

    Create a 3-period TOU tariff:

    >>> tou_3 = TOUTariff(
    ...     time_periods={
    ...         "peak": "16:00-20:00",
    ...         "mid_peak": "08:00-16:00",
    ...         "off_peak": "20:00-08:00"
    ...     },
    ...     prices={"peak": 0.35, "mid_peak": 0.25, "off_peak": 0.15},
    ...     name="Residential TOU 3-Period"
    ... )
    """

    TIME_PATTERN = re.compile(
        r"^([0-1][0-9]|2[0-3]):([0-5][0-9])-([0-1][0-9]|2[0-3]):([0-5][0-9])$"
    )

    def __init__(
        self,
        time_periods: Dict[str, str],
        prices: Dict[str, float],
        name: str,
        description: str = "",
        weekday_only: bool = False,
    ):
        """
        Initialize a Time-of-Use tariff.

        Parameters
        ----------
        time_periods : Dict[str, str]
            Maps period names to time ranges in format "HH:MM-HH:MM"
        prices : Dict[str, float]
            Maps period names to prices in €/kWh (must be > 0)
        name : str
            Tariff name for display
        description : str, optional
            Human-readable description, by default ""
        weekday_only : bool, optional
            If True, weekends use lowest priced period, by default False

        Raises
        ------
        ValueError
            If validation fails (price validation, time format, mismatched names)
        """
        self.name = name
        self.description = description
        self.weekday_only = weekday_only

        # Validate that period names match
        if set(time_periods.keys()) != set(prices.keys()):
            raise ValueError(
                f"Period names in time_periods and prices must match. "
                f"time_periods has {set(time_periods.keys())}, "
                f"prices has {set(prices.keys())}"
            )

        # Validate time format and prices
        for period_name, time_range in time_periods.items():
            self._validate_time_format(time_range, period_name)

        for period_name, price in prices.items():
            if price <= 0:
                raise ValueError(
                    f"Price must be positive, got {price} for period {period_name}"
                )

        self.time_periods = time_periods.copy()
        self.prices = prices.copy()

        # Parse time periods into start/end times for efficient lookup
        self._parsed_periods: Dict[str, tuple] = {}
        for period_name, time_range in self.time_periods.items():
            start_str, end_str = time_range.split("-")
            start_time = datetime.strptime(start_str, "%H:%M").time()
            end_time = datetime.strptime(end_str, "%H:%M").time()
            self._parsed_periods[period_name] = (start_time, end_time)

        # Find the off-peak period (lowest price) for weekends
        self._off_peak_period = min(self.prices.keys(), key=lambda k: self.prices[k])

    def _validate_time_format(self, time_range: str, period_name: str) -> None:
        """
        Validate that time range matches format "HH:MM-HH:MM".

        Parameters
        ----------
        time_range : str
            Time range string to validate
        period_name : str
            Period name for error messages

        Raises
        ------
        ValueError
            If time format is invalid
        """
        if not self.TIME_PATTERN.match(time_range):
            raise ValueError(
                f"Invalid time format for period '{period_name}': '{time_range}'. "
                f"Expected format 'HH:MM-HH:MM' (e.g., '16:00-20:00')"
            )

    def calculate_price(self, timestamp: datetime) -> float:
        """
        Calculate the electricity price at a given timestamp.

        Parameters
        ----------
        timestamp : datetime
            The time for which to calculate the price

        Returns
        -------
        float
            Price in €/kWh

        Raises
        ------
        ValueError
            If timestamp has no matching period (should not happen with valid tariff)

        Examples
        --------
        >>> tou = TOUTariff(
        ...     time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
        ...     prices={"peak": 0.35, "off_peak": 0.15},
        ...     name="Test TOU"
        ... )
        >>> tou.calculate_price(datetime(2025, 10, 30, 18, 0))  # 6 PM
        0.35
        >>> tou.calculate_price(datetime(2025, 10, 30, 22, 0))  # 10 PM
        0.15
        """
        period = self.get_period_at_time(timestamp)
        return self.prices[period]

    def calculate_bill(self, load_profile: pd.DataFrame) -> float:
        """
        Calculate the total bill for a customer's load profile.

        Parameters
        ----------
        load_profile : pd.DataFrame
            DataFrame with columns ['timestamp', 'load_kw']

        Returns
        -------
        float
            Total bill in euros

        Raises
        ------
        ValueError
            If required columns are missing from load_profile

        Examples
        --------
        >>> import pandas as pd
        >>> from datetime import datetime
        >>> tou = TOUTariff(
        ...     time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
        ...     prices={"peak": 0.35, "off_peak": 0.15},
        ...     name="Test TOU"
        ... )
        >>> load_df = pd.DataFrame({
        ...     'timestamp': pd.date_range('2025-10-30', periods=24, freq='h'),
        ...     'load_kw': [2.5] * 24
        ... })
        >>> bill = tou.calculate_bill(load_df)
        """
        # Validate required columns
        required_cols = ["timestamp", "load_kw"]
        missing_cols = [col for col in required_cols if col not in load_profile.columns]
        if missing_cols:
            raise ValueError(
                f"Load profile missing required columns: {missing_cols}. "
                f"Expected columns: {required_cols}"
            )

        # Handle empty DataFrame
        if len(load_profile) == 0:
            return 0.0

        # Calculate price for each timestamp using vectorized operations
        load_profile = load_profile.copy()
        load_profile["price"] = load_profile["timestamp"].apply(self.calculate_price)
        load_profile["cost"] = load_profile["load_kw"] * load_profile["price"]

        return float(load_profile["cost"].sum())

    def add_time_period(self, period_name: str, time_range: str, price: float) -> None:
        """
        Add or update a time period.

        Parameters
        ----------
        period_name : str
            Name of the period to add/update
        time_range : str
            Time range in format "HH:MM-HH:MM"
        price : float
            Price in €/kWh (must be > 0)

        Raises
        ------
        ValueError
            If time format is invalid or price is not positive

        Examples
        --------
        >>> tou = TOUTariff(
        ...     time_periods={"off_peak": "00:00-23:59"},
        ...     prices={"off_peak": 0.15},
        ...     name="Flat Rate"
        ... )
        >>> tou.add_time_period("peak", "16:00-20:00", 0.35)
        """
        self._validate_time_format(time_range, period_name)

        if price <= 0:
            raise ValueError(
                f"Price must be positive, got {price} for period {period_name}"
            )

        self.time_periods[period_name] = time_range
        self.prices[period_name] = price

        # Update parsed periods
        start_str, end_str = time_range.split("-")
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()
        self._parsed_periods[period_name] = (start_time, end_time)

        # Update off-peak period
        self._off_peak_period = min(self.prices.keys(), key=lambda k: self.prices[k])

    def remove_time_period(self, period_name: str) -> None:
        """
        Remove a time period.

        Parameters
        ----------
        period_name : str
            Name of the period to remove

        Raises
        ------
        ValueError
            If this is the last period or period doesn't exist

        Examples
        --------
        >>> tou = TOUTariff(
        ...     time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
        ...     prices={"peak": 0.35, "off_peak": 0.15},
        ...     name="Test TOU"
        ... )
        >>> tou.remove_time_period("peak")
        """
        if period_name not in self.time_periods:
            raise ValueError(f"Period '{period_name}' does not exist")

        if len(self.time_periods) == 1:
            raise ValueError(
                "Cannot remove the last time period. At least one period must remain."
            )

        del self.time_periods[period_name]
        del self.prices[period_name]
        del self._parsed_periods[period_name]

        # Update off-peak period
        self._off_peak_period = min(self.prices.keys(), key=lambda k: self.prices[k])

    def validate_periods(self) -> bool:
        """
        Check that time periods cover full 24 hours without gaps or overlaps.

        Returns
        -------
        bool
            True if periods are valid

        Raises
        ------
        ValueError
            If periods have gaps, overlaps, or don't cover 24 hours

        Notes
        -----
        This is a simplified validation that checks if we have continuous coverage.
        For complex tariffs with many periods, manual verification may be needed.
        """
        # For a single period that should cover 24 hours
        if len(self.time_periods) == 1:
            return True

        # Create a minute-by-minute coverage array
        coverage = [False] * (24 * 60)

        for period_name, (start_time, end_time) in self._parsed_periods.items():
            start_minutes = start_time.hour * 60 + start_time.minute
            end_minutes = end_time.hour * 60 + end_time.minute

            # Handle midnight crossing
            if end_minutes <= start_minutes:
                # Covers from start to midnight
                for i in range(start_minutes, 24 * 60):
                    if coverage[i]:
                        raise ValueError(
                            f"Time period overlap detected in period '{period_name}'"
                        )
                    coverage[i] = True
                # Covers from midnight to end
                for i in range(0, end_minutes):
                    if coverage[i]:
                        raise ValueError(
                            f"Time period overlap detected in period '{period_name}'"
                        )
                    coverage[i] = True
            else:
                # Normal range within same day
                for i in range(start_minutes, end_minutes):
                    if coverage[i]:
                        raise ValueError(
                            f"Time period overlap detected in period '{period_name}'"
                        )
                    coverage[i] = True

        # Check for gaps
        if not all(coverage):
            first_gap = coverage.index(False)
            gap_hour = first_gap // 60
            gap_minute = first_gap % 60
            raise ValueError(
                f"Time period gap detected at {gap_hour:02d}:{gap_minute:02d}. "
                f"All 24 hours must be covered."
            )

        return True

    def get_period_at_time(self, timestamp: datetime) -> str:
        """
        Return the period name for a given timestamp.

        Parameters
        ----------
        timestamp : datetime
            The time to check

        Returns
        -------
        str
            Period name

        Raises
        ------
        ValueError
            If timestamp has no matching period

        Examples
        --------
        >>> tou = TOUTariff(
        ...     time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
        ...     prices={"peak": 0.35, "off_peak": 0.15},
        ...     name="Test TOU"
        ... )
        >>> tou.get_period_at_time(datetime(2025, 10, 30, 18, 0))
        'peak'
        """
        # Check if weekday_only and it's a weekend
        if self.weekday_only and timestamp.weekday() >= 5:  # 5=Saturday, 6=Sunday
            return self._off_peak_period

        current_time = timestamp.time()

        for period_name, (start_time, end_time) in self._parsed_periods.items():
            # Handle midnight crossing (e.g., 22:00-06:00)
            if end_time <= start_time:
                if current_time >= start_time or current_time < end_time:
                    return period_name
            else:
                # Normal range within same day
                if start_time <= current_time < end_time:
                    return period_name

        raise ValueError(
            f"No matching period found for timestamp {timestamp}. "
            f"This indicates incomplete time period coverage."
        )

    def get_price_schedule(self, start_date: datetime, days: int = 1) -> pd.DataFrame:
        """
        Generate a DataFrame with hourly prices for given date range.

        Parameters
        ----------
        start_date : datetime
            Starting date/time
        days : int, optional
            Number of days to generate schedule for, by default 1

        Returns
        -------
        pd.DataFrame
            DataFrame with columns ['timestamp', 'period', 'price_euro_per_kwh']

        Examples
        --------
        >>> tou = TOUTariff(
        ...     time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
        ...     prices={"peak": 0.35, "off_peak": 0.15},
        ...     name="Test TOU"
        ... )
        >>> schedule = tou.get_price_schedule(datetime(2025, 10, 30), days=1)
        >>> len(schedule)
        24
        """
        timestamps = pd.date_range(start=start_date, periods=days * 24, freq="h")

        periods = [self.get_period_at_time(ts) for ts in timestamps]
        prices = [self.prices[period] for period in periods]

        return pd.DataFrame(
            {"timestamp": timestamps, "period": periods, "price_euro_per_kwh": prices}
        )


class RTPTariff(BaseTariff):
    """Real-Time Pricing tariff with dynamic prices based on market data."""

    pass


class VariableGridFee:
    """Variable grid fee with energy-based and/or capacity-based components."""

    pass
