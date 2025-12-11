import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
# Legacy test file - functionality moved to integration/api/

@pytest.fixture
def client():
    return TestClient(app)

def test_create_user(client):
    import uuid
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    response = client.post("/api/v1/users/", json={
        "name": "Test User",
        "email": unique_email,
        "password": "testpassword123"
    })
    assert response.status_code == 201
    assert response.json()["name"] == "Test User"
    assert response.json()["email"] == unique_email

def test_add_health_data(client):
    import uuid
    # First create a user
    unique_email = f"test2_{uuid.uuid4().hex[:8]}@example.com"
    user_response = client.post("/api/v1/users/", json={
        "name": "Test User 2",
        "email": unique_email,
        "password": "testpassword123"
    })
    user_id = user_response.json()["id"]
    
    # Then add health data
    response = client.post(
        f"/api/v1/health-data/?user_id={user_id}",
        json={
            "data_type": "sleep_duration",
            "value": 7.5,
            "unit": "hours",
            "source": "wearable"
        }
    )
    assert response.status_code == 200
    assert response.json()["data_type"] == "sleep_duration"

def test_health_check(client):
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

