# VISE-D Architecture

**Last Updated:** June 2026

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
│   src/network/ (pandapower) + src/flexibility/ (load)    │
│        src/planning/ (solar/wind site planning)          │
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
├── planning/            # Site planning tools (Layer: Business Logic)
│   ├── solar.py         # Solar farm planning, obstacle detection
│   ├── wind.py          # Wind turbine placement, spacing rules
│   └── geo_utils.py     # Geographic coordinate utilities
│
├── ui/                  # User interface components (Layer: Presentation)
│   └── components/      # Technology parameter forms (German UI)
│       ├── bev.py
│       ├── electrical_storage.py
│       ├── heat_pump.py
│       ├── photovoltaics.py
│       ├── wind_energy.py
│       ├── location_weather.py
│       └── netzmittimeseries.py
│
├── visualization/       # Visualization utilities (Layer: Infrastructure)
│   ├── research_figures.py  # Publication plots (original: lilienkampa)
│   ├── displays.py      # Display components, formatting
│   └── (future: interactive_maps.py for Folium components)
│
├── network/             # Pandapower integration (Layer: Business Logic)
│   └── examples.py      # Example network topologies
│
├── flexibility/         # Household load and flexibility models (Layer: Business Logic)
│
├── content/             # Shared page descriptions (Layer: Presentation)
│   └── page_descriptions.py
│
└── pages/               # Dashboard page modules (Layer: Presentation)
    ├── startseite.py
    ├── netzmodell.py
    ├── flexibility_configurator.py
    ├── solar_installation_mastr.py
    ├── wind_installation_mastr.py
    ├── storage_installation_mastr.py
    ├── research_results.py
    ├── grid_expansion_research.py
    ├── bev_settings.py
    ├── heatpump_configuration.py
    ├── pv_configuration.py
    ├── wind_configuration.py
    ├── electrical_storage_configuration.py
    └── thermal_storage_settings.py
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

**Note:** the planning module is not currently surfaced as a dashboard page.

**Known limitation:** `simulate_windfarm_output()` is not yet implemented (the solar
counterpart `simulate_solarfarm_output()` exists).

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
- One module per page, imported lazily by dashboard.py on first navigation
- Each page orchestrates: UI forms → data loading → business logic → visualization

**Navigation groups (see `dashboard.py`):**
1. **Übersicht** — startseite.py
2. **Energiesystemanalysen** — netzmodell.py, flexibility_configurator.py
3. **Marktstammdatenregister** — solar_installation_mastr.py, wind_installation_mastr.py,
   storage_installation_mastr.py
4. **Forschungsergebnisse** — research_results.py, grid_expansion_research.py
5. **Lastprofilgeneratoren** — bev_settings.py, heatpump_configuration.py, pv_configuration.py,
   wind_configuration.py, electrical_storage_configuration.py, thermal_storage_settings.py

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
4. Business logic processes parameters (planning/, network/)
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

### Planning Data Flow

```
Polygon geometry (site boundary)
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
├── conftest.py           # Shared fixtures and markers (unit, integration, ui, slow)
├── data_layer/           # Data layer tests
│   ├── test_cache.py
│   └── test_environment.py
└── pages/                # Page module tests
    └── ...
```

**Test Strategy:**
- Mock Streamlit caching decorators using `__wrapped__` attribute
- Lightweight fixtures avoid heavy dependencies (no actual DB/file I/O)
- Test both success and failure paths for error handling

Run `pytest --cov=src --cov-report=html` for a current coverage report.

## Module Dependency Graph

```
dashboard.py (entry point)
    ↓
pages/* (page modules)
    ↓ ↓ ↓
    ↓ planning/                            network/
    ↓     ↓                                    ↓
    ↓     └────────────────────────────────────┘
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

---

**Author:** Pyosch  
**AI Assistance:** Claude Code (Claude Opus 4.8)
