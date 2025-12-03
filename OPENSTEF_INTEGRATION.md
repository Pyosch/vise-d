# OpenSTEF Integration Guide for VISE-D Dashboard

## Table of Contents
1. [What is OpenSTEF?](#what-is-openstef)
2. [Key Features](#key-features)
3. [Integration Architecture](#integration-architecture)
4. [Data Requirements](#data-requirements)
5. [Implementation Details](#implementation-details)
6. [Usage Workflow](#usage-workflow)

---

## What is OpenSTEF?

**OpenSTEF** (Open Short-Term Energy Forecasting) is a Python package developed for generating short-term forecasts in the energy sector. It provides a complete machine learning pipeline for time-series forecasting of energy data.

### Core Capabilities:
- **Short-term forecasting** (15 minutes to 48 hours ahead)
- **Automated ML pipelines** with model selection
- **Multiple ML algorithms**: XGBoost, LightGBM, Random Forest, Linear models
- **Feature engineering**: Automatic creation of time-based and weather-related features
- **Model validation**: Backtesting and cross-validation
- **Component splitting**: Split net load into components using DAZLS (Domain Adaptation for Zero-shot Learning in Sequence)

### License:
Mozilla Public License 2.0 (MPL-2.0)

---

## Key Features

### 1. **Machine Learning Models**
- XGBoost (primary model)
- LightGBM
- Random Forest
- Linear Regression
- Quantile Regression for uncertainty estimation

### 2. **Feature Engineering**
OpenSTEF automatically creates features from:
- **Time features**: hour, day of week, month, holidays
- **Weather features**: temperature, radiation, wind speed
- **Lag features**: historical load values
- **Rolling statistics**: moving averages, trends

### 3. **Prediction Types**
- **Point forecasts**: Single value predictions
- **Probabilistic forecasts**: Prediction intervals (P10, P50, P90)
- **Component forecasts**: Split total load into solar, wind, baseload

---

## Integration Architecture

### Data Flow

```
┌─────────────────────┐
│   Wetterdienst      │
│   (DWD Weather)     │
└──────────┬──────────┘
           │
           │ Fetch weather data
           │ (temperature, radiation,
           │  wind, pressure)
           ▼
┌─────────────────────┐
│  Data Preparation   │
│  - Merge weather    │
│  - Create features  │
│  - Handle missing   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   OpenSTEF          │
│   - Train model     │
│   - Make forecast   │
│   - Validate        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Dashboard Display  │
│  - Forecast plots   │
│  - Model metrics    │
│  - Feature import.  │
└─────────────────────┘
```

### Integration Points

1. **Weather Data Source**: Wetterdienst (already integrated in your project via vpplib)
2. **Energy Data**: Your MaStR solar/wind generation data
3. **Forecasting Engine**: OpenSTEF
4. **Visualization**: Streamlit dashboard

---

## Data Requirements

### Input Data Format

OpenSTEF requires a pandas DataFrame with the following structure:

| Column | Type | Description | Required |
|--------|------|-------------|----------|
| `datetime` | datetime | Timestamp (UTC preferred) | ✅ Yes |
| `load` | float | Energy value to forecast (MW/kW) | ✅ Yes |
| `temperature` | float | Temperature (°C) | ⭐ Recommended |
| `radiation` | float | Solar radiation (W/m²) | ⭐ For solar |
| `windspeed_100m` | float | Wind speed at 100m (m/s) | ⭐ For wind |
| `humidity` | float | Relative humidity (%) | ⚪ Optional |
| `pressure` | float | Air pressure (hPa) | ⚪ Optional |
| `clouds` | float | Cloud cover (%) | ⚪ Optional |

### Minimum Data Requirements

- **Training period**: At least **3 months** of historical data
- **Optimal period**: **1-2 years** for seasonal patterns
- **Resolution**: 15-min, hourly, or daily
- **Completeness**: <10% missing values (OpenSTEF can handle some gaps)

---

## Implementation Details

### 1. Wetterdienst Data Fetching

Your project already uses Wetterdienst in `vpplib/environment.py`:

```python
from wetterdienst.provider.dwd.observation import DwdObservationRequest
```

For OpenSTEF integration, we'll fetch:
- **Hourly temperature** (for load correlation)
- **Solar radiation** (for PV forecasting)
- **Wind speed** (for wind forecasting)
- **Pressure, humidity** (additional features)

### 2. OpenSTEF Pipeline Components

#### a) Data Preparation
```python
from openstef.data_classes.prediction_job import PredictionJobDataClass
from openstef.pipeline.train_model import train_model_pipeline
from openstef.pipeline.create_forecast import create_forecast_pipeline
```

#### b) Model Training
- Automatically selects best model from ensemble
- Performs hyperparameter optimization
- Validates using cross-validation

#### c) Forecasting
- Creates 48-hour ahead forecasts
- Provides prediction intervals
- Updates predictions as new data arrives

### 3. Dashboard Integration

New tab: **"Energy Forecasting (OpenSTEF)"**

**Features:**
- Select data source (Solar, Wind, or Combined)
- Select location from MaStR database
- Configure forecast horizon (6h, 12h, 24h, 48h)
- Train new model or use existing
- View forecast plots with confidence intervals
- Display model performance metrics (MAE, RMSE, R²)
- Feature importance analysis

---

## Usage Workflow

### Step-by-Step Process

#### 1. **Data Collection**
```python
# Fetch historical energy generation from MaStR
energy_data = prepare_solar_data(location="Berlin", mastr_db_path=mastr_db_path)

# Fetch weather data from Wetterdienst
weather_data = fetch_dwd_weather(
    lat=52.5200, 
    lon=13.4050,
    start_date="2023-01-01",
    end_date="2024-12-31"
)

# Merge datasets
combined_data = merge_energy_weather(energy_data, weather_data)
```

#### 2. **Model Training**
```python
from openstef_forecasting import train_forecast_model

model, metrics = train_forecast_model(
    data=combined_data,
    target_column="energy_generation",
    model_type="xgboost"
)

# Metrics: MAE, RMSE, R², feature importance
```

#### 3. **Generate Forecast**
```python
from openstef_forecasting import create_forecast

forecast_df = create_forecast(
    model=model,
    weather_forecast=future_weather_data,
    horizon_hours=48
)

# Returns: timestamp, predicted_load, lower_bound, upper_bound
```

#### 4. **Visualization**
```python
import plotly.graph_objects as go

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=forecast_df['timestamp'],
    y=forecast_df['predicted_load'],
    name='Forecast'
))
fig.add_trace(go.Scatter(
    x=forecast_df['timestamp'],
    y=forecast_df['upper_bound'],
    fill=None,
    mode='lines',
    line_color='rgba(0,100,200,0.2)',
    name='Upper Bound'
))
st.plotly_chart(fig)
```

---

## Advanced Features

### 1. **Probabilistic Forecasting**
Generate P10, P50, P90 quantiles for uncertainty estimation:

```python
forecast = create_quantile_forecast(
    model=model,
    quantiles=[0.1, 0.5, 0.9]
)
```

### 2. **Component Splitting (DAZLS)**
Split net load into components:

```python
from openstef.tasks.split_forecast import split_forecast

components = split_forecast(
    net_load=total_load,
    pv_generation=solar_data,
    wind_generation=wind_data
)
# Returns: baseload, solar, wind separately
```

### 3. **Model Retraining**
Automatically retrain models periodically:

```python
# Daily retraining with new data
if should_retrain(last_train_date):
    new_model = train_model_pipeline(
        data=updated_data,
        backtest_months=3
    )
```

---

## Performance Considerations

### Caching Strategy
```python
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_trained_model(model_path):
    return pickle.load(open(model_path, 'rb'))

@st.cache_data(ttl=1800)  # Cache for 30 minutes
def fetch_weather_forecast():
    return get_dwd_forecast_data()
```

### Memory Optimization
- Use hourly resolution for long-term forecasts
- Use 15-min resolution only for short-term (< 24h)
- Limit training data to last 2 years

---

## Example Use Cases

### 1. **Solar Generation Forecast**
- Input: Historical PV generation + radiation + temperature
- Output: 48-hour solar production forecast
- Use case: Grid balancing, energy trading

### 2. **Wind Power Forecast**
- Input: Wind generation + wind speed + direction
- Output: Day-ahead wind production
- Use case: Reserve capacity planning

### 3. **Net Load Forecast**
- Input: Total grid load + weather + calendar features
- Output: Load forecast with components
- Use case: Distribution network planning

---

## Dependencies

Add to `requirements.txt`:
```
openstef>=3.4.0
scikit-learn>=1.3.0
xgboost>=2.0.0
lightgbm>=4.0.0
pvlib>=0.10.0
wetterdienst>=0.115.0  # Already included
```

---

## Resources

- **OpenSTEF GitHub**: https://github.com/OpenSTEF/openstef
- **Documentation**: https://openstef.github.io/openstef/
- **Example Notebooks**: https://github.com/OpenSTEF/openstef-offline-example
- **Reference Implementation**: https://github.com/OpenSTEF/openstef-reference
- **Wetterdienst Docs**: https://wetterdienst.readthedocs.io/

---

## Next Steps

1. ✅ Install OpenSTEF: `pip install openstef`
2. ✅ Create `openstef_forecasting.py` module
3. ✅ Add dashboard tab for forecasting
4. ✅ Test with sample MaStR data
5. ✅ Deploy and monitor forecasts

---

**Last Updated**: November 26, 2025  
**Author**: VISE-D Development Team  
**Version**: 1.0
