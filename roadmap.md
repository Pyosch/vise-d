# VISE-D Project Overview

## Project Overview

VISE-D (Virtuelles Institut Smart Energy - Smart Data) is an energy-system analysis tool for
German distribution grids, providing:

- **Multi-technology simulation**: PV, wind, battery storage, heat pumps, electric vehicles
- **Distribution grid analysis**: Pandapower-based network modeling and time-series power flow
- **Real data integration**: MaStR (Marktstammdatenregister) data with 26,000+ installations
- **Flexibility modelling**: Appliance-level household load shifting and aggregation
- **Interactive planning**: Geographic tools for solar farm and wind turbine site planning
- **Research platform**: Visualization and analysis tools for energy-system research

## Architecture

The project was restructured from a monolithic 2,351-line dashboard into a clean, layered
modular architecture. The `dashboard.py` entry point holds navigation only (89 lines); all
application code lives under `src/`:

```
src/
├── config/              Configuration and constants
├── data_layer/          Data loading and caching
├── utils/               Validation and error handling
├── mastr/               MaStR data integration
├── planning/            Solar/wind planning algorithms
├── ui/components/       Technology parameter forms (German UI)
├── visualization/       Plotting and interactive maps
├── network/             Pandapower network analysis
├── flexibility/         Household load and flexibility models
└── pages/               Dashboard page modules
```

The refactoring history is documented in the
[phase reports](docs/project/phase-reports/) (Phases 0–5).

## OpenSTEF Forecasting (evaluated and discarded)

OpenSTEF (Open Short-Term Energy Forecasting) was integrated and evaluated as a machine-learning
forecasting backend for renewable generation. After evaluation it was found not to meet the
project's quality and usability requirements and was discarded. It is **not** exposed in the
dashboard; the dormant integration code under `src/forecasting/` is retained only for reference.

## Known Limitations

- **Wind-farm planning simulation:** `simulate_windfarm_output()` is referenced by the planning
  module but not implemented; the solar counterpart `simulate_solarfarm_output()` exists.
- **Optimal power flow (OPF):** deprioritized; the time-series power flow uses a fixed voltage
  band and post-hoc loading normalization. OPF is a possible future extension.

## Possible Future Directions

These are ideas for future work, not committed deliverables:

- **Tariff analysis:** time-of-use / real-time pricing models and DSO intervention analysis,
  building on the published research already presented in the dashboard.
- **Multi-scenario planning:** batch simulation, parameter sweeps, and side-by-side scenario
  comparison.

## Development Guidelines

### Code Standards
- **Python:** PEP 8 compliance, Black formatter (line length 88)
- **Docstrings:** Google style, required for all public functions
- **Type Hints:** Python 3.11+ type annotations
- **Language Policy:** English code/comments, German UI text
- **Attribution:** `__author__ = "Pyosch"`, `__credits__ = ["Claude Code (Claude Opus 4.8)"]`

### Testing
- **Framework:** pytest with coverage reports
- **Structure:** `tests/` mirrors the `src/` directory layout
- **Markers:** `unit`, `integration`, `ui`, `slow` (registered in `tests/conftest.py`)

### Git Workflow
- **Commits:** Conventional commits (feat:, fix:, refactor:, docs:, test:, chore:)

## Key Dependencies

- **Python 3.11+**: Core language
- **Streamlit**: Interactive dashboard framework
- **Pandapower**: Grid network analysis
- **vpplib 0.0.6**: Virtual power plant component models
- **windpowerlib**: Wind turbine power curves
- **geopandas / shapely / pyproj / osmnx**: Geographic tooling for site planning

## External Data Sources

- **MaStR**: German Marktstammdatenregister (energy installation registry)
- **DWD**: German Weather Service (weather data via vpplib's `DWDClient`)
- **OSM**: OpenStreetMap (geographic data for planning)

---

**Project Lead:** Pyosch  
**AI Assistance:** Claude Code (Claude Opus 4.8)
