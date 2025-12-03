# OpenSTEF Quick Reference Card

## 🚀 Installation (One Command)

```powershell
pip install openstef scikit-learn xgboost lightgbm wetterdienst polars mlflow joblib
```

## 📊 Dashboard Usage

1. **Launch**: `streamlit run dashboard.py`
2. **Navigate**: Click "⚡ Energy Forecasting (OpenSTEF)"
3. **Configure**: Select location, data source, model type
4. **Train**: Click "🚀 Start Training" (2-5 min)
5. **Forecast**: Click "🔮 Generate Forecast"

## 🔧 Key Components

### Files
| File | Purpose |
|------|---------|
| `openstef_forecasting.py` | Main forecasting engine (700 lines) |
| `OPENSTEF_INTEGRATION.md` | Complete integration guide |
| `OPENSTEF_INSTALLATION.md` | Setup instructions |
| `OPENSTEF_SUMMARY.md` | This overview |

### Classes & Methods
```python
# Initialize forecaster
forecaster = OpenSTEFForecaster("Berlin", lat=52.52, lon=13.40)

# Fetch weather data
weather = forecaster.fetch_weather_data("2023-01-01", "2024-12-31")

# Prepare training data
data = forecaster.prepare_training_data(energy_df, weather_df)

# Train model
model, metrics = forecaster.train_model(data, model_type='xgb')

# Create forecast
forecast = forecaster.create_forecast(model, "2024-11-27", horizon_hours=48)

# Plot results
fig = forecaster.plot_forecast(forecast)
```

## 🎯 Model Types

| Type | Speed | Accuracy | Use When |
|------|-------|----------|----------|
| `xgb` | ⭐⭐ | ⭐⭐⭐⭐⭐ | Best accuracy (recommended) |
| `lgb` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Large datasets |
| `linear` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Quick baseline |
| `xgb_quantile` | ⭐⭐ | ⭐⭐⭐⭐ | Uncertainty quantification |

## 📈 Expected Performance

### Typical Metrics (Good Data)
- **R² Score**: 0.80 - 0.90 (solar), 0.70 - 0.85 (wind)
- **MAE**: 5-10% of capacity (solar), 10-15% (wind)
- **Training Time**: 2-8 minutes (1-2 years of hourly data)

## ⚙️ Configuration Options

### Sidebar Settings
- **Data Source**: Solar / Wind / Combined
- **Location**: From MaStR database
- **Model Type**: xgb / lgb / linear / xgb_quantile
- **Forecast Horizon**: 6 - 168 hours
- **Training Period**: 3 - 24 months

## 🔍 Data Requirements

### Minimum
- ✅ 3 months of hourly data
- ✅ Location coordinates (lat/lon)
- ✅ Energy generation values

### Recommended
- ⭐ 12 months of data (seasonal patterns)
- ⭐ Hourly resolution
- ⭐ < 10% missing values

### Optimal
- 🌟 24 months of data
- 🌟 Weather covariates (temp, radiation, wind)
- 🌟 Complete historical records

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| "OpenSTEF not installed" | `pip install openstef xgboost` |
| "No data for location" | Try different location with more installations |
| "Training failed" | Reduce training period or use `model_type='linear'` |
| Memory errors | Use hourly (not 15-min) data, reduce training period |
| Poor accuracy | Need more data (> 12 months) or better weather data |

## 📚 Learn More

- 📖 **Full Guide**: `OPENSTEF_INTEGRATION.md`
- ⚙️ **Setup**: `OPENSTEF_INSTALLATION.md`
- 📋 **Overview**: `OPENSTEF_SUMMARY.md`
- 🌐 **Online Docs**: https://openstef.github.io/openstef/
- 💻 **Examples**: https://github.com/OpenSTEF/openstef-offline-example

## 🎓 Quick Tips

1. **Start Simple**: Use 6-month training period with 'linear' model for testing
2. **Use XGBoost**: Switch to 'xgb' for production (best accuracy)
3. **Check Weather**: Ensure Wetterdienst data available for your location
4. **Monitor Metrics**: R² > 0.80 is good, > 0.90 is excellent
5. **Retrain Regularly**: Update models monthly with new data

## 🔄 Typical Workflow

```
Select Location → Configure Settings → Train Model (2-5 min) →
View Metrics (R², MAE, RMSE) → Generate Forecast → 
Download CSV → Use in Planning
```

## 📞 Support

- 🐛 **Bug Reports**: https://github.com/OpenSTEF/openstef/issues
- 💬 **Discussions**: OpenSTEF Teams Channel
- 📧 **Questions**: Check documentation first!

---

**Version**: 1.0 | **Date**: Nov 26, 2025 | **Project**: VISE-D Dashboard
