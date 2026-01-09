"""Unit tests for vpplib Environment caching.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.data_layer.environment import get_cached_environment


class TestGetCachedEnvironment:
    """Test Environment object caching."""

    @patch('src.data_layer.environment.Environment')
    def test_get_cached_environment_without_coordinates(self, mock_env_class):
        """Test Environment creation without PV data."""
        # Arrange
        mock_env = Mock()
        mock_env_class.return_value = mock_env

        # Act
        with patch('streamlit.cache_resource', lambda ttl: lambda func: func):
            result = get_cached_environment('2024-01-01 00:00:00', '2024-12-31 23:00:00')

        # Assert
        assert result == mock_env
        mock_env_class.assert_called_once_with(
            start='2024-01-01 00:00:00',
            end='2024-12-31 23:00:00'
        )
        mock_env.get_dwd_pv_data.assert_not_called()

    @patch('src.data_layer.environment.Environment')
    def test_get_cached_environment_with_coordinates(self, mock_env_class):
        """Test Environment creation with PV data fetching."""
        # Arrange
        mock_env = Mock()
        mock_env_class.return_value = mock_env

        # Act
        with patch('streamlit.cache_resource', lambda ttl: lambda func: func):
            result = get_cached_environment(
                '2024-01-01 00:00:00',
                '2024-12-31 23:00:00',
                lat=50.776351,
                lon=6.083862
            )

        # Assert
        assert result == mock_env
        mock_env_class.assert_called_once()
        mock_env.get_dwd_pv_data.assert_called_once_with(
            lat=50.776351,
            lon=6.083862
        )

    @patch('src.data_layer.environment.st.error')
    @patch('src.data_layer.environment.Environment')
    def test_get_cached_environment_exception(self, mock_env_class, mock_st_error):
        """Test Environment creation exception handling."""
        # Arrange
        mock_env_class.side_effect = Exception("Weather data unavailable")

        # Act
        from src.data_layer import environment as env_module
        result = env_module.get_cached_environment.__wrapped__('2024-01-01 00:00:00', '2024-12-31 23:00:00')

        # Assert
        assert result is None
        mock_st_error.assert_called_once()

    @patch('src.data_layer.environment.st.error')
    @patch('src.data_layer.environment.Environment')
    def test_get_cached_environment_pv_data_fetch_error(self, mock_env_class, mock_st_error):
        """Test handling of PV data fetch errors."""
        # Arrange
        mock_env = Mock()
        mock_env.get_dwd_pv_data.side_effect = Exception("DWD API error")
        mock_env_class.return_value = mock_env

        # Act
        from src.data_layer import environment as env_module
        result = env_module.get_cached_environment.__wrapped__(
            '2024-01-01 00:00:00',
            '2024-12-31 23:00:00',
            lat=50.0,
            lon=6.0
        )

        # Assert - function should catch exception and return None
        assert result is None
        mock_st_error.assert_called_once()


pytestmark = pytest.mark.unit
