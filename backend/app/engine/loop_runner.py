import json
import logging
from sqlalchemy.orm import Session
from datetime import datetime

from app.domain.metric_registry import METRICS
from app.domain.metric_policies import get_metric_policy
from app.domain.models.baseline import Baseline
from app.engine.signal_builder import fetch_recent_values

logger = logging.getLogger(__name__)
# Import apply_guardrails - need to handle the guardrails.py file vs guardrails/ package conflict
# Import directly from the file using importlib
import importlib.util
import os
backend_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
guardrails_file_path = os.path.join(backend_path, "app", "engine", "guardrails.py")
spec = importlib.util.spec_from_file_location("app.engine.guardrails_file", guardrails_file_path)
guardrails_file = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guardrails_file)
apply_guardrails = guardrails_file.apply_guardrails

from app.engine.guardrails.safety_guardrails import run_safety_gate
from app.engine.guardrails import filter_insights, apply_escalation_rules
from app.engine.detectors import detect_change, detect_trend, detect_instability
from app.engine.insight_factory import (
    make_change_insight_payload,
    make_trend_insight_payload,
    make_instability_insight_payload,
)
from app.domain.repositories.insight_repository import InsightRepository
from app.domain.repositories.audit_repository import AuditRepository
from app.domain.repositories.explanation_repository import ExplanationRepository


def run_loop(db: Session, user_id: int) -> dict:
    """
    Runs detection across all registry metrics for a user.
    Creates Insights with status="detected" and structured evidence.
    
    WEEK 4: Populates audit events and explanation edges for explainability.
    """
    created = []
    repo = InsightRepository(db)
    audit_repo = AuditRepository(db)
    explanation_repo = ExplanationRepository(db)

    # 0) Safety gate - check for red flags BEFORE normal detectors
    latest_metrics = {}
    for metric_key in METRICS.keys():
        values = fetch_recent_values(
            db=db, user_id=user_id, metric_key=metric_key, window_days=3
        )
        if values:
            latest_metrics[metric_key] = float(sum(values) / len(values))

    # (Optional) Pull symptom tags from check-ins/symptom table if you have them
    symptom_tags = []  # MVP: wire later

    safety_payload = run_safety_gate(user_id=user_id, latest_metrics=latest_metrics, symptom_tags=symptom_tags)
    if safety_payload:
        created_insight = repo.create(
            user_id=safety_payload["user_id"],
            insight_type=safety_payload["insight_type"],
            title=safety_payload["title"],
            description=safety_payload["description"],
            confidence_score=safety_payload["confidence_score"],
            metadata_json=safety_payload["metadata_json"],
        )
        return {
            "created": 1,
            "skipped": "safety_override",
            "items": [created_insight],
        }

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

        # SECURITY FIX (Risk #5): Explicit baseline availability check
        try:
            baseline = (
                db.query(Baseline)
                .filter(Baseline.user_id == user_id, Baseline.metric_type == metric_key)
                .one_or_none()
            )
            if baseline is None:
                # Baseline not computed yet - skip this metric for now
                # This is expected for new metrics/users
                continue
        except Exception as e:
            # SECURITY FIX: Log baseline retrieval failure instead of silently skipping
            logger.warning(
                "baseline_retrieval_failed",
                extra={
                    "user_id": user_id,
                    "metric_key": metric_key,
                    "error": str(e),
                },
            )
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
            
            # WEEK 4: Check for insufficient data
            if len(change_values) < 5:
                # Create "insufficient data" insight instead of silently skipping
                insight = repo.create(
                    user_id=user_id,
                    title=f"Insufficient data for {metric_key}",
                    description=f"Not enough data points ({len(change_values)} < 5) to detect changes in {metric_key}. Please collect more data.",
                    insight_type="insufficient_data",
                    confidence_score=1.0,  # High confidence that data is insufficient
                    metadata_json=json.dumps({
                        "metric_key": metric_key,
                        "data_points": len(change_values),
                        "required_points": 5,
                        "status": "insufficient_data",
                    }),
                )
                created.append(insight)
                continue
            
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
                
                # WEEK 4: Create audit event for explainability
                try:
                    audit_repo.create(
                        user_id=user_id,
                        entity_type="insight",
                        entity_id=insight.id,
                        decision_type="created",
                        decision_reason=f"Change detected in {metric_key}",
                        source_metrics=[metric_key],
                        time_windows={metric_key: {"start": change.get("window_start"), "end": change.get("window_end")}},
                        detectors_used=["change_detector"],
                        thresholds_crossed=[{"threshold": "z_score", "value": change.get("z_score"), "threshold_value": policy.change.z_threshold}],
                        safety_checks_applied=[],
                        metadata={"baseline_mean": baseline.mean, "baseline_std": baseline.std},
                    )
                    
                    # Create explanation edge from baseline to insight
                    explanation_repo.create_edge(
                        target_type="insight",
                        target_id=insight.id,
                        source_type="baseline",
                        source_id=None,  # Baseline doesn't have a single ID
                        contribution_weight=1.0,
                        description=f"Change detected relative to baseline (mean={baseline.mean:.2f}, std={baseline.std:.2f})",
                    )
                except Exception as e:
                    logger.warning(f"Failed to create audit event for insight {insight.id}: {e}")

        # 3) Trend detection (14d)
        if "trend" in policy.allowed_insights and policy.trend:
            trend_values = fetch_recent_values(
                db=db, user_id=user_id, metric_key=metric_key, window_days=trend_window_days
            )
            
            # WEEK 4: Check for insufficient data
            if len(trend_values) < 7:
                # Skip trend detection if insufficient data (already handled above for change)
                continue
            
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
                    insight_type="trend",
                    confidence_score=confidence,
                    metadata_json=json.dumps(evidence),
                )
                created.append(insight)
                
                # WEEK 4: Create audit event
                try:
                    audit_repo.create(
                        user_id=user_id,
                        entity_type="insight",
                        entity_id=insight.id,
                        decision_type="created",
                        decision_reason=f"Trend detected in {metric_key}",
                        source_metrics=[metric_key],
                        time_windows={metric_key: {"start": trend.get("window_start"), "end": trend.get("window_end")}},
                        detectors_used=["trend_detector"],
                        thresholds_crossed=[{"threshold": "slope", "value": trend.get("slope"), "threshold_value": policy.trend.slope_threshold}],
                        safety_checks_applied=[],
                        metadata={"slope": trend.get("slope")},
                    )
                except Exception as e:
                    logger.warning(f"Failed to create audit event for trend insight {insight.id}: {e}")

        # 4) Instability detection (14d)
        if "instability" in policy.allowed_insights and policy.instability:
            inst_values = fetch_recent_values(
                db=db, user_id=user_id, metric_key=metric_key, window_days=instability_window_days
            )
            
            # WEEK 4: Check for insufficient data
            if len(inst_values) < 7:
                continue
            
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
                    insight_type="instability",
                    confidence_score=confidence,
                    metadata_json=json.dumps(evidence),
                )
                created.append(insight)
                
                # WEEK 4: Create audit event
                try:
                    audit_repo.create(
                        user_id=user_id,
                        entity_type="insight",
                        entity_id=insight.id,
                        decision_type="created",
                        decision_reason=f"Instability detected in {metric_key}",
                        source_metrics=[metric_key],
                        time_windows={metric_key: {"start": instability.get("window_start"), "end": instability.get("window_end")}},
                        detectors_used=["instability_detector"],
                        thresholds_crossed=[{"threshold": "std_ratio", "value": instability.get("std_ratio"), "threshold_value": policy.instability.ratio_threshold}],
                        safety_checks_applied=[],
                        metadata={"baseline_std": baseline.std},
                    )
                except Exception as e:
                    logger.warning(f"Failed to create audit event for instability insight {insight.id}: {e}")

    # Apply guardrails: filter weak insights and apply escalation rules
    # Convert Insight objects to dicts for filtering
    insights_dicts = []
    for ins in created:
        metadata = {}
        if ins.metadata_json:
            if isinstance(ins.metadata_json, dict):
                metadata = ins.metadata_json
            else:
                try:
                    metadata = json.loads(ins.metadata_json)
                except Exception:
                    metadata = {}
        
        # Extract effect_size from evidence (may be in different places)
        effect_size = metadata.get("effect_size", 0.0)
        if not effect_size:
            effect_size = abs(metadata.get("delta", 0.0)) or abs(metadata.get("z_score", 0.0)) or 0.0
        
        insights_dicts.append({
            "id": ins.id,
            "user_id": ins.user_id,
            "metric_key": metadata.get("metric_key", "unknown"),
            "confidence": float(ins.confidence_score or 0.0),
            "coverage": float(metadata.get("coverage", 0.0)),
            "effect_size": float(effect_size),
            "evidence": metadata,
            "insight": ins,  # Keep reference to original
        })
    
    # Filter and escalate
    filtered = filter_insights(insights_dicts)
    escalated = apply_escalation_rules(filtered)
    
    # Update status for weak signals and return filtered insights
    final_insights = []
    for item in escalated:
        if "insight" in item:
            ins = item["insight"]
            if item.get("status") == "weak_signal":
                # Update the insight's metadata to reflect weak signal status
                metadata = {}
                if ins.metadata_json:
                    if isinstance(ins.metadata_json, dict):
                        metadata = ins.metadata_json
                    else:
                        try:
                            metadata = json.loads(ins.metadata_json)
                        except Exception:
                            metadata = {}
                metadata["status"] = "weak_signal"
                ins.metadata_json = json.dumps(metadata)
                db.commit()
            final_insights.append(ins)
        else:
            # Fallback: create a minimal insight if needed
            final_insights.append(item)
    
    return {
        "created": len(final_insights),
        "items": final_insights,
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
