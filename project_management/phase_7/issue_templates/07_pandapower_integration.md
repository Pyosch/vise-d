# [Phase 7.2.2] Create Pandapower Network Integration Module

**Labels**: `enhancement`, `phase-7`, `priority-medium`, `copilot-ready`, `grid-analysis`  
**Milestone**: Phase 7.2 - Real-Time Pricing & Grid Integration  
**Estimated Time**: 3-4 days  
**Dependencies**: Issue #2 (TOUTariff), Issue #6 (RTPTariff), existing `pp_networks.py`  
**Assignee**: [Your name]

---

## 📋 Description

Create a module to integrate tariff-driven demand response with Pandapower network analysis. This enables simulation of how tariff designs impact grid congestion, line loadings, and voltage levels.

---

## 🎯 Context

- **Part of**: Phase 7.2 - Real-Time Pricing & Grid Integration
- **Reference**: `roadmap.md` Section 7.2, Task 2.4
- **Integration Points**: Pandapower networks (existing `pp_networks.py`), tariff models, demand response
- **Purpose**: Evaluate grid impacts of tariff-driven load changes

---

## 📦 Requirements

### Module: `market_design/grid_integration.py`

Create a new module with the following functions:

---

### Function 1: `apply_tariff_to_network()`

**Purpose**: Apply tariff-driven load changes to a Pandapower network and run power flow

**Signature**:
```python
def apply_tariff_to_network(
    net: pandapower.auxiliary.pandapowerNet,
    tariff: BaseTariff,
    load_profiles: pd.DataFrame,
    timestamp: datetime,
    demand_response: DemandResponseModel = None
) -> Tuple[pandapower.auxiliary.pandapowerNet, Dict]:
```

**Parameters**:
- `net`: Pandapower network object (e.g., CIGRE MV network)
- `tariff`: Any tariff object (TOUTariff, RTPTariff, etc.)
- `load_profiles`: DataFrame with columns ['bus_id', 'timestamp', 'load_kw']
  - Maps each load to a bus in the network
- `timestamp`: Specific time to simulate
- `demand_response`: Optional DR model to apply before power flow

**Returns**:
- `net`: Modified Pandapower network with updated loads
- `metrics`: Dict with grid state metrics (see below)

**Process**:
1. Extract load values for given timestamp from load_profiles
2. If demand_response provided: Apply DR to modify loads
3. Update `net.load` table with new P_mw values
4. Run power flow: `pp.runpp(net)`
5. Extract metrics from converged network
6. Return network and metrics

**Metrics Dict**:
```python
{
    'timestamp': datetime,
    'converged': bool,
    'total_load_mw': float,
    'total_generation_mw': float,
    'total_losses_mw': float,
    'max_line_loading_percent': float,
    'mean_line_loading_percent': float,
    'lines_overloaded': int,  # Count of lines > 100%
    'min_voltage_pu': float,
    'max_voltage_pu': float,
    'voltage_violations': int,  # Count of buses outside 0.95-1.05 pu
    'congested_lines': List[int],  # Line indices > 80% loading
}
```

---

### Function 2: `simulate_tariff_impact()`

**Purpose**: Run time-series simulation of tariff impact on network

**Signature**:
```python
def simulate_tariff_impact(
    net: pandapower.auxiliary.pandapowerNet,
    tariff: BaseTariff,
    load_profiles: pd.DataFrame,
    demand_response: DemandResponseModel = None,
    start_time: datetime = None,
    duration_hours: int = 24
) -> pd.DataFrame:
```

**Parameters**:
- `net`: Pandapower network
- `tariff`: Tariff to simulate
- `load_profiles`: Time-series load data for all buses
- `demand_response`: Optional DR model
- `start_time`: Simulation start (default: first timestamp in load_profiles)
- `duration_hours`: How many hours to simulate (default: 24)

**Returns**:
- DataFrame with columns: ['timestamp', 'converged', 'total_load_mw', 'max_line_loading_percent', 'min_voltage_pu', ...]
  - One row per hour

**Process**:
1. Loop through each hour in duration
2. Call `apply_tariff_to_network()` for each timestamp
3. Collect metrics into list
4. Return as DataFrame

---

### Function 3: `identify_congestion_hotspots()`

**Purpose**: Identify lines and transformers with chronic congestion

**Signature**:
```python
def identify_congestion_hotspots(
    simulation_results: pd.DataFrame,
    threshold: float = 0.8
) -> Dict[str, List[int]]:
```

**Parameters**:
- `simulation_results`: Output from `simulate_tariff_impact()`
- `threshold`: Loading percentage threshold (default: 80%)

**Returns**:
```python
{
    'critical_hours': List[datetime],  # Hours with any overloads
    'frequently_congested_lines': List[int],  # Lines > threshold in >50% of hours
    'peak_loading_hour': datetime,  # Hour with max loading
    'recommendations': List[str],  # Text suggestions for tariff design
}
```

---

### Function 4: `compare_tariff_scenarios()`

**Purpose**: Compare grid impacts of multiple tariff designs

**Signature**:
```python
def compare_tariff_scenarios(
    net: pandapower.auxiliary.pandapowerNet,
    scenarios: Dict[str, Dict],
    load_profiles: pd.DataFrame,
    duration_hours: int = 24
) -> pd.DataFrame:
```

**Parameters**:
- `net`: Pandapower network
- `scenarios`: Dict of scenario definitions
  ```python
  {
      'Baseline': {
          'tariff': None,  # Flat rate / no tariff
          'demand_response': None
      },
      'TOU 2-Period': {
          'tariff': tou_tariff_obj,
          'demand_response': dr_model_passive
      },
      'RTP': {
          'tariff': rtp_tariff_obj,
          'demand_response': dr_model_active
      }
  }
  ```
- `load_profiles`: Load data
- `duration_hours`: Simulation duration

**Returns**:
- DataFrame comparing scenarios:
  ```
  | scenario      | avg_line_loading | max_line_loading | voltage_violations | peak_load_mw |
  |---------------|------------------|------------------|--------------------|--------------|
  | Baseline      | 45.2%            | 87.3%            | 0                  | 12.5         |
  | TOU 2-Period  | 42.1%            | 79.8%            | 0                  | 11.2         |
  | RTP           | 40.5%            | 75.2%            | 0                  | 10.8         |
  ```

---

## 🔧 Technical Requirements

### Pandapower Integration

**Key Functions to Use**:
```python
import pandapower as pp
import pandapower.networks as pn

# Load standard network
net = pn.create_cigre_network_mv()

# Update loads
net.load.at[load_idx, 'p_mw'] = new_load_mw

# Run power flow
pp.runpp(net)

# Check convergence
if net.converged:
    # Extract results
    line_loading = net.res_line.loading_percent.values
    bus_voltage = net.res_bus.vm_pu.values
```

### Load Mapping Strategy

Map customer load profiles to Pandapower buses:

```python
# Approach 1: Simple aggregation
# - Group customers by bus
# - Sum loads at each bus
# - Update net.load table

def map_loads_to_buses(load_profiles, bus_mapping, timestamp):
    """
    Parameters:
    - load_profiles: DataFrame ['customer_id', 'timestamp', 'load_kw']
    - bus_mapping: Dict {customer_id: bus_id}
    - timestamp: datetime
    
    Returns:
    - DataFrame ['bus_id', 'load_mw']
    """
    # Filter to timestamp
    loads_at_time = load_profiles[load_profiles['timestamp'] == timestamp]
    
    # Add bus_id column
    loads_at_time['bus_id'] = loads_at_time['customer_id'].map(bus_mapping)
    
    # Aggregate by bus
    bus_loads = loads_at_time.groupby('bus_id')['load_kw'].sum() / 1000  # Convert to MW
    
    return bus_loads.reset_index(columns=['bus_id', 'load_mw'])
```

### Error Handling

```python
try:
    pp.runpp(net)
    if not net.converged:
        warnings.warn(f"Power flow did not converge at {timestamp}")
        # Return metrics with converged=False
except Exception as e:
    logging.error(f"Power flow failed: {str(e)}")
    # Return None or default metrics
```

---

## ✅ Acceptance Criteria

### Functionality
- [ ] `apply_tariff_to_network()` successfully runs power flow
- [ ] Metrics are extracted correctly from network results
- [ ] `simulate_tariff_impact()` runs 24-hour simulation
- [ ] Handles non-convergence gracefully
- [ ] `identify_congestion_hotspots()` finds overloaded lines
- [ ] `compare_tariff_scenarios()` generates comparison DataFrame

### Integration
- [ ] Works with existing CIGRE MV network from `pp_networks.py`
- [ ] Integrates with TOUTariff and RTPTariff classes
- [ ] Integrates with DemandResponseModel
- [ ] Load profiles map correctly to network buses

### Code Quality
- [ ] Python 3.11+ type hints
- [ ] Google-style docstrings with examples
- [ ] Passes black and flake8
- [ ] Proper error handling and logging

### Testing
- [ ] Unit tests for load mapping
- [ ] Integration test with CIGRE network
- [ ] Test convergence failure scenarios
- [ ] >85% code coverage

---

## 🧪 Testing Requirements

Create tests in `market_design/tests/test_grid_integration.py`

### Test Cases:

**Unit Tests**:
```python
def test_map_loads_to_buses():
    """Test load aggregation to network buses"""
    # Create sample load_profiles and bus_mapping
    # Verify correct aggregation

def test_apply_tariff_baseline():
    """Test applying baseline (no tariff) to network"""
    # Load CIGRE network, apply flat loads, verify power flow

def test_apply_tariff_with_tou():
    """Test applying TOU tariff to network"""
    # Create TOU tariff, apply to network, verify loads reduced during peak
```

**Integration Tests**:
```python
def test_simulate_24h_cigre_network():
    """Test 24-hour simulation with CIGRE MV network"""
    # Run full 24-hour simulation
    # Verify all hours converge
    # Check results DataFrame structure

def test_compare_tou_vs_baseline():
    """Test comparison of TOU vs baseline scenario"""
    # Define both scenarios
    # Run comparison
    # Verify TOU reduces peak loading

def test_congestion_identification():
    """Test identification of congested lines"""
    # Run simulation with known overload
    # Verify congestion hotspot detection
```

**Edge Cases**:
```python
def test_handle_non_convergence():
    """Test graceful handling when power flow doesn't converge"""
    # Create scenario that won't converge (extreme loads)
    # Verify proper error handling

def test_empty_load_profiles():
    """Test behavior with no loads"""
    # Should handle gracefully or raise informative error
```

---

## 📚 Reference Materials

- **Roadmap**: `roadmap.md` Section 7.2, Task 2.4
- **Existing Network Code**: `pp_networks.py` (existing Pandapower usage)
- **Pandapower Docs**: https://pandapower.readthedocs.io/
  - Power flow: https://pandapower.readthedocs.io/en/latest/powerflow.html
  - CIGRE networks: https://pandapower.readthedocs.io/en/latest/networks/cigre.html
- **Tariff Classes**: `market_design/tariff_models.py`
- **Demand Response**: `market_design/demand_response.py`

---

## 🤖 GitHub Copilot Prompt Suggestion

```
@workspace Create grid_integration.py module in market_design/

Implement functions (see issue #7):

1. apply_tariff_to_network(net, tariff, load_profiles, timestamp, demand_response=None)
   - Map loads to Pandapower buses
   - Apply demand response if provided
   - Update net.load table
   - Run pp.runpp(net)
   - Extract metrics: line loadings, voltages, losses
   - Return (net, metrics_dict)

2. simulate_tariff_impact(net, tariff, load_profiles, dr_model, duration_hours=24)
   - Loop through hours
   - Call apply_tariff_to_network() each hour
   - Collect metrics into DataFrame
   - Return time-series results

3. identify_congestion_hotspots(simulation_results, threshold=0.8)
   - Analyze results for lines > threshold
   - Identify frequently congested lines
   - Return recommendations dict

4. compare_tariff_scenarios(net, scenarios_dict, load_profiles, duration=24)
   - Run simulation for each scenario
   - Aggregate metrics (avg, max)
   - Return comparison DataFrame

Integration:
- Use existing pp_networks.py patterns
- Import TOUTariff, RTPTariff from tariff_models
- Import DemandResponseModel from demand_response
- Handle power flow non-convergence gracefully

Example usage:
```python
from pandapower.networks import create_cigre_network_mv
net = create_cigre_network_mv()
tou = TOUTariff(...)
results = simulate_tariff_impact(net, tou, load_profiles, duration_hours=24)
hotspots = identify_congestion_hotspots(results)
```

Use Python 3.11+ type hints, comprehensive error handling.
```

---

## 🗒️ Implementation Notes

### Sample Load-to-Bus Mapping

For CIGRE MV network (14 buses), create sample mapping:

```python
# Example: Distribute 100 customers across network buses
# Focus on buses with existing loads

bus_mapping = {
    # Residential customers on LV buses
    **{i: 3 for i in range(0, 20)},    # 20 customers on bus 3
    **{i: 4 for i in range(20, 40)},   # 20 customers on bus 4
    # ... etc
}

# Or random assignment for testing
import random
bus_mapping = {i: random.choice([3,4,5,6,7,8]) for i in range(100)}
```

### Performance Optimization

For large simulations (1000+ customers, 168 hours):

```python
# Optimize 1: Vectorize load updates
net.load.loc[:, 'p_mw'] = bus_loads_array

# Optimize 2: Use pp.runpp_3ph() only if needed (slower)
# Standard runpp() sufficient for most cases

# Optimize 3: Cache network state between iterations
# Don't reload network each time
```

---

## 🔄 Related Issues

- **Depends on**: #2 (TOUTariff), #6 (RTPTariff), #3 (DemandResponse)
- **Uses**: Existing `pp_networks.py` module
- **Blocks**: #8 (Grid impact visualization needs this data)
- **Enhances**: Phase 7.1 (adds grid dimension to bill analysis)

---

**Created**: [Date]  
**Last Updated**: [Date]  
**Status**: Open / In Progress / Complete
