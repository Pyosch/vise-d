"""OpenSTEF (Open Short-Term Energy Forecasting) integration package.

Provides forecasting capabilities for renewable energy generation using DWD weather
data and OpenSTEF framework with MLflow model tracking.

Author: Pyosch
AI Assistance: Claude Code (Claude Opus 4.8)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["Claude Code (Claude Opus 4.8)"]

from src.forecasting.openstef import (
    DWDWeatherFetcher,
    OpenSTEFForecaster,
    create_forecast_plot,
    create_prediction_job,
    generate_forecast,
    load_historical_generation_data,
    load_historical_weather_data,
    load_model_from_pickle,
    load_model_metadata,
    prepare_forecast_input,
)

__all__ = [
    "DWDWeatherFetcher",
    "OpenSTEFForecaster",
    "create_forecast_plot",
    "create_prediction_job",
    "generate_forecast",
    "load_historical_generation_data",
    "load_historical_weather_data",
    "load_model_from_pickle",
    "load_model_metadata",
    "prepare_forecast_input",
]
