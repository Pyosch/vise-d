# [Phase 7.2.1] Implement RTPTariff Class with EPEX Data Import

**Labels**: `enhancement`, `phase-7`, `priority-medium`, `copilot-ready`  
**Milestone**: Phase 7.2 - Real-Time Pricing & Grid Integration  
**Estimated Time**: 2-3 days  
**Dependencies**: Issue #2 (TOUTariff class), Phase 7.1 complete  
**Assignee**: [Your name]

---

## 📋 Description

Implement the `RTPTariff` class for Real-Time Pricing tariffs with dynamic prices based on wholesale market data (EPEX SPOT or similar). Include data loading, price forecasting, and congestion-based adjustments.

---

## 🎯 Context

- **Part of**: Phase 7.2 - Real-Time Pricing & Grid Integration
- **Reference**: `roadmap.md` Section 7.2, Task 2.1
- **Data Source**: EPEX SPOT day-ahead prices (or synthetic data if API unavailable)
- **Integration Points**: `BaseTariff` abstract class, demand response model, grid integration module

---

## 📦 Requirements

### Class Implementation: `RTPTariff`

Location: `market_design/tariff_models.py`

**Inherits from**: `BaseTariff`

**Properties**:
```python
- name: str - Tariff name (e.g., "RTP - EPEX Day-Ahead")
- description: str - Human-readable description
- base_prices: pd.DataFrame - Price data with columns ['timestamp', 'price_euro_per_kwh']
- congestion_multiplier: float - Factor for congestion-based price adjustment (default: 1.0)
- price_cap: float - Maximum allowed price in €/kWh (default: 1.0)
- price_floor: float - Minimum allowed price in €/kWh (default: 0.0)
- markup: float - Retail markup on wholesale price (default: 0.05 = 5 cents)
```

**Methods**:

1. `__init__(self, name: str, base_prices: pd.DataFrame = None, congestion_multiplier: float = 1.0, price_cap: float = 1.0, price_floor: float = 0.0, markup: float = 0.05)`
   - Initialize RTP tariff
   - If base_prices is None, create empty DataFrame
   - Validate price_cap > price_floor

2. `load_price_data(self, source: str, start_date: datetime, end_date: datetime) -> None`
   - **source**: "epex", "csv", or "synthetic"
   - Load price data from specified source
   - Store in self.base_prices DataFrame
   - Handle missing data (interpolation or forward-fill)

3. `calculate_price(self, timestamp: datetime) -> float`
   - Look up base price for timestamp
   - Apply markup: `retail_price = base_price + markup`
   - Apply congestion multiplier: `final_price = retail_price * congestion_multiplier`
   - Enforce cap and floor: `max(price_floor, min(price_cap, final_price))`
   - Return final price

4. `calculate_bill(self, load_profile: pd.DataFrame) -> float`
   - For each timestamp in load_profile, get price
   - Calculate: `bill = sum(load_kw * price * 1 hour)`
   - Return total bill in euros

5. `apply_congestion(self, congestion_factor: float) -> None`
   - Update self.congestion_multiplier
   - Validate congestion_factor >= 0
   - Typical values: 1.0 (no congestion) to 2.0 (high congestion)

6. `forecast_24h(self, start_time: datetime) -> pd.DataFrame`
   - Return 24-hour price forecast starting from start_time
   - Columns: ['timestamp', 'forecast_price_euro_per_kwh']
   - Useful for demand response optimization

7. `get_price_statistics(self, start_date: datetime = None, end_date: datetime = None) -> Dict`
   - Calculate statistics for price data in given period
   - Return dict: {'mean': float, 'median': float, 'min': float, 'max': float, 'std': float}

8. `load_from_csv(self, filepath: str) -> None`
   - Helper method to load prices from CSV file
   - Expected columns: ['timestamp', 'price']
   - Convert to base_prices DataFrame

---

## 📊 Data Integration Options

### Option 1: EPEX SPOT API (Preferred)

Research EPEX SPOT API or open data sources:
- Check if API is publicly available
- Document authentication requirements
- Implement in separate module: `market_design/data_loaders/epex_loader.py`

**If API available**:
```python
def load_epex_data(start_date, end_date, market='DE'):
    """Load EPEX SPOT day-ahead prices"""
    # API call implementation
    # Return DataFrame with timestamp, price columns
```

### Option 2: Synthetic Data (Fallback)

If real data unavailable, generate realistic synthetic prices:

```python
def generate_synthetic_rtp_prices(start_date, end_date):
    """
    Generate synthetic RTP prices based on typical patterns.
    
    Pattern:
    - Base price: €0.10-0.15/kWh
    - Daily pattern: Low at night (€0.08), high at peak (€0.30)
    - Weekly pattern: Higher on weekdays
    - Random variations: ±20%
    """
    # Implementation
    return prices_df
```

### Option 3: CSV File

Provide sample CSV file in `data/sample_rtp_prices.csv`:
```csv
timestamp,price_euro_per_kwh
2025-01-01 00:00:00,0.08
2025-01-01 01:00:00,0.07
...
```

**Decision**: Start with Option 3 (CSV), add Option 1 (EPEX) later if time permits

---

## 🔧 Technical Requirements

### Price Data Validation

```python
def validate_price_data(self, df: pd.DataFrame) -> bool:
    """Validate loaded price data"""
    required_columns = ['timestamp', 'price_euro_per_kwh']
    
    # Check columns exist
    if not all(col in df.columns for col in required_columns):
        raise ValueError(f"Missing columns. Required: {required_columns}")
    
    # Check timestamp is datetime
    if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        raise ValueError("timestamp must be datetime type")
    
    # Check for negative prices (can happen in reality, but warn)
    if (df['price_euro_per_kwh'] < 0).any():
        warnings.warn("Negative prices detected (can occur in wholesale markets)")
    
    # Check for gaps > 1 hour
    df_sorted = df.sort_values('timestamp')
    time_diff = df_sorted['timestamp'].diff()
    if (time_diff > pd.Timedelta(hours=2)).any():
        warnings.warn("Gaps > 1 hour detected in price data")
    
    return True
```

### Caching Strategy

Use existing cache infrastructure:
```python
import hashlib
import json

def cache_price_data(self, source, start_date, end_date, data):
    """Cache loaded price data to avoid repeated API calls"""
    cache_key = hashlib.sha256(
        f"{source}_{start_date}_{end_date}".encode()
    ).hexdigest()
    
    cache_path = f"cache/{cache_key}.json"
    # Save data
```

---

## ✅ Acceptance Criteria

### Functionality
- [ ] Class inherits from `BaseTariff` correctly
- [ ] Can load price data from CSV file
- [ ] `calculate_price()` returns correct price for any timestamp
- [ ] `calculate_bill()` calculates correct total bill
- [ ] Congestion multiplier adjusts prices correctly
- [ ] Price cap and floor are enforced
- [ ] 24-hour forecast works correctly
- [ ] Handles missing timestamps gracefully (interpolation)

### Code Quality
- [ ] Python 3.11+ type hints on all methods
- [ ] Google-style docstrings with examples
- [ ] Passes `black --check` and `flake8`
- [ ] No syntax errors

### Data
- [ ] Sample CSV file created in `data/sample_rtp_prices.csv`
- [ ] CSV covers at least 30 days of hourly data
- [ ] Prices follow realistic daily patterns

### Testing
- [ ] Unit tests cover >90% of code
- [ ] All edge cases tested

---

## 🧪 Testing Requirements

Create tests in `market_design/tests/test_tariff_models.py` (extend existing file)

### Test Cases:

**Normal Operation**:
```python
def test_rtp_tariff_load_csv():
    """Test loading prices from CSV file"""
    # Create sample CSV, load it, verify DataFrame structure

def test_rtp_calculate_price_no_congestion():
    """Test price calculation without congestion"""
    # Base price €0.10 + markup €0.05 = €0.15

def test_rtp_calculate_price_with_congestion():
    """Test price calculation with congestion multiplier"""
    # (€0.10 + €0.05) * 1.5 = €0.225

def test_rtp_price_cap_enforcement():
    """Test that price cap is enforced"""
    # Set cap = €0.30, verify never exceeds

def test_rtp_forecast_24h():
    """Test 24-hour forecast generation"""
    # Verify returns 24 hourly prices
```

**Edge Cases**:
```python
def test_rtp_missing_timestamp():
    """Test behavior when requested timestamp not in data"""
    # Should interpolate or raise helpful error

def test_rtp_negative_wholesale_price():
    """Test handling of negative wholesale prices (can happen)"""
    # With floor = 0, should return 0 or small markup

def test_rtp_congestion_zero():
    """Test congestion_multiplier = 0"""
    # Should result in price = 0 (extreme demand response scenario)
```

**Integration**:
```python
def test_rtp_with_demand_response():
    """Test RTP tariff with demand response model"""
    # Load RTP prices, apply DR, verify load shifting to low-price hours
```

---

## 📚 Reference Materials

- **Roadmap**: `roadmap.md` Section 7.2, Task 2.1
- **EPEX SPOT**: https://www.epexspot.com/ (research data access)
- **Base Class**: `BaseTariff` in `market_design/tariff_models.py`
- **Pandas DateTime**: https://pandas.pydata.org/docs/user_guide/timeseries.html
- **Similar Pattern**: `TOUTariff` class for structure reference

---

## 🤖 GitHub Copilot Prompt Suggestion

```
@workspace Implement the RTPTariff class in market_design/tariff_models.py

Requirements (see issue #6):
1. Inherits from BaseTariff
2. Properties: base_prices (DataFrame), congestion_multiplier, price_cap, price_floor, markup
3. Methods:
   - load_price_data(source, start_date, end_date) - Load from CSV or generate synthetic
   - calculate_price(timestamp) - Base price + markup, apply congestion, enforce cap/floor
   - calculate_bill(load_profile) - Sum of load * price for each hour
   - forecast_24h(start_time) - Return 24-hour price forecast
   - apply_congestion(factor) - Update congestion multiplier

4. Data loading:
   - Start with CSV file: data/sample_rtp_prices.csv
   - Handle missing timestamps with interpolation
   - Validate data structure

5. Example usage:
```python
rtp = RTPTariff(
    name="RTP - Day-Ahead",
    price_cap=1.0,
    price_floor=0.0,
    markup=0.05
)
rtp.load_from_csv('data/sample_rtp_prices.csv')
rtp.apply_congestion(1.2)  # 20% congestion surcharge
price = rtp.calculate_price(datetime(2025, 10, 30, 18, 0))
```

Use Python 3.11+ type hints, Google-style docstrings.
Include validation and error handling for missing data.
```

---

## 🗒️ Implementation Notes

### Sample CSV Data Generation

Create helper script to generate sample data:

```python
# scripts/generate_sample_rtp_data.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_sample_rtp_prices():
    """Generate 30 days of realistic hourly RTP prices"""
    start = datetime(2025, 1, 1)
    timestamps = pd.date_range(start, periods=30*24, freq='H')
    
    prices = []
    for ts in timestamps:
        hour = ts.hour
        is_weekend = ts.weekday() >= 5
        
        # Base price pattern
        if hour < 6:  # Night
            base = 0.08
        elif hour < 9:  # Morning ramp
            base = 0.15
        elif hour < 16:  # Day
            base = 0.12
        elif hour < 21:  # Peak
            base = 0.30
        else:  # Evening
            base = 0.15
        
        # Weekend discount
        if is_weekend:
            base *= 0.8
        
        # Add random variation
        price = base * np.random.uniform(0.8, 1.2)
        prices.append(price)
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'price_euro_per_kwh': prices
    })
    
    df.to_csv('data/sample_rtp_prices.csv', index=False)
    print(f"Generated {len(df)} hourly prices")

if __name__ == '__main__':
    generate_sample_rtp_prices()
```

Run this script before implementing RTPTariff class.

---

## 🔄 Related Issues

- **Depends on**: #2 (BaseTariff interface), Phase 7.1 complete
- **Blocks**: #7 (Pandapower integration will use RTP prices)
- **Blocks**: #8 (Load profile visualization will compare TOU vs RTP)
- **Enhances**: #3 (Demand response can optimize against RTP signals)

---

**Created**: [Date]  
**Last Updated**: [Date]  
**Status**: Open / In Progress / Complete
