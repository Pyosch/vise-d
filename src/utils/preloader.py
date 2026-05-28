"""Background library preloader for VISE-D dashboard startup optimisation.

Imports heavy libraries into sys.modules on a daemon thread immediately after
dashboard.py starts. Pages that need these libraries will find them already
cached; if the thread is still running when a page is first visited, Python's
import lock ensures the page waits only for the remaining import time.

Libraries are loaded in rough order of navigation likelihood.
"""

import sys
import threading

_PRIORITY_MODULES = [
    'pandapower',
    'pandapower.networks',
    'vpplib',
    'vpplib.environment',
    'open_mastr',
    'geopandas',
    'osmnx',
]


def _preload() -> None:
    for mod in _PRIORITY_MODULES:
        if mod not in sys.modules:
            try:
                __import__(mod)
            except Exception:
                pass


threading.Thread(target=_preload, daemon=True).start()
