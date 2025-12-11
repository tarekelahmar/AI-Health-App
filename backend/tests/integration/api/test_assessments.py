import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def test_user(client):
    """Create test user"""
    response = client.post("/api/v1/users/", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "testpassword123"
    })
    return response.json()

@pytest.fixture
def test_health_data(client, test_user):
    """Create test health data"""
    user_id = test_user["id"]
    client.post(f"/api/v1/health-data/?user_id={user_id}", json={
        "data_type": "sleep_duration",
        "value": 5.5,
        "unit": "hours",
        "source": "wearable"
    })
    return user_id

def test_create_assessment(client, test_health_data):
    """Test assessment creation"""
    response = client.post(f"/api/v1/assessments/{test_health_data}")
    assert response.status_code == 200
    assert "dysfunctions" in response.json()

def test_assessment_detects_low_sleep(client, test_health_data):
    """Test that low sleep is detected"""
    response = client.post(f"/api/v1/assessments/{test_health_data}")
    dysfunctions = response.json()["dysfunctions"]
    
    sleep_issues = [d for d in dysfunctions if "sleep" in d["dysfunction_id"]]
    assert len(sleep_issues) > 0
    assert sleep_issues[0]["severity"] in ["mild", "moderate", "severe"]

def test_protocol_generation(client, test_health_data):
    """Test protocol generation from assessment"""
    # Create assessment first
    client.post(f"/api/v1/assessments/{test_health_data}")
    
    # Generate protocol
    response = client.post(f"/api/v1/protocols/{test_health_data}")
    assert response.status_code == 200
    
    protocol = response.json()
    assert "interventions" in protocol
    assert len(protocol["interventions"]) > 0
