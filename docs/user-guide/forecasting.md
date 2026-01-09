# OpenSTEF Energy Forecasting Guide

**Last Updated:** January 9, 2026

Complete guide for using OpenSTEF (Open Short-Term Energy Forecasting) with VISE-D for ML-based renewable energy predictions.

## Table of Contents
- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Using the Dashboard](#using-the-dashboard)
- [Technical Details](#technical-details)
- [Advanced Features](#advanced-features)
- [Troubleshooting](#troubleshooting)
- [Reference](#reference)

---

## Overview

### What is OpenSTEF?

**OpenSTEF** (Open Short-Term Energy Forecasting) is a Python package for generating short-term forecasts in the energy sector. It provides a complete machine learning pipeline for time-series forecasting.

**Key Capabilities:**
- 📊 Short-term forecasting (6-168 hours ahead)
- 🤖 Automated ML pipelines with model selection
- 📈 Multiple algorithms: XGBoost, LightGBM, Linear models
- 🌤️ Automatic weather feature engineering
- 📉 Model validation and performance metrics
- 🎯 Uncertainty quantification with prediction intervals

**License:** Mozilla Public License 2.0 (MPL-2.0)

### Architecture Overview

```
┌─────────────────────┐
│   DWD Weather       │  ← German Weather Service
│   (Wetterdienst)    │     Temperature, Radiation, Wind
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Data Preparation   │  ← Merge MaStR energy + weather
│  - Feature Eng.     │     Create time features
│  - Handle Missing   │     Fill gaps, align timestamps
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   OpenSTEF ML       │  ← Train XGBoost/LightGBM/Linear
│   - Auto ML         │     Hyperparameter tuning
│   - Validation      │     Cross-validation
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Forecast Output    │  ← 6-168 hour predictions
│  - Point Forecast   │     Mean prediction
│  - Uncertainty      │     Confidence intervals
└─────────────────────┘
```

---

## Installation

### Quick Install

Activate your virtual environment and run:

```powershell
# Windows PowerShell
cd c:\Users\sbirk\Documents\Code\vise-d
.\vise\Scripts\activate

# Install OpenSTEF and dependencies
pip install openstef scikit-learn xgboost lightgbm wetterdienst polars mlflow joblib
```

Or use the requirements file:

```powershell
pip install -r requirements.txt
```

### Package Overview

| Package | Version | Purpose |
|---------|---------|---------|
| `openstef` | >=3.4.0 | Main forecasting framework |
| `scikit-learn` | >=1.3.0 | ML algorithms |
| `xgboost` | >=2.0.0 | XGBoost model (best accuracy) |
| `lightgbm` | >=4.0.0 | LightGBM alternative |
| `wetterdienst` | >=0.115.0 | German weather data |
| `polars` | >=0.19.0 | Fast dataframe operations |
| `mlflow` | >=2.8.0 | Model tracking |
| `joblib` | >=1.3.0 | Model persistence |

### Verify Installation

```python
from openstef_forecasting import OpenSTEFForecaster, OPENSTEF_AVAILABLE

if OPENSTEF_AVAILABLE:
    print("✅ OpenSTEF is ready!")
else:
    print("❌ OpenSTEF not available")
```

---

## Quick Start

### 5-Minute Tutorial

1. **Launch the dashboard:**
   ```powershell
   streamlit run dashboard.py
   ```

2. **Navigate to forecasting:**
   - Click "Kurzfristige Energieprognose (OpenSTEF)" in sidebar

3. **Configure settings:**
   - Select location from dropdown (e.g., "Berlin")
   - Choose data source: Solar / Wind / Combined
   - Select model type: `xgb` (recommended)
   - Set training period: 12 months

4. **Train the model:**
   - Click "🚀 Start Training"
   - Wait 2-5 minutes for training to complete
   - View performance metrics (R², MAE, RMSE)

5. **Generate forecast:**
   - Navigate to "Forecast" tab
   - Set forecast start date and horizon (e.g., 48 hours)
   - Click "🔮 Generate Forecast"
   - View interactive chart with confidence intervals

6. **Export results:**
   - Click "Download Forecast as CSV"
   - Use predictions in your planning tools

---

## Using the Dashboard

### Page Overview

The OpenSTEF forecasting page has 4 tabs:

#### 1. **Forecast Tab**
- Generate predictions for selected horizon
- Interactive Plotly chart with zoom/pan
- Confidence intervals (90%)
- CSV export functionality

#### 2. **Train Model Tab**
- Select location and data source
- Configure model parameters
- Start training process
- View real-time progress

#### 3. **Model Performance Tab**
- Performance metrics (R², MAE, RMSE, MAPE)
- Feature importance chart
- Model diagnostics
- Cross-validation results

#### 4. **Info Tab**
- Usage instructions
- Data requirements
- Model descriptions
- Troubleshooting tips

### Configuration Options

**Location Selection:**
- Choose from MaStR database locations
- Requires sufficient historical data (>3 months)

**Data Source:**
- **Solar**: Photovoltaic generation data
- **Wind**: Wind turbine generation data
- **Combined**: Both solar and wind (experimental)

**Model Types:**

| Type | Speed | Accuracy | Use Case |
|------|-------|----------|----------|
| `xgb` | ⭐⭐ | ⭐⭐⭐⭐⭐ | Production (best accuracy) |
| `lgb` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Large datasets |
| `linear` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Quick baseline |
| `xgb_quantile` | ⭐⭐ | ⭐⭐⭐⭐ | Uncertainty quantification |

**Forecast Horizon:**
- Minimum: 6 hours
- Maximum: 168 hours (7 days)
- Recommended: 24-48 hours for best accuracy

**Training Period:**
- Minimum: 3 months
- Recommended: 12 months (captures seasonal patterns)
- Maximum: 24 months

---

## Technical Details

### Data Requirements

**Minimum Requirements:**
- ✅ 3 months of hourly data
- ✅ Location coordinates (lat/lon)
- ✅ Energy generation values

**Recommended:**
- ⭐ 12 months of data (seasonal patterns)
- ⭐ Hourly resolution
- ⭐ < 10% missing values
- ⭐ Weather covariates (temp, radiation, wind)

**Optimal:**
- 🌟 24 months of complete data
- 🌟 Weather features included
- 🌟 High-quality, validated measurements

### Feature Engineering

OpenSTEF automatically creates features from:

1. **Time Features:**
   - Hour of day (0-23)
   - Day of week (0-6)
   - Month of year (1-12)
   - Weekends vs weekdays
   - Public holidays

2. **Weather Features:**
   - Temperature (°C)
   - Solar radiation (W/m²)
   - Wind speed (m/s)
   - Air pressure (hPa)
   - Humidity (%)

3. **Lag Features:**
   - Historical load values (1h, 24h, 168h ago)
   - Rolling averages (7-day, 30-day)
   - Seasonal patterns

### Model Training Process

```python
# Example training workflow
forecaster = OpenSTEFForecaster("Berlin", lat=52.52, lon=13.40)

# 1. Fetch weather data
weather = forecaster.fetch_weather_data(
    start="2023-01-01",
    end="2024-12-31"
)

# 2. Prepare training data
data = forecaster.prepare_training_data(energy_df, weather_df)

# 3. Train model
model, metrics = forecaster.train_model(
    data,
    model_type='xgb',
    horizon_hours=48
)
# → R²=0.85, MAE=5.2 kW, RMSE=7.8 kW

# 4. Generate forecast
forecast = forecaster.create_forecast(
    model=model,
    forecast_start="2024-11-27 00:00",
    horizon_hours=48
)

# 5. Visualize
fig = forecaster.plot_forecast(forecast)
```

### Expected Performance

**Typical Metrics (Good Data):**

| Metric | Solar | Wind | Combined |
|--------|-------|------|----------|
| **R²** | 0.80-0.90 | 0.70-0.85 | 0.75-0.85 |
| **MAE** | 5-10% cap | 10-15% cap | 8-12% cap |
| **RMSE** | 7-12% cap | 12-18% cap | 10-15% cap |
| **Training** | 2-5 min | 3-6 min | 5-8 min |

*Note: "cap" = percentage of installed capacity*

**Performance Factors:**
- ✅ Data quality (completeness, accuracy)
- ✅ Training period length (more data = better)
- ✅ Weather data availability
- ✅ Location characteristics (variability)

---

## Advanced Features

### Probabilistic Forecasting

Use quantile regression for uncertainty quantification:

```python
model, metrics = forecaster.train_model(
    data,
    model_type='xgb_quantile',  # Quantile regression
    quantiles=[0.1, 0.5, 0.9]   # P10, P50, P90
)
```

**Output:**
- P10: 10th percentile (optimistic)
- P50: Median (most likely)
- P90: 90th percentile (conservative)

### Model Persistence

Save and load trained models:

```python
import joblib

# Save model
joblib.dump(model, 'trained_model.pkl')

# Load model
model = joblib.load('trained_model.pkl')
```

### Batch Forecasting

Generate forecasts for multiple horizons:

```python
horizons = [24, 48, 72, 168]  # hours
forecasts = {}

for h in horizons:
    forecast = forecaster.create_forecast(
        model, start_date, horizon_hours=h
    )
    forecasts[h] = forecast
```

### MLflow Integration

Track experiments with MLflow:

```python
import mlflow

mlflow.start_run()
mlflow.log_params({"model_type": "xgb", "horizon": 48})
mlflow.log_metrics(metrics)
mlflow.sklearn.log_model(model, "model")
mlflow.end_run()
```

---

## Troubleshooting

### Issue: "OpenSTEF not installed"

**Solution:**
```powershell
pip install openstef xgboost lightgbm
```

### Issue: "No data for location"

**Solution:**
- Try different location with more installations
- Check MaStR database has data for selected area
- Verify date range has sufficient coverage

### Issue: "Training failed"

**Symptoms:** Error during model training

**Solutions:**
1. Reduce training period (12 → 6 months)
2. Use simpler model (`model_type='linear'`)
3. Check data quality (missing values, outliers)
4. Verify weather data availability

### Issue: Memory errors

**Symptoms:** Out of memory during training

**Solutions:**
1. Use hourly (not 15-min) resolution
2. Reduce training period
3. Use LightGBM instead of XGBoost
4. Close other applications

### Issue: Poor accuracy (R² < 0.70)

**Possible Causes:**
- Insufficient training data (<6 months)
- High data variability
- Missing weather features
- Location-specific issues (shading, curtailment)

**Solutions:**
1. Increase training period (12-24 months)
2. Check data quality
3. Add more weather features
4. Try different model types

### Issue: Wetterdienst API errors

**Symptoms:** Cannot fetch weather data

**Solutions:**
1. Check internet connection
2. Verify coordinates within Germany
3. Update Wetterdienst: `pip install --upgrade wetterdienst`
4. Try different date range

---

## Reference

### Key Classes and Methods

**OpenSTEFForecaster:**
```python
class OpenSTEFForecaster:
    def __init__(self, location_name, lat, lon)
    def fetch_weather_data(self, start, end)
    def prepare_training_data(self, energy_df, weather_df)
    def train_model(self, data, model_type, horizon_hours)
    def create_forecast(self, model, forecast_start, horizon_hours)
    def plot_forecast(self, forecast_df)
    def display_metrics(self, metrics)
```

### Model Types Reference

| Type | Algorithm | Pros | Cons |
|------|-----------|------|------|
| `xgb` | XGBoost | Best accuracy, handles non-linearity | Slower training |
| `lgb` | LightGBM | Fast, memory efficient | Slightly lower accuracy |
| `linear` | Linear Regression | Very fast, interpretable | Poor for complex patterns |
| `xgb_quantile` | XGBoost Quantile | Uncertainty quantification | Slowest training |

### Data Format Specification

**Required columns:**
```python
{
    'datetime': pd.DatetimeIndex,  # Timestamp
    'load': float,                  # Energy value (kW/MW)
}
```

**Optional weather columns:**
```python
{
    'temperature': float,           # °C
    'radiation': float,             # W/m²
    'windspeed_100m': float,        # m/s
    'pressure': float,              # hPa
    'humidity': float,              # %
    'clouds': float,                # %
}
```

### Performance Benchmarks

**Training Time (1 year hourly data):**
- Linear: ~30 seconds
- LightGBM: ~2 minutes
- XGBoost: ~5 minutes
- XGBoost Quantile: ~8 minutes

**Forecast Generation:**
- 24-hour horizon: < 1 second
- 168-hour horizon: < 2 seconds

### External Resources

- **OpenSTEF Documentation:** https://openstef.github.io/openstef/
- **GitHub Repository:** https://github.com/OpenSTEF/openstef
- **Example Notebooks:** https://github.com/OpenSTEF/openstef-offline-example
- **Wetterdienst Docs:** https://wetterdienst.readthedocs.io/
- **XGBoost Documentation:** https://xgboost.readthedocs.io/

---

## See Also

- [Installation Guide](../getting-started/installation.md)
- [Configuration Guide](../getting-started/configuration.md)
- [Dashboard Overview](dashboard-overview.md)
- [Developer Guide: Caching](../developer-guide/caching.md)

---

**Project:** VISE-D  
**Module:** src/forecasting/openstef.py  
**Version:** 1.0  
**Last Updated:** January 9, 2026
