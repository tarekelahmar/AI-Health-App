"""Unit tests for domain schemas"""
import pytest
from datetime import datetime

from app.domain.schemas.user import UserCreate, UserResponse
from app.domain.schemas.insight import InsightResponse


def test_user_create_schema():
    """Test UserCreate schema validation"""
    user_data = UserCreate(
        name="Test User",
        email="test@example.com",
        password="password123"
    )
    assert user_data.name == "Test User"
    assert user_data.email == "test@example.com"
    assert user_data.password == "password123"


def test_user_response_schema():
    """Test UserResponse schema"""
    user_response = UserResponse(
        id=1,
        name="Test User",
        email="test@example.com",
        created_at=datetime.utcnow()
    )
    assert user_response.id == 1
    assert user_response.name == "Test User"


def test_insight_response_schema():
    """Test InsightResponse schema"""
    insight = InsightResponse(
        id=1,
        user_id=1,
        insight_type="dysfunction",
        title="Test Insight",
        description="Test description",
        confidence_score=0.85,
        generated_at=datetime.utcnow()
    )
    assert insight.id == 1
    assert insight.confidence_score == 0.85

