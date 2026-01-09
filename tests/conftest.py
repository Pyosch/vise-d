"""Test fixtures and configuration for VISE-D test suite.

This module provides shared fixtures and pytest configuration for all tests.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import pytest
import pandas as pd
from unittest.mock import Mock


@pytest.fixture
def sample_mastr_dataframe():
    """Create sample MaStR-like DataFrame for testing.
    
    Returns:
        pd.DataFrame: Sample data with typical MaStR columns.
    """
    return pd.DataFrame({
        'EinheitMastrNummer': ['SEE001', 'SEE002', 'SEE003'],
        'Gemeinde': ['Aachen', 'Aachen', 'Berlin'],
        'Bruttoleistung': [10.5, 25.0, 50.0],
        'Laengengrad': [6.0, 6.1, 13.4],
        'Breitengrad': [50.7, 50.8, 52.5],
        'Inbetriebnahmedatum': pd.to_datetime(['2020-01-01', '2021-06-15', '2022-03-10'])
    })


@pytest.fixture
def sample_research_dataframe():
    """Create sample research results DataFrame for testing.
    
    Returns:
        pd.DataFrame: Sample data with EV research parameters.
    """
    return pd.DataFrame({
        'diffusion_evs': [0.1, 0.1, 0.2, 0.2],
        'curtailment': ['none', 'smart', 'none', 'smart'],
        'grid_type': ['urban', 'urban', 'rural', 'rural'],
        'diffusion_hps': [0.3, 0.3, 0.4, 0.4],
        'diffusion_pv_storage': [0.2, 0.2, 0.5, 0.5],
        'tariff_wholesale': ['fixed', 'tou', 'fixed', 'rtp'],
        'tariff_grid_usage_fee': ['low', 'low', 'high', 'high'],
        'value': [100.5, 95.2, 110.3, 88.7]
    })


@pytest.fixture
def mock_streamlit():
    """Create mock Streamlit module for testing UI components.
    
    Returns:
        Mock: Mock object with Streamlit-like interface.
    """
    mock_st = Mock()
    
    # Basic decorators
    mock_st.cache_data = lambda ttl=None: lambda func: func
    mock_st.cache_resource = lambda ttl=None: lambda func: func
    
    # Message functions
    mock_st.error = Mock()
    mock_st.success = Mock()
    mock_st.warning = Mock()
    mock_st.info = Mock()
    mock_st.write = Mock()
    mock_st.title = Mock()
    mock_st.header = Mock()
    mock_st.subheader = Mock()
    mock_st.markdown = Mock()
    
    # Input widgets
    mock_st.button = Mock(return_value=False)
    mock_st.selectbox = Mock(return_value='Essen')
    mock_st.number_input = Mock(return_value=0.0)
    
    # Layout
    mock_st.columns = Mock(return_value=[Mock(), Mock()])
    
    # Context managers - spinner, sidebar, form, etc.
    mock_spinner = Mock()
    mock_spinner.__enter__ = Mock(return_value=mock_spinner)
    mock_spinner.__exit__ = Mock(return_value=None)
    mock_st.spinner = Mock(return_value=mock_spinner)
    
    mock_sidebar = Mock()
    mock_sidebar.__enter__ = Mock(return_value=mock_sidebar)
    mock_sidebar.__exit__ = Mock(return_value=None)
    mock_sidebar.subheader = Mock()
    mock_sidebar.columns = Mock(return_value=[Mock(), Mock()])
    mock_sidebar.button = Mock(return_value=False)
    mock_sidebar.header = Mock()
    mock_sidebar.number_input = Mock(return_value=0.0)
    mock_st.sidebar = mock_sidebar
    
    mock_container = Mock()
    mock_container.__enter__ = Mock(return_value=mock_container)
    mock_container.__exit__ = Mock(return_value=None)
    mock_container.header = Mock()
    mock_container.markdown = Mock()
    mock_container.number_input = Mock(return_value=0.0)
    mock_container.button = Mock(return_value=False)
    mock_st.container = Mock(return_value=mock_container)
    
    mock_form = Mock()
    mock_form.__enter__ = Mock(return_value=mock_form)
    mock_form.__exit__ = Mock(return_value=None)
    mock_form.form_submit_button = Mock(return_value=False)
    mock_st.form = Mock(return_value=mock_form)
    
    mock_expander = Mock()
    mock_expander.__enter__ = Mock(return_value=mock_expander)
    mock_expander.__exit__ = Mock(return_value=None)
    mock_expander.markdown = Mock()
    mock_expander.code = Mock()
    mock_st.expander = Mock(return_value=mock_expander)
    
    # Progress and status
    mock_progress = Mock()
    mock_progress.progress = Mock()
    mock_progress.empty = Mock()
    mock_st.progress = Mock(return_value=mock_progress)
    mock_st.empty = Mock(return_value=Mock())
    
    # Plotting
    mock_st.plotly_chart = Mock()
    mock_st.pyplot = Mock()
    mock_st.dataframe = Mock()
    mock_st.metric = Mock()
    
    # Session state - make it a dictionary-like object
    mock_session_state = {}
    mock_st.session_state = mock_session_state
    
    return mock_st


@pytest.fixture
def mock_environment():
    """Create mock vpplib Environment for testing.
    
    Returns:
        Mock: Mock Environment object with typical attributes.
    """
    mock_env = Mock()
    mock_env.start = '2024-01-01 00:00:00'
    mock_env.end = '2024-12-31 23:00:00'
    mock_env.get_dwd_pv_data = Mock()
    mock_env.timeseries = pd.date_range('2024-01-01', '2024-12-31', freq='h')
    return mock_env


@pytest.fixture
def temp_mastr_db(tmp_path):
    """Create temporary SQLite database for MaStR testing.
    
    Args:
        tmp_path: pytest built-in fixture providing temporary directory.
    
    Returns:
        pathlib.Path: Path to temporary database file.
    """
    import sqlite3
    
    db_path = tmp_path / "test_mastr.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create sample solar table
    cursor.execute("""
        CREATE TABLE solar_extended (
            EinheitMastrNummer TEXT PRIMARY KEY,
            Gemeinde TEXT,
            Bruttoleistung REAL,
            Laengengrad REAL,
            Breitengrad REAL,
            Inbetriebnahmedatum TEXT
        )
    """)
    
    # Insert sample data
    cursor.execute("""
        INSERT INTO solar_extended VALUES
        ('SEE001', 'Aachen', 10.5, 6.0, 50.7, '2020-01-01'),
        ('SEE002', 'Berlin', 25.0, 13.4, 52.5, '2021-06-15')
    """)
    
    conn.commit()
    conn.close()
    
    return db_path


# Configure pytest markers
def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "ui: mark test as UI component test")
    config.addinivalue_line("markers", "slow: mark test as slow-running")
