from datetime import datetime, timedelta

from app.services.data_quality import DataQualityService


def test_valid_score():
    dq = DataQualityService()
    ts = datetime.utcnow() - timedelta(hours=1)
    qa = dq.assess_single_value("sleep_duration", ts, 420.0, datetime.utcnow())
    assert qa.validity is True
    assert 0.8 <= qa.score <= 1.0


def test_invalid_score():
    dq = DataQualityService()
    ts = datetime.utcnow() - timedelta(hours=1)
    qa = dq.assess_single_value("sleep_duration", ts, -5.0, datetime.utcnow())
    assert qa.validity is False
    assert qa.score < 0.6


