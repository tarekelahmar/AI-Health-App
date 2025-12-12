import json
from datetime import datetime, timedelta
import pytest

from app.domain.repositories.wearable_repository import WearableRepository
from app.engine.reasoning.insight_generator import InsightEngine
from app.dependencies import get_insight_engine


# ---------------------------------------------------------
# FIXTURE OVERRIDE (inject test InsightEngine into app)
# ---------------------------------------------------------

@pytest.fixture(autouse=True)
def override_insight_engine_dependency(app_fixture, db_session):
    """
    Overrides the InsightEngine dependency inside FastAPI so that all API calls
    during this test use the test database session.
    """
    from app.domain.repositories import (
        LabResultRepository,
        WearableRepository,
        HealthDataRepository,
        SymptomRepository,
        InsightRepository,
    )
    from app.config.security import get_current_user
    from app.domain.models.user import User

    # Create a test user with simple hashed password (bcrypt hash of "test")
    # Using a pre-computed hash to avoid bcrypt issues in tests
    test_user = User(
        name="Test User",
        email="test@example.com",
        hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqYqYqYqYq"  # dummy hash
    )
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)

    def _get_test_engine():
        return InsightEngine(
            lab_repo=LabResultRepository(db_session),
            wearable_repo=WearableRepository(db_session),
            health_data_repo=HealthDataRepository(db_session),
            symptom_repo=SymptomRepository(db_session),
            insight_repo=InsightRepository(db_session),
        )

    def _get_test_user():
        return test_user

    app_fixture.dependency_overrides[get_insight_engine] = _get_test_engine
    app_fixture.dependency_overrides[get_current_user] = _get_test_user
    yield
    app_fixture.dependency_overrides.clear()


# ---------------------------------------------------------
# HELPER: Insert synthetic wearable data
# ---------------------------------------------------------

def seed_wearable_sleep_and_hrv(db_session, user_id, days=14):
    now = datetime.utcnow()
    wearable_repo = WearableRepository(db_session)

    for i in range(days):
        ts = now - timedelta(days=i)

        # Sleep duration with slight upward trend
        wearable_repo.create(
            user_id=user_id,
            device_type="fitbit",
            metric_type="sleep_duration",
            value=6.0 + (i * 0.1),
            unit="hours",
            timestamp=ts,
        )

        # HRV with downward trend
        wearable_repo.create(
            user_id=user_id,
            device_type="fitbit",
            metric_type="hrv",
            value=70 - i,
            unit="ms",
            timestamp=ts,
        )

        # Activity minutes increasing
        wearable_repo.create(
            user_id=user_id,
            device_type="fitbit",
            metric_type="activity_minutes",
            value=40 + (i * 5),
            unit="minutes",
            timestamp=ts,
        )

    db_session.commit()


# ---------------------------------------------------------
# MAIN TEST: Sleep insights API
# ---------------------------------------------------------

def test_sleep_insights_api(client, db_session):
    """
    Tests the /api/v1/insights/sleep endpoint using real repos + test DB.

    Ensures:
    - Data is correctly stored
    - InsightEngine processes real SQLAlchemy rows
    - API returns structured JSON with expected fields
    """
    # Get the test user (created in fixture)
    from app.domain.models.user import User
    test_user = db_session.query(User).filter(User.email == "test@example.com").first()
    assert test_user is not None

    # Seed data into test DB
    seed_wearable_sleep_and_hrv(db_session, user_id=test_user.id, days=14)

    # Call API
    response = client.post("/api/v1/insights/sleep?window_days=14")

    assert response.status_code == 200, response.text
    data = response.json()

    # ----------------------------------------------
    # Assert response structure
    # ----------------------------------------------
    assert "metric_summaries" in data
    assert "correlations" in data
    assert data["category"] == "sleep"
    assert data["title"] == "Sleep pattern insights"

    # ----------------------------------------------
    # Assert metric summaries
    # ----------------------------------------------
    ms = data["metric_summaries"]
    assert len(ms) >= 1

    summary_names = {m["metric_name"] for m in ms}
    assert "sleep_duration" in summary_names
    assert "hrv" in summary_names

    sleep_summary = next(m for m in ms if m["metric_name"] == "sleep_duration")

    assert sleep_summary["latest_value"] is not None
    assert sleep_summary["mean_value"] is not None
    assert sleep_summary["trend"] in ["improving", "worsening", "stable", "unknown"]

    # ----------------------------------------------
    # Assert correlations
    # ----------------------------------------------
    corrs = data["correlations"]
    assert len(corrs) >= 1

    corr_keys = {"metric_x", "metric_y", "r", "n", "strength", "direction", "is_reliable"}
    for c in corrs:
        assert corr_keys.issubset(c.keys())

    # HRV should correlate with sleep in some direction
    corr_sleep_hrv = next(
        (c for c in corrs if c["metric_y"] == "hrv"),
        None
    )
    assert corr_sleep_hrv is not None

    # ----------------------------------------------
    # Optional: print for debugging
    # ----------------------------------------------
    print("API insight output:")
    print(json.dumps(data, indent=2))

