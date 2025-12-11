"""Tests for validation utilities"""
import pytest
from app.utils.validation import validate_health_data


def test_validate_health_data_valid():
    """Test validation with valid data"""
    result = validate_health_data("sleep_duration", 7.5, "hours")
    assert result["valid"] is True


def test_validate_health_data_invalid_type():
    """Test validation with invalid data type"""
    result = validate_health_data("invalid_type", 7.5, "hours")
    assert result["valid"] is False
    assert "error" in result

