from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import sqrt
from statistics import mean, pstdev
from typing import Optional, List, Tuple, Dict, Any, Union

from sqlalchemy.orm import Session

from app.domain.models.health_data_point import HealthDataPoint
from app.domain.models.experiment import Experiment
from app.domain.models.adherence_event import AdherenceEvent
from app.domain.models.evaluation_result import EvaluationResult

try:
    # Optional: metric registry helps determine "expected direction"
    from app.domain.metric_registry import get_metric_spec  # type: ignore
except Exception:
    get_metric_spec = None  # type: ignore


@dataclass
class WindowStats:
    n: int
    coverage: float
    values: List[float]
    mean: float
    std: float


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _cohens_d(pre: List[float], post: List[float]) -> float:
    """
    Cohen's d using pooled std (population std). Safe for MVP / interpretable.
    Returns 0 if insufficient variance.
    """
    if len(pre) < 2 or len(post) < 2:
        return 0.0
    pre_m = mean(pre)
    post_m = mean(post)
    pre_s = pstdev(pre) if len(pre) >= 2 else 0.0
    post_s = pstdev(post) if len(post) >= 2 else 0.0
    pooled = sqrt((pre_s**2 + post_s**2) / 2.0)
    if pooled <= 1e-9:
        return 0.0
    return (post_m - pre_m) / pooled


def _date_floor_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def _fetch_values(
    db: Session,
    user_id: int,
    metric_key: str,
    start: datetime,
    end: datetime,
) -> List[Tuple[datetime, float]]:
    """
    Fetch raw points. Works whether the column is metric_type or data_type in DB.
    Your codebase standardizes on metric_type in Python; some DBs still use data_type.
    HealthDataPoint should map appropriately, but we keep this query simple.
    """
    q = (
        db.query(HealthDataPoint)
        .filter(HealthDataPoint.user_id == user_id)
        .filter(HealthDataPoint.metric_type == metric_key)  # canonical python attribute
        .filter(HealthDataPoint.timestamp >= start)
        .filter(HealthDataPoint.timestamp < end)
        .order_by(HealthDataPoint.timestamp.asc())
    )
    rows = q.all()
    out: List[Tuple[datetime, float]] = []
    for r in rows:
        try:
            out.append((r.timestamp, float(r.value)))
        except Exception:
            continue
    return out


def _aggregate_daily(values: List[Tuple[datetime, float]]) -> Dict[datetime, float]:
    """
    Aggregate multiple points per day -> daily mean.
    """
    buckets: Dict[datetime, List[float]] = {}
    for ts, v in values:
        day = _date_floor_utc(ts)
        buckets.setdefault(day, []).append(v)
    return {day: mean(vs) for day, vs in buckets.items() if vs}


def _window_stats(
    daily: Dict[datetime, float],
    start: datetime,
    end: datetime,
    expected_days: int,
) -> WindowStats:
    days = []
    cur = _date_floor_utc(start)
    end_day = _date_floor_utc(end)
    while cur < end_day:
        days.append(cur)
        cur = cur + timedelta(days=1)

    present = [daily[d] for d in days if d in daily]
    n = len(present)
    coverage = 0.0 if expected_days <= 0 else min(1.0, n / float(expected_days))
    m = mean(present) if present else 0.0
    s = pstdev(present) if len(present) >= 2 else 0.0
    return WindowStats(n=n, coverage=coverage, values=present, mean=m, std=s)


def _compute_adherence_rate(
    db: Session,
    experiment_id: int,
    start: datetime,
    end: datetime,
) -> float:
    """
    MVP adherence: % of logged events with taken=True in [start, end).
    If no events, returns 0 (unknown -> treated separately).
    """
    q = (
        db.query(AdherenceEvent)
        .filter(AdherenceEvent.experiment_id == experiment_id)
        .filter(AdherenceEvent.timestamp >= start)
        .filter(AdherenceEvent.timestamp < end)
        .order_by(AdherenceEvent.timestamp.asc())
    )
    events = q.all()
    if not events:
        return 0.0
    taken = 0
    total = 0
    for e in events:
        total += 1
        if getattr(e, "taken", False):
            taken += 1
    if total == 0:
        return 0.0
    return max(0.0, min(1.0, taken / float(total)))


def _expected_direction_for_experiment(exp: Experiment, metric_key: str) -> Optional[str]:
    """
    Returns 'up' or 'down' or None.
    Priority:
      1) explicit field on Experiment (expected_direction / expected_change)
      2) metric registry directionality (higher_is_better / higher_is_worse)
    """
    # 1) Experiment explicit
    for attr in ["expected_direction", "expected_change", "expected_delta_direction"]:
        if hasattr(exp, attr):
            val = getattr(exp, attr)
            if isinstance(val, str) and val.lower() in {"up", "down"}:
                return val.lower()

    # 2) Metric registry fallback
    if get_metric_spec is not None:
        try:
            spec = get_metric_spec(metric_key)
            # support either naming
            higher_is_better = getattr(spec, "higher_is_better", None)
            higher_is_worse = getattr(spec, "higher_is_worse", None)
            if higher_is_better is True:
                return "up"
            if higher_is_worse is True:
                return "down"
            # sometimes it's "polarity"
            polarity = getattr(spec, "polarity", None)
            if isinstance(polarity, str):
                if polarity.lower() in {"higher_is_better", "positive"}:
                    return "up"
                if polarity.lower() in {"higher_is_worse", "negative"}:
                    return "down"
        except Exception:
            pass

    return None


def evaluate_experiment(
    db: Session,
    experiment_id: int,
    baseline_days: int = 14,
    intervention_days: int = 14,
    min_coverage: float = 0.60,
    min_points: int = 7,
) -> EvaluationResult:
    """
    Core evaluation:
    - baseline window: [start - baseline_days, start)
    - intervention window: [start, min(start + intervention_days, end or now))
    - daily aggregation
    - coverage-aware stats
    - effect size + percent change
    - verdict

    Writes EvaluationResult row and returns it.
    """
    exp: Optional[Experiment] = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if exp is None:
        raise ValueError(f"Experiment {experiment_id} not found")

    user_id = exp.user_id
    # metric key field name may differ; try a few
    metric_key = None
    for attr in ["primary_metric_key", "metric_key", "outcome_metric_key"]:
        if hasattr(exp, attr):
            metric_key = getattr(exp, attr)
            if isinstance(metric_key, str) and metric_key:
                break
    if not metric_key:
        raise ValueError("Experiment missing primary metric key (primary_metric_key/metric_key)")

    # time bounds
    start = exp.started_at if hasattr(exp, "started_at") else getattr(exp, "start_at", None)
    if start is None:
        raise ValueError("Experiment missing start_at")
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)

    end = getattr(exp, "ended_at", None) or getattr(exp, "stopped_at", None)
    if end is not None and end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    now = _utcnow()
    intervention_end = min(now, end) if end else now
    planned_intervention_end = start + timedelta(days=intervention_days)
    intervention_end = min(intervention_end, planned_intervention_end)

    baseline_start = start - timedelta(days=baseline_days)
    baseline_end = start

    # Fetch + aggregate
    pre_raw = _fetch_values(db, user_id, metric_key, baseline_start, baseline_end)
    post_raw = _fetch_values(db, user_id, metric_key, start, intervention_end)

    pre_daily = _aggregate_daily(pre_raw)
    post_daily = _aggregate_daily(post_raw)

    pre_stats = _window_stats(pre_daily, baseline_start, baseline_end, expected_days=baseline_days)
    post_stats = _window_stats(post_daily, start, intervention_end, expected_days=intervention_days)

    # adherence in intervention window
    adherence_rate = _compute_adherence_rate(db, experiment_id, start, intervention_end)

    # effect math
    delta = post_stats.mean - pre_stats.mean
    pct_change = 0.0
    if abs(pre_stats.mean) > 1e-9:
        pct_change = (delta / pre_stats.mean) * 100.0

    d = _cohens_d(pre_stats.values, post_stats.values)
    expected_dir = _expected_direction_for_experiment(exp, metric_key)

    # verdict logic (simple, interpretable, safe)
    verdict = "unclear"
    reasons: List[str] = []

    if pre_stats.coverage < min_coverage or post_stats.coverage < min_coverage:
        verdict = "insufficient_data"
        reasons.append("coverage_below_threshold")
    if pre_stats.n < min_points or post_stats.n < min_points:
        verdict = "insufficient_data"
        reasons.append("not_enough_points")

    # SECURITY FIX (Risk #7): Require adherence evidence for positive verdicts
    # Compute uncertainty bands (confidence intervals)
    from math import sqrt
    
    # Try to use scipy for confidence intervals, fallback to simple approximation
    try:
        from scipy import stats as scipy_stats
        HAS_SCIPY = True
    except ImportError:
        HAS_SCIPY = False
        # Fallback: use t-distribution approximation (z-score for large n)
        def _t_ppf(confidence, df):
            # Simple approximation: for df >= 30, use z=1.96 for 95% CI
            if df >= 30:
                return 1.96
            # For smaller df, use conservative approximation
            return 2.0  # Conservative fallback
        scipy_stats = None  # type: ignore
    
    # Calculate 95% confidence intervals for baseline and intervention means
    baseline_ci_lower = baseline_ci_upper = pre_stats.mean
    intervention_ci_lower = intervention_ci_upper = post_stats.mean
    
    if pre_stats.n >= 2 and pre_stats.std > 0:
        try:
            if HAS_SCIPY:
                t_crit = scipy_stats.t.ppf(0.975, pre_stats.n - 1)  # 95% CI
            else:
                t_crit = _t_ppf(0.975, pre_stats.n - 1)
            se = pre_stats.std / sqrt(pre_stats.n)
            baseline_ci_lower = pre_stats.mean - t_crit * se
            baseline_ci_upper = pre_stats.mean + t_crit * se
        except Exception:
            pass  # Fallback to mean if CI calculation fails
    
    if post_stats.n >= 2 and post_stats.std > 0:
        try:
            if HAS_SCIPY:
                t_crit = scipy_stats.t.ppf(0.975, post_stats.n - 1)  # 95% CI
            else:
                t_crit = _t_ppf(0.975, post_stats.n - 1)
            se = post_stats.std / sqrt(post_stats.n)
            intervention_ci_lower = post_stats.mean - t_crit * se
            intervention_ci_upper = post_stats.mean + t_crit * se
        except Exception:
            pass  # Fallback to mean if CI calculation fails
    
    # Compute confidence score (0-1) based on effect size, coverage, and adherence
    confidence_score = 0.0
    if pre_stats.n >= min_points and post_stats.n >= min_points:
        # Base confidence from effect size
        abs_d = abs(d)
        effect_confidence = min(1.0, abs_d / 0.80)  # Normalize to 0-1, with 0.8+ = 1.0
        
        # Coverage penalty (low coverage reduces confidence)
        coverage_penalty = min(pre_stats.coverage, post_stats.coverage)
        
        # Adherence requirement (SECURITY FIX: no adherence = zero confidence for positive verdicts)
        adherence_confidence = 1.0 if adherence_rate > 0 else 0.0
        
        # Combined confidence
        confidence_score = effect_confidence * coverage_penalty * adherence_confidence
    
    # If we have enough data, decide helpful/not_helpful/unclear
    if verdict != "insufficient_data":
        # effect magnitude tiers
        abs_d = abs(d)
        meaningful = abs_d >= 0.35  # MVP threshold (small/medium boundary-ish)
        strong = abs_d >= 0.60

        # direction check
        actual_dir = "up" if delta > 0 else "down" if delta < 0 else "flat"
        direction_matches = (expected_dir is None) or (actual_dir == expected_dir)

        # SECURITY FIX (Risk #7): Require adherence evidence for "helpful" verdicts
        # Also require minimum confidence
        min_confidence_for_helpful = 0.5  # Minimum confidence threshold
        has_adherence_evidence = adherence_rate > 0.0
        
        if meaningful and direction_matches:
            # SECURITY FIX: Cannot be "helpful" without adherence evidence
            if not has_adherence_evidence:
                verdict = "unclear"
                reasons.append("effect_size_meaningful_but_no_adherence_evidence")
                reasons.append("cannot_confirm_intervention_was_followed")
            elif confidence_score < min_confidence_for_helpful:
                verdict = "unclear"
                reasons.append("effect_size_meaningful_but_low_confidence")
                reasons.append(f"confidence_score_below_threshold_{confidence_score:.2f}")
            else:
                verdict = "helpful" if strong else "helpful"
                reasons.append("effect_size_meaningful")
                if expected_dir is not None:
                    reasons.append("direction_matches_expected")
                if has_adherence_evidence:
                    reasons.append(f"adherence_evidence_present_{adherence_rate*100:.0f}%")
        elif meaningful and not direction_matches:
            verdict = "not_helpful"
            reasons.append("effect_size_meaningful_but_wrong_direction")
        else:
            verdict = "unclear"
            reasons.append("effect_too_small_or_noisy")
        
        # SECURITY FIX: Always record adherence status prominently
        if adherence_rate == 0.0:
            reasons.append("no_adherence_events_logged")
            reasons.append("adherence_unknown_cannot_confirm_effectiveness")
        elif adherence_rate < 0.5:
            reasons.append(f"low_adherence_rate_{adherence_rate*100:.0f}%")
            reasons.append("low_adherence_reduces_confidence_in_results")

    details: Dict[str, Any] = {
        "metric_key": metric_key,
        "baseline_days": baseline_days,
        "intervention_days": intervention_days,
        "baseline_window": {"start": baseline_start.isoformat(), "end": baseline_end.isoformat()},
        "intervention_window": {"start": start.isoformat(), "end": intervention_end.isoformat()},
        "pre": {
            "n": pre_stats.n,
            "coverage": pre_stats.coverage,
            "mean": pre_stats.mean,
            "std": pre_stats.std,
            "ci_lower": baseline_ci_lower,  # SECURITY FIX (Risk #7): Uncertainty bands
            "ci_upper": baseline_ci_upper,
        },
        "post": {
            "n": post_stats.n,
            "coverage": post_stats.coverage,
            "mean": post_stats.mean,
            "std": post_stats.std,
            "ci_lower": intervention_ci_lower,  # SECURITY FIX (Risk #7): Uncertainty bands
            "ci_upper": intervention_ci_upper,
        },
        "delta": delta,
        "percent_change": pct_change,
        "effect_size_d": d,
        "expected_direction": expected_dir,
        "reasons": reasons,
        "adherence_rate": adherence_rate,
        "confidence_score": confidence_score,  # SECURITY FIX (Risk #7): Confidence score
        "has_adherence_evidence": adherence_rate > 0.0,  # SECURITY FIX (Risk #7): Explicit adherence flag
    }

    # Generate summary text
    # SECURITY FIX (Risk #7): Prominently label confidence and adherence status
    summary_parts = [f"Metric: {metric_key}"]
    
    # Add confidence label prominently
    if confidence_score < 0.5:
        summary_parts.append(f"[LOW CONFIDENCE: {confidence_score*100:.0f}%]")
    elif confidence_score < 0.7:
        summary_parts.append(f"[MODERATE CONFIDENCE: {confidence_score*100:.0f}%]")
    else:
        summary_parts.append(f"[HIGH CONFIDENCE: {confidence_score*100:.0f}%]")
    
    if verdict == "helpful":
        summary_parts.append(f"Intervention showed {abs(pct_change):.1f}% change in expected direction (effect size: {d:.2f})")
    elif verdict == "not_helpful":
        summary_parts.append(f"Intervention showed {abs(pct_change):.1f}% change in wrong direction (effect size: {d:.2f})")
    elif verdict == "unclear":
        if "no_adherence_evidence" in reasons or "adherence_unknown" in reasons:
            summary_parts.append(f"Effect size meaningful ({d:.2f}) but cannot confirm intervention was followed")
        else:
            summary_parts.append(f"Effect size too small or noisy (effect size: {d:.2f})")
    else:
        summary_parts.append("Insufficient data for evaluation")
    
    # SECURITY FIX (Risk #7): Prominently display adherence status
    if adherence_rate > 0:
        summary_parts.append(f"Adherence: {adherence_rate*100:.0f}%")
        if adherence_rate < 0.5:
            summary_parts.append("[WARNING: Low adherence may affect results]")
    else:
        summary_parts.append("[WARNING: No adherence events logged - cannot confirm intervention was followed]")
    
    summary = ". ".join(summary_parts)

    # Persist EvaluationResult
    ev = EvaluationResult(
        user_id=user_id,
        experiment_id=experiment_id,
        metric_key=metric_key,
        baseline_mean=pre_stats.mean,
        baseline_std=pre_stats.std,
        intervention_mean=post_stats.mean,
        intervention_std=post_stats.std,
        delta=delta,
        percent_change=pct_change,
        effect_size=d,
        coverage=min(pre_stats.coverage, post_stats.coverage),
        adherence_rate=adherence_rate,
        verdict=verdict,
        summary=summary,
        created_at=_utcnow(),
        details_json=details,
    )

    db.add(ev)
    db.commit()
    db.refresh(ev)
    
    # WEEK 4: Create audit event for explainability
    try:
        from app.domain.repositories.audit_repository import AuditRepository
        audit_repo = AuditRepository(db)
        audit_repo.create(
            user_id=user_id,
            entity_type="evaluation",
            entity_id=ev.id,
            decision_type="created",
            decision_reason=f"Evaluation completed: {verdict}",
            source_metrics=[metric_key],
            time_windows={
                "baseline": {"start": baseline_start.isoformat(), "end": baseline_end.isoformat()},
                "intervention": {"start": start.isoformat(), "end": intervention_end.isoformat()},
            },
            detectors_used=["evaluation_service"],
            thresholds_crossed=[
                {"threshold": "min_coverage", "value": min(pre_stats.coverage, post_stats.coverage), "threshold_value": min_coverage},
                {"threshold": "min_points", "value": min(pre_stats.n, post_stats.n), "threshold_value": min_points},
            ],
            safety_checks_applied=[
                {"check": "adherence_required", "result": "passed" if adherence_rate > 0 else "failed"},
                {"check": "confidence_threshold", "result": "passed" if confidence_score >= 0.5 else "failed"},
            ],
            metadata={
                "verdict": verdict,
                "effect_size": d,
                "adherence_rate": adherence_rate,
                "confidence_score": confidence_score,
            },
        )
        
        # Create explanation edges
        from app.domain.repositories.explanation_repository import ExplanationRepository
        explanation_repo = ExplanationRepository(db)
        
        # Edge from experiment to evaluation
        explanation_repo.create_edge(
            target_type="evaluation",
            target_id=ev.id,
            source_type="experiment",
            source_id=experiment_id,
            contribution_weight=1.0,
            description=f"Evaluation of experiment {experiment_id}",
        )
        
        # Edge from baseline data to evaluation
        explanation_repo.create_edge(
            target_type="evaluation",
            target_id=ev.id,
            source_type="health_data",
            source_id=None,
            contribution_weight=0.5,
            description=f"Baseline data for {metric_key} (n={pre_stats.n}, mean={pre_stats.mean:.2f})",
        )
        
        # Edge from intervention data to evaluation
        explanation_repo.create_edge(
            target_type="evaluation",
            target_id=ev.id,
            source_type="health_data",
            source_id=None,
            contribution_weight=0.5,
            description=f"Intervention data for {metric_key} (n={post_stats.n}, mean={post_stats.mean:.2f})",
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to create audit event for evaluation {ev.id}: {e}")
    
    return ev

