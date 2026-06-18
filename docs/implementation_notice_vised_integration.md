# Implementation Notice: vise-d Integration Sprint (Agent 2)

**Date:** 2026-05-11  
**Based on:** `docs/agent_prompt_vised_integration.md`  
**Status:** Complete

---

## What was implemented

| Section | Item | Status |
|---------|------|--------|
| A | `src/utils/vpplib_interface.py` | Done — real imports, no mock |
| B | Copy 4 CSV files to `data/flexibility_profiles/` | Done |
| B | `src/flexibility/` package (6 modules + `__init__.py`) | Done |
| C | `src/pages/flexibility_configurator.py` | Done |
| D | `src/pages/network_scenario.py` | Done |
| E | DWD consolidation in `weather_integration.py` | Done immediately |

---

## Deviations from the original prompt

### Section A — No mock was needed

> *Prompt said:* Create a mock implementation; replace later when Agent 1 is done.

Agent 1 had already finished when this sprint started. vpplib `0.0.6` was already
installed in the `vise/` virtual environment with `vpplib.operator` present.
`vpplib_interface.py` therefore uses real imports from the start:

```python
from vpplib.operator import assign_assets_to_buses, build_timeseries_net
```

No `pip install` step was required.

---

### Section B — CSV column names differ from spec

> *Prompt said:* Column format is `{ClassName}__power_kw`.

The actual CSVs produced by `household_flexibility_simulation` have **five** columns per
typology class:

```
{class}__mean_power_kw
{class}__std_power_kw
{class}__min_power_kw
{class}__max_power_kw
{class}__n_households
```

`flexibility_configurator.py` uses `{class}__mean_power_kw` as the representative power
series. This is consistent with how the `export.py` and `LoadProfileGenerator` work.

Similarly, `flexibility_summary.csv` columns are:

```
typology_class, device, mean_shiftable_kwh, std_shiftable_kwh,
mean_flexibility_score, mean_shift_window_h, n_members
```

The prompt listed `appliance, owned, flexibility_score, shiftable_kwh, shift_window_h`.
The page reads the actual column names (`mean_shiftable_kwh`, grouped by `typology_class`).

---

### Section D — `prepare_solar_data` / `prepare_wind_data` location

> *Prompt said:* Import from `src/mastr/simulation.py`.

Both functions are defined in `src/mastr/preprocessing.py`.
`network_scenario.py` imports them from there directly:

```python
from src.mastr.preprocessing import prepare_solar_data, prepare_wind_data
```

`simulation.py` imports them as well for its own use; neither re-exports them.

---

### Section D — Wind uses one aggregate sgen, not per-asset

> *Prompt said:* Create pandapower sgen elements for each asset at its assigned bus.

This is done for **PV** (one sgen per MaStR asset, using `aggregate_pv_time_series`
which returns `{EinheitMastrNummer: timeseries}`).

For **wind**, `aggregate_wind_time_series` returns a **single summed DataFrame** across
all turbines. Creating per-turbine sgens would require accessing individual `.timeseries`
attributes before aggregation. For practical clarity, one aggregate wind sgen is created
at the dominant bus (the bus assigned to the most wind assets):

```python
dominant_bus = Counter(wind_bus_assignments.values()).most_common(1)[0][0]
```

This is functionally equivalent at the network level — the total injected power is
identical.

---

### Section E — DWD consolidation done immediately, not deferred

> *Prompt said:* Mark with `# TODO: DWD consolidation — pending Agent 1` until Agent 1 is done.

Since Agent 1 was already complete, the consolidation was applied immediately.
Key changes in `src/data_layer/weather_integration.py`:

1. `from dwd_fetcher import DWDFetcher` → `from vpplib.dwd_client import DWDClient`

2. `get_dwd_fetcher()` — removed `ranking_strategy` parameter (not in `DWDClient.__init__`):
   ```python
   return DWDClient(
       cache_dir=str(cache_dir),
       cache_expiry_hours=DWD.CACHE_EXPIRY_HOURS,
       timezone=DWD.TIMEZONE,
   )
   ```

3. **`fetch_weather_for_wind`** — `DWDClient` has no `for_windpowerlib` parameter.
   The call now fetches raw flat columns (`wind_speed`, `temperature`, `pressure`) and
   the windpowerlib MultiIndex format is built manually:
   ```python
   wind_data[('wind_speed', '10')]    = data['wind_speed']           # m/s
   wind_data[('temperature', '2')]    = data['temperature'] + 273.15  # °C → K
   wind_data[('pressure', '0')]       = data['pressure'] * 100.0      # hPa → Pa
   wind_data[('roughness_length', '0')] = 0.15                        # m, open terrain
   ```

4. **`find_nearest_stations`** — `DWDClient` has no `find_stations()` method.
   Updated to use `fetcher.station_manager.find_nearest_stations(parameter=...)` (singular,
   called once per parameter, returns `List[Station]` objects):
   ```python
   for param in parameters:
       station_objs = fetcher.station_manager.find_nearest_stations(
           latitude, longitude, parameter=param, n=n_stations, ...
       )
   ```

5. **`fetch_weather_for_pv`** and **`fetch_weather_for_heatpump`** — already used
   `for_pvlib=True` and `allow_multi_station=True`; these parameters exist in
   `DWDClient.get_observations` unchanged.

---

### `build_timeseries_net` — integer index required

> *vpplib docstring says:* `Index: DatetimeIndex (one row per timestep)`.

The **implementation** uses `range(len(df))` as time steps and calls
`DFData.get_time_step_value(time_step=int)`, which does `df.loc[int, col]`.
Passing a `DatetimeIndex`-ed DataFrame causes a `KeyError`.

**Fix in `network_scenario.py`:** reset both DataFrames to integer index before
calling `build_timeseries_net`, then re-attach the DatetimeIndex to results:

```python
results = build_timeseries_net(net, sgen_df.reset_index(drop=True), load_df.reset_index(drop=True))
for key, df in results.items():
    if len(df) == len(sim_index):
        df.index = sim_index
```

This is a vpplib bug/documentation mismatch — file an issue if this causes problems.

---

## File inventory

### New files created

| Path | Description |
|------|-------------|
| `src/utils/vpplib_interface.py` | Provides `build_timeseries_net` (die frühere geografische Zuweisung `assign_assets_to_buses` wurde entfernt — die MaStR-Zuweisung erfolgt rein manuell) |
| `src/flexibility/__init__.py` | Empty package marker |
| `src/flexibility/appliance_defaults.py` | Copied from `household_flexibility_simulation/config/`, imports fixed |
| `src/flexibility/appliance_model.py` | Copied from `model/`, imports fixed |
| `src/flexibility/household_profile.py` | Copied from `model/`, imports fixed |
| `src/flexibility/flexibility_model.py` | Copied from `model/`, imports fixed |
| `src/flexibility/seasonal_modifier.py` | Copied from `simulation/`, imports fixed |
| `src/flexibility/load_profile_generator.py` | Copied from `simulation/`, imports fixed |
| `src/pages/flexibility_configurator.py` | New Streamlit page — Section C |
| `src/pages/network_scenario.py` | New Streamlit page — Section D |
| `data/flexibility_profiles/load_profiles_winter.csv` | Pre-computed (excluded by `.gitignore`) |
| `data/flexibility_profiles/load_profiles_transition.csv` | Pre-computed (excluded by `.gitignore`) |
| `data/flexibility_profiles/load_profiles_summer.csv` | Pre-computed (excluded by `.gitignore`) |
| `data/flexibility_profiles/flexibility_summary.csv` | Pre-computed (excluded by `.gitignore`) |

### Modified files

| Path | Change |
|------|--------|
| `src/data_layer/weather_integration.py` | DWD consolidation: `DWDFetcher` → `DWDClient`, manual wind MultiIndex, updated `find_nearest_stations` |

### Untouched (as required)

- `src/mastr/simulation.py`
- `src/mastr/preprocessing.py`
- All existing `src/pages/` files
- `src/network/examples.py`

---

## Import fix map for `src/flexibility/`

| Original import | Fixed import |
|----------------|--------------|
| `from config.appliance_defaults import ...` | `from src.flexibility.appliance_defaults import ...` |
| `from model.household_profile import ...` | `from src.flexibility.household_profile import ...` |
| `from model.flexibility_model import ...` | `from src.flexibility.flexibility_model import ...` |
| `from model.appliance_model import ...` | `from src.flexibility.appliance_model import ...` |
| `from simulation.load_profile_generator import ...` | `from src.flexibility.load_profile_generator import ...` |
| `from simulation.seasonal_modifier import ...` | `from src.flexibility.seasonal_modifier import ...` |

---

## Verification commands

```powershell
# Working directory: C:\Users\sbirk\Documents\Code\vise-d

# 1. Import checks
.\vise\Scripts\python -c "from src.utils.vpplib_interface import build_timeseries_net; print('OK')"
.\vise\Scripts\python -c "from src.flexibility.load_profile_generator import LoadProfileGenerator; print('OK')"
.\vise\Scripts\python -c "from src.data_layer.weather_integration import fetch_weather_for_pv; print('OK')"

# 2. End-to-end timeseries power flow test
.\vise\Scripts\python -c "
import pandas as pd
import pandapower.networks as pn
from src.utils.vpplib_interface import build_timeseries_net
net = pn.panda_four_load_branch()
idx = range(96)
load_df = pd.DataFrame({i: 0.001 for i in net.load.index}, index=idx)
sgen_df = pd.DataFrame(index=idx)
r = build_timeseries_net(net, sgen_df, load_df)
print('res_line:', r['res_line'].shape, 'res_bus:', r['res_bus'].shape)
"

# 3. Run Streamlit app
streamlit run app.py
# → navigate to 'Flexibilitätskonfigurator', configure mix, click 'Lastprofil berechnen'
# → click '→ Im Netzmodell analysieren'
# → load MaStR assets, run scenario, verify heatmap renders
```
