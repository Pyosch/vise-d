"""
Tariff model classes for electricity pricing schemes.

Provides abstract base class and concrete implementations for:
- Time-of-Use (TOU) tariffs
- Real-Time Pricing (RTP) tariffs
- Variable grid fees
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
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
    """Time-of-Use tariff with defined time periods and fixed prices per period."""

    pass


class RTPTariff(BaseTariff):
    """Real-Time Pricing tariff with dynamic prices based on market data."""

    pass


class VariableGridFee:
    """Variable grid fee with energy-based and/or capacity-based components."""

    pass
