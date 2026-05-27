# Dashboard Startup Profiler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `scripts/profile_startup.py` — a standalone diagnostic script that measures and ranks dashboard cold-start time across three dimensions: third-party library imports, page module imports, and MaStR data loading.

**Architecture:** Section 1 spawns a fresh subprocess per library so each import time is isolated (unaffected by prior imports). Section 2 imports pages in-process with `importlib` so cumulative `sys.modules` caching is captured accurately — matching real startup behavior. Section 3 calls the MaStR location functions directly and reports whether the CSV cache was warm or cold.

**Tech Stack:** Python stdlib only (`subprocess`, `importlib`, `time`, `sys`, `pathlib`). Virtualenv at `C:\Users\sbirk\Documents\Code\vise-d\vise` — use `vise\Scripts\python.exe` or activate the environment before running commands.

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `scripts/profile_startup.py` | Create | The profiler script — all three sections + output formatting |
| `tests/test_profile_startup.py` | Create | Tests for the pure helper functions |

No changes to any application file.

---

## Task 1: Script skeleton, helpers, and their tests

**Files:**
- Create: `tests/test_profile_startup.py`
- Create: `scripts/profile_startup.py`

- [ ] **Step 1: Write failing tests for `make_bar` and `format_row`**

Create `tests/test_profile_startup.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.profile_startup import make_bar, format_row


def test_make_bar_full():
    assert make_bar(100, 100, width=10) == "██████████"


def test_make_bar_half():
    assert make_bar(50, 100, width=10) == "█████"


def test_make_bar_zero_ms():
    assert make_bar(0, 100, width=10) == ""


def test_make_bar_zero_max():
    assert make_bar(50, 0, width=10) == ""


def test_format_row_basic():
    row = format_row("pandas", 1234.5, "", max_ms=5000)
    assert "pandas" in row
    assert "1235" in row  # rounded ms


def test_format_row_with_note():
    row = format_row("vpplib", -1, "[not installed]", max_ms=5000)
    assert "[not installed]" in row
    assert "vpplib" in row
```

- [ ] **Step 2: Run tests — verify they fail with ImportError**

```
vise\Scripts\python.exe -m pytest tests/test_profile_startup.py -v
```

Expected: `ModuleNotFoundError: No module named 'scripts.profile_startup'`

- [ ] **Step 3: Create `scripts/profile_startup.py` with sys.path setup and helpers**

```python
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
    ms_col = f"{ms:>7.0f} ms"
    bar = make_bar(ms, max_ms)
    note_part = f"  {note}" if note else ""
    return f"{label_col} {ms_col}  {bar}{note_part}"
```

- [ ] **Step 4: Run tests — verify they pass**

```
vise\Scripts\python.exe -m pytest tests/test_profile_startup.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```
git add scripts/profile_startup.py tests/test_profile_startup.py
git commit -m "feat: add startup profiler skeleton with make_bar and format_row helpers"
```

---

## Task 2: Section 1 — library import times via subprocess

**Files:**
- Modify: `scripts/profile_startup.py`
- Modify: `tests/test_profile_startup.py`

- [ ] **Step 1: Write failing test for `time_subprocess_import`**

Add to `tests/test_profile_startup.py`:

```python
from scripts.profile_startup import time_subprocess_import


def test_time_subprocess_import_known_library():
    ms, note = time_subprocess_import("sys")
    assert ms > 0
    assert note == ""


def test_time_subprocess_import_missing_library():
    ms, note = time_subprocess_import("_nonexistent_library_xyz")
    assert ms < 0
    assert "[not installed]" in note
```

- [ ] **Step 2: Run tests — verify they fail**

```
vise\Scripts\python.exe -m pytest tests/test_profile_startup.py::test_time_subprocess_import_known_library tests/test_profile_startup.py::test_time_subprocess_import_missing_library -v
```

Expected: `ImportError` — function not defined yet.

- [ ] **Step 3: Implement `time_subprocess_import` and `run_section1`**

Add to `scripts/profile_startup.py` after the helpers:

```python
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
```

- [ ] **Step 4: Run tests — verify they pass**

```
vise\Scripts\python.exe -m pytest tests/test_profile_startup.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```
git add scripts/profile_startup.py tests/test_profile_startup.py
git commit -m "feat: add Section 1 library import timing via subprocess"
```

---

## Task 3: Section 2 — page module import times (in-process)

**Files:**
- Modify: `scripts/profile_startup.py`
- Modify: `tests/test_profile_startup.py`

- [ ] **Step 1: Write failing test for `time_page_import`**

Add to `tests/test_profile_startup.py`:

```python
from scripts.profile_startup import time_page_import


def test_time_page_import_known_module():
    ms, note = time_page_import("pathlib")
    assert ms >= 0
    assert note == ""


def test_time_page_import_missing_module():
    ms, note = time_page_import("_nonexistent_module_xyz")
    assert ms < 0
    assert "[error]" in note
```

- [ ] **Step 2: Run tests — verify they fail**

```
vise\Scripts\python.exe -m pytest tests/test_profile_startup.py::test_time_page_import_known_module tests/test_profile_startup.py::test_time_page_import_missing_module -v
```

Expected: `ImportError` — function not defined yet.

- [ ] **Step 3: Implement `time_page_import` and `run_section2`**

Add to `scripts/profile_startup.py`:

```python
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
```

- [ ] **Step 4: Run tests — verify they pass**

```
vise\Scripts\python.exe -m pytest tests/test_profile_startup.py -v
```

Expected: all 10 tests PASS.

- [ ] **Step 5: Commit**

```
git add scripts/profile_startup.py tests/test_profile_startup.py
git commit -m "feat: add Section 2 page module import timing in-process"
```

---

## Task 4: Section 3 — MaStR data loading times

**Files:**
- Modify: `scripts/profile_startup.py`
- Modify: `tests/test_profile_startup.py`

- [ ] **Step 1: Write failing test for `run_section3`**

Add to `tests/test_profile_startup.py`:

```python
from scripts.profile_startup import run_section3


def test_run_section3_missing_db(tmp_path):
    """run_section3 must return a result list even when the DB is absent."""
    results = run_section3(db_path=tmp_path / "nonexistent.db")
    # Should return one entry with a [DB not found] note
    assert len(results) == 1
    label, ms, note = results[0]
    assert "[DB not found" in note
    assert ms < 0
```

- [ ] **Step 2: Run test — verify it fails**

```
vise\Scripts\python.exe -m pytest tests/test_profile_startup.py::test_run_section3_missing_db -v
```

Expected: `ImportError` — function not defined yet.

- [ ] **Step 3: Implement `run_section3`**

Add to `scripts/profile_startup.py`:

```python
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
```

- [ ] **Step 4: Run tests — verify they pass**

```
vise\Scripts\python.exe -m pytest tests/test_profile_startup.py -v
```

Expected: all 11 tests PASS.

- [ ] **Step 5: Commit**

```
git add scripts/profile_startup.py tests/test_profile_startup.py
git commit -m "feat: add Section 3 MaStR data loading timing"
```

---

## Task 5: Wire everything into `main()` and verify end-to-end

**Files:**
- Modify: `scripts/profile_startup.py`

- [ ] **Step 1: Implement `print_section` and `main`**

Add to `scripts/profile_startup.py`:

```python
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
```

- [ ] **Step 2: Run the full test suite — verify all tests pass**

```
vise\Scripts\python.exe -m pytest tests/test_profile_startup.py -v
```

Expected: all 11 tests PASS, no errors.

- [ ] **Step 3: Run the script end-to-end and verify output**

```
vise\Scripts\python.exe scripts/profile_startup.py
```

Expected:
- Header line prints with Python version and platform
- Section 1 shows ~9 library rows sorted slowest-first with bar charts; `[not installed]` for any missing libraries
- Section 2 shows 15 page rows sorted slowest-first
- Section 3 shows 3 MaStR rows with cache status labels, OR `[DB not found — skipping]` if the DB is absent
- Tuna command prints at the end
- Script exits cleanly (exit code 0)

If Section 3 shows `[DB not found]`, that is correct behavior — no action needed.

- [ ] **Step 4: Commit**

```
git add scripts/profile_startup.py
git commit -m "feat: wire main() and print_section, profiler script complete"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task that covers it |
|-----------------|-------------------|
| Section 1: 9 libraries timed via subprocess | Task 2 (`run_section1`, `time_subprocess_import`) |
| Section 2: 15 pages timed in-process | Task 3 (`run_section2`, `time_page_import`) |
| Section 2: sys.modules caching documented in output | Task 5 (`print_section` note string) |
| Section 3: solar/wind/storage location loading | Task 4 (`run_section3`) |
| Section 3: CSV cache hit vs DB query cold label | Task 4 (`cache_status` logic) |
| Missing library → `[not installed]` | Task 2 (`time_subprocess_import` returncode check) |
| Missing DB → `[DB not found — skipping]` | Task 4 (`resolved_db.exists()` check) |
| Output sorted slowest-first with bar charts | Task 1 (`make_bar`, `format_row`) + Task 5 (`print_section`) |
| Tuna command printed at end | Task 5 (`main`) |
| No changes to application files | All tasks — only `scripts/` and `tests/` touched |

All spec requirements are covered. No gaps found.

**Placeholder scan:** No TBD, TODO, or "similar to Task N" references. All code blocks are complete.

**Type consistency:** `time_subprocess_import` → `tuple[float, str]`, `time_page_import` → `tuple[float, str]`, `run_section1/2/3` → `list[tuple[str, float, str]]`. `print_section` consumes `list[tuple[str, float, str]]`. Consistent throughout.
