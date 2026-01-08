"""OpenSTEF (Open Short-Term Energy Forecasting) integration for VISE-D.

Provides comprehensive forecasting capabilities for renewable energy generation,
including DWD weather data fetching, model training with MLflow, and prediction.

Consolidates functionality from:
- openstef_forecasting.py (OpenSTEFForecaster class)
- fetching_data_opestref.py (DWD data fetching)
- forecasting_utils.py (model loading and prediction utilities)

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import pickle
import json
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import mlflow

from wetterdienst.provider.dwd.mosmix import DwdMosmixRequest
from wetterdienst import Settings
from openstef.data_classes.prediction_job import PredictionJobDataClass
from openstef.model.regressors.xgb import XGBOpenstfRegressor
from openstef.pipeline.create_forecast import create_forecast_pipeline_core

from src.config import DATA_DIR, MLRUNS_DIR, FIGURES_DIR, OPENSTEF

# ============================================================================
# DWD Weather Data Fetching
# ============================================================================

class DWDWeatherFetcher:
    """Fetches and processes weather data from German Weather Service (DWD)."""
    
    def __init__(self, station_id: str = "10513", settings: Optional[Settings] = None):
        """Initialize DWD weather fetcher.
        
        Args:
            station_id: DWD station ID (default: 10513 for reference station).
            settings: Wetterdienst settings object (optional).
        """
        self.station_id = station_id
        self.settings = settings or Settings(ts_shape="long", ts_si_units=False)
    
    def fetch_weather_data(
        self, 
        parameters: list[str], 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Fetch weather data from DWD MOSMIX service.
        
        Args:
            parameters: List of weather parameters to fetch.
            start_date: Start date for data retrieval (optional).
            end_date: End date for data retrieval (optional).
            
        Returns:
            DataFrame with weather data indexed by timestamp.
        """
        request = DwdMosmixRequest(
            parameter=parameters,
            mosmix_type="small",
            settings=self.settings
        ).filter_by_station_id(station_id=(self.station_id,))
        
        if start_date and end_date:
            request = request.filter_by_date(start_date, end_date)
        
        stations = request.df
        
        if stations.empty:
            raise ValueError(f"No data found for station {self.station_id}")
        
        # Pivot to wide format with parameters as columns
        df = stations.pivot(index="date", columns="parameter", values="value")
        df.index = pd.to_datetime(df.index)
        
        return df
    
    def fetch_solar_radiation_data(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Fetch solar radiation and related parameters for PV forecasting.
        
        Args:
            start_date: Start date for data retrieval (optional).
            end_date: End date for data retrieval (optional).
            
        Returns:
            DataFrame with solar radiation data.
        """
        solar_parameters = [
            "radiation_global",  # Global radiation
            "radiation_sky_short_wave_diffuse",  # Diffuse radiation
            "sunshine_duration",  # Sunshine duration
            "cloud_cover_total",  # Cloud cover
            "temperature_air_mean_2m",  # Air temperature
        ]
        
        return self.fetch_weather_data(solar_parameters, start_date, end_date)


# ============================================================================
# Model Management
# ============================================================================

def load_model_metadata(location: str = "Aachen", data_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Load model metadata from JSON file.
    
    Args:
        location: Location name for the model.
        data_dir: Directory containing model files (uses config default if None).
        
    Returns:
        Dictionary containing model metadata.
        
    Raises:
        FileNotFoundError: If metadata file doesn't exist.
    """
    if data_dir is None:
        data_dir = DATA_DIR
    
    metadata_path = Path(data_dir) / f"model_metadata_{location}.json"
    
    if not metadata_path.exists():
        raise FileNotFoundError(f"Model metadata not found: {metadata_path}")
    
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    return metadata


def load_model_from_pickle(location: str = "Aachen", data_dir: Optional[Path] = None) -> XGBOpenstfRegressor:
    """Load trained OpenSTEF model from pickle file.
    
    Args:
        location: Location name for the model.
        data_dir: Directory containing model files (uses config default if None).
        
    Returns:
        Loaded OpenSTEF model.
        
    Raises:
        FileNotFoundError: If model file doesn't exist.
    """
    if data_dir is None:
        data_dir = DATA_DIR
    
    model_path = Path(data_dir) / f"openstef_model_{location}.pkl"
    
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")
    
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    return model


def create_prediction_job(
    metadata: Dict[str, Any], 
    lat: Optional[float] = None, 
    lon: Optional[float] = None
) -> PredictionJobDataClass:
    """Create OpenSTEF prediction job from metadata.
    
    Args:
        metadata: Model metadata dictionary.
        lat: Latitude for location (overrides metadata if provided).
        lon: Longitude for location (overrides metadata if provided).
        
    Returns:
        PredictionJobDataClass object for forecasting.
    """
    return PredictionJobDataClass(
        id=metadata.get("id", 1),
        name=metadata.get("name", "PV Forecast"),
        model=metadata.get("model", "xgb"),
        horizon_minutes=metadata.get("horizon_minutes", 2880),  # 48 hours
        resolution_minutes=metadata.get("resolution_minutes", 15),
        lat=lat or metadata.get("lat", 50.0),
        lon=lon or metadata.get("lon", 6.0),
    )


# ============================================================================
# Forecasting Pipeline
# ============================================================================

def prepare_forecast_input(
    historical_data: pd.DataFrame, 
    forecast_horizon_hours: int = 48,
    resolution_minutes: int = 15
) -> pd.DataFrame:
    """Prepare input data for forecast generation.
    
    Args:
        historical_data: Historical time series data.
        forecast_horizon_hours: Forecast horizon in hours.
        resolution_minutes: Time resolution in minutes.
        
    Returns:
        DataFrame prepared for forecasting.
    """
    # Ensure datetime index
    if not isinstance(historical_data.index, pd.DatetimeIndex):
        historical_data.index = pd.to_datetime(historical_data.index)
    
    # Resample to desired resolution
    forecast_input = historical_data.resample(f"{resolution_minutes}T").mean()
    
    # Forward fill missing values (up to 2 hours)
    forecast_input = forecast_input.fillna(method='ffill', limit=int(120 / resolution_minutes))
    
    # Create future timestamps for forecast horizon
    last_timestamp = forecast_input.index[-1]
    future_timestamps = pd.date_range(
        start=last_timestamp + timedelta(minutes=resolution_minutes),
        periods=int((forecast_horizon_hours * 60) / resolution_minutes),
        freq=f"{resolution_minutes}T"
    )
    
    # Extend dataframe with NaN values for future
    future_df = pd.DataFrame(index=future_timestamps, columns=forecast_input.columns)
    forecast_input = pd.concat([forecast_input, future_df])
    
    return forecast_input


def generate_forecast(
    pj: PredictionJobDataClass,
    forecast_input: pd.DataFrame,
    mlflow_dir: Optional[Path] = None
) -> pd.DataFrame:
    """Generate forecast using OpenSTEF pipeline.
    
    Args:
        pj: Prediction job configuration.
        forecast_input: Prepared input data for forecasting.
        mlflow_dir: MLflow tracking directory (uses config default if None).
        
    Returns:
        DataFrame with forecast results.
    """
    if mlflow_dir is None:
        mlflow_dir = MLRUNS_DIR
    
    mlflow.set_tracking_uri(str(mlflow_dir))
    
    forecast = create_forecast_pipeline_core(
        pj=pj,
        input_data=forecast_input,
        model_type=OPENSTEF.DEFAULT_MODEL_TYPE
    )
    
    return forecast


# ============================================================================
# Visualization
# ============================================================================

def create_forecast_plot(
    historical_data: pd.DataFrame,
    forecast_data: pd.DataFrame,
    location: str = "Aachen",
    title: str = "PV Generation Forecast",
    show_confidence: bool = True
) -> go.Figure:
    """Create interactive forecast visualization with Plotly.
    
    Args:
        historical_data: Historical generation data.
        forecast_data: Forecast results.
        location: Location name for plot title.
        title: Plot title.
        show_confidence: Whether to show confidence intervals.
        
    Returns:
        Plotly figure object.
    """
    fig = make_subplots(
        rows=1, cols=1,
        subplot_titles=[f"{title} - {location}"]
    )
    
    # Historical data
    fig.add_trace(
        go.Scatter(
            x=historical_data.index,
            y=historical_data.values if isinstance(historical_data, pd.Series) else historical_data.iloc[:, 0],
            name="Historical",
            mode="lines",
            line=dict(color="blue", width=2)
        )
    )
    
    # Forecast
    fig.add_trace(
        go.Scatter(
            x=forecast_data.index,
            y=forecast_data["forecast"],
            name="Forecast",
            mode="lines",
            line=dict(color="red", width=2, dash="dash")
        )
    )
    
    # Confidence intervals
    if show_confidence and "forecast_upper" in forecast_data.columns:
        fig.add_trace(
            go.Scatter(
                x=forecast_data.index,
                y=forecast_data["forecast_upper"],
                name="Upper Bound",
                mode="lines",
                line=dict(width=0),
                showlegend=False
            )
        )
        fig.add_trace(
            go.Scatter(
                x=forecast_data.index,
                y=forecast_data["forecast_lower"],
                name="Confidence Interval",
                mode="lines",
                line=dict(width=0),
                fillcolor="rgba(255, 0, 0, 0.2)",
                fill="tonexty",
                showlegend=True
            )
        )
    
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Generation (kW)",
        hovermode="x unified",
        template="plotly_white",
        height=500
    )
    
    return fig


# ============================================================================
# Main Forecaster Class
# ============================================================================

class OpenSTEFForecaster:
    """Main class for energy forecasting using OpenSTEF framework.
    
    Provides end-to-end forecasting workflow including data fetching,
    model training, prediction, and visualization.
    """
    
    def __init__(
        self,
        location: str = "Aachen",
        dwd_station_id: str = "10513",
        forecast_horizon_hours: int = 48,
        resolution_minutes: int = 15
    ):
        """Initialize OpenSTEF forecaster.
        
        Args:
            location: Location name for forecasting.
            dwd_station_id: DWD weather station ID.
            forecast_horizon_hours: Forecast horizon in hours.
            resolution_minutes: Time resolution in minutes.
        """
        self.location = location
        self.dwd_station_id = dwd_station_id
        self.forecast_horizon_hours = forecast_horizon_hours
        self.resolution_minutes = resolution_minutes
        
        self.weather_fetcher = DWDWeatherFetcher(station_id=dwd_station_id)
        self.model = None
        self.metadata = None
        self.prediction_job = None
    
    def load_model(self, data_dir: Optional[Path] = None) -> None:
        """Load trained model and metadata.
        
        Args:
            data_dir: Directory containing model files.
        """
        self.metadata = load_model_metadata(self.location, data_dir)
        self.model = load_model_from_pickle(self.location, data_dir)
        self.prediction_job = create_prediction_job(
            self.metadata,
            lat=self.metadata.get("lat"),
            lon=self.metadata.get("lon")
        )
    
    def fetch_weather_forecast(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Fetch weather forecast from DWD.
        
        Args:
            start_date: Start date for forecast.
            end_date: End date for forecast.
            
        Returns:
            DataFrame with weather forecast data.
        """
        return self.weather_fetcher.fetch_solar_radiation_data(start_date, end_date)
    
    def generate_forecast(
        self,
        historical_data: pd.DataFrame,
        weather_forecast: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """Generate energy generation forecast.
        
        Args:
            historical_data: Historical generation and weather data.
            weather_forecast: Future weather forecast (fetched if not provided).
            
        Returns:
            DataFrame with forecast results.
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load_model() first.")
        
        # Fetch weather forecast if not provided
        if weather_forecast is None:
            weather_forecast = self.fetch_weather_forecast()
        
        # Prepare input data
        forecast_input = prepare_forecast_input(
            historical_data,
            self.forecast_horizon_hours,
            self.resolution_minutes
        )
        
        # Merge weather forecast
        if not weather_forecast.empty:
            forecast_input = forecast_input.join(weather_forecast, how="left")
        
        # Generate forecast
        forecast = generate_forecast(
            self.prediction_job,
            forecast_input
        )
        
        return forecast
    
    def create_visualization(
        self,
        historical_data: pd.DataFrame,
        forecast_data: pd.DataFrame,
        title: Optional[str] = None
    ) -> go.Figure:
        """Create forecast visualization.
        
        Args:
            historical_data: Historical generation data.
            forecast_data: Forecast results.
            title: Custom plot title.
            
        Returns:
            Plotly figure object.
        """
        if title is None:
            title = f"Energy Generation Forecast - {self.location}"
        
        return create_forecast_plot(
            historical_data,
            forecast_data,
            self.location,
            title
        )


# ============================================================================
# Utility Functions
# ============================================================================

def load_historical_weather_data(location: str = "Aachen", data_dir: Optional[Path] = None) -> pd.DataFrame:
    """Load historical weather data from file.
    
    Args:
        location: Location name.
        data_dir: Data directory (uses config default if None).
        
    Returns:
        DataFrame with historical weather data.
    """
    if data_dir is None:
        data_dir = DATA_DIR
    
    weather_path = Path(data_dir) / f"historical_weather_{location}.csv"
    
    if not weather_path.exists():
        raise FileNotFoundError(f"Historical weather data not found: {weather_path}")
    
    df = pd.read_csv(weather_path, index_col=0, parse_dates=True)
    return df


def load_historical_generation_data(location: str = "Aachen", data_dir: Optional[Path] = None) -> pd.DataFrame:
    """Load historical generation data from file.
    
    Args:
        location: Location name.
        data_dir: Data directory (uses config default if None).
        
    Returns:
        DataFrame with historical generation data.
    """
    if data_dir is None:
        data_dir = DATA_DIR
    
    generation_path = Path(data_dir) / f"historical_generation_{location}.csv"
    
    if not generation_path.exists():
        raise FileNotFoundError(f"Historical generation data not found: {generation_path}")
    
    df = pd.read_csv(generation_path, index_col=0, parse_dates=True)
    return df
