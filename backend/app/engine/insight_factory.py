from app.engine.confidence import compute_confidence
from app.engine.statistics.confidence import compute_bayesian_confidence


def make_change_insight_payload(change, expected_days: int):
    # Phase 2.2: Use Bayesian confidence for change detection
    bayesian = compute_bayesian_confidence(
        observed_mean=change.recent_mean,
        baseline_center=change.baseline_mean,
        baseline_spread=change.baseline_std,
        n_observations=change.n_points,
    )
    confidence = bayesian.probability_real

    title = f"{change.metric_key}: {change.strength} change detected"
    summary = (
        f"Recent average shifted {change.direction} vs your baseline "
        f"(z={change.z_score:.2f})."
    )

    evidence = {
        "type": "change",
        "window_days": change.window_days,
        "n_points": change.n_points,
        "recent_mean": change.recent_mean,
        "baseline_mean": change.baseline_mean,
        "baseline_std": change.baseline_std,
        "z_score": change.z_score,
        "direction": change.direction,
        "strength": change.strength,
        # Phase 2.2: Bayesian confidence metadata
        "bayesian_probability": bayesian.probability_real,
        "bayes_factor": bayesian.bayes_factor,
        "effect_size_d": bayesian.effect_size,
        "credible_interval_80": list(bayesian.credible_interval_80),
        "credible_interval_95": list(bayesian.credible_interval_95),
        "confidence_interpretation": bayesian.interpretation,
    }

    return title, summary, confidence, evidence


def make_trend_insight_payload(trend, expected_days: int):
    confidence = compute_confidence(
        sample_days=trend.n_points,
        expected_days=expected_days,
        effect_size=abs(trend.slope_per_day),
        consistency_ratio=min(trend.n_points / expected_days, 1.0),
    )

    title = f"{trend.metric_key}: {trend.strength} trend {trend.direction}"
    summary = f"Metric is trending {trend.direction} over the last {trend.window_days} days."

    evidence = {
        "type": "trend",
        "window_days": trend.window_days,
        "n_points": trend.n_points,
        "slope_per_day": trend.slope_per_day,
        "direction": trend.direction,
        "strength": trend.strength,
    }

    return title, summary, confidence, evidence


def make_instability_insight_payload(instability, expected_days: int):
    confidence = compute_confidence(
        sample_days=instability.n_points,
        expected_days=expected_days,
        effect_size=instability.ratio,
        consistency_ratio=min(instability.n_points / expected_days, 1.0),
    )

    title = f"{instability.metric_key}: variability increased ({instability.strength})"
    summary = (
        f"Day-to-day variability increased vs your baseline "
        f"(ratio={instability.ratio:.2f}x)."
    )

    evidence = {
        "type": "instability",
        "window_days": instability.window_days,
        "n_points": instability.n_points,
        "recent_std": instability.recent_std,
        "baseline_std": instability.baseline_std,
        "instability_ratio": instability.ratio,
        "strength": instability.strength,
    }

    return title, summary, confidence, evidence
