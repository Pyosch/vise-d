from mastr_preprocessing import prepare_solar_data
import os
from wetterdienst.provider.dwd.observation import DwdObservationRequest
from wetterdienst import Settings
import pandas as pd
import numpy as np
import pvlib
from vpplib import Environment
from mastr_energy_generation import pick_pvsystem_mastr, prepare_pv_time_series_mastr, aggregate_pv_time_series
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from openstef.data_classes.prediction_job import PredictionJobDataClass
from openstef.pipeline.train_model import train_model_pipeline
from openstef.pipeline.create_forecast import create_forecast_pipeline
from openstef.model.serializer import MLflowSerializer
from openstef.validation import validation
      
mastr_db_path = r'C:\Users\mashu\.open-MaStR\data\sqlite\open-mastr.db'

# Define time period - full year for forecasting
location = "Berlin"  # German name for Cologne
start = "2025-01-01 00:00:00"
end = "2025-12-31 23:45:00"

print("Fetching solar installation data...")
gdf_solar, city_district = prepare_solar_data(location=location, mastr_db_path=mastr_db_path)
print(f"Found {len(gdf_solar)} solar installations")

print("Fetching weather data from DWD...")
ref_env = Environment(start=start, end=end)
ref_env.get_dwd_pv_data(lat=city_district.lat[0], lon=city_district.lon[0])
print(f"Weather data shape: {ref_env.pv_data.shape}")

# Save the weather data to CSV
weather_output_path = os.path.join(os.path.dirname(__file__), 'data', f'{location}_weather_data.csv')
os.makedirs(os.path.dirname(weather_output_path), exist_ok=True)
ref_env.pv_data.to_csv(weather_output_path)
print(f"Weather data saved to: {weather_output_path}")

# Save solar installation data
solar_output_path = os.path.join(os.path.dirname(__file__), 'data', f'{location}_solar_installations.csv')
gdf_solar.to_csv(solar_output_path, index=False)
print(f"Solar installations saved to: {solar_output_path}")

# Calculate simple PV generation from weather data and total capacity
print("\nCalculating aggregate PV generation...")

# Get total installed capacity
total_capacity_kw = gdf_solar['Bruttoleistung'].sum()
print(f"Total installed capacity: {total_capacity_kw:.2f} kW")

# Simple PV generation calculation using GHI and a performance ratio
performance_ratio = 0.75  # Typical PR for PV systems

# Create generation dataframe directly from weather data
pv_generation_df = ref_env.pv_data[['ghi']].copy()
pv_generation_df['pv_generation_kw'] = (
    pv_generation_df['ghi'] * total_capacity_kw * performance_ratio / 1000
)
pv_generation_df = pv_generation_df[['pv_generation_kw']]  # Keep only generation column

print(f"\nPV generation data shape: {pv_generation_df.shape}")

# Save to CSV
pv_output_path = os.path.join(os.path.dirname(__file__), 'data', f'{location}_pv_generation.csv')
pv_generation_df.to_csv(pv_output_path)
print(f"PV generation data saved to: {pv_output_path}")

print("\nPV generation preview:")
print(pv_generation_df.head(10))
print(f"\nMax generation: {pv_generation_df['pv_generation_kw'].max():.2f} kW")
print(f"Total annual energy: {pv_generation_df['pv_generation_kw'].sum() * 0.25:.2f} kWh")

# 0.25 for 15-min intervals

# Prepare data for OpenSTEF training
print("\n" + "="*60)
print("PREPARING DATA FOR OPENSTEF TRAINING")
print("="*60)

# Create MLflow and artifact directories (moved outside try block so accessible everywhere)
mlflow_dir = os.path.join(os.path.dirname(__file__), 'mlruns')
artifact_dir = os.path.join(os.path.dirname(__file__), 'artifacts')
os.makedirs(mlflow_dir, exist_ok=True)
os.makedirs(artifact_dir, exist_ok=True)

# Convert to proper file URI format for MLflow
mlflow_uri = f"file:///{mlflow_dir.replace(os.sep, '/')}"

# Create prediction job
pj = dict(
    model = "xgb",
    id = 308,
    quantiles = [0.10,0.30,0.50,0.70,0.90],
    forecast_type = "demand",
    lat = city_district.lat[0],
    lon = city_district.lon[0],
    resolution_minutes = 15,
    name = "berlin_pv_forecast",
    save_train_forecasts = True)

pj = PredictionJobDataClass(**pj)

# Prepare training data in OpenSTEF format
train_data = ref_env.pv_data.copy()

# Convert index to timezone-aware (UTC) - required by OpenSTEF
train_data.index = train_data.index.tz_localize('UTC')

# Also make pv_generation_df timezone-aware and align indices
pv_generation_df.index = pv_generation_df.index.tz_localize('UTC')

# Remove duplicate timestamps (keep first occurrence) from both datasets
if train_data.index.duplicated().any():
    num_duplicates = train_data.index.duplicated().sum()
    print(f"Warning: Found {num_duplicates} duplicate timestamps, removing them...")
    train_data = train_data[~train_data.index.duplicated(keep='first')]
    # Also remove from pv_generation_df to keep them aligned
    pv_generation_df = pv_generation_df[~pv_generation_df.index.duplicated(keep='first')]

# Align both dataframes on the same index
train_data, pv_generation_df = train_data.align(pv_generation_df, join='inner', axis=0)

# Add load column as FIRST column (required by OpenSTEF)
train_data.insert(0, 'load', pv_generation_df['pv_generation_kw'].values)

# Note: Do NOT add time-based features manually - OpenSTEF will generate them automatically
#  print(f"Training data shape: {train_data.shape}")
# print(f"Training data columns: {train_data.columns.tolist()}")
# print(f"\nTraining data preview:")
# print(train_data.head())

# # Train the model
# print("\n" + "="*60)
# print("TRAINING MODEL")
# print("="*60)

try:
    model_specs, model, report = train_model_pipeline(
        pj=pj,
        input_data=train_data,
        check_old_model_age=False,
        mlflow_tracking_uri=mlflow_uri,
        artifact_folder=artifact_dir,
    )
    
    print("\n✓ Model training completed successfully!")
    print(f"\nModel Performance Metrics:")
    # Extract metrics from report object (may be nested in 'metrics' or directly accessible)
    metrics = report if isinstance(report, dict) else (report.metrics if hasattr(report, 'metrics') else {})
    print(f"  R² Score: {metrics.get('r_score', metrics.get('r2', 'N/A'))}")
    print(f"  MAE: {metrics.get('mae', 'N/A')}")
    print(f"  RMSE: {metrics.get('rmse', 'N/A')}")
    print(f"  MAPE: {metrics.get('mape', 'N/A')}")
    
    # Save model
    model_output_path = os.path.join(os.path.dirname(__file__), 'data', f'{location}_trained_model.pkl')
    import pickle
    with open(model_output_path, 'wb') as f:
        pickle.dump(model, f)
    print(f"\nModel saved to: {model_output_path}")
    
    # Save training metadata for dashboard integration
    metadata = {
        'training_date': pd.Timestamp.now().isoformat(),
        'location': location,
        'total_capacity_kw': float(total_capacity_kw),
        'training_period_start': start,
        'training_period_end': end,
        'num_installations': len(gdf_solar),
        'model_id': pj.id,
        'resolution_minutes': pj.resolution_minutes,
        'metrics': metrics if isinstance(metrics, dict) else {},
        'mlflow_experiment_id': str(pj.id)
    }
    
    metadata_path = os.path.join(os.path.dirname(__file__), 'data', f'{location}_model_metadata.json')
    import json
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Model metadata saved to: {metadata_path}")
    
    # FORECASTING PART
    print("\n" + "="*60)
    print("GENERATING FORECAST")
    print("="*60)
    
    # OpenSTEF forecasting: Provide historical + future data with NaN in load column for forecast period
    # The model predicts where load is NaN
    
    lookback_hours = 24 * 7  # 1 week of context
    forecast_horizon_hours = 47  # Forecast 47 hours ahead
    
    # Step 1: Get recent historical data (last week with actual load values)
    lookback_steps = int(lookback_hours * 4)  # 15-min intervals
    historical_part = train_data.tail(lookback_steps).copy()
    
    # Step 2: Create future time index for forecast - start immediately after last data point
    last_timestamp = train_data.index[-1]
    
    forecast_steps = int(forecast_horizon_hours * 4)  # 15-min intervals
    future_index = pd.date_range(
        start=last_timestamp + pd.Timedelta(minutes=15),
        periods=forecast_steps,
        freq='15min',
        tz='UTC'
    )
    
    # Step 3: Create forecast dataframe with NaN load (this is what gets predicted)
    future_part = pd.DataFrame(index=future_index)
    future_part['load'] = np.nan  # NaN = forecast target
    
    # Step 4: Add weather features using historical pattern from recent similar periods
    # For each forecast hour, use weather from 1-7 days ago at the same time of day
    print("Building forecast weather from historical patterns...")
    
    for i, future_ts in enumerate(future_index):
        # Try multiple days back to find valid weather data
        weather_found = False
        
        for days_back in range(1, 8):  # Try 1-7 days back
            past_ts = future_ts - pd.Timedelta(days=days_back)
            
            # Handle year boundary: if past_ts is before our data, use same day-of-year from training year
            if past_ts < train_data.index[0]:
                # Use same day and time from the training year
                past_ts = past_ts.replace(year=train_data.index[0].year)
            
            # Find closest historical data point
            if past_ts in train_data.index:
                past_row = train_data.loc[past_ts]
                weather_found = True
            else:
                # Find nearest timestamp within +/- 1 hour
                time_window = train_data.loc[
                    (train_data.index >= past_ts - pd.Timedelta(hours=1)) & 
                    (train_data.index <= past_ts + pd.Timedelta(hours=1))
                ]
                if not time_window.empty:
                    past_row = time_window.iloc[0]
                    weather_found = True
            
            if weather_found:
                # Copy weather features from historical data
                for col in ['ghi', 'dhi', 'dni', 'bh', 'zenith']:
                    if col in train_data.columns and pd.notna(past_row[col]):
                        future_part.loc[future_ts, col] = past_row[col]
                break
        
        if not weather_found and i > 0:
            # Fallback: copy from previous forecast timestep
            for col in ['ghi', 'dhi', 'dni', 'bh', 'zenith']:
                if col in future_part.columns:
                    future_part.loc[future_ts, col] = future_part.iloc[i-1][col]
    
    # Step 5: Combine historical + future
    forecast_input = pd.concat([historical_part, future_part], axis=0)
    
    print(f"Input data range: {forecast_input.index[0]} to {forecast_input.index[-1]}")
    print(f"  - Historical (with load): {len(historical_part)} rows")
    print(f"  - Forecast (NaN load): {len(future_part)} rows")
    print(f"  - Total input: {forecast_input.shape}")
    
    # Generate forecast using OpenSTEF
    try:
        # OpenSTEF's create_forecast_pipeline loads the model from MLflow automatically
        # Use the same MLflow URI that was used during training
        forecast = create_forecast_pipeline(
            pj=pj,
            input_data=forecast_input,
            mlflow_tracking_uri=mlflow_uri
        )
        
        print("\n✓ Forecast generated successfully!")
        print(f"Forecast shape: {forecast.shape}")
        
        # Save forecast
        forecast_output_path = os.path.join(os.path.dirname(__file__), 'data', f'{location}_forecast.csv')
        forecast.to_csv(forecast_output_path)
        print(f"Forecast saved to: {forecast_output_path}")
        
        print("\nForecast preview:")
        print(forecast.head(10))
        
        if 'forecast' in forecast.columns:
            # Check if forecast has valid values
            valid_forecast = forecast['forecast'].dropna()
            if len(valid_forecast) > 0:
                print(f"\nForecast statistics:")
                print(f"  Mean: {valid_forecast.mean():.2f} kW")
                print(f"  Max: {valid_forecast.max():.2f} kW")
                print(f"  Min: {valid_forecast.min():.2f} kW")
                print(f"  Valid predictions: {len(valid_forecast)}/{len(forecast)}")
            else:
                print(f"\n⚠️ Warning: Forecast contains only NaN values")
                print(f"   This may be due to using persistence weather data (constant values)")
                print(f"   OpenSTEF removed constant load values as suspicious data")
        
        # VISUALIZATION
        print("\n" + "="*60)
        print("CREATING VISUALIZATION")
        print("="*60)
        
        try:
            # Prepare data for visualization
            # Get last 7 days of historical data for context
            lookback_hours = 7 * 24  # 7 days
            lookback_steps = int(lookback_hours * 60 / 15)  # Convert to 15-min intervals
            historical_subset = pv_generation_df.tail(lookback_steps).copy()
            historical_subset = historical_subset.reset_index()
            historical_subset.columns = ['datetime', 'actual']
            
            print(f"Historical data for plot: {len(historical_subset)} rows")
            
            # Prepare forecast data
            forecast_data = forecast.copy()
            if 'forecast' not in forecast_data.columns:
                # If forecast doesn't have the expected column, use the first numeric column
                numeric_cols = forecast_data.select_dtypes(include=['float64', 'int64']).columns
                if len(numeric_cols) > 0:
                    forecast_data['forecast'] = forecast_data[numeric_cols[0]]
                    print(f"Using column '{numeric_cols[0]}' as forecast")
            
            forecast_data = forecast_data.reset_index()
            if 'datetime' not in forecast_data.columns:
                forecast_data.columns = ['datetime'] + list(forecast_data.columns[1:])
            
            print(f"Forecast data for plot: {len(forecast_data)} rows")
            print(f"Forecast columns: {forecast_data.columns.tolist()}")
        
            # Create interactive Plotly figure
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
                x=forecast_data['datetime'],
                y=forecast_data['forecast'],
                name='Forecast',
                line=dict(color='#A23B72', width=3, dash='dash'),
                mode='lines',
                hovertemplate='<b>Forecast</b><br>Time: %{x}<br>Power: %{y:.2f} kW<extra></extra>'
            ))
        
            # Add confidence intervals if available
            if 'forecast_lower' in forecast_data.columns and 'forecast_upper' in forecast_data.columns:
                # Upper bound
                fig.add_trace(go.Scatter(
                    x=forecast_data['datetime'].tolist() + forecast_data['datetime'].tolist()[::-1],
                    y=forecast_data['forecast_upper'].tolist() + forecast_data['forecast_lower'].tolist()[::-1],
                    fill='toself',
                    fillcolor='rgba(162, 59, 114, 0.2)',
                    line=dict(color='rgba(255,255,255,0)'),
                    name='90% Confidence Interval',
                    showlegend=True,
                    hoverinfo='skip'
                ))
        
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
        
            # Display plot in browser window
            fig.show()
            print(f"\n✓ Interactive plot displayed in browser!")
            
            # Also save to file for later viewing
            plot_output_path = os.path.join(os.path.dirname(__file__), 'data', f'{location}_forecast_plot.html')
            fig.write_html(plot_output_path)
            print(f"✓ Plot also saved to: {plot_output_path}")
                
        except Exception as viz_error:
            print(f"\n✗ Error creating visualization: {str(viz_error)}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"\n✗ Error generating forecast: {str(e)}")
        import traceback
        traceback.print_exc()
    
except Exception as e:
    print(f"\n✗ Error training model: {str(e)}")
    import traceback
    traceback.print_exc()

        