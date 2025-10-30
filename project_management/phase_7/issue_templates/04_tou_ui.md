# [Phase 7.1.4] Create Basic TOU Configuration UI in dashboard.py

**Labels**: `enhancement`, `phase-7`, `ui`, `priority-high`, `copilot-ready`  
**Milestone**: Phase 7.1 - Foundation  
**Estimated Time**: 2-3 days  
**Dependencies**: Issue #2 (TOUTariff class)  
**Assignee**: [Your name]

---

## 📋 Description

Create a new Streamlit page "Tariff Design Studio" in `dashboard.py` with an interactive UI for configuring Time-of-Use tariffs, running simulations, and viewing basic results.

---

## 🎯 Context

- **Part of**: Phase 7.1 - Foundation & Basic TOU
- **Reference**: `roadmap.md` Section 7.2, Task 1.4, and Section 7.1 (UI mockups)
- **Integration Points**: `dashboard.py` (add new page function), `TOUTariff` class, Streamlit widgets
- **UI Reference**: Follow pattern from existing pages like `solar_installation_mastr()`

---

## 📦 Requirements

### New Function in `dashboard.py`

**Function name**: `tariff_design_studio()`

**Location**: Add to `dashboard.py` (follow existing page function pattern)

**Page Navigation**: Add to sidebar menu (after existing pages)

---

## 🎨 UI Layout

### Page Structure

```
⚡ Tariff Design Studio
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Introduction text explaining TOU tariffs and simulation]

┌─ Configuration ────────────────────────┐
│                                        │
│  Tariff Name: [Text Input]            │
│                                        │
│  Number of Time Periods:               │
│  ○ 2 Periods (Peak/Off-Peak)          │
│  ○ 3 Periods (Peak/Mid/Off-Peak)      │
│                                        │
│  ┌─ Peak Period ──────────────────┐   │
│  │ Start Time: [16:00] ▼          │   │
│  │ End Time:   [20:00] ▼          │   │
│  │ Price:      [0.35] €/kWh       │   │
│  └────────────────────────────────┘   │
│                                        │
│  ┌─ Off-Peak Period ──────────────┐   │
│  │ Start Time: [20:00] ▼          │   │
│  │ End Time:   [16:00] ▼          │   │
│  │ Price:      [0.15] €/kWh       │   │
│  └────────────────────────────────┘   │
│                                        │
│  [+ Add Period] (if 3-period selected)│
│                                        │
│  Demand Response:                      │
│  □ Enable demand response simulation   │
│  Behavior Type: [Active] ▼             │
│  Elasticity: [-0.15] (slider)          │
│                                        │
└────────────────────────────────────────┘

┌─ Simulation Settings ──────────────────┐
│ Number of Customers: [100] (slider)    │
│ Simulation Period: [30 days]           │
│ Customer Mix:                          │
│   - Residential: [80%]                 │
│   - Commercial: [20%]                  │
└────────────────────────────────────────┘

              [Run Simulation]

┌─ Results Preview ──────────────────────┐
│ (Placeholder for Task 1.5 - Bill viz)  │
└────────────────────────────────────────┘
```

---

## 🔧 Widget Requirements

### Configuration Widgets

1. **Tariff Name** (st.text_input)
   - Default: "Custom TOU Tariff"
   - Validation: Non-empty string

2. **Number of Periods** (st.radio)
   - Options: "2 Periods", "3 Periods"
   - Default: "2 Periods"
   - Dynamically show/hide period 3 configuration

3. **Time Period Configuration** (for each period):
   - **Start Time** (st.time_input or st.selectbox with hourly slots)
     - Format: HH:00 (hourly granularity)
     - Range: 00:00 to 23:00
   - **End Time** (same as start time)
   - **Price** (st.number_input)
     - Min: 0.01, Max: 1.0, Step: 0.01
     - Unit: €/kWh
     - Validation: Must be > 0

4. **Demand Response** (st.checkbox + conditional widgets)
   - Checkbox: "Enable demand response simulation"
   - If enabled:
     - **Behavior Type** (st.selectbox): ["Passive", "Active", "Automated"]
     - **Elasticity** (st.slider): Range -0.5 to 0.0, Default -0.15, Step 0.01

### Simulation Settings

5. **Number of Customers** (st.slider)
   - Min: 10, Max: 1000, Default: 100, Step: 10

6. **Simulation Period** (st.selectbox)
   - Options: ["1 day", "7 days", "30 days"]
   - Default: "30 days"

7. **Customer Mix** (st.slider for each segment)
   - Residential %: 0-100%, Default 80%
   - Commercial %: Auto-calculated as (100% - Residential%)

---

## 🔄 Functionality Requirements

### Input Validation

Implement validation before running simulation:

```python
def validate_tou_config():
    """Validate TOU configuration inputs"""
    errors = []
    
    # Check all prices > 0
    if any(price <= 0 for price in prices.values()):
        errors.append("All prices must be greater than 0")
    
    # Check time periods cover 24 hours
    # (Use TOUTariff.validate_periods() method)
    
    # Check no overlapping periods
    
    # Check customer mix sums to 100%
    
    if errors:
        st.error("Configuration errors:\n" + "\n".join(errors))
        return False
    return True
```

Display errors using `st.error()` with specific messages.

### Run Simulation Button

When clicked:
1. Validate configuration (see above)
2. Show `st.spinner("Running simulation...")`
3. Create `TOUTariff` object from widget values
4. Generate synthetic load profiles (use existing MaStR data or simple synthetic)
5. If demand response enabled: Create `DemandResponseModel` and apply
6. Calculate bills for all customers
7. Store results in `st.session_state` for visualization
8. Show success message: `st.success(f"Simulation complete for {n} customers")`

### Error Handling

Wrap simulation in try/except:
```python
try:
    # Run simulation
    results = run_tou_simulation(config)
    st.session_state['tou_results'] = results
except ValueError as e:
    st.error(f"Configuration error: {str(e)}")
except Exception as e:
    st.error(f"Simulation failed: {str(e)}")
    st.write("Please check your configuration and try again.")
```

---

## ✅ Acceptance Criteria

### UI
- [ ] New page appears in sidebar navigation
- [ ] Page has title with ⚡ emoji
- [ ] Introduction text explains TOU tariffs
- [ ] All configuration widgets render correctly
- [ ] 3-period widgets show/hide based on radio selection
- [ ] Demand response widgets show/hide based on checkbox

### Functionality
- [ ] Can configure 2-period TOU tariff
- [ ] Can configure 3-period TOU tariff
- [ ] Validation catches invalid inputs (negative prices, gaps, etc.)
- [ ] "Run Simulation" button triggers simulation
- [ ] Simulation creates TOUTariff object correctly
- [ ] Results stored in session state
- [ ] Error messages display for invalid configs

### Code Quality
- [ ] Follows existing dashboard.py code style
- [ ] Uses st.session_state for state management
- [ ] Properly integrated with sidebar navigation
- [ ] No hardcoded values (use constants)
- [ ] Passes flake8 linting

---

## 🧪 Testing Instructions

### Manual Testing Checklist

After implementation, test these scenarios:

1. **2-Period Configuration**:
   - Configure Peak: 16:00-20:00, €0.35/kWh
   - Configure Off-Peak: 20:00-16:00, €0.15/kWh
   - Run simulation with 100 customers
   - Verify no errors

2. **3-Period Configuration**:
   - Configure Peak, Mid-Peak, Off-Peak
   - Run simulation
   - Verify correct period assignment

3. **Validation**:
   - Try negative price → Should show error
   - Try time period gap → Should show error
   - Try overlapping periods → Should show error

4. **Demand Response**:
   - Enable demand response
   - Select "Active" behavior
   - Run simulation
   - Verify results differ from baseline

5. **Performance**:
   - Run with 1000 customers
   - Verify completes in <30 seconds

---

## 📚 Reference Materials

- **Roadmap**: `roadmap.md` Section 7.1 (UI mockups) and 7.2 Task 1.4
- **Existing Page Pattern**: See `solar_installation_mastr()` in `dashboard.py` (line ~950)
- **Streamlit Docs**: https://docs.streamlit.io/
- **Session State**: https://docs.streamlit.io/library/api-reference/session-state
- **TOUTariff Class**: `market_design/tariff_models.py`

---

## 🤖 GitHub Copilot Prompt Suggestion

```
@workspace Create a new Streamlit page function tariff_design_studio() in dashboard.py

Requirements (see issue #4):
1. Add page to sidebar navigation (after existing pages)
2. Title: "⚡ Tariff Design Studio"
3. Configuration UI:
   - Radio button: 2 or 3 time periods
   - For each period: start time, end time, price (€/kWh)
   - Checkbox: Enable demand response
   - Slider: Number of customers (10-1000)
4. Validation:
   - Prices > 0
   - Time periods cover 24 hours (use TOUTariff.validate_periods())
   - Display errors with st.error()
5. Run Simulation button:
   - Create TOUTariff object from inputs
   - Generate synthetic load profiles
   - Calculate bills
   - Store in st.session_state['tou_results']
   - Show success message

Follow the pattern from solar_installation_mastr() function (line ~950).
Use st.session_state for state management.
Include proper error handling with try/except.
```

---

## 🗒️ Implementation Notes

### Synthetic Load Profile Generation

For initial version (before integration with MaStR data):

```python
def generate_synthetic_load_profiles(n_customers, days=30):
    """Generate simple synthetic load profiles for testing"""
    timestamps = pd.date_range('2025-01-01', periods=24*days, freq='H')
    
    profiles = []
    for i in range(n_customers):
        # Simple pattern: higher during day, lower at night
        base_load = np.random.uniform(1.5, 3.0)
        hourly_pattern = [
            base_load * 0.5,  # 00:00-08:00 (night)
            base_load * 1.0,  # 08:00-16:00 (day)
            base_load * 1.3,  # 16:00-20:00 (peak)
            base_load * 0.7,  # 20:00-24:00 (evening)
        ]
        # Repeat pattern for all days
        loads = np.tile(hourly_pattern, days)[:len(timestamps)]
        
        profiles.append(pd.DataFrame({
            'customer_id': i,
            'timestamp': timestamps,
            'load_kw': loads
        }))
    
    return pd.concat(profiles, ignore_index=True)
```

### Session State Structure

```python
st.session_state['tou_results'] = {
    'tariff': tou_tariff_object,
    'load_profiles': DataFrame,  # original
    'modified_profiles': DataFrame,  # after demand response
    'bills_baseline': DataFrame,  # flat rate bills
    'bills_tou': DataFrame,  # TOU bills
    'config': {
        'n_customers': 100,
        'periods': 2,
        'demand_response_enabled': True,
        ...
    }
}
```

---

## 🔄 Related Issues

- **Depends on**: #2 (Needs TOUTariff class)
- **Integrates with**: #3 (Uses DemandResponseModel if enabled)
- **Blocks**: #5 (Visualization will display these results)

---

**Created**: [Date]  
**Last Updated**: [Date]  
**Status**: Open / In Progress / Complete
