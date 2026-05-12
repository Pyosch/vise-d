# Agent Prompt: vise-d Integration Sprint

## Context

You are working on `vise-d`, a Streamlit dashboard for the VISE-D research project.
The dashboard allows Stadtwerke staff to assess grid congestion, explore installed
assets from Germany's Marktstammdatenregister (MaStR), and evaluate whether demand
flexibility can resolve congestion or enable new grid connections.

This sprint has two parallel workstreams. You are **Agent 2 — vise-d**. You work
primarily in `C:\Users\sbirk\Documents\Code\vise-d\`. You may read (but not modify)
`C:\Users\sbirk\Documents\Code\household_flexibility_simulation\` to copy source files.

A separate agent (Agent 1) is refactoring `C:\Users\sbirk\Documents\Code\vpplib\`
in parallel. Until Agent 1 is done, you use the mock interface defined in Section A.
When Agent 1 finishes, replace the mock with real imports (see Section A).

---

## Section A — vpplib Interface (Mock First, Real Later)

Create `C:\Users\sbirk\Documents\Code\vise-d\src\utils\vpplib_interface.py`:

```python
"""
Interface to vpplib network functions.

TODO: When Agent 1 (vpplib refactor) is complete, replace the mock implementations
below with real imports:

    from vpplib.operator import assign_assets_to_buses, build_timeseries_net

The function signatures are identical — it is a drop-in replacement.
"""
import random
import pandas as pd


def assign_assets_to_buses(net, gdf, seed=42):
    """MOCK: assigns all assets randomly to load buses.

    Parameters
    ----------
    net : pandapower network
    gdf : pd.DataFrame with columns 'EinheitMastrNummer', 'Breitengrad', 'Laengengrad'
    seed : int

    Returns
    -------
    dict[str, int]  {EinheitMastrNummer: bus_index}
    """
    random.seed(seed)
    load_buses = net.load.bus.unique().tolist()
    if not load_buses:
        load_buses = net.bus.index.tolist()
    return {
        row["EinheitMastrNummer"]: random.choice(load_buses)
        for _, row in gdf.iterrows()
    }


def build_timeseries_net(net, sgen_timeseries_df, load_timeseries_df, output_keys=None):
    """MOCK: returns plausible-looking placeholder results.

    Parameters
    ----------
    net : pandapower network
    sgen_timeseries_df : pd.DataFrame  (index=DatetimeIndex, columns=sgen indices)
    load_timeseries_df : pd.DataFrame  (index=DatetimeIndex, columns=load indices)
    output_keys : list of (element, variable) tuples — ignored in mock

    Returns
    -------
    dict with keys 'res_line' and 'res_bus'
    """
    idx = sgen_timeseries_df.index
    return {
        "res_line": pd.DataFrame(
            30.0, index=idx, columns=net.line.index
        ),
        "res_bus": pd.DataFrame(
            1.0, index=idx, columns=net.bus.index
        ),
    }
```

---

## Section B — Flexibility Modules: Run Pipeline + Merge Code

### Step 1: Generate CSV outputs

Run the household flexibility pipeline once to produce the data files:

```
cd C:\Users\sbirk\Documents\Code\household_flexibility_simulation
python main.py
```

This produces CSVs in `output/results/`. Copy them to:
```
C:\Users\sbirk\Documents\Code\vise-d\data\flexibility_profiles\
  load_profiles_winter.csv
  load_profiles_transition.csv
  load_profiles_summer.csv
  flexibility_summary.csv
```

### CSV formats (do not change these — Agent 1 may also read them)

**`load_profiles_{season}.csv`**
- Index column: `timestamp` (DatetimeIndex, 672 rows = 1 week at 15 min)
- Data columns: `{ClassName}__power_kw` (double underscore separator)
  Example column name: `High_Tech_Heavy_User__power_kw`

**`flexibility_summary.csv`**
- Columns: `typology_class`, `appliance`, `owned`, `flexibility_score`,
  `shiftable_kwh`, `shift_window_h`

### Step 2: Merge source modules into vise-d

Copy the following files from `household_flexibility_simulation` into
`vise-d/src/flexibility/` (create the folder, add `__init__.py`):

| Source | Destination |
|--------|-------------|
| `model/household_profile.py` | `src/flexibility/household_profile.py` |
| `model/flexibility_model.py` | `src/flexibility/flexibility_model.py` |
| `model/appliance_model.py` | `src/flexibility/appliance_model.py` |
| `config/appliance_defaults.py` | `src/flexibility/appliance_defaults.py` |
| `simulation/load_profile_generator.py` | `src/flexibility/load_profile_generator.py` |
| `simulation/seasonal_modifier.py` | `src/flexibility/seasonal_modifier.py` |

After copying, fix all internal imports so they reference `src.flexibility.*`
instead of their original module paths. Do not modify the logic or docstrings.

---

## Section C — New Page: Flexibility Configurator

Create `C:\Users\sbirk\Documents\Code\vise-d\src\pages\flexibility_configurator.py`.

This page lets users configure the household mix and flexibility participation rate
for a grid area, then produces aggregate load timeseries for use in the network
scenario page.

### UI flow

**1. Data source**
Load the pre-computed CSVs from `data/flexibility_profiles/`. Parse typology class
names by splitting column names on `__` and taking the first part, replacing `_`
with spaces.

**2. Season selection**
Radio buttons: Winter / Übergang / Sommer (maps to winter/transition/summer CSV)

**3. Household mix**
For each typology class: a number input for household count (default 10, min 0).
Show a short description derived from the class name. Group less common classes
under an expander ("Weitere Klassen").

**4. Flexibility participation rate**
A single slider: 0–100%, default 20%.
Label: "Anteil flexibler Haushalte"

**5. Aggregate load profile**
Compute:
```python
# For each class: scale profile by household count
# Sum all classes → baseline_load (p_mw Series, DatetimeIndex)
# Apply participation rate to shiftable appliances → flex_scenario_load
```

Show a Plotly line chart comparing baseline vs. flexibility scenario load profile
(1 week, 15-min resolution). Show peak load, average load, and estimated
shiftable energy (kWh) as metrics.

**6. Pass to network scenario page**
Write to session state:
```python
st.session_state["baseline_load_df"]      # pd.DataFrame, index=DatetimeIndex, col='p_mw'
st.session_state["flex_scenario_load_df"] # pd.DataFrame, index=DatetimeIndex, col='p_mw'
st.session_state["participation_rate"]    # float 0.0–1.0
```
Show a button "→ Im Netzmodell analysieren" that navigates to the network scenario
page using `st.switch_page()`.

---

## Section D — New Page: Network Scenario

Create `C:\Users\sbirk\Documents\Code\vise-d\src\pages\network_scenario.py`.

This is the central integration page. It wires together:
- A pandapower network
- MaStR generation assets (from `src/mastr/simulation.py`)
- Household load profiles (from session state or inline configuration)
- The vpplib interface functions from `src/utils/vpplib_interface.py`

### UI flow

**Step 1: Network selection**

Dropdown with pandapower test networks:
```python
networks = {
    "4-Knoten-Stichleitung":   pn.panda_four_load_branch(),
    "CIGRE Mittelspannung":    pn.create_cigre_network_mv(),
    "Kerber Freileitung":      pn.create_kerber_landnetz_freileitung_1(),
}
```
Show the selected network topology using `pp.plotting.plotly.simple_plotly(net)`.

**Step 2: Region and time period**

- Text input: Ort (e.g. "Aachen") — passed to `prepare_solar_data(location=...)` and
  `prepare_wind_data(location=...)` from `src/mastr/simulation.py`.
- Date range picker: start and end date for the simulation.

**Step 3: Asset simulation**

On button click "MaStR-Anlagen laden":
1. Call `prepare_solar_data(location, mastr_db_path)` and `prepare_wind_data(...)`.
   The `mastr_db_path` should be read from `src/config/paths.py` or a configurable
   setting. Show how many assets were found, how many have coordinates.
2. Call `revise_power_values(gdf)` on the solar GDF.
3. Build PV and wind timeseries using `build_pvsystems_from_params` /
   `init_windturbines_mastr` from `src/mastr/simulation.py`.
   Use `fetch_weather_for_pv` / `fetch_weather_for_wind` from
   `src/data_layer/weather_integration.py` for the environment.
4. Call `assign_assets_to_buses(net, gdf)` from `src/utils/vpplib_interface.py`
   for each asset type.
5. Create pandapower sgen elements in the net for each asset at its assigned bus.

**Step 4: Load configuration**

Check if `st.session_state` has `baseline_load_df` (set by the flexibility
configurator page). If yes, show a summary and use it. If not, show a simplified
inline slider: total load in kW, distributed uniformly across load buses.

Build `load_timeseries_df`: a DataFrame with DatetimeIndex matching the simulation
period, columns = load element indices in `net.load.index`, values = p_mw.

**Step 5: Run scenario**

Two buttons side by side:
- "Basis-Szenario berechnen" → calls `build_timeseries_net(net, sgen_df, load_df)`
- "Flexibilitäts-Szenario berechnen" → calls with `flex_scenario_load_df`

Show a spinner while running. Store results in session state.

**Step 6: Results visualisation**

Show results side-by-side (baseline vs. flexibility):

- **Leitungsauslastung**: Heatmap (lines × time), colour scale 0–120%,
  red above 100%. Use Plotly `px.imshow`.
- **Engpass-Zeitpunkte**: Table of (timestamp, line_name, loading_%) where
  loading > 80%.
- **Spannungsband**: Min/max bus voltage per timestep as a ribbon chart.
- **Summary metric**: "Engpässe beseitigt: X von Y Zeitpunkten" comparing
  baseline vs. flexibility scenario.

Write results to:
```python
st.session_state["scenario_results"]  # dict from build_timeseries_net
st.session_state["selected_net"]      # pandapower network object
```

---

## Section E — DWD Consolidation (do after Agent 1 is done)

Once Agent 1 confirms the vpplib DWDClient is updated, change
`src/data_layer/weather_integration.py`:

```python
# Remove:
from dwd_fetcher import DWDFetcher

# Add:
from vpplib.dwd_client import DWDClient

def get_dwd_fetcher():
    return DWDClient(
        cache_dir=str(cache_dir),
        cache_expiry_hours=DWD.CACHE_EXPIRY_HOURS,
        timezone=DWD.TIMEZONE,
    )
```

Also update the `get_observations()` calls to pass `for_pvlib=True` and
`allow_multi_station=True` as Agent 1 has added these parameters.

Mark this section with a `# TODO: DWD consolidation — pending Agent 1` comment
until it can be done.

---

## Section F — What NOT to do

- Do not modify `src/mastr/simulation.py` — use it as-is.
- Do not modify `src/data_layer/weather_integration.py` until Agent 1 is done
  (mark with TODO).
- Do not modify any existing dashboard pages (`src/pages/`).
- Do not add new Python package dependencies that are not already installed in the
  vise-d virtual environment (`vise/`).
- Do not create README files.
- Do not commit the `data/flexibility_profiles/*.csv` files to git if the repo
  has a `.gitignore` rule for data files — check first.

---

## Suggested order of work

1. Read `src/mastr/simulation.py` — understand the asset pipeline.
2. Read `src/data_layer/weather_integration.py` — understand DWD interface.
3. Read `src/network/examples.py` — understand existing network display.
4. Read `household_flexibility_simulation/main.py` and `output/export.py`.
5. Run `household_flexibility_simulation/main.py` → copy CSVs.
6. Create `src/utils/vpplib_interface.py` (mock).
7. Create `src/flexibility/` folder and copy + fix imports for all modules.
8. Create `src/pages/flexibility_configurator.py`.
9. Create `src/pages/network_scenario.py`.
10. Mark DWD consolidation as TODO and leave a clear comment for handoff.
