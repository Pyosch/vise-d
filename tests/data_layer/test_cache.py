"""Unit tests for data_layer caching functions.

This test module uses lightweight fixtures and mocking strategies to test
caching functionality without requiring actual database or file access.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from src.data_layer.cache import (
    CACHE_CONFIG,
    load_example_data,
    get_cached_unique_locations,
    get_cached_mastr_data,
    create_cached_violin_plot,
    create_cached_scatter_map,
    update_violin_plot,
)


class TestCacheConfig:
    """Test cache configuration constants."""

    def test_cache_config_exists(self):
        """Verify CACHE_CONFIG dict exists with all required keys."""
        assert 'DATA_LOAD_TTL' in CACHE_CONFIG
        assert 'DATABASE_TTL' in CACHE_CONFIG
        assert 'VISUALIZATION_TTL' in CACHE_CONFIG
        assert 'ENVIRONMENT_TTL' in CACHE_CONFIG

    def test_cache_config_values_are_positive(self):
        """Verify all TTL values are positive integers."""
        for key, value in CACHE_CONFIG.items():
            assert isinstance(value, int), f"{key} should be an integer"
            assert value > 0, f"{key} should be positive"

    def test_cache_config_ttl_hierarchy(self):
        """Verify TTL values follow expected hierarchy (data > db > viz)."""
        assert CACHE_CONFIG['DATA_LOAD_TTL'] >= CACHE_CONFIG['DATABASE_TTL']
        assert CACHE_CONFIG['DATABASE_TTL'] >= CACHE_CONFIG['VISUALIZATION_TTL']


class TestLoadExampleData:
    """Test load_example_data function with mocking."""

    @patch('src.data_layer.cache.pd.read_csv')
    def test_load_example_data_success(self, mock_read_csv):
        """Test successful data loading returns DataFrame."""
        # Arrange
        expected_df = pd.DataFrame({'col1': [1, 2, 3], 'col2': [4, 5, 6]})
        mock_read_csv.return_value = expected_df

        # Act
        # Need to clear streamlit cache for testing
        with patch('streamlit.cache_data', lambda ttl: lambda func: func):
            result = load_example_data()

        # Assert
        mock_read_csv.assert_called_once_with('./data/figures/example_data_10000.csv')
        pd.testing.assert_frame_equal(result, expected_df)

    @patch('src.data_layer.cache.st.error')
    @patch('src.data_layer.cache.pd.read_csv')
    def test_load_example_data_file_not_found(self, mock_read_csv, mock_st_error):
        """Test file not found returns empty DataFrame and shows error."""
        # Arrange
        mock_read_csv.side_effect = FileNotFoundError("File not found")

        # Act
        # Call the unwrapped function directly to avoid caching
        from src.data_layer import cache as cache_module
        result = cache_module.load_example_data.__wrapped__()

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert result.empty
        mock_st_error.assert_called_once()


class TestGetCachedUniqueLocations:
    """Test location caching with database mocking."""

    @patch('src.mastr.preprocessing.get_unique_solar_locations')
    def test_get_cached_unique_locations_solar(self, mock_get_solar):
        """Test fetching unique solar locations."""
        # Arrange
        expected_locations = ['Aachen', 'Berlin', 'München']
        mock_get_solar.return_value = expected_locations

        # Act
        with patch('streamlit.cache_data', lambda ttl: lambda func: func):
            result = get_cached_unique_locations('solar', '/fake/path.db')

        # Assert
        assert result == expected_locations
        mock_get_solar.assert_called_once_with(mastr_db_path='/fake/path.db')

    @patch('src.mastr.preprocessing.get_unique_wind_locations')
    def test_get_cached_unique_locations_wind(self, mock_get_wind):
        """Test fetching unique wind locations."""
        # Arrange
        expected_locations = ['Hamburg', 'Dresden']
        mock_get_wind.return_value = expected_locations

        # Act
        with patch('streamlit.cache_data', lambda ttl: lambda func: func):
            result = get_cached_unique_locations('wind', '/fake/path.db')

        # Assert
        assert result == expected_locations
        mock_get_wind.assert_called_once_with(mastr_db_path='/fake/path.db')

    def test_get_cached_unique_locations_invalid_type(self):
        """Test invalid location type returns empty list."""
        # Act
        with patch('streamlit.cache_data', lambda ttl: lambda func: func):
            result = get_cached_unique_locations('invalid', '/fake/path.db')

        # Assert
        assert result == []

    @patch('src.data_layer.cache.st.error')
    @patch('src.mastr.preprocessing.get_unique_solar_locations')
    def test_get_cached_unique_locations_exception(self, mock_get_solar, mock_st_error):
        """Test exception handling returns empty list and shows error."""
        # Arrange
        mock_get_solar.side_effect = Exception("Database connection failed")

        # Act
        # Call the unwrapped function directly to avoid caching
        from src.data_layer import cache as cache_module
        result = cache_module.get_cached_unique_locations.__wrapped__('solar', '/fake/path.db')

        # Assert
        assert result == []
        mock_st_error.assert_called_once()


class TestGetCachedMastrData:
    """Test MaStR data caching with mocking."""

    @patch('src.mastr.preprocessing.prepare_solar_data')
    def test_get_cached_mastr_data_solar(self, mock_prepare_solar):
        """Test fetching solar data."""
        # Arrange
        expected_gdf = pd.DataFrame({'col': [1, 2]})  # Use DataFrame instead of Mock
        expected_summary = {'total': 100}
        mock_prepare_solar.return_value = (expected_gdf, expected_summary)

        # Act
        from src.data_layer import cache as cache_module
        gdf, summary = cache_module.get_cached_mastr_data.__wrapped__('Aachen', 'solar', '/fake/path.db')

        # Assert
        pd.testing.assert_frame_equal(gdf, expected_gdf)
        assert summary == expected_summary
        mock_prepare_solar.assert_called_once_with(
            location='Aachen',
            mastr_db_path='/fake/path.db'
        )

    def test_get_cached_mastr_data_invalid_type(self):
        """Test invalid data type returns None tuple."""
        # Act
        with patch('streamlit.cache_data', lambda ttl: lambda func: func):
            result = get_cached_mastr_data('Aachen', 'invalid', '/fake/path.db')

        # Assert
        assert result == (None, None)


class TestCreateCachedViolinPlot:
    """Test violin plot caching."""

    @patch('src.data_layer.cache.px.violin')
    def test_create_cached_violin_plot(self, mock_violin):
        """Test violin plot generation with filtered data."""
        # Arrange
        df = pd.DataFrame({
            'diffusion_evs': [0.1, 0.1, 0.2],
            'curtailment': ['A', 'A', 'B'],
            'grid_type': ['urban', 'urban', 'rural'],
            'diffusion_hps': [0.3, 0.3, 0.4],
            'diffusion_pv_storage': [0.2, 0.2, 0.5],
            'tariff_wholesale': ['fixed', 'fixed', 'tou'],
            'tariff_grid_usage_fee': ['low', 'low', 'high'],
            'value': [10, 20, 30]
        })
        # Return a serializable dict instead of Mock
        mock_violin.return_value = {'data': [], 'layout': {}}

        # Act
        from src.data_layer import cache as cache_module
        fig = cache_module.create_cached_violin_plot.__wrapped__(
            df, 0.1, 'A', 'urban', 0.3, 0.2, 'fixed', 'low'
        )

        # Assert
        assert fig is not None
        mock_violin.assert_called_once()
        # Verify filtered DataFrame has correct shape
        call_args = mock_violin.call_args
        filtered_df = call_args[0][0]
        assert len(filtered_df) == 2  # Should match 2 rows


class TestCreateCachedScatterMap:
    """Test scatter map caching."""

    @patch('src.data_layer.cache.px.scatter_mapbox')
    def test_create_cached_scatter_map_success(self, mock_scatter_mapbox):
        """Test successful map creation."""
        # Arrange
        mock_gdf = pd.DataFrame({
            'lat': [50.0, 51.0],
            'lon': [6.0, 7.0],
            'name': ['Location 1', 'Location 2']
        })
        # Return a serializable dict instead of Mock
        mock_fig = {'data': [], 'layout': {}}
        mock_scatter_mapbox.return_value = mock_fig

        # Act
        from src.data_layer import cache as cache_module
        fig = cache_module.create_cached_scatter_map.__wrapped__(
            mock_gdf, 'lat', 'lon', ['name'],
            50.5, 6.5, color='blue', title='Test Map'
        )

        # Assert
        assert fig == mock_fig
        mock_scatter_mapbox.assert_called_once()

    @patch('src.data_layer.cache.st.error')
    @patch('src.data_layer.cache.px.scatter_mapbox')
    def test_create_cached_scatter_map_exception(self, mock_scatter_mapbox, mock_st_error):
        """Test map creation exception handling."""
        # Arrange
        mock_scatter_mapbox.side_effect = Exception("Mapbox error")

        # Act
        with patch('streamlit.cache_data', lambda ttl: lambda func: func):
            fig = create_cached_scatter_map(
                Mock(), 'lat', 'lon', ['name'], 50.5, 6.5
            )

        # Assert
        assert fig is None
        mock_st_error.assert_called_once()


class TestUpdateViolinPlot:
    """Test violin plot wrapper function."""

    @patch('src.data_layer.cache.create_cached_violin_plot')
    def test_update_violin_plot_calls_cached_function(self, mock_cached_plot):
        """Test wrapper delegates to cached implementation."""
        # Arrange
        df = pd.DataFrame({'value': [1, 2, 3]})
        mock_cached_plot.return_value = Mock()

        # Act
        result = update_violin_plot(
            df, 0.1, 'A', 'urban', 0.3, 0.2, 'fixed', 'low'
        )

        # Assert
        assert result is not None
        mock_cached_plot.assert_called_once_with(
            df, 0.1, 'A', 'urban', 0.3, 0.2, 'fixed', 'low'
        )


class TestCacheConfigLocation:
    """CACHE_CONFIG must be importable from src.config.constants."""

    def test_cache_config_importable_from_constants(self):
        from src.config.constants import CACHE_CONFIG
        assert isinstance(CACHE_CONFIG, dict)

    def test_cache_config_constants_has_required_keys(self):
        from src.config.constants import CACHE_CONFIG
        for key in ('DATA_LOAD_TTL', 'DATABASE_TTL', 'VISUALIZATION_TTL', 'ENVIRONMENT_TTL'):
            assert key in CACHE_CONFIG, f"Missing key: {key}"

    def test_cache_config_constants_values_are_positive_ints(self):
        from src.config.constants import CACHE_CONFIG
        for key, value in CACHE_CONFIG.items():
            assert isinstance(value, int), f"{key} must be int"
            assert value > 0, f"{key} must be > 0"


# Integration test markers for future use
pytestmark = pytest.mark.unit
