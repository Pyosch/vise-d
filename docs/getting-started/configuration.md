# Configuration Guide

**Last Updated:** January 9, 2026

This guide covers environment setup, database configuration, and API access for VISE-D.

## Table of Contents
- [MaStR Database Setup](#mastr-database-setup)
- [Weather Data Configuration](#weather-data-configuration)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)

---

## MaStR Database Setup

### What is MaStR?

The **Marktstammdatenregister (MaStR)** is Germany's official registry of all power generation and storage units. VISE-D uses this data for real-world analysis.

### Database Location

VISE-D expects the MaStR database at:
```
data/open-mastr.db
```

**Default open-MaStR location:**
```
C:/Users/<username>/.open-MaStR/data/sqlite/open-mastr.db
```

### Configuration

In `dashboard.py` (around line 45), the database path is configured:

```python
# Import configuration
from src.config import MASTR_DB_PATH

# MaStR database path from configuration
mastr_db_path = str(MASTR_DB_PATH)
```

To use a custom path, update `src/config/paths.py`:

```python
# Option 1: Use default location
MASTR_DB_PATH = DATA_DIR / "open-mastr.db"

# Option 2: Use open-MaStR default location
MASTR_DB_PATH = Path.home() / ".open-MaStR" / "data" / "sqlite" / "open-mastr.db"

# Option 3: Use custom absolute path
MASTR_DB_PATH = Path("C:/custom/path/to/open-mastr.db")
```

### Verify Database Tables

Check that your database contains the required tables:

```bash
sqlite3 "path/to/open-mastr.db" ".tables"
```

**Required tables:**
- `solar_extended` (or `extended_solar`)
- `wind_extended` (or `extended_wind`)
- `storage_extended` (or `extended_storage`)

### Table Name Mismatches

If your database uses different table names (e.g., `extended_solar` instead of `solar_extended`), update the queries in `src/mastr/preprocessing.py`:

**Find and replace:**
- `solar_extended` → your actual solar table name
- `wind_extended` → your actual wind table name
- `storage_extended` → your actual storage table name

Search for: `FROM solar_extended`, `FROM wind_extended`, `FROM storage_extended`

---

## Weather Data Configuration

### DWD (German Weather Service) Data

VISE-D uses DWD weather data for simulations. The data is fetched via API calls.

**Supported data types:**
- Solar radiation (for PV simulation)
- Wind speed and direction (for wind turbine simulation)
- Temperature and pressure (for heat pump simulation)

**Configuration:**
No additional setup required - API calls are handled automatically by the application.

### ERA5 Wind Data

For wind farm planning, VISE-D uses ERA5 reanalysis data.

**Expected location:**
```
data/era5_germany_2024_wind/
```

**Required files:**
- Wind speed data (u and v components)
- Wind direction data
- Pressure data

**Download:** ERA5 data must be downloaded separately from the Copernicus Climate Data Store.

---

## Environment Variables

### Optional Environment Variables

Create a `.env` file in the project root for optional configuration:

```bash
# MaStR Database
MASTR_DB_PATH=/path/to/open-mastr.db

# Cache settings (optional - defaults used if not set)
CACHE_TTL_DATA=3600
CACHE_TTL_DATABASE=1800
CACHE_TTL_VISUALIZATION=600
CACHE_TTL_ENVIRONMENT=3600

# Streamlit configuration (optional)
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_HEADLESS=true
```

### Loading Environment Variables

If using `.env`, install `python-dotenv`:

```bash
pip install python-dotenv
```

Add to the top of `dashboard.py`:

```python
from dotenv import load_dotenv
load_dotenv()
```

---

## Troubleshooting

### Issue: "Table not found" Error

**Problem:** MaStR database tables don't match expected names.

**Solution:**
1. Check actual table names: `sqlite3 database.db ".tables"`
2. Update table names in `src/mastr/preprocessing.py`
3. Or use a compatible open-MaStR version

### Issue: Database File Not Found

**Problem:** VISE-D can't locate the MaStR database.

**Solution:**
1. Verify file exists at configured path
2. Update `MASTR_DB_PATH` in `src/config/paths.py`
3. Ensure file permissions allow read access

### Issue: Weather Data API Errors

**Problem:** DWD API calls failing.

**Solution:**
1. Check internet connection
2. Verify DWD API is accessible
3. Check if coordinates are within Germany
4. Try again later if API is temporarily down

### Issue: ERA5 Data Missing

**Problem:** Wind planning fails due to missing ERA5 data.

**Solution:**
1. Download ERA5 data from Copernicus Climate Data Store
2. Place files in `data/era5_germany_2024_wind/`
3. Verify file naming matches expected pattern

### Issue: Slow Dashboard Performance

**Problem:** Pages loading slowly.

**Solution:**
1. Clear cache using sidebar button
2. Check database query performance
3. Verify sufficient RAM available
4. Consider using smaller dataset for testing

---

## See Also

- [Installation Guide](installation.md)
- [Quickstart Tutorial](quickstart.md)
- [Developer Guide: Caching](../developer-guide/caching.md)
- [MaStR Database Documentation](https://www.marktstammdatenregister.de/)
