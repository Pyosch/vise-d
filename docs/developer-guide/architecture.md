# VISE-D Architecture

**Last Updated:** January 2026

## Overview

VISE-D follows a modular layered architecture with clear separation of concerns. The application is structured around a Streamlit dashboard that orchestrates various modules for data access, business logic, and visualization.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│                    Presentation Layer                    │
│  dashboard.py (navigation) + src/pages/ (page modules)  │
│              src/ui/ (components, layout)                │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   Business Logic Layer                   │
│  src/planning/ (solar/wind) + src/forecasting/ (models) │
│         src/network/ (pandapower integration)            │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    Data Access Layer                     │
│    src/data_layer/ (caching, loaders, environment)      │
│         src/mastr/ (database queries, preprocessing)     │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  Infrastructure Layer                    │
│   src/config/ (paths, constants) + src/utils/ (helpers) │
│      src/visualization/ (plotting, displays, maps)       │
└─────────────────────────────────────────────────────────┘
```

## Module Directory Structure

```
src/
├── config/              # Configuration management (Layer: Infrastructure)
│   ├── paths.py         # Cross-platform path definitions using pathlib
│   └── constants.py     # Application-wide constants (PV modules, BEV types)
│
├── data_layer/          # Data access and caching (Layer: Data Access)
│   ├── cache.py         # Streamlit cache decorators with TTL config
│   ├── loaders.py       # Data loading functions (CSV, network graphs)
│   └── environment.py   # vpplib Environment caching (1-hour TTL)
│
├── utils/               # Shared utilities (Layer: Infrastructure)
│   ├── validation.py    # Input validation (ranges, coordinates, efficiency)
│   ├── error_handling.py # Error decorators and user-friendly messages
│   └── helpers.py       # Utility functions (safe_float, format_energy)
│
├── mastr/               # MaStR database integration (Layer: Data Access)
│   ├── preprocessing.py # Database queries, geodata loading
│   └── simulation.py    # MaStR data simulation and processing
│
├── forecasting/         # Energy forecasting (Layer: Business Logic)
│   ├── openstef.py      # OpenSTEF model integration, MLflow tracking
│   └── utils.py         # Forecasting helper functions
│
├── planning/            # Site planning tools (Layer: Business Logic)
│   ├── solar.py         # Solar farm planning, obstacle detection
│   ├── wind.py          # Wind turbine placement, spacing rules
│   └── geo_utils.py     # Geographic coordinate utilities
│
├── ui/                  # User interface components (Layer: Presentation)
│   ├── components/      # Technology parameter forms (German UI)
│   │   ├── bev.py       # Battery electric vehicle form
│   │   ├── electrical_energy_storage.py
│   │   ├── heat_pump.py
│   │   ├── photovoltaic.py
│   │   ├── wind_power.py
│   │   ├── user_profile.py
│   │   └── environment.py
│   └── layout.py        # Sidebar, navigation elements
│
├── visualization/       # Visualization utilities (Layer: Infrastructure)
│   ├── research_figures.py  # Publication plots (original: lilienkampa)
│   ├── displays.py      # Display components, formatting
│   └── (future: interactive_maps.py for Folium components)
│
├── network/             # Pandapower integration (Layer: Business Logic)
│   └── examples.py      # Example network topologies
│
└── pages/               # Dashboard page modules (Layer: Presentation)
    ├── research_results.py
    ├── network_calculations.py
    ├── bev_settings.py
    ├── heatpump_configuration.py
    ├── pv_configuration.py
    ├── wind_configuration.py
    ├── electrical_storage_configuration.py
    ├── thermal_storage_settings.py
    ├── hydrogen_research.py
    ├── hydrogen_electrolyzer_settings.py
    ├── solar_installation_mastr.py
    ├── wind_installation_mastr.py
    ├── storage_installation_mastr.py
    ├── energy_generation_solar.py
    ├── wind_energy_generation.py
    ├── openstef_forecasting.py
    └── planning_ffpv_wea.py
```

## Module Responsibilities

### Configuration Layer (`src/config/`)

**Purpose:** Centralized configuration management, cross-platform compatibility

**Key Components:**
- `paths.py`: Defines all project paths using pathlib.Path (PROJECT_ROOT, DATA_DIR, MASTR_DB_PATH)
- `constants.py`: Application constants (PV_MODULES, BEV_TYPES, REGIONS, default values)

**Design Pattern:** Singleton-like module imports ensure consistent paths across application

**Dependencies:** None (foundation layer)

### Data Layer (`src/data_layer/`)

**Purpose:** Manage data loading, caching, and environment creation with intelligent TTL

**Key Components:**
- `cache.py`: Streamlit cache decorators (@st.cache_data, @st.cache_resource)
- `loaders.py`: Data loading functions with appropriate TTL configuration
- `environment.py`: vpplib Environment object caching (expensive operation, 1-hour TTL)

**Caching Strategy:**
| Function | TTL | Rationale |
|----------|-----|-----------|
| `load_netzgraph()` | Default | Static network topology |
| `load_mosmix_data()` | Default | Historical weather data |
| `load_vpplib_environment()` | 1 hour | ERA5 data changes daily |
| MaStR queries | 30 min | Database relatively static |
| Visualizations | 10 min | Parameter-dependent, regenerate on changes |

**Design Pattern:** Decorator pattern for caching, Factory pattern for Environment creation

**Dependencies:** config/, utils/

### Utilities Layer (`src/utils/`)

**Purpose:** Shared functionality used across multiple modules

**Key Components:**
- `validation.py`: Real-time input validation with industry standards
  - Numeric ranges, percentages, efficiency values
  - Geographic coordinates, power ratings
  - Energy system parameters
- `error_handling.py`: User-friendly error handling with troubleshooting guidance
  - Database operation errors
  - API call errors
  - Data processing errors
- `helpers.py`: Utility functions (safe_float, format_energy)

**Design Pattern:** Utility/Helper pattern, Decorator pattern for error handling

**Dependencies:** None (foundation layer)

### MaStR Integration (`src/mastr/`)

**Purpose:** Interface with German Marktstammdatenregister database (26,000+ installations)

**Key Components:**
- `preprocessing.py`: Database queries, geodata loading, location filtering
  - Supports solar (11,558), wind (3,827), storage (11,042) installations
  - Geodata with coordinates for geographic visualization
- `simulation.py`: MaStR data simulation and analysis

**Data Flow:**
```
SQLite DB (data/open-mastr.db)
    ↓
preprocessing.py (queries, filtering)
    ↓
GeoDataFrame with coordinates
    ↓
Cached in data_layer (30-min TTL)
    ↓
Used by pages/ modules for visualization
```

**Design Pattern:** Repository pattern for data access, DTO pattern for geodata

**Dependencies:** config/, data_layer/, utils/

### Forecasting Layer (`src/forecasting/`)

**Purpose:** Energy generation forecasting using OpenSTEF models

**Key Components:**
- `openstef.py`: OpenSTEF integration, model training, MLflow tracking
- `utils.py`: Forecasting utilities, data preparation

**Data Flow:**
```
Historical weather data (DWD/ERA5)
    ↓
Feature engineering (openstef.py)
    ↓
OpenSTEF model (XGBoost/LightGBM)
    ↓
PV/Wind generation forecast
    ↓
MLflow tracking for model versions
```

**Design Pattern:** Strategy pattern for different forecast models, Observer pattern for MLflow tracking

**Dependencies:** data_layer/, utils/

### Planning Layer (`src/planning/`)

**Purpose:** Geographic site planning for solar and wind installations

**Key Components:**
- `solar.py`: Solar farm planning with obstacle detection
  - `fetch_obstacles_solar()`: OpenStreetMap queries
  - `packing_solar()`: Panel placement algorithm
  - `simulate_solarfarm_output()`: Energy generation calculation
- `wind.py`: Wind turbine placement with spacing constraints
  - `fetch_obstacles_wind()`: Wind-specific obstacles
  - `packing_wind()`: Turbine placement with distance rules
  - `get_weather_for_windpowerlib()`: ERA5 data loading
- `geo_utils.py`: Coordinate transformations, distance calculations

**Algorithms:**
- **Solar packing**: Grid-based placement with obstacle avoidance
- **Wind packing**: Minimum distance constraints (3-5 rotor diameters)

**Design Pattern:** Template Method pattern for packing algorithms, Strategy pattern for obstacle detection

**Dependencies:** data_layer/, utils/, config/

**Known Issue:** `simulate_windfarm_output()` not yet implemented

### UI Layer (`src/ui/`)

**Purpose:** User interface components with German language text

**Key Components:**
- `components/`: Technology parameter input forms
  - Each component creates Streamlit forms for user input
  - Returns configuration dictionaries for vpplib models
  - **Important:** UI forms only, not model implementations (models from vpplib library)
- `layout.py`: Sidebar navigation, page layout utilities

**vpplib Integration:**
```
UI Form (German labels)
    ↓
Parameter dictionary
    ↓
vpplib component creation (Photovoltaic, WindPower, BatteryElectricVehicle)
    ↓
Simulation with Environment object
    ↓
Results visualization
```

**Design Pattern:** Form Object pattern, Facade pattern for vpplib integration

**Language Policy:** German UI text, English code/comments (dual-language approach)

**Dependencies:** config/, utils/

### Visualization Layer (`src/visualization/`)

**Purpose:** Plotting, interactive visualizations, display formatting

**Key Components:**
- `research_figures.py`: Publication-quality research plots (original author: lilienkampa)
  - EV integration research visualizations
  - Interactive Plotly charts
- `displays.py`: Display components, data formatting utilities

**Visualization Types:**
- Research plots: `fig_5()`, `fig_7()`, `fig_8()`, `fig_9()`
- Interactive maps: Plotly Mapbox (scatter maps, heatmaps)
- Statistical plots: Violin plots, distribution analysis

**Design Pattern:** Builder pattern for complex visualizations, Strategy pattern for different plot types

**Dependencies:** data_layer/, utils/

### Network Layer (`src/network/`)

**Purpose:** Pandapower grid network analysis and power flow calculations

**Key Components:**
- `examples.py`: Example network topologies (German UI labels)

**Power Flow Analysis:**
```
Network topology (pandapower.Network)
    ↓
Component loads (PV, wind, BEV, heat pumps)
    ↓
Power flow calculation (pandapower.runpp)
    ↓
Results (voltages, line loading, transformer utilization)
    ↓
Visualization (network diagram, loading plots)
```

**Design Pattern:** Facade pattern for Pandapower integration

**Dependencies:** data_layer/, visualization/

### Pages Layer (`src/pages/`)

**Purpose:** Dashboard page modules, each implementing a specific analysis workflow

**Key Components:**
- 17 page modules, each with a `render()` function called by dashboard.py
- Each page orchestrates: UI forms → data loading → business logic → visualization

**Page Categories:**
1. **Research & Analysis** (2 pages)
   - research_results.py, hydrogen_research.py
2. **Technology Configuration** (8 pages)
   - bev_settings.py, heatpump_configuration.py, pv_configuration.py, etc.
3. **MaStR Data Analysis** (3 pages)
   - solar_installation_mastr.py, wind_installation_mastr.py, storage_installation_mastr.py
4. **Energy Generation** (2 pages)
   - energy_generation_solar.py, wind_energy_generation.py
5. **Planning & Forecasting** (2 pages)
   - planning_ffpv_wea.py, openstef_forecasting.py

**Design Pattern:** Page Controller pattern, each page is independent module

**Dependencies:** All layers (orchestrates entire application stack)

## Data Flow Patterns

### Typical User Workflow

```
1. User navigates to page (dashboard.py → pages/*)
    ↓
2. Page loads cached data (pages/* → data_layer/)
    ↓
3. User fills form (ui/components/)
    ↓
4. Business logic processes parameters (planning/, forecasting/, network/)
    ↓
5. Results visualized (visualization/)
    ↓
6. Cached for future requests (data_layer/)
```

### MaStR Data Flow

```
SQLite Database (data/open-mastr.db)
    ↓
mastr/preprocessing.py (query with location filter)
    ↓
data_layer/cache.py (30-min TTL)
    ↓
pages/solar_installation_mastr.py (display and analysis)
    ↓
visualization/displays.py (maps, charts)
```

### Forecasting Data Flow

```
Historical weather data (ERA5/DWD)
    ↓
data_layer/environment.py (vpplib Environment, 1-hour cache)
    ↓
forecasting/openstef.py (feature engineering, model training)
    ↓
OpenSTEF model prediction
    ↓
MLflow tracking (model versioning)
    ↓
pages/openstef_forecasting.py (visualization)
```

### Planning Data Flow

```
User draws polygon on map (pages/planning_ffpv_wea.py)
    ↓
planning/geo_utils.py (coordinate conversion)
    ↓
planning/solar.py or wind.py (obstacle detection via OSM)
    ↓
Packing algorithm (solar panel or turbine placement)
    ↓
Simulation (energy generation calculation)
    ↓
visualization/ (results display)
```

## Key Design Patterns

### 1. Layered Architecture
- Clear separation: presentation → business logic → data access → infrastructure
- Each layer depends only on layers below, not above

### 2. Caching Strategy (Decorator Pattern)
- Streamlit @st.cache_data for immutable data
- Streamlit @st.cache_resource for expensive objects (vpplib Environment)
- Configurable TTL based on data change frequency

### 3. Repository Pattern (MaStR Integration)
- Abstracts database access behind clean interface
- Enables testing with mock repositories

### 4. Facade Pattern (vpplib/Pandapower Integration)
- Simplifies complex library interfaces
- UI components create simple config dicts, facades handle library complexity

### 5. Page Controller Pattern
- Each page is independent module with render() function
- dashboard.py acts as front controller, routing to page modules

### 6. Error Handling (Decorator Pattern)
- @handle_errors decorator provides consistent error handling
- User-friendly messages with troubleshooting guidance

## Testing Architecture

```
tests/
├── conftest.py           # Shared fixtures (mock_streamlit, temp_mastr_db)
├── data_layer/           # Data layer tests (19 tests, 100% pass)
│   ├── test_cache.py
│   └── test_environment.py
├── pages/                # Page module tests (34 tests, 67.6% pass)
│   ├── test_research_results.py
│   ├── test_bev_settings.py
│   └── ...
└── (future: planning/, forecasting/, network/)
```

**Test Strategy:**
- Mock Streamlit caching decorators using `__wrapped__` attribute
- Lightweight fixtures avoid heavy dependencies (no actual DB/file I/O)
- Test both success and failure paths for error handling

**Current Coverage:** ~30% (pages only)  
**Target:** 70% → 90% for production

## Module Dependency Graph

```
dashboard.py (entry point)
    ↓
pages/* (17 page modules)
    ↓ ↓ ↓
    ↓ planning/         forecasting/         network/
    ↓     ↓                  ↓                  ↓
    ↓     └──────────────────┴──────────────────┘
    ↓                        ↓
    ↓                   data_layer/
    ↓                        ↓
    ui/                 mastr/
    ↓                        ↓
visualization/               ↓
    ↓                        ↓
    └────────────────────────┴──────→ config/, utils/
```

**Key Principles:**
- No circular dependencies
- Lower layers have no knowledge of upper layers
- config/ and utils/ are foundation (no dependencies)

## Extension Points

### Adding a New Page
1. Create `src/pages/new_page.py` with `render()` function
2. Add page to `dashboard.py` navigation
3. Import required modules (data_layer, planning, visualization)
4. Create tests in `tests/pages/test_new_page.py`

### Adding a New Technology Component
1. Create UI form in `src/ui/components/new_tech.py`
2. Return configuration dict compatible with vpplib or custom model
3. Add page in `src/pages/new_tech_configuration.py`
4. Update `src/config/constants.py` with technology-specific constants

### Adding a New Data Source
1. Create module in `src/data_layer/new_source.py`
2. Implement caching with appropriate TTL
3. Add preprocessing in separate module if needed
4. Create tests with mock data

## Performance Considerations

### Caching
- **Critical:** vpplib Environment creation is expensive (5-15 seconds)
- **Strategy:** 1-hour TTL balances freshness vs. performance
- **Impact:** 90%+ load time reduction for cached operations

### Database Queries
- **Issue:** Large MaStR queries (26,000+ records) not paginated
- **Mitigation:** 30-minute cache reduces repeated queries
- **Future:** Implement pagination for large result sets

### Visualization
- **Issue:** Map rendering can be slow (3-8 seconds)
- **Mitigation:** 10-minute cache for parameter-dependent visualizations
- **Future:** Lazy loading for off-screen map elements

## Security Considerations

### Input Validation
- All user inputs validated through `src/utils/validation.py`
- Numeric ranges checked against industry standards
- Geographic coordinates validated before OSM queries

### Database Access
- Read-only access to MaStR database
- No user-provided SQL queries (parameterized queries only)

### File System Access
- All paths use `pathlib` for safe cross-platform handling
- No user-provided file paths

## Future Architectural Improvements

### Phase 6: Testing
- Increase coverage 30% → 70%
- Add integration tests for cross-module workflows
- CI/CD pipeline with automated test runs

### Phase 7: Tariff Design Studio
- New `src/tariff/` module for tariff modeling
- DSO intervention analysis algorithms
- Economic impact calculations

### Phase 8: Multi-Scenario Planning
- `src/scenarios/` module for scenario management
- Batch simulation engine
- Parallel processing for parameter sweeps

---

**Author:** Pyosch  
**AI Assistance:** GitHub Copilot (Claude Sonnet 4.5)
