from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_providers_health_endpoint_ok():
    resp = client.get("/providers/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "providers" in body
    assert isinstance(body["providers"], list)


