"""Smoke tests for the surviving MaStR and thermal-storage pages.

Earlier revisions also covered ``energy_generation_solar``,
``wind_energy_generation`` and the hydrogen pages; those were consolidated into
the ``*_installation_mastr`` pages or removed from the project, so their tests
are gone with them.

What remains is a per-page import-and-callable check. The page functions are
imported directly from their submodules (the ``src.pages`` package is lazy and
exports nothing), so a successful import already exercises the module's
top-level code — catching import errors, missing dependencies and renamed
entrypoints without needing a Streamlit runtime, database or network.
"""

import pytest

from src.pages.solar_installation_mastr import solar_installation_mastr
from src.pages.wind_installation_mastr import wind_installation_mastr
from src.pages.storage_installation_mastr import storage_installation_mastr
from src.pages.thermal_storage_settings import thermal_storage_settings

pytestmark = pytest.mark.unit


class TestSolarInstallationMastr:
    """Tests for solar_installation_mastr page."""

    def test_function_exists(self):
        """Verify solar_installation_mastr imports cleanly and is callable."""
        assert callable(solar_installation_mastr)


class TestWindInstallationMastr:
    """Tests for wind_installation_mastr page."""

    def test_function_exists(self):
        """Verify wind_installation_mastr imports cleanly and is callable."""
        assert callable(wind_installation_mastr)


class TestStorageInstallationMastr:
    """Tests for storage_installation_mastr page."""

    def test_function_exists(self):
        """Verify storage_installation_mastr imports cleanly and is callable."""
        assert callable(storage_installation_mastr)


class TestThermalStorageSettings:
    """Tests for thermal_storage_settings page."""

    def test_function_exists(self):
        """Verify thermal_storage_settings imports cleanly and is callable."""
        assert callable(thermal_storage_settings)
