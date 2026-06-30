"""Error handling utilities for VISE-D dashboard.

Provides decorators and utilities for graceful error handling including database operations,
API calls, data processing, and file system operations with user-friendly Streamlit messages.

Author: Pyosch
AI Assistance: Claude Code (Claude Opus 4.8)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["Claude Code (Claude Opus 4.8)"]

import streamlit as st
import pandas as pd
import traceback
import logging
from typing import Any, Callable, Optional, Dict
from functools import wraps
import sqlite3
import requests
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vise_d_errors.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass


class APIError(Exception):
    """Custom exception for API-related errors."""
    pass


class DataProcessingError(Exception):
    """Custom exception for data processing errors."""
    pass


def handle_database_errors(func: Callable) -> Callable:
    """Decorator to handle database operation errors gracefully.
    
    Catches SQLite errors and displays user-friendly error messages with
    troubleshooting guidance in the Streamlit UI.
    
    Args:
        func: Function to wrap with error handling.
        
    Returns:
        Wrapped function that handles database errors.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except sqlite3.OperationalError as e:
            logger.error(f"Database operational error in {func.__name__}: {str(e)}")
            st.error("🗄️ **Database Connection Error**")
            st.error("The MaStR database appears to be unavailable or corrupted.")
            
            with st.expander("🔧 **Troubleshooting Steps**"):
                st.markdown("""
                1. **Check database file**: Ensure `data/open-mastr.db` exists
                2. **Verify file permissions**: Make sure the database file is readable
                3. **Database integrity**: The database file may be corrupted
                4. **Restart application**: Try refreshing the page
                """)
            
            st.info(
                "💡 **Alternative**: Try selecting a different location or contact support."
            )
            return None
            
        except sqlite3.DatabaseError as e:
            logger.error(f"Database error in {func.__name__}: {str(e)}")
            st.error("🗄️ **Database Error**")
            st.error(f"Database operation failed: {str(e)}")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            st.error("❌ **Unexpected Database Error**")
            st.error("An unexpected error occurred while accessing the database.")
            
            with st.expander("🔍 **Technical Details**"):
                st.code(str(e))
            
            return None
    return wrapper


def handle_api_errors(func: Callable) -> Callable:
    """Decorator to handle API call errors gracefully.
    
    Catches network and API errors and displays user-friendly error messages
    with troubleshooting guidance in the Streamlit UI.
    
    Args:
        func: Function to wrap with error handling.
        
    Returns:
        Wrapped function that handles API errors.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.ConnectionError:
            logger.error(f"Network connection error in {func.__name__}")
            st.error("🌐 **Network Connection Error**")
            st.error("Unable to connect to external data services.")
            
            with st.expander("🔧 **Troubleshooting Steps**"):
                st.markdown("""
                1. **Check internet connection**: Ensure you're connected to the internet
                2. **Firewall settings**: Check if firewall is blocking the connection
                3. **VPN issues**: Try disabling VPN if active
                4. **Service availability**: The external service may be temporarily down
                """)
            return None
            
        except requests.Timeout:
            logger.error(f"Request timeout in {func.__name__}")
            st.error("⏱️ **Request Timeout**")
            st.error("The external service is taking too long to respond.")
            st.info("💡 Please try again in a few moments.")
            return None
            
        except requests.HTTPError as e:
            logger.error(f"HTTP error in {func.__name__}: {str(e)}")
            st.error(f"🌐 **Service Error**: {e.response.status_code}")
            st.error("The external service returned an error.")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected API error in {func.__name__}: {str(e)}")
            st.error("❌ **API Communication Error**")
            st.error("Failed to communicate with external services.")
            return None
    return wrapper


def handle_data_processing_errors(func: Callable) -> Callable:
    """Decorator to handle data processing errors gracefully.
    
    Catches pandas and data processing errors and displays user-friendly
    error messages in the Streamlit UI.
    
    Args:
        func: Function to wrap with error handling.
        
    Returns:
        Wrapped function that handles data processing errors.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except pd.errors.EmptyDataError:
            logger.error(f"Empty data error in {func.__name__}")
            st.error("📊 **No Data Available**")
            st.error("The selected location or time period has no available data.")
            st.info("💡 **Try**: Select a different location or adjust your parameters.")
            return None
            
        except pd.errors.ParserError as e:
            logger.error(f"Data parsing error in {func.__name__}: {str(e)}")
            st.error("📊 **Data Format Error**")
            st.error("The data could not be processed due to formatting issues.")
            return None
            
        except KeyError as e:
            logger.error(f"Missing data column in {func.__name__}: {str(e)}")
            st.error("📊 **Data Structure Error**")
            st.error(f"Expected data column is missing: {str(e)}")
            st.info("💡 The database may have been updated or corrupted.")
            return None
            
        except ValueError as e:
            logger.error(f"Data value error in {func.__name__}: {str(e)}")
            st.error("📊 **Data Value Error**")
            st.error("Invalid data values encountered during processing.")
            
            with st.expander("🔍 **Technical Details**"):
                st.code(str(e))
            return None
            
        except Exception as e:
            logger.error(
                f"Unexpected data processing error in {func.__name__}: {str(e)}"
            )
            st.error("❌ **Data Processing Error**")
            st.error("An unexpected error occurred while processing the data.")
            return None
    return wrapper


def safe_file_operation(file_path: str, operation: str = "read") -> bool:
    """Check if file operations can be performed safely.
    
    Validates file existence, permissions, and size before operations
    and displays user-friendly error messages in Streamlit UI.
    
    Args:
        file_path: Path to the file.
        operation: Type of operation ('read', 'write', 'delete').
        
    Returns:
        True if operation is safe, False otherwise.
    """
    path = Path(file_path)
    
    try:
        if operation == "read":
            if not path.exists():
                st.error(f"📁 **File Not Found**: `{file_path}`")
                st.info("💡 Please check if the file exists and the path is correct.")
                return False
            if not path.is_file():
                st.error(f"📁 **Invalid File**: `{file_path}` is not a file")
                return False
            if not path.stat().st_size > 0:
                st.warning(f"📁 **Empty File**: `{file_path}` appears to be empty")
                return False
                
        elif operation == "write":
            if not path.parent.exists():
                st.error(f"📁 **Directory Not Found**: `{path.parent}`")
                return False
            if path.exists() and not path.is_file():
                st.error(
                    f"📁 **Cannot Write**: `{file_path}` exists but is not a file"
                )
                return False
                
        return True
        
    except PermissionError:
        st.error(f"🔒 **Permission Denied**: Cannot {operation} file `{file_path}`")
        st.info("💡 Check file permissions or try running as administrator.")
        return False
    except Exception as e:
        st.error(f"📁 **File System Error**: {str(e)}")
        return False


def display_error_summary(errors: Dict[str, Any]) -> None:
    """Display a comprehensive error summary in Streamlit UI.
    
    Args:
        errors: Dictionary of error types and their details.
    """
    if not errors:
        return
        
    st.error("❌ **Operation Failed - Error Summary**")
    
    error_types = {
        'database': '🗄️ Database Errors',
        'api': '🌐 Network/API Errors', 
        'validation': '📝 Input Validation Errors',
        'processing': '📊 Data Processing Errors',
        'file': '📁 File System Errors'
    }
    
    for error_type, title in error_types.items():
        if error_type in errors and errors[error_type]:
            with st.expander(title):
                for error in errors[error_type]:
                    st.error(error)


def log_user_action(action: str, details: Dict[str, Any] = None) -> None:
    """Log user actions for debugging and analytics.
    
    Args:
        action: Description of the action.
        details: Additional details about the action.
    """
    log_entry = f"User action: {action}"
    if details:
        log_entry += f" | Details: {details}"
    logger.info(log_entry)


def create_error_report(error: Exception, context: Dict[str, Any] = None) -> str:
    """Create a detailed error report for debugging.
    
    Args:
        error: The exception that occurred.
        context: Additional context about the error.
        
    Returns:
        Formatted error report string.
    """
    report_lines = [
        "=" * 50,
        "VISE-D ERROR REPORT",
        "=" * 50,
        f"Error Type: {type(error).__name__}",
        f"Error Message: {str(error)}",
        f"Timestamp: {pd.Timestamp.now()}",
        ""
    ]
    
    if context:
        report_lines.extend([
            "Context Information:",
            "-" * 20
        ])
        for key, value in context.items():
            report_lines.append(f"{key}: {value}")
        report_lines.append("")
    
    report_lines.extend([
        "Stack Trace:",
        "-" * 20,
        traceback.format_exc(),
        "=" * 50
    ])
    
    return "\n".join(report_lines)


def show_loading_with_progress(
    message: str, 
    progress_callback: Optional[Callable] = None
):
    """Context manager for showing loading progress in Streamlit UI.
    
    Args:
        message: Loading message to display.
        progress_callback: Optional callback function for progress updates.
        
    Returns:
        LoadingContext instance for use with 'with' statement.
    """
    class LoadingContext:
        """Context manager for progress tracking."""
        
        def __init__(self, message: str):
            self.message = message
            self.progress_bar = None
            self.status_text = None
            
        def __enter__(self):
            self.progress_bar = st.progress(0)
            self.status_text = st.empty()
            self.status_text.text(f"🔄 {self.message}")
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.progress_bar:
                self.progress_bar.progress(100)
            if self.status_text:
                if exc_type is None:
                    self.status_text.text("✅ Operation completed successfully!")
                else:
                    self.status_text.text("❌ Operation failed!")
            
        def update_progress(self, progress: int, message: str = None):
            """Update progress bar and optional status message.
            
            Args:
                progress: Progress percentage (0-100).
                message: Optional status message to display.
            """
            if self.progress_bar:
                self.progress_bar.progress(progress)
            if self.status_text and message:
                self.status_text.text(f"🔄 {message}")
    
    return LoadingContext(message)
