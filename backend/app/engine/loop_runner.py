import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.health_domains import domain_for_signal
from app.domain.metric_policies import get_metric_policy
from app.domain.metrics.registry import METRIC_REGISTRY, get_metric_spec
from app.domain.models.baseline import Baseline
from app.domain.repositories.audit_repository import AuditRepository
from app.domain.repositories.daily_checkin_repository import DailyCheckInRepository
from app.domain.repositories.explanation_repository import ExplanationRepository
from app.domain.repositories.insight_repository import InsightRepository
from app.domain.repositories.symptom_repository import SymptomRepository
from app.engine.detectors import detect_change, detect_instability, detect_trend
from app.engine.domain_status import compute_domain_statuses
from app.engine.governance.claim_policy import get_policy, validate_language
from app.engine.governance.insight_suppression import InsightSuppressionService
from app.engine.guardrails import apply_escalation_rules, filter_insights
from app.engine.guardrails.safety_guardrails import run_safety_gate
from app.engine.metric_guardrails import apply_guardrails
from app.engine.insight_factory import (
    make_change_insight_payload,
    make_instability_insight_payload,
    make_trend_insight_payload,
)
from app.engine.signal_builder import fetch_recent_values

logger = logging.getLogger(__name__)

# Local alias so validation tests can still monkeypatch the metric set.
METRICS = METRIC_REGISTRY


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
        # Phase 1.1: pull canonical spec and filter raw values using registry bounds
        try:
            spec = get_metric_spec(metric_key)
        except KeyError:
            # Governance: skip unknown/removed metrics rather than failing the loop.
            continue

        values = fetch_recent_values(
            db=db, user_id=user_id, metric_key=metric_key, window_days=3
        )
        validated_values = [
            v for v in values
            if spec.valid_range[0] <= v <= spec.valid_range[1]
        ]
        if validated_values:
            latest_metrics[metric_key] = float(sum(validated_values) / len(validated_values))

    # Wire symptom tags from check-ins and symptoms into safety gate
    symptom_tags = []
    try:
        # Get recent symptoms (last 7 days)
        symptom_repo = SymptomRepository(db)
        recent_symptoms = symptom_repo.list_recent(user_id=user_id, days=7)
        symptom_tags.extend([s.symptom_name for s in recent_symptoms if s.symptom_name])
        
        # Extract symptom-like keywords from check-in notes (last 3 days)
        checkin_repo = DailyCheckInRepository(db)
        from datetime import date, timedelta
        three_days_ago = date.today() - timedelta(days=3)
        recent_checkins = checkin_repo.list_range(user_id=user_id, start_date=three_days_ago, end_date=date.today())
        
        # Common symptom keywords to extract from notes
        symptom_keywords = [
            "fatigue", "tired", "exhausted", "brain fog", "headache", "pain", "ache",
            "nausea", "dizziness", "anxiety", "depression", "insomnia", "sleep issues",
            "joint pain", "muscle pain", "chest pain", "shortness of breath"
        ]
        for checkin in recent_checkins:
            if checkin.notes:
                notes_lower = checkin.notes.lower()
                for keyword in symptom_keywords:
                    if keyword in notes_lower and keyword not in symptom_tags:
                        symptom_tags.append(keyword)
    except Exception as e:
        logger.warning(f"Failed to extract symptom tags: {e}")

    safety_payload = run_safety_gate(user_id=user_id, latest_metrics=latest_metrics, symptom_tags=symptom_tags)
    if safety_payload:
        # Pure metadata only: attach domain_key deterministically from the primary metric_key (if present).
        # Backward compatible: if safety payload has no metric_key, domain_key remains None.
        try:
            meta_obj = safety_payload.get("metadata_json")
            if isinstance(meta_obj, str) and meta_obj:
                meta_obj = json.loads(meta_obj)
            if not isinstance(meta_obj, dict):
                meta_obj = {}
        except Exception:
            meta_obj = {}
        mk = meta_obj.get("metric_key")
        dk = domain_for_signal(mk) if isinstance(mk, str) else None
        meta_obj["domain_key"] = dk.value if dk else None

        created_insight = repo.create(
            user_id=safety_payload["user_id"],
            insight_type=safety_payload["insight_type"],
            title=safety_payload["title"],
            description=safety_payload["description"],
            confidence_score=safety_payload["confidence_score"],
            metadata_json=json.dumps(meta_obj),
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

    # GOVERNANCE: Daily cap should be enforced against insights that existed *before* this run.
    # If we count "today" after creating new insights, we end up double-counting this run and
    # suppressing too aggressively (even when under the cap). So capture the pre-run count now.
    suppression_service = InsightSuppressionService(db)
    today = datetime.utcnow()
    try:
        existing_today_pre_run = suppression_service._count_today_insights(user_id, today)  # internal helper OK here
    except Exception:
        existing_today_pre_run = 0

    for metric_key in METRICS.keys():
        # Phase 1.1: centralize metric metadata + bounds
        try:
            spec = get_metric_spec(metric_key)
        except KeyError:
            # If a metric was removed from the registry, skip it safely.
            continue
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
        raw_values_for_guard = fetch_recent_values(
            db=db, user_id=user_id, metric_key=metric_key, window_days=change_window_days
        )
        validated_values_for_guard = [
            v for v in raw_values_for_guard
            if spec.valid_range[0] <= v <= spec.valid_range[1]
        ]
        recent_values_for_guard = validated_values_for_guard[-5:]
        guardrail = apply_guardrails(metric_key=metric_key, values=recent_values_for_guard)
        if guardrail:
            dk = domain_for_signal(metric_key)
            insight = repo.create(
                user_id=user_id,
                title=guardrail["title"],
                description=guardrail["summary"],
                insight_type="change",
                confidence_score=guardrail["confidence"],
                metadata_json=json.dumps(
                    {
                        "metric_key": metric_key,
                        # Domain metadata only (no behavior impact)
                        "domain_key": dk.value if dk else None,
                        "status": guardrail["status"],
                    }
                ),
            )
            created.append(insight)
            continue

        # 2) Change detection (7d)
        if "change" in policy.allowed_insights and policy.change:
            raw_change_values = fetch_recent_values(
                db=db, user_id=user_id, metric_key=metric_key, window_days=change_window_days
            )

            change_values = [
                v for v in raw_change_values
                if spec.valid_range[0] <= v <= spec.valid_range[1]
            ]
            
            # WEEK 4: Check for insufficient data
            if len(change_values) < 5:
                dk = domain_for_signal(metric_key)
                # Create "insufficient data" insight instead of silently skipping
                insight = repo.create(
                    user_id=user_id,
                    title=f"Insufficient data for {metric_key}",
                    description=f"Not enough data points ({len(change_values)} < 5) to detect changes in {metric_key}. Please collect more data.",
                    insight_type="insufficient_data",
                    confidence_score=1.0,  # High confidence that data is insufficient
                    metadata_json=json.dumps({
                        "metric_key": metric_key,
                        # Domain metadata only (no behavior impact)
                        "domain_key": dk.value if dk else None,
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
                
                # GOVERNANCE: Apply claim policy enforcement
                # Map confidence to claim level (1-5 scale)
                try:
                    claim_level = min(5, max(1, int(confidence * 5) + 1))
                    is_valid, violations = validate_language(claim_level, f"{title} {summary}")
                except Exception as e:
                    # FAIL-CLOSED: if governance validation fails, drop the output rather than surfacing it.
                    logger.error(
                        "claim_policy_validation_failed_drop_output",
                        extra={
                            "user_id": user_id,
                            "metric_key": metric_key,
                            "insight_type": "change",
                            "error_type": type(e).__name__,
                            "error": str(e),
                        },
                        exc_info=True,
                    )
                    continue
                if not is_valid:
                    # Downgrade or drop insight that violates claim policy
                    logger.warning(
                        f"Insight violates claim policy (level {claim_level}): {violations}. "
                        f"Title: {title}, Summary: {summary}"
                    )
                    # Downgrade confidence and adjust language
                    claim_level = max(1, claim_level - 1)
                    try:
                        policy_for_level = get_policy(claim_level)
                    except Exception as e:
                        # FAIL-CLOSED: drop rather than surfacing un-governed text
                        logger.error(
                            "claim_policy_lookup_failed_drop_output",
                            extra={
                                "user_id": user_id,
                                "metric_key": metric_key,
                                "insight_type": "change",
                                "claim_level": claim_level,
                                "error_type": type(e).__name__,
                                "error": str(e),
                            },
                            exc_info=True,
                        )
                        continue
                    # Use policy-compliant language
                    example = (
                        policy_for_level.example_language.split(":", 1)[1].strip()
                        if ":" in policy_for_level.example_language
                        else policy_for_level.example_language
                    )
                    title = f"{metric_key}: {example}"
                    summary = f"Recent data shows {policy_for_level.must_use_phrases[0] if policy_for_level.must_use_phrases else 'a change'} in {metric_key}."
                    confidence = min(confidence, claim_level / 5.0)  # Cap confidence to policy level
                
                # Persist evidence in a shape that satisfies invariants:
                # - top-level fields for existing transformers
                # - plus an "evidence" object for invariant checks
                evidence_payload = dict(evidence)
                evidence_payload["metric_key"] = metric_key
                # Domain metadata only (no behavior impact)
                dk = domain_for_signal(metric_key)
                evidence_payload["domain_key"] = dk.value if dk else None
                evidence_payload["claim_level"] = claim_level
                evidence_payload["policy_violations"] = violations if not is_valid else []
                meta = dict(evidence_payload)
                meta["evidence"] = dict(evidence_payload)
                insight = repo.create(
                    user_id=user_id,
                    title=title,
                    description=summary,
                    insight_type="change",
                    confidence_score=confidence,
                    metadata_json=json.dumps(meta),
                )
                created.append(insight)
                
                # WEEK 4: Create audit event for explainability
                try:
                    dk = domain_for_signal(metric_key)
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
                        metadata={
                            # Domain metadata only (no behavior impact)
                            "domain_key": dk.value if dk else None,
                            "baseline_mean": baseline.mean,
                            "baseline_std": baseline.std,
                        },
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
            raw_trend_values = fetch_recent_values(
                db=db, user_id=user_id, metric_key=metric_key, window_days=trend_window_days
            )

            trend_values = [
                v for v in raw_trend_values
                if spec.valid_range[0] <= v <= spec.valid_range[1]
            ]
            
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
                
                # GOVERNANCE: Apply claim policy enforcement
                try:
                    claim_level = min(5, max(1, int(confidence * 5) + 1))
                    is_valid, violations = validate_language(claim_level, f"{title} {summary}")
                except Exception as e:
                    # FAIL-CLOSED: if governance validation fails, drop the output rather than surfacing it.
                    logger.error(
                        "claim_policy_validation_failed_drop_output",
                        extra={
                            "user_id": user_id,
                            "metric_key": metric_key,
                            "insight_type": "trend",
                            "error_type": type(e).__name__,
                            "error": str(e),
                        },
                        exc_info=True,
                    )
                    continue
                if not is_valid:
                    logger.warning(f"Trend insight violates claim policy (level {claim_level}): {violations}")
                    claim_level = max(1, claim_level - 1)
                    try:
                        policy_for_level = get_policy(claim_level)
                    except Exception as e:
                        # FAIL-CLOSED: drop rather than surfacing un-governed text
                        logger.error(
                            "claim_policy_lookup_failed_drop_output",
                            extra={
                                "user_id": user_id,
                                "metric_key": metric_key,
                                "insight_type": "trend",
                                "claim_level": claim_level,
                                "error_type": type(e).__name__,
                                "error": str(e),
                            },
                            exc_info=True,
                        )
                        continue
                    example = (
                        policy_for_level.example_language.split(":", 1)[1].strip()
                        if ":" in policy_for_level.example_language
                        else policy_for_level.example_language
                    )
                    title = f"{metric_key}: {example}"
                    summary = f"Data {policy_for_level.must_use_phrases[0] if policy_for_level.must_use_phrases else 'shows a trend'} in {metric_key}."
                    confidence = min(confidence, claim_level / 5.0)
                
                evidence_payload = dict(evidence)
                evidence_payload["metric_key"] = metric_key
                dk = domain_for_signal(metric_key)
                evidence_payload["domain_key"] = dk.value if dk else None
                evidence_payload["claim_level"] = claim_level
                evidence_payload["policy_violations"] = violations if not is_valid else []
                meta = dict(evidence_payload)
                meta["evidence"] = dict(evidence_payload)
                insight = repo.create(
                    user_id=user_id,
                    title=title,
                    description=summary,
                    insight_type="trend",
                    confidence_score=confidence,
                    metadata_json=json.dumps(meta),
                )
                created.append(insight)
                
                # WEEK 4: Create audit event
                try:
                    dk = domain_for_signal(metric_key)
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
                        metadata={
                            "domain_key": dk.value if dk else None,
                            "slope": trend.get("slope"),
                        },
                    )
                except Exception as e:
                    logger.warning(f"Failed to create audit event for trend insight {insight.id}: {e}")

        # 4) Instability detection (14d)
        if "instability" in policy.allowed_insights and policy.instability:
            raw_inst_values = fetch_recent_values(
                db=db, user_id=user_id, metric_key=metric_key, window_days=instability_window_days
            )

            inst_values = [
                v for v in raw_inst_values
                if spec.valid_range[0] <= v <= spec.valid_range[1]
            ]
            
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
                
                # GOVERNANCE: Apply claim policy enforcement
                try:
                    claim_level = min(5, max(1, int(confidence * 5) + 1))
                    is_valid, violations = validate_language(claim_level, f"{title} {summary}")
                except Exception as e:
                    # FAIL-CLOSED: if governance validation fails, drop the output rather than surfacing it.
                    logger.error(
                        "claim_policy_validation_failed_drop_output",
                        extra={
                            "user_id": user_id,
                            "metric_key": metric_key,
                            "insight_type": "instability",
                            "error_type": type(e).__name__,
                            "error": str(e),
                        },
                        exc_info=True,
                    )
                    continue
                if not is_valid:
                    logger.warning(f"Instability insight violates claim policy (level {claim_level}): {violations}")
                    claim_level = max(1, claim_level - 1)
                    try:
                        policy_for_level = get_policy(claim_level)
                    except Exception as e:
                        # FAIL-CLOSED: drop rather than surfacing un-governed text
                        logger.error(
                            "claim_policy_lookup_failed_drop_output",
                            extra={
                                "user_id": user_id,
                                "metric_key": metric_key,
                                "insight_type": "instability",
                                "claim_level": claim_level,
                                "error_type": type(e).__name__,
                                "error": str(e),
                            },
                            exc_info=True,
                        )
                        continue
                    example = (
                        policy_for_level.example_language.split(":", 1)[1].strip()
                        if ":" in policy_for_level.example_language
                        else policy_for_level.example_language
                    )
                    title = f"{metric_key}: {example}"
                    summary = f"Variability {policy_for_level.must_use_phrases[0] if policy_for_level.must_use_phrases else 'has changed'} in {metric_key}."
                    confidence = min(confidence, claim_level / 5.0)
                
                evidence_payload = dict(evidence)
                evidence_payload["metric_key"] = metric_key
                dk = domain_for_signal(metric_key)
                evidence_payload["domain_key"] = dk.value if dk else None
                evidence_payload["claim_level"] = claim_level
                evidence_payload["policy_violations"] = violations if not is_valid else []
                meta = dict(evidence_payload)
                meta["evidence"] = dict(evidence_payload)
                insight = repo.create(
                    user_id=user_id,
                    title=title,
                    description=summary,
                    insight_type="instability",
                    confidence_score=confidence,
                    metadata_json=json.dumps(meta),
                )
                created.append(insight)
                
                # WEEK 4: Create audit event
                try:
                    dk = domain_for_signal(metric_key)
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
                        metadata={
                            "domain_key": dk.value if dk else None,
                            "baseline_std": baseline.std,
                        },
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
    
    # GOVERNANCE: Apply insight suppression before surfacing to users
    suppressed_count = 0
    
    # Update status for weak signals, apply duplicate suppression, then enforce daily cap by confidence.
    candidates: list = []

    for item in escalated:
        if "insight" not in item:
            # FAIL-CLOSED: never surface unknown/untyped items.
            logger.error(
                "unexpected_escalation_item_drop_output",
                extra={
                    "user_id": user_id,
                    "keys": list(item.keys()) if isinstance(item, dict) else None,
                    "type": type(item).__name__,
                },
            )
            suppressed_count += 1
            continue

        ins = item["insight"]

        # Persist weak signal status (metadata) but never crash governance if parsing fails
        if item.get("status") == "weak_signal":
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

        # Duplicate suppression (fail-closed on errors)
        try:
            should_suppress, reason = suppression_service.should_suppress_insight(user_id, ins, today=today)
        except Exception as e:
            logger.error(
                "suppression_check_failed_drop_output",
                extra={
                    "user_id": user_id,
                    "insight_id": getattr(ins, "id", None),
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
                exc_info=True,
            )
            suppressed_count += 1
            continue

        if should_suppress:
            logger.info(f"Suppressing insight {ins.id}: {reason}")
            try:
                suppression_service.mark_suppressed(
                    user_id=user_id,
                    source_type="insight",
                    source_id=ins.id,
                    reason=reason or "suppressed",
                )
            except Exception:
                # Best-effort; suppression recording failure should still not surface the item.
                pass
            suppressed_count += 1
            continue

        candidates.append(ins)

    # Enforce daily cap: allow only the highest-confidence N (low confidence suppressed first).
    remaining_slots = max(0, suppression_service.MAX_DAILY_INSIGHTS - existing_today_pre_run)

    candidates.sort(key=lambda x: float(getattr(x, "confidence_score", 0.0) or 0.0), reverse=True)

    final_insights = candidates[:remaining_slots]
    to_suppress = candidates[remaining_slots:]
    for ins in to_suppress:
        suppressed_count += 1
        try:
            suppression_service.mark_suppressed(
                user_id=user_id,
                source_type="insight",
                source_id=ins.id,
                reason=f"Daily cap reached ({suppression_service.MAX_DAILY_INSIGHTS}), suppressing lower-confidence",
            )
        except Exception:
            pass
    
    logger.info(f"Loop complete: {len(final_insights)} insights surfaced, {suppressed_count} suppressed")

    # Domain-level status (metadata only): classify "intentional silence" per domain.
    # IMPORTANT: This is NOT used for decisions, suppression, or ranking.
    computed_at = datetime.utcnow().isoformat()
    domain_statuses = compute_domain_statuses(db, user_id=user_id, surfaced_insights=final_insights)
    domain_statuses_payload = {k.value: v.value for k, v in domain_statuses.items()}

    # AUDITABILITY: record computed statuses for provenance (non-user-facing).
    try:
        audit_repo.create(
            user_id=user_id,
            entity_type="domain_status",
            entity_id=user_id,  # stable per-user entity id (allows history via created_at)
            decision_type="computed",
            decision_reason="Computed domain status (silence classification)",
            source_metrics=[],
            time_windows=None,
            detectors_used=["domain_status"],
            thresholds_crossed=[],
            safety_checks_applied=[],
            metadata={
                "computed_at": computed_at,
                "domain_statuses": domain_statuses_payload,
            },
        )
    except Exception:
        # Best-effort only; domain status must never break the loop.
        pass
    
    return {
        "created": len(final_insights),
        "suppressed": suppressed_count,
        "items": final_insights,
        # Internal metadata only (safe to return; consumers may ignore)
        "domain_statuses": domain_statuses_payload,
        "domain_status_computed_at": computed_at,
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
