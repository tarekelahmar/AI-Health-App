"""Tests for user API endpoints"""
import pytest
from fastapi.testclient import TestClient


def test_create_user(client: TestClient):
    """Test user creation"""
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


def test_get_user(client: TestClient):
    """Test getting a user"""
    # First create a user
    import uuid
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    create_response = client.post("/api/v1/users/", json={
        "name": "Test User",
        "email": unique_email,
        "password": "testpassword123"
    })
    user_id = create_response.json()["id"]
    
    # Then get the user
    response = client.get(f"/api/v1/users/{user_id}")
    assert response.status_code == 200
    assert response.json()["id"] == user_id

