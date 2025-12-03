# OpenSTEF Installation Guide

## Quick Start

To install OpenSTEF and all dependencies for the VISE-D dashboard, follow these steps:

### 1. Activate your virtual environment

```powershell
# Windows PowerShell
F:\Streamlit_Project\env\Scripts\activate
```

### 2. Install OpenSTEF dependencies

```powershell
pip install openstef scikit-learn xgboost lightgbm wetterdienst polars mlflow joblib
```

**OR** install from the updated requirements file:

```powershell
pip install -r requirements.txt
```

### 3. Verify installation

```powershell
python -c "import openstef; print('OpenSTEF version:', openstef.__version__)"
```

---

## Platform-Specific Notes

### Windows

If you encounter issues with XGBoost on Windows, you may need to install Visual C++ Build Tools:
1. Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Install "Desktop development with C++" workload

### Conda Environment (Alternative)

If using conda, create a new environment:

```powershell
conda create -n vise-d python=3.10
conda activate vise-d
pip install -r requirements.txt
```

---

## Package Overview

### Core OpenSTEF Packages

| Package | Version | Purpose |
|---------|---------|---------|
| `openstef` | >=3.4.0 | Main forecasting framework |
| `scikit-learn` | >=1.3.0 | Machine learning algorithms |
| `xgboost` | >=2.0.0 | XGBoost model (recommended) |
| `lightgbm` | >=4.0.0 | LightGBM model |
| `polars` | >=0.19.0 | Fast dataframe operations |
| `mlflow` | >=2.8.0 | Model tracking and serialization |
| `joblib` | >=1.3.0 | Model persistence |

### Weather Data

| Package | Version | Purpose |
|---------|---------|---------|
| `wetterdienst` | >=0.115.0 | German weather data (DWD) |

---

## Testing the Installation

Run the test script to verify everything works:

```python
from openstef_forecasting import OpenSTEFForecaster, OPENSTEF_AVAILABLE

if OPENSTEF_AVAILABLE:
    print("✅ OpenSTEF is ready!")
    forecaster = OpenSTEFForecaster("Test", 52.52, 13.40)
    print(f"✅ Forecaster initialized for {forecaster.location_name}")
else:
    print("❌ OpenSTEF not available")
```

---

## Troubleshooting

### Issue: "Import openstef could not be resolved"

**Solution:** Make sure you're using the correct Python environment:

```powershell
python --version  # Should be 3.9-3.11
pip list | grep openstef  # Should show openstef installation
```

### Issue: XGBoost installation fails

**Solution:** Try installing from conda-forge:

```powershell
conda install -c conda-forge xgboost
```

### Issue: Wetterdienst errors

**Solution:** Update to latest version:

```powershell
pip install --upgrade wetterdienst
```

### Issue: Memory errors during training

**Solution:** Reduce training data period or use lower resolution:

- Use hourly instead of 15-minute data
- Limit training period to 12 months instead of 24
- Use `model_type='linear'` instead of `'xgb'` for faster training

---

## Next Steps

After successful installation:

1. ✅ Launch the dashboard: `streamlit run dashboard.py`
2. ✅ Navigate to "⚡ Energy Forecasting (OpenSTEF)" tab
3. ✅ Select a location and data source
4. ✅ Train your first model
5. ✅ Generate forecasts!

---

## Resources

- **OpenSTEF Documentation**: https://openstef.github.io/openstef/
- **Integration Guide**: See `OPENSTEF_INTEGRATION.md`
- **Example Notebooks**: https://github.com/OpenSTEF/openstef-offline-example
- **Wetterdienst Docs**: https://wetterdienst.readthedocs.io/

---

**Last Updated**: November 26, 2025
