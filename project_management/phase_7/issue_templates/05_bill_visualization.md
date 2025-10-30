# [Phase 7.1.5] Implement Bill Impact Visualization Component

**Labels**: `enhancement`, `phase-7`, `visualization`, `priority-high`, `copilot-ready`  
**Milestone**: Phase 7.1 - Foundation  
**Estimated Time**: 2-3 days  
**Dependencies**: Issue #2 (TOUTariff), Issue #4 (UI with results)  
**Assignee**: [Your name]

---

## 📋 Description

Create interactive Plotly visualizations in `market_design/visualizations.py` to display bill impact analysis from TOU tariff simulations. Integrate these into the Tariff Design Studio page.

---

## 🎯 Context

- **Part of**: Phase 7.1 - Foundation & Basic TOU
- **Reference**: `roadmap.md` Section 7.2 Task 1.5, Section 7.1.1 (UI mockup for Bill Impact tab)
- **Integration Points**: `dashboard.py` (Tariff Design Studio page), simulation results in `st.session_state`
- **Style Reference**: Existing Plotly charts in `dashboard.py` (lines ~800-900)

---

## 📦 Requirements

### Module: `market_design/visualizations.py`

Create visualization functions using Plotly for interactive charts.

---

## 📊 Visualization 1: Bill Impact Box Plot

**Function**: `create_bill_impact_boxplot()`

**Purpose**: Compare customer bill distributions between baseline (flat rate) and TOU scenarios

**Signature**:
```python
def create_bill_impact_boxplot(
    baseline_bills: pd.DataFrame,
    scenario_bills: pd.DataFrame,
    scenario_name: str = "TOU Tariff",
    title: str = "Bill Impact Comparison"
) -> go.Figure:
```

**Parameters**:
- `baseline_bills`: DataFrame with columns ['customer_id', 'bill_euro']
- `scenario_bills`: Same structure as baseline
- `scenario_name`: Label for the scenario (e.g., "TOU 3-Period")
- `title`: Chart title

**Chart Requirements**:
- **Type**: Side-by-side box plots
- **X-axis**: Two categories: "Baseline (Flat Rate)" and scenario_name
- **Y-axis**: Bill amount in euros
- **Elements**:
  - Box plots showing median, Q1, Q3, whiskers
  - Outliers as individual points
  - Mean markers (diamonds or stars)
- **Annotations**: Add text box with summary statistics:
  - Median savings: `€X.XX (Y%)`
  - Mean savings: `€X.XX (Y%)`
  - Customers saving: `N (Z%)`
  - Customers paying more: `M (W%)`
- **Colors**:
  - Baseline: Gray (#7f8c8d)
  - TOU Scenario: Blue (#3498db)
- **Interactivity**:
  - Hover tooltip showing customer_id and exact bill amount
  - Click to highlight outliers

**Example Output**:
```
Bill Impact Comparison
┌─────────────────────────────────────────┐
│  ┌─┬─┐    ┌─┬─┐                        │
│  │ │ │    │ │ │    Summary:            │
│  │ │ │    │ │ │    Median: -€15 (-12%)│
│ ─┼─┼─┼─  ─┼─┼─┼─   Saving: 75 (75%)   │
│  │ │ │    │ │ │    Paying more: 25     │
│  └─┴─┘    └─┴─┘                        │
│ Baseline   TOU                          │
└─────────────────────────────────────────┘
```

---

## 📊 Visualization 2: Customer Segment Breakdown

**Function**: `create_segment_breakdown_chart()`

**Purpose**: Show bill impact by customer segment (residential vs. commercial)

**Signature**:
```python
def create_segment_breakdown_chart(
    bills_df: pd.DataFrame,
    segment_column: str = 'segment',
    title: str = "Bill Impact by Customer Segment"
) -> go.Figure:
```

**Parameters**:
- `bills_df`: DataFrame with columns ['customer_id', 'segment', 'bill_baseline', 'bill_tou', 'savings']
- `segment_column`: Column name for customer segments
- `title`: Chart title

**Chart Requirements**:
- **Type**: Grouped bar chart
- **X-axis**: Customer segments (Residential, Commercial)
- **Y-axis**: Average bill amount (€)
- **Bars**: Two bars per segment (Baseline, TOU)
- **Annotations**: Show percentage savings above each segment
- **Colors**: Consistent with box plot (gray/blue)

---

## 📊 Visualization 3: Savings Distribution Histogram

**Function**: `create_savings_distribution()`

**Purpose**: Show distribution of customer savings (histogram)

**Signature**:
```python
def create_savings_distribution(
    savings_df: pd.DataFrame,
    title: str = "Distribution of Customer Savings"
) -> go.Figure:
```

**Parameters**:
- `savings_df`: DataFrame with column ['savings_euro']
  - Negative values = savings
  - Positive values = paying more

**Chart Requirements**:
- **Type**: Histogram
- **X-axis**: Savings in euros (bins of €5)
- **Y-axis**: Number of customers
- **Colors**:
  - Negative bins (savings): Green (#27ae60)
  - Positive bins (paying more): Red (#e74c3c)
  - Zero bin (neutral): Gray
- **Vertical line**: Mark zero point
- **Annotations**: Show percentage in each category

---

## 📊 Visualization 4: Bill Component Stacked Bar (Optional Enhancement)

**Function**: `create_bill_components_chart()`

**Purpose**: Break down TOU bill into components (peak, off-peak, mid-peak charges)

**Signature**:
```python
def create_bill_components_chart(
    bills_by_period: pd.DataFrame,
    title: str = "Bill Breakdown by Time Period"
) -> go.Figure:
```

**Chart Requirements**:
- **Type**: Stacked bar chart
- **X-axis**: Customers (or customer segments)
- **Y-axis**: Bill amount (€)
- **Stack segments**: Peak charge, Mid-peak charge, Off-peak charge
- **Colors**: Red (peak), Orange (mid), Green (off-peak)

---

## 🔄 Integration with Dashboard

### Update `tariff_design_studio()` function

After simulation results are calculated, display visualizations:

```python
# In dashboard.py, tariff_design_studio() function

if 'tou_results' in st.session_state:
    results = st.session_state['tou_results']
    
    st.subheader("📊 Bill Impact Analysis")
    
    # Tab layout for different views
    tab1, tab2, tab3 = st.tabs(["Overview", "By Segment", "Distribution"])
    
    with tab1:
        fig = create_bill_impact_boxplot(
            baseline_bills=results['bills_baseline'],
            scenario_bills=results['bills_tou'],
            scenario_name="TOU Tariff"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        fig = create_segment_breakdown_chart(
            bills_df=results['bills_combined']
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        fig = create_savings_distribution(
            savings_df=results['savings']
        )
        st.plotly_chart(fig, use_container_width=True)
```

---

## ✅ Acceptance Criteria

### Visualizations
- [ ] `create_bill_impact_boxplot()` renders correctly
- [ ] Box plots show median, quartiles, outliers
- [ ] Summary statistics annotation is accurate
- [ ] `create_segment_breakdown_chart()` shows segments correctly
- [ ] `create_savings_distribution()` histogram has correct bins
- [ ] All charts use consistent color scheme
- [ ] Interactive hover tooltips work

### Integration
- [ ] Visualizations appear in Tariff Design Studio page
- [ ] Tab navigation works correctly
- [ ] Charts update when simulation is re-run
- [ ] Charts are responsive (use_container_width=True)
- [ ] No errors when displaying with different data sizes

### Code Quality
- [ ] All functions have type hints
- [ ] Google-style docstrings with examples
- [ ] Follows existing Plotly chart style from dashboard.py
- [ ] Passes black and flake8

---

## 🧪 Testing Requirements

Create tests in `market_design/tests/test_visualizations.py`

### Test Cases:

```python
def test_bill_impact_boxplot_creates_figure():
    """Test that boxplot function returns valid Plotly figure"""
    # Create sample data, call function, verify Figure type

def test_boxplot_handles_empty_data():
    """Test graceful handling of empty DataFrames"""
    # Pass empty DataFrames, should raise ValueError or return empty fig

def test_savings_calculation_accuracy():
    """Test that summary statistics are calculated correctly"""
    # Known data: 100 customers, 75 save €10, 25 pay €5 more
    # Verify annotation shows correct percentages

def test_segment_breakdown_all_segments():
    """Test that all segments appear in chart"""
    # Data with 3 segments, verify all appear

def test_chart_responsiveness():
    """Test charts work with various data sizes"""
    # Test with 10, 100, 1000 customers
```

---

## 📚 Reference Materials

- **Roadmap**: `roadmap.md` Section 7.1.1 (Bill Impact Analysis UI mockup)
- **Existing Charts**: `dashboard.py` lines ~800-900 for Plotly style reference
- **Plotly Docs**:
  - Box plots: https://plotly.com/python/box-plots/
  - Bar charts: https://plotly.com/python/bar-charts/
  - Histograms: https://plotly.com/python/histograms/
- **Color Scheme**: Use existing dashboard colors for consistency

---

## 🤖 GitHub Copilot Prompt Suggestion

```
@workspace Create visualization functions in market_design/visualizations.py

Functions needed (see issue #5):

1. create_bill_impact_boxplot(baseline_bills, scenario_bills, scenario_name, title)
   - Side-by-side box plots comparing bills
   - Show median, quartiles, outliers, mean markers
   - Add summary annotation: median savings, % customers saving
   - Colors: baseline=gray, scenario=blue
   - Interactive hover with customer_id and bill amount

2. create_segment_breakdown_chart(bills_df, segment_column, title)
   - Grouped bar chart by customer segment
   - Two bars per segment: baseline vs TOU
   - Show percentage savings above bars

3. create_savings_distribution(savings_df, title)
   - Histogram of savings (€5 bins)
   - Green bars for savings, red for paying more
   - Vertical line at zero

Use plotly.graph_objects (not express).
Match style from existing charts in dashboard.py lines 800-900.
Include comprehensive docstrings with example usage.
Add type hints for all parameters.

Then integrate into dashboard.py tariff_design_studio() function using st.tabs().
```

---

## 🗒️ Implementation Notes

### Summary Statistics Calculation

```python
def calculate_bill_summary(baseline, scenario):
    """Calculate summary statistics for annotation"""
    savings = baseline - scenario
    
    return {
        'median_savings_euro': savings.median(),
        'median_savings_pct': (savings.median() / baseline.median()) * 100,
        'mean_savings_euro': savings.mean(),
        'n_saving': (savings > 0).sum(),
        'pct_saving': ((savings > 0).sum() / len(savings)) * 100,
        'n_paying_more': (savings < 0).sum(),
        'pct_paying_more': ((savings < 0).sum() / len(savings)) * 100,
    }
```

### Plotly Layout Template

For consistency across all charts:

```python
layout_template = {
    'font': {'family': 'Arial, sans-serif', 'size': 12},
    'plot_bgcolor': '#f8f9fa',
    'paper_bgcolor': 'white',
    'title': {'font': {'size': 18, 'color': '#2c3e50'}},
    'xaxis': {'gridcolor': '#ecf0f1'},
    'yaxis': {'gridcolor': '#ecf0f1'},
}
```

---

## 🔄 Related Issues

- **Depends on**: #2 (Needs bill calculation results)
- **Depends on**: #4 (Integrates into Tariff Studio UI)
- **Enhances**: Phase 7.1 completion (final deliverable of foundation phase)

---

**Created**: [Date]  
**Last Updated**: [Date]  
**Status**: Open / In Progress / Complete
