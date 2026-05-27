#!/usr/bin/env python3
"""Pre-build MaStR location CSV caches from the SQLite database.

Run this once after downloading a fresh MaStR database to avoid the slow
DISTINCT query on the 7.5 GB SQLite file during dashboard startup.

Usage:
    python scripts/update_location_cache.py [--db PATH]

CSVs are written to data/mastr/ (solar_locations.csv, wind_locations.csv,
storage_locations.csv).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
from src.mastr.preprocessing import rebuild_location_caches
from src.config.paths import MASTR_DB_PATH


def main():
    parser = argparse.ArgumentParser(description="Rebuild MaStR location CSV caches")
    parser.add_argument(
        "--db",
        default=str(MASTR_DB_PATH),
        help=f"Path to MaStR SQLite database (default: {MASTR_DB_PATH})",
    )
    args = parser.parse_args()

    print(f"Rebuilding location caches from: {args.db}")
    rebuild_location_caches(args.db)
    print("Done. CSVs written to data/mastr/.")


if __name__ == "__main__":
    main()
