"""VISE-D Dashboard Startup Profiler.

Measures cold-start time across three dimensions:
  1. Third-party library import times (isolated per-subprocess)
  2. Page module import times (in-process, cumulative sys.modules)
  3. MaStR data loading times (CSV cache hit vs. DB query)

Usage:
    python scripts/profile_startup.py
"""

import sys
import time
import subprocess
import importlib
import platform
from pathlib import Path

# Add project root to sys.path so src.* imports work
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


# ── Constants ──────────────────────────────────────────────────────────────

LIBRARY_IMPORTS = [
    "pandas",
    "numpy",
    "plotly",
    "geopandas",
    "pandapower",
    "pandapower.networks",
    "osmnx",
    "open_mastr",
    "vpplib.environment",
]

PAGE_MODULES = [
    "src.pages.research_results",
    "src.pages.bev_settings",
    "src.pages.pv_configuration",
    "src.pages.wind_configuration",
    "src.pages.heatpump_configuration",
    "src.pages.electrical_storage_configuration",
    "src.pages.thermal_storage_settings",
    "src.pages.solar_installation_mastr",
    "src.pages.wind_installation_mastr",
    "src.pages.storage_installation_mastr",
    "src.pages.energy_generation_solar",
    "src.pages.wind_energy_generation",
    "src.pages.flexibility_configurator",
    "src.pages.netzmodell",
    "src.pages.mv_fallstudie",
]


# ── Pure helpers ───────────────────────────────────────────────────────────

def make_bar(ms: float, max_ms: float, width: int = 20) -> str:
    """Return a Unicode block bar scaled to max_ms."""
    if max_ms == 0 or ms <= 0:
        return ""
    filled = int((ms / max_ms) * width)
    return "█" * filled


def format_row(label: str, ms: float, note: str, max_ms: float) -> str:
    """Format one result row: label, ms, bar, optional note."""
    label_col = f"  {label:<35}"
    if ms < 0:
        return f"{label_col} {note}"
    ms_rounded = int(ms + 0.5)
    ms_col = f"{ms_rounded:>7} ms"
    bar = make_bar(ms, max_ms)
    note_part = f"  {note}" if note else ""
    return f"{label_col} {ms_col}  {bar}{note_part}"


def time_subprocess_import(lib_name: str, timeout: int = 120) -> tuple[float, str]:
    """Import a library in a fresh subprocess and return (elapsed_ms, note).

    Returns (-1, "[not installed]") if the import fails.
    Returns (-1, "[timeout]") if the subprocess exceeds timeout seconds.
    Uses sys.executable so the profiler runs in the same virtualenv.
    """
    cmd = [sys.executable, "-c", f"import {lib_name}"]
    t0 = time.perf_counter()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            cwd=str(_PROJECT_ROOT),
        )
    except subprocess.TimeoutExpired:
        return -1, "[timeout]"
    elapsed_ms = (time.perf_counter() - t0) * 1000
    if result.returncode != 0:
        return -1, "[not installed]"
    return elapsed_ms, ""


def run_section1() -> list[tuple[str, float, str]]:
    """Time each library import in an isolated subprocess.

    Returns list of (label, ms, note) sorted slowest-first.
    Skips Python startup overhead by measuring `python -c pass` first
    and subtracting it from each result.
    """
    # Measure Python startup overhead
    startup_ms, _ = time_subprocess_import("sys")  # sys is always available
    # "import sys" is effectively just Python startup — sys is a builtin
    # We use this as our baseline to subtract from each measurement.

    results = []
    for lib in LIBRARY_IMPORTS:
        print(f"  timing {lib}...", end="\r", flush=True)
        ms, note = time_subprocess_import(lib)
        net_ms = (ms - startup_ms) if ms >= 0 else ms
        results.append((lib, net_ms, note))

    print(" " * 60, end="\r")  # clear progress line
    results.sort(key=lambda x: x[1], reverse=True)
    return results
