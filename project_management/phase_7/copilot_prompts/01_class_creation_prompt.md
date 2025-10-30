# Copilot Prompt Template: Class Creation

Use this template when asking GitHub Copilot to create new classes in the `market_design/` module.

---

## Generic Class Creation Prompt

```
@workspace I need to create the [ClassName] class in market_design/[module_name].py

Context:
- Part of Phase 7: Tariff Design Studio (see roadmap.md Section 7.2)
- Integrates with existing [related_component] in [related_file]
- Follows the code style in technologies/[reference_file].py

Requirements:
1. Class: [ClassName]
   - Inherits from: [BaseClass] (if applicable)
   - Purpose: [brief description]
   
2. Properties/Attributes:
   - [attribute1]: [type] - [description]
   - [attribute2]: [type] - [description]
   
3. Methods:
   - __init__(self, [params]): Initialize with [description]
   - [method1](self, [params]) -> [return_type]: [description]
   - [method2](self, [params]) -> [return_type]: [description]
   
4. Validation:
   - [validation_rule_1]
   - [validation_rule_2]
   
5. Style Requirements:
   - Python 3.11+ type hints on all methods
   - Google-style docstrings
   - Input validation with clear error messages
   - PEP 8 compliant

Example Usage:
```python
[Show example code of how the class should be used]
```

Reference:
- See issue #[issue_number] for detailed requirements
- Architecture in roadmap.md Section 7.0
```

---

## Example 1: TOUTariff Class

```
@workspace I need to create the TOUTariff class in market_design/tariff_models.py

Context:
- Part of Phase 7: Tariff Design Studio (see roadmap.md Section 7.2)
- Inherits from BaseTariff abstract class (already defined in same file)
- Similar to existing component classes in technologies/photovoltaics.py

Requirements:
1. Class: TOUTariff
   - Inherits from: BaseTariff
   - Purpose: Time-of-Use tariff with defined time periods and fixed prices
   
2. Properties/Attributes:
   - time_periods: Dict[str, str] - Maps period names to time ranges (e.g., {"peak": "16:00-20:00"})
   - prices: Dict[str, float] - Maps period names to prices in €/kWh
   - name: str - Tariff name for display
   - description: Optional[str] - Human-readable description
   
3. Methods:
   - __init__(self, time_periods: Dict[str, str], prices: Dict[str, float], name: str, description: str = "")
   - calculate_price(self, timestamp: datetime) -> float: Determine which period timestamp falls into, return price
   - calculate_bill(self, load_profile: pd.DataFrame) -> float: Sum load_kw * price for each hour
   - add_time_period(self, period_name: str, time_range: str, price: float): Add/update a period
   - validate_periods(self) -> bool: Check that periods cover full 24 hours without gaps
   - get_period_at_time(self, timestamp: datetime) -> str: Return period name for given time
   
4. Validation:
   - All prices must be > 0 (raise ValueError if not)
   - Time periods must cover full 24 hours (raise ValueError if gaps)
   - Time ranges in format "HH:MM-HH:MM" (raise ValueError if invalid)
   - Period names in time_periods and prices must match
   
5. Style Requirements:
   - Python 3.11+ type hints on all methods
   - Google-style docstrings with Parameters, Returns, Raises, Examples
   - Input validation with clear error messages
   - PEP 8 compliant

Example Usage:
```python
tou = TOUTariff(
    time_periods={
        "peak": "16:00-20:00",
        "off_peak": "20:00-16:00"
    },
    prices={
        "peak": 0.35,
        "off_peak": 0.15
    },
    name="Residential TOU 2-Period"
)

# Calculate price at specific time
price = tou.calculate_price(datetime(2025, 10, 29, 18, 0))  # Should return 0.35 (peak)

# Calculate bill from load profile
load_df = pd.DataFrame({
    'timestamp': pd.date_range('2025-10-29', periods=24, freq='H'),
    'load_kw': [2.5] * 24
})
bill = tou.calculate_bill(load_df)  # Should return total in euros
```

Reference:
- See issue #[TOUTariff_issue_number] for detailed requirements
- Architecture in roadmap.md Section 7.0
- Abstract base class BaseTariff in same file
```

---

## Example 2: DemandResponseModel Class

```
@workspace I need to create the DemandResponseModel class in market_design/demand_response.py

Context:
- Part of Phase 7.1.3: Basic demand response modeling
- Models price-responsive consumer behavior for tariff simulations
- Integrates with TOUTariff and RTPTariff classes

Requirements:
1. Class: DemandResponseModel
   - Purpose: Model load shifting and reduction based on price signals
   
2. Properties/Attributes:
   - elasticity: float - Price elasticity coefficient (typically -0.1 to -0.3)
   - behavior_type: str - Consumer type: "passive", "active", or "automated"
   - flexibility_window: int - Hours over which load can shift (e.g., 6 hours)
   - max_shift_percentage: float - Maximum % of load that can shift (0.0-1.0)
   
3. Methods:
   - __init__(self, elasticity: float = -0.15, behavior_type: str = "passive", ...)
   - apply_demand_response(self, load_profile: pd.DataFrame, price_signal: pd.Series) -> pd.DataFrame
     Returns modified load profile with shifted/reduced loads
   - calculate_load_change(self, original_load: float, price_ratio: float) -> float
     Calculate new load based on elasticity formula
   - shift_load(self, load_profile: pd.DataFrame, from_hours: List[int], to_hours: List[int]) -> pd.DataFrame
     Shift loads from high-price to low-price hours
   - validate_energy_conservation(self, original: pd.DataFrame, modified: pd.DataFrame) -> bool
     Ensure total energy is conserved (accounting for elasticity-based reduction)
   
4. Validation:
   - elasticity must be negative (raise ValueError if positive)
   - behavior_type must be in ["passive", "active", "automated"]
   - flexibility_window must be > 0
   - max_shift_percentage must be in range [0.0, 1.0]
   - Total shifted energy cannot exceed max_shift_percentage
   
5. Style Requirements:
   - Python 3.11+ type hints
   - Google-style docstrings with mathematical formulas in docstring
   - Unit tests covering edge cases (see test_demand_response.py)

Example Usage:
```python
dr_model = DemandResponseModel(
    elasticity=-0.15,
    behavior_type="active",
    flexibility_window=6,
    max_shift_percentage=0.3
)

# Apply to load profile with TOU pricing
load_df = pd.DataFrame({
    'timestamp': pd.date_range('2025-10-29', periods=24, freq='H'),
    'load_kw': [3.0, 2.8, 2.5, ...],
})
price_series = tou_tariff.get_prices_for_profile(load_df)

modified_load = dr_model.apply_demand_response(load_df, price_series)
# Result: Loads shifted from peak (16-20h) to off-peak hours
```

Reference:
- See roadmap.md Section 7.2 Phase 1 Task 1.3
- Literature: Price elasticity typically -0.1 to -0.3 for residential
```

---

## Example 3: Visualization Function

```
@workspace I need to create a bill impact visualization function in market_design/visualizations.py

Context:
- Part of Phase 7.1.5: Bill impact visualization
- Creates interactive Plotly charts for Streamlit dashboard
- Follows style of existing charts in dashboard.py

Requirements:
1. Function: create_bill_impact_boxplot
   - Purpose: Compare customer bill distributions across tariff scenarios
   
2. Parameters:
   - baseline_bills: pd.DataFrame - Columns: ['customer_id', 'bill_euro']
   - scenario_bills: pd.DataFrame - Same structure as baseline
   - scenario_name: str - Name for legend (e.g., "TOU 3-Period")
   - title: str - Chart title (default: "Bill Impact Comparison")
   
3. Returns:
   - plotly.graph_objects.Figure - Interactive box plot
   
4. Chart Features:
   - Side-by-side box plots (baseline vs scenario)
   - Show median, quartiles, outliers
   - Add mean markers (as diamonds)
   - Color scheme: baseline=gray, scenario=blue
   - Add summary statistics annotation (mean savings, % customers saving)
   - Interactive hover showing customer_id and bill amount
   
5. Style Requirements:
   - Match existing Plotly charts in dashboard.py (check line ~800-900)
   - Use plotly.graph_objects (not express)
   - Include detailed docstring with example
   - Type hints on all parameters

Example Usage:
```python
import plotly.graph_objects as go
from market_design.visualizations import create_bill_impact_boxplot

baseline = pd.DataFrame({
    'customer_id': [1, 2, 3, ...],
    'bill_euro': [120, 135, 98, ...]
})

tou_bills = pd.DataFrame({
    'customer_id': [1, 2, 3, ...],
    'bill_euro': [110, 125, 105, ...]  # Some save, some pay more
})

fig = create_bill_impact_boxplot(
    baseline_bills=baseline,
    scenario_bills=tou_bills,
    scenario_name="TOU 3-Period",
    title="Monthly Bill Impact - 100 Residential Customers"
)

# Display in Streamlit
st.plotly_chart(fig, use_container_width=True)
```

Reference:
- Existing visualization style: dashboard.py lines 800-900
- Plotly box plot docs: https://plotly.com/python/box-plots/
- UI mockup: roadmap.md Section 7.1.1 (Bill Impact Analysis tab)
```

---

## Tips for Effective Copilot Prompts

### 1. Always Reference Existing Code
```
Use the same structure as [existing_file.py]
Follow the pattern in technologies/photovoltaics.py for class initialization
Match the chart style in dashboard.py lines 850-920
```

### 2. Be Specific About Types
```
Parameters:
- load_profile: pd.DataFrame with columns ['timestamp', 'load_kw']
- prices: Dict[str, float] mapping period names to €/kWh values
- elasticity: float in range [-0.5, 0.0]
```

### 3. Include Example Usage
Always show how the class/function should be used in practice.

### 4. Specify Validation Requirements
```
Validation:
- Raise ValueError if price < 0
- Raise TypeError if load_profile is not a DataFrame
- Warn if time periods have gaps
```

### 5. Request Documentation Style
```
Style: Google-style docstrings with Parameters, Returns, Raises, Examples sections
Include mathematical formulas in docstring where relevant
Add inline comments for complex logic
```

---

## Iteration Prompts

After Copilot generates initial code, use these follow-up prompts:

### Add Missing Validation
```
@workspace Add input validation to the [ClassName] class:
- Check that [parameter] is within valid range
- Raise descriptive ValueError with suggested fix
- Add type checking for DataFrame columns
```

### Improve Documentation
```
@workspace Improve the docstring for [method_name]:
- Add an Examples section with realistic data
- Document the mathematical formula used
- Clarify what happens in edge cases (empty input, etc.)
```

### Add Type Hints
```
@workspace Add complete type hints to all methods in [ClassName]
Use Python 3.11+ style (e.g., list[str] instead of List[str])
Import from typing only when necessary
```

### Match Existing Style
```
@workspace Refactor [ClassName] to match the code style in [reference_file]:
- Same import organization (stdlib, third-party, local)
- Same error handling pattern
- Same naming conventions
```

---

## Common Issues & Solutions

### Issue: Generated Code Too Complex

**Solution**: Ask for simplification
```
@workspace Simplify the [method_name] implementation:
- Remove unnecessary abstractions
- Use straightforward pandas operations
- Keep cyclomatic complexity < 10
```

### Issue: Missing Edge Case Handling

**Solution**: Request specific scenarios
```
@workspace Add handling for these edge cases in [method_name]:
1. Empty DataFrame input
2. Missing required columns
3. Negative values in load data
4. Timestamps not in chronological order
```

### Issue: Inconsistent with Project Style

**Solution**: Explicit style reference
```
@workspace Reformat this code to match:
- Import style from dashboard.py lines 1-50
- Class structure from technologies/photovoltaics.py
- Docstring format from mastr_preprocessing.py
```

---

Save time by copying and adapting these templates for your specific needs!
