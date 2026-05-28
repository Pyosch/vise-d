"""Tests for the background library preloader."""

import sys
import threading
from unittest.mock import patch, MagicMock


def test_preloader_starts_one_daemon_thread():
    """Importing src.utils.preloader must start exactly one daemon thread."""
    captured = []
    original_thread = threading.Thread

    def capturing_thread(*args, **kwargs):
        t = original_thread(*args, **kwargs)
        captured.append(t)
        return t

    sys.modules.pop('src.utils.preloader', None)

    with patch('threading.Thread', side_effect=capturing_thread):
        import src.utils.preloader  # noqa: F401

    assert len(captured) == 1, f"Expected 1 thread, got {len(captured)}"
    assert captured[0].daemon is True, "Preloader thread must be a daemon"


def test_preloader_priority_modules_includes_heavy_libraries():
    """_PRIORITY_MODULES must include all libraries that cause slow page loads."""
    import src.utils.preloader
    expected = [
        'pandapower', 'pandapower.networks',
        'vpplib', 'vpplib.environment',
        'open_mastr', 'geopandas', 'osmnx',
    ]
    for mod in expected:
        assert mod in src.utils.preloader._PRIORITY_MODULES, (
            f"'{mod}' missing from _PRIORITY_MODULES — it won't be pre-warmed"
        )
