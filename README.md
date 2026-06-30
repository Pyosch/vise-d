# VISE-D: Virtuelles Institut Smart Energy - Smart Data

Interactive Streamlit dashboard for energy-system analysis of German distribution grids:
multi-technology DER simulation, real MaStR installation data, weather-driven load and
generation profiles, and Pandapower power-flow analysis.

## Features

- **Multi-technology simulation**: PV, wind, battery storage, heat pumps, electric vehicles
- **Grid network analysis**: Pandapower-based time-series power flow with voltage-band and
  line/transformer loading checks
- **Real data integration**: 26,000+ installations from the MaStR (Marktstammdatenregister)
- **Flexibility modelling**: Appliance-level household load shifting and aggregation
- **Interactive planning**: Geographic tools for solar and wind site planning
- **Reporting**: Excel and PDF export of simulation results

## Quick Start

```bash
# Clone and navigate
git clone <repository-url>
cd vise-d

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/macOS

# Install and run
pip install -r requirements.txt
streamlit run dashboard.py
```

Dashboard opens at `http://localhost:8501`

## Documentation

- **[Getting Started](docs/getting-started/)** - Installation, configuration, quickstart
- **[Dashboard Documentation](docs/project/dashboard-dokumentation.md)** - Page-by-page guide (German)
- **[Developer Guide](docs/developer-guide/)** - Architecture, testing, caching
- **[Project Roadmap](roadmap.md)** - Project status and overview

## Project Status

Refactored into a clean, modular architecture: the dashboard entry point was reduced from
2,351 lines to 89 lines (90.2% reduction), with all application code organised under `src/`.
See the [phase reports](docs/project/phase-reports/) for the refactoring history.

## Key Dependencies

- Python 3.11+, Streamlit, Pandapower
- vpplib 0.0.6 (component models)
- windpowerlib, geopandas / shapely / pyproj
- pandas, numpy, plotly, matplotlib

## Language Policy

**Code & Comments**: English (PEP 8, international collaboration)  
**User Interface**: German (target audience)

## Testing

```bash
pytest                              # Run all tests
pytest --cov=src --cov-report=html  # With coverage
```

Test markers (`unit`, `integration`, `ui`, `slow`) are registered in `tests/conftest.py`.

## Authors

**Pyosch** - Lead Developer  
**Claude Code (Claude Opus 4.8)** - AI Assistance

---

**Last Updated**: June 2026
