"""
Quick script to check MaStR database table structure.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

import sqlite3
import sys
from pathlib import Path

def check_database_schema(db_path):
    """
    Check the schema of an open-MaStR SQLite database.
    
    Args:
        db_path: Path to the SQLite database file
    """
    print(f"\n{'='*60}")
    print(f"Checking database: {db_path}")
    print(f"{'='*60}\n")
    
    if not Path(db_path).exists():
        print(f"ERROR: Database file not found at {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = cursor.fetchall()
        
        print(f"Found {len(tables)} tables:\n")
        
        # Look for specific tables we need
        table_names = [table[0] for table in tables]
        needed_tables = ['solar_extended', 'wind_extended', 'storage_extended']
        
        for needed in needed_tables:
            if needed in table_names:
                print(f"  [OK] {needed}")
            else:
                print(f"  [MISSING] {needed}")
        
        print("\nAll available tables:")
        for table in table_names:
            print(f"  - {table}")
        
        # Check for extended tables specifically
        extended_tables = [t for t in table_names if 'extended' in t.lower()]
        if extended_tables:
            print(f"\nTables with 'extended' in name:")
            for table in extended_tables:
                print(f"  - {table}")
                
                # Show first few columns
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                print(f"    Columns ({len(columns)} total): ", end="")
                print(", ".join([col[1] for col in columns[:5]]) + ", ...")
        
        # Check if 'Ort' column exists in relevant tables
        print(f"\nChecking for 'Ort' (location) column:")
        for table in extended_tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in cursor.fetchall()]
            if 'Ort' in columns:
                print(f"  [OK] {table} has 'Ort' column")
                # Count locations
                cursor.execute(f"SELECT COUNT(DISTINCT Ort) FROM {table} WHERE Ort IS NOT NULL")
                count = cursor.fetchone()[0]
                print(f"       -> {count} unique locations")
            else:
                print(f"  [NO] {table} missing 'Ort' column")
        
        conn.close()
        
        print(f"\n{'='*60}")
        print("Database check complete!")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Default to data/open-mastr.db
    default_path = Path(__file__).parent / "data" / "open-mastr.db"
    
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = str(default_path)
    
    check_database_schema(db_path)
