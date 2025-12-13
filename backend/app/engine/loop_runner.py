import json
from sqlalchemy.orm import Session
from datetime import datetime

from app.domain.metric_registry import METRICS
from app.domain.metric_policies import get_metric_policy
from app.domain.models.baseline import Baseline
from app.engine.signal_builder import fetch_recent_values
from app.engine.guardrails import apply_guardrails
from app.engine.detectors import detect_change, detect_trend, detect_instability
from app.engine.insight_factory import (
    make_change_insight_payload,
    make_trend_insight_payload,
    make_instability_insight_payload,
)
from app.domain.repositories.insight_repository import InsightRepository


def run_loop(db: Session, user_id: int) -> dict:
    """
    Runs detection across all registry metrics for a user.
    Creates Insights with status="detected" and structured evidence.
    """
    created = []
    repo = InsightRepository(db)

    # windows (MVP)
    change_window_days = 7
    trend_window_days = 14
    instability_window_days = 14

    for metric_key in METRICS.keys():
        # Get metric policy
        try:
            policy = get_metric_policy(metric_key)
        except ValueError:
            # Skip metrics without policies
            continue

        # Fetch baseline (must exist; if not, skip)
        try:
            baseline = (
                db.query(Baseline)
                .filter(Baseline.user_id == user_id, Baseline.metric_type == metric_key)
                .one_or_none()
            )
            if baseline is None:
                continue
        except Exception:
            # If baselines table doesn't exist, skip this metric
            continue

        # 1) Guardrails check (uses last 5 values from change window)
        recent_values_for_guard = fetch_recent_values(
            db=db, user_id=user_id, metric_key=metric_key, window_days=change_window_days
        )[-5:]
        guardrail = apply_guardrails(metric_key=metric_key, values=recent_values_for_guard)
        if guardrail:
            insight = repo.create(
                user_id=user_id,
                title=guardrail["title"],
                description=guardrail["summary"],
                insight_type="change",
                confidence_score=guardrail["confidence"],
                metadata_json=json.dumps({"metric_key": metric_key, "status": guardrail["status"]}),
            )
            created.append(insight)
            continue

        # 2) Change detection (7d)
        if "change" in policy.allowed_insights and policy.change:
            change_values = fetch_recent_values(
                db=db, user_id=user_id, metric_key=metric_key, window_days=change_window_days
            )
            change = detect_change(
                metric_key=metric_key,
                values=change_values,
                baseline_mean=baseline.mean,
                baseline_std=baseline.std,
                window_days=change_window_days,
                z_threshold=policy.change.z_threshold,
            )
            if change:
                title, summary, confidence, evidence = make_change_insight_payload(change, expected_days=change_window_days)
                evidence["metric_key"] = metric_key
                insight = repo.create(
                    user_id=user_id,
                    title=title,
                    description=summary,
                    insight_type="change",
                    confidence_score=confidence,
                    metadata_json=json.dumps(evidence),
                )
                created.append(insight)

        # 3) Trend detection (14d)
        if "trend" in policy.allowed_insights and policy.trend:
            trend_values = fetch_recent_values(
                db=db, user_id=user_id, metric_key=metric_key, window_days=trend_window_days
            )
            trend = detect_trend(
                metric_key=metric_key,
                values=trend_values,
                window_days=trend_window_days,
                slope_threshold=policy.trend.slope_threshold,
            )
            if trend:
                title, summary, confidence, evidence = make_trend_insight_payload(trend, expected_days=trend_window_days)
                evidence["metric_key"] = metric_key
                insight = repo.create(
                    user_id=user_id,
                    title=title,
                    description=summary,
                    insight_type="change",
                    confidence_score=confidence,
                    metadata_json=json.dumps(evidence),
                )
                created.append(insight)

        # 4) Instability detection (14d)
        if "instability" in policy.allowed_insights and policy.instability:
            inst_values = fetch_recent_values(
                db=db, user_id=user_id, metric_key=metric_key, window_days=instability_window_days
            )
            instability = detect_instability(
                metric_key=metric_key,
                values=inst_values,
                baseline_std=baseline.std,
                window_days=instability_window_days,
                ratio_threshold=policy.instability.ratio_threshold,
            )
            if instability:
                title, summary, confidence, evidence = make_instability_insight_payload(instability, expected_days=instability_window_days)
                evidence["metric_key"] = metric_key
                insight = repo.create(
                    user_id=user_id,
                    title=title,
                    description=summary,
                    insight_type="change",
                    confidence_score=confidence,
                    metadata_json=json.dumps(evidence),
                )
                created.append(insight)

    return {
        "created": len(created),
        "items": created,
    }


# Legacy function for backward compatibility
def run_loop_for_user(
    *,
    db: Session,
    user_id: int,
) -> list:
    """
    Legacy wrapper - calls new run_loop and returns items list.
    """
    result = run_loop(db, user_id)
    return result["items"]
