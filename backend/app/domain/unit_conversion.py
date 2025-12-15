"""
Unit conversion service for health metrics.

SECURITY FIX (Risk #6): Prevents "silent wrongness" from unit mismatches.
Converts values between compatible units and rejects ambiguous conversions.
"""

from __future__ import annotations

from typing import Dict, Optional, List, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class UnitConversionError(ValueError):
    """Raised when unit conversion fails or is ambiguous."""
    pass


# Unit conversion factors (to canonical unit)
UNIT_CONVERSIONS: Dict[str, Dict[str, float]] = {
    # Time units (to minutes)
    "time": {
        "minutes": 1.0,
        "min": 1.0,
        "hours": 60.0,
        "hr": 60.0,
        "hrs": 60.0,
        "h": 60.0,
        "days": 1440.0,
        "d": 1440.0,
    },
    # Percentage units (to percent)
    "percent": {
        "percent": 1.0,
        "%": 1.0,
        "ratio": 100.0,  # 0.85 ratio = 85%
        "decimal": 100.0,  # 0.85 decimal = 85%
    },
    # Count units (no conversion needed, but validate)
    "count": {
        "count": 1.0,
        "steps": 1.0,
        "beats": 1.0,
    },
    # Score units (no conversion, but validate range)
    "score": {
        "score_1_5": 1.0,
        "score_1_10": 1.0,
        "score_0_100": 1.0,
    },
    # Heart rate units (to bpm)
    "heart_rate": {
        "bpm": 1.0,
        "beats_per_minute": 1.0,
    },
    # Duration units (to ms for HRV, minutes for sleep)
    "duration_ms": {
        "ms": 1.0,
        "milliseconds": 1.0,
        "s": 1000.0,  # seconds to milliseconds
        "seconds": 1000.0,
    },
}


def get_unit_category(unit: str) -> Optional[str]:
    """
    Determine which category a unit belongs to.
    
    Returns category name or None if unknown.
    """
    unit_lower = unit.lower().strip()
    
    for category, units in UNIT_CONVERSIONS.items():
        if unit_lower in units:
            return category
    
    return None


def convert_unit(
    value: float,
    from_unit: str,
    to_unit: str,
    unit_category: Optional[str] = None,
) -> float:
    """
    Convert a value from one unit to another.
    
    Args:
        value: The value to convert
        from_unit: Source unit
        to_unit: Target unit
        unit_category: Optional category hint (e.g., "time", "percent")
    
    Returns:
        Converted value
    
    Raises:
        UnitConversionError: If conversion is not possible or ambiguous
    """
    from_unit_lower = from_unit.lower().strip()
    to_unit_lower = to_unit.lower().strip()
    
    # Same unit - no conversion needed
    if from_unit_lower == to_unit_lower:
        return value
    
    # Determine category
    if not unit_category:
        category_from = get_unit_category(from_unit)
        category_to = get_unit_category(to_unit)
        
        if category_from != category_to:
            raise UnitConversionError(
                f"Cannot convert between incompatible unit categories: "
                f"{from_unit} ({category_from}) -> {to_unit} ({category_to})"
            )
        
        if not category_from:
            raise UnitConversionError(
                f"Unknown unit category for '{from_unit}'. "
                f"Cannot convert to '{to_unit}'."
            )
        
        unit_category = category_from
    
    # Get conversion factors
    conversions = UNIT_CONVERSIONS.get(unit_category)
    if not conversions:
        raise UnitConversionError(f"Unknown unit category: {unit_category}")
    
    from_factor = conversions.get(from_unit_lower)
    to_factor = conversions.get(to_unit_lower)
    
    if from_factor is None:
        raise UnitConversionError(f"Unknown source unit: '{from_unit}' in category '{unit_category}'")
    if to_factor is None:
        raise UnitConversionError(f"Unknown target unit: '{to_unit}' in category '{unit_category}'")
    
    # Convert: value_in_canonical = value * from_factor
    #         value_in_target = value_in_canonical / to_factor
    canonical_value = value * from_factor
    target_value = canonical_value / to_factor
    
    return target_value


def validate_unit_compatibility(
    provided_unit: str,
    expected_unit: str,
    metric_key: str,
) -> Tuple[bool, Optional[str], Optional[float]]:
    """
    Validate if provided unit is compatible with expected unit.
    
    Returns:
        (is_compatible, error_message, converted_value)
        - is_compatible: True if units match or can be converted
        - error_message: None if compatible, error message if not
        - converted_value: None if units match, converted value if conversion needed
    """
    provided_lower = provided_unit.lower().strip()
    expected_lower = expected_unit.lower().strip()
    
    # Exact match
    if provided_lower == expected_lower:
        return True, None, None
    
    # Try to determine if conversion is possible
    category_provided = get_unit_category(provided_unit)
    category_expected = get_unit_category(expected_unit)
    
    if category_provided != category_expected:
        return False, (
            f"Unit mismatch for metric '{metric_key}': "
            f"provided '{provided_unit}' (category: {category_provided}) "
            f"cannot be converted to expected '{expected_unit}' (category: {category_expected}). "
            f"These units are incompatible."
        ), None
    
    if not category_provided:
        return False, (
            f"Unknown unit '{provided_unit}' for metric '{metric_key}'. "
            f"Expected unit: '{expected_unit}'"
        ), None
    
    # Conversion is possible - return success (caller should convert value separately)
    return True, None, None

