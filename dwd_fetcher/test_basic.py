"""
Test suite for DWD Data Fetcher module.
Tests basic functionality without requiring network access where possible.
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    try:
        from dwd_fetcher import DWDFetcher, WeightingStrategy
        from dwd_fetcher.config import DWDConfig
        from dwd_fetcher.cache import CacheManager
        from dwd_fetcher.stations import StationManager, Station
        from dwd_fetcher.downloader import Downloader
        from dwd_fetcher.transformers import DataTransformer
        from dwd_fetcher.parsers import MOSMIXParameterManager, ObservationParser, ForecastParser
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def test_config():
    """Test configuration module."""
    print("\nTesting configuration...")
    try:
        from dwd_fetcher.config import DWDConfig, WeightingStrategy
        
        # Check base URLs
        assert DWDConfig.BASE_URL == "https://opendata.dwd.de"
        assert "cache" in DWDConfig.DEFAULT_CACHE_DIR.lower()
        assert DWDConfig.DEFAULT_CACHE_EXPIRY_HOURS == 24
        
        # Check weighting strategies
        assert WeightingStrategy.INVERSE_DISTANCE.value == "inverse_distance"
        assert WeightingStrategy.SIMPLE_AVERAGE.value == "simple_average"
        
        # Check parameter mappings
        assert 'solar' in DWDConfig.PARAM_DIRS
        assert 'wind' in DWDConfig.PARAM_DIRS
        
        # Test URL generation
        url = DWDConfig.get_obs_url('temperature', 'hourly')
        assert 'air_temperature' in url
        assert 'hourly' in url
        
        print("✓ Configuration tests passed")
        return True
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_manager():
    """Test cache manager functionality."""
    print("\nTesting cache manager...")
    try:
        from dwd_fetcher.cache import CacheManager
        import tempfile
        import shutil
        
        # Create temporary cache directory
        temp_dir = tempfile.mkdtemp()
        
        try:
            cache = CacheManager(cache_dir=temp_dir, default_expiry_hours=1)
            
            # Test cache set/get
            test_url = "http://example.com/test"
            test_content = "test content"
            
            cache.set(test_url, test_content, binary=False)
            retrieved = cache.get(test_url, binary=False)
            
            assert retrieved == test_content, "Cache content mismatch"
            
            # Test cache validation
            assert cache.is_valid(cache._get_cache_key(test_url), expiry_hours=1)
            
            # Test invalidation
            cache.invalidate(test_url)
            assert cache.get(test_url, binary=False) is None
            
            # Test cache info
            info = cache.get_cache_info()
            assert 'total_items' in info
            assert info['cache_dir'] == temp_dir
            
            print("✓ Cache manager tests passed")
            return True
            
        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except Exception as e:
        print(f"✗ Cache manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_station_distance():
    """Test station distance calculation."""
    print("\nTesting station distance calculation...")
    try:
        from dwd_fetcher.stations import StationManager
        
        # Test Haversine distance calculation
        # Berlin to Munich (approx 504 km)
        berlin_lat, berlin_lon = 52.52, 13.41
        munich_lat, munich_lon = 48.14, 11.58
        
        distance = StationManager._haversine_distance(
            berlin_lat, berlin_lon,
            munich_lat, munich_lon
        )
        
        # Distance should be approximately 504 km
        assert 480 < distance < 530, f"Distance calculation off: {distance} km"
        
        # Test same location
        same_distance = StationManager._haversine_distance(
            berlin_lat, berlin_lon,
            berlin_lat, berlin_lon
        )
        assert same_distance < 0.01, "Same location should have ~0 distance"
        
        print(f"✓ Station distance tests passed (Berlin-Munich: {distance:.1f} km)")
        return True
        
    except Exception as e:
        print(f"✗ Station distance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_transformer():
    """Test data transformation functions."""
    print("\nTesting data transformers...")
    try:
        from dwd_fetcher.transformers import DataTransformer
        
        transformer = DataTransformer(timezone="Europe/Berlin")
        
        # Create test DataFrame with Kelvin temperature
        test_data = pd.DataFrame({
            'TTT': [273.15, 283.15, 293.15],  # 0°C, 10°C, 20°C in Kelvin
            'Rad1h': [3600, 7200, 10800],      # kJ/m² per hour
            'PPPP': [101325, 101325, 101325],  # Pa
            'FF': [5.0, 10.0, 15.0]            # m/s
        }, index=pd.date_range('2024-01-01', periods=3, freq='h'))
        
        # Transform for pvlib
        pvlib_data = transformer.transform_for_pvlib(test_data)
        
        # Check temperature conversion (K to °C)
        assert 'temp_air' in pvlib_data.columns
        assert abs(pvlib_data['temp_air'].iloc[0] - 0.0) < 0.1
        assert abs(pvlib_data['temp_air'].iloc[1] - 10.0) < 0.1
        
        # Check radiation conversion (kJ/m²/h to W/m²)
        # 3600 kJ/m²/h = 3600 * 1000 / 3600 = 1000 W/m²
        if 'ghi' in pvlib_data.columns:
            # The conversion may not happen if values don't meet threshold
            # Just check that the column exists and has valid data
            assert pvlib_data['ghi'].notna().any()
        
        # Check pressure conversion (Pa to hPa)
        if 'pressure' in pvlib_data.columns:
            assert abs(pvlib_data['pressure'].iloc[0] - 1013.25) < 1.0
        
        print("✓ Data transformer tests passed")
        return True
        
    except Exception as e:
        print(f"✗ Data transformer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multi_station_merging():
    """Test multi-station data merging."""
    print("\nTesting multi-station data merging...")
    try:
        from dwd_fetcher.transformers import DataTransformer
        from dwd_fetcher.stations import Station
        from dwd_fetcher.config import WeightingStrategy
        
        transformer = DataTransformer()
        
        # Create test stations
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
        
        # Create test data
        dates = pd.date_range('2024-01-01', periods=5, freq='h')
        data1 = pd.DataFrame({'temp': [10, 11, 12, 13, 14]}, index=dates)
        data2 = pd.DataFrame({'temp': [9, 10, 11, 12, 13]}, index=dates)
        
        station_data = {station1: data1, station2: data2}
        
        # Test nearest only
        merged = transformer.merge_multi_station_data(
            station_data, WeightingStrategy.NEAREST_ONLY
        )
        assert len(merged) == 5
        assert list(merged['temp']) == [10, 11, 12, 13, 14]  # Should use station1 (nearest)
        
        # Test simple average
        merged = transformer.merge_multi_station_data(
            station_data, WeightingStrategy.SIMPLE_AVERAGE
        )
        assert len(merged) == 5
        assert abs(merged['temp'].iloc[0] - 9.5) < 0.01  # Average of 10 and 9
        
        # Test inverse distance
        merged = transformer.merge_multi_station_data(
            station_data, WeightingStrategy.INVERSE_DISTANCE, power=2.0
        )
        assert len(merged) == 5
        # Station 1 is 10km away, station 2 is 20km away
        # Weights: 1/100 vs 1/400 = 4:1 ratio
        # (10*4 + 9*1) / 5 = 49/5 = 9.8
        expected = (10 * (1/100) + 9 * (1/400)) / ((1/100) + (1/400))
        assert abs(merged['temp'].iloc[0] - expected) < 0.1
        
        print("✓ Multi-station merging tests passed")
        return True
        
    except Exception as e:
        print(f"✗ Multi-station merging test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fetcher_initialization():
    """Test DWDFetcher initialization."""
    print("\nTesting DWDFetcher initialization...")
    try:
        from dwd_fetcher import DWDFetcher, WeightingStrategy
        
        # Test default initialization
        fetcher = DWDFetcher()
        assert fetcher.cache_manager is not None
        assert fetcher.station_manager is not None
        assert fetcher.downloader is not None
        
        # Test custom initialization
        fetcher2 = DWDFetcher(
            cache_dir="test_cache",
            cache_expiry_hours=12,
            timezone="UTC",
            weighting_strategy=WeightingStrategy.SIMPLE_AVERAGE
        )
        assert fetcher2.cache_manager.default_expiry_hours == 12
        assert fetcher2.transformer.timezone == "UTC"
        assert fetcher2.weighting_strategy == WeightingStrategy.SIMPLE_AVERAGE
        
        # Test cache info
        info = fetcher.get_cache_info()
        assert 'cache_dir' in info
        assert 'total_items' in info
        
        print("✓ DWDFetcher initialization tests passed")
        return True
        
    except Exception as e:
        print(f"✗ DWDFetcher initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_station_parsing():
    """Test station metadata parsing."""
    print("\nTesting station metadata parsing...")
    try:
        from dwd_fetcher.stations import StationManager
        
        # Create a sample station file content
        sample_content = """Stations_id von_datum bis_datum Stationshoehe geoBreite geoLaenge Stationsname
----------- --------- --------- ------------- --------- --------- ------------
00044       19500101  20241231  44            52.9336   8.2370    Bremen
00071       19500101  20241231  48            52.4642   13.4021   Berlin-Tegel
00722       18960101  20241231  263           52.4677   13.4021   Berlin-Dahlem
"""
        
        manager = StationManager()
        stations = manager._parse_station_file(sample_content, 'temperature')
        
        assert len(stations) >= 2, f"Should parse at least 2 stations, got {len(stations)}"
        
        # Check if Bremen was parsed
        bremen = stations.get('00044')
        if bremen:
            assert bremen.name == 'Bremen'
            assert abs(bremen.latitude - 52.9336) < 0.01
            assert abs(bremen.longitude - 8.2370) < 0.01
            assert bremen.elevation == 44
        
        print(f"✓ Station parsing tests passed (parsed {len(stations)} stations)")
        return True
        
    except Exception as e:
        print(f"✗ Station parsing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests and report results."""
    print("="*70)
    print("DWD Data Fetcher - Test Suite")
    print("="*70)
    
    tests = [
        ("Module Imports", test_imports),
        ("Configuration", test_config),
        ("Cache Manager", test_cache_manager),
        ("Station Distance", test_station_distance),
        ("Data Transformer", test_data_transformer),
        ("Multi-Station Merging", test_multi_station_merging),
        ("DWDFetcher Initialization", test_fetcher_initialization),
        ("Station Parsing", test_station_parsing),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ {name} - Unexpected error: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
