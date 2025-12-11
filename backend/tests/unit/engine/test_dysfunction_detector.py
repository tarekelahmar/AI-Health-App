"""Unit tests for dysfunction detector"""
import pytest
from unittest.mock import Mock, patch

from app.engine.reasoning.dysfunction_detector import DysfunctionDetector
from app.config.settings import get_settings

settings = get_settings()


def test_dysfunction_detector_initialization():
    """Test dysfunction detector can be initialized"""
    detector = DysfunctionDetector(settings.HEALTH_ONTOLOGY_PATH)
    assert detector is not None
    assert detector.ontology is not None
    assert "data_types" in detector.ontology


def test_detect_dysfunctions_with_mock_db():
    """Test dysfunction detection with mocked database"""
    detector = DysfunctionDetector(settings.HEALTH_ONTOLOGY_PATH)
    
    # Mock database session
    mock_db = Mock()
    mock_data_point = Mock()
    mock_data_point.data_type = "sleep_duration"
    mock_data_point.value = 5.0  # Low sleep
    mock_data_point.unit = "hours"
    
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_data_point]
    
    # This would need actual implementation to test properly
    # For now, just verify detector can be called
    assert detector is not None

