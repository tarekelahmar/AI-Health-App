import os
import sys
from datetime import datetime

import pytest
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# Ensure backend/ is on sys.path so `import app...` works regardless of pytest rootdir.
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)


# Allow PostgreSQL JSONB columns to be created in SQLite for testing purposes.
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "JSON"


def _make_db(tmp_path):
    db_path = tmp_path / "domain_status.sqlite"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    from app.core.database import Base  # noqa: WPS433

    # Import models before create_all so tables are registered.
    from app.domain.models.baseline import Baseline  # noqa: F401,WPS433
    from app.domain.models.health_data_point import HealthDataPoint  # noqa: F401,WPS433
    from app.domain.models.insight import Insight  # noqa: F401,WPS433
    from app.domain.models.decision_signal import DecisionSignal  # noqa: F401,WPS433

    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal


def test_1_no_sleep_data__status_no_data(tmp_path):
    from app.engine.domain_status import compute_domain_status, DomainStatus
    from app.domain.health_domains import HealthDomainKey

    TestingSessionLocal = _make_db(tmp_path)
    db = TestingSessionLocal()
    try:
        status = compute_domain_status(db, user_id=1, domain_key=HealthDomainKey.SLEEP, surfaced_insights=[])
        assert status == DomainStatus.NO_DATA
    finally:
        db.close()


def test_2_sleep_data_no_baseline__baseline_building(tmp_path):
    from app.engine.domain_status import compute_domain_status, DomainStatus
    from app.domain.health_domains import HealthDomainKey
    from app.domain.models.health_data_point import HealthDataPoint

    TestingSessionLocal = _make_db(tmp_path)
    db = TestingSessionLocal()
    try:
        db.add(
            HealthDataPoint(
                user_id=1,
                metric_type="sleep_duration",
                value=420.0,
                unit="min",
                source="manual",
                timestamp=datetime.utcnow(),
            )
        )
        db.commit()

        status = compute_domain_status(db, user_id=1, domain_key=HealthDomainKey.SLEEP, surfaced_insights=[])
        assert status == DomainStatus.BASELINE_BUILDING
    finally:
        db.close()


def test_3_sleep_baseline_no_insights__no_signal_detected(tmp_path):
    from app.engine.domain_status import compute_domain_status, DomainStatus
    from app.domain.health_domains import HealthDomainKey
    from app.domain.models.health_data_point import HealthDataPoint
    from app.domain.models.baseline import Baseline

    TestingSessionLocal = _make_db(tmp_path)
    db = TestingSessionLocal()
    try:
        db.add(
            HealthDataPoint(
                user_id=1,
                metric_type="sleep_duration",
                value=420.0,
                unit="min",
                source="manual",
                timestamp=datetime.utcnow(),
            )
        )
        db.add(Baseline(user_id=1, metric_type="sleep_duration", mean=400.0, std=30.0, window_days=30))
        db.commit()

        status = compute_domain_status(db, user_id=1, domain_key=HealthDomainKey.SLEEP, surfaced_insights=[])
        assert status == DomainStatus.NO_SIGNAL_DETECTED
    finally:
        db.close()


def test_4_sleep_baseline_with_surfaced_insight__signal_detected(tmp_path):
    from app.engine.domain_status import compute_domain_status, DomainStatus
    from app.domain.health_domains import HealthDomainKey
    from app.domain.models.health_data_point import HealthDataPoint
    from app.domain.models.baseline import Baseline
    from types import SimpleNamespace
    import json

    TestingSessionLocal = _make_db(tmp_path)
    db = TestingSessionLocal()
    try:
        db.add(
            HealthDataPoint(
                user_id=1,
                metric_type="sleep_duration",
                value=420.0,
                unit="min",
                source="manual",
                timestamp=datetime.utcnow(),
            )
        )
        db.add(Baseline(user_id=1, metric_type="sleep_duration", mean=400.0, std=30.0, window_days=30))
        db.commit()

        surfaced = [
            SimpleNamespace(metadata_json=json.dumps({"metric_key": "sleep_duration", "domain_key": "sleep"}))
        ]
        status = compute_domain_status(db, user_id=1, domain_key=HealthDomainKey.SLEEP, surfaced_insights=surfaced)
        assert status == DomainStatus.SIGNAL_DETECTED
    finally:
        db.close()


