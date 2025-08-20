# Input Validation Utilities for VISE-D Dashboard
# Author: GitHub Copilot Assistant
# Date: August 20, 2025

import streamlit as st
import pandas as pd
from typing import Union, List, Optional, Tuple
import re

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

class InputValidator:
    """Comprehensive input validation for Streamlit forms"""
    
    @staticmethod
    def validate_numeric_range(value: float, min_val: float, max_val: float, 
                             field_name: str) -> Tuple[bool, str]:
        """
        Validate numeric input within specified range
        
        Args:
            value: Input value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            field_name: Name of the field for error messages
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if value < min_val or value > max_val:
            return False, f"❌ {field_name} must be between {min_val} and {max_val}. Current value: {value}"
        return True, ""
    
    @staticmethod
    def validate_positive_number(value: float, field_name: str, 
                                allow_zero: bool = True) -> Tuple[bool, str]:
        """
        Validate that a number is positive (and optionally allow zero)
        
        Args:
            value: Input value to validate
            field_name: Name of the field for error messages
            allow_zero: Whether zero is allowed
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if allow_zero and value < 0:
            return False, f"❌ {field_name} must be greater than or equal to 0. Current value: {value}"
        elif not allow_zero and value <= 0:
            return False, f"❌ {field_name} must be greater than 0. Current value: {value}"
        return True, ""
    
    @staticmethod
    def validate_percentage(value: float, field_name: str) -> Tuple[bool, str]:
        """
        Validate percentage input (0-100)
        
        Args:
            value: Input value to validate
            field_name: Name of the field for error messages
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        return InputValidator.validate_numeric_range(value, 0.0, 100.0, field_name)
    
    @staticmethod
    def validate_efficiency(value: float, field_name: str) -> Tuple[bool, str]:
        """
        Validate efficiency input (0-100%)
        
        Args:
            value: Input value to validate
            field_name: Name of the field for error messages
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if value < 0 or value > 100:
            return False, f"❌ {field_name} must be between 0% and 100%. Current value: {value}%"
        if value > 95:
            return True, f"⚠️ Warning: {field_name} is very high ({value}%). Please verify this value."
        return True, ""
    
    @staticmethod
    def validate_geographic_coordinate(latitude: float, longitude: float) -> Tuple[bool, str]:
        """
        Validate geographic coordinates
        
        Args:
            latitude: Latitude value
            longitude: Longitude value
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if latitude < -90 or latitude > 90:
            return False, f"❌ Latitude must be between -90° and 90°. Current value: {latitude}°"
        if longitude < -180 or longitude > 180:
            return False, f"❌ Longitude must be between -180° and 180°. Current value: {longitude}°"
        return True, ""
    
    @staticmethod
    def validate_power_rating(value: float, field_name: str, max_reasonable: float = 10000) -> Tuple[bool, str]:
        """
        Validate power rating inputs with reasonable limits
        
        Args:
            value: Power value in kW
            field_name: Name of the field for error messages
            max_reasonable: Maximum reasonable power rating
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if value < 0:
            return False, f"❌ {field_name} cannot be negative. Current value: {value} kW"
        if value > max_reasonable:
            return True, f"⚠️ Warning: {field_name} is very high ({value} kW). Please verify this value."
        if value == 0:
            return True, f"⚠️ Warning: {field_name} is set to 0 kW. This may result in no energy generation/consumption."
        return True, ""
    
    @staticmethod
    def validate_angle(value: float, field_name: str, min_angle: float = 0, max_angle: float = 360) -> Tuple[bool, str]:
        """
        Validate angle inputs (typically 0-360° or 0-90°)
        
        Args:
            value: Angle value in degrees
            field_name: Name of the field
            min_angle: Minimum allowed angle
            max_angle: Maximum allowed angle
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        return InputValidator.validate_numeric_range(value, min_angle, max_angle, f"{field_name} (degrees)")

def display_validation_results(validation_results: List[Tuple[bool, str]], 
                             show_success: bool = True) -> bool:
    """
    Display validation results in Streamlit UI
    
    Args:
        validation_results: List of validation results from validator functions
        show_success: Whether to show success messages
        
    Returns:
        bool: True if all validations passed, False otherwise
    """
    all_valid = True
    errors = []
    warnings = []
    
    for is_valid, message in validation_results:
        if not is_valid:
            all_valid = False
            errors.append(message)
        elif message and ("Warning" in message or "⚠️" in message):
            warnings.append(message)
    
    # Display errors
    if errors:
        st.error("**Input Validation Errors:**")
        for error in errors:
            st.error(error)
    
    # Display warnings
    if warnings:
        for warning in warnings:
            st.warning(warning)
    
    # Display success message if everything is valid
    if all_valid and show_success and not warnings:
        st.success("✅ All inputs are valid!")
    
    return all_valid

def validate_location_selection(location: str, available_locations: List[str]) -> Tuple[bool, str]:
    """
    Validate location selection from dropdown
    
    Args:
        location: Selected location
        available_locations: List of available locations
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not location:
        return False, "❌ Please select a location from the dropdown"
    if location not in available_locations:
        return False, f"❌ Selected location '{location}' is not available in the database"
    return True, ""

def safe_database_operation(operation_func, error_message: str = "Database operation failed"):
    """
    Decorator for safe database operations with error handling
    
    Args:
        operation_func: Function to execute safely
        error_message: Custom error message for failures
        
    Returns:
        Result of operation_func or None if error occurred
    """
    try:
        return operation_func()
    except Exception as e:
        st.error(f"❌ {error_message}")
        st.error(f"Technical details: {str(e)}")
        st.info("💡 **Possible solutions:**")
        st.info("- Check your internet connection")
        st.info("- Verify the selected location has data available")
        st.info("- Try refreshing the page")
        return None

def validate_energy_system_inputs(
    power_rating: float = None,
    efficiency: float = None, 
    capacity: float = None,
    angle: float = None,
    azimuth: float = None
) -> List[Tuple[bool, str]]:
    """
    Comprehensive validation for energy system inputs
    
    Args:
        power_rating: Power rating in kW
        efficiency: Efficiency percentage (0-100)
        capacity: Capacity in kWh
        angle: Tilt angle in degrees (0-90)
        azimuth: Azimuth angle in degrees (0-360)
        
    Returns:
        List of validation results
    """
    results = []
    
    if power_rating is not None:
        results.append(InputValidator.validate_power_rating(power_rating, "Power Rating"))
    
    if efficiency is not None:
        results.append(InputValidator.validate_efficiency(efficiency, "Efficiency"))
    
    if capacity is not None:
        results.append(InputValidator.validate_positive_number(capacity, "Capacity"))
    
    if angle is not None:
        results.append(InputValidator.validate_angle(angle, "Tilt Angle", 0, 90))
    
    if azimuth is not None:
        results.append(InputValidator.validate_angle(azimuth, "Azimuth Angle", 0, 360))
    
    return results
