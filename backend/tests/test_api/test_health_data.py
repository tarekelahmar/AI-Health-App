"""Tests for health data API endpoints"""
import pytest
from fastapi.testclient import TestClient


def test_add_health_data(client: TestClient):
    """Test adding health data"""
    import uuid
    # First create a user
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    user_response = client.post("/users/", json={
        "name": "Test User",
        "email": unique_email
    })
    user_id = user_response.json()["id"]
    
    # Then add health data
    response = client.post(
        f"/health-data/?user_id={user_id}",
        json={
            "data_type": "sleep_duration",
            "value": 7.5,
            "unit": "hours",
            "source": "wearable"
        }
    )
    assert response.status_code == 200
    assert response.json()["data_type"] == "sleep_duration"

