"""Smoke tests for the surviving settings / configuration pages.

Earlier revisions also covered ``network_calculations`` and
``openstef_forecasting``; both were removed from the project, so their tests are
gone with them.

What remains is a per-page import-and-callable check. The page functions are
imported directly from their submodules (the ``src.pages`` package is lazy and
exports nothing), so a successful import already exercises the module's
top-level code — catching import errors, missing dependencies and renamed
entrypoints without needing a Streamlit runtime, database or network.
"""

import pytest

from src.pages.research_results import research_results
from src.pages.bev_settings import bev_settings
from src.pages.pv_configuration import pv_configuration
from src.pages.wind_configuration import wind_configuration
from src.pages.heatpump_configuration import heatpump_configuration
from src.pages.electrical_storage_configuration import electrical_storage_configuration

pytestmark = pytest.mark.unit


class TestResearchResults:
    """Tests for research_results page."""

    def test_function_exists(self):
        """Verify research_results imports cleanly and is callable."""
        assert callable(research_results)


class TestBEVSettings:
    """Tests for bev_settings page."""

    def test_function_exists(self):
        """Verify bev_settings imports cleanly and is callable."""
        assert callable(bev_settings)


class TestPVConfiguration:
    """Tests for pv_configuration page."""

    def test_function_exists(self):
        """Verify pv_configuration imports cleanly and is callable."""
        assert callable(pv_configuration)


class TestWindConfiguration:
    """Tests for wind_configuration page."""

    def test_function_exists(self):
        """Verify wind_configuration imports cleanly and is callable."""
        assert callable(wind_configuration)


class TestHeatPumpConfiguration:
    """Tests for heatpump_configuration page."""

    def test_function_exists(self):
        """Verify heatpump_configuration imports cleanly and is callable."""
        assert callable(heatpump_configuration)


class TestElectricalStorageConfiguration:
    """Tests for electrical_storage_configuration page."""

    def test_function_exists(self):
        """Verify electrical_storage_configuration imports cleanly and is callable."""
        assert callable(electrical_storage_configuration)
