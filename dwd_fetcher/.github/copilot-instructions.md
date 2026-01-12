# Copilot Instructions for DWD Data Fetcher

## Project Overview

This is a Python module for fetching meteorological data from the Deutscher Wetterdienst (DWD) Open Data portal (https://opendata.dwd.de/). It provides access to both historical/recent observations and MOSMIX forecasts for solar irradiance, wind speed, temperature, and air pressure across Germany.

**Key Design Decision**: Direct DWD Open Data access without the `wetterdienst` library, which has breaking changes and compatibility issues.

## Architecture

### Module Structure

```
dwd_fetcher/
├── config.py           # URL patterns, parameter mappings, constants
├── cache.py            # File-based caching with expiration
├── downloader.py       # HTTP downloads with retry logic
├── stations.py         # Station metadata and location search
├── fetcher.py          # Main API (orchestrates other modules)
├── transformers.py     # Data merging and unit conversions
└── parsers/
    ├── mosmix_params.py   # MetElementDefinition.xml parser
    ├── observations.py    # ZIP/CSV observation parser
    └── forecasts.py       # KMZ/KML forecast parser
```

### Data Flow

1. **Station Discovery**: `stations.py` loads station metadata, searches by location
2. **Data Fetching**: `fetcher.py` orchestrates fetching from `observations.py` or `forecasts.py`
3. **Caching**: `cache.py` manages downloads to avoid repeated requests
4. **Transformation**: `transformers.py` merges multi-station data and converts units
5. **Output**: Formatted for pvlib/windpowerlib or raw DataFrames

## Critical Implementation Details

### 1. DWD Server Quirks

**Station File Locations**:
- Station metadata files can be in TWO locations:
  1. Parameter directory (e.g., `/hourly/air_temperature/`)
  2. Help directory (`/help/`)
- `stations.py` tries both locations in `load_stations()`

**File Naming Conventions**:
- Recent data: `{resolution}_{param_code}_{station_id:05d}_akt.zip`
- Historical data: `{resolution}_{param_code}_{station_id:05d}_*_hist.zip`
- Resolution strings: `stundenwerte` (hourly), `zehnminutenwerte` (10-minute), `tageswerte` (daily)
- Station files: `{PARAM_CODE}_{Resolution}_Beschreibung_Stationen.txt`

**Parameter Codes**:
- Solar: `ST` (Strahlung/Stundenwerte)
- Wind: `FF` (wind speed)
- Temperature: `TU` (air temperature)
- Pressure: `P0` (pressure at station level)

### 2. Station Activity Filtering

**Important**: Station metadata includes `start_date` and `end_date` for data availability.

- By default, `active_only=False` in `find_stations()` and `get_observations()`
- This allows finding stations even if current date > station's end_date
- **Why**: Essential for accessing historical data from stations that have stopped operating
- Example: In 2026, most 2025 data comes from stations marked as inactive

### 3. Data Parsing Challenges

**CSV Format**:
- Delimiter: semicolon (`;`)
- Encoding: `latin-1`
- Missing values: `-999` (as string or number)
- Columns include metadata: `STATIONS_ID`, `MESS_DATUM`, `eor`

**Critical**: Must convert ALL data columns to numeric types with `pd.to_numeric(..., errors='coerce')`:
- CSV parser reads some numeric values as strings
- String values cause `TypeError: can't multiply sequence by non-int of type 'float'` during weighted merging
- Drop metadata columns (`STATIONS_ID`, `MESS_DATUM`, `eor`) to prevent join conflicts

**Timestamp Parsing**:
- Format: `YYYYMMDDHH` (e.g., `2024010113` = 2024-01-01 13:00)
- Column names: `MESS_DATUM` or `MESS_DATUM_BEGINN`
- Must drop timestamp column after setting as index

### 4. Multi-Station Data Merging

**Weighting Strategies** (`transformers.py`):
1. `INVERSE_DISTANCE`: Weight = 1/(distance^2)
2. `SIMPLE_AVERAGE`: Equal weights
3. `NEAREST_ONLY`: Use only closest station
4. `DATA_COMPLETENESS`: Weight by % non-missing values

**Critical Filter**: Only merge NUMERIC columns:
- Filter columns before merging: `pd.api.types.is_numeric_dtype(df[col])`
- Prevents trying to merge string metadata columns
- Update all weighting strategies to use `numeric_columns` not `all_columns`

**Pressure Unit Conversion**:
- DWD provides pressure in various units (Pa or hPa)
- Check median value: if > 10000, assume Pa and divide by 100
- Must handle both Series and DataFrame column types (from joins)

### 5. Station Hashability

**Issue**: Station objects are used as dictionary keys in `transformers.py`

**Solution**: Implement `__hash__` and `__eq__` methods in Station dataclass:
```python
def __hash__(self):
    return hash(self.station_id)

def __eq__(self, other):
    if not isinstance(other, Station):
        return False
    return self.station_id == other.station_id
```

## Common Tasks

### Adding a New Parameter

1. **Update `config.py`**:
   - Add to `PARAM_DIRS` (DWD directory name)
   - Add to `OBS_PARAM_CODES` (file naming code)
   - Add to `MOSMIX_PARAM_CODES` if forecast support needed

2. **Update `transformers.py`**:
   - Add column mapping in `transform_for_pvlib()` or `transform_for_windpowerlib()`
   - Add unit conversion if needed

3. **Test**: Run `example.py` with new parameter

### Debugging Data Issues

1. **Check station availability**: 
   ```python
   stations = fetcher.find_stations(..., active_only=False)
   print([(s.name, s.end_date, s.is_active()) for s in stations])
   ```

2. **Verify file URLs**: Add print statements in `observations.py`:
   ```python
   print(f"Trying URL: {url}")
   ```

3. **Inspect raw data**: Before transformation:
   ```python
   df, meta = fetcher.get_observations(..., for_pvlib=False)
   print(df.dtypes)  # Check column types
   print(df.head())
   ```

4. **Check cache**: Files stored in `.dwd_cache/` with JSON metadata

### Handling Missing Data

**Stations without files**:
- Some stations in metadata don't have actual data files (404 errors)
- Module tries multiple stations automatically
- Warnings added to metadata['warnings']

**Data gaps**:
- `merge_multi_station_data()` uses outer join to preserve all timestamps
- Missing values handled per weighting strategy
- No automatic interpolation (by design - user's choice)

## Testing

### Unit Tests (`test_basic.py`)
- Mock-based tests for individual components
- Run: `python -m pytest test_basic.py -v`

### Integration Tests (`test_integration.py`)
- Full workflow tests with mock data
- Run: `python -m pytest test_integration.py -v`

### Manual Testing (`example.py`)
- Real DWD server access
- Validates: station finding, data fetching, merging, caching
- Current example location: Köln (better data availability than Berlin)

## Performance Considerations

1. **Caching**: Default 24h expiry reduces server load
2. **Parallel downloads**: Currently sequential (future improvement)
3. **Station selection**: Limit `n_stations` to 3-5 for performance
4. **Resolution**: 10-minute data = 6x more records than hourly

## Known Limitations

1. **No MOSMIX forecast parsing implemented yet** (returns 0 timesteps)
2. **Some stations have no data files** despite being in metadata
3. **Historical data merging** assumes continuous time coverage
4. **No height correction** for wind data
5. **Quality flags** preserved but not filtered automatically

## Dependencies

- **requests**: DWD server communication
- **pandas**: Data manipulation (DataFrame joins, reindexing)
- **numpy**: Numerical operations
- **lxml**: XML/KML parsing for MOSMIX
- **pytz**: Timezone conversions

## Git Workflow

- Small, focused commits per feature/fix
- Clear commit messages explaining "why"
- Keep `.dwd_cache/` in `.gitignore`
- Document breaking changes in README.md

## Troubleshooting Common Errors

### `TypeError: can't multiply sequence by non-int of type 'float'`
- **Cause**: Data column contains strings instead of numbers
- **Fix**: Ensure `pd.to_numeric()` called in `_parse_zip_data()`

### `ValueError: columns overlap but no suffix specified`
- **Cause**: Metadata columns (STATIONS_ID, MESS_DATUM) in multiple DataFrames
- **Fix**: Drop these columns in `_parse_zip_data()` after parsing

### `404 Client Error: Not Found`
- **Cause**: Station has metadata but no data files on server
- **Fix**: Try more stations (increase `n_stations`) or different location

### `ValueError: The truth value of a Series is ambiguous`
- **Cause**: Comparing Series directly in boolean context
- **Fix**: Use explicit checks: `if len(series) > 0:` or `if series.empty:`

### Empty DataFrame returned
- **Cause**: All stations inactive OR files not found OR date range outside data coverage
- **Fix**: Set `active_only=False`, check `metadata['warnings']`, verify date range

## Future Improvements

- Implement MOSMIX forecast parsing (KMZ/KML)
- Add async downloads for better performance
- Height correction for wind data
- More sophisticated gap filling options
- ICON model data integration
- Quality flag filtering options
- Data completeness visualization

## Resources

- DWD Open Data Portal: https://opendata.dwd.de/
- Station metadata: `CDC/observations_germany/climate/{resolution}/{parameter}/`
- MOSMIX: `weather/local_forecasts/mos/MOSMIX_S/all_stations/kml/`
- Parameter definitions: `weather/lib/MetElementDefinition.xml`
