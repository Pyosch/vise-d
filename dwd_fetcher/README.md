# DWD Data Fetcher

A Python module for fetching meteorological data from the Deutscher Wetterdienst (DWD) Open Data portal. Provides access to both historical/recent observations and MOSMIX forecasts for solar irradiance, wind speed, temperature, and air pressure across Germany.

**Key Design Decision**: Direct DWD Open Data access without the `wetterdienst` library, which has breaking changes and compatibility issues.

## Features

- **Direct DWD Open Data Access**: Fetches data directly from https://opendata.dwd.de/ without third-party dependencies
- **Quality-Based Station Selection**: Intelligent ranking that prioritizes stations with available data over just proximity
- **Observation Data**: Historical and recent measurements from DWD weather stations
- **Forecast Data**: MOSMIX forecasts with up to 10-day horizon (parser implementation pending)
- **Multi-Station Support**: Combines data from multiple nearby stations with configurable weighting strategies
- **Automatic Data Merging**: Seamlessly merges historical and recent data with boundary documentation
- **pvlib & windpowerlib Compatible**: Output formats ready for solar and wind energy simulations
- **Intelligent Caching**: Configurable cache with 24-hour default expiry and manual refresh
- **Station Search**: Location-based search with distance calculation
- **Resolution-Aware**: Handles parameter-specific data storage patterns (e.g., 10-minute pressure in temperature files)

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from dwd_fetcher import DWDFetcher, WeightingStrategy
from datetime import datetime

# Initialize fetcher with quality-based ranking
fetcher = DWDFetcher(
    cache_dir=".dwd_cache",
    cache_expiry_hours=24,
    timezone="Europe/Berlin",
    weighting_strategy=WeightingStrategy.INVERSE_DISTANCE,
    ranking_strategy="quality_weighted",  # Recommend over "distance_only"
    quality_check_limit=5  # Check 5 closest stations for data availability
)

# Find nearest weather stations
stations = fetcher.find_stations(
    latitude=52.52,  # Berlin
    longitude=13.41,
    parameters=['solar', 'wind', 'temperature', 'pressure'],
    n=3,
    max_distance_km=50,
    active_only=False  # False allows access to historical data from inactive stations
)

# Get observation data
obs_data, metadata = fetcher.get_observations(
    latitude=52.52,
    longitude=13.41,
    parameters=['solar', 'wind', 'temperature', 'pressure'],
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31),
    resolution='hourly',  # 'hourly', 'daily', or '10_minutes'
    for_pvlib=True,  # Format for pvlib
    active_only=False  # Allow stations outside their active date range
)

print(f"Retrieved {len(obs_data)} observations")
print(f"Stations used: {metadata['stations_used']}")
print(f"Data sources: {metadata['data_sources']}")

# Get forecast data
forecast_data, forecast_meta = fetcher.get_forecast(
    latitude=52.52,
    longitude=13.41,
    for_pvlib=True
)

print(f"Retrieved {len(forecast_data)} forecast timesteps")

# Get combined historical + forecast
combined_data, combined_meta = fetcher.get_combined_data(
    latitude=52.52,
    longitude=13.41,
    parameters=['solar', 'wind', 'temperature', 'pressure'],
    historical_start=datetime(2024, 12, 1),
    include_forecast=True,
    for_pvlib=True
)

print(f"Combined dataset: {len(combined_data)} timesteps")
print(f"Transition point: {combined_meta.get('transition_point')}")
```
```

## Configuration

### Station Ranking Strategies

The module supports three strategies for selecting stations:

1. **`distance_only`** (fastest): Select by distance only
   - No quality checks
   - May select stations without data for requested period
   - Best for quick queries when data availability is known

2. **`quality_weighted`** (recommended): Balance distance and data quality
   - Checks file existence for closest N stations
   - Scores stations by: (quality² × 1000) / distance²
   - Quality based on temporal relevance (1.0 = active, 0.7 = <1yr old, etc.)
   - Adds ~1 second but significantly improves data retrieval success

3. **`quality_first`**: Prioritize data quality over distance
   - Sorts by quality score first, then distance
   - Best when data availability is critical

```python
# Example: Quality-weighted ranking (recommended)
fetcher = DWDFetcher(
    ranking_strategy="quality_weighted",
    quality_check_limit=5  # Check 5 closest stations
)

data, meta = fetcher.get_observations(
    latitude=50.94,
    longitude=6.96,
    parameters=['temperature'],
    resolution='10_minutes'
)

# Check quality scores in metadata
for station in meta['stations_used']['temperature']:
    print(f"{station['name']}: quality={station['quality_score']}, "
          f"distance={station['distance_km']:.1f}km, "
          f"combined={station['combined_score']:.2f}")
```

### Weighting Strategies

When combining data from multiple stations:

- `INVERSE_DISTANCE`: Weight by 1/distance² (default)
- `SIMPLE_AVERAGE`: Equal weighting for all stations
- `NEAREST_ONLY`: Use only the nearest station
- `DATA_COMPLETENESS`: Weight by data completeness

```python
from dwd_fetcher import WeightingStrategy

fetcher = DWDFetcher(weighting_strategy=WeightingStrategy.DATA_COMPLETENESS)
```

### Cache Management

```python
# Get cache information
cache_info = fetcher.get_cache_info()
print(cache_info)

# Clear cache
fetcher.clear_cache()

# Force refresh specific data
data, meta = fetcher.get_observations(
    latitude=52.52,
    longitude=13.41,
    parameters=['temperature'],
    force_refresh=True  # Bypass cache
)
```

### MOSMIX Parameter Updates

```python
# Update MOSMIX parameter definitions from DWD
fetcher.update_mosmix_parameters()
```

## Parameters

Available parameters:
- **solar**: Solar global radiation (GHI) - *10-minute resolution only*
- **wind**: Wind speed at 10m height
- **temperature**: Air temperature at 2m height
- **pressure**: Air pressure at station level

### Resolution Support

| Parameter | 10-minute | Hourly | Daily |
|-----------|-----------|--------|-------|
| solar | ✅ | ❌ | ❌ |
| wind | ✅ | ✅ | ✅ |
| temperature | ✅ | ✅ | ✅ |
| pressure | ✅ | ✅ | ✅ |

### Important: Resolution-Dependent Data Storage

**Pressure data** has a special storage pattern on DWD servers:
- **10-minute resolution**: Stored in `air_temperature` directory (column: `PP_10`)
- **Hourly/daily resolution**: Stored in separate `pressure` directory (column: `P0`)

The module handles this automatically using resolution-aware configuration methods. When fetching 10-minute pressure data, it correctly accesses the temperature files that contain both temperature and pressure measurements.

### Quality Flags

Quality flags (QN columns) are preserved with parameter-specific naming to avoid column overlap:
- `QN_temperature`: Temperature quality flag
- `QN_wind`: Wind quality flag
- `QN_pressure`: Pressure quality flag
- `QN_solar`: Solar quality flag

Quality values typically range from 1-10, where higher values indicate better quality. These can be used for filtering if needed.

## Data Formats

### For pvlib

```python
data, _ = fetcher.get_observations(
    latitude=52.52,
    longitude=13.41,
    parameters=['solar', 'wind', 'temperature', 'pressure'],
    for_pvlib=True
)

# Columns: ghi, temp_air, wind_speed, pressure
# Units: W/m², °C, m/s, hPa
# Index: timezone-aware datetime
```

### For windpowerlib

```python
data, _ = fetcher.get_observations(
    latitude=52.52,
    longitude=13.41,
    parameters=['wind', 'temperature', 'pressure'],
    for_windpowerlib=True
)

# Columns: wind_speed, temperature, pressure, height
# Units: m/s, °C, hPa, m
# Index: timezone-aware datetime
```

## Multi-Station Handling

The module can combine data from multiple nearby stations when requested:

```python
data, metadata = fetcher.get_observations(
    latitude=52.52,
    longitude=13.41,
    parameters=['solar', 'wind'],
    n_stations=3,  # Use up to 3 stations per parameter
    max_distance_km=50,
    allow_multi_station=True
)

# Check which stations were used
for param, stations in metadata['stations_used'].items():
    print(f"{param}: {len(stations)} stations")
    for station in stations:
        print(f"  - {station['name']} ({station['distance_km']:.1f} km)")

# Check for warnings about multi-station merging
for warning in metadata['warnings']:
    print(f"Warning: {warning}")
```

## Data Boundary Handling

Historical and recent data are automatically merged:

```python
data, metadata = fetcher.get_observations(
    latitude=52.52,
    longitude=13.41,
    parameters=['temperature'],
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2024, 12, 31)
)

# Check data sources
for param, sources in metadata['data_sources'].items():
    for source in sources:
        print(f"{param} - Station {source['station_id']}:")
        print(f"  Sources: {source['sources']}")
        print(f"  Boundary: {source['boundary_date']}")
```

## Project Structure

```
dwd_data_fetcher/
├── dwd_fetcher/
│   ├── __init__.py          # Package initialization
│   ├── config.py            # Configuration and constants
│   ├── cache.py             # Cache management with MD5 hashing
│   ├── downloader.py        # HTTP download with retry logic
│   ├── stations.py          # Station search, quality scoring
│   ├── fetcher.py           # Main API interface (DWDFetcher)
│   ├── transformers.py      # Data merging and transformations
│   └── parsers/
│       ├── __init__.py
│       ├── mosmix_params.py # MOSMIX parameter extractor
│       ├── observations.py  # ZIP/CSV observation parser
│       └── forecasts.py     # KMZ/KML forecast parser (pending)
├── example.py               # Comprehensive usage examples
├── requirements.txt
├── setup.py
└── README.md
```

## Key Implementation Details

### Station Metadata

- Station files can be in TWO locations: parameter directory or `/help/` directory
- `start_date` and `end_date` indicate operational period
- `active_only=False` (default) allows accessing historical data from inactive stations

### DWD Server File Naming

- Recent data: `{resolution}_{param_code}_{station_id:05d}_akt.zip`
- Historical data: `{resolution}_{param_code}_{station_id:05d}_*_hist.zip`
- Resolution strings: `stundenwerte` (hourly), `zehnminutenwerte` (10-minute), `tageswerte` (daily)

### Data Parsing

- **Delimiter**: semicolon (`;`)
- **Encoding**: `latin-1`
- **Missing values**: `-999` (converted to NaN)
- **Timestamp format**: `YYYYMMDDHH` (e.g., `2024010113` = 2024-01-01 13:00)
- **Quality flags**: Renamed to be parameter-specific to avoid column overlap

### Multi-Station Merging

- Only numeric columns are merged
- Metadata columns (`STATIONS_ID`, `MESS_DATUM`, `eor`) dropped before merging
- Weighting computed by distance or data completeness
- Outer join preserves all timestamps

### Pressure Unit Conversion

- Checks median value: if > 10000, assumes Pa and divides by 100
- Handles both Series and DataFrame columns from joins

## Dependencies

- **requests**: HTTP requests to DWD servers
- **pandas**: Data manipulation and time series
- **numpy**: Numerical operations
- **lxml**: XML/KML parsing for MOSMIX
- **pytz**: Timezone handling

## Data Sources

This module fetches data from:
- **Observations**: `https://opendata.dwd.de/climate_environment/CDC/observations_germany/`
- **Forecasts**: `https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_S/`
- **Parameter Definitions**: `https://opendata.dwd.de/weather/lib/MetElementDefinition.xml`

## License

This module accesses freely available data from DWD's Open Data portal. Please refer to DWD's data usage terms.

## Development Status

**Version**: 0.1.0 (Alpha)

### Implemented
- ✅ Direct DWD Open Data access
- ✅ Station search with quality-based ranking
- ✅ Observation data fetching (historical + recent)
- ✅ Multi-station data merging with multiple weighting strategies
- ✅ Resolution-aware parameter handling
- ✅ pvlib/windpowerlib output formatting
- ✅ Intelligent caching with expiration
- ✅ Quality flag preservation
- ✅ Comprehensive error handling and warnings

### Pending
- ⏳ MOSMIX forecast parsing (KMZ/KML)
- ⏳ Height correction for wind data
- ⏳ Quality flag filtering options
- ⏳ Async/parallel downloads
- ⏳ Additional parameters (humidity, precipitation)
- ⏳ ICON model data integration

## Known Issues and Limitations

1. **MOSMIX forecasts**: Parser not yet implemented (returns 0 timesteps)
2. **Station file availability**: Some stations in metadata don't have actual data files (404 errors handled gracefully)
3. **Solar data**: Only available at 10-minute resolution
4. **Column overlap**: Resolved by parameter-specific quality flag naming
5. **No automatic interpolation**: Data gaps preserved; user's choice to fill

## Troubleshooting

### No data returned / Empty DataFrame
- **Cause**: Station inactive OR files not found OR date range outside coverage
- **Solution**: Set `active_only=False`, check `metadata['warnings']`, verify date range, use `ranking_strategy="quality_weighted"`

### 404 Client Error: Not Found
- **Cause**: Station has metadata but no data files on server
- **Solution**: Try more stations (increase `n_stations`) or different location, use quality-weighted ranking

### Station selection issues
- **Problem**: Closest station has no data
- **Solution**: Use `ranking_strategy="quality_weighted"` instead of `"distance_only"`
- **Example**: Near Köln, station 02968 (5.6km) ended Sept 2024, but station 02667 (16.2km) has data through Jan 2026

## Contributing

This is an initial implementation. Contributions welcome for:
- MOSMIX forecast parser implementation
- Additional parameters support
- Performance optimization (async downloads)
- Data quality visualization tools
- Height correction algorithms
- Extended documentation and examples

## Notes

- Cache default expiry: 24 hours for observations, 1 hour for forecasts
- Station search uses Haversine distance calculation
- All timestamps handled in UTC and converted to specified timezone
- Missing data: User's choice to interpolate, forward_fill, or drop
- Quality flags preserved and can be filtered by users
- **Station activity**: `active_only=False` allows finding stations even if current date is outside operational period (essential for historical data)
- **Data availability**: Not all stations have files for all periods; module gracefully handles missing files and combines available data from multiple stations
- **Quality-based ranking adds ~1 second** but significantly improves data retrieval success
- **Performance**: Sequential downloads (parallel implementation future improvement)
- **Column naming**: QN flags are parameter-specific (e.g., `QN_temperature`, `QN_wind`) to prevent merge conflicts
