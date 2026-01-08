"""Cross-platform path configuration for VISE-D project.

Uses pathlib for platform-independent path handling across Windows, Linux, and macOS.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

from pathlib import Path
from typing import Final

# Project root directory (vise-d/)
PROJECT_ROOT: Final[Path] = Path(__file__).parent.parent.parent.resolve()

# Data directories
DATA_DIR: Final[Path] = PROJECT_ROOT / "data"
ERA5_WIND_DIR: Final[Path] = DATA_DIR / "era5_germany_2024_wind"
FIGURES_DIR: Final[Path] = DATA_DIR / "figures"

# Cache directory
CACHE_DIR: Final[Path] = PROJECT_ROOT / "cache"

# MaStR database path
# Note: The open-MaStR database is located in the root data directory
MASTR_DB_PATH: Final[Path] = DATA_DIR / "open-mastr.db"

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
