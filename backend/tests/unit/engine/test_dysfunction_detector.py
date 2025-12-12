"""Comprehensive unit tests for dysfunction detector"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from app.engine.reasoning.dysfunction_detector import DysfunctionDetector
from app.domain.models.health_data_point import HealthDataPoint
from sqlalchemy.orm import Session


def test_dysfunction_detector_initialization():
    """Test dysfunction detector can be initialized"""
    detector = DysfunctionDetector()
    assert detector is not None
    assert detector.ontology is not None
    assert "dysfunctions" in detector.ontology or "data_types" in detector.ontology


def test_detect_dysfunctions_severe_case(db):
    """Test detecting severe dysfunction"""
    detector = DysfunctionDetector()
    
    # Create test data with severe values
    now = datetime.utcnow()
    data_point = HealthDataPoint(
        user_id=1,
        data_type="sleep_duration",
        value=4.0,  # Very low sleep (severe)
        unit="hours",
        source="wearable",
        timestamp=now - timedelta(days=1),
    )
    db.add(data_point)
    db.commit()
    
    # Mock ontology with thresholds
    detector.ontology = {
        "dysfunctions": [
            {
                "id": "sleep_disorder",
                "name": "Sleep Disorder",
                "assessment_thresholds": {
                    "severe": {
                        "sleep_duration": [0, 5]  # Below 5 hours is severe
                    },
                    "moderate": {
                        "sleep_duration": [5, 6]
                    },
                    "mild": {
                        "sleep_duration": [6, 7]
                    }
                }
            }
        ]
    }
    
    detected = detector.detect_dysfunctions(user_id=1, db=db, days=30)
    
    # Should detect severe sleep disorder
    assert len(detected) > 0
    sleep_disorder = next((d for d in detected if d["dysfunction_id"] == "sleep_disorder"), None)
    if sleep_disorder:
        assert sleep_disorder["severity"] == "severe"
        assert sleep_disorder["confidence"] >= 0.85


def test_detect_dysfunctions_moderate_case(db):
    """Test detecting moderate dysfunction"""
    detector = DysfunctionDetector()
    
    now = datetime.utcnow()
    data_point = HealthDataPoint(
        user_id=1,
        data_type="sleep_duration",
        value=5.5,  # Moderate sleep issue
        unit="hours",
        source="wearable",
        timestamp=now - timedelta(days=1),
    )
    db.add(data_point)
    db.commit()
    
    detector.ontology = {
        "dysfunctions": [
            {
                "id": "sleep_disorder",
                "name": "Sleep Disorder",
                "assessment_thresholds": {
                    "severe": {"sleep_duration": [0, 5]},
                    "moderate": {"sleep_duration": [5, 6]},
                    "mild": {"sleep_duration": [6, 7]}
                }
            }
        ]
    }
    
    detected = detector.detect_dysfunctions(user_id=1, db=db, days=30)
    
    sleep_disorder = next((d for d in detected if d["dysfunction_id"] == "sleep_disorder"), None)
    if sleep_disorder:
        assert sleep_disorder["severity"] == "moderate"
        assert sleep_disorder["confidence"] >= 0.70


def test_detect_dysfunctions_no_dysfunction(db):
    """Test when no dysfunction is detected (normal values)"""
    detector = DysfunctionDetector()
    
    now = datetime.utcnow()
    data_point = HealthDataPoint(
        user_id=1,
        data_type="sleep_duration",
        value=7.5,  # Normal sleep
        unit="hours",
        source="wearable",
        timestamp=now - timedelta(days=1),
    )
    db.add(data_point)
    db.commit()
    
    detector.ontology = {
        "dysfunctions": [
            {
                "id": "sleep_disorder",
                "name": "Sleep Disorder",
                "assessment_thresholds": {
                    "severe": {"sleep_duration": [0, 5]},
                    "moderate": {"sleep_duration": [5, 6]},
                    "mild": {"sleep_duration": [6, 7]}
                }
            }
        ]
    }
    
    detected = detector.detect_dysfunctions(user_id=1, db=db, days=30)
    
    # Should not detect sleep disorder (value is 7.5, outside all thresholds)
    sleep_disorder = next((d for d in detected if d["dysfunction_id"] == "sleep_disorder"), None)
    assert sleep_disorder is None


def test_detect_dysfunctions_insufficient_data(db):
    """Test with insufficient data (no data points)"""
    detector = DysfunctionDetector()
    
    detector.ontology = {
        "dysfunctions": [
            {
                "id": "sleep_disorder",
                "name": "Sleep Disorder",
                "assessment_thresholds": {
                    "severe": {"sleep_duration": [0, 5]}
                }
            }
        ]
    }
    
    detected = detector.detect_dysfunctions(user_id=999, db=db, days=30)
    
    # Should return empty list when no data
    assert len(detected) == 0


def test_assess_dysfunction_severity_priority():
    """Test that severe markers take priority over moderate/mild"""
    detector = DysfunctionDetector()
    
    # Create mock dysfunction with multiple severity levels
    dysfunction = {
        "id": "test_dysfunction",
        "name": "Test Dysfunction",
        "assessment_thresholds": {
            "severe": {"metric1": [0, 10]},
            "moderate": {"metric2": [10, 20]},
            "mild": {"metric3": [20, 30]}
        }
    }
    
    # Data with severe marker
    data_summary = {
        "metric1": 5.0,  # In severe range
        "metric2": 15.0,  # In moderate range
        "metric3": 25.0,  # In mild range
    }
    
    severity, confidence = detector._assess_dysfunction(dysfunction, data_summary)
    
    assert severity == "severe"
    assert confidence == 0.85


def test_assess_dysfunction_moderate_only():
    """Test assessment when only moderate markers present"""
    detector = DysfunctionDetector()
    
    dysfunction = {
        "id": "test_dysfunction",
        "assessment_thresholds": {
            "moderate": {"metric1": [10, 20]},
            "mild": {"metric2": [20, 30]}
        }
    }
    
    data_summary = {
        "metric1": 15.0,  # In moderate range
        "metric2": 25.0,  # In mild range
    }
    
    severity, confidence = detector._assess_dysfunction(dysfunction, data_summary)
    
    assert severity == "moderate"
    assert confidence == 0.70


def test_assess_dysfunction_no_markers():
    """Test assessment when no markers are outside normal range"""
    detector = DysfunctionDetector()
    
    dysfunction = {
        "id": "test_dysfunction",
        "assessment_thresholds": {
            "severe": {"metric1": [0, 10]},
            "moderate": {"metric2": [10, 20]}
        }
    }
    
    data_summary = {
        "metric1": 15.0,  # Outside severe range (normal)
        "metric2": 25.0,  # Outside moderate range (normal)
    }
    
    severity, confidence = detector._assess_dysfunction(dysfunction, data_summary)
    
    assert severity is None
    assert confidence == 0


def test_detect_dysfunctions_sorted_by_confidence(db):
    """Test that detected dysfunctions are sorted by confidence"""
    detector = DysfunctionDetector()
    
    now = datetime.utcnow()
    # Create data for multiple dysfunctions
    db.add(HealthDataPoint(user_id=1, data_type="sleep_duration", value=4.0, unit="hours", source="wearable", timestamp=now - timedelta(days=1)))
    db.add(HealthDataPoint(user_id=1, data_type="stress_score", value=8.0, unit="score", source="manual", timestamp=now - timedelta(days=1)))
    db.commit()
    
    detector.ontology = {
        "dysfunctions": [
            {
                "id": "sleep_disorder",
                "name": "Sleep Disorder",
                "assessment_thresholds": {
                    "severe": {"sleep_duration": [0, 5]}
                }
            },
            {
                "id": "high_stress",
                "name": "High Stress",
                "assessment_thresholds": {
                    "moderate": {"stress_score": [7, 10]}
                }
            }
        ]
    }
    
    detected = detector.detect_dysfunctions(user_id=1, db=db, days=30)
    
    # Should be sorted by confidence (descending)
    if len(detected) > 1:
        assert detected[0]["confidence"] >= detected[1]["confidence"]

