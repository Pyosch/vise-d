"""Tests that src.pages does not eagerly load page modules."""

import os
import subprocess
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
    """src.pages must not eagerly load page modules from __init__.py.

    Checked in a fresh interpreter that does nothing but ``import src.pages``:
    importing any page submodule (as other tests legitimately do) attaches it to
    the ``src.pages`` package, so this invariant can only be verified in a clean
    process — otherwise the result depends on test import order.
    """
    names = ", ".join(repr(n) for n in _PAGE_FUNCTION_NAMES)
    code = (
        "import src.pages\n"
        f"leaked = [n for n in ({names},) if hasattr(src.pages, n)]\n"
        "assert not leaked, 'src.pages eagerly exposes: ' + ', '.join(leaked)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=_REPO_ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_pages_init_all_is_empty():
    """__all__ in src.pages should be empty."""
    import src.pages
    assert src.pages.__all__ == []
