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

    # If we have enough data, decide helpful/not_helpful/unclear
    if verdict != "insufficient_data":
        # effect magnitude tiers
        abs_d = abs(d)
        meaningful = abs_d >= 0.35  # MVP threshold (small/medium boundary-ish)
        strong = abs_d >= 0.60

        # direction check
        actual_dir = "up" if delta > 0 else "down" if delta < 0 else "flat"
        direction_matches = (expected_dir is None) or (actual_dir == expected_dir)

        if meaningful and direction_matches:
            verdict = "helpful" if strong else "helpful"
            reasons.append("effect_size_meaningful")
            if expected_dir is not None:
                reasons.append("direction_matches_expected")
        elif meaningful and not direction_matches:
            verdict = "not_helpful"
            reasons.append("effect_size_meaningful_but_wrong_direction")
        else:
            verdict = "unclear"
            reasons.append("effect_too_small_or_noisy")

        # adherence note (doesn't override, but recorded)
        if adherence_rate == 0.0:
            reasons.append("no_adherence_events_logged")

    details: Dict[str, Any] = {
        "metric_key": metric_key,
        "baseline_days": baseline_days,
        "intervention_days": intervention_days,
        "baseline_window": {"start": baseline_start.isoformat(), "end": baseline_end.isoformat()},
        "intervention_window": {"start": start.isoformat(), "end": intervention_end.isoformat()},
        "pre": {"n": pre_stats.n, "coverage": pre_stats.coverage, "mean": pre_stats.mean, "std": pre_stats.std},
        "post": {"n": post_stats.n, "coverage": post_stats.coverage, "mean": post_stats.mean, "std": post_stats.std},
        "delta": delta,
        "percent_change": pct_change,
        "effect_size_d": d,
        "expected_direction": expected_dir,
        "reasons": reasons,
        "adherence_rate": adherence_rate,
    }

    # Generate summary text
    summary_parts = [f"Metric: {metric_key}"]
    if verdict == "helpful":
        summary_parts.append(f"Intervention showed {abs(pct_change):.1f}% change in expected direction (effect size: {d:.2f})")
    elif verdict == "not_helpful":
        summary_parts.append(f"Intervention showed {abs(pct_change):.1f}% change in wrong direction (effect size: {d:.2f})")
    elif verdict == "unclear":
        summary_parts.append(f"Effect size too small or noisy (effect size: {d:.2f})")
    else:
        summary_parts.append("Insufficient data for evaluation")
    
    if adherence_rate > 0:
        summary_parts.append(f"Adherence: {adherence_rate*100:.0f}%")
    else:
        summary_parts.append("No adherence events logged")
    
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
    return ev

