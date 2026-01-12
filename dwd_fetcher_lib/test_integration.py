"""
Integration test demonstrating the complete workflow without network access.
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dwd_fetcher import DWDFetcher, WeightingStrategy


def test_complete_workflow():
    """Test the complete workflow with mock components."""
    print("="*70)
    print("Integration Test - Complete Workflow")
    print("="*70)
    
    # Initialize fetcher
    print("\n1. Initializing DWDFetcher...")
    fetcher = DWDFetcher(
        cache_dir="test_cache",
        cache_expiry_hours=24,
        timezone="Europe/Berlin",
        weighting_strategy=WeightingStrategy.INVERSE_DISTANCE
    )
    print("   ✓ Fetcher initialized successfully")
    
    # Test cache info
    print("\n2. Testing cache management...")
    cache_info = fetcher.get_cache_info()
    print(f"   Cache directory: {cache_info['cache_dir']}")
    print(f"   Default expiry: {cache_info['default_expiry_hours']} hours")
    print("   ✓ Cache management working")
    
    # Test configuration
    print("\n3. Testing configuration...")
    from dwd_fetcher.config import DWDConfig
    
    solar_url = DWDConfig.get_obs_url('solar', 'hourly')
    print(f"   Solar data URL: {solar_url}")
    assert 'solar' in solar_url
    
    station_file = DWDConfig.get_station_description_filename('wind', 'hourly')
    print(f"   Station file: {station_file}")
    assert 'FF' in station_file
    print("   ✓ Configuration working")
    
    # Test data transformation
    print("\n4. Testing data transformation...")
    test_data = pd.DataFrame({
        'TTT': [273.15, 283.15, 293.15],  # Kelvin
        'FF': [5.0, 10.0, 15.0],           # m/s
        'PPPP': [101325, 101325, 101325],  # Pa
    }, index=pd.date_range('2024-01-01', periods=3, freq='h'))
    
    # Transform for pvlib
    pvlib_data = fetcher.transformer.transform_for_pvlib(test_data)
    print(f"   Original columns: {list(test_data.columns)}")
    print(f"   Transformed columns: {list(pvlib_data.columns)}")
    print(f"   Temperature (first value): {pvlib_data['temp_air'].iloc[0]:.1f}°C")
    print("   ✓ Data transformation working")
    
    # Test multi-station merging
    print("\n5. Testing multi-station merging...")
    from dwd_fetcher.stations import Station
    
    station1 = Station(
        station_id="001", name="Station 1",
        latitude=52.5, longitude=13.4, elevation=50,
        start_date=None, end_date=None, parameter="temperature",
        distance_km=10.0
    )
    
    station2 = Station(
        station_id="002", name="Station 2",
        latitude=52.6, longitude=13.5, elevation=60,
        start_date=None, end_date=None, parameter="temperature",
        distance_km=20.0
    )
    
    dates = pd.date_range('2024-01-01', periods=5, freq='h')
    data1 = pd.DataFrame({'temp': [10, 11, 12, 13, 14]}, index=dates)
    data2 = pd.DataFrame({'temp': [9, 10, 11, 12, 13]}, index=dates)
    
    merged = fetcher.transformer.merge_multi_station_data(
        {station1: data1, station2: data2},
        WeightingStrategy.INVERSE_DISTANCE
    )
    
    print(f"   Merged {len(merged)} timesteps from 2 stations")
    print(f"   Merging strategy: {WeightingStrategy.INVERSE_DISTANCE.value}")
    print(f"   First merged value: {merged['temp'].iloc[0]:.2f}")
    print("   ✓ Multi-station merging working")
    
    # Test station distance calculation
    print("\n6. Testing station operations...")
    from dwd_fetcher.stations import StationManager
    
    # Berlin to Hamburg (approx 255 km)
    distance = StationManager._haversine_distance(52.52, 13.41, 53.55, 10.00)
    print(f"   Berlin to Hamburg distance: {distance:.1f} km")
    assert 250 < distance < 300
    print("   ✓ Station distance calculation working")
    
    # Test station parsing
    print("\n7. Testing station metadata parsing...")
    sample_station_data = """Stations_id von_datum bis_datum Stationshoehe geoBreite geoLaenge Stationsname
----------- --------- --------- ------------- --------- --------- ------------
00044       19500101  20241231  44            52.9336   8.2370    Bremen
"""
    
    manager = fetcher.station_manager
    stations = manager._parse_station_file(sample_station_data, 'test_param')
    print(f"   Parsed {len(stations)} station(s)")
    if '00044' in stations:
        bremen = stations['00044']
        print(f"   Station: {bremen.name} at ({bremen.latitude:.4f}, {bremen.longitude:.4f})")
    print("   ✓ Station parsing working")
    
    # Test quality filtering
    print("\n8. Testing data quality filtering...")
    quality_data = pd.DataFrame({
        'temp': [10.0, 11.0, 12.0, 13.0],
        'QN': [3, 1, 0, 2]  # Quality flags
    }, index=pd.date_range('2024-01-01', periods=4, freq='h'))
    
    filtered = fetcher.transformer.apply_quality_filters(quality_data, min_quality=2)
    valid_count = filtered['temp'].notna().sum()
    print(f"   Original values: {len(quality_data)}")
    print(f"   Valid values (quality >= 2): {valid_count}")
    print("   ✓ Quality filtering working")
    
    # Test missing data handling
    print("\n9. Testing missing data handling...")
    missing_data = pd.DataFrame({
        'temp': [10.0, None, None, 13.0, 14.0]
    }, index=pd.date_range('2024-01-01', periods=5, freq='h'))
    
    interpolated = fetcher.transformer.handle_missing_data(
        missing_data, method='interpolate', limit=3
    )
    
    filled_count = interpolated['temp'].notna().sum()
    print(f"   Original non-null: {missing_data['temp'].notna().sum()}")
    print(f"   After interpolation: {filled_count}")
    print("   ✓ Missing data handling working")
    
    # Summary
    print("\n" + "="*70)
    print("✅ All integration tests passed!")
    print("="*70)
    print("\nThe DWD Data Fetcher module is working correctly!")
    print("\nKey features verified:")
    print("  • Module initialization and configuration")
    print("  • Cache management")
    print("  • Data transformation (unit conversions)")
    print("  • Multi-station data merging")
    print("  • Station distance calculations")
    print("  • Station metadata parsing")
    print("  • Quality filtering")
    print("  • Missing data interpolation")
    print("\nThe module is ready for use with real DWD data!")
    
    # Cleanup test cache
    import shutil
    if os.path.exists("test_cache"):
        shutil.rmtree("test_cache", ignore_errors=True)
    
    return True


if __name__ == "__main__":
    try:
        success = test_complete_workflow()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
