# [Phase 7.3.7] Create PDF Export Functionality

**Labels**: `enhancement`, `phase-7`, `priority-low`, `copilot-ready`, `reporting`  
**Milestone**: Phase 7.3 - Advanced Features & Export  
**Estimated Time**: 2-3 days  
**Dependencies**: All visualization functions (Issues #5, #8), tariff models, grid integration  
**Assignee**: [Your name]

---

## 📋 Description

Implement PDF export functionality to generate professional tariff design reports. These reports include scenario comparisons, visualizations, bill calculations, and grid impact analysis - suitable for presentations to stakeholders and regulators.

---

## 🎯 Context

- **Part of**: Phase 7.3 - Advanced Features & Export
- **Reference**: `roadmap.md` Section 7.3, Task 3.7
- **Use Cases**: 
  - Present tariff proposals to DSO management
  - Share analysis with regulatory authorities
  - Document tariff design decisions
  - Customer communication materials
- **Integration Points**: All visualization functions, simulation results, tariff configurations

---

## 📦 Requirements

### Module: `market_design/export_utils.py`

Create export module with PDF generation capabilities.

---

## 📄 Function 1: `generate_tariff_report()`

**Purpose**: Main function to create comprehensive tariff design PDF report

**Signature**:
```python
def generate_tariff_report(
    simulation_results: Dict,
    output_path: str = "tariff_report.pdf",
    include_sections: List[str] = None,
    branding: Dict = None
) -> str:
```

**Parameters**:
- `simulation_results`: Dict containing all simulation data
  ```python
  {
      'metadata': {
          'report_title': str,
          'created_date': datetime,
          'author': str,
          'dso_name': str
      },
      'scenarios': {
          'Baseline': {...},
          'TOU': {...},
          'RTP': {...}
      },
      'tariff_configs': {
          'TOU': TOUTariff object,
          'RTP': RTPTariff object
      },
      'load_data': DataFrame,
      'grid_results': DataFrame,
      'bill_impacts': DataFrame,
      'visualizations': {
          'bill_comparison': Figure,
          'load_curves': Figure,
          'grid_impact': Figure
      }
  }
  ```
- `output_path`: File path for generated PDF
- `include_sections`: List of sections to include (default: all)
  - Options: ['executive_summary', 'tariff_config', 'bill_impact', 'load_analysis', 'grid_impact', 'recommendations']
- `branding`: Optional branding customization
  ```python
  {
      'logo_path': str,  # Path to logo image
      'primary_color': str,  # Hex color (e.g., '#1f77b4')
      'company_name': str,
      'footer_text': str
  }
  ```

**Returns**:
- Path to generated PDF file

**Process**:
1. Initialize PDF document (ReportLab or matplotlib PDF backend)
2. Add title page with branding
3. Generate table of contents
4. Add each requested section
5. Include visualizations as embedded images
6. Add summary tables
7. Add appendix with technical details
8. Save and return file path

---

## 📄 Report Structure

### Title Page
- Report title
- DSO name/logo
- Date generated
- Author
- Version number

### Executive Summary (1 page)
- Key findings (bullet points)
- Recommended tariff design
- Expected impact metrics:
  - Peak demand reduction: X MW (Y%)
  - Customer bill impact: +/- €Z average
  - Grid congestion reduction: A%
  - Revenue adequacy: B%

### Section 1: Tariff Configuration Details
**For each tariff scenario**:
- Tariff name and type
- Configuration parameters
  - Time periods (TOU)
  - Price levels
  - Grid fee structure
- Rationale for design choices

**Example Table**:
```
TOU Tariff Configuration
├─ Peak Period: 16:00-20:00 (weekdays)
│  └─ Price: €0.35/kWh
├─ Mid-Peak: 09:00-16:00, 20:00-22:00
│  └─ Price: €0.20/kWh
└─ Off-Peak: 22:00-09:00, weekends
   └─ Price: €0.12/kWh

Grid Fee: €0.05/kWh + €50/kW/year capacity charge
```

### Section 2: Bill Impact Analysis
- Distribution of bill changes (box plot from Issue #5)
- Segment-wise comparison (visualization from Issue #5)
- Customer impact tables:
  ```
  | Customer Segment | Avg. Bill Change | Min | Max | % Customers Better Off |
  |------------------|------------------|-----|-----|------------------------|
  | Residential      | -€5.20/month    | -€25| +€8 | 78%                    |
  | Small Business   | -€12.40/month   | -€45| +€15| 65%                    |
  | Industrial       | -€230/month     | -€890| +€120| 82%                 |
  ```

### Section 3: Load Profile Analysis
- Aggregated load curves (from Issue #8)
- Load duration curves
- Peak demand reduction metrics
- Time-series heatmaps showing load shifts

### Section 4: Grid Impact Analysis
- Line loading comparison (baseline vs scenarios)
- Congestion hotspot identification
- Voltage profile improvements
- Transformer loading changes
- Cost-benefit of grid reinforcement deferral

### Section 5: Recommendations
- Recommended tariff design
- Implementation timeline
- Customer communication strategy
- Monitoring metrics
- Potential risks and mitigation

### Appendix
- Technical parameters
- Data sources
- Calculation methodology
- Assumptions and limitations

---

## 🔧 Technical Requirements

### PDF Generation Library

**Recommended**: Use `matplotlib` with PDF backend (simplest for Plotly integration)

**Alternative**: `ReportLab` (more control over layout)

**Installation**:
```python
# requirements.txt additions
matplotlib>=3.7.0
reportlab>=4.0.0
Pillow>=10.0.0  # For image handling
kaleido>=0.2.1  # For Plotly to static image conversion
```

### Implementation Approach

```python
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import plotly.io as pio
from datetime import datetime

def generate_tariff_report(simulation_results, output_path="tariff_report.pdf", 
                          include_sections=None, branding=None):
    """
    Generate comprehensive PDF report.
    """
    if include_sections is None:
        include_sections = [
            'executive_summary', 'tariff_config', 'bill_impact',
            'load_analysis', 'grid_impact', 'recommendations'
        ]
    
    with PdfPages(output_path) as pdf:
        # Title page
        _add_title_page(pdf, simulation_results['metadata'], branding)
        
        # Each section
        if 'executive_summary' in include_sections:
            _add_executive_summary(pdf, simulation_results)
        
        if 'tariff_config' in include_sections:
            _add_tariff_configuration(pdf, simulation_results['tariff_configs'])
        
        if 'bill_impact' in include_sections:
            _add_bill_impact_section(pdf, simulation_results)
        
        if 'load_analysis' in include_sections:
            _add_load_analysis_section(pdf, simulation_results)
        
        if 'grid_impact' in include_sections:
            _add_grid_impact_section(pdf, simulation_results)
        
        if 'recommendations' in include_sections:
            _add_recommendations_section(pdf, simulation_results)
        
        # Metadata
        d = pdf.infodict()
        d['Title'] = simulation_results['metadata']['report_title']
        d['Author'] = simulation_results['metadata'].get('author', 'VISE-D')
        d['Subject'] = 'Tariff Design Analysis Report'
        d['Keywords'] = 'Tariff, TOU, RTP, Grid Fees, Demand Response'
        d['CreationDate'] = datetime.now()
    
    return output_path
```

### Helper Functions

```python
def _add_title_page(pdf, metadata, branding):
    """Create title page"""
    fig, ax = plt.subplots(figsize=(8.5, 11))
    ax.axis('off')
    
    # Title
    ax.text(0.5, 0.7, metadata['report_title'], 
            ha='center', va='center', fontsize=24, fontweight='bold')
    
    # DSO name
    ax.text(0.5, 0.6, metadata.get('dso_name', ''), 
            ha='center', va='center', fontsize=18)
    
    # Date
    ax.text(0.5, 0.5, f"Generated: {metadata['created_date'].strftime('%Y-%m-%d')}", 
            ha='center', va='center', fontsize=12)
    
    # Logo (if provided)
    if branding and 'logo_path' in branding:
        from PIL import Image
        logo = Image.open(branding['logo_path'])
        # Add logo to figure
    
    pdf.savefig(fig, bbox_inches='tight')
    plt.close()

def _add_plotly_figure_to_pdf(pdf, plotly_fig, title=None):
    """Convert Plotly figure to PDF page"""
    # Convert Plotly to static image
    img_bytes = pio.to_image(plotly_fig, format='png', width=1200, height=800)
    
    # Create matplotlib figure with image
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.axis('off')
    
    if title:
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    
    from PIL import Image
    import io
    img = Image.open(io.BytesIO(img_bytes))
    ax.imshow(img)
    
    pdf.savefig(fig, bbox_inches='tight')
    plt.close()

def _add_summary_table(pdf, data, title, column_widths=None):
    """Add a data table to PDF"""
    fig, ax = plt.subplots(figsize=(8.5, 11))
    ax.axis('off')
    
    ax.text(0.5, 0.95, title, ha='center', va='top', 
            fontsize=14, fontweight='bold', transform=ax.transAxes)
    
    # Create table
    table = ax.table(
        cellText=data.values,
        colLabels=data.columns,
        cellLoc='left',
        loc='center',
        bbox=[0.1, 0.1, 0.8, 0.8]
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.5)
    
    # Style header
    for i in range(len(data.columns)):
        table[(0, i)].set_facecolor('#4472C4')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    pdf.savefig(fig, bbox_inches='tight')
    plt.close()
```

---

## ✅ Acceptance Criteria

### Functionality
- [ ] PDF is generated without errors
- [ ] All requested sections are included
- [ ] Visualizations are embedded correctly
- [ ] Tables are formatted properly
- [ ] Multi-page reports work
- [ ] File size is reasonable (<10 MB for typical report)

### Content Quality
- [ ] Executive summary is concise and actionable
- [ ] All metrics are accurate
- [ ] Visualizations are clear and labeled
- [ ] Tables have proper headers
- [ ] Recommendations are specific

### Code Quality
- [ ] Python 3.11+ type hints
- [ ] Google-style docstrings
- [ ] Passes black and flake8
- [ ] Error handling for missing data
- [ ] Progress indication for long reports

### UX
- [ ] PDF generation completes in <30 seconds
- [ ] Progress bar/spinner in Streamlit UI
- [ ] Download link provided after generation
- [ ] PDF opens correctly in standard viewers (Adobe, Chrome, etc.)

---

## 🧪 Testing Requirements

Create tests in `market_design/tests/test_export_utils.py`

### Test Cases:

```python
def test_generate_basic_report():
    """Test basic report generation with minimal data"""
    # Create minimal simulation_results dict
    # Generate PDF
    # Verify file exists and size > 0

def test_generate_full_report():
    """Test comprehensive report with all sections"""
    # Create complete simulation_results
    # Include all visualizations
    # Verify all sections present (check PDF metadata or page count)

def test_selective_sections():
    """Test generating report with subset of sections"""
    # Generate with only ['executive_summary', 'bill_impact']
    # Verify other sections not included

def test_branding_customization():
    """Test custom branding is applied"""
    # Provide branding dict with logo, colors
    # Verify PDF contains branding elements

def test_missing_visualization_handling():
    """Test graceful handling when visualization missing"""
    # simulation_results with some visualizations = None
    # Should skip those sections or show placeholder

def test_large_dataset_performance():
    """Test performance with large datasets"""
    # 1000+ customers, 8760 hours
    # Should complete in <60 seconds
    
def test_pdf_file_validity():
    """Test generated PDF is valid"""
    # Use PyPDF2 to open and verify structure
    import PyPDF2
    # Verify can extract text, count pages
```

---

## 📚 Reference Materials

- **Roadmap**: `roadmap.md` Section 7.3, Task 3.7
- **Matplotlib PDF Backend**: https://matplotlib.org/stable/api/backend_pdf_api.html
- **ReportLab Docs**: https://www.reportlab.com/docs/reportlab-userguide.pdf
- **Plotly to Image**: https://plotly.com/python/static-image-export/
- **Visualization Functions**: Issues #5, #8 for source figures

---

## 🤖 GitHub Copilot Prompt Suggestion

```
@workspace Create export_utils.py in market_design/ for PDF report generation

Main function: generate_tariff_report(simulation_results, output_path, include_sections, branding)

Report structure (see issue #10):
1. Title page (with optional logo/branding)
2. Executive summary (key metrics, recommendations)
3. Tariff configuration details (tables)
4. Bill impact analysis (tables + visualizations from Issue #5)
5. Load profile analysis (visualizations from Issue #8)
6. Grid impact analysis (grid simulation results)
7. Recommendations section
8. Technical appendix

Use matplotlib PDF backend:
```python
from matplotlib.backends.backend_pdf import PdfPages

with PdfPages(output_path) as pdf:
    # Add title page
    _add_title_page(pdf, metadata, branding)
    
    # Add sections
    for section in include_sections:
        # Generate page(s) for each section
    
    # Set PDF metadata
    d = pdf.infodict()
    d['Title'] = '...'
```

Helper functions needed:
- _add_title_page(pdf, metadata, branding)
- _add_executive_summary(pdf, results)
- _add_plotly_figure_to_pdf(pdf, plotly_fig, title)
- _add_summary_table(pdf, dataframe, title)
- _add_text_section(pdf, title, paragraphs)

For Plotly figures → static images:
```python
import plotly.io as pio
img_bytes = pio.to_image(fig, format='png', width=1200, height=800)
# Embed in matplotlib figure
```

Tables: Use ax.table() in matplotlib for data tables

Include error handling:
- Missing visualizations → placeholder or skip
- Empty data → informative message
- Large files → compression/optimization

Integration point: Add "Export PDF" button to Streamlit dashboard that calls this function.

Use Python 3.11+ type hints, comprehensive docstrings.
```

---

## 🗒️ Implementation Notes

### Streamlit Integration

Add export button to `tariff_design_studio()` in `dashboard.py`:

```python
# In tariff_design_studio() function

if 'simulation_results' in st.session_state:
    st.divider()
    st.subheader("📄 Export Report")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        report_title = st.text_input(
            "Report Title",
            value="Tariff Design Analysis Report"
        )
    
    with col2:
        sections = st.multiselect(
            "Include Sections",
            ['executive_summary', 'tariff_config', 'bill_impact',
             'load_analysis', 'grid_impact', 'recommendations'],
            default=['executive_summary', 'bill_impact', 'load_analysis']
        )
    
    with col3:
        if st.button("📥 Generate PDF", type="primary"):
            with st.spinner("Generating PDF report..."):
                # Prepare simulation_results dict
                sim_results = {
                    'metadata': {
                        'report_title': report_title,
                        'created_date': datetime.now(),
                        'author': st.session_state.get('user_name', 'User'),
                        'dso_name': 'Distribution System Operator'
                    },
                    'scenarios': st.session_state['simulation_results'],
                    'tariff_configs': {...},
                    'visualizations': {...}
                }
                
                # Generate PDF
                from market_design.export_utils import generate_tariff_report
                pdf_path = generate_tariff_report(
                    sim_results,
                    output_path="reports/tariff_report.pdf",
                    include_sections=sections
                )
                
                # Provide download
                with open(pdf_path, 'rb') as f:
                    st.download_button(
                        label="⬇️ Download Report",
                        data=f,
                        file_name=f"tariff_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf"
                    )
                
                st.success("✅ Report generated successfully!")
```

### Performance Optimization

For large reports:

```python
# Use lower resolution for embedded images
img_bytes = pio.to_image(fig, format='png', width=800, height=600)

# Compress images
from PIL import Image
img = img.convert('RGB')
img.save(buffer, format='JPEG', quality=85, optimize=True)

# Show progress
for i, section in enumerate(include_sections):
    progress = (i + 1) / len(include_sections)
    # Update progress bar
```

### Example Report Output

**File**: `reports/example_tariff_report.pdf`
- Pages: 12-15
- Size: 3-5 MB
- Contains: 5-7 visualizations, 3-4 data tables
- Format: Letter (8.5" × 11")

---

## 🔄 Related Issues

- **Depends on**: #5 (Bill visualization functions), #8 (Load profile visualizations)
- **Uses**: All tariff classes (#2, #6, #9), grid integration (#7)
- **Final deliverable**: Completes Phase 7.3 export functionality
- **Stakeholder value**: Enables external communication of tariff designs

---

**Created**: [Date]  
**Last Updated**: [Date]  
**Status**: Open / In Progress / Complete
