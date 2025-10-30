# [Phase 7.1.1] Create market_design Package Structure

**Labels**: `enhancement`, `phase-7`, `priority-high`, `copilot-ready`  
**Milestone**: Phase 7.1 - Foundation  
**Estimated Time**: 4-6 hours  
**Dependencies**: None  
**Assignee**: [Your name]

---

## 📋 Description

Create the foundational Python package structure for the Tariff Design Studio market modeling module. This establishes the architecture for all subsequent Phase 7 development.

---

## 🎯 Context

- **Part of**: Phase 7 - Lightweight Market & Tariff Design Module
- **Reference**: `roadmap.md` Section 7.2 (Phase 1: Foundation & Basic TOU)
- **Integration Points**: `dashboard.py` (Streamlit UI), Pandapower networks, existing `technologies/` modules

---

## 📦 Directory Structure to Create

```
market_design/
├── __init__.py                # Package initialization & exports
├── tariff_models.py           # TOU, RTP, VariableGridFee classes
├── tariff_simulator.py        # Main simulation orchestrator
├── demand_response.py         # Price elasticity, consumer behavior
├── revenue_analysis.py        # DSO revenue adequacy calculations
├── grid_integration.py        # Pandapower coupling logic
├── visualizations.py          # Plotting functions for Tariff Studio
├── export_utils.py            # PDF/CSV report generation
└── use_cases/                 # Pre-configured scenario directory
    └── __init__.py
```

Additionally create:
```
market_design/tests/           # Unit tests directory
├── __init__.py
├── test_tariff_models.py
├── test_demand_response.py
├── test_grid_integration.py
└── test_revenue_analysis.py
```

---

## ✅ File Content Requirements

### `market_design/__init__.py`

**Required content**:
```python
"""
Tariff Design Studio - Lightweight Market Modeling Module

This package provides tools for designing and analyzing electricity tariffs
including Time-of-Use (TOU), Real-Time Pricing (RTP), and variable grid fees.

Main Components:
- tariff_models: TOUTariff, RTPTariff, VariableGridFee classes
- tariff_simulator: Orchestrate multi-customer simulations
- demand_response: Model price-responsive consumer behavior
- revenue_analysis: DSO revenue adequacy calculations
- grid_integration: Couple with Pandapower network analysis
- visualizations: Create interactive charts for Streamlit UI
- export_utils: Generate PDF/CSV reports
"""

__version__ = "0.1.0"
__author__ = "VISE-D Project"

# Core exports (classes will be implemented in subsequent tasks)
# from .tariff_models import BaseTariff, TOUTariff, RTPTariff, VariableGridFee
# from .tariff_simulator import TariffSimulator
# from .demand_response import DemandResponseModel
# from .revenue_analysis import RevenueAnalyzer

# Commented out until classes are implemented
# __all__ = [
#     "BaseTariff",
#     "TOUTariff",
#     "RTPTariff",
#     "VariableGridFee",
#     "TariffSimulator",
#     "DemandResponseModel",
#     "RevenueAnalyzer",
# ]
```

### `market_design/tariff_models.py`

**Required content** (skeleton only - full implementation in Task 1.2):
```python
"""
Tariff model classes for electricity pricing schemes.

Provides abstract base class and concrete implementations for:
- Time-of-Use (TOU) tariffs
- Real-Time Pricing (RTP) tariffs
- Variable grid fees
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import numpy as np


class BaseTariff(ABC):
    """
    Abstract base class for all tariff types.
    
    All tariff models must implement methods to calculate prices
    and customer bills based on load profiles.
    """
    
    @abstractmethod
    def calculate_price(self, timestamp: datetime) -> float:
        """
        Calculate the electricity price at a given timestamp.
        
        Parameters
        ----------
        timestamp : datetime
            The time for which to calculate the price
            
        Returns
        -------
        float
            Price in €/kWh
        """
        pass
    
    @abstractmethod
    def calculate_bill(self, load_profile: pd.DataFrame) -> float:
        """
        Calculate the total bill for a customer's load profile.
        
        Parameters
        ----------
        load_profile : pd.DataFrame
            DataFrame with columns ['timestamp', 'load_kw']
            
        Returns
        -------
        float
            Total bill in euros
        """
        pass


# Placeholder classes - to be implemented in subsequent tasks
class TOUTariff(BaseTariff):
    """Time-of-Use tariff with defined time periods and fixed prices per period."""
    pass


class RTPTariff(BaseTariff):
    """Real-Time Pricing tariff with dynamic prices based on market data."""
    pass


class VariableGridFee:
    """Variable grid fee with energy-based and/or capacity-based components."""
    pass
```

### Other Module Files

All other `.py` files should be created with:
1. **Module docstring** explaining purpose
2. **Standard imports section** (ABC, typing, pandas, numpy as needed)
3. **Placeholder comment**: `# Implementation in Phase 7.X.X - See roadmap.md`

Example for `demand_response.py`:
```python
"""
Demand response modeling for price-responsive consumer behavior.

Provides functions to model load shifting and reduction based on
price signals from TOU or RTP tariffs.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional

# Implementation in Phase 7.1.3 - See roadmap.md Section 7.2
```

### `market_design/tests/__init__.py`

Empty file (just create it).

### Test Module Files

Each `test_*.py` file should contain:
```python
"""Unit tests for [module_name]."""

import pytest
import pandas as pd
from market_design.[module_name] import [ClassOrFunctionName]

# Tests will be implemented alongside feature development
# See roadmap.md Section 7.2 for testing requirements
```

---

## 🔧 Technical Requirements

### Type Hints
- Use Python 3.11+ type hints on **all** public functions and methods
- Use `typing` module for complex types: `Dict`, `List`, `Optional`, etc.

### Docstrings
- **Google style** docstrings for all modules, classes, and public methods
- Include: Description, Parameters, Returns, Examples (where helpful)
- Reference: https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings

### Dependencies
These packages are already in `requirements.txt`:
- `pandas >= 1.5.0`
- `numpy >= 1.24.0`
- `plotly >= 5.0.0` (for visualizations.py)

No new dependencies should be added in this task.

### Code Style
- Follow **PEP 8** style guidelines
- Use **black** formatter (line length 88)
- Pass **flake8** linting with no errors

---

## ✅ Acceptance Criteria

Before marking this issue as complete, verify:

- [ ] All directories created with correct structure
- [ ] All `.py` files created with docstrings
- [ ] `__init__.py` has package version and docstring
- [ ] `BaseTariff` abstract class defined with required methods
- [ ] Type hints present on all method signatures
- [ ] No syntax errors: `python -m py_compile market_design/*.py`
- [ ] Package imports work: `python -c "import market_design; print(market_design.__version__)"`
- [ ] Black formatting passes: `black --check market_design/`
- [ ] Flake8 passes: `flake8 market_design/`

---

## 🧪 Testing Instructions

After creating the structure, run these commands in PowerShell:

```powershell
# Navigate to project root
cd C:\Users\sbirk\Documents\Code\vise-d

# Activate virtual environment (should already be active)
.\vise\Scripts\Activate.ps1

# Check syntax of all files
Get-ChildItem -Path market_design -Filter *.py -Recurse | ForEach-Object { 
    python -m py_compile $_.FullName 
}

# Test package import
python -c "import market_design; print(f'Package version: {market_design.__version__}')"

# Run formatters and linters
black market_design/
flake8 market_design/
```

Expected output: No errors, package version prints as "0.1.0"

---

## 📚 Reference Materials

- **Roadmap**: `roadmap.md` Section 7.0 (Architecture) and 7.2 (Phase 1)
- **Existing Code Style**: See `technologies/photovoltaics.py` for reference
- **Dashboard Integration**: See `dashboard.py` (especially page functions like `solar_installation_mastr()`)
- **Copilot Prompt Template**: `project_management/phase_7/copilot_prompts/class_creation.md`

---

## 🤖 GitHub Copilot Prompt Suggestion

Copy this into VS Code Copilot Chat to get started:

```
@workspace I need to create the market_design package structure for Phase 7.

Create the following structure:
- market_design/ directory with 8 .py files + use_cases/ subdirectory
- market_design/tests/ directory with 4 test files

Requirements:
1. __init__.py: Package docstring, version "0.1.0", commented-out exports
2. tariff_models.py: BaseTariff abstract class with calculate_price() and calculate_bill() methods
3. Other modules: Module docstrings + placeholder comments
4. All files: Google-style docstrings, type hints, PEP 8 compliant

Reference:
- Existing code style in technologies/photovoltaics.py
- See roadmap.md Section 7.2 for architecture details

Create all files according to the issue template in:
project_management/phase_7/issue_templates/01_package_structure.md
```

---

## 🗒️ Notes

- This task establishes the **foundation** for all Phase 7 work
- Focus on clean structure and documentation over complex logic
- Full implementations will come in subsequent tasks (1.2, 1.3, etc.)
- Keep this issue open until all acceptance criteria are met

---

**Created**: [Date]  
**Last Updated**: [Date]  
**Status**: Open / In Progress / Complete
