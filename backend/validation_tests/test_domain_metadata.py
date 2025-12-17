import json
import os
import sys
from datetime import datetime, date
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles


# Allow PostgreSQL JSONB columns to be created in SQLite for testing purposes.
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "JSON"

# Ensure backend/ is on sys.path so `import app...` works regardless of pytest rootdir.
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)


def test_1_domain_mapping_sleep_signal():
    from app.domain.health_domains import domain_for_signal, HealthDomainKey

    assert domain_for_signal("sleep_duration") == HealthDomainKey.SLEEP


def test_2_insight_created_with_sleep_metric_has_domain_key(monkeypatch, tmp_path):
    """
    Lightweight sanity check:
    - create a minimal loop run for a sleep signal
    - verify the created Insight metadata contains domain_key == sleep
    """
    db_path = tmp_path / "domain_meta.sqlite"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["ENV_MODE"] = "dev"
    os.environ["AUTH_MODE"] = "private"

    # Reload modules that capture settings/engine at import time.
    for mod in [
        "app.config.environment",
        "app.config.settings",
        "app.api",
        "app.api.v1",
        "app.core.database",
        "app.domain.models",
        "app.engine.loop_runner",
    ]:
        sys.modules.pop(mod, None)
    for name in list(sys.modules.keys()):
        if name.startswith("app.domain"):
            sys.modules.pop(name, None)

    from app.core.database import Base, engine, SessionLocal  # noqa: WPS433
    # Import required models BEFORE create_all so tables are registered with Base.metadata.
    from app.domain.models.baseline import Baseline  # noqa: WPS433
    from app.domain.models.insight import Insight  # noqa: F401,WPS433
    import app.domain.models as _dm  # noqa: F401,WPS433 (register remaining models)

    Base.metadata.create_all(bind=engine)

    # Seed required baseline for sleep_duration (loop runner requires baseline per metric).
    db = SessionLocal()
    db.add(Baseline(user_id=1, metric_type="sleep_duration", mean=100.0, std=10.0, window_days=30))
    db.commit()

    import app.engine.loop_runner as lr  # noqa: WPS433

    # Minimal deterministic loop config
    monkeypatch.setattr(lr, "METRICS", {"sleep_duration": object()})
    monkeypatch.setattr(lr, "filter_insights", lambda xs: xs)
    monkeypatch.setattr(lr, "apply_escalation_rules", lambda xs: xs)
    monkeypatch.setattr(lr, "apply_guardrails", lambda metric_key, values: None)
    monkeypatch.setattr(lr, "run_safety_gate", lambda **kwargs: None)
    monkeypatch.setattr(lr, "fetch_recent_values", lambda **kwargs: [1, 1, 1, 1, 1, 1, 1])
    monkeypatch.setattr(
        lr,
        "detect_change",
        lambda **kwargs: {"metric_key": "sleep_duration", "n_points": 7, "window_days": 7, "z_score": 2.0},
    )
    monkeypatch.setattr(
        lr,
        "get_metric_policy",
        lambda metric_key: SimpleNamespace(
            allowed_insights=["change"],
            change=SimpleNamespace(z_threshold=0.5),
            trend=None,
            instability=None,
        ),
    )
    monkeypatch.setattr(
        lr,
        "make_change_insight_payload",
        lambda change, expected_days: ("Sleep signal", "Sleep may have changed.", 0.6, {"n_points": 7}),
    )

    res = lr.run_loop(db=db, user_id=1)
    assert res["created"] >= 1
    ins = res["items"][0]
    meta = json.loads(ins.metadata_json or "{}")
    assert meta.get("domain_key") == "sleep"
    db.close()


def test_3_legacy_insight_without_domain_key_is_handled_gracefully():
    """
    Legacy data check: transformer should not crash if domain_key is missing.
    """
    from app.api.transformers.insight_transformer import transform_insight

    class _LegacyInsight:
        id = 1
        generated_at = datetime.utcnow()
        insight_type = "change"
        title = "Legacy"
        description = "Legacy"
        confidence_score = 0.5
        metadata_json = json.dumps({"metric_key": "sleep_duration"})  # no domain_key

    out = transform_insight(_LegacyInsight())
    assert out.domain_key is not None
    assert out.domain_key.value == "sleep"


