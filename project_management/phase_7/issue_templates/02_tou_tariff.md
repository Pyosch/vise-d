# [Phase 7.1.2] Implement TOUTariff Class with Unit Tests

**Labels**: `enhancement`, `phase-7`, `priority-high`, `copilot-ready`  
**Milestone**: Phase 7.1 - Foundation  
**Estimated Time**: 2 days  
**Dependencies**: Issue #1 (Package Structure)  
**Assignee**: [Your name]

---

## 📋 Description

Implement the `TOUTariff` class with complete Time-of-Use tariff logic including time period management, price calculation, and bill computation. This is the foundational tariff model for Phase 7.

---

## 🎯 Context

- **Part of**: Phase 7.1 - Foundation & Basic TOU
- **Reference**: `roadmap.md` Section 7.2, Task 1.2
- **Integration Points**: `BaseTariff` abstract class, dashboard UI (Task 1.4), demand response (Task 1.3)

---

## 📦 Requirements

### Class Implementation: `TOUTariff`

Location: `market_design/tariff_models.py`

**Inherits from**: `BaseTariff` (already defined)

**Properties**:
```python
- name: str - Tariff name for display (e.g., "Residential TOU 3-Period")
- description: str - Human-readable description
- time_periods: Dict[str, str] - Maps period names to time ranges
  Example: {"peak": "16:00-20:00", "off_peak": "20:00-16:00"}
- prices: Dict[str, float] - Maps period names to prices in €/kWh
  Example: {"peak": 0.35, "off_peak": 0.15}
- weekday_only: bool - Whether peak/off-peak applies only on weekdays (default: False)
```

**Methods**:

1. `__init__(self, time_periods: Dict[str, str], prices: Dict[str, float], name: str, description: str = "", weekday_only: bool = False)`
   - Initialize tariff with validation
   - Validate that period names match between time_periods and prices
   - Validate time format "HH:MM-HH:MM"

2. `calculate_price(self, timestamp: datetime) -> float`
   - Determine which period the timestamp falls into
   - Return the corresponding price
   - Handle weekday_only flag (weekend = off_peak if True)
   - Raise ValueError if timestamp has no matching period

3. `calculate_bill(self, load_profile: pd.DataFrame) -> float`
   - Input: DataFrame with columns ['timestamp', 'load_kw']
   - For each hour, calculate price * load_kw
   - Return sum in euros
   - Handle missing timestamps gracefully

4. `add_time_period(self, period_name: str, time_range: str, price: float) -> None`
   - Add or update a time period
   - Validate time_range format
   - Validate price > 0

5. `remove_time_period(self, period_name: str) -> None`
   - Remove a time period
   - Validate that at least one period remains

6. `validate_periods(self) -> bool`
   - Check that time periods cover full 24 hours
   - Check for gaps or overlaps
   - Raise ValueError with descriptive message if invalid

7. `get_period_at_time(self, timestamp: datetime) -> str`
   - Return the period name for a given timestamp
   - Consider weekday_only flag

8. `get_price_schedule(self, start_date: datetime, days: int = 1) -> pd.DataFrame`
   - Generate a DataFrame with hourly prices for given date range
   - Columns: ['timestamp', 'period', 'price_euro_per_kwh']
   - Useful for visualization

---

## 🔧 Input Validation Requirements

**Validation Rules**:
1. All prices must be > 0 (raise `ValueError` with message: "Price must be positive, got {price} for period {name}")
2. Time periods must be in format "HH:MM-HH:MM" (use regex validation)
3. Period names in `time_periods` and `prices` must match exactly
4. Time periods should cover full 24 hours (use `validate_periods()`)
5. Load profile DataFrame must have columns ['timestamp', 'load_kw'] (raise `ValueError` if missing)

**Error Messages**: Use descriptive, actionable error messages

---

## ✅ Acceptance Criteria

### Functionality
- [ ] Class inherits from `BaseTariff` correctly
- [ ] Can create TOU tariff with 2 periods (peak/off-peak)
- [ ] Can create TOU tariff with 3 periods (peak/mid-peak/off-peak)
- [ ] `calculate_price()` returns correct price for any timestamp
- [ ] `calculate_bill()` calculates correct total bill
- [ ] Validation catches all invalid inputs with clear error messages

### Code Quality
- [ ] Python 3.11+ type hints on all methods
- [ ] Google-style docstrings with examples
- [ ] Passes `black --check`
- [ ] Passes `flake8` with 0 errors
- [ ] No syntax errors: `python -m py_compile`

### Testing (see Testing Requirements below)
- [ ] Unit tests cover >90% of code
- [ ] All edge cases tested
- [ ] All error cases tested

---

## 🧪 Testing Requirements

Create comprehensive pytest tests in `market_design/tests/test_tariff_models.py`

### Test Cases to Implement:

**Normal Operation**:
```python
def test_tou_tariff_2_period():
    """Test basic 2-period TOU tariff (peak/off-peak)"""
    # Create tariff, calculate price at peak time, verify correct

def test_tou_tariff_3_period():
    """Test 3-period TOU tariff (peak/mid-peak/off-peak)"""
    # Create tariff, calculate prices for all periods, verify

def test_calculate_bill_simple():
    """Test bill calculation with uniform load profile"""
    # 24 hours at 2.5 kW, verify bill = sum(load * price per period)
```

**Edge Cases**:
```python
def test_midnight_boundary():
    """Test time period crossing midnight (e.g., '22:00-06:00')"""
    # Verify prices correct at 23:59, 00:00, 00:01

def test_single_period_flat_rate():
    """Test tariff with single period (equivalent to flat rate)"""
    # All times should return same price

def test_weekday_only_flag():
    """Test weekday_only behavior on Saturday/Sunday"""
    # Weekend should default to off_peak when weekday_only=True

def test_bill_calculation_multi_day():
    """Test bill calculation over multiple days"""
    # Load profile spanning 3 days, verify correct total
```

**Error Cases**:
```python
def test_negative_price_raises_error():
    """Test that negative price raises ValueError"""
    # Attempt to create tariff with negative price, expect ValueError

def test_invalid_time_format_raises_error():
    """Test that invalid time format raises ValueError"""
    # Try "16-20" instead of "16:00-20:00", expect error

def test_mismatched_period_names():
    """Test that mismatched period names raise ValueError"""
    # time_periods has "peak" but prices has "Peak" (case mismatch)

def test_time_period_gap_detected():
    """Test that gaps in time coverage raise ValueError"""
    # Only define 16:00-20:00, leaving 20:00-16:00 undefined

def test_missing_load_profile_columns():
    """Test that missing DataFrame columns raise ValueError"""
    # DataFrame with only 'timestamp' column, expect error

def test_empty_load_profile():
    """Test handling of empty DataFrame"""
    # Should return 0.0 bill or raise ValueError (decide)
```

**Coverage Target**: >90%

---

## 📚 Reference Materials

- **Roadmap**: `roadmap.md` Section 7.2, Task 1.2
- **Base Class**: `market_design/tariff_models.py` - `BaseTariff`
- **Similar Pattern**: `technologies/photovoltaics.py` for class structure
- **Pandas Usage**: `mastr_preprocessing.py` for DataFrame handling examples
- **Time Handling**: Use `datetime.time()` for time-of-day comparisons

---

## 🤖 GitHub Copilot Prompt Suggestion

```
@workspace Implement the TOUTariff class in market_design/tariff_models.py

Requirements (see issue #2 for full details):
1. Inherits from BaseTariff
2. Properties: time_periods (Dict[str, str]), prices (Dict[str, float]), name, description
3. Methods: calculate_price(timestamp), calculate_bill(load_profile), validate_periods()
4. Validation: prices > 0, time format "HH:MM-HH:MM", 24h coverage
5. Handle midnight boundary crossing (e.g., "22:00-06:00" off-peak period)

Example usage:
```python
tou = TOUTariff(
    time_periods={"peak": "16:00-20:00", "off_peak": "20:00-16:00"},
    prices={"peak": 0.35, "off_peak": 0.15},
    name="Residential TOU 2-Period"
)
price = tou.calculate_price(datetime(2025, 10, 30, 18, 0))  # Returns 0.35
bill = tou.calculate_bill(load_df)  # DataFrame with timestamp, load_kw
```

Use Python 3.11+ type hints, Google-style docstrings.
Reference existing code style in technologies/photovoltaics.py
```

---

## 🗒️ Implementation Notes

### Time Period Parsing Strategy

For handling time ranges like "16:00-20:00":
1. Split on "-" to get start and end times
2. Parse each as `datetime.time()` object
3. For midnight crossings (end < start), treat as wrapping to next day

### Weekday Logic

When `weekday_only=True`:
- Monday-Friday: Use defined time periods
- Saturday-Sunday: All hours count as "off_peak" (or lowest priced period)

### Bill Calculation Performance

For large load profiles (1000+ customers):
- Use vectorized pandas operations
- Avoid row-by-row iteration
- Example: `load_profile['price'] = load_profile['timestamp'].apply(calculate_price)`

---

## 🔄 Related Issues

- **Depends on**: #1 (Package structure must exist)
- **Blocks**: #3 (Demand response needs tariff prices)
- **Blocks**: #4 (UI configuration needs working tariff class)
- **Blocks**: #5 (Bill visualization needs calculate_bill method)

---

**Created**: [Date]  
**Last Updated**: [Date]  
**Status**: Open / In Progress / Complete
