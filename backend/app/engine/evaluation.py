from datetime import datetime
from typing import List, Optional
from statistics import mean, stdev

from app.core.signal import Signal
from app.domain.models.experiment_run import ExperimentRun


def _window_values(
    signals: List[Signal],
    metric_key: str,
    start: datetime,
    end: datetime,
) -> List[float]:
    return [
        s.value
        for s in signals
        if s.metric_key == metric_key and start <= s.timestamp < end
    ]


def _cohens_d(a: List[float], b: List[float]) -> Optional[float]:
    if len(a) < 2 or len(b) < 2:
        return None
    sa = stdev(a)
    sb = stdev(b)
    pooled = ((sa**2 + sb**2) / 2) ** 0.5
    if pooled == 0:
        return None
    return (mean(b) - mean(a)) / pooled


def _confidence(a: List[float], b: List[float], expected_days: int = 14) -> float:
    # Simple missingness-based confidence
    coverage = (min(len(a), expected_days) + min(len(b), expected_days)) / (2 * expected_days)
    return max(0.0, min(1.0, coverage))


def evaluate_experiment(
    *,
    experiment: ExperimentRun,
    signals: List[Signal],
) -> dict:
    metric = experiment.target_metric

    baseline_vals = _window_values(signals, metric, experiment.baseline_start, experiment.baseline_end)
    followup_vals = _window_values(signals, metric, experiment.followup_start, experiment.followup_end)

    if not baseline_vals or not followup_vals:
        raise ValueError("Not enough data to evaluate experiment")

    baseline_mean = mean(baseline_vals)
    followup_mean = mean(followup_vals)
    delta = followup_mean - baseline_mean

    d = _cohens_d(baseline_vals, followup_vals)
    conf = _confidence(baseline_vals, followup_vals)

    # For MVP, we classify based on direction of delta
    if abs(delta) < 1e-6:
        conclusion = "no_change"
    elif delta > 0:
        conclusion = "improved"
    else:
        conclusion = "worsened"

    return {
        "baseline_mean": baseline_mean,
        "followup_mean": followup_mean,
        "delta": delta,
        "effect_size": d,
        "confidence": conf,
        "conclusion": conclusion,
    }

