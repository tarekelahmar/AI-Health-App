"""Tests for dysfunction detector service"""
import pytest
from app.services.dysfunction_detector import DysfunctionDetector
from app.core.config import HEALTH_ONTOLOGY_PATH


def test_dysfunction_detector_initialization():
    """Test dysfunction detector can be initialized"""
    detector = DysfunctionDetector(HEALTH_ONTOLOGY_PATH)
    assert detector is not None
    assert detector.ontology is not None

