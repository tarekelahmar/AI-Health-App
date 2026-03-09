from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.domain.repositories.insight_repository import InsightRepository
from app.domain.repositories.evaluation_repository import EvaluationRepository
from app.domain.repositories.daily_checkin_repository import DailyCheckInRepository
from app.domain.repositories.adherence_repository import AdherenceRepository
from app.domain.repositories.narrative_repository import NarrativeRepository
from app.domain.repositories.personal_driver_repository import PersonalDriverRepository
from app.domain.repositories.audit_repository import AuditRepository
from app.domain.repositories.explanation_repository import ExplanationRepository
from app.engine.governance.claim_policy import validate_language, get_policy, is_action_allowed
from app.domain.health_domains import domain_for_signal
from app.engine.domain_status import compute_domain_statuses

# Optional LLM translation layer (safe): reuse your existing pattern if present
try:
    from app.llm.client import translate_insight  # type: ignore
except Exception:
    translate_insight = None  # noqa: N816


@dataclass
class NarrativeDraft:
    title: str
    summary: str
    key_points: List[Any]
    drivers: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    risks: List[Dict[str, Any]]
    metadata: Dict[str, Any]


def _to_dt(d: date, end: bool = False) -> datetime:
    if end:
        return datetime(d.year, d.month, d.day, 23, 59, 59)
    return datetime(d.year, d.month, d.day, 0, 0, 0)


def _pick_top(items: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
    return items[:k]


def synthesize_narrative(
    db: Session,
    *,
    user_id: int,
    period_type: str,
    start: date,
    end: date,
    include_llm_translation: bool = False,
) -> NarrativeDraft:
    import logging
    logger = logging.getLogger(__name__)

    insight_repo = InsightRepository(db)
    eval_repo = EvaluationRepository(db)
    checkin_repo = DailyCheckInRepository(db)
    adherence_repo = AdherenceRepository(db)

    # Pull core signals (keep this deterministic & explainable)
    # Insights: assume repo can list_by_user; if not, adapt to yours.
    insights = insight_repo.list_by_user(user_id=user_id, limit=200)

    # Filter insights generated within range (created_at / generated_at)
    in_range = []
    for it in insights:
        ts = getattr(it, "generated_at", None) or getattr(it, "created_at", None)
        if ts is None:
            continue
        if _to_dt(start) <= ts <= _to_dt(end, end=True):
            in_range.append(it)

    evaluations = eval_repo.list_by_user(user_id=user_id, limit=50)
    eval_in_range = []
    for ev in evaluations:
        ts = getattr(ev, "created_at", None)
        if ts and _to_dt(start) <= ts <= _to_dt(end, end=True):
            eval_in_range.append(ev)

    # Daily checkins in range
    try:
        checkins = checkin_repo.list_range(user_id=user_id, start_date=start, end_date=end)
    except AttributeError:
        # Fallback: get individual checkins and filter
        all_checkins = checkin_repo.list_by_user(user_id=user_id, limit=100)
        checkins = []
        for c in all_checkins:
            checkin_date = getattr(c, "checkin_date", None)
            if checkin_date and start <= checkin_date <= end:
                checkins.append(c)

    # Adherence events in range (if your repo supports it)
    try:
        adherence = adherence_repo.list_range(user_id=user_id, start_date=start, end_date=end)
    except (AttributeError, Exception):
        # Fallback: get via experiments
        adherence = []

    # Pull personal drivers (STEP T integration)
    personal_driver_repo = PersonalDriverRepository(db)
    personal_drivers = personal_driver_repo.list_for_user(user_id=user_id, limit=50)
    
    # Build drivers from insights evidence + personal drivers
    drivers = []
    risks = []
    
    # Add personal drivers to key points
    window_days = (end - start).days + 1
    for pd in personal_drivers[:10]:  # Top 10 personal drivers
        if pd.confidence >= 0.6:  # Only high-confidence drivers
            # GOVERNANCE: Apply claim policy to driver descriptions
            try:
                claim_level = min(5, max(1, int(pd.confidence * 5) + 1))
                policy = get_policy(claim_level)
            except Exception as e:
                # FAIL-CLOSED: if governance lookups fail, drop this segment.
                logger.error(
                    "narrative_claim_policy_lookup_failed_drop_segment",
                    extra={
                        "user_id": user_id,
                        "segment": "personal_driver",
                        "driver_key": getattr(pd, "driver_key", None),
                        "error_type": type(e).__name__,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                continue
            
            # Use policy-compliant language
            if claim_level >= 3:
                direction_text = "appears to improve" if pd.direction == "positive" else "appears to worsen" if pd.direction == "negative" else "appears to affect"
            elif claim_level == 2:
                direction_text = "is associated with improvement in" if pd.direction == "positive" else "is associated with decline in" if pd.direction == "negative" else "is associated with"
            else:
                direction_text = "shows change in"  # Level 1: observational only
            
            lag_text = f" (with {pd.lag_days} day lag)" if pd.lag_days > 0 else ""
            driver_text = f"{pd.driver_key.replace('_', ' ')} {direction_text} {pd.outcome_metric.replace('_', ' ')}{lag_text}"
            
            # Validate and adjust if needed
            try:
                is_valid, violations = validate_language(claim_level, driver_text)
            except Exception as e:
                # FAIL-CLOSED: drop this segment rather than include unvalidated language.
                logger.error(
                    "narrative_claim_policy_validation_failed_drop_segment",
                    extra={
                        "user_id": user_id,
                        "segment": "personal_driver",
                        "driver_key": getattr(pd, "driver_key", None),
                        "error_type": type(e).__name__,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                continue
            if not is_valid:
                # Downgrade to safer language
                claim_level = max(1, claim_level - 1)
                try:
                    policy = get_policy(claim_level)
                except Exception as e:
                    logger.error(
                        "narrative_claim_policy_lookup_failed_drop_segment",
                        extra={
                            "user_id": user_id,
                            "segment": "personal_driver",
                            "driver_key": getattr(pd, "driver_key", None),
                            "claim_level": claim_level,
                            "error_type": type(e).__name__,
                            "error": str(e),
                        },
                        exc_info=True,
                    )
                    continue
                driver_text = f"{pd.driver_key.replace('_', ' ')} {policy.must_use_phrases[0] if policy.must_use_phrases else 'shows change in'} {pd.outcome_metric.replace('_', ' ')}{lag_text}"
            
            drivers.append({
                "metric_key": pd.outcome_metric,
                # Pure metadata only (no behavior impact)
                "domain_key": (domain_for_signal(pd.outcome_metric).value if domain_for_signal(pd.outcome_metric) else None),
                "why": driver_text,
                "type": "personal_driver",
                "confidence": pd.confidence,
                "effect_size": pd.effect_size,
                "variance_explained": pd.variance_explained,
                "driver_key": pd.driver_key,
                "claim_level": claim_level,
            })
    
    for it in in_range[:50]:
        meta = {}
        try:
            metadata_str = getattr(it, "metadata_json", None) or "{}"
            if isinstance(metadata_str, str):
                import json
                meta = json.loads(metadata_str)
            elif isinstance(metadata_str, dict):
                meta = metadata_str
        except Exception:
            meta = {}

        # Skip "insufficient_data" insights - they're informational, not actionable
        insight_type = getattr(it, "insight_type", None) or meta.get("type")
        if insight_type == "insufficient_data":
            continue

        metric_key = meta.get("metric_key") or getattr(it, "metric_key", None)
        confidence = getattr(it, "confidence_score", None) or meta.get("confidence")
        typ = meta.get("type") or insight_type or "insight"

        # Safety surfaced
        safety = meta.get("safety")
        if isinstance(safety, dict) and safety.get("risk_level") in ("high", "moderate"):
            risks.append(
                {
                    "risk": safety.get("headline", "Safety note"),
                    "guidance": safety.get("guidance", "Review this carefully."),
                    "metric_key": metric_key,
                }
            )

        drivers.append(
            {
                "metric_key": metric_key,
                # Pure metadata only (no behavior impact)
                "domain_key": (domain_for_signal(metric_key).value if metric_key and domain_for_signal(metric_key) else None),
                "why": getattr(it, "title", "Change detected"),
                "type": typ,
                "confidence": float(confidence) if confidence is not None else None,
                "evidence": meta,
            }
        )

    # Actions: from evaluations + adherence gaps + checkins
    # GOVERNANCE: Apply claim policy to recommended actions
    actions = []
    for ev in eval_in_range[:10]:
        verdict = getattr(ev, "verdict", "")
        confidence = getattr(ev, "confidence_score", 0.5) or 0.5
        try:
            claim_level = min(5, max(1, int(confidence * 5) + 1))
            policy = get_policy(claim_level)
        except Exception as e:
            # FAIL-CLOSED: drop this action segment
            logger.error(
                "narrative_claim_policy_lookup_failed_drop_segment",
                extra={
                    "user_id": user_id,
                    "segment": "evaluation_action",
                    "evaluation_id": getattr(ev, "id", None),
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
                exc_info=True,
            )
            continue
        
        # Only suggest actions allowed at this claim level
        if verdict == "helpful":
            try:
                allowed = is_action_allowed(claim_level, "continue_protocol")
            except Exception as e:
                logger.error(
                    "narrative_action_allowlist_failed_drop_segment",
                    extra={
                        "user_id": user_id,
                        "segment": "evaluation_action",
                        "evaluation_id": getattr(ev, "id", None),
                        "claim_level": claim_level,
                        "error_type": type(e).__name__,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                continue
            if allowed:
                action_text = "Consider continuing"
                rationale = f"Experiment {policy.must_use_phrases[0] if policy.must_use_phrases else 'suggests'} this protocol may be helpful"
            else:
                # Downgrade to monitoring only
                action_text = "Monitor"
                rationale = f"Experiment data {policy.must_use_phrases[0] if policy.must_use_phrases else 'shows'} potential benefit (uncertain)"
        else:
            action_text = "Review"
            rationale = f"Experiment verdict: {verdict}"
        
        actions.append(
            {
                "action": action_text,
                "rationale": rationale,
                "metric_key": getattr(ev, "metric_key", None),
                # Pure metadata only (no behavior impact)
                "domain_key": (
                    domain_for_signal(getattr(ev, "metric_key", None)).value
                    if getattr(ev, "metric_key", None) and domain_for_signal(getattr(ev, "metric_key", None))
                    else None
                ),
                "safety": getattr(ev, "details_json", None),
                "claim_level": claim_level,
            }
        )

    # If user didn't check in much, prompt
    expected_days = (end - start).days + 1
    coverage = len(checkins) / expected_days if expected_days > 0 else 0.0
    if coverage < 0.5:
        actions.append(
            {
                "action": "Complete daily check-ins",
                "rationale": "Your subjective signals help explain wearable/lab changes and make evaluations more reliable.",
                "metric_key": None,
                "domain_key": None,
                "safety": None,
            }
        )

    # Simple key points (human-readable bullets, deterministic)
    # GOVERNANCE: Apply claim policy to key points
    key_points = []
    if not in_range and not personal_drivers:
        key_points.append("No notable changes detected in this period.")
    else:
        # Prioritize personal drivers in key points
        top_personal = [d for d in drivers if d.get("type") == "personal_driver"][:3]
        top_insights = [d for d in drivers if d.get("type") != "personal_driver"][:2]
        
        for d in top_personal + top_insights:
            mk = d.get("metric_key") or "metric"
            why = d.get("why", "Change detected")
            claim_level = d.get("claim_level", 1)
            
            # Validate key point language
            key_point_text = f"{mk}: {why}"
            try:
                is_valid, violations = validate_language(claim_level, key_point_text)
            except Exception as e:
                # FAIL-CLOSED: drop this key point rather than include unvalidated text.
                logger.error(
                    "narrative_claim_policy_validation_failed_drop_segment",
                    extra={
                        "user_id": user_id,
                        "segment": "key_point",
                        "metric_key": mk,
                        "error_type": type(e).__name__,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                continue
            if not is_valid:
                # Adjust to policy-compliant language
                try:
                    policy = get_policy(claim_level)
                except Exception as e:
                    logger.error(
                        "narrative_claim_policy_lookup_failed_drop_segment",
                        extra={
                            "user_id": user_id,
                            "segment": "key_point",
                            "metric_key": mk,
                            "claim_level": claim_level,
                            "error_type": type(e).__name__,
                            "error": str(e),
                        },
                        exc_info=True,
                    )
                    continue
                why = f"{policy.must_use_phrases[0] if policy.must_use_phrases else 'shows change'} in {mk}"
                key_point_text = f"{mk}: {why}"
            
            key_points.append(key_point_text)
        
        # Add personal driver summary if available (with claim policy)
        if personal_drivers:
            top_positive = [pd for pd in personal_drivers if pd.direction == "positive"][:1]
            if top_positive:
                pd = top_positive[0]
                try:
                    claim_level = min(5, max(1, int(pd.confidence * 5) + 1))
                    policy = get_policy(claim_level)
                except Exception as e:
                    logger.error(
                        "narrative_claim_policy_lookup_failed_drop_segment",
                        extra={
                            "user_id": user_id,
                            "segment": "personal_driver_summary",
                            "driver_key": getattr(pd, "driver_key", None),
                            "error_type": type(e).__name__,
                            "error": str(e),
                        },
                        exc_info=True,
                    )
                    # Just skip summary; narrative still returns.
                    pass
                else:
                
                    if claim_level >= 3:
                        summary_text = f"Over the last {window_days} days, {pd.driver_key.replace('_', ' ')} appears to be your strongest driver of {pd.outcome_metric.replace('_', ' ')}."
                    elif claim_level == 2:
                        summary_text = f"Over the last {window_days} days, {pd.driver_key.replace('_', ' ')} is associated with changes in {pd.outcome_metric.replace('_', ' ')}."
                    else:
                        summary_text = f"Over the last {window_days} days, {pd.driver_key.replace('_', ' ')} shows correlation with {pd.outcome_metric.replace('_', ' ')}."
                
                    # Validate
                    try:
                        is_valid, _ = validate_language(claim_level, summary_text)
                    except Exception as e:
                        logger.error(
                            "narrative_claim_policy_validation_failed_drop_segment",
                            extra={
                                "user_id": user_id,
                                "segment": "personal_driver_summary",
                                "driver_key": getattr(pd, "driver_key", None),
                                "error_type": type(e).__name__,
                                "error": str(e),
                            },
                            exc_info=True,
                        )
                        # Drop summary segment
                        summary_text = ""
                    if summary_text and not is_valid:
                        summary_text = f"Over the last {window_days} days, {pd.driver_key.replace('_', ' ')} {policy.must_use_phrases[0] if policy.must_use_phrases else 'shows change'} in {pd.outcome_metric.replace('_', ' ')}."
                
                    if summary_text:
                        key_points.insert(0, summary_text)

    # Summary/title
    if period_type == "daily":
        title = f"Daily summary — {start.isoformat()}"
    else:
        title = f"Weekly summary — {start.isoformat()} to {end.isoformat()}"

    summary = (
        f"{len(in_range)} insights generated. "
        f"{len(eval_in_range)} experiment evaluations. "
        f"Check-in coverage: {int(coverage * 100)}%."
    )

    metadata = {
        "insights_count": len(in_range),
        "evaluations_count": len(eval_in_range),
        "checkins_count": len(checkins),
        "checkin_coverage": coverage,
        "adherence_events_count": len(adherence),
    }

    # Pure metadata only: attach domain keys for key points without changing wording/ordering.
    # We keep key_points as strings for backward compatibility, and store structured segments in metadata.
    key_point_segments: List[Dict[str, Any]] = []
    for kp in key_points:
        if not isinstance(kp, str):
            continue
        mk = None
        if ":" in kp:
            mk = kp.split(":", 1)[0].strip()
        dk = domain_for_signal(mk) if mk else None
        key_point_segments.append(
            {
                "text": kp,
                "metric_key": mk,
                "domain_key": dk.value if dk else None,
            }
        )
    metadata["key_point_segments"] = key_point_segments

    # Optional: LLM translation of the narrative summary ONLY (not decisions)
    # Keep it safe and gated
    if include_llm_translation and translate_insight is not None:
        try:
            # Reuse your translate_insight as a generic "plain-language" function if it exists.
            # If not suitable, keep deterministic.
            pass
        except Exception:
            pass

    return NarrativeDraft(
        title=title,
        summary=summary,
        key_points=key_points,
        drivers=drivers[:25],
        actions=actions[:10],
        risks=risks[:10],
        metadata=metadata,
    )


def generate_and_persist_narrative(
    db: Session,
    *,
    user_id: int,
    period_type: str,
    start: date,
    end: date,
    include_llm_translation: bool = False,
):
    """
    Generate and persist narrative.
    
    WEEK 4: Creates audit events and explanation edges for explainability.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    repo = NarrativeRepository(db)
    draft = synthesize_narrative(
        db,
        user_id=user_id,
        period_type=period_type,
        start=start,
        end=end,
        include_llm_translation=include_llm_translation,
    )

    # Domain-level status (metadata only): compute conservative silence classification.
    # This does not change narrative content, ordering, or suppression.
    try:
        domain_statuses = compute_domain_statuses(db, user_id=user_id, surfaced_insights=None)
        draft.metadata["domain_statuses"] = {k.value: v.value for k, v in domain_statuses.items()}
        draft.metadata["domain_status_computed_at"] = datetime.utcnow().isoformat()
    except Exception:
        # Best-effort only; never block narrative persistence.
        pass
    narrative = repo.upsert(
        user_id=user_id,
        period_type=period_type,
        period_start=start,
        period_end=end,
        title=draft.title,
        summary=draft.summary,
        key_points_json=draft.key_points,
        drivers_json=draft.drivers,
        actions_json=draft.actions,
        risks_json=draft.risks,
        metadata_json=draft.metadata,
    )
    
    # WEEK 4: Create audit event for explainability
    try:
        audit_repo = AuditRepository(db)
        explanation_repo = ExplanationRepository(db)
        
        # Extract source metrics from metadata
        source_metrics = []
        if draft.metadata:
            # Try to extract metric keys from insights/evaluations used
            source_metrics = draft.metadata.get("source_metrics", [])
        
        # Pure metadata only: narrative may span multiple domains; record the set for provenance.
        domain_keys = set()
        for seg_list in (draft.drivers or [], draft.actions or [], draft.risks or []):
            for seg in seg_list:
                if isinstance(seg, dict):
                    dk = seg.get("domain_key")
                    if isinstance(dk, str) and dk:
                        domain_keys.add(dk)
        domain_keys_list = sorted(domain_keys) if domain_keys else []
        domain_key_single = domain_keys_list[0] if len(domain_keys_list) == 1 else None

        audit_repo.create(
            user_id=user_id,
            entity_type="narrative",
            entity_id=narrative.id,
            decision_type="created",
            decision_reason=f"Generated {period_type} narrative for period {start} to {end}",
            source_metrics=source_metrics,
            time_windows={"period": {"start": start.isoformat(), "end": end.isoformat()}},
            detectors_used=["narrative_synthesizer"],
            thresholds_crossed=[],
            safety_checks_applied=[],
            metadata={
                "domain_key": domain_key_single,
                "domain_keys": domain_keys_list,
                # Domain status is included for provenance only.
                "domain_statuses": (draft.metadata or {}).get("domain_statuses"),
                "domain_status_computed_at": (draft.metadata or {}).get("domain_status_computed_at"),
                "period_type": period_type,
                "key_points_count": len(draft.key_points),
                "drivers_count": len(draft.drivers),
                "actions_count": len(draft.actions),
                "risks_count": len(draft.risks),
            },
        )
        
        # Create explanation edges from insights/evaluations to narrative
        # (This would require tracking which insights/evaluations were used)
        # For now, create a generic edge
        explanation_repo.create_edge(
            target_type="narrative",
            target_id=narrative.id,
            source_type="insight",
            source_id=None,
            contribution_weight=1.0,
            description=f"Synthesized from insights and evaluations in period {start} to {end}",
        )
    except Exception as e:
        logger.warning(f"Failed to create audit event for narrative {narrative.id}: {e}")
    
    return narrative

