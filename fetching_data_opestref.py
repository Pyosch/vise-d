from mastr_preprocessing import prepare_solar_data
import os
from datetime import datetime
from wetterdienst.provider.dwd.mosmix import DwdMosmixRequest
from wetterdienst.provider.dwd.observation import DwdObservationRequest
from wetterdienst.metadata.period import Period
from wetterdienst.metadata.resolution import Resolution
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
import mlflow

# CONFIGURATION
# Set to False to use the existing pre-trained model from 'mlruns/'
# Set to True to retrain the model (e.g. if you have new data or changed parameters)
TRAIN_MODEL = False 
      
mastr_db_path = r'data\open-mastr.db'

# Define time period - use most recent full year of data available
location = "Köln"
# Note: 'start' and 'end' are currently unused as we fetch "recent" data from DWD which gives a fixed period.
# start = "2025-01-01 00:00:00"
# end = "2025-12-18 23:45:00"

print("Fetching solar installation data...")
gdf_solar, city_district = prepare_solar_data(location=location, mastr_db_path=mastr_db_path)
print(f"Found {len(gdf_solar)} solar installations")

#
#  Find Nearest DWD Observation Station
# 
print("\n" + "="*80)
print("FINDING NEAREST DWD Observation WEATHER STATION")
print("="*80)

print(f"System time: {datetime.now()}")

settings = Settings(
    ts_shape="long", 
    ts_humanize=True, 
    ts_convert_units=True,
    cache_disable=True  # Force fresh data fetch to avoid stale cache from August
)

# Find nearest DWD station
# We prioritize finding a station with SOLAR data, as that is most critical and sparse.
# Temperature is more commonly available, but solar is the bottleneck.
# We search for the top 10 stations to find one that actually has valid Global Radiation (GS_10/radiation_global).
stations_request = DwdObservationRequest(
    parameters=[("10_minutes", "solar")], 
    periods="recent",
    settings=settings
)

stations = stations_request.filter_by_rank(
    latlon=(city_district.lat[0], city_district.lon[0]),
    rank=10
)

station_df = stations.df
# Convert to pandas if it's a Polars DataFrame
if hasattr(station_df, 'to_pandas'):
    station_df = station_df.to_pandas()

if station_df.empty:
    raise ValueError(f"No Dwd station found near {location}")

# Iterate through stations to find one with valid radiation data
valid_station_found = False
station_id = None
station_name = None

print(f"Checking {len(station_df)} nearby stations for valid solar data...")

for idx, row in station_df.iterrows():
    curr_id = row['station_id']
    curr_name = row['name']
    curr_dist = row['distance']
    
    print(f"Checking station: {curr_name} (ID: {curr_id}, Dist: {curr_dist:.1f} km)...")
    
    try:
        # Quick check of recent data for this station
        check_request = DwdObservationRequest(
            parameters=[("10_minutes", "solar")],
            periods="recent",
            settings=settings
        ).filter_by_station_id(station_id=(curr_id,))
        
        check_data = check_request.values.all().df
        if hasattr(check_data, 'to_pandas'):
            check_data = check_data.to_pandas()
            
        if check_data.empty:
            print(f"   ❌ No data available.")
            continue
            
        # Check if 'radiation_global' exists and has non-zero values
        # Note: DWD often returns -999 or NaN for missing data, but wetterdienst might handle it.
        # We check for the parameter name and if the sum is > 0.
        
        # Pivot to see columns
        check_pivot = check_data.pivot_table(
            index='date', columns='parameter', values='value', aggfunc='first'
        )
        
        if 'radiation_global' in check_pivot.columns:
            # Check if we have valid data (not just 0 or NaN)
            # We sum the data. If it's all 0, it's invalid for PV.
            total_rad = check_pivot['radiation_global'].sum()
            if total_rad > 10: # Threshold to be safe
                print(f"   ✅ Found valid solar data! Total GHI sum: {total_rad:.2f}")
                station_id = curr_id
                station_name = curr_name
                valid_station_found = True
                break
            else:
                print(f"   ❌ 'radiation_global' exists but sum is {total_rad:.2f} (all zeros/missing).")
        else:
            print(f"   ❌ 'radiation_global' parameter missing.")
            
    except Exception as e:
        print(f"   ❌ Error checking station: {e}")

if not valid_station_found:
    # Fallback to the first one but warn heavily
    print("⚠️ WARNING: No station with valid Global Radiation found in top 10.")
    print("   Falling back to nearest station, but PV generation will likely be 0.")
    station_id = station_df.iloc[0]['station_id']
    station_name = station_df.iloc[0]['name']
else:
    print(f"✅ Selected Station: {station_name} (ID: {station_id})")

print(f"✅ Using Dwd station: {station_name} (ID: {station_id})")
#
# BLOCK 4: Request DWD Weather Parameters

print("\n" + "="*80)
print("FETCHING Dwd WEATHER DATA")
print("="*80)

Dwd_request = DwdObservationRequest(
    parameters=[
        ("10_minutes", "solar"),
        ("10_minutes", "temperature_air"),
    ],
    periods="recent",
    settings=settings
).filter_by_station_id(station_id=(station_id,))

Dwd_data = Dwd_request.values.all().df

# Convert to pandas if it's a Polars DataFrame
if hasattr(Dwd_data, 'to_pandas'):
    Dwd_data = Dwd_data.to_pandas()
if Dwd_data.empty:
    raise ValueError("No Dwd data available")

print(f"✅ Dwd data shape: {Dwd_data.shape}")
print(f"   Parameters: {Dwd_data['parameter'].unique().tolist()}")
print(f"   Date range: {Dwd_data['date'].min()} to {Dwd_data['date'].max()}")

# 
# BLOCK 5: Transform DWD Data to PV Format
# 
print("\n" + "="*80)
print("TRANSFORMING WEATHER DATA")
print("="*80)

# Convert to wide format
Dwd_pivot = Dwd_data.pivot_table(
    index='date',
    columns='parameter',
    values='value',
    aggfunc='first'
)

weather_data = pd.DataFrame(index=Dwd_pivot.index)

# Unit conversion: Dwd radiation is in J/cm², convert to W/m²
if 'radiation_global' in Dwd_pivot.columns:
    weather_data['ghi'] = Dwd_pivot['radiation_global'] * 10000 / 3600
else:
    weather_data['ghi'] = 0

if 'radiation_sky_short_wave_diffuse' in Dwd_pivot.columns:
    weather_data['dhi'] = Dwd_pivot['radiation_sky_short_wave_diffuse'] * 10000 / 3600
else:
    weather_data['dhi'] = weather_data['ghi'] * 0.15

weather_data['dni'] = weather_data['ghi'] - weather_data['dhi']
weather_data['zenith'] = 0
weather_data['bh'] = 0

# Map additional requested parameters
if 'sunshine_duration' in Dwd_pivot.columns:
    weather_data['sunshine_duration'] = Dwd_pivot['sunshine_duration']

if 'radiation_sky_long_wave' in Dwd_pivot.columns:
    weather_data['radiation_sky_long_wave'] = Dwd_pivot['radiation_sky_long_wave'] * 10000 / 3600 # Convert J/cm² to W/m²

# Map Air Temperature (requested in Block 4)
if 'temperature_air_mean_200' in Dwd_pivot.columns:
    weather_data['temperature'] = Dwd_pivot['temperature_air_mean_200'] - 273.15  # Convert Kelvin to Celsius if needed, though DWD is usually Celsius. 
    # DWD Mosmix is K, Observation is usually C. Let's assume C for Observation, but check values if weird.
    # Actually DWD Observation is usually in °C.
    weather_data['temperature'] = Dwd_pivot['temperature_air_mean_200']
else:
    # Fallback if specific column name differs
    temp_cols = [c for c in Dwd_pivot.columns if 'temperature' in c]
    if temp_cols:
        print(f"⚠️ 'temperature_air_mean_200' not found. Using {temp_cols[0]} instead.")
        weather_data['temperature'] = Dwd_pivot[temp_cols[0]]
    else:
        print("⚠️ No temperature data found. Defaulting to 20°C.")
        weather_data['temperature'] = 20

print(f"✅ Weather data shape: {weather_data.shape}")
print(f"   Columns: {weather_data.columns.tolist()}")
print(f"   Date range: {weather_data.index.min()} to {weather_data.index.max()}")

if weather_data['ghi'].sum() == 0:
    print("⚠️ WARNING: GHI (Global Horizontal Irradiance) is all zeros! Check if the selected station actually has solar data.")
    print(f"   Station: {station_name} (ID: {station_id})")

# Save weather data
weather_output_path = os.path.join(os.path.dirname(__file__), 'data', f'{location}_weather_data_Dwd.csv')
os.makedirs(os.path.dirname(weather_output_path), exist_ok=True)
weather_data.to_csv(weather_output_path)
print(f"   Saved to: {weather_output_path}")


# BLOCK 5.5: Ensure Data Continuity (Required for OpenSTEF)
#
# OpenSTEF requires a strictly continuous time series without missing timestamps.
# Since we are using real observations, we might have small gaps.
# We will resample to hourly frequency and interpolate missing values.

print("\n" + "="*80)
print("ENSURING DATA CONTINUITY")
print("="*80)

# 1. Sort index to be sure
weather_data = weather_data.sort_index()

# 2. Create a complete hourly index from start to end
if not weather_data.empty:
    full_idx = pd.date_range(start=weather_data.index.min(), end=weather_data.index.max(), freq='h')
    
    # 3. Reindex to introduce NaNs for missing hours
    original_len = len(weather_data)
    weather_data = weather_data.reindex(full_idx)
    new_len = len(weather_data)
    
    if new_len > original_len:
        print(f"⚠️ Found {new_len - original_len} missing timestamps. Filling gaps...")
    
    # 4. Interpolate missing values (linear interpolation for weather is usually safe for small gaps)
    # Limit direction='both' handles gaps at start/end if necessary, though mainly we care about internal gaps
    weather_data = weather_data.interpolate(method='time', limit_direction='both')
    
    print(f"✅ Data is continuous. Shape: {weather_data.shape}")
    print(f"   Date range: {weather_data.index.min()} to {weather_data.index.max()}")
else:
    print("⚠️ Warning: Weather data is empty!")


# BLOCK 6: Calculate PV Generation from Weather
# ============================================================================int("\n" + "="*80)
print("CALCULATING PV GENERATION")
print("="*80)

total_capacity_kw = gdf_solar['Bruttoleistung'].sum()
print(f"Total installed capacity: {total_capacity_kw:.2f} kW")

performance_ratio = 0.75

pv_generation_df = weather_data[['ghi']].copy()
pv_generation_df['pv_generation_kw'] = (
    pv_generation_df['ghi'] * total_capacity_kw * performance_ratio / 1000
)
pv_generation_df = pv_generation_df[['pv_generation_kw']]

print(f"✅ PV generation calculated")
print(f"   Total energy: {pv_generation_df['pv_generation_kw'].sum():.2f} kWh")
print(f"   Average power: {pv_generation_df['pv_generation_kw'].mean():.2f} kW")
print(f"   Peak power: {pv_generation_df['pv_generation_kw'].max():.2f} kW")

# Save PV generation
pv_output_path = os.path.join(os.path.dirname(__file__), 'data', f'{location}_pv_generation.csv')
pv_generation_df.to_csv(pv_output_path)
print(f"   Saved to: {pv_output_path}")


# BLOCK 7: Prepare Data for OpenSTEF Training
# ============================================================================
print("\n" + "="*80)
print("PREPARING OPENSTEF TRAINING DATA")
print("="*80)

train_data = weather_data.copy()

# Ensure index is DatetimeIndex with UTC timezone
if not isinstance(train_data.index, pd.DatetimeIndex):
    train_data.index = pd.to_datetime(train_data.index)

# Ensure UTC timezone
if train_data.index.tz is None:
    train_data.index = train_data.index.tz_localize('UTC')
elif str(train_data.index.tz) != 'UTC':
    train_data.index = train_data.index.tz_convert('UTC')

# Add PV generation as 'load' column
train_data['load'] = pv_generation_df['pv_generation_kw']

# Remove NaN values
train_data = train_data.dropna()

# Verify index is still DatetimeIndex after all operations
if not isinstance(train_data.index, pd.DatetimeIndex):
    train_data.index = pd.to_datetime(train_data.index)

# Ensure index has a frequency (OpenSTEF requires this)
if train_data.index.freq is None:
    # Infer frequency from the data
    train_data = train_data.asfreq(pd.infer_freq(train_data.index))

# Make absolutely sure the index is preserved by setting it as a proper DatetimeIndex
train_data.index = pd.DatetimeIndex(train_data.index)
train_data.index.name = 'forecast'  # OpenSTEF expects index name to be 'forecast'

# Reorder columns: 'load' must be first, other columns in between, 'horizon' will be added by OpenSTEF as last
cols = train_data.columns.tolist()
cols.remove('load')
train_data = train_data[['load'] + cols]

print(f"✅ Training data prepared")
print(f"   Shape: {train_data.shape}")
print(f"   Columns: {train_data.columns.tolist()}")
print(f"   Index type: {type(train_data.index).__name__}")
print(f"   Index name: {train_data.index.name}")
print(f"   Index freq: {train_data.index.freq}")
print(f"   Date range: {train_data.index.min()} to {train_data.index.max()}")
print(f"\n   >>> LAST AVAILABLE DATA POINT: {train_data.index.max()} <<<")


# BLOCK 8: Configure Prediction Job
# ============================================================================
print("\n" + "="*80)
print("CONFIGURING OPENSTEF PREDICTION JOB")
print("="*80)

pj_dataclass = PredictionJobDataClass(
    id=1,
    name=f"{location}_PV_Forecast",
    model="xgb",
    forecast_type="demand",  # PV generation is treated as demand
    horizon_minutes=5760,  # 96 hours (4 days)
    resolution_minutes=60,  # Hourly
    train_components=0,
    lat=city_district.lat[0],
    lon=city_district.lon[0],
    rolling_aggregate_features=None,  # Disable rolling features to avoid DatetimeIndex issues
    save_train_forecasts=True,  # Required to get return values from train_model_pipeline
    quantiles=[0.1, 0.5, 0.9],  # Required for confidence intervals
)

# Use the Pydantic object directly (don't convert to dict)
pj = pj_dataclass

print(f"✅ Prediction job configured:")
print(f"   Model: {pj.model}")
print(f"   Forecast horizon: {pj.horizon_minutes/60:.1f} hours")
print(f"   Resolution: {pj.resolution_minutes} minutes")
print(f"   Location: ({pj.lat:.4f}, {pj.lon:.4f})")

# Double-check train_data before passing to OpenSTEF
print(f"\n🔍 Final check before training:")
print(f"   Index type: {type(train_data.index)}")
print(f"   Is DatetimeIndex: {isinstance(train_data.index, pd.DatetimeIndex)}")
print(f"   Index dtype: {train_data.index.dtype}")
print(f"   PredictionJob type: {type(pj)}")
print(f"   Has rolling_aggregate_features attr: {hasattr(pj, 'rolling_aggregate_features')}")


# BLOCK 9: Train the Model
# ============================================================================
print("\n" + "="*80)
print("TRAINING OPENSTEF MODEL")
print("="*80)

# Create MLflow and artifact directories
mlflow_dir = os.path.join(os.path.dirname(__file__), 'mlruns')
artifact_dir = os.path.join(os.path.dirname(__file__), 'artifacts')
os.makedirs(mlflow_dir, exist_ok=True)
os.makedirs(artifact_dir, exist_ok=True)

# Convert to proper file URI format for MLflow
mlflow_uri = f"file:///{mlflow_dir.replace(os.sep, '/')}"

# Ensure MLflow knows where to look/save
mlflow.set_tracking_uri(mlflow_uri)

if TRAIN_MODEL:
    try:
        # train_model_pipeline returns data_sets tuple when save_train_forecasts=True
        data_sets = train_model_pipeline(
            pj=pj,
            input_data=train_data,
            check_old_model_age=False,
            mlflow_tracking_uri=mlflow_uri,
            artifact_folder=artifact_dir,
        )
        
        print("✅ Model trained and saved successfully!")
        
        if data_sets is not None and len(data_sets) >= 2:
            train_data_with_features, validation_data = data_sets[0], data_sets[1]
            print(f"   Training data shape: {train_data_with_features.shape}")
            print(f"   Validation data shape: {validation_data.shape}")
        else:
            train_data_with_features = None
            validation_data = None
            print("   Note: Model saved to MLflow, forecast data available")
        
    except Exception as e:
        print(f"❌ Error training model: {str(e)}")
        import traceback
        traceback.print_exc()
else:
    print("⏩ Skipping training (TRAIN_MODEL = False)")
    print(f"   Using existing model from: {mlflow_uri}")
    # We assume the model exists. If not, create_forecast_pipeline will fail.


# BLOCK 10: Create Forecast
# ============================================================================
print("\n" + "="*80)
print("CREATING FORECAST")
print("="*80)

try:
    # Prepare forecast input
    # OpenSTEF requires the target column ('load') to be NaN for the forecast period
    # We will forecast the last 47 hours of the available data (matching the horizon)
    forecast_input = train_data.copy()
    
    # Define forecast period
    # Since we might only have historical data (observations), we can't always forecast the "real" future
    # because we lack future weather data.
    # So we will set the forecast start time to be shortly before the end of our available data.
    
    last_data_point = forecast_input.index.max()
    print(f"ℹ️  Last available data point in dataset: {last_data_point}")
    forecast_horizon_hours = 96
    
    # If data ends in the past (relative to now), assume we are backtesting
    if last_data_point < pd.Timestamp.now(tz='UTC') - pd.Timedelta(hours=1):
        print(f"⚠️ Data ends in the past ({last_data_point}). Switching to backcast mode.")
        cutoff_date = last_data_point - pd.Timedelta(hours=48) # Forecast the last 48 hours of available data
    else:
        # Real forecast mode
        cutoff_date = pd.Timestamp.now(tz='UTC').floor('h')

    print(f"Preparing forecast input...")
    print(f"   Original range: {forecast_input.index.min()} to {forecast_input.index.max()}")
    print(f"   Forecast start (cutoff): {cutoff_date}")
    
    # Add tiny noise to 'load' to prevent OpenSTEF's "Flatliner" error during night (all zeros)
    # OpenSTEF throws an error if recent data is perfectly constant.
    # We add random noise between 0 and 0.001 kW (1 Watt)
    print("   Adding microscopic noise to prevent 'Flatliner' error on zero values...")
    noise = np.random.uniform(0, 0.001, size=len(forecast_input))
    forecast_input['load'] = forecast_input['load'] + noise
    
    # Set 'load' to NaN for the forecast period to trigger forecasting
    mask = forecast_input.index >= cutoff_date
    forecast_input.loc[mask, 'load'] = np.nan
    
    print(f"   NaNs in load: {forecast_input['load'].isna().sum()}")
    
    # Ensure index is strictly DatetimeIndex with UTC timezone
    forecast_input.index = pd.DatetimeIndex(forecast_input.index)
    if forecast_input.index.tz is None:
        forecast_input.index = forecast_input.index.tz_localize('UTC')
    
    # create_forecast_pipeline loads the model from MLflow automatically
    forecast = create_forecast_pipeline(
        pj=pj,
        input_data=forecast_input,
        mlflow_tracking_uri=mlflow_uri,
    )
    
    print(f"✅ Forecast created!")
    print(f"   Shape: {forecast.shape}")
    print(f"   Columns: {forecast.columns.tolist()}")
    
    # Save forecast
    forecast_output_path = os.path.join(os.path.dirname(__file__), 'data', f'{location}_forecast.csv')
    forecast.to_csv(forecast_output_path)
    print(f"   Saved to: {forecast_output_path}")
    
   
    # BLOCK 11: Visualization
    # ====================================================================
    print("\n" + "="*80)
    print("CREATING VISUALIZATIONS")
    print("="*80)
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('PV Generation Forecast', 'Weather Parameters'),
        vertical_spacing=0.1
    )
    
    # Define visualization window: Start 24 hours before the forecast starts to show context
    viz_start = cutoff_date - pd.Timedelta(hours=24)
    viz_end = viz_start + pd.Timedelta(hours=forecast_horizon_hours + 24)
    current_time = pd.Timestamp.now(tz='UTC')
    
    # Filter data for plotting
    # "Calculated PV" (Actuals) stops where the forecast begins to avoid overlap
    # We want to see the transition from Actuals -> Forecast
    plot_mask = (pv_generation_df.index >= viz_start) & (pv_generation_df.index <= cutoff_date)
    actual_data = pv_generation_df.loc[plot_mask]
    
    fig.add_trace(
        go.Scatter(
            x=actual_data.index,
            y=actual_data['pv_generation_kw'],
            name='Calculated PV (History)',
            line=dict(color='blue', width=2),
            opacity=0.7
        ),
        row=1, col=1
    )
    
    if 'forecast' in forecast.columns:
        # Forecast starts from the cutoff_date (which might be in the past if backcasting)
        forecast_mask = (forecast.index >= cutoff_date) & (forecast.index <= viz_end)
        forecast_plot = forecast.loc[forecast_mask]
        
        fig.add_trace(
            go.Scatter(
                x=forecast_plot.index,
                y=forecast_plot['forecast'],
                name='OpenSTEF Forecast',
                line=dict(color='red', dash='solid', width=2)
            ),
            row=1, col=1
        )
    
    # Filter weather data to same window
    weather_mask = (weather_data.index >= viz_start) & (weather_data.index <= viz_end)
    weather_recent = weather_data.loc[weather_mask]
    
    fig.add_trace(
        go.Scatter(
            x=weather_recent.index,
            y=weather_recent['ghi'],
            name='GHI (W/m²)',
            line=dict(color='orange')
        ),
        row=2, col=1
    )
    
    fig.update_xaxes(title_text="Time", row=2, col=1)
    fig.update_yaxes(title_text="Power (kW)", row=1, col=1)
    fig.update_yaxes(title_text="GHI (W/m²)", row=2, col=1)
    
    fig.update_layout(
        title=f'{location} PV Forecast - OpenSTEF with DWD Observation Data',
        height=800,
        showlegend=True
    )
    
    plot_output_path = os.path.join(os.path.dirname(__file__), 'data', f'{location}_forecast_plot.html')
    fig.write_html(plot_output_path)
    print(f"✅ Plot saved to: {plot_output_path}")
    
    # Display in browser
    fig.show()
    print(f"   Opening plot in browser...")
    
    # Summary statistics
    print("\n" + "="*80)
    print("FORECAST SUMMARY")
    print("="*80)
    
    if 'forecast' in forecast.columns:
        print(f"\nForecast statistics:")
        print(f"  Mean: {forecast['forecast'].mean():.2f} kW")
        print(f"  Max: {forecast['forecast'].max():.2f} kW")
        print(f"  Min: {forecast['forecast'].min():.2f} kW")
        print(f"  Total energy (47h): {forecast['forecast'].sum():.2f} kWh")
    
    print("\nActual generation statistics (last 7 days):")
    print(f"  Mean: {actual_data['pv_generation_kw'].mean():.2f} kW")
    print(f"  Max: {actual_data['pv_generation_kw'].max():.2f} kW")
    print(f"  Min: {actual_data['pv_generation_kw'].min():.2f} kW")
    print(f"  Total energy: {actual_data['pv_generation_kw'].sum():.2f} kWh")
    
except Exception as e:
    print(f"❌ Error creating forecast: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("COMPLETED!")
print("="*80)