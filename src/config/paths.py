"""Cross-platform path configuration for VISE-D project.

Uses pathlib for platform-independent path handling across Windows, Linux, and macOS.

Author: Pyosch
AI Assistance: Claude Code (Claude Opus 4.8)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["Claude Code (Claude Opus 4.8)"]

import os
from pathlib import Path
from typing import Final

# Project root directory (vise-d/)
PROJECT_ROOT: Final[Path] = Path(__file__).parent.parent.parent.resolve()

# Data directories
DATA_DIR: Final[Path] = PROJECT_ROOT / "data"
FIGURES_DIR: Final[Path] = DATA_DIR / "figures"

# Cache directory
CACHE_DIR: Final[Path] = PROJECT_ROOT / "cache"

# MaStR database path
# Note: The open-MaStR database is located in the root data directory.
# Override with the VISED_MASTR_DB_PATH environment variable to point elsewhere — or, to
# exercise the online REST fallback while keeping the real DB in place, set it to a path
# that does NOT exist:
#   * a non-existent file inside data/  → tier 2 (town dropdown from the shipped CSVs +
#     live plant data), e.g. VISED_MASTR_DB_PATH=data/__force_online__.db
#   * a non-existent path in an empty dir → tier 3 (free-text Ort/PLZ + live plant data).
_MASTR_DB_ENV = os.environ.get("VISED_MASTR_DB_PATH")
MASTR_DB_PATH: Final[Path] = Path(_MASTR_DB_ENV) if _MASTR_DB_ENV else DATA_DIR / "open-mastr.db"

# PV parametrization cache directory (one CSV per location)
PV_PARAMS_DIR: Final[Path] = DATA_DIR / "pv_parametrization"

# MLflow tracking directory
MLRUNS_DIR: Final[Path] = PROJECT_ROOT / "mlruns"

# Documentation directory
DOCS_DIR: Final[Path] = PROJECT_ROOT / "docs"

# Examples directory
EXAMPLES_DIR: Final[Path] = PROJECT_ROOT / "examples"


def ensure_directories() -> None:
    """Create necessary directories if they don't exist.
    
    Creates cache, data, and figures directories to ensure
    the application can store data without errors.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def get_relative_path(absolute_path: Path) -> Path:
    """Convert absolute path to project-relative path.
    
    Args:
        absolute_path: Absolute path to convert.
        
    Returns:
        Path relative to PROJECT_ROOT.
        
    Raises:
        ValueError: If path is not within project directory.
    """
    try:
        return absolute_path.relative_to(PROJECT_ROOT)
    except ValueError as e:
        raise ValueError(
            f"Path {absolute_path} is not within project root {PROJECT_ROOT}"
        ) from e
