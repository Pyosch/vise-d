"""
Utility functions for OpenSTEF-based PV generation forecasting.
Used by both training scripts and Streamlit dashboard.
"""

import os
import json
import pickle
import pandas as pd
import plotly.graph_objects as go
from openstef.data_classes.prediction_job import PredictionJobDataClass
from openstef.pipeline.create_forecast import create_forecast_pipeline


def load_model_metadata(location="Aachen", data_dir="data"):
    """
    Load model training metadata from JSON file.
    
    Parameters:
    -----------
    location : str
        Location name (e.g., 'Aachen')
    data_dir : str
        Directory containing metadata file
        
    Returns:
    --------
    dict : Model metadata including training date, metrics, capacity, etc.
    """
    metadata_path = os.path.join(data_dir, f'{location}_model_metadata.json')
    
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Model metadata not found: {metadata_path}")
    
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    return metadata


def load_model_from_pickle(location="Aachen", data_dir="data"):
    """
    Load trained model from pickle file.
    
    Parameters:
    -----------
    location : str
        Location name (e.g., 'Aachen')
    data_dir : str
        Directory containing model file
        
    Returns:
    --------
    model : Trained XGBoost model
    """
    model_path = os.path.join(data_dir, f'{location}_trained_model.pkl')
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
    
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    return model


def create_prediction_job(metadata, lat=None, lon=None):
    """
    Create PredictionJobDataClass from metadata.
    
    Parameters:
    -----------
    metadata : dict
        Model metadata dictionary
    lat : float, optional
        Latitude (uses metadata location if not provided)
    lon : float, optional
        Longitude (uses metadata location if not provided)
        
    Returns:
    --------
    PredictionJobDataClass : Prediction job configuration
    """
    pj_dict = {
        "model": "xgb",
        "id": metadata['model_id'],
        "quantiles": [0.10, 0.30, 0.50, 0.70, 0.90],
        "forecast_type": "demand",
        "lat": lat if lat is not None else 50.7753,  # Aachen default
        "lon": lon if lon is not None else 6.0839,
        "resolution_minutes": metadata['resolution_minutes'],
        "name": f"{metadata['location']}_pv_forecast",
        "save_train_forecasts": True
    }
    
    return PredictionJobDataClass(**pj_dict)


def prepare_forecast_input(historical_data, forecast_horizon_hours=48, resolution_minutes=15):
    """
    Prepare input data for forecasting using persistence method.
    
    Parameters:
    -----------
    historical_data : pd.DataFrame
        Historical weather data with columns: ghi, dhi, dni, bh, zenith
    forecast_horizon_hours : int
        Number of hours to forecast ahead
    resolution_minutes : int
        Time resolution in minutes (default: 15)
        
    Returns:
    --------
    pd.DataFrame : Forecast input data with weather features
    """
    # Get the last known weather conditions
    last_weather = historical_data.iloc[-1]
    
    # Calculate number of forecast steps
    forecast_steps = int(forecast_horizon_hours * 60 / resolution_minutes)
    
    # Create forecast time index starting after last historical point
    forecast_start = historical_data.index[-1] + pd.Timedelta(minutes=resolution_minutes)
    forecast_index = pd.date_range(
        start=forecast_start,
        periods=forecast_steps,
        freq=f'{resolution_minutes}min',
        tz='UTC'  # Ensure UTC timezone
    )
    
    # Create forecast input dataframe
    forecast_input = pd.DataFrame(index=forecast_index)
    
    # Use persistence: replicate last known weather conditions
    weather_features = ['ghi', 'dhi', 'dni', 'bh', 'zenith']
    for col in weather_features:
        if col in historical_data.columns:
            forecast_input[col] = last_weather[col]
    
    return forecast_input


def generate_forecast(pj, forecast_input, mlflow_dir="mlruns"):
    """
    Generate forecast using OpenSTEF pipeline.
    
    Parameters:
    -----------
    pj : PredictionJobDataClass
        Prediction job configuration
    forecast_input : pd.DataFrame
        Forecast input data with weather features
    mlflow_dir : str
        MLflow tracking directory
        
    Returns:
    --------
    pd.DataFrame : Forecast results with confidence intervals
    """
    # Convert MLflow directory to proper URI format
    mlflow_uri = f"file:///{mlflow_dir.replace(os.sep, '/')}"
    
    # Generate forecast
    forecast = create_forecast_pipeline(
        pj=pj,
        input_data=forecast_input,
        mlflow_tracking_uri=mlflow_uri
    )
    
    return forecast


def create_forecast_plot(historical_data, forecast_data, location="Aachen", 
                         lookback_hours=7*24, forecast_horizon_hours=48):
    """
    Create interactive Plotly visualization of historical data and forecast.
    
    Parameters:
    -----------
    historical_data : pd.DataFrame
        Historical PV generation data with 'pv_generation_kw' column
    forecast_data : pd.DataFrame
        Forecast results from OpenSTEF
    location : str
        Location name for plot title
    lookback_hours : int
        Hours of historical data to show (default: 7 days)
    forecast_horizon_hours : int
        Forecast horizon in hours
        
    Returns:
    --------
    plotly.graph_objects.Figure : Interactive plot
    """
    # Prepare historical data subset
    lookback_steps = int(lookback_hours * 4)  # 15-min intervals
    historical_subset = historical_data.tail(lookback_steps).copy()
    historical_subset = historical_subset.reset_index()
    historical_subset.columns = ['datetime', 'actual']
    
    # Prepare forecast data
    forecast_df = forecast_data.copy()
    
    # Handle different forecast column names
    if 'forecast' not in forecast_df.columns:
        numeric_cols = forecast_df.select_dtypes(include=['float64', 'int64']).columns
        if len(numeric_cols) > 0:
            forecast_df['forecast'] = forecast_df[numeric_cols[0]]
    
    forecast_df = forecast_df.reset_index()
    if 'datetime' not in forecast_df.columns:
        forecast_df.columns = ['datetime'] + list(forecast_df.columns[1:])
    
    # Create figure
    fig = go.Figure()
    
    # Add historical data
    fig.add_trace(go.Scatter(
        x=historical_subset['datetime'],
        y=historical_subset['actual'],
        name='Historical Generation',
        line=dict(color='#2E86AB', width=2),
        mode='lines',
        hovertemplate='<b>Historical</b><br>Time: %{x}<br>Power: %{y:.2f} kW<extra></extra>'
    ))
    
    # Add forecast data
    fig.add_trace(go.Scatter(
        x=forecast_df['datetime'],
        y=forecast_df['forecast'],
        name='Forecast',
        line=dict(color='#A23B72', width=3, dash='dash'),
        mode='lines',
        hovertemplate='<b>Forecast</b><br>Time: %{x}<br>Power: %{y:.2f} kW<extra></extra>'
    ))
    
    # Add confidence intervals if available
    if 'forecast_lower' in forecast_df.columns and 'forecast_upper' in forecast_df.columns:
        fig.add_trace(go.Scatter(
            x=forecast_df['datetime'].tolist() + forecast_df['datetime'].tolist()[::-1],
            y=forecast_df['forecast_upper'].tolist() + forecast_df['forecast_lower'].tolist()[::-1],
            fill='toself',
            fillcolor='rgba(162, 59, 114, 0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            name='90% Confidence Interval',
            showlegend=True,
            hoverinfo='skip'
        ))
    
    # Add vertical line at forecast start
    transition_time = historical_subset['datetime'].iloc[-1]
    fig.add_vline(
        x=transition_time,
        line_dash="dot",
        line_color="gray",
        annotation_text="Forecast Start",
        annotation_position="top"
    )
    
    # Update layout
    fig.update_layout(
        title=f'PV Generation: Historical Data & {forecast_horizon_hours}h Forecast - {location}',
        xaxis_title='Date & Time',
        yaxis_title='Power Generation (kW)',
        hovermode='x unified',
        template='plotly_white',
        height=600,
        font=dict(size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray'
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray'
        )
    )
    
    return fig


def load_historical_weather_data(location="Aachen", data_dir="data"):
    """
    Load historical weather data from CSV.
    
    Parameters:
    -----------
    location : str
        Location name
    data_dir : str
        Data directory
        
    Returns:
    --------
    pd.DataFrame : Historical weather data with DatetimeIndex
    """
    weather_path = os.path.join(data_dir, f'{location}_weather_data.csv')
    
    if not os.path.exists(weather_path):
        raise FileNotFoundError(f"Weather data not found: {weather_path}")
    
    weather_data = pd.read_csv(weather_path, index_col=0, parse_dates=True)
    
    # Ensure UTC timezone
    if weather_data.index.tz is None:
        weather_data.index = weather_data.index.tz_localize('UTC')
    
    return weather_data


def load_historical_generation_data(location="Aachen", data_dir="data"):
    """
    Load historical PV generation data from CSV.
    
    Parameters:
    -----------
    location : str
        Location name
    data_dir : str
        Data directory
        
    Returns:
    --------
    pd.DataFrame : Historical PV generation data with DatetimeIndex
    """
    generation_path = os.path.join(data_dir, f'{location}_pv_generation.csv')
    
    if not os.path.exists(generation_path):
        raise FileNotFoundError(f"Generation data not found: {generation_path}")
    
    generation_data = pd.read_csv(generation_path, index_col=0, parse_dates=True)
    
    # Ensure UTC timezone
    if generation_data.index.tz is None:
        generation_data.index = generation_data.index.tz_localize('UTC')
    
    return generation_data
