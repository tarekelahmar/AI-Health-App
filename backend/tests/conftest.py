"""
Test Configuration and Fixtures

This conftest sets up the testing environment properly:
1. Sets required environment variables BEFORE any imports
2. Uses SQLite in-memory database for fast tests
3. Mocks external services (OpenAI, etc.)
4. Provides fixtures for common test needs
"""

import pytest
import os
import sys
from unittest.mock import MagicMock, patch

# ============================================================
# CRITICAL: Set environment variables BEFORE any app imports
# ============================================================
os.environ.setdefault("ENV_MODE", "dev")
os.environ.setdefault("AUTH_MODE", "public")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-32chars!")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-real")  # Prevent validation failures
os.environ.setdefault("ENABLE_LLM_TRANSLATION", "false")  # Disable LLM in tests
os.environ.setdefault("ENABLE_SCHEDULER", "false")  # Disable scheduler in tests

# ============================================================
# Mock the RAG module before it gets imported
# This prevents OpenAI validation errors during import
# ============================================================

# Create a mock module for the RAG retriever
mock_rag_module = MagicMock()
mock_rag_module.HealthRAGEngine = MagicMock()
sys.modules['app.engine.rag.retriever'] = mock_rag_module

# Also mock langchain to prevent import errors if not installed
mock_langchain = MagicMock()
sys.modules['langchain'] = mock_langchain
sys.modules['langchain.text_splitter'] = mock_langchain
sys.modules['langchain.vectorstores'] = mock_langchain
sys.modules['langchain.embeddings'] = mock_langchain
sys.modules['langchain.embeddings.openai'] = mock_langchain
sys.modules['langchain.chat_models'] = mock_langchain
sys.modules['langchain.prompts'] = mock_langchain
sys.modules['langchain.schema'] = mock_langchain
sys.modules['langchain.schema.runnable'] = mock_langchain
sys.modules['langchain.schema.output_parser'] = mock_langchain

# Mock chromadb
mock_chroma = MagicMock()
sys.modules['chromadb'] = mock_chroma

# ============================================================
# Now we can safely import app modules
# ============================================================

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db

# Import app AFTER mocks are in place
from app.main import app

# ============================================================
# Database Setup - Use in-memory SQLite for speed
# ============================================================

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Required for in-memory SQLite with multiple connections
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override the database dependency for tests"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the app's database dependency
app.dependency_overrides[get_db] = override_get_db


# ============================================================
# Pytest Fixtures
# ============================================================

@pytest.fixture(scope="function")
def db():
    """
    Database fixture that creates all tables before each test
    and drops them after.
    """
    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create a session
    session = TestingSessionLocal()

    yield session

    # Cleanup
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db):
    """Alias for db fixture for backward compatibility"""
    yield db


@pytest.fixture(scope="function")
def client(db):
    """
    Test client fixture.

    Creates a fresh database for each test and provides
    a TestClient instance for making HTTP requests.
    """
    from fastapi.testclient import TestClient

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def app_fixture():
    """FastAPI app fixture"""
    return app


@pytest.fixture
def test_user(client, db):
    """
    Fixture that creates a test user and returns user data.
    """
    from datetime import datetime

    response = client.post(
        "/api/v1/users/",
        json={
            "name": "Test User",
            "email": f"test_{datetime.now().timestamp()}@example.com",
            "password": "TestPassword123!"
        }
    )

    if response.status_code == 201:
        return response.json()
    else:
        pytest.fail(f"Failed to create test user: {response.json()}")


@pytest.fixture
def test_user_with_consent(test_user, client):
    """
    Fixture that creates a test user with consent granted.
    """
    user_id = test_user["id"]

    response = client.post(
        f"/api/v1/consent?user_id={user_id}",
        json={
            "consent_version": "1.0",
            "understands_not_medical_advice": True,
            "consents_to_data_analysis": True,
            "understands_recommendations_experimental": True,
            "understands_can_stop_anytime": True,
            "consents_to_whoop_ingestion": True,
        }
    )

    if response.status_code != 200:
        pytest.fail(f"Failed to create consent: {response.json()}")

    return test_user


# ============================================================
# Pytest Configuration
# ============================================================

def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")
