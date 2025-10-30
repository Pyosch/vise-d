# [Phase 7.1.3] Implement Demand Response Price Elasticity Model

**Labels**: `enhancement`, `phase-7`, `priority-high`, `copilot-ready`  
**Milestone**: Phase 7.1 - Foundation  
**Estimated Time**: 1-2 days  
**Dependencies**: Issue #2 (TOUTariff class)  
**Assignee**: [Your name]

---

## 📋 Description

Implement a demand response model that simulates how customers adjust their electricity consumption in response to price signals from TOU or RTP tariffs. Use price elasticity theory with load shifting capabilities.

---

## 🎯 Context

- **Part of**: Phase 7.1 - Foundation & Basic TOU
- **Reference**: `roadmap.md` Section 7.2, Task 1.3
- **Theory**: Price elasticity of demand (literature: residential elasticity typically -0.1 to -0.3)
- **Integration Points**: TOUTariff class, load profiles, bill calculations

---

## 📦 Requirements

### Module: `market_design/demand_response.py`

Create a new module with the following components:

### Class: `DemandResponseModel`

**Properties**:
```python
- elasticity: float - Price elasticity coefficient (typically -0.15)
  Negative value: demand decreases as price increases
- behavior_type: str - Consumer behavior: "passive", "active", "automated"
  passive: Only responds to very high prices
  active: Responds to all price signals, shifts loads
  automated: Perfect response (smart home, battery)
- flexibility_window: int - Hours over which loads can shift (default: 6)
- max_shift_percentage: float - Max % of load that can shift (0.0-1.0, default: 0.3)
- shiftable_appliances: List[str] - Types of loads that can shift
  Example: ["dishwasher", "washing_machine", "ev_charging"]
```

**Methods**:

1. `__init__(self, elasticity: float = -0.15, behavior_type: str = "passive", flexibility_window: int = 6, max_shift_percentage: float = 0.3)`
   - Initialize model with validation
   - Validate elasticity is negative
   - Validate behavior_type in allowed values

2. `apply_demand_response(self, load_profile: pd.DataFrame, price_signal: pd.Series) -> pd.DataFrame`
   - **Input**: Original load profile with columns ['timestamp', 'load_kw']
   - **Input**: Price signal (Series with same index as load_profile)
   - **Output**: Modified load profile with demand response applied
   - **Process**:
     1. Calculate price ratios (price vs. average price)
     2. Apply elasticity formula to reduce/increase loads
     3. Shift flexible loads from high-price to low-price periods
     4. Ensure energy conservation (total energy same or slightly reduced)

3. `calculate_load_change(self, original_load: float, price_ratio: float) -> float`
   - Formula: `new_load = original_load * (price_ratio ^ elasticity)`
   - Example: If price doubles (ratio=2.0) and elasticity=-0.15:
     `new_load = original * (2.0 ^ -0.15) = original * 0.90 = 10% reduction`

4. `shift_load(self, load_profile: pd.DataFrame, from_hours: List[int], to_hours: List[int], amount_kw: float) -> pd.DataFrame`
   - Shift specified amount of load from high-price hours to low-price hours
   - Respect flexibility_window constraint
   - Respect max_shift_percentage constraint

5. `identify_shift_opportunities(self, load_profile: pd.DataFrame, price_signal: pd.Series) -> Dict[str, List[int]]`
   - Analyze price signal to identify:
     - `high_price_hours`: Hours to reduce load
     - `low_price_hours`: Hours to increase load (within flexibility window)
   - Return dict with both lists

6. `validate_energy_conservation(self, original: pd.DataFrame, modified: pd.DataFrame) -> bool`
   - Check that total energy is conserved (accounting for elasticity reduction)
   - Allow small reduction due to elasticity, but no increase
   - Return True if valid, raise ValueError if energy increased

---

## 🔧 Technical Requirements

### Behavior Type Implementation

**Passive** (`behavior_type="passive"`):
- Only responds to prices >1.5x average
- Low load shifting (<10%)
- High inertia (slow response)

**Active** (`behavior_type="active"`):
- Responds to all price variations
- Moderate load shifting (20-30%)
- Normal response time

**Automated** (`behavior_type="automated"`):
- Optimal response to price signals
- High load shifting (up to 50%)
- Instant response (smart home automation)

### Price Elasticity Formula

Standard economic formula:
```
% change in demand = elasticity × % change in price

If price_ratio = new_price / avg_price:
new_demand = original_demand × (price_ratio ^ elasticity)
```

### Load Shifting Logic

Example scenario:
- Peak hour (18:00): Price = €0.40/kWh, Load = 4 kW
- Off-peak (23:00): Price = €0.15/kWh, Load = 1 kW
- Flexibility window = 6 hours (can shift from 18:00 to 23:00)
- Action: Shift 1 kW from 18:00 to 23:00 (dishwasher delayed)

---

## ✅ Acceptance Criteria

### Functionality
- [ ] Can create DemandResponseModel with different behavior types
- [ ] `apply_demand_response()` modifies loads based on price signals
- [ ] Load changes follow elasticity formula correctly
- [ ] Load shifting respects time window and percentage constraints
- [ ] Energy is conserved (or slightly reduced)
- [ ] Behavior types produce different response magnitudes

### Code Quality
- [ ] Python 3.11+ type hints on all methods
- [ ] Google-style docstrings with mathematical formulas
- [ ] Passes `black --check` and `flake8`
- [ ] No syntax errors

### Testing
- [ ] Unit tests cover >90% of code
- [ ] Validation against literature elasticity values
- [ ] Edge cases tested (zero load, flat prices, etc.)

---

## 🧪 Testing Requirements

Create tests in `market_design/tests/test_demand_response.py`

### Test Cases:

**Normal Operation**:
```python
def test_apply_demand_response_passive():
    """Test passive consumer behavior"""
    # Small price variation → minimal response

def test_apply_demand_response_active():
    """Test active consumer behavior"""
    # Price variation → moderate load shifting

def test_apply_demand_response_automated():
    """Test automated optimal response"""
    # Price variation → maximum allowable shifting

def test_load_shifting_within_window():
    """Test that load shifts only within flexibility window"""
    # 6-hour window: verify no shifts beyond 6 hours

def test_elasticity_calculation():
    """Test elasticity formula correctness"""
    # Price doubles → load reduces by (2^-0.15) = ~10%
```

**Edge Cases**:
```python
def test_flat_price_signal():
    """Test response when all prices are equal"""
    # No price variation → no demand response

def test_zero_load_periods():
    """Test handling of zero load hours"""
    # Should handle gracefully, not shift from/to zero

def test_extreme_price_spike():
    """Test response to very high price (5x average)"""
    # Should reduce load significantly but not below zero

def test_max_shift_percentage_enforced():
    """Test that max_shift_percentage is respected"""
    # Even with optimal opportunity, don't exceed limit
```

**Validation**:
```python
def test_energy_conservation():
    """Test that total energy is conserved or reduced"""
    # Sum of modified loads <= sum of original loads

def test_literature_elasticity_range():
    """Test that results align with published studies"""
    # With elasticity=-0.15, verify 10-20% peak reduction for TOU
```

---

## 📚 Reference Materials

- **Roadmap**: `roadmap.md` Section 7.2, Task 1.3
- **Literature**: Price elasticity for residential: -0.1 to -0.3
  - Source: Faruqui & Sergici (2010) "Household Response to Dynamic Pricing"
- **Integration**: Use with `TOUTariff.get_price_schedule()` for price signals
- **Pandas Docs**: https://pandas.pydata.org/docs/ for DataFrame operations

---

## 🤖 GitHub Copilot Prompt Suggestion

```
@workspace Create the DemandResponseModel class in market_design/demand_response.py

Requirements (see issue #3):
1. Model price-responsive consumer behavior
2. Properties: elasticity (float), behavior_type (str), flexibility_window (int)
3. Methods: apply_demand_response(), shift_load(), validate_energy_conservation()
4. Three behavior types: passive, active, automated (different response magnitudes)
5. Use elasticity formula: new_load = original_load × (price_ratio ^ elasticity)

Example usage:
```python
dr_model = DemandResponseModel(
    elasticity=-0.15,
    behavior_type="active",
    flexibility_window=6,
    max_shift_percentage=0.3
)

# Apply to load profile with TOU prices
modified_load = dr_model.apply_demand_response(load_df, price_series)
# Result: Loads shifted from peak to off-peak hours
```

Include comprehensive docstrings with mathematical formulas.
Validate energy conservation (total kWh should not increase).
Use vectorized pandas operations for performance.
```

---

## 🗒️ Implementation Notes

### Vectorized Operations

For performance with large datasets:
```python
# Good (vectorized)
load_profile['new_load'] = load_profile['load_kw'] * (price_ratio ** elasticity)

# Bad (iterative)
for idx, row in load_profile.iterrows():
    row['new_load'] = row['load_kw'] * (price_ratio ** elasticity)
```

### Shiftable Load Assumptions

Typical residential shiftable loads:
- Dishwasher: 1-2 kWh, shift window 0-12 hours
- Washing machine: 0.5-1.5 kWh, shift window 0-8 hours
- EV charging: 10-50 kWh, shift window 0-10 hours
- Heat pump (if storage): Variable, shift window 2-4 hours

---

## 🔄 Related Issues

- **Depends on**: #2 (Needs TOUTariff for price signals)
- **Blocks**: #4 (UI will show with/without demand response)
- **Blocks**: #5 (Bill visualization will compare scenarios)

---

**Created**: [Date]  
**Last Updated**: [Date]  
**Status**: Open / In Progress / Complete
