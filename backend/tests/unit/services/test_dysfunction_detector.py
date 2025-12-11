"""Tests for dysfunction detector service"""
import pytest
from app.engine.reasoning.dysfunction_detector import DysfunctionDetector
from app.config.settings import get_settings

settings = get_settings()


def test_dysfunction_detector_initialization():
    """Test dysfunction detector can be initialized"""
    detector = DysfunctionDetector(settings.HEALTH_ONTOLOGY_PATH)
    assert detector is not None
    assert detector.ontology is not None

