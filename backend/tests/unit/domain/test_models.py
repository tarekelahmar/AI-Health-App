"""Unit tests for domain models"""
import pytest
from datetime import datetime

from app.domain.models.user import User
from app.domain.models.insight import Insight
from app.domain.models.protocol import Protocol


def test_user_model():
    """Test User model creation"""
    user = User(
        name="Test User",
        email="test@example.com",
        hashed_password="hashed_password"
    )
    assert user.name == "Test User"
    assert user.email == "test@example.com"
    assert user.hashed_password == "hashed_password"


def test_insight_model():
    """Test Insight model creation"""
    insight = Insight(
        user_id=1,
        insight_type="dysfunction",
        title="Test Insight",
        description="Test description",
        confidence_score=0.85
    )
    assert insight.user_id == 1
    assert insight.insight_type == "dysfunction"
    assert insight.confidence_score == 0.85


def test_protocol_model():
    """Test Protocol model creation"""
    protocol = Protocol(
        user_id=1,
        week_number=1,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow(),
        interventions=[],
        status="active"
    )
    assert protocol.user_id == 1
    assert protocol.week_number == 1
    assert protocol.status == "active"

