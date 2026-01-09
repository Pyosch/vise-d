"""
Unit tests for Phase 5b MaStR and energy generation pages.

Tests MaStR database integration and simulation functionality for:
- solar_installation_mastr
- wind_installation_mastr
- storage_installation_mastr
- energy_generation_solar
- wind_energy_generation
- hydrogen_research
- hydrogen_electrolyzer_settings
- thermal_storage_settings
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from src.pages import (
    solar_installation_mastr,
    wind_installation_mastr,
    storage_installation_mastr,
    energy_generation_solar,
    wind_energy_generation,
    hydrogen_research,
    hydrogen_electrolyzer_settings,
    thermal_storage_settings,
)


class TestSolarInstallationMastr:
    """Tests for solar_installation_mastr page."""
    
    def test_function_exists(self):
        """Verify solar_installation_mastr function exists and is callable."""
        assert callable(solar_installation_mastr)
    
    def test_basic_execution(self, mock_streamlit):
        """Test solar_installation_mastr executes without errors."""
        mock_locations = ['Essen', 'Berlin', 'Munich']
        
        with patch('src.pages.solar_installation_mastr.st', mock_streamlit), \
             patch('src.pages.solar_installation_mastr.get_cached_unique_locations', return_value=mock_locations):
            solar_installation_mastr()
            assert mock_streamlit.title.called
            assert mock_streamlit.selectbox.called
    
    def test_handles_empty_locations(self, mock_streamlit):
        """Test handling when no locations are available."""
        with patch('src.pages.solar_installation_mastr.st', mock_streamlit), \
             patch('src.pages.solar_installation_mastr.get_cached_unique_locations', return_value=[]):
            solar_installation_mastr()
            assert mock_streamlit.error.called


class TestWindInstallationMastr:
    """Tests for wind_installation_mastr page."""
    
    def test_function_exists(self):
        """Verify wind_installation_mastr function exists and is callable."""
        assert callable(wind_installation_mastr)
    
    def test_basic_execution(self, mock_streamlit):
        """Test wind_installation_mastr executes without errors."""
        mock_locations = ['Essen', 'Hamburg']
        
        with patch('src.pages.wind_installation_mastr.st', mock_streamlit), \
             patch('src.pages.wind_installation_mastr.get_unique_wind_locations', return_value=mock_locations):
            wind_installation_mastr()
            assert mock_streamlit.title.called
            assert mock_streamlit.selectbox.called


class TestStorageInstallationMastr:
    """Tests for storage_installation_mastr page."""
    
    def test_function_exists(self):
        """Verify storage_installation_mastr function exists and is callable."""
        assert callable(storage_installation_mastr)
    
    def test_basic_execution(self, mock_streamlit):
        """Test storage_installation_mastr executes without errors."""
        mock_locations = ['Essen', 'Cologne']
        
        with patch('src.pages.storage_installation_mastr.st', mock_streamlit), \
             patch('src.pages.storage_installation_mastr.get_unique_storage_locations', return_value=mock_locations):
            storage_installation_mastr()
            assert mock_streamlit.title.called
            assert mock_streamlit.selectbox.called


class TestEnergyGenerationSolar:
    """Tests for energy_generation_solar page."""
    
    def test_function_exists(self):
        """Verify energy_generation_solar function exists and is callable."""
        assert callable(energy_generation_solar)
    
    def test_basic_execution(self, mock_streamlit):
        """Test energy_generation_solar executes without errors."""
        mock_locations = ['Essen', 'Dortmund']
        
        with patch('src.pages.energy_generation_solar.st', mock_streamlit), \
             patch('src.pages.energy_generation_solar.get_cached_unique_locations', return_value=mock_locations):
            energy_generation_solar()
            assert mock_streamlit.title.called
            assert mock_streamlit.selectbox.called


class TestWindEnergyGeneration:
    """Tests for wind_energy_generation page."""
    
    def test_function_exists(self):
        """Verify wind_energy_generation function exists and is callable."""
        assert callable(wind_energy_generation)
    
    def test_basic_execution(self, mock_streamlit):
        """Test wind_energy_generation executes without errors."""
        mock_locations = ['Essen', 'Bochum']
        
        with patch('src.pages.wind_energy_generation.st', mock_streamlit), \
             patch('src.pages.wind_energy_generation.get_unique_wind_locations', return_value=mock_locations):
            wind_energy_generation()
            assert mock_streamlit.title.called
            assert mock_streamlit.selectbox.called


class TestHydrogenResearch:
    """Tests for hydrogen_research page."""
    
    def test_function_exists(self):
        """Verify hydrogen_research function exists and is callable."""
        assert callable(hydrogen_research)
    
    def test_basic_execution(self, mock_streamlit):
        """Test hydrogen_research executes without errors."""
        # Mock st.columns to return a list of mocks
        col1, col2 = Mock(), Mock()
        mock_streamlit.columns.return_value = [col1, col2]
        
        with patch('src.pages.hydrogen_research.st', mock_streamlit), \
             patch('src.pages.hydrogen_research.fig_5') as mock_fig5, \
             patch('src.pages.hydrogen_research.fig_7') as mock_fig7, \
             patch('src.pages.hydrogen_research.fig_8') as mock_fig8, \
             patch('src.pages.hydrogen_research.fig_9') as mock_fig9:
            
            # Mock pyplot methods
            mock_fig5.return_value = MagicMock()
            mock_fig7.return_value = MagicMock()
            mock_fig8.return_value = MagicMock()
            mock_fig9.return_value = MagicMock()
            
            hydrogen_research()
            assert mock_streamlit.write.called
            assert mock_streamlit.pyplot.called


class TestHydrogenElectrolyzerSettings:
    """Tests for hydrogen_electrolyzer_settings page."""
    
    def test_function_exists(self):
        """Verify hydrogen_electrolyzer_settings function exists and is callable."""
        assert callable(hydrogen_electrolyzer_settings)
    
    def test_basic_execution(self, mock_streamlit):
        """Test hydrogen_electrolyzer_settings executes without errors."""
        mock_streamlit.session_state['hydrogen_settings'] = {'Power_Electrolyzer': 15000.0, 'Pressure_Hydrogen': 30.0}
        
        # Mock st.columns to return list of mocks
        col1, col2 = Mock(), Mock()
        mock_streamlit.columns.return_value = [col1, col2]
        mock_streamlit.sidebar.columns = Mock(return_value=[col1, col2])
        
        with patch('src.pages.hydrogen_electrolyzer_settings.st', mock_streamlit), \
             patch('src.pages.hydrogen_electrolyzer_settings.go') as mock_go:
            hydrogen_electrolyzer_settings()
            assert mock_streamlit.title.called


class TestThermalStorageSettings:
    """Tests for thermal_storage_settings page."""
    
    def test_function_exists(self):
        """Verify thermal_storage_settings function exists and is callable."""
        assert callable(thermal_storage_settings)
    
    def test_basic_execution(self, mock_streamlit):
        """Test thermal_storage_settings executes without errors."""
        # Don't initialize session state - let the function do it
        with patch('src.pages.thermal_storage_settings.st', mock_streamlit):
            thermal_storage_settings()
            assert mock_streamlit.title.called
            # Verify session state was initialized
            assert 'thermal_storage_settings' in mock_streamlit.session_state
    
    def test_session_state_initialization(self, mock_streamlit):
        """Test thermal storage settings are initialized correctly."""
        with patch('src.pages.thermal_storage_settings.st', mock_streamlit):
            thermal_storage_settings()
            settings = mock_streamlit.session_state.get('thermal_storage_settings', {})
            
            # Check default values are set
            assert 'target temperature' in settings
            assert 'minimum temperature' in settings
            assert 'mass' in settings
            assert settings['mass'] == 300  # Default 300 kg
            assert settings['cp'] == 4.18  # Default specific heat of water
