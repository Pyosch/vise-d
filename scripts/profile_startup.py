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


def time_page_import(module_name: str) -> tuple[float, str]:
    """Import a module in-process and return (elapsed_ms, note).

    Modules share sys.modules — the first module to import a heavy library
    pays the full cost; subsequent modules see cached imports and appear fast.
    This reflects real startup behavior.

    Returns (-1, "[error: <msg>]") on ImportError.
    """
    t0 = time.perf_counter()
    try:
        importlib.import_module(module_name)
    except Exception as e:
        return -1, f"[error: {type(e).__name__}]"
    return (time.perf_counter() - t0) * 1000, ""


def run_section2() -> list[tuple[str, float, str]]:
    """Import each page module in-process and time it.

    Returns list of (short_name, ms, note) sorted slowest-first.
    Cumulative sys.modules caching means the first module that pulls in
    pandapower/osmnx/etc. will appear slow; later ones will be fast.
    """
    results = []
    for module in PAGE_MODULES:
        short = module.split(".")[-1]  # e.g. "netzmodell"
        print(f"  importing {short}...", end="\r", flush=True)
        ms, note = time_page_import(module)
        results.append((short, ms, note))

    print(" " * 60, end="\r")
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def run_section3(db_path=None) -> list[tuple[str, float, str]]:
    """Time the three MaStR location-cache loading calls.

    Returns list of (label, ms, note).
    Note indicates "CSV cache hit" or "DB query cold".

    Accepts an optional db_path for testing with a non-default path.
    """
    try:
        from src.config.paths import MASTR_DB_PATH
        from src.mastr.preprocessing import (
            get_unique_solar_locations,
            get_unique_wind_locations,
            get_unique_storage_locations,
            _LOCATION_CACHE_DIR,
        )
    except Exception as e:
        return [("MaStR import", -1, f"[import error: {e}]")]

    resolved_db = Path(db_path) if db_path is not None else Path(MASTR_DB_PATH)

    if not resolved_db.exists():
        return [("MaStR DB", -1, f"[DB not found — skipping: {resolved_db}]")]

    entries = [
        ("solar locations",   _LOCATION_CACHE_DIR / "solar_locations.csv",   get_unique_solar_locations),
        ("wind locations",    _LOCATION_CACHE_DIR / "wind_locations.csv",     get_unique_wind_locations),
        ("storage locations", _LOCATION_CACHE_DIR / "storage_locations.csv",  get_unique_storage_locations),
    ]

    results = []
    for label, csv_path, fn in entries:
        cache_status = "CSV cache hit" if Path(csv_path).exists() else "DB query cold"
        t0 = time.perf_counter()
        try:
            fn(str(resolved_db))
            ms = (time.perf_counter() - t0) * 1000
            results.append((label, ms, cache_status))
        except Exception as e:
            results.append((label, -1, f"[error: {e}]"))

    return results


def print_section(
    title: str,
    note: str,
    results: list[tuple[str, float, str]],
) -> None:
    """Print one profiler section with a sorted bar chart."""
    print(f"\n--- {title} ---")
    if note:
        print(f"Note: {note}\n")
    valid_ms = [ms for _, ms, _ in results if ms >= 0]
    max_ms = max(valid_ms) if valid_ms else 1
    for label, ms, row_note in results:
        print(format_row(label, ms, row_note, max_ms))


def main() -> None:
    # Ensure stdout can handle Unicode block characters on Windows
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=== VISE-D Dashboard Startup Profiler ===")
    print(f"Python {sys.version.split()[0]} | Platform: {platform.system()} {platform.release()}")
    print(f"Virtualenv: {sys.executable}")

    print("\nSection 1: timing library imports (fresh subprocess per library)…")
    sec1 = run_section1()
    print_section(
        "Section 1: Library import times (net of Python startup)",
        "each library is imported in an isolated subprocess — times are independent",
        sec1,
    )

    print("\nSection 2: timing page imports (in-process, cumulative)…")
    sec2 = run_section2()
    print_section(
        "Section 2: Page import times",
        "first page to import a library pays full cost; later pages see cached imports",
        sec2,
    )

    print("\nSection 3: timing MaStR data loading…")
    sec3 = run_section3()
    valid_sec3 = [ms for _, ms, _ in sec3 if ms >= 0]
    max_ms_sec3 = max(valid_sec3) if valid_sec3 else 1
    print("\n--- Section 3: MaStR data loading ---\n")
    for label, ms, note in sec3:
        print(format_row(label, ms, note, max_ms_sec3))

    print("\n--- Tuna flamegraph ---")
    print("For a full import-tree visualization, run:")
    print('  pip install tuna')
    print(f'  {sys.executable} -X importtime -c "import streamlit; from src import pages" 2>import_time.txt')
    print('  tuna import_time.txt')
    print()


if __name__ == "__main__":
    main()
