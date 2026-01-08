"""Utility functions for VISE-D application.

Provides validation and error handling utilities for robust data processing.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

from src.utils.validation import (
    InputValidator,
    ValidationError,
    display_validation_results,
    safe_database_operation,
    validate_energy_system_inputs,
    validate_location_selection,
)
from src.utils.error_handling import (
    APIError,
    DatabaseError,
    DataProcessingError,
    create_error_report,
    display_error_summary,
    handle_api_errors,
    handle_data_processing_errors,
    handle_database_errors,
    log_user_action,
    safe_file_operation,
    show_loading_with_progress,
)

__all__ = [
    # Validation
    "InputValidator",
    "ValidationError",
    "display_validation_results",
    "safe_database_operation",
    "validate_energy_system_inputs",
    "validate_location_selection",
    # Error handling
    "APIError",
    "DatabaseError",
    "DataProcessingError",
    "create_error_report",
    "display_error_summary",
    "handle_api_errors",
    "handle_data_processing_errors",
    "handle_database_errors",
    "log_user_action",
    "safe_file_operation",
    "show_loading_with_progress",
]
