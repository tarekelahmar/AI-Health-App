import json
import os
import sys
from datetime import datetime, timedelta, date
from types import SimpleNamespace
from typing import Optional

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException, Request, status
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

# Ensure backend/ is on sys.path so `import app...` works regardless of pytest rootdir.
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)


# Allow PostgreSQL JSONB columns to be created in SQLite for testing purposes.
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "JSON"


def _fresh_import_app(*, env_mode: str, auth_mode: str):
    """
    Build a fresh FastAPI app with router-level auth behavior reflecting env vars.
    We avoid backend/tests/conftest.py by keeping these tests in backend/validation_tests/.
    """
    os.environ["ENV_MODE"] = env_mode
    os.environ["AUTH_MODE"] = auth_mode
    os.environ.setdefault("ENABLE_LLM_TRANSLATION", "false")
    os.environ.setdefault("JWT_SECRET", "test-secret")
    os.environ.setdefault("SECRET_KEY", "test-secret")  # app.config.settings uses SECRET_KEY

    # Ensure router factory + auth mode are re-evaluated under this environment.
    for mod in [
        "app.api",
        "app.api.v1",
        "app.config.environment",
        "app.api.auth_mode",
        "app.api.consent_gate",
        "app.api.router_factory",
        "app.api.v1.insights",
        "app.api.v1.narratives",
        "app.api.v1.protocols",
        "app.api.v1.experiments",
        "app.api.v1.loop",
        "app.api.v1.providers_whoop",
        "app.api.v1.system",
        "app.main",
    ]:
        if mod in sys.modules:
            del sys.modules[mod]

    from app.main import app  # noqa: WPS433
    return app


def _make_sqlite_db(tmp_path):
    db_path = tmp_path / "validation.sqlite"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, TestingSessionLocal


@pytest.fixture()
def app_and_db(tmp_path, monkeypatch):
    # Private mode to test 401/403 behavior
    # Use a file-based SQLite DB for isolated, deterministic tests.
    db_path = tmp_path / "validation.sqlite"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["ENV_MODE"] = "dev"
    os.environ["AUTH_MODE"] = "private"
    os.environ.setdefault("ENABLE_LLM_TRANSLATION", "false")
    os.environ.setdefault("JWT_SECRET", "test-secret")
    os.environ.setdefault("SECRET_KEY", "test-secret")

    # Clear cached modules that capture settings/Base at import time.
    for mod in [
        "app.api",
        "app.api.v1",
        "app.config.environment",
        "app.config.settings",
        "app.api.auth_mode",
        "app.api.consent_gate",
        "app.api.router_factory",
        "app.core.database",
        "app.database",
        "app.api.v1.insights",
        "app.api.v1.narratives",
        "app.api.v1.protocols",
        "app.api.v1.experiments",
        "app.api.v1.loop",
        "app.api.v1.providers_whoop",
        "app.api.v1.system",
        "app.main",
    ]:
        if mod in sys.modules:
            del sys.modules[mod]

    # Also clear domain modules so they re-bind to the fresh Base.
    for name in list(sys.modules.keys()):
        if name.startswith("app.domain"):
            del sys.modules[name]

    from app.main import app  # noqa: WPS433

    # Use the app's configured engine/session
    from app.core.database import Base, get_db, engine, SessionLocal  # noqa: WPS433
    import app.api.auth_mode as auth_mode_mod  # noqa: WPS433
    import app.api.router_factory as router_factory_mod  # noqa: WPS433
    import app.api.consent_gate as consent_gate_mod  # noqa: WPS433
    from app.domain import models as domain_models  # noqa: F401,WPS433

    Base.metadata.create_all(bind=engine)

    # Override identity gate for tests:
    # - Missing Authorization -> 401
    # - Any Bearer token -> user_id=1
    def _test_request_user_id(request: Request) -> int:
        auth = request.headers.get("authorization") or ""
        if not auth.lower().startswith("bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return 1

    async def _test_current_user_optional(token: Optional[str] = None):
        # Mirrors behavior in private mode: missing token -> 401, otherwise accept any token.
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return SimpleNamespace(id=1)

    # Override any references of get_request_user_id that might have been imported
    # and captured at import time (router_factory adds it as a router-level dependency).
    app.dependency_overrides[auth_mode_mod.get_request_user_id] = _test_request_user_id
    app.dependency_overrides[router_factory_mod.get_request_user_id] = _test_request_user_id
    app.dependency_overrides[consent_gate_mod.get_request_user_id] = _test_request_user_id
    # Also override get_current_user_optional in case a captured get_request_user_id instance
    # is still used somewhere; this keeps private-mode auth deterministic.
    app.dependency_overrides[auth_mode_mod.get_current_user_optional] = _test_current_user_optional

    # Sanity check: ensure the /insights router-level auth dependency is actually overridden.
    from fastapi.routing import APIRoute  # noqa: WPS433
    for r in app.routes:
        if isinstance(r, APIRoute) and r.path == "/api/v1/insights/feed":
            for d in r.dependant.dependencies:
                call = d.call
                if getattr(call, "__name__", None) == "get_request_user_id":
                    assert call in app.dependency_overrides, "get_request_user_id override not applied to /insights/feed"

    return app, SessionLocal, engine


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _insert_consent(db, **kwargs):
    from app.domain.models.consent import Consent  # noqa: WPS433

    defaults = dict(
        user_id=1,
        consent_version="1.0",
        consent_timestamp=datetime.utcnow(),
        understands_not_medical_advice=True,
        consents_to_data_analysis=True,
        understands_recommendations_experimental=True,
        understands_can_stop_anytime=True,
        consents_to_whoop_ingestion=True,
        consents_to_fitbit_ingestion=False,
        consents_to_oura_ingestion=False,
        revoked_at=None,
        revocation_reason=None,
        onboarding_completed=True,
        onboarding_completed_at=datetime.utcnow(),
    )
    defaults.update(kwargs)
    obj = Consent(**defaults)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def test_1_private_mode_no_jwt_401_insights_feed_and_run(app_and_db):
    app, _, _ = app_and_db
    client = TestClient(app)

    r = client.get("/api/v1/insights/feed")
    assert r.status_code == 401

    r = client.post("/api/v1/insights/run")
    assert r.status_code == 401


def test_2_jwt_present_no_consent_403_with_reason_header(app_and_db):
    app, TestingSessionLocal, _ = app_and_db
    client = TestClient(app)

    r = client.get("/api/v1/insights/feed", headers=_auth_headers())
    assert r.status_code == 403
    assert r.headers.get("X-Consent-Error-Reason") == "no_consent"


def test_3_consent_revoked_403_with_reason_header(app_and_db):
    app, TestingSessionLocal, _ = app_and_db
    client = TestClient(app)

    db = TestingSessionLocal()
    try:
        _insert_consent(db, revoked_at=datetime.utcnow(), revocation_reason="user_requested")
    finally:
        db.close()

    r = client.get("/api/v1/insights/feed", headers=_auth_headers())
    assert r.status_code == 403
    assert r.headers.get("X-Consent-Error-Reason") == "consent_revoked"


def test_4_scope_denied_experiments_protocols_403(app_and_db):
    app, TestingSessionLocal, _ = app_and_db
    client = TestClient(app)

    db = TestingSessionLocal()
    try:
        _insert_consent(db, understands_recommendations_experimental=False)
    finally:
        db.close()

    payload = {"title": "Test Protocol", "description": "x", "interventions": []}
    r = client.post("/api/v1/protocols", json=payload, headers=_auth_headers())
    assert r.status_code == 403
    assert r.headers.get("X-Consent-Error-Reason") == "scope_experiments_denied"


def test_5_provider_scope_denied_whoop_sync_403(app_and_db):
    app, TestingSessionLocal, _ = app_and_db
    client = TestClient(app)

    db = TestingSessionLocal()
    try:
        _insert_consent(db, consents_to_whoop_ingestion=False)
    finally:
        db.close()

    r = client.post("/api/v1/providers/whoop/sync", headers=_auth_headers(), params={"days": 1})
    assert r.status_code == 403
    assert r.headers.get("X-Consent-Error-Reason") == "scope_provider_whoop_denied"


def test_6_claim_policy_enforced_on_generated_insight(app_and_db, monkeypatch):
    """
    Force a low-confidence insight with forbidden wording, assert it is downgraded (not leaked)
    and claim_level/policy_violations are stored.
    """
    _, TestingSessionLocal, _ = app_and_db
    db = TestingSessionLocal()
    try:
        # Consent not needed here; this is engine-level.
        from app.domain.models.baseline import Baseline  # noqa: WPS433

        db.add(Baseline(user_id=1, metric_type="sleep_duration", mean=100.0, std=10.0, window_days=30))
        db.commit()

        import app.engine.loop_runner as lr  # noqa: WPS433

        # Keep loop minimal and deterministic
        monkeypatch.setattr(lr, "METRICS", {"sleep_duration": object()})
        monkeypatch.setattr(lr, "filter_insights", lambda xs: xs)
        monkeypatch.setattr(lr, "apply_escalation_rules", lambda xs: xs)
        monkeypatch.setattr(lr, "apply_guardrails", lambda metric_key, values: None)
        monkeypatch.setattr(lr, "fetch_recent_values", lambda **kwargs: [1, 1, 1, 1, 1, 1, 1])
        monkeypatch.setattr(lr, "run_safety_gate", lambda **kwargs: None)

        DummyPolicy = SimpleNamespace(
            allowed_insights=["change"],
            change=SimpleNamespace(z_threshold=0.5),
            trend=None,
            instability=None,
        )
        monkeypatch.setattr(lr, "get_metric_policy", lambda metric_key: DummyPolicy)

        # Force detection hit and forbidden language
        monkeypatch.setattr(
            lr,
            "detect_change",
            lambda **kwargs: {"metric_key": "sleep_duration", "n_points": 7, "window_days": 7, "z_score": 2.0},
        )
        monkeypatch.setattr(
            lr,
            "make_change_insight_payload",
            lambda change, expected_days: (
                "Sleep causes recovery to improve",  # forbidden at low level
                "We recommend you improve sleep immediately.",  # forbidden
                0.1,  # low confidence => claim level 1
                {"z_score": 2.0, "window_days": 7, "n_points": 7},
            ),
        )

        res = lr.run_loop(db=db, user_id=1)
        assert res["created"] >= 1

        ins = res["items"][0]
        meta = json.loads(ins.metadata_json or "{}")
        assert "claim_level" in meta
        assert "policy_violations" in meta
        # Ensure downgraded title/summary do not contain forbidden verbs
        assert "causes" not in (ins.title or "").lower()
        assert "recommend" not in (ins.description or "").lower()
    finally:
        db.close()


def test_7_narrative_actions_low_claim_level_only_monitor(app_and_db):
    _, TestingSessionLocal, _ = app_and_db
    db = TestingSessionLocal()
    try:
        from app.domain.models.evaluation_result import EvaluationResult  # noqa: WPS433
        from app.domain.models.daily_checkin import DailyCheckIn  # noqa: WPS433
        from app.engine.synthesis.narrative_synthesizer import synthesize_narrative  # noqa: WPS433

        # Minimal evaluation in range with low confidence
        ev = EvaluationResult(
            user_id=1,
            experiment_id=1,
            metric_key="sleep_duration",
            verdict="helpful",
            summary="x",
            baseline_mean=0.0,
            baseline_std=1.0,
            intervention_mean=0.0,
            intervention_std=1.0,
            delta=0.0,
            percent_change=0.0,
            effect_size=0.0,
            coverage=0.8,
            adherence_rate=0.8,
            details_json=None,
        )
        db.add(ev)
        # Ensure check-in coverage is high enough to avoid "Complete daily check-ins" action
        db.add(DailyCheckIn(user_id=1, checkin_date=date.today(), notes="ok"))
        db.commit()

        draft = synthesize_narrative(
            db,
            user_id=1,
            period_type="daily",
            start=date.today(),
            end=date.today(),
            include_llm_translation=False,
        )
        # All actions must be non-prescriptive at low claim level
        for a in draft.actions:
            assert "monitor" in a.get("action", "").lower()
            assert "take" not in (a.get("action", "") + " " + a.get("rationale", "")).lower()
            assert "increase" not in (a.get("action", "") + " " + a.get("rationale", "")).lower()
            assert "try" not in (a.get("action", "") + " " + a.get("rationale", "")).lower()
    finally:
        db.close()


def test_8_llm_suggested_next_step_injection_dropped(monkeypatch):
    """
    Simulate LLM output containing an adversarial suggested_next_step and verify it is dropped.
    """
    import app.llm.client as llm_client  # noqa: WPS433
    import app.domain.claims.claim_policy as cp  # noqa: WPS433

    # Force LLM enabled and provide fake client response
    monkeypatch.setattr(llm_client, "ENABLE_LLM", True)

    class _FakeResp:
        def __init__(self, content: str):
            self.choices = [SimpleNamespace(message=SimpleNamespace(content=content))]

    class _FakeChat:
        def completions(self):
            raise RuntimeError("not used")

    class _FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    return _FakeResp(
                        json.dumps(
                            {
                                "explanation": "Data might suggest a change (uncertain).",
                                "uncertainty": "Limited evidence.",
                                "suggested_next_step": "You should start a new protocol now.",
                            }
                        )
                    )

    monkeypatch.setattr(llm_client, "_client", _FakeClient())
    # Fail claim policy only for the suggested_next_step (keep explanation accepted)
    monkeypatch.setattr(
        cp,
        "validate_claim_language",
        lambda text, grade: ((False, ["violation"]) if "you should" in (text or "").lower() else (True, [])),
    )

    out = llm_client.translate_insight(
        {"title": "t", "summary": "s", "metric_key": "m", "confidence": 0.4, "status": "detected", "evidence": {}},
        evidence_grade=cp.EvidenceGrade.D,
        claim_policy=cp.get_claim_policy(cp.EvidenceGrade.D),
    )
    assert out is not None
    assert out.get("suggested_next_step", "") == ""


def test_9_legacy_policy_violating_text_not_returned_from_feed(app_and_db):
    app, TestingSessionLocal, _ = app_and_db
    client = TestClient(app)

    db = TestingSessionLocal()
    try:
        _insert_consent(db)  # allow /insights/feed
        from app.domain.models.insight import Insight  # noqa: WPS433

        bad = Insight(
            user_id=1,
            insight_type="change",
            title="Sleep causes recovery to improve",
            description="We recommend you take a supplement.",
            confidence_score=0.2,
            generated_at=datetime.utcnow(),
            metadata_json=json.dumps({"metric_key": "sleep_duration", "n_points": 1}),
        )
        db.add(bad)
        db.commit()
    finally:
        db.close()

    r = client.get("/api/v1/insights/feed", headers=_auth_headers())
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 1
    text = (items[0]["title"] + " " + items[0]["summary"]).lower()
    assert "causes" not in text
    assert "recommend" not in text


def test_10_suppression_daily_cap_enforced_low_conf_suppressed_first(app_and_db, monkeypatch):
    _, TestingSessionLocal, _ = app_and_db
    db = TestingSessionLocal()
    try:
        from app.domain.models.baseline import Baseline  # noqa: WPS433
        # Use real metric keys from registry to satisfy invariants
        from app.domain.metric_registry import METRICS as REGISTRY  # noqa: WPS433
        metric_keys = list(REGISTRY.keys())[:15]
        for mk in metric_keys:
            db.add(Baseline(user_id=1, metric_type=mk, mean=100.0, std=10.0, window_days=30))
        db.commit()

        import app.engine.loop_runner as lr  # noqa: WPS433
        monkeypatch.setattr(lr, "METRICS", {mk: object() for mk in metric_keys})
        monkeypatch.setattr(lr, "filter_insights", lambda xs: xs)
        monkeypatch.setattr(lr, "apply_escalation_rules", lambda xs: xs)
        monkeypatch.setattr(lr, "apply_guardrails", lambda metric_key, values: None)
        monkeypatch.setattr(lr, "fetch_recent_values", lambda **kwargs: [1, 1, 1, 1, 1, 1, 1])
        monkeypatch.setattr(lr, "run_safety_gate", lambda **kwargs: None)
        DummyPolicy = SimpleNamespace(
            allowed_insights=["change"],
            change=SimpleNamespace(z_threshold=0.5),
            trend=None,
            instability=None,
        )
        monkeypatch.setattr(lr, "get_metric_policy", lambda metric_key: DummyPolicy)

        # Make 15 insights with varying confidence (and policy-compliant language so confidence isn't capped)
        confs = [0.9] * 5 + [0.5] * 10
        it = iter(confs)
        monkeypatch.setattr(
            lr,
            "detect_change",
            lambda **kwargs: {"metric_key": kwargs.get("metric_key"), "n_points": 7, "window_days": 7, "z_score": 2.0},
        )

        def _payload(change, expected_days):
            c = next(it)
            if c >= 0.8:
                # claim level 5: include required phrase
                title = "Reliable pattern detected"
                summary = "A reliable pattern is present."
            else:
                # claim level 3: include required phrase
                title = "Signal may be present"
                summary = "This may be worth testing."
            return (title, summary, c, {"z_score": 2.0, "window_days": 7, "n_points": 7})

        monkeypatch.setattr(lr, "make_change_insight_payload", _payload)

        res = lr.run_loop(db=db, user_id=1)
        assert res["created"] <= 10
        # Remaining should be the highest confidence first
        surfaced = [float(x.confidence_score or 0.0) for x in res["items"]]
        assert all(c >= 0.5 for c in surfaced)
        assert surfaced.count(0.9) == 5
    finally:
        db.close()


def test_11_duplicate_within_7_days_suppressed_unless_high_conf(app_and_db, monkeypatch):
    _, TestingSessionLocal, _ = app_and_db
    db = TestingSessionLocal()
    try:
        from app.domain.models.insight import Insight  # noqa: WPS433
        from app.domain.models.baseline import Baseline  # noqa: WPS433

        db.add(Baseline(user_id=1, metric_type="sleep_duration", mean=100.0, std=10.0, window_days=30))
        db.add(
            Insight(
                user_id=1,
                insight_type="change",
                title="Old",
                description="Old",
                confidence_score=0.9,
                generated_at=datetime.utcnow() - timedelta(days=2),
                metadata_json=json.dumps({"metric_key": "sleep_duration"}),
            )
        )
        db.commit()

        import app.engine.loop_runner as lr  # noqa: WPS433
        monkeypatch.setattr(lr, "METRICS", {"sleep_duration": object()})
        monkeypatch.setattr(lr, "filter_insights", lambda xs: xs)
        monkeypatch.setattr(lr, "apply_escalation_rules", lambda xs: xs)
        monkeypatch.setattr(lr, "apply_guardrails", lambda metric_key, values: None)
        monkeypatch.setattr(lr, "fetch_recent_values", lambda **kwargs: [1, 1, 1, 1, 1, 1, 1])
        monkeypatch.setattr(lr, "run_safety_gate", lambda **kwargs: None)
        DummyPolicy = SimpleNamespace(
            allowed_insights=["change"],
            change=SimpleNamespace(z_threshold=0.5),
            trend=None,
            instability=None,
        )
        monkeypatch.setattr(lr, "get_metric_policy", lambda metric_key: DummyPolicy)
        monkeypatch.setattr(lr, "detect_change", lambda **kwargs: SimpleNamespace(metric_key="sleep_duration", n_points=7, window_days=7, z_score=2.0))

        # Low confidence repeat => suppressed
        monkeypatch.setattr(
            lr,
            "make_change_insight_payload",
            lambda change, expected_days: ("t", "s", 0.5, {"window_days": 7, "n_points": 7}),
        )
        res = lr.run_loop(db=db, user_id=1)
        assert res["created"] == 0

        # High confidence repeat => allowed
        monkeypatch.setattr(
            lr,
            "make_change_insight_payload",
            lambda change, expected_days: ("t", "s", 0.9, {"window_days": 7, "n_points": 7}),
        )
        res2 = lr.run_loop(db=db, user_id=1)
        assert res2["created"] == 1
    finally:
        db.close()


def test_12_migration_integrity_fresh_db(tmp_path):
    """
    Fresh DB: alembic upgrade head then verify health_data.metric_type exists.
    Uses SQLite here as a lightweight stand-in for drift detection.
    """
    db_path = tmp_path / "migrate.sqlite"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["ENV_MODE"] = "staging"
    os.environ["AUTH_MODE"] = "private"

    # Run migrations against fresh DB
    import subprocess  # noqa: WPS433

    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env = os.environ.copy()
    env["PYTHONPATH"] = backend_root + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    subprocess.check_call(["alembic", "-c", "alembic.ini", "upgrade", "head"], cwd=backend_root, env=env)

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    insp = inspect(engine)
    assert "health_data" in insp.get_table_names()
    cols = [c["name"] for c in insp.get_columns("health_data")]
    assert "metric_type" in cols

