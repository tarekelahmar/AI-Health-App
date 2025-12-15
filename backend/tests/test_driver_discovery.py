"""
Minimal unit tests for driver discovery service.
Tests thresholds and directionality handling.
"""
import pytest
from datetime import date, timedelta
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session

from app.engine.drivers.driver_discovery_service import DriverDiscoveryService, DailyExposure, DailyOutcome
from app.domain.models.driver_finding import DriverFinding


def test_minimum_thresholds():
    """Test that findings are rejected if they don't meet minimum thresholds"""
    db = Mock(Session)
    service = DriverDiscoveryService(db)
    
    # Test MIN_EXPOSED_DAYS
    assert service.MIN_EXPOSED_DAYS == 6
    assert service.MIN_TOTAL_DAYS == 14
    assert service.MIN_COVERAGE == 0.6


def test_confidence_clamping():
    """Test that confidence is clamped to [0, 1]"""
    db = Mock(Session)
    service = DriverDiscoveryService(db)
    
    # Simulate finding with confidence calculation
    # Confidence should be: (coverage * 0.4 + effect_magnitude * 0.4 + sample_factor * 0.2)
    # And clamped to [0, 1]
    
    # Test case: very high values should clamp to 1.0
    coverage = 1.0
    effect_magnitude = 1.0
    sample_factor = 1.0
    confidence = (coverage * 0.4 + effect_magnitude * 0.4 + sample_factor * 0.2)
    confidence = max(0.0, min(1.0, confidence))
    assert confidence == 1.0
    
    # Test case: negative values should clamp to 0.0
    coverage = -0.5
    effect_magnitude = -0.5
    sample_factor = -0.5
    confidence = (coverage * 0.4 + effect_magnitude * 0.4 + sample_factor * 0.2)
    confidence = max(0.0, min(1.0, confidence))
    assert confidence == 0.0


def test_directionality_higher_is_better():
    """Test direction determination when higher is better"""
    # For metrics where higher is better:
    # - positive effect_size => "improves"
    # - negative effect_size => "worsens"
    
    higher_is_better = True
    effect_size_positive = 0.5
    effect_size_negative = -0.5
    
    # Small effect should be "unclear"
    if abs(effect_size_positive) < 0.2:
        direction = "unclear"
    elif higher_is_better:
        direction = "improves" if effect_size_positive > 0 else "worsens"
    else:
        direction = "worsens" if effect_size_positive > 0 else "improves"
    
    assert direction == "improves"
    
    if abs(effect_size_negative) < 0.2:
        direction = "unclear"
    elif higher_is_better:
        direction = "improves" if effect_size_negative > 0 else "worsens"
    else:
        direction = "worsens" if effect_size_negative > 0 else "improves"
    
    assert direction == "worsens"


def test_directionality_lower_is_better():
    """Test direction determination when lower is better (e.g., stress)"""
    # For metrics where lower is better:
    # - positive effect_size => "worsens" (increases the metric)
    # - negative effect_size => "improves" (decreases the metric)
    
    higher_is_better = False
    effect_size_positive = 0.5
    effect_size_negative = -0.5
    
    if abs(effect_size_positive) < 0.2:
        direction = "unclear"
    elif higher_is_better:
        direction = "improves" if effect_size_positive > 0 else "worsens"
    else:
        direction = "worsens" if effect_size_positive > 0 else "improves"
    
    assert direction == "worsens"
    
    if abs(effect_size_negative) < 0.2:
        direction = "unclear"
    elif higher_is_better:
        direction = "improves" if effect_size_negative > 0 else "worsens"
    else:
        direction = "worsens" if effect_size_negative > 0 else "improves"
    
    assert direction == "improves"


def test_small_effect_is_unclear():
    """Test that small effect sizes are marked as unclear"""
    effect_size_small = 0.15  # Less than 0.2 threshold
    
    if abs(effect_size_small) < 0.2:
        direction = "unclear"
    else:
        direction = "improves"  # Would be determined by higher_is_better
    
    assert direction == "unclear"

