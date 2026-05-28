"""Tests that src.pages does not eagerly load page modules."""

import pytest


_PAGE_FUNCTION_NAMES = [
    'research_results',
    'bev_settings',
    'pv_configuration',
    'wind_configuration',
    'heatpump_configuration',
    'electrical_storage_configuration',
    'thermal_storage_settings',
    'solar_installation_mastr',
    'wind_installation_mastr',
    'storage_installation_mastr',
    'energy_generation_solar',
    'wind_energy_generation',
    'flexibility_configurator',
    'netzmodell',
    'mv_fallstudie',
]


def test_pages_init_does_not_expose_page_functions():
    """src.pages must not have any page function at module level after gutting __init__.py."""
    import src.pages
    for name in _PAGE_FUNCTION_NAMES:
        assert not hasattr(src.pages, name), (
            f"src.pages.{name} found at module level — __init__.py still imports it eagerly"
        )


def test_pages_init_all_is_empty():
    """__all__ in src.pages should be empty."""
    import src.pages
    assert src.pages.__all__ == []
