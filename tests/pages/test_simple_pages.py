"""
Unit tests for Phase 5a simple page functions.

Tests basic execution and functionality for:
- research_results
- network_calculations
- bev_settings
- pv_configuration
- wind_configuration
- heatpump_configuration
- electrical_storage_configuration
- openstef_forecasting
"""

import datetime
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from src.pages import (
    research_results,
    network_calculations,
    bev_settings,
    pv_configuration,
    wind_configuration,
    heatpump_configuration,
    electrical_storage_configuration,
    openstef_forecasting,
)


class TestResearchResults:
    """Tests for research_results page."""
    
    def test_function_exists(self):
        """Verify research_results function exists and is callable."""
        assert callable(research_results)
    
    def test_basic_execution(self, mock_streamlit, sample_mastr_dataframe):
        """Test research_results executes without errors."""
        # Create a global df for the module
        import src.pages.research_results as rr_module
        rr_module.df = sample_mastr_dataframe
        
        with patch('src.pages.research_results.st', mock_streamlit):
            research_results()
            assert mock_streamlit.title.called


class TestNetworkCalculations:
    """Tests for network_calculations page."""
    
    def test_function_exists(self):
        """Verify network_calculations function exists and is callable."""
        assert callable(network_calculations)
    
    def test_basic_execution(self, mock_streamlit):
        """Test network_calculations executes without errors."""
        # network_calculations imports streamlit internally
        import src.pages.network_calculations as nc_module
        
        with patch.object(nc_module, 'st', mock_streamlit), \
             patch.object(nc_module, 'pp_networks') as mock_pp:
            network_calculations()
            assert mock_streamlit.title.called


class TestBEVSettings:
    """Tests for bev_settings page."""
    
    def test_function_exists(self):
        """Verify bev_settings function exists and is callable."""
        assert callable(bev_settings)
    
    def test_basic_execution(self, mock_streamlit):
        """Test bev_settings executes without errors."""
        # Initialize session state with complete defaults
        mock_streamlit.session_state['bev_settings'] = {
            "max_battery_capacity": 75.0,
            "min_battery_capacity": 15.0,
            "battery_usage": 50.0,
            "charging_power": 11.0,
            "charging_efficiency": 0.95,
            "load_degradation_begin": 0.8,
            "user_profile": "None",
            "selected_environment": "None",
            "start_time": datetime.time(18, 0, 0),
            "end_time": datetime.time(7, 0, 0),
            "timebase": 15
        }
        
        with patch('src.pages.bev_settings.st', mock_streamlit), \
             patch('src.pages.bev_settings.battery_electric_vehicle_settings') as mock_bev:
            bev_settings()
            assert mock_streamlit.title.called


class TestPVConfiguration:
    """Tests for pv_configuration page."""
    
    def test_function_exists(self):
        """Verify pv_configuration function exists and is callable."""
        assert callable(pv_configuration)
    
    def test_basic_execution(self, mock_streamlit):
        """Test pv_configuration executes without errors."""
        # Initialize session state with complete defaults
        mock_streamlit.session_state['pv_settings'] = {
            "PV Module Library": "SandiaMod",
            "PV Module": "Canadian_Solar_CS5P_220M___2009_",
            "PV Inverter Library": "cecinverter",
            "PV Inverter": "ABB__MICRO_0_25_I_OUTD_US_208__208V_",
            "PV Surface Tilt": 30.0,
            "PV Surface Azimuth": 180.0,
            "PV Modules per String": 10,
            "PV Strings per Inverter": 2
        }
        
        with patch('src.pages.pv_configuration.st', mock_streamlit), \
             patch('src.pages.pv_configuration.pv_settings') as mock_pv:
            pv_configuration()
            assert mock_streamlit.title.called


class TestWindConfiguration:
    """Tests for wind_configuration page."""
    
    def test_function_exists(self):
        """Verify wind_configuration function exists and is callable."""
        assert callable(wind_configuration)
    
    def test_basic_execution(self, mock_streamlit):
        """Test wind_configuration executes without errors."""
        # Initialize session state with complete defaults
        mock_streamlit.session_state['wind_settings'] = {
            "Turbine Type": "E-140",
            "Hub Height": 135,
            "Rotor Diameter": 140,
            "Data Source": "Wind Turbines",
            "Wind Speed Model": "logarithmic",
            "Density Model": "Barometric",
            "Temperature Model": "Linear Gradient",
            "power_output_model": "power_curve",
            "Density Correction": False,
            "Obstacle Height": 0.0,
            "hellman_exp": 0.2
        }
        
        with patch('src.pages.wind_configuration.st', mock_streamlit), \
             patch('src.pages.wind_configuration.wind') as mock_wind:
            wind_configuration()
            assert mock_streamlit.title.called


class TestHeatPumpConfiguration:
    """Tests for heatpump_configuration page."""
    
    def test_function_exists(self):
        """Verify heatpump_configuration function exists and is callable."""
        assert callable(heatpump_configuration)
    
    def test_basic_execution(self, mock_streamlit):
        """Test heatpump_configuration executes without errors."""
        # Initialize session state with complete defaults
        mock_streamlit.session_state['heatpump_settings'] = {
            "identifier": "hp1",
            "user_profile": "None",
            "heat_pump_type": "Air",
            "Heat System Temperature": 55.0,
            "el_power": 8.0,
            "th_power": 24.0,
            "Ramp Up Time": datetime.time(0, 30),
            "Ramp Down Time": datetime.time(0, 30),
            "Minimum Run Time": datetime.time(1, 0),
            "Minimum Stop Time": datetime.time(0, 30)
        }
        
        with patch('src.pages.heatpump_configuration.st', mock_streamlit), \
             patch('src.pages.heatpump_configuration.heatpump_settings') as mock_hp:
            heatpump_configuration()
            assert mock_streamlit.title.called


class TestElectricalStorageConfiguration:
    """Tests for electrical_storage_configuration page."""
    
    def test_function_exists(self):
        """Verify electrical_storage_configuration function exists and is callable."""
        assert callable(electrical_storage_configuration)
    
    def test_basic_execution(self, mock_streamlit):
        """Test electrical_storage_configuration executes without errors."""
        # Initialize session state with defaults and mock PV object
        mock_streamlit.session_state['electrical_storage'] = {
            "Charge Efficiency": 0.95,
            "Discharge Efficiency": 0.95,
            "Max Power": 10.0,
            "Max Capacity": 10.0,
            "max_c": 1.0
        }
        # Create a minimal mock PV object (required by simulation)
        from unittest.mock import MagicMock
        mock_pv = MagicMock()
        mock_pv.identifier = "test_pv"
        mock_pv.timeseries = None
        mock_streamlit.session_state['pv'] = mock_pv
        
        with patch('src.pages.electrical_storage_configuration.st', mock_streamlit), \
             patch('src.pages.electrical_storage_configuration.electrical_storage') as mock_es:
            electrical_storage_configuration()
            assert mock_streamlit.title.called


class TestOpenSTEFForecasting:
    """Tests for openstef_forecasting page."""
    
    def test_function_exists(self):
        """Verify openstef_forecasting function exists and is callable."""
        assert callable(openstef_forecasting)
    
    def test_basic_execution(self, mock_streamlit):
        """Test openstef_forecasting executes without errors."""
        with patch('src.pages.openstef_forecasting.st', mock_streamlit):
            openstef_forecasting()
            assert mock_streamlit.title.called
