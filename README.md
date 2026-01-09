# VISE-D: Virtuelles Institut Smart Energy - Smart Data

Interactive dashboard for energy system analysis in German distribution grids with real MaStR data, renewable energy forecasting, and network power flow calculations.

## Features

- **Multi-technology simulation**: PV, wind, battery storage, heat pumps, electric vehicles
- **Grid network analysis**: Pandapower-based power flow calculations
- **Energy forecasting**: OpenSTEF integration for renewable predictions
- **Interactive planning**: Geographic tools for solar and wind site planning
- **Real data integration**: 26,000+ installations from MaStR database

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
- **[User Guide](docs/user-guide/)** - Features, forecasting, planning tools
- **[Developer Guide](docs/developer-guide/)** - Architecture, testing, caching
- **[Project Roadmap](roadmap.md)** - Development status and future plans

## Project Status

✅ **Phase 0-5 Complete** (January 2026) - Fully refactored modular architecture  
🔄 **Phase 6 In Progress** - Test coverage expansion (30% → 70%)  
📋 **Future Phases** - Tariff design studio, multi-scenario planning

Dashboard reduced from 2,351 lines → 89 lines (90.2% reduction). See [phase reports](docs/project/phase-reports/).

## Key Dependencies

- Python 3.11+, Streamlit, Pandapower
- vpplib 0.0.5 (component models)
- windpowerlib, OpenSTEF
- pandas, numpy, plotly

## Language Policy

**Code & Comments**: English (PEP 8, international collaboration)  
**User Interface**: German (target audience)

## Testing

```bash
pytest                              # Run all tests
pytest --cov=src --cov-report=html  # With coverage
```

Current: 30% coverage (pages) | Target: 70% → 90%

## Authors

**Pyosch** - Lead Developer  
**GitHub Copilot (Claude Sonnet 4.5)** - AI Assistance

---

**Last Updated**: January 2026
