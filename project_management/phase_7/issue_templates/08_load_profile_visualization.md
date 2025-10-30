# [Phase 7.2.3] Build Load Profile Comparison Visualization

**Labels**: `enhancement`, `phase-7`, `visualization`, `priority-medium`, `copilot-ready`  
**Milestone**: Phase 7.2 - Real-Time Pricing & Grid Integration  
**Estimated Time**: 2 days  
**Dependencies**: Issue #7 (Pandapower integration), Issue #6 (RTPTariff)  
**Assignee**: [Your name]

---

## 📋 Description

Create interactive Plotly visualizations to compare aggregated load profiles across tariff scenarios (Baseline, TOU, RTP). Show how tariff-driven demand response shifts peak loads and reduces grid congestion.

---

## 🎯 Context

- **Part of**: Phase 7.2 - Real-Time Pricing & Grid Integration
- **Reference**: `roadmap.md` Section 7.2 Task 2.5, Section 7.1.2 (UI mockup for Load Profiles tab)
- **Integration Points**: Tariff Design Studio UI, grid simulation results, Plotly visualizations
- **Purpose**: Visualize grid-level load changes from tariff interventions

---

## 📦 Requirements

### Module: `market_design/visualizations.py` (extend existing)

Add new visualization functions to existing module created in Issue #5.

---

## 📊 Visualization 1: Aggregated Load Curve Comparison

**Function**: `create_load_curve_comparison()`

**Purpose**: Show aggregated system load over time for multiple tariff scenarios

**Signature**:
```python
def create_load_curve_comparison(
    scenarios_data: Dict[str, pd.DataFrame],
    title: str = "Aggregated Load Profile Comparison",
    show_difference: bool = True
) -> go.Figure:
```

**Parameters**:
- `scenarios_data`: Dict mapping scenario names to DataFrames
  ```python
  {
      'Baseline': DataFrame(['timestamp', 'total_load_mw']),
      'TOU 2-Period': DataFrame(['timestamp', 'total_load_mw']),
      'RTP': DataFrame(['timestamp', 'total_load_mw'])
  }
  ```
- `title`: Chart title
- `show_difference`: If True, add annotation showing peak reduction

**Chart Requirements**:
- **Type**: Line chart with multiple traces
- **X-axis**: Time (hourly)
- **Y-axis**: Total load (MW)
- **Lines**: One per scenario
  - Baseline: Dashed gray line
  - TOU: Solid blue line
  - RTP: Solid green line
- **Markers**: Highlight peak load points for each scenario
- **Shaded areas**: If show_difference=True, shade area between baseline and TOU
- **Annotations**: Show peak reduction values
  - "Peak reduction: 1.2 MW (9.6%)"
- **Legend**: Interactive (click to toggle scenarios)
- **Hover tooltip**: Show exact time, load value, scenario name

**Example Output**:
```
Aggregated Load Profile Comparison
┌─────────────────────────────────────────┐
│ 12                Peak: 11.5 MW (Baseline)
│ MW    ╱╲                                │
│ 10   ╱  ╲  ╱╲   Peak reduction:        │
│  8  ╱    ╲╱  ╲  1.2 MW (10%)           │
│  6 ╱          ╲                         │
│  4╱            ╲___                     │
│   0   6   12  18  24  Hour              │
│   ▬▬▬ Baseline  ▬▬▬ TOU  ▬▬▬ RTP       │
└─────────────────────────────────────────┘
```

---

## 📊 Visualization 2: Load Duration Curve

**Function**: `create_load_duration_curve()`

**Purpose**: Show sorted load distribution (helps assess capacity requirements)

**Signature**:
```python
def create_load_duration_curve(
    scenarios_data: Dict[str, pd.DataFrame],
    title: str = "Load Duration Curve Comparison"
) -> go.Figure:
```

**Parameters**:
- `scenarios_data`: Same as above

**Chart Requirements**:
- **Type**: Line chart
- **X-axis**: Hours (sorted by load, descending)
- **Y-axis**: Load (MW)
- **Lines**: One per scenario
- **Shaded percentile bands**: Show 10th, 50th, 90th percentiles
- **Annotations**: Mark critical percentiles
  - "95th percentile: 8.5 MW"
  - "Peak: 11.2 MW"

**Purpose**: Shows how tariffs flatten the load curve (reduce peak, fill valleys)

---

## 📊 Visualization 3: Peak Demand Reduction Metrics

**Function**: `create_peak_reduction_summary()`

**Purpose**: Summary visualization of peak reduction achievements

**Signature**:
```python
def create_peak_reduction_summary(
    baseline_peak: float,
    scenario_peaks: Dict[str, float],
    title: str = "Peak Demand Reduction Summary"
) -> go.Figure:
```

**Parameters**:
- `baseline_peak`: Baseline peak load (MW)
- `scenario_peaks`: Dict {scenario_name: peak_load_mw}

**Chart Requirements**:
- **Type**: Horizontal bar chart with annotations
- **Bars**: One per scenario
- **Colors**: Gradient based on reduction amount (green = more reduction)
- **Annotations**: Show absolute and percentage reduction
  - "TOU: -1.2 MW (-10.4%)"
  - "RTP: -1.8 MW (-15.7%)"
- **Reference line**: Baseline peak marked as vertical line

---

## 📊 Visualization 4: Hourly Load Change Heatmap

**Function**: `create_load_change_heatmap()`

**Purpose**: Show hour-by-hour load changes from baseline (useful for weekly patterns)

**Signature**:
```python
def create_load_change_heatmap(
    baseline_loads: pd.DataFrame,
    scenario_loads: pd.DataFrame,
    scenario_name: str = "TOU Tariff"
) -> go.Figure:
```

**Parameters**:
- `baseline_loads`: DataFrame ['timestamp', 'total_load_mw']
- `scenario_loads`: Same structure
- `scenario_name`: Name for title

**Chart Requirements**:
- **Type**: Heatmap
- **X-axis**: Hour of day (0-23)
- **Y-axis**: Day of week (Mon-Sun)
- **Colors**: Red (load increase), Blue (load decrease), White (no change)
- **Color scale**: Diverging (-2 MW to +2 MW)
- **Hover**: Show exact load change

**Purpose**: Identify patterns - e.g., "TOU reduces weekday evening peak by 15%"

---

## 🔄 Integration with Dashboard

### Update `tariff_design_studio()` function in `dashboard.py`

Add new tab for load profile visualizations:

```python
# In dashboard.py, tariff_design_studio() function

if 'simulation_results' in st.session_state:
    results = st.session_state['simulation_results']
    
    st.subheader("📈 Load Profile Analysis")
    
    # Tab layout
    tab1, tab2, tab3, tab4 = st.tabs([
        "Load Curves", 
        "Duration Curve", 
        "Peak Reduction",
        "Hourly Heatmap"
    ])
    
    with tab1:
        # Prepare data for comparison
        scenarios_data = {
            'Baseline': results['baseline_loads'],
            'TOU': results['tou_loads'],
            'RTP': results['rtp_loads']  # if RTP enabled
        }
        
        fig = create_load_curve_comparison(scenarios_data)
        st.plotly_chart(fig, use_container_width=True)
        
        # Summary metrics below chart
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Baseline Peak", f"{baseline_peak:.2f} MW")
        with col2:
            peak_reduction = baseline_peak - tou_peak
            st.metric("TOU Peak", f"{tou_peak:.2f} MW", 
                     delta=f"{-peak_reduction:.2f} MW")
        with col3:
            pct_reduction = (peak_reduction / baseline_peak) * 100
            st.metric("Peak Reduction", f"{pct_reduction:.1f}%")
    
    with tab2:
        fig = create_load_duration_curve(scenarios_data)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        scenario_peaks = {
            'TOU': results['tou_peak'],
            'RTP': results['rtp_peak']
        }
        fig = create_peak_reduction_summary(baseline_peak, scenario_peaks)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        fig = create_load_change_heatmap(
            results['baseline_loads'],
            results['tou_loads'],
            scenario_name="TOU 2-Period"
        )
        st.plotly_chart(fig, use_container_width=True)
```

---

## ✅ Acceptance Criteria

### Visualizations
- [ ] `create_load_curve_comparison()` renders correctly
- [ ] Multiple scenarios displayed on same chart
- [ ] Peak points are marked clearly
- [ ] `create_load_duration_curve()` sorts loads correctly
- [ ] `create_peak_reduction_summary()` shows reductions
- [ ] `create_load_change_heatmap()` uses diverging colors correctly
- [ ] All charts are interactive (zoom, pan, hover)

### Integration
- [ ] Charts appear in Tariff Design Studio page
- [ ] Tab navigation works
- [ ] Charts update when simulation is re-run
- [ ] Streamlit metrics display correct values
- [ ] No errors with different scenario combinations

### Code Quality
- [ ] Type hints on all functions
- [ ] Google-style docstrings with examples
- [ ] Follows existing visualization style
- [ ] Passes black and flake8

### UX
- [ ] Charts load in <2 seconds
- [ ] Tooltips are informative
- [ ] Color scheme is accessible (colorblind-friendly)
- [ ] Legends are clear

---

## 🧪 Testing Requirements

Create tests in `market_design/tests/test_visualizations.py` (extend existing)

### Test Cases:

```python
def test_load_curve_comparison_creates_figure():
    """Test load curve comparison returns valid Plotly figure"""
    # Create sample scenarios_data with 24-hour loads
    # Call function, verify Figure type

def test_load_curve_handles_single_scenario():
    """Test that single scenario (no comparison) works"""
    # Should still render with just baseline

def test_load_duration_curve_sorting():
    """Test that loads are sorted descending"""
    # Verify x-axis represents hours in descending load order

def test_peak_reduction_calculation():
    """Test peak reduction percentages are correct"""
    # Known baseline=10 MW, TOU=9 MW → 10% reduction

def test_heatmap_diverging_colors():
    """Test heatmap uses correct color scale"""
    # Verify negative values are blue, positive are red

def test_chart_handles_missing_data():
    """Test graceful handling of NaN values"""
    # DataFrame with gaps should interpolate or skip
```

---

## 📚 Reference Materials

- **Roadmap**: `roadmap.md` Section 7.1.2 (Load Profiles tab mockup)
- **Existing Visualizations**: `market_design/visualizations.py` (Issue #5)
- **Plotly Docs**:
  - Line charts: https://plotly.com/python/line-charts/
  - Heatmaps: https://plotly.com/python/heatmaps/
  - Multiple traces: https://plotly.com/python/multiple-axes/
- **Dashboard Integration**: `dashboard.py` existing tab patterns
- **Grid Results**: Output from `grid_integration.simulate_tariff_impact()`

---

## 🤖 GitHub Copilot Prompt Suggestion

```
@workspace Add load profile visualization functions to market_design/visualizations.py

New functions (see issue #8):

1. create_load_curve_comparison(scenarios_data, title, show_difference=True)
   - Line chart comparing aggregated load curves
   - scenarios_data = {'Baseline': df, 'TOU': df, 'RTP': df}
   - Each df has ['timestamp', 'total_load_mw']
   - Mark peak points with annotations
   - Show peak reduction if show_difference=True
   - Interactive legend (toggle scenarios)

2. create_load_duration_curve(scenarios_data, title)
   - Sort loads descending for each scenario
   - Plot load vs cumulative hours
   - Mark percentiles (95th, 50th)
   - Show capacity requirements

3. create_peak_reduction_summary(baseline_peak, scenario_peaks, title)
   - Horizontal bar chart
   - scenario_peaks = {'TOU': 9.2, 'RTP': 8.8}
   - Annotate with absolute and % reduction
   - Color gradient based on reduction

4. create_load_change_heatmap(baseline_loads, scenario_loads, scenario_name)
   - 2D heatmap: hour (x) vs day-of-week (y)
   - Color = load change (MW)
   - Diverging colorscale (blue=decrease, red=increase)

Then integrate into dashboard.py tariff_design_studio() function:
- Add "Load Profile Analysis" section
- 4 tabs for each visualization
- Add st.metric() displays for peak values

Match style from existing visualizations (Issue #5).
Use plotly.graph_objects, include comprehensive docstrings.
```

---

## 🗒️ Implementation Notes

### Data Preparation Helper

Create helper function to aggregate individual customer loads to system level:

```python
def aggregate_customer_loads(load_profiles: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate individual customer loads to system total.
    
    Parameters:
    - load_profiles: DataFrame ['customer_id', 'timestamp', 'load_kw']
    
    Returns:
    - DataFrame ['timestamp', 'total_load_mw']
    """
    aggregated = load_profiles.groupby('timestamp')['load_kw'].sum()
    aggregated = aggregated / 1000  # Convert kW to MW
    
    return pd.DataFrame({
        'timestamp': aggregated.index,
        'total_load_mw': aggregated.values
    })
```

### Color Palette

For consistency across all charts:

```python
SCENARIO_COLORS = {
    'Baseline': '#95a5a6',      # Gray
    'TOU': '#3498db',           # Blue
    'TOU 2-Period': '#3498db',  
    'TOU 3-Period': '#2980b9',  # Darker blue
    'RTP': '#27ae60',           # Green
    'CPP': '#e74c3c',           # Red (critical peak)
}

# For heatmap diverging scale
DIVERGING_COLORSCALE = 'RdBu_r'  # Red-Blue reversed (blue=decrease)
```

---

## 🔄 Related Issues

- **Depends on**: #7 (Grid integration provides load data)
- **Depends on**: #6 (RTP tariff for scenario comparison)
- **Extends**: #5 (Adds to existing visualizations.py)
- **Blocks**: Complete Phase 7.2 (last visualization task)

---

**Created**: [Date]  
**Last Updated**: [Date]  
**Status**: Open / In Progress / Complete
