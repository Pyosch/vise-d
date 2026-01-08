# MaStR Database Configuration

## Issue: Table Names Not Found

The VISE-D application currently expects specific table names in the MaStR database:
- `solar_extended`
- `wind_extended`
- `storage_extended`

However, the open-MaStR database may use different table naming conventions depending on the version and download method.

## Quick Fix: Check Your Table Names

1. **Locate your open-MaStR database file**:
   - Default location: `C:/Users/<username>/.open-MaStR/data/sqlite/open-mastr.db`
   
2. **Check the actual table names** using a SQLite browser or command:
   ```bash
   sqlite3 "C:/Users/<username>/.open-MaStR/data/sqlite/open-mastr.db" ".tables"
   ```

3. **Common open-MaStR table names** include:
   - `basic_units` (base table for all units)
   - `wind_extended` or `extended_wind`
   - `solar_extended` or `extended_solar`
   - `storage_extended` or `extended_storage`
   - `biomass_extended`
   - etc.

## Solution 1: Update Database Path (Immediate)

In `dashboard.py` (line ~62), uncomment and update the database path:

```python
# Alternative: Uncomment and update the line below with your actual database path
mastr_db_path = 'C:/Users/<your-username>/.open-MaStR/data/sqlite/open-mastr.db'
```

## Solution 2: Fix Table Names (if different)

If your database uses different table names (e.g., `extended_solar` instead of `solar_extended`), you need to update the queries in:
- `src/mastr/preprocessing.py`

Find and replace:
- `solar_extended` → your actual solar table name
- `wind_extended` → your actual wind table name  
- `storage_extended` → your actual storage table name

**Search for**: `FROM solar_extended`, `FROM wind_extended`, `FROM storage_extended`

## Solution 3: Verify Database Schema (Recommended for Development)

Run this Python script to check your database schema:

```python
import sqlite3

db_path = 'C:/Users/<username>/.open-MaStR/data/sqlite/open-mastr.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("Available tables:")
for table in tables:
    print(f"  - {table[0]}")
    
# Check solar table structure (example)
table_name = 'solar_extended'  # Try your table name here
try:
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    print(f"\nColumns in {table_name}:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
except Exception as e:
    print(f"Table {table_name} not found: {e}")

conn.close()
```

## Future Enhancement

We will add a configuration file (`src/config/mastr_tables.py`) to make table names configurable:

```python
# Future: src/config/mastr_tables.py
MASTR_TABLES = {
    "solar": "solar_extended",
    "wind": "wind_extended", 
    "storage": "storage_extended",
    "grid_connections": "grid_connections"
}
```

This will allow easy switching between different MaStR database schemas without code changes.

## Error Message Reference

If you see:
```
Failed to load solar locations: Failed to fetch unique locations: 
Execution failed on sql 'SELECT DISTINCT Ort FROM solar_extended WHERE Ort IS NOT NULL': 
no such table: solar_extended
```

This means:
1. The database path is wrong, OR
2. The table name is different in your database

Follow Solution 1 and 2 above to fix it.
