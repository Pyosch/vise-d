# Dashboard Startup Profiler — Design Spec

**Date:** 2026-05-27  
**Status:** Approved  
**Scope:** Diagnostic only — no fixes, no Streamlit runtime changes

---

## Problem

The VISE-D dashboard has a slow initial startup. The root cause is unknown. The goal is to measure and rank which components consume the most time during the cold-start phase so that follow-up optimization work is targeted rather than speculative.

---

## Deliverable

A single standalone script: `scripts/profile_startup.py`

Run with: `python scripts/profile_startup.py`

No Streamlit server needed. No changes to existing application code.

---

## What the script measures

### Section 1 — Third-party library import times

Imports each heavy library individually in a fresh subprocess context and records wall-clock time:

- `pandas`
- `numpy`
- `plotly`
- `geopandas`
- `pandapower`
- `pandapower.networks`
- `osmnx`
- `open_mastr`
- `vpplib.environment` (guarded with try/except — may not be installed)

Each import is timed with `time.perf_counter()`. Output is sorted slowest-first.

### Section 2 — Page module import times

Imports each page module from `src.pages` individually and records wall-clock time:

Pages to time (matching current `src/pages/__init__.py`):
- `src.pages.research_results`
- `src.pages.bev_settings`
- `src.pages.pv_configuration`
- `src.pages.wind_configuration`
- `src.pages.heatpump_configuration`
- `src.pages.electrical_storage_configuration`
- `src.pages.thermal_storage_settings`
- `src.pages.solar_installation_mastr`
- `src.pages.wind_installation_mastr`
- `src.pages.storage_installation_mastr`
- `src.pages.energy_generation_solar`
- `src.pages.wind_energy_generation`
- `src.pages.flexibility_configurator`
- `src.pages.netzmodell`
- `src.pages.mv_fallstudie`

**Implementation note:** Because Python caches imported modules in `sys.modules`, importing page A will share module cache with page B. This means the first page that triggers a heavy import (e.g. pandapower) will appear slow, and subsequent pages that also use it will appear fast. This is intentional and reflects the real import order cost. The script documents this behavior in its output header.

### Section 3 — MaStR data loading times

Times the three location-cache loading calls from `src.mastr.preprocessing`:

- `get_unique_solar_locations(mastr_db_path)`
- `get_unique_wind_locations(mastr_db_path)`
- `get_unique_storage_locations(mastr_db_path)`

For each call, the script:
1. Checks whether the CSV cache file exists and reports "CSV cache hit" or "DB query (cold)"
2. Times the actual call
3. Reports the result

This distinguishes the cold-start case (no CSV cache, must query SQLite) from the warm case.

---

## Output format

```
=== VISE-D Dashboard Startup Profiler ===
Python 3.x.x | Platform: win32

--- Section 1: Library import times ---
Note: imports share sys.modules cache — times are cumulative first-load costs.

  pandapower.networks    3420 ms  ████████████████████
  osmnx                  1890 ms  ██████████
  geopandas               540 ms  ███
  ...

--- Section 2: Page import times ---
Note: first page to import a library pays the full cost; later pages benefit from cache.

  netzmodell             3501 ms  ████████████████████
  mv_fallstudie           180 ms  █
  ...

--- Section 3: MaStR data loading ---

  solar locations    [CSV cache hit]  45 ms
  wind locations     [DB query cold]  3200 ms
  storage locations  [DB query cold]  2900 ms

--- Tuna flamegraph ---
For full import tree visualization, run:
  pip install tuna
  python -X importtime -c "import streamlit; from src import pages" 2>import_time.txt
  tuna import_time.txt
```

---

## Error handling

- If a library is not installed (e.g. `vpplib`), the script skips it and prints `[not installed]` rather than crashing.
- If `MASTR_DB_PATH` does not exist, Section 3 prints `[DB not found — skipping]`.
- The script must complete even if individual imports fail.

---

## Files changed

| File | Change |
|------|--------|
| `scripts/profile_startup.py` | New file — the profiler script |

No changes to `dashboard.py`, `src/pages/__init__.py`, or any other application file.

---

## Out of scope

- Streamlit server startup time (Streamlit internals, not measurable from Python directly)
- Runtime behavior after the page renders (database queries triggered by user interaction)
- Any fixes or optimizations (this spec is diagnosis only)
- CI integration or automated performance regression tracking
