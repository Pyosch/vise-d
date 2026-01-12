"""
Test historical data fetching with the new logic.
"""

from dwd_fetcher import DWDFetcher
from datetime import datetime

def main():
    fetcher = DWDFetcher(cache_dir=".dwd_cache")
    
    # Test 1: Recent data only (should fetch recent file only)
    print("="*70)
    print("Test 1: Recent data (2025-12-01 to 2026-01-07)")
    print("="*70)
    df, meta = fetcher.get_observations(
        latitude=50.8645,
        longitude=7.1575,
        parameters=['temperature'],
        start_date=datetime(2025, 12, 1),
        end_date=datetime(2026, 1, 7),
        resolution='10_minutes',
        n_stations=1
    )
    print(f"Shape: {df.shape}")
    print(f"Sources: {meta['data_sources']['temperature'][0]['sources']}")
    print(f"Date range: {df.index.min()} to {df.index.max()}\n")
    
    # Test 2: Historical data (should fetch both recent and historical)
    print("="*70)
    print("Test 2: Historical data (2020-01-01 to 2020-01-07)")
    print("="*70)
    df, meta = fetcher.get_observations(
        latitude=50.8645,
        longitude=7.1575,
        parameters=['temperature'],
        start_date=datetime(2020, 1, 1),
        end_date=datetime(2020, 1, 7),
        resolution='10_minutes',
        n_stations=1
    )
    print(f"Shape: {df.shape}")
    if 'temperature' in meta.get('data_sources', {}):
        print(f"Sources: {meta['data_sources']['temperature'][0]['sources']}")
        if not df.empty:
            print(f"Date range: {df.index.min()} to {df.index.max()}")
    else:
        print("No temperature data found")
        print(f"Warnings: {meta.get('warnings', [])}")
    print()
    
    # Test 3: Spanning both (should fetch both recent and historical)
    print("="*70)
    print("Test 3: Spanning data (2020-01-01 to 2026-01-07)")
    print("="*70)
    df, meta = fetcher.get_observations(
        latitude=50.8645,
        longitude=7.1575,
        parameters=['temperature'],
        start_date=datetime(2020, 1, 1),
        end_date=datetime(2026, 1, 7),
        resolution='10_minutes',
        n_stations=1
    )
    print(f"Shape: {df.shape}")
    if 'temperature' in meta.get('data_sources', {}):
        print(f"Sources: {meta['data_sources']['temperature'][0]['sources']}")
        if not df.empty:
            print(f"Date range: {df.index.min()} to {df.index.max()}")
    else:
        print("No temperature data found")
        print(f"Warnings: {meta.get('warnings', [])}")
    print()

if __name__ == "__main__":
    main()
