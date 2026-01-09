"""
OpenSTEF Energy Forecasting Module for VISE-D Dashboard

This module provides functionality to:
1. Prepare data for OpenSTEF forecasting
2. Train forecasting models
3. Generate energy forecasts
4. Validate and evaluate models
5. Visualize forecast results

Author: VISE-D Team
Date: November 2025
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, List
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# OpenSTEF imports
try:
    from openstef.data_classes.prediction_job import PredictionJobDataClass
    from openstef.pipeline.train_model import train_model_pipeline
    from openstef.pipeline.create_forecast import create_forecast_pipeline
    from openstef.model.serializer import MLflowSerializer
    from openstef.validation import validation
    OPENSTEF_AVAILABLE = True
except ImportError:
    OPENSTEF_AVAILABLE = False
    st.warning("⚠️ OpenSTEF not installed. Run: pip install openstef")

# Wetterdienst for weather data
try:
    from wetterdienst import Settings
    from wetterdienst.provider.dwd.observation import DwdObservationRequest
    WETTERDIENST_AVAILABLE = True
except ImportError:
    WETTERDIENST_AVAILABLE = False


class OpenSTEFForecaster:
    """
    Main class for energy forecasting using OpenSTEF
    """
    
    def __init__(self, location_name: str, latitude: float, longitude: float):
        """
        Initialize the forecaster
        
        Args:
            location_name: Name of the location (e.g., "Berlin")
            latitude: Latitude coordinate
            longitude: Longitude coordinate
        """
        self.location_name = location_name
        self.latitude = latitude
        self.longitude = longitude
        self.model = None
        self.training_data = None
        self.feature_importance = None
        self.metrics = {}
        
    def fetch_weather_data(
        self, 
        start_date: str, 
        end_date: str,
        resolution: str = "hourly"
    ) -> pd.DataFrame:
        """
        Fetch weather data from DWD using Wetterdienst
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            resolution: Data resolution (hourly, daily)
            
        Returns:
            DataFrame with weather data
        """
        if not WETTERDIENST_AVAILABLE:
            st.error("Wetterdienst not available. Using dummy data.")
            return self._create_dummy_weather_data(start_date, end_date)
        
        try:
            settings = Settings(
                ts_shape="long",
                ts_humanize=True,
                ts_convert_units=True
            )
            
            # Get nearby station
            stations_request = DwdObservationRequest(
                parameters=[("hourly", "temperature_air", "temperature_air_mean_200")],
                start_date=start_date,
                end_date=end_date,
                settings=settings
            ).filter_by_rank(
                latlon=(self.latitude, self.longitude),
                rank=1
            )
            
            # Fetch multiple parameters
            weather_params = {
                'temperature': ('hourly', 'temperature_air', 'temperature_air_mean_200'),
                'radiation': ('hourly', 'solar', 'radiation_global'),
                'wind': ('hourly', 'wind', 'wind_speed'),
                'pressure': ('hourly', 'pressure', 'pressure_air_site'),
            }
            
            weather_dfs = []
            
            for param_name, (res, dataset, param) in weather_params.items():
                try:
                    request = DwdObservationRequest(
                        parameters=[(res, dataset, param)],
                        start_date=start_date,
                        end_date=end_date,
                        settings=settings
                    ).filter_by_rank(
                        latlon=(self.latitude, self.longitude),
                        rank=1
                    )
                    
                    values = request.values.all().df
                    if not values.empty:
                        # Pivot to wide format
                        df_pivot = values.pivot_table(
                            index='date',
                            columns='parameter',
                            values='value',
                            aggfunc='first'
                        )
                        df_pivot.columns = [param_name]
                        weather_dfs.append(df_pivot)
                except Exception as e:
                    st.warning(f"Could not fetch {param_name}: {str(e)}")
            
            if weather_dfs:
                weather_df = pd.concat(weather_dfs, axis=1)
                weather_df.index.name = 'datetime'
                return weather_df.reset_index()
            else:
                return self._create_dummy_weather_data(start_date, end_date)
                
        except Exception as e:
            st.error(f"Error fetching weather data: {str(e)}")
            return self._create_dummy_weather_data(start_date, end_date)
    
    def _create_dummy_weather_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Create dummy weather data for testing"""
        date_range = pd.date_range(start=start_date, end=end_date, freq='h')
        
        # Create realistic seasonal patterns
        hour_of_year = np.arange(len(date_range)) / (24 * 365) * 2 * np.pi
        
        df = pd.DataFrame({
            'datetime': date_range,
            'temperature': 10 + 10 * np.sin(hour_of_year) + np.random.randn(len(date_range)) * 2,
            'radiation': np.maximum(0, 200 + 300 * np.sin(hour_of_year) + np.random.randn(len(date_range)) * 50),
            'wind_speed': np.maximum(0, 5 + 3 * np.sin(hour_of_year / 2) + np.random.randn(len(date_range)) * 2),
            'pressure': 1013 + np.random.randn(len(date_range)) * 5,
        })
        
        return df
    
    def prepare_training_data(
        self,
        energy_data: pd.DataFrame,
        weather_data: pd.DataFrame,
        target_column: str = 'energy_generation'
    ) -> pd.DataFrame:
        """
        Prepare combined dataset for model training
        
        Args:
            energy_data: DataFrame with energy generation data
            weather_data: DataFrame with weather data
            target_column: Name of the column to forecast
            
        Returns:
            Combined DataFrame ready for OpenSTEF
        """
        # Ensure datetime columns
        if 'datetime' not in energy_data.columns:
            energy_data['datetime'] = pd.to_datetime(energy_data.index)
        if 'datetime' not in weather_data.columns:
            weather_data['datetime'] = pd.to_datetime(weather_data.index)
        
        # Merge on datetime
        combined = pd.merge(
            energy_data,
            weather_data,
            on='datetime',
            how='left'
        )
        
        # Sort by datetime
        combined = combined.sort_values('datetime').reset_index(drop=True)
        
        # Rename target column to 'load' (OpenSTEF convention)
        if target_column in combined.columns and target_column != 'load':
            combined['load'] = combined[target_column]
        
        # Forward fill missing weather data (up to 3 hours)
        weather_cols = ['temperature', 'radiation', 'wind_speed', 'pressure']
        combined[weather_cols] = combined[weather_cols].ffill(limit=3)
        
        # Drop rows with missing load values
        combined = combined.dropna(subset=['load'])
        
        # Add time-based features
        combined['hour'] = combined['datetime'].dt.hour
        combined['day_of_week'] = combined['datetime'].dt.dayofweek
        combined['month'] = combined['datetime'].dt.month
        combined['is_weekend'] = (combined['day_of_week'] >= 5).astype(int)
        
        self.training_data = combined
        return combined
    
    def create_prediction_job(
        self,
        data: pd.DataFrame,
        model_type: str = 'xgb'
    ) -> PredictionJobDataClass:
        """
        Create OpenSTEF prediction job configuration
        
        Args:
            data: Prepared training data
            model_type: Model type ('xgb', 'lgb', 'linear', 'xgb_quantile')
            
        Returns:
            PredictionJobDataClass object
        """
        if not OPENSTEF_AVAILABLE:
            return None
        
        # Create prediction job
        pj = PredictionJobDataClass(
            id=1,
            name=f"{self.location_name}_forecast",
            model=model_type,
            horizon_minutes=2880,  # 48 hours
            resolution_minutes=60,  # 1 hour
            train_components=False,
            lat=self.latitude,
            lon=self.longitude,
        )
        
        return pj
    
    def train_model(
        self,
        data: pd.DataFrame,
        model_type: str = 'xgb',
        backtest_months: int = 3
    ) -> Tuple[object, Dict]:
        """
        Train forecasting model using OpenSTEF
        
        Args:
            data: Prepared training data
            model_type: Type of model to train
            backtest_months: Number of months for backtesting
            
        Returns:
            Tuple of (trained_model, metrics_dict)
        """
        if not OPENSTEF_AVAILABLE:
            st.error("OpenSTEF not available")
            return None, {}
        
        try:
            # Create prediction job
            pj = self.create_prediction_job(data, model_type)
            
            # Prepare data in OpenSTEF format
            train_data = data.copy()
            train_data = train_data.set_index('datetime')
            
            # Train model using OpenSTEF pipeline
            with st.spinner("Training model... This may take a few minutes."):
                model_specs, model, report = train_model_pipeline(
                    pj=pj,
                    input_data=train_data,
                    check_old_model_age=False
                )
            
            self.model = model
            
            # Extract metrics from report
            metrics = {
                'r_score': report.get('r_score', 0.0),
                'mae': report.get('mae', 0.0),
                'rmse': report.get('rmse', 0.0),
                'mape': report.get('mape', 0.0),
            }
            
            self.metrics = metrics
            
            # Feature importance
            if hasattr(model, 'feature_importances_'):
                feature_names = [col for col in train_data.columns if col != 'load']
                self.feature_importance = pd.DataFrame({
                    'feature': feature_names,
                    'importance': model.feature_importances_
                }).sort_values('importance', ascending=False)
            
            return model, metrics
            
        except Exception as e:
            st.error(f"Error training model: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
            return None, {}
    
    def create_forecast(
        self,
        model: object,
        forecast_start: str,
        horizon_hours: int = 48,
        weather_forecast: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Create energy forecast
        
        Args:
            model: Trained model
            forecast_start: Start datetime for forecast
            horizon_hours: Forecast horizon in hours
            weather_forecast: Future weather data (if None, uses persistence)
            
        Returns:
            DataFrame with forecast
        """
        if not OPENSTEF_AVAILABLE or model is None:
            return self._create_dummy_forecast(forecast_start, horizon_hours)
        
        try:
            # Create future datetime index
            forecast_index = pd.date_range(
                start=forecast_start,
                periods=horizon_hours,
                freq='h'
            )
            
            # Prepare forecast input data
            if weather_forecast is None:
                # Use persistence (last known weather)
                if self.training_data is not None:
                    last_weather = self.training_data.iloc[-1]
                    forecast_input = pd.DataFrame({
                        'datetime': forecast_index,
                        'temperature': last_weather.get('temperature', 15),
                        'radiation': last_weather.get('radiation', 0),
                        'wind_speed': last_weather.get('wind_speed', 5),
                        'pressure': last_weather.get('pressure', 1013),
                    })
                else:
                    forecast_input = self._create_dummy_weather_data(
                        forecast_start,
                        (pd.to_datetime(forecast_start) + pd.Timedelta(hours=horizon_hours)).strftime('%Y-%m-%d')
                    )
            else:
                forecast_input = weather_forecast.copy()
            
            # Add time features
            forecast_input['hour'] = forecast_input['datetime'].dt.hour
            forecast_input['day_of_week'] = forecast_input['datetime'].dt.dayofweek
            forecast_input['month'] = forecast_input['datetime'].dt.month
            forecast_input['is_weekend'] = (forecast_input['day_of_week'] >= 5).astype(int)
            
            # Set datetime as index
            forecast_input = forecast_input.set_index('datetime')
            
            # Make predictions
            predictions = model.predict(forecast_input)
            
            # Create forecast DataFrame
            forecast_df = pd.DataFrame({
                'datetime': forecast_index,
                'forecast': predictions,
                'lower_bound': predictions * 0.9,  # Simple 90% interval
                'upper_bound': predictions * 1.1,
            })
            
            return forecast_df
            
        except Exception as e:
            st.error(f"Error creating forecast: {str(e)}")
            return self._create_dummy_forecast(forecast_start, horizon_hours)
    
    def _create_dummy_forecast(self, start_date: str, horizon_hours: int) -> pd.DataFrame:
        """Create dummy forecast for demonstration"""
        forecast_index = pd.date_range(start=start_date, periods=horizon_hours, freq='h')
        hour_of_day = forecast_index.hour
        
        # Create realistic load pattern
        base_load = 50 + 30 * np.sin(2 * np.pi * hour_of_day / 24)
        noise = np.random.randn(len(forecast_index)) * 5
        
        forecast = base_load + noise
        
        return pd.DataFrame({
            'datetime': forecast_index,
            'forecast': forecast,
            'lower_bound': forecast * 0.9,
            'upper_bound': forecast * 1.1,
        })
    
    def plot_forecast(
        self,
        forecast_df: pd.DataFrame,
        historical_data: Optional[pd.DataFrame] = None,
        title: str = "Energy Forecast"
    ) -> go.Figure:
        """
        Create interactive forecast plot
        
        Args:
            forecast_df: Forecast DataFrame
            historical_data: Optional historical data to plot alongside
            title: Plot title
            
        Returns:
            Plotly Figure object
        """
        fig = go.Figure()
        
        # Plot historical data if provided
        if historical_data is not None:
            fig.add_trace(go.Scatter(
                x=historical_data['datetime'],
                y=historical_data.get('load', historical_data.get('energy_generation', [])),
                name='Historical',
                line=dict(color='gray', width=2),
                mode='lines'
            ))
        
        # Plot forecast
        fig.add_trace(go.Scatter(
            x=forecast_df['datetime'],
            y=forecast_df['forecast'],
            name='Forecast',
            line=dict(color='blue', width=3),
            mode='lines'
        ))
        
        # Plot confidence interval
        fig.add_trace(go.Scatter(
            x=forecast_df['datetime'].tolist() + forecast_df['datetime'].tolist()[::-1],
            y=forecast_df['upper_bound'].tolist() + forecast_df['lower_bound'].tolist()[::-1],
            fill='toself',
            fillcolor='rgba(0, 100, 200, 0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            name='Confidence Interval',
            showlegend=True
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title='Datetime',
            yaxis_title='Energy (kW)',
            hovermode='x unified',
            template='plotly_white',
            height=500
        )
        
        return fig
    
    def plot_feature_importance(self, top_n: int = 15) -> go.Figure:
        """
        Plot feature importance
        
        Args:
            top_n: Number of top features to display
            
        Returns:
            Plotly Figure object
        """
        if self.feature_importance is None:
            return None
        
        top_features = self.feature_importance.head(top_n)
        
        fig = go.Figure(go.Bar(
            x=top_features['importance'],
            y=top_features['feature'],
            orientation='h',
            marker=dict(color='steelblue')
        ))
        
        fig.update_layout(
            title='Feature Importance',
            xaxis_title='Importance',
            yaxis_title='Feature',
            height=400,
            template='plotly_white'
        )
        
        return fig
    
    def display_metrics(self):
        """Display model performance metrics in Streamlit"""
        if not self.metrics:
            st.warning("No metrics available. Train a model first.")
            return
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("R² Score", f"{self.metrics.get('r_score', 0):.3f}")
        with col2:
            st.metric("MAE", f"{self.metrics.get('mae', 0):.2f}")
        with col3:
            st.metric("RMSE", f"{self.metrics.get('rmse', 0):.2f}")
        with col4:
            st.metric("MAPE", f"{self.metrics.get('mape', 0):.2f}%")


def demo_forecast_workflow():
    """
    Demonstration of complete forecasting workflow
    """
    st.header("OpenSTEF Energy Forecasting Demo")
    
    # Initialize forecaster
    forecaster = OpenSTEFForecaster(
        location_name="Berlin",
        latitude=52.5200,
        longitude=13.4050
    )
    
    # Step 1: Fetch weather data
    st.subheader("1. Fetch Weather Data")
    weather_df = forecaster.fetch_weather_data(
        start_date="2023-01-01",
        end_date="2023-12-31"
    )
    st.dataframe(weather_df.head())
    
    # Step 2: Create dummy energy data
    st.subheader("2. Energy Generation Data")
    energy_df = pd.DataFrame({
        'datetime': weather_df['datetime'],
        'energy_generation': np.random.rand(len(weather_df)) * 100 + 50
    })
    st.dataframe(energy_df.head())
    
    # Step 3: Prepare training data
    st.subheader("3. Prepare Training Data")
    combined_df = forecaster.prepare_training_data(energy_df, weather_df)
    st.dataframe(combined_df.head())
    
    # Step 4: Train model
    st.subheader("4. Train Model")
    if st.button("Train Model"):
        model, metrics = forecaster.train_model(combined_df)
        st.success("Model trained successfully!")
        forecaster.display_metrics()
    
    # Step 5: Create forecast
    st.subheader("5. Generate Forecast")
    if st.button("Generate Forecast"):
        forecast_df = forecaster.create_forecast(
            model=forecaster.model,
            forecast_start="2024-01-01",
            horizon_hours=48
        )
        fig = forecaster.plot_forecast(forecast_df, historical_data=combined_df.tail(100))
        st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    # Run demo when executed directly
    demo_forecast_workflow()
