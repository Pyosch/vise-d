# [Phase 7.3.1] Implement VariableGridFee Class

**Labels**: `enhancement`, `phase-7`, `priority-low`, `copilot-ready`, `grid-fees`  
**Milestone**: Phase 7.3 - Advanced Features & Export  
**Estimated Time**: 2-3 days  
**Dependencies**: Issue #2 (BaseTariff interface), Issue #7 (Grid integration for usage data)  
**Assignee**: [Your name]

---

## 📋 Description

Implement the `VariableGridFee` class for location-based and capacity-based grid usage fees. This enables modeling of network charges that vary by grid zone and include both energy-based fees and capacity charges based on peak demand.

---

## 🎯 Context

- **Part of**: Phase 7.3 - Advanced Features & Export
- **Reference**: `roadmap.md` Section 7.3, Task 3.1
- **Real-World Context**: Many European DSOs are transitioning to capacity-based grid fees to better reflect actual grid costs
- **Integration Points**: Works alongside tariff models (TOU, RTP), grid simulation results

---

## 📦 Requirements

### Class Implementation: `VariableGridFee`

Location: `market_design/tariff_models.py` (add to existing file)

**Note**: This is NOT a tariff (doesn't inherit from BaseTariff), but a separate fee structure that's added on top of energy tariffs.

**Properties**:
```python
- name: str - Fee structure name (e.g., "Zone-Based Grid Fee 2025")
- description: str - Human-readable description
- base_fee_euro_per_kwh: float - Base network usage fee (€/kWh)
- zone_multipliers: Dict[str, float] - Multipliers by grid zone
  Example: {'urban': 0.8, 'suburban': 1.0, 'rural': 1.2}
- capacity_charge_enabled: bool - Whether to include capacity charge
- capacity_charge_euro_per_kw_year: float - Annual capacity charge (€/kW/year)
- measurement_window_months: int - Window for measuring peak (typically 12 months)
- voltage_level_multipliers: Dict[str, float] - Multipliers by connection voltage
  Example: {'lv': 1.0, 'mv': 0.7, 'hv': 0.5}
```

**Methods**:

1. `__init__(self, name: str, base_fee: float, zone_multipliers: Dict[str, float] = None, capacity_charge_enabled: bool = False, capacity_charge_rate: float = 0.0)`
   - Initialize grid fee structure
   - Validate base_fee >= 0
   - Default zone_multipliers to {'default': 1.0} if None

2. `calculate_energy_fee(self, energy_kwh: float, zone: str = 'default', voltage_level: str = 'lv') -> float`
   - Calculate energy-based grid fee
   - Formula: `base_fee * zone_multiplier * voltage_multiplier * energy_kwh`
   - Return fee in euros

3. `calculate_capacity_charge(self, peak_demand_kw: float, zone: str = 'default') -> float`
   - Calculate annual capacity charge based on peak demand
   - Formula: `capacity_charge_rate * zone_multiplier * peak_demand_kw`
   - Return annual charge in euros

4. `calculate_monthly_capacity_charge(self, peak_demand_kw: float, zone: str = 'default') -> float`
   - Monthly capacity charge (annual / 12)
   - Formula: `calculate_capacity_charge() / 12`

5. `calculate_total_fee(self, load_profile: pd.DataFrame, zone: str = 'default', voltage_level: str = 'lv') -> Dict`
   - Calculate complete grid fee for a load profile
   - load_profile columns: ['timestamp', 'load_kw']
   - Returns dict:
     ```python
     {
         'energy_fee_euro': float,
         'capacity_charge_annual_euro': float,
         'capacity_charge_monthly_euro': float,
         'total_annual_euro': float,
         'peak_demand_kw': float,
         'total_energy_kwh': float
     }
     ```

6. `get_zone_multiplier(self, zone: str) -> float`
   - Helper to get zone multiplier with fallback
   - If zone not found, return 1.0 and warn

7. `compare_zones(self, load_profile: pd.DataFrame, zones: List[str]) -> pd.DataFrame`
   - Compare costs across different zones
   - Returns DataFrame with columns: ['zone', 'energy_fee', 'capacity_charge', 'total_fee']

8. `simulate_capacity_charge_scenarios(self, annual_energy_kwh: float, load_factor: float, zone: str = 'default') -> Dict`
   - Simulate capacity charges for different load profiles
   - load_factor: ratio of average to peak load (0-1)
   - Lower load factor = higher peaks = higher capacity charge
   - Useful for showing customers cost impact of peak management

---

## 🔧 Technical Requirements

### Zone Definition Standards

Support common European grid zone classifications:

```python
# Typical zone definitions
STANDARD_ZONES = {
    'urban_core': 0.75,      # Dense urban, low network costs per customer
    'urban': 0.85,
    'suburban': 1.0,         # Baseline
    'rural': 1.25,           # Longer lines, fewer customers
    'remote': 1.5            # Very high network costs
}

# Alternative: By grid congestion level
CONGESTION_ZONES = {
    'low_congestion': 0.9,
    'medium_congestion': 1.0,
    'high_congestion': 1.3,
    'critical_congestion': 1.6
}
```

### Capacity Charge Calculation Details

**Rolling Window for Peak Measurement**:
```python
def find_peak_demand(load_profile: pd.DataFrame, window_months: int = 12) -> float:
    """
    Find peak demand over measurement window.
    
    Parameters:
    - load_profile: DataFrame with ['timestamp', 'load_kw']
    - window_months: Measurement period (typically 12)
    
    Returns:
    - Peak demand in kW (max of all hourly averages)
    """
    # If data < window_months, use all available data
    end_date = load_profile['timestamp'].max()
    start_date = end_date - pd.DateOffset(months=window_months)
    
    window_data = load_profile[load_profile['timestamp'] >= start_date]
    
    if len(window_data) == 0:
        raise ValueError("No data in measurement window")
    
    peak_kw = window_data['load_kw'].max()
    
    return peak_kw
```

### Validation and Error Handling

```python
def validate_zone(self, zone: str) -> None:
    """Validate that zone exists in zone_multipliers"""
    if zone not in self.zone_multipliers:
        available = ', '.join(self.zone_multipliers.keys())
        warnings.warn(
            f"Zone '{zone}' not found. Available zones: {available}. "
            f"Using multiplier 1.0"
        )

def validate_voltage_level(self, voltage_level: str) -> None:
    """Validate voltage level"""
    valid_levels = ['lv', 'mv', 'hv']
    if voltage_level not in valid_levels:
        raise ValueError(
            f"Invalid voltage level: {voltage_level}. "
            f"Must be one of {valid_levels}"
        )
```

---

## ✅ Acceptance Criteria

### Functionality
- [ ] Class calculates energy fees correctly
- [ ] Zone multipliers are applied correctly
- [ ] Voltage level multipliers work
- [ ] Capacity charge calculation is accurate
- [ ] Peak demand is found correctly from load profile
- [ ] `calculate_total_fee()` returns all components
- [ ] `compare_zones()` generates comparison DataFrame

### Code Quality
- [ ] Python 3.11+ type hints on all methods
- [ ] Google-style docstrings with examples
- [ ] Passes `black --check` and `flake8`
- [ ] Input validation with helpful error messages
- [ ] No syntax errors

### Integration
- [ ] Works with load profiles from demand response model
- [ ] Can be combined with TOUTariff and RTPTariff
- [ ] Integrates with grid simulation results

### Testing
- [ ] Unit tests cover >90% of code
- [ ] All edge cases tested

---

## 🧪 Testing Requirements

Create tests in `market_design/tests/test_tariff_models.py` (extend existing)

### Test Cases:

**Normal Operation**:
```python
def test_variable_grid_fee_energy_only():
    """Test energy fee calculation without capacity charge"""
    fee = VariableGridFee(
        name="Basic Grid Fee",
        base_fee=0.05,  # 5 cents/kWh
        zone_multipliers={'urban': 0.8, 'rural': 1.2}
    )
    
    # Urban: 100 kWh * €0.05 * 0.8 = €4.00
    assert fee.calculate_energy_fee(100, zone='urban') == 4.0
    
    # Rural: 100 kWh * €0.05 * 1.2 = €6.00
    assert fee.calculate_energy_fee(100, zone='rural') == 6.0

def test_variable_grid_fee_with_capacity_charge():
    """Test capacity charge calculation"""
    fee = VariableGridFee(
        name="Capacity Grid Fee",
        base_fee=0.03,
        capacity_charge_enabled=True,
        capacity_charge_rate=50.0  # €50/kW/year
    )
    
    # Peak 10 kW → €50 * 10 = €500/year
    annual = fee.calculate_capacity_charge(10.0)
    assert annual == 500.0
    
    # Monthly: €500 / 12 ≈ €41.67
    monthly = fee.calculate_monthly_capacity_charge(10.0)
    assert abs(monthly - 41.67) < 0.01

def test_total_fee_calculation():
    """Test complete fee calculation from load profile"""
    # Create sample load profile
    timestamps = pd.date_range('2025-01-01', periods=24, freq='H')
    loads = [5, 5, 5, 5, 5, 6, 8, 10, 8, 6, 5, 5, 
             5, 5, 6, 7, 8, 10, 9, 7, 6, 5, 5, 5]  # Peak = 10 kW
    
    load_profile = pd.DataFrame({
        'timestamp': timestamps,
        'load_kw': loads
    })
    
    fee = VariableGridFee(
        name="Test",
        base_fee=0.05,
        capacity_charge_enabled=True,
        capacity_charge_rate=50.0
    )
    
    result = fee.calculate_total_fee(load_profile, zone='default')
    
    # Verify structure
    assert 'energy_fee_euro' in result
    assert 'capacity_charge_annual_euro' in result
    assert 'peak_demand_kw' in result
    assert result['peak_demand_kw'] == 10.0
```

**Edge Cases**:
```python
def test_unknown_zone_fallback():
    """Test that unknown zone uses multiplier 1.0 with warning"""
    fee = VariableGridFee(
        name="Test",
        base_fee=0.05,
        zone_multipliers={'zone_a': 0.8}
    )
    
    with warnings.catch_warnings(record=True) as w:
        result = fee.calculate_energy_fee(100, zone='unknown')
        assert len(w) == 1
        assert "not found" in str(w[0].message)
        assert result == 5.0  # 100 * 0.05 * 1.0

def test_voltage_level_multipliers():
    """Test voltage level affects pricing"""
    fee = VariableGridFee(
        name="Voltage Test",
        base_fee=0.05,
        voltage_level_multipliers={'lv': 1.0, 'mv': 0.7}
    )
    
    # LV: higher fee
    lv_fee = fee.calculate_energy_fee(100, voltage_level='lv')
    assert lv_fee == 5.0
    
    # MV: 30% lower fee
    mv_fee = fee.calculate_energy_fee(100, voltage_level='mv')
    assert mv_fee == 3.5

def test_zero_load_profile():
    """Test behavior with zero loads"""
    load_profile = pd.DataFrame({
        'timestamp': pd.date_range('2025-01-01', periods=24, freq='H'),
        'load_kw': [0] * 24
    })
    
    fee = VariableGridFee(
        name="Test",
        base_fee=0.05,
        capacity_charge_enabled=True,
        capacity_charge_rate=50.0
    )
    
    result = fee.calculate_total_fee(load_profile)
    assert result['peak_demand_kw'] == 0.0
    assert result['capacity_charge_annual_euro'] == 0.0
```

**Scenario Comparisons**:
```python
def test_compare_zones():
    """Test zone comparison functionality"""
    load_profile = pd.DataFrame({
        'timestamp': pd.date_range('2025-01-01', periods=24, freq='H'),
        'load_kw': [5] * 24
    })
    
    fee = VariableGridFee(
        name="Multi-Zone",
        base_fee=0.05,
        zone_multipliers={'urban': 0.8, 'suburban': 1.0, 'rural': 1.2}
    )
    
    comparison = fee.compare_zones(load_profile, ['urban', 'suburban', 'rural'])
    
    assert len(comparison) == 3
    assert 'zone' in comparison.columns
    assert 'total_fee' in comparison.columns
    # Urban should be cheapest
    assert comparison.loc[comparison['zone'] == 'urban', 'total_fee'].values[0] < \
           comparison.loc[comparison['zone'] == 'rural', 'total_fee'].values[0]

def test_load_factor_impact_on_capacity_charge():
    """Test that lower load factor increases capacity charge impact"""
    fee = VariableGridFee(
        name="Capacity Test",
        base_fee=0.03,
        capacity_charge_enabled=True,
        capacity_charge_rate=50.0
    )
    
    annual_energy = 50000  # kWh/year
    
    # High load factor (flat load)
    scenario_high_lf = fee.simulate_capacity_charge_scenarios(
        annual_energy, load_factor=0.8
    )
    
    # Low load factor (peaky load)
    scenario_low_lf = fee.simulate_capacity_charge_scenarios(
        annual_energy, load_factor=0.3
    )
    
    # Lower load factor → higher peak → higher capacity charge
    assert scenario_low_lf['capacity_charge_euro'] > scenario_high_lf['capacity_charge_euro']
```

---

## 📚 Reference Materials

- **Roadmap**: `roadmap.md` Section 7.3, Task 3.1
- **Real-World Examples**:
  - German grid fees: https://www.bundesnetzagentur.de/
  - Austrian capacity charges: E-Control documentation
- **Base Class**: `BaseTariff` pattern (though this doesn't inherit from it)
- **Load Profiles**: Integration with demand response load profiles

---

## 🤖 GitHub Copilot Prompt Suggestion

```
@workspace Create VariableGridFee class in market_design/tariff_models.py

Requirements (see issue #9):

Class: VariableGridFee (does NOT inherit from BaseTariff - separate fee structure)

Properties:
- name, description: str
- base_fee_euro_per_kwh: float - Base network fee
- zone_multipliers: Dict[str, float] - e.g., {'urban': 0.8, 'rural': 1.2}
- capacity_charge_enabled: bool
- capacity_charge_euro_per_kw_year: float
- voltage_level_multipliers: Dict[str, float] - e.g., {'lv': 1.0, 'mv': 0.7}

Methods:
1. calculate_energy_fee(energy_kwh, zone, voltage_level)
   - Formula: base_fee * zone_mult * voltage_mult * energy_kwh

2. calculate_capacity_charge(peak_demand_kw, zone)
   - Annual charge: capacity_rate * zone_mult * peak_kw

3. calculate_monthly_capacity_charge(peak_demand_kw, zone)
   - Monthly: annual / 12

4. calculate_total_fee(load_profile: DataFrame, zone, voltage_level)
   - Find peak from load_profile
   - Calculate energy fee (sum of all kWh)
   - Calculate capacity charge if enabled
   - Return dict with all components

5. compare_zones(load_profile, zones: List[str])
   - Calculate fees for each zone
   - Return comparison DataFrame

6. simulate_capacity_charge_scenarios(annual_energy_kwh, load_factor, zone)
   - Show impact of load factor on capacity charges
   - load_factor = avg_load / peak_load

Include validation:
- Check zone exists (fallback to 1.0 if not)
- Validate voltage_level in ['lv', 'mv', 'hv']
- base_fee >= 0, capacity_charge_rate >= 0

Example usage:
```python
fee = VariableGridFee(
    name="Zone-Based Grid Fee 2025",
    base_fee=0.05,
    zone_multipliers={'urban': 0.8, 'rural': 1.2},
    capacity_charge_enabled=True,
    capacity_charge_rate=50.0
)

result = fee.calculate_total_fee(load_profile, zone='urban', voltage_level='lv')
print(f"Total annual fee: €{result['total_annual_euro']:.2f}")
```

Use Python 3.11+ type hints, Google-style docstrings.
```

---

## 🗒️ Implementation Notes

### Real-World Context

Many European DSOs are transitioning to capacity-based fees:

**Germany (planned)**:
- Current: Mostly energy-based (€/kWh)
- Future: Hybrid with capacity component
- Goal: Incentivize peak reduction

**Austria**:
- Already uses capacity charges
- Measured over 12-month rolling window
- Significant cost driver for high-peak customers

**Netherlands**:
- Zone-based fees by grid stress level
- Dynamic adjustments based on congestion

### UI Integration Suggestion

When implementing UI (separate issue), include calculator:

```python
# In Streamlit UI
st.subheader("Grid Fee Calculator")

col1, col2 = st.columns(2)
with col1:
    zone = st.selectbox("Grid Zone", ['urban', 'suburban', 'rural'])
    voltage = st.selectbox("Connection Level", ['lv', 'mv', 'hv'])

with col2:
    annual_energy = st.number_input("Annual Energy (kWh)", value=5000)
    peak_demand = st.number_input("Peak Demand (kW)", value=10.0)

if st.button("Calculate Grid Fees"):
    # Show energy fee + capacity charge breakdown
    # Compare to other zones
```

---

## 🔄 Related Issues

- **Depends on**: #2 (BaseTariff interface for consistency), #7 (Grid integration)
- **Used by**: Revenue analysis (DSO income from grid fees)
- **Complements**: #2 (TOUTariff), #6 (RTPTariff) - grid fees added on top
- **Blocks**: #10 (PDF export will include grid fee breakdown)

---

**Created**: [Date]  
**Last Updated**: [Date]  
**Status**: Open / In Progress / Complete
