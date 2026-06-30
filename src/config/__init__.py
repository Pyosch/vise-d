"""Configuration package for VISE-D application.

Provides centralized configuration management with cross-platform path handling
and application constants.

Author: Pyosch
AI Assistance: Claude Code (Claude Opus 4.8)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["Claude Code (Claude Opus 4.8)"]

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
    EXAMPLES_DIR,
    FIGURES_DIR,
    MASTR_DB_PATH,
    MLRUNS_DIR,
    PROJECT_ROOT,
    PV_PARAMS_DIR,
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
    "FIGURES_DIR",
    "CACHE_DIR",
    "MASTR_DB_PATH",
    "PV_PARAMS_DIR",
    "MLRUNS_DIR",
    "DOCS_DIR",
    "EXAMPLES_DIR",
    # Path utilities
    "ensure_directories",
    "get_relative_path",
]
