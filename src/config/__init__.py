"""Configuration package for VISE-D application.

Provides centralized configuration management with cross-platform path handling
and application constants.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

from src.config.constants import (
    CACHE,
    DWD,
    LIMITS,
    NETWORK,
    OPENSTEF,
    UI,
    CacheConfig,
    DWDConfig,
    NetworkConfig,
    OpenSTEFConfig,
    UIConfig,
    ValidationLimits,
)
from src.config.paths import (
    CACHE_DIR,
    DATA_DIR,
    DOCS_DIR,
    ERA5_WIND_DIR,
    EXAMPLES_DIR,
    FIGURES_DIR,
    MASTR_DB_PATH,
    MLRUNS_DIR,
    PROJECT_ROOT,
    ensure_directories,
    get_relative_path,
)

__all__ = [
    # Configuration objects
    "CACHE",
    "DWD",
    "LIMITS",
    "NETWORK",
    "OPENSTEF",
    "UI",
    # Configuration classes
    "CacheConfig",
    "DWDConfig",
    "NetworkConfig",
    "OpenSTEFConfig",
    "UIConfig",
    "ValidationLimits",
    # Path constants
    "PROJECT_ROOT",
    "DATA_DIR",
    "ERA5_WIND_DIR",
    "FIGURES_DIR",
    "CACHE_DIR",
    "MASTR_DB_PATH",
    "MLRUNS_DIR",
    "DOCS_DIR",
    "EXAMPLES_DIR",
    # Path utilities
    "ensure_directories",
    "get_relative_path",
]
