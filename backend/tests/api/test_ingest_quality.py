from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.domain.models.health_data_point import HealthDataPoint


def test_ingest_quality_tags_points(client, db: Session, test_user):
    """
    Integration test: manual health-data ingestion should tag rows
    with basic quality metadata, without changing the public API contract.
    """
    user_id = test_user["id"]

    # Ingest a single valid sleep_duration point
    ts = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    payload = {
        "user_id": user_id,
        "points": [
            {
                "metric_key": "sleep_duration",
                "value": 440,
                "timestamp": ts,
                "source": "wearable",
            }
        ],
    }

    resp = client.post(f"/api/v1/health-data/batch?user_id={user_id}", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["inserted"] == 1
    assert body["rejected"] == 0

    # Fetch stored row and assert quality fields populated.
    hp = db.query(HealthDataPoint).first()
    assert hp is not None
    assert hp.quality_score is not None
    # Manual ingestions should mark validity according to registry range.
    assert hp.validity is True


