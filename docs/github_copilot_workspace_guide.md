# GitHub Copilot Workspace Setup Guide for VISE-D Phase 7

**Created**: October 29, 2025  
**Purpose**: Step-by-step guide for using GitHub Copilot Workspace to implement the Tariff Design Studio (Phase 7)  
**Reference**: See `roadmap.md` Section 7 for technical requirements and implementation phases

---

## Overview: What GitHub Copilot Workspace Can Do For You

### ✅ Best Suited Tasks
- Scaffolding the `market_design/` module structure
- Implementing data models and classes (TOUTariff, RTPTariff, etc.)
- Creating unit tests for tariff calculations
- Building Streamlit UI components with your specifications
- Writing documentation and docstrings
- Refactoring existing code for integration

### ⚠️ Less Suited Tasks (keep human oversight)
- Complex algorithm design (demand response optimization)
- Pandapower integration logic (requires domain expertise)
- Strategic architecture decisions
- Validation against real-world data

---

## Step 1: Enable GitHub Copilot Workspace

### If You Don't Have It Yet
1. Go to https://github.com/features/copilot
2. Ensure you have GitHub Copilot subscription (Individual or Business)
3. Enable "Copilot Workspace" in your GitHub settings (beta feature as of Oct 2025)

### In VS Code
1. Install/update **GitHub Copilot** extension
2. Install **GitHub Copilot Chat** extension
3. Sign in with your GitHub account
4. Verify Copilot is active (bottom-right status bar should show Copilot icon)

**Test It**: Open Copilot Chat with `Ctrl+Shift+I` and type: `@workspace Hello, test message`

---

## Step 2: Create GitHub Issues for Agent Tasks

Create structured issues that GitHub Workspace agents can understand.

### Issue Template Example

```markdown
Title: [Phase 7.1.1] Create market_design package structure

Labels: enhancement, phase-7, copilot-task

## Description
Create the foundational Python package structure for the Tariff Design Studio market modeling module.

## Context
- Part of Phase 7: Lightweight Market & Tariff Design Module
- See roadmap.md Section 7.2 (Phase 1: Foundation & Basic TOU)
- Integrates with existing dashboard.py and Pandapower networks

## Requirements

### Directory Structure
Create the following structure:
```
market_design/
├── __init__.py
├── tariff_models.py      # TOU, RTP, VariableGridFee classes
├── tariff_simulator.py   # Main simulation orchestrator
├── demand_response.py    # Price elasticity, consumer behavior
├── revenue_analysis.py   # DSO revenue adequacy
├── grid_integration.py   # Pandapower coupling
├── visualizations.py     # Plotting functions
├── export_utils.py       # PDF/CSV export
└── use_cases/           # Pre-configured scenarios directory
    └── __init__.py
```

### File Content Requirements

**`__init__.py`:**
- Export main classes: TOUTariff, RTPTariff, VariableGridFee, TariffSimulator
- Version string: `__version__ = "0.1.0"`
- Package docstring explaining module purpose

**`tariff_models.py`:**
- Base class: `BaseTariff` (abstract)
  - Methods: `calculate_price(timestamp)`, `calculate_bill(load_profile)`
- `TOUTariff` class (inherits BaseTariff)
  - Properties: time_periods (dict), prices (dict)
  - Methods: `add_time_period()`, `calculate_price()`, `calculate_bill()`
- `RTPTariff` class (inherits BaseTariff)
  - Properties: base_prices (DataFrame), congestion_multiplier, price_cap, price_floor
  - Methods: `load_price_data()`, `apply_congestion()`, `forecast_24h()`
- `VariableGridFee` class
  - Properties: base_fee, zone_multipliers, capacity_charge_rate
  - Methods: `calculate_energy_fee()`, `calculate_capacity_charge()`

**Type hints**: Use Python 3.11+ type hints throughout
**Docstrings**: Google style docstrings for all classes and methods
**Dependencies**: pandas, numpy (already in requirements.txt)

### Acceptance Criteria
- [ ] All files created with correct structure
- [ ] Classes have proper docstrings
- [ ] Type hints on all method signatures
- [ ] No syntax errors (passes `python -m py_compile`)
- [ ] Imports work correctly (`from market_design import TOUTariff`)

### Reference
- See roadmap.md Section 7.2 (Phase 1, Task 1.1)
- Technical architecture in roadmap.md Section 7.0
```

---

## Step 3: Recommended Issues for Phase 7 Kickoff

Create these issues to leverage GitHub Copilot Workspace effectively:

### Priority 1 (Weeks 1-2)
1. `[Phase 7.1.1] Create market_design package structure` (use template above)
2. `[Phase 7.1.2] Implement TOUTariff class with unit tests`
3. `[Phase 7.1.3] Implement demand response price elasticity model`
4. `[Phase 7.1.4] Create basic TOU configuration UI in dashboard.py`
5. `[Phase 7.1.5] Implement bill impact visualization component`

### Priority 2 (Weeks 3-4)
6. `[Phase 7.2.1] Implement RTPTariff class with EPEX data import`
7. `[Phase 7.2.2] Create Pandapower network integration module`
8. `[Phase 7.2.3] Build load profile comparison visualization`

### Priority 3 (Weeks 5-8)
9. `[Phase 7.3.1] Implement VariableGridFee class`
10. `[Phase 7.3.7] Create PDF export functionality`

**Tip**: Create all issues at once, then work through them sequentially. This gives you a clear project board view.

---

## Step 4: Using GitHub Copilot Workspace

### In VS Code (Recommended)

#### Open Copilot Chat
- Shortcut: `Ctrl+Shift+I` (Windows/Linux) or `Cmd+Shift+I` (Mac)
- Or click the chat icon in the sidebar

#### Reference Your Issue
```
@workspace I need to implement GitHub issue #123: Create market_design package structure.

Please create the files and classes as specified in the issue description.
Use the roadmap.md file for context on the overall architecture.
```

#### Iterate with Context
```
@workspace Add type hints to the TOUTariff class following Python 3.11 best practices.
Ensure it integrates with the existing pandas DataFrames used in dashboard.py.
```

#### Generate Tests
```
@workspace Create pytest unit tests for the TOUTariff.calculate_bill() method.
Include edge cases: empty load profile, negative prices, missing time periods.
```

### On GitHub.com (Copilot Workspace Web)

1. Navigate to your issue on GitHub.com
2. Click "Open in Copilot Workspace" button (if available)
3. Copilot will analyze the issue and propose implementation plan
4. Review proposed files/changes
5. Click "Create Pull Request" to open PR with generated code

**Note**: Web interface may have limited availability depending on your subscription tier.

---

## Step 5: Best Practices for Working with Copilot on Phase 7

### Write Clear, Specific Prompts

❌ **Bad Prompt**: 
```
"Create tariff stuff"
```

✅ **Good Prompt**: 
```
@workspace Create a TOUTariff class in market_design/tariff_models.py that:
- Accepts time periods as dict: {"peak": "16:00-20:00", "off-peak": "20:00-16:00"}
- Accepts prices as dict: {"peak": 0.35, "off-peak": 0.15}
- Has a calculate_bill(load_profile: pd.DataFrame) method
- load_profile has columns: ['timestamp', 'load_kw']
- Returns total bill in euros

Include Google-style docstrings and type hints.
```

### Leverage Your Existing Codebase

```
@workspace I need to add a new Streamlit page for Tariff Design Studio.
Use the same structure as the existing solar_installation_mastr() function in dashboard.py.
Include:
- Title with ⚡ emoji
- Progress bars (similar to wind_installation_mastr)
- Tabs for TOU, RTP, and Grid Fees
- Error handling like in storage_installation_mastr()
```

### Iterate Incrementally

Don't ask for entire Phase 7 at once. Break it down:

1. **First**: "Create empty package structure"
2. **Then**: "Implement TOUTariff class skeleton"
3. **Then**: "Add calculate_bill method with logic"
4. **Then**: "Create unit tests"
5. **Then**: "Add visualization integration"

### Use Slash Commands in Chat

- `/new` - Create new workspace for task
- `/tests` - Generate tests for selected code
- `/doc` - Generate documentation
- `/fix` - Fix errors in selected code
- `/explain` - Explain complex code

---

## Step 6: Sample Workflow for Phase 7.1.2 (TOUTariff Implementation)

Here's a complete example workflow from issue to working code:

### Step 6.1: Create the Issue on GitHub
```markdown
Title: [Phase 7.1.2] Implement TOUTariff class with unit tests

Description: See Step 2 template structure...
```

### Step 6.2: In VS Code Copilot Chat
```
@workspace Implement the TOUTariff class from issue #124.

Reference:
- See roadmap.md Section 7.2 Phase 1 for requirements
- Follow the pattern in technologies/photovoltaics.py for class structure
- Use pandas for load profile handling (similar to mastr_preprocessing.py)

The class should:
1. Store time period definitions (peak/off-peak/mid-peak)
2. Store prices per period
3. Calculate which time period a given timestamp belongs to
4. Calculate total bill from a load profile DataFrame
```

### Step 6.3: Review and Refine
```
@workspace The TOUTariff class looks good, but:
1. Add validation: prices must be > 0
2. Add validation: time periods must cover full 24 hours
3. Add a method to visualize the time periods (using plotly)
4. Handle daylight saving time edge cases
```

### Step 6.4: Generate Tests
```
@workspace /tests

Create comprehensive pytest tests for TOUTariff including:
- Normal operation with 3 periods
- Edge case: midnight boundary
- Edge case: single time period (flat rate)
- Error case: overlapping time periods
- Error case: negative price
```

### Step 6.5: Create Documentation
```
@workspace /doc

Create a markdown file docs/tariff_models_guide.md that explains:
- How to use TOUTariff class
- Example code snippets
- Configuration options
- Common pitfalls
```

---

## Step 7: Monitoring and Quality Control

### Always Review Generated Code

After Copilot generates code, check:

- ✅ Does it match the requirements in roadmap.md?
- ✅ Are there edge cases not handled?
- ✅ Does it integrate with existing Pandapower/vpplib code?
- ✅ Are there security issues (input validation)?
- ✅ Is the code style consistent with existing codebase?

### Test Immediately

```powershell
# Run unit tests
.\vise\Scripts\python.exe -m pytest market_design\tests\

# Check code quality
.\vise\Scripts\python.exe -m flake8 market_design\

# Auto-format
.\vise\Scripts\python.exe -m black market_design\

# Type checking
.\vise\Scripts\python.exe -m mypy market_design\
```

### Validate Integration

```powershell
# Test imports
.\vise\Scripts\python.exe -c "from market_design import TOUTariff; print('OK')"

# Run dashboard to check UI integration
.\vise\Scripts\python.exe -m streamlit run dashboard.py
```

---

## Step 8: Recommended GitHub Project Board Setup

### Create a GitHub Project

1. Go to your repository on GitHub.com
2. Click "Projects" tab
3. Create new project: "Phase 7: Tariff Design Studio"
4. Use "Board" layout

### Columns Setup

```
📋 Backlog → 🔨 In Progress → 👀 Review → ✅ Done
```

**Backlog**: All Phase 7 issues (69 tasks from roadmap)  
**In Progress**: Issues you're actively working on with Copilot  
**Review**: Generated code pending your review/testing  
**Done**: Completed and integrated  

### Automation (Optional)

Set up GitHub Actions to:
- Run tests on every PR
- Check code formatting (black, flake8)
- Validate no new errors

**Example `.github/workflows/test.yml`:**
```yaml
name: Test Phase 7

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov black flake8
      - run: pytest market_design/tests/
      - run: black --check market_design/
      - run: flake8 market_design/
```

---

## Step 9: Initial Setup Checklist

Before starting with Copilot Workspace, complete these tasks:

- [ ] Create `market_design/` directory manually
- [ ] Add to `.gitignore`: `__pycache__/`, `*.pyc`, `.pytest_cache/`
- [ ] Create `market_design/tests/` directory
- [ ] Install pytest: `pip install pytest pytest-cov`
- [ ] Install code quality tools: `pip install black flake8 mypy`
- [ ] Create first issue: "Create market_design package structure"
- [ ] Enable GitHub Actions for CI/CD (optional but recommended)
- [ ] Configure Copilot settings in VS Code (Settings → GitHub Copilot)
- [ ] Review roadmap.md Section 7 to understand architecture

---

## Step 10: Quick Start Command Sequence

Run these commands in PowerShell to set up the initial structure:

```powershell
# Navigate to project directory
cd C:\Users\sbirk\Documents\Code\vise-d

# Create package structure
New-Item -ItemType Directory -Path "market_design" -Force
New-Item -ItemType Directory -Path "market_design\tests" -Force
New-Item -ItemType Directory -Path "market_design\use_cases" -Force

# Create empty files for Copilot to populate
New-Item -ItemType File -Path "market_design\__init__.py"
New-Item -ItemType File -Path "market_design\tariff_models.py"
New-Item -ItemType File -Path "market_design\tariff_simulator.py"
New-Item -ItemType File -Path "market_design\demand_response.py"
New-Item -ItemType File -Path "market_design\revenue_analysis.py"
New-Item -ItemType File -Path "market_design\grid_integration.py"
New-Item -ItemType File -Path "market_design\visualizations.py"
New-Item -ItemType File -Path "market_design\export_utils.py"

# Create test directory structure
New-Item -ItemType File -Path "market_design\tests\__init__.py"
New-Item -ItemType File -Path "market_design\tests\test_tariff_models.py"
New-Item -ItemType File -Path "market_design\tests\test_demand_response.py"

# Install test and development dependencies
.\vise\Scripts\python.exe -m pip install pytest pytest-cov black flake8 mypy

# Verify setup
Test-Path "market_design"  # Should return True
.\vise\Scripts\python.exe -c "import market_design; print('Package accessible')"
```

### Update .gitignore

Add these lines to `.gitignore`:

```
# Python
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.mypy_cache/
.coverage
htmlcov/

# Phase 7 specific
market_design/__pycache__/
market_design/tests/__pycache__/
```

---

## 🎯 Your First Copilot Task

After completing Step 10, start with this prompt in VS Code Copilot Chat:

```
@workspace I'm implementing Phase 7 of the VISE-D project (see roadmap.md Section 7.2).

First task: Create the market_design package with proper initialization:

1. In market_design/__init__.py:
   - Add package docstring explaining this is the Tariff Design Studio module
   - Add version: __version__ = "0.1.0"
   - Prepare exports for: TOUTariff, RTPTariff, VariableGridFee, TariffSimulator
   - Add proper type hints and imports

2. In market_design/tariff_models.py:
   - Create BaseTariff abstract base class with ABC
   - Add abstract methods: calculate_price(timestamp), calculate_bill(load_profile)
   - Add proper docstrings explaining the interface

Use Python 3.11+ type hints and Google-style docstrings.
Reference the existing code style in dashboard.py and technologies/ folder.
```

---

## Troubleshooting Common Issues

### Issue: Copilot Doesn't Understand Context

**Solution**: Be more explicit with file references
```
@workspace In the file dashboard.py, find the function solar_installation_mastr() 
starting at line 950. I want to create a similar function called tariff_design_studio()
with the same structure but for tariff configuration instead of solar data.
```

### Issue: Generated Code Has Errors

**Solution**: Ask Copilot to fix them
```
@workspace /fix

The TOUTariff class has an error on line 45. The time_periods dict is not properly 
initialized. Please fix this and add validation to ensure all required fields are present.
```

### Issue: Code Doesn't Match Project Style

**Solution**: Reference existing files explicitly
```
@workspace Please rewrite the TOUTariff class to match the coding style used in 
technologies/photovoltaics.py. Use the same:
- Import organization
- Class structure
- Docstring format
- Error handling patterns
```

### Issue: Tests Don't Cover Edge Cases

**Solution**: Request specific test scenarios
```
@workspace The current tests for calculate_bill() are insufficient. Add tests for:
1. Load profile with gaps (missing hours)
2. Load profile spanning multiple days
3. Leap year February 29th
4. Daylight saving time transition
5. Empty DataFrame
6. Non-chronological timestamps
```

---

## Tips for Maximum Productivity

### 1. Keep Roadmap.md Open
Always have `roadmap.md` open in VS Code so Copilot can reference it with `@workspace`

### 2. Work in Small Batches
- Implement one class at a time
- Test immediately after implementation
- Commit working code frequently

### 3. Use Multi-File Context
```
@workspace Using:
- roadmap.md for architecture
- dashboard.py for Streamlit patterns
- technologies/photovoltaics.py for class structure

Create the VariableGridFee class in market_design/tariff_models.py
```

### 4. Save Good Prompts
When a prompt works well, save it in a `prompts.md` file for reuse with variations

### 5. Review Copilot Suggestions Before Accepting
- Read the code carefully
- Test edge cases manually
- Verify integration points

---

## Next Steps After Setup

Once you've completed Steps 1-10:

1. **Week 1**: Implement Phase 1 tasks (TOUTariff, basic UI, bill visualization)
2. **Week 2**: Add tests and documentation for Phase 1 components
3. **Week 3-4**: Implement Phase 2 (RTP, Pandapower integration)
4. **Week 5-6**: Implement Phase 3 (Variable grid fees, export functionality)
5. **Week 7**: Create use cases and validation

**Track Progress**: Update your GitHub Project board after each completed task

---

## Additional Resources

- **GitHub Copilot Documentation**: https://docs.github.com/copilot
- **VS Code Copilot Chat Guide**: https://code.visualstudio.com/docs/copilot/copilot-chat
- **VISE-D Roadmap**: `roadmap.md` Section 7
- **Technical Architecture**: `roadmap.md` Section 7.0-7.3
- **Project Repository**: https://github.com/Pyosch/vise-d

---

## Questions or Issues?

If you get stuck:
1. Check this guide's troubleshooting section
2. Review the specific Phase requirements in `roadmap.md`
3. Ask Copilot to explain: `@workspace /explain [selected code]`
4. Consult existing similar code in `technologies/` folder

**Remember**: Copilot is a tool to accelerate development, but you remain the architect. Always review, test, and validate generated code before integrating it into the main codebase.

Good luck with Phase 7 implementation! 🚀
