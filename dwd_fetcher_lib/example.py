"""
Example usage of DWD Data Fetcher module.

This script demonstrates the main features of the module including:
- Finding weather stations
- Fetching observation data
- Fetching forecast data
- Combining historical and forecast data
- Formatting for pvlib and windpowerlib
"""

from dwd_fetcher import DWDFetcher, WeightingStrategy
from datetime import datetime, timedelta


def main():
    # Initialize the fetcher
    print("Initializing DWD Data Fetcher...")
    fetcher = DWDFetcher(
        cache_dir=".dwd_cache",
        cache_expiry_hours=24,
        timezone="Europe/Berlin",
        weighting_strategy=WeightingStrategy.INVERSE_DISTANCE
    )
    
    # Example location: Köln (Cologne)
    latitude = 50.94
    longitude = 6.96
    
    print(f"\nLocation: Köln ({latitude}, {longitude})")
    
    # Example 1: Find nearest weather stations
    print("\n" + "="*70)
    print("Example 1: Finding nearest weather stations")
    print("="*70)
    
    # Note: Check for stations without requiring them to be currently active
    # since this example might run with historical data
    stations = fetcher.find_stations(
        latitude=latitude,
        longitude=longitude,
        parameters=['solar', 'wind', 'temperature', 'pressure'],
        n=3,
        max_distance_km=100
    )
    
    for param, station_list in stations.items():
        print(f"\n{param.upper()} stations:")
        for station in station_list:
            print(f"  - {station['name']} (ID: {station['station_id']})")
            print(f"    Distance: {station['distance_km']:.1f} km")
            print(f"    Active: {station['is_active']}")
    
    # Example 2: Fetch recent observation data
    print("\n" + "="*70)
    print("Example 2: Fetching recent observation data")
    print("="*70)
    
    # Get data for the last 7 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    obs_data, obs_metadata = fetcher.get_observations(
        latitude=latitude,
        longitude=longitude,
        parameters=['temperature', 'wind'],  # Removed pressure to avoid column overlap
        start_date=start_date,
        end_date=end_date,
        resolution='10_minutes',
        max_distance_km=50,
        n_stations=2,
        allow_multi_station=True
    )
    
    print(f"\nRetrieved {len(obs_data)} observation records")
    print(f"Date range: {obs_data.index.min()} to {obs_data.index.max()}")
    print(f"\nColumns: {list(obs_data.columns)}")
    print(f"\nFirst few rows:")
    print(obs_data.head())
    
    # Show metadata
    print(f"\nStations used:")
    for param, stations in obs_metadata['stations_used'].items():
        print(f"  {param}: {len(stations)} station(s)")
        for s in stations:
            print(f"    - {s['name']} ({s['distance_km']:.1f} km)")
    
    if obs_metadata['warnings']:
        print(f"\nWarnings:")
        for warning in obs_metadata['warnings']:
            print(f"  - {warning}")
    
    # Example 3: Fetch forecast data
    print("\n" + "="*70)
    print("Example 3: Fetching MOSMIX forecast data")
    print("="*70)
    
    forecast_data, forecast_metadata = fetcher.get_forecast(
        latitude=latitude,
        longitude=longitude
    )
    
    print(f"\nRetrieved {len(forecast_data)} forecast timesteps")
    if not forecast_data.empty:
        print(f"Forecast range: {forecast_data.index.min()} to {forecast_data.index.max()}")
        print(f"\nColumns: {list(forecast_data.columns)}")
        print(f"\nFirst few rows:")
        print(forecast_data.head())
        print(f"\nStation ID: {forecast_metadata.get('station_id')}")
    
    # Example 4: Get data formatted for pvlib
    print("\n" + "="*70)
    print("Example 4: Data formatted for pvlib")
    print("="*70)
    
    pvlib_data, pvlib_meta = fetcher.get_observations(
        latitude=latitude,
        longitude=longitude,
        parameters=['solar', 'wind', 'temperature'],  # Removed pressure
        start_date=start_date,
        end_date=end_date,
        resolution='10_minutes',
        for_pvlib=True,
        allow_multi_station=True
    )
    
    print(f"\nPVlib-formatted data: {len(pvlib_data)} records")
    if not pvlib_data.empty:
        print(f"Columns: {list(pvlib_data.columns)}")
        print(f"\nSample data:")
        print(pvlib_data.head())
        print(f"\nData types:")
        print(pvlib_data.dtypes)
    
    # Example 5: Get data formatted for windpowerlib
    print("\n" + "="*70)
    print("Example 5: Data formatted for windpowerlib")
    print("="*70)
    
    wind_data, wind_meta = fetcher.get_observations(
        latitude=latitude,
        longitude=longitude,
        parameters=['wind', 'temperature'],  # Removed pressure
        start_date=start_date,
        end_date=end_date,
        resolution='10_minutes',
        for_windpowerlib=True
    )
    
    print(f"\nWindpowerlib-formatted data: {len(wind_data)} records")
    if not wind_data.empty:
        print(f"Columns: {list(wind_data.columns)}")
        print(f"\nSample data:")
        print(wind_data.head())
    
    # Example 6: Combined historical and forecast data
    print("\n" + "="*70)
    print("Example 6: Combined historical observations + forecast")
    print("="*70)
    
    combined_data, combined_meta = fetcher.get_combined_data(
        latitude=latitude,
        longitude=longitude,
        parameters=['temperature', 'wind'],  # Removed pressure
        historical_start=start_date,
        include_forecast=True,
        for_pvlib=True
    )
    
    print(f"\nCombined dataset: {len(combined_data)} records")
    if not combined_data.empty:
        print(f"Date range: {combined_data.index.min()} to {combined_data.index.max()}")
        print(f"Transition point (obs->forecast): {combined_meta.get('transition_point')}")
        print(f"\nSample of combined data:")
        print(combined_data.head(10))
    
    # Example 7: Cache management
    print("\n" + "="*70)
    print("Example 7: Cache information")
    print("="*70)
    
    cache_info = fetcher.get_cache_info()
    print(f"\nCache directory: {cache_info['cache_dir']}")
    print(f"Total cached items: {cache_info['total_items']}")
    print(f"Valid items: {cache_info['valid_items']}")
    print(f"Expired items: {cache_info['expired_items']}")
    print(f"Total size: {cache_info['total_size_bytes'] / 1024 / 1024:.2f} MB")
    print(f"Default expiry: {cache_info['default_expiry_hours']} hours")
    
    # Example 8: Quality-based station ranking
    print("\n" + "="*70)
    print("Example 8: Quality-based station ranking comparison")
    print("="*70)
    
    print("\nDemonstrating station selection with and without quality checks...")
    print("This addresses the issue where closest station (02968) may lack data")
    print("while a slightly farther station (02667) has better availability.\n")
    
    # Test with distance-only (default behavior)
    print("A) Distance-only ranking (default):")
    fetcher_distance = DWDFetcher(
        cache_dir=".dwd_cache",
        ranking_strategy="distance_only"
    )
    
    data_dist, meta_dist = fetcher_distance.get_observations(
        latitude=latitude,
        longitude=longitude,
        parameters=['temperature'],
        start_date=start_date,
        end_date=end_date,
        resolution='10_minutes',
        n_stations=3,
        allow_multi_station=False  # Use only one station for clarity
    )
    
    if 'temperature' in meta_dist['stations_used']:
        for i, station in enumerate(meta_dist['stations_used']['temperature'], 1):
            print(f"  {i}. Station {station['station_id']}: {station['name']}")
            print(f"     Distance: {station['distance_km']:.1f} km")
            print(f"     Quality score: {station.get('quality_score', 'not checked')}")
    
    print(f"\n  Retrieved {len(data_dist)} records")
    if len(data_dist) > 0:
        print(f"  Data completeness: {(1 - data_dist.isna().sum().sum() / (len(data_dist) * len(data_dist.columns))) * 100:.1f}%")
    
    # Test with quality-weighted ranking
    print("\n\nB) Quality-weighted ranking:")
    fetcher_quality = DWDFetcher(
        cache_dir=".dwd_cache",
        ranking_strategy="quality_weighted",
        quality_check_limit=5  # Check 5 closest stations
    )
    
    data_qual, meta_qual = fetcher_quality.get_observations(
        latitude=latitude,
        longitude=longitude,
        parameters=['temperature'],
        start_date=start_date,
        end_date=end_date,
        resolution='10_minutes',
        n_stations=3,
        allow_multi_station=False
    )
    
    if 'temperature' in meta_qual['stations_used']:
        for i, station in enumerate(meta_qual['stations_used']['temperature'], 1):
            print(f"  {i}. Station {station['station_id']}: {station['name']}")
            print(f"     Distance: {station['distance_km']:.1f} km")
            print(f"     Quality score: {station.get('quality_score', 'N/A')}")
            print(f"     Combined score: {station.get('combined_score', 'N/A')}")
    
    print(f"\n  Retrieved {len(data_qual)} records")
    if len(data_qual) > 0:
        print(f"  Data completeness: {(1 - data_qual.isna().sum().sum() / (len(data_qual) * len(data_qual.columns))) * 100:.1f}%")
    
    # Test with quality-first ranking
    print("\n\nC) Quality-first ranking:")
    fetcher_quality_first = DWDFetcher(
        cache_dir=".dwd_cache",
        ranking_strategy="quality_first",
        quality_check_limit=5
    )
    
    data_qf, meta_qf = fetcher_quality_first.get_observations(
        latitude=latitude,
        longitude=longitude,
        parameters=['temperature'],
        start_date=start_date,
        end_date=end_date,
        resolution='10_minutes',
        n_stations=3,
        allow_multi_station=False
    )
    
    if 'temperature' in meta_qf['stations_used']:
        for i, station in enumerate(meta_qf['stations_used']['temperature'], 1):
            print(f"  {i}. Station {station['station_id']}: {station['name']}")
            print(f"     Distance: {station['distance_km']:.1f} km")
            print(f"     Quality score: {station.get('quality_score', 'N/A')}")
    
    print(f"\n  Retrieved {len(data_qf)} records")
    if len(data_qf) > 0:
        print(f"  Data completeness: {(1 - data_qf.isna().sum().sum() / (len(data_qf) * len(data_qf.columns))) * 100:.1f}%")
    
    print("\n\nConclusion:")
    print("  - 'distance_only': Fastest, but may select stations without data")
    print("  - 'quality_weighted': Best balance of proximity and data availability")
    print("  - 'quality_first': Prioritizes data quality over distance")
    print("  Quality checks add ~1 second but significantly improve data retrieval success")
    
    print("\n" + "="*70)
    print("Examples completed successfully!")
    print("="*70)


if __name__ == "__main__":
    main()
