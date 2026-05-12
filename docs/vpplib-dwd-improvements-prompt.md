# Coding Agent Prompt: Improve vpplib DWD Weather Fetcher

## Background

This project uses two DWD (Deutscher Wetterdienst) weather data fetchers in parallel:

1. **`vpplib` built-in** — located at `vpplib/environment.py` and `vpplib/dwd_client.py`. The `Environment` class exposes `get_dwd_pv_data()`, `get_dwd_wind_data()`, and `get_dwd_temp_data()`. These are used by downstream simulation components (`Photovoltaic`, `WindPower`, etc.).

2. **Local `dwd_fetcher_lib`** — located at `dwd_fetcher_lib/dwd_fetcher/` in the consuming project. This library was developed to address gaps in the vpplib fetcher, and the goal is to upstream those improvements into vpplib so the local library can eventually be retired.

Your task is to **produce an implementation plan** for adding the four capabilities described below to the vpplib DWD fetcher. Do not implement yet — produce a plan with concrete file paths, changed functions, new interfaces, and a test strategy.

---

## Repository locations

- **vpplib source:** `C:\Users\sbirk\Documents\Code\vpplib\vpplib\`
  - `environment.py` — `Environment` class, `get_dwd_pv_data / wind / temp` methods
  - `dwd_client.py` — `DWDClient` class, `CacheManager`, station search, data download
- **Reference implementation:** `C:\Users\sbirk\Documents\Code\vise-d\dwd_fetcher_lib\dwd_fetcher\`
  - `fetcher.py` — main `DWDFetcher` class (the authoritative reference for all four issues)
  - `stations.py` — station search and quality scoring
  - `transformers.py` — pvlib / windpowerlib output formatters
  - `config.py` — weighting/ranking strategy enums

---

## Issue 1 — Multi-station merging with configurable weighting

**Current behaviour in vpplib:**
`get_dwd_pv_data()` (and the wind/temp equivalents) select exactly one DWD station — the nearest one that meets a minimum data-quality threshold (`min_quality_per_parameter`, default 80 %). If that station has gaps, there is no fallback.

**Desired behaviour:**
Allow combining data from *N* nearby stations to fill gaps and improve spatial representativeness. The merged result should be a single DataFrame with the same schema as today.

**Reference implementation to study:**
`DWDFetcher.get_observations()` in `fetcher.py`, specifically the `allow_multi_station` and `n_stations` parameters and the `_merge_multi_station_data()` private method. Also see `WeightingStrategy` in `config.py` for the four strategies: `NEAREST_ONLY`, `INVERSE_DISTANCE`, `DATA_COMPLETENESS`, `QUALITY_WEIGHTED`.

**Constraints / acceptance criteria:**
- Default behaviour must be unchanged (`n_stations=1`, `allow_multi_station=False`).
- When enabled, the merged DataFrame must have the same index and column structure as today's single-station output so downstream `Photovoltaic` / `WindPower` components are unaffected.
- The chosen strategy and the contributing station list should be surfaced in the returned metadata.

---

## Issue 2 — Quality-based station ranking

**Current behaviour in vpplib:**
`DWDClient.__find_nearest_station()` sorts candidate stations by geographic distance only. A station 5 km away with 60 % data coverage ranks above one 8 km away with 99 % coverage.

**Desired behaviour:**
Add a `ranking_strategy` parameter (alongside the existing `distance` sorting) so users can choose between:
- `DISTANCE_ONLY` — current behaviour, kept as default
- `QUALITY_WEIGHTED` — combined score of distance and data completeness
- `QUALITY_FIRST` — filter for minimum quality first, then sort by distance

**Reference implementation to study:**
`StationSelector` in `stations.py` and the `_score_stations()` method in `fetcher.py`. The scoring formula is: `combined_score = (1 - distance_weight) * quality_score + distance_weight * distance_score`.

**Constraints / acceptance criteria:**
- `DISTANCE_ONLY` must be the default to preserve existing behaviour.
- The scoring and ranking logic should live in `dwd_client.py` close to the existing `__find_nearest_station()` method, not in `environment.py`.
- The three public methods (`get_dwd_pv_data`, `get_dwd_wind_data`, `get_dwd_temp_data`) should each accept a `ranking_strategy` kwarg that is forwarded to the client.

---

## Issue 3 — Configurable temporal resolution

**Current behaviour in vpplib:**
Observation data is always fetched at 10-minute resolution. The `Environment` constructor accepts a `time_freq` parameter (e.g. `"15min"`, `"60min"`) which controls internal resampling, but all raw DWD downloads are hardcoded to the `10_minutes` dataset.

**Desired behaviour:**
Allow the caller to request data at `10_minutes`, `hourly`, or `daily` resolution. When a coarser resolution is requested, fetch the native DWD dataset at that resolution directly (e.g. `climate_observations/germany/hourly/`) rather than downloading 10-minute data and resampling.

**Reference implementation to study:**
`DWDFetcher.get_observations()` — the `resolution` parameter and how it maps to DWD Open Data URL paths in `downloader.py`. The URL pattern is: `https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/{resolution}/`.

**Constraints / acceptance criteria:**
- `10_minutes` remains the default to preserve existing behaviour.
- The resolution selection must happen at download time in `dwd_client.py`, not as a post-hoc resample.
- Hourly and daily datasets have different column names than 10-minute datasets; the plan must address how to normalise column names so `__process_observation_parameter()` and downstream callers are unaffected.

---

## Issue 4 — Parameter completeness reporting

**Current behaviour in vpplib:**
After fetching, the caller has no programmatic way to know which parameters were fully covered, which had gaps, and how gaps were handled (filled, interpolated, or left as NaN). The only signal is `station_metadata` which contains a scalar `quality` percentage per station.

**Desired behaviour:**
Return a structured completeness report alongside the weather DataFrame. At minimum it should contain:
- Per-parameter coverage percentage (0–100)
- Number and location (time ranges) of gap intervals > 1 h
- Whether a fallback (multi-station merge or interpolation) was applied

**Reference implementation to study:**
`DWDFetcher._check_parameter_completeness()` in `fetcher.py` and the `parameter_availability` key in the metadata dict returned by `get_observations()`.

**Constraints / acceptance criteria:**
- The report must be returned as an additional value or included in the existing `station_metadata` dict so callers who ignore it are unaffected (no signature break).
- The report should be available for all three public methods (`get_dwd_pv_data`, `get_dwd_wind_data`, `get_dwd_temp_data`).

---

## What the plan should include

For each issue, provide:

1. **Affected files and functions** — list every file and method that needs to change, with current line numbers.
2. **New interfaces** — show the new/changed function signatures with their parameters, types, and defaults.
3. **Implementation sketch** — pseudocode or a concise description of the algorithm change (not full code).
4. **Migration notes** — any backwards-compatibility concerns and how to handle them.
5. **Test strategy** — what unit/integration tests should be added or updated, and what edge cases to cover.

The plan should be ordered so that each issue can be implemented independently and merged without depending on the others.
