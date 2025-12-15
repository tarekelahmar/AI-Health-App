from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np

from app.domain.repositories.health_data_repository import HealthDataRepository
from app.domain.repositories.adherence_repository import AdherenceRepository
from app.domain.repositories.experiment_repository import ExperimentRepository


# ----------------------------
# Result data structures
# ----------------------------

@dataclass
class DiDResult:
    baseline_trend: float
    intervention_trend: float
    diff_in_diff: float


@dataclass
class ITSResult:
    level_change: float
    slope_change: float


@dataclass
class SensitivityResult:
    stable: bool
    flips: int
    tested_windows: int


@dataclass
class MetricEvaluation:
    metric_key: str
    baseline_mean: float
    intervention_mean: float
    percent_change: float
    effect_size: float
    did: DiDResult
    its: ITSResult
    sensitivity: SensitivityResult
    coverage: float
    adherence_rate: float


@dataclass
class EvaluationVerdict:
    verdict: str  # helpful | not_helpful | unclear | insufficient_data
    confidence: float
    reasons: List[str]


# ----------------------------
# Core math helpers
# ----------------------------

def _mean(xs: List[float]) -> float:
    return float(np.mean(xs)) if xs else float("nan")


def _std(xs: List[float]) -> float:
    return float(np.std(xs, ddof=1)) if len(xs) > 1 else float("nan")


def cohens_d(a: List[float], b: List[float]) -> float:
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    pooled_std = math.sqrt(((_std(a) ** 2) + (_std(b) ** 2)) / 2)
    if pooled_std == 0:
        return 0.0
    return (_mean(b) - _mean(a)) / pooled_std


def linear_slope(xs: List[float]) -> float:
    if len(xs) < 3:
        return 0.0
    y = np.array(xs)
    x = np.arange(len(xs))
    slope, _ = np.polyfit(x, y, 1)
    return float(slope)


# ----------------------------
# Advanced evaluation engine
# ----------------------------

class AdvancedEvaluationEngine:
    """
    This engine evaluates interventions using multiple
    quasi-causal statistical checks.

    IMPORTANT:
    - This is NOT medical diagnosis
    - This is NOT population inference
    - This is personal longitudinal analysis
    """

    def __init__(
        self,
        health_repo: HealthDataRepository,
        adherence_repo: AdherenceRepository,
        experiment_repo: ExperimentRepository,
    ):
        self.health_repo = health_repo
        self.adherence_repo = adherence_repo
        self.experiment_repo = experiment_repo

    # ----------------------------
    # Public entrypoint
    # ----------------------------

    def evaluate_experiment(
        self,
        *,
        user_id: int,
        experiment_id: int,
        metric_keys: List[str],
        baseline_days: int = 14,
        intervention_days: int = 14,
    ) -> EvaluationVerdict:

        metric_results: List[MetricEvaluation] = []

        for metric in metric_keys:
            result = self._evaluate_single_metric(
                user_id=user_id,
                experiment_id=experiment_id,
                metric_key=metric,
                baseline_days=baseline_days,
                intervention_days=intervention_days,
            )
            if result:
                metric_results.append(result)

        if not metric_results:
            return EvaluationVerdict(
                verdict="insufficient_data",
                confidence=0.0,
                reasons=["No metrics had sufficient data"],
            )

        return self._aggregate_verdict(metric_results)

    # ----------------------------
    # Per-metric evaluation
    # ----------------------------

    def _evaluate_single_metric(
        self,
        *,
        user_id: int,
        experiment_id: int,
        metric_key: str,
        baseline_days: int,
        intervention_days: int,
    ) -> Optional[MetricEvaluation]:

        experiment = self.experiment_repo.get(experiment_id)
        if not experiment:
            return None

        start = experiment.started_at
        # Handle timezone-naive datetimes
        if start and start.tzinfo is None:
            start = start.replace(tzinfo=None)
        end = experiment.ended_at or datetime.utcnow()
        if end and end.tzinfo is None:
            end = end.replace(tzinfo=None)

        baseline_start = start - timedelta(days=baseline_days)
        intervention_end = start + timedelta(days=intervention_days)

        baseline_points = self.health_repo.get_by_time_range(
            user_id=user_id,
            start_date=baseline_start,
            end_date=start,
            data_type=metric_key,
        )

        intervention_points = self.health_repo.get_by_time_range(
            user_id=user_id,
            start_date=start,
            end_date=intervention_end,
            data_type=metric_key,
        )

        if len(baseline_points) < 5 or len(intervention_points) < 5:
            return None

        baseline_values = [p.value for p in baseline_points]
        intervention_values = [p.value for p in intervention_points]

        # Core stats
        baseline_mean = _mean(baseline_values)
        intervention_mean = _mean(intervention_values)
        percent_change = (
            (intervention_mean - baseline_mean) / baseline_mean * 100
            if baseline_mean != 0
            else 0.0
        )

        effect = cohens_d(baseline_values, intervention_values)

        # Difference-in-Differences
        did = DiDResult(
            baseline_trend=linear_slope(baseline_values),
            intervention_trend=linear_slope(intervention_values),
            diff_in_diff=linear_slope(intervention_values)
            - linear_slope(baseline_values),
        )

        # Interrupted time series
        its = ITSResult(
            level_change=intervention_mean - baseline_mean,
            slope_change=did.diff_in_diff,
        )

        # Sensitivity analysis
        sensitivity = self._sensitivity_analysis(
            user_id=user_id,
            metric_key=metric_key,
            start=start,
            baseline_days=baseline_days,
            intervention_days=intervention_days,
        )

        # Calculate adherence rate from events
        adherence_events = self.adherence_repo.list_by_experiment(experiment_id=experiment_id)
        if adherence_events:
            taken_count = sum(1 for e in adherence_events if getattr(e, "taken", False))
            adherence_rate = taken_count / len(adherence_events) if adherence_events else 0.0
        else:
            adherence_rate = 0.0

        coverage = min(
            len(baseline_points) / baseline_days,
            len(intervention_points) / intervention_days,
        )

        return MetricEvaluation(
            metric_key=metric_key,
            baseline_mean=baseline_mean,
            intervention_mean=intervention_mean,
            percent_change=percent_change,
            effect_size=effect,
            did=did,
            its=its,
            sensitivity=sensitivity,
            coverage=coverage,
            adherence_rate=adherence_rate,
        )

    # ----------------------------
    # Sensitivity analysis
    # ----------------------------

    def _sensitivity_analysis(
        self,
        *,
        user_id: int,
        metric_key: str,
        start: datetime,
        baseline_days: int,
        intervention_days: int,
        shifts: int = 3,
    ) -> SensitivityResult:

        flips = 0
        tested = 0
        original_direction = None

        for delta in range(-shifts, shifts + 1):
            tested += 1
            shifted_start = start + timedelta(days=delta)

            baseline = self.health_repo.get_by_time_range(
                user_id=user_id,
                start_date=shifted_start - timedelta(days=baseline_days),
                end_date=shifted_start,
                data_type=metric_key,
            )

            intervention = self.health_repo.get_by_time_range(
                user_id=user_id,
                start_date=shifted_start,
                end_date=shifted_start + timedelta(days=intervention_days),
                data_type=metric_key,
            )

            if len(baseline) < 5 or len(intervention) < 5:
                continue

            diff = _mean([p.value for p in intervention]) - _mean(
                [p.value for p in baseline]
            )

            direction = "up" if diff > 0 else "down"

            if original_direction is None:
                original_direction = direction
            elif direction != original_direction:
                flips += 1

        return SensitivityResult(
            stable=flips <= 1,
            flips=flips,
            tested_windows=tested,
        )

    # ----------------------------
    # Aggregate verdict
    # ----------------------------

    def _aggregate_verdict(
        self, metrics: List[MetricEvaluation]
    ) -> EvaluationVerdict:

        positive = 0
        negative = 0
        unclear = 0
        reasons: List[str] = []

        for m in metrics:
            if (
                m.effect_size > 0.3
                and m.did.diff_in_diff > 0
                and m.sensitivity.stable
                and m.adherence_rate >= 0.6
            ):
                positive += 1
            elif m.effect_size < 0.1:
                negative += 1
            else:
                unclear += 1

        if positive >= 2:
            verdict = "helpful"
        elif negative >= 2:
            verdict = "not_helpful"
        elif unclear >= 1:
            verdict = "unclear"
        else:
            verdict = "insufficient_data"

        confidence = min(1.0, positive / max(len(metrics), 1))

        return EvaluationVerdict(
            verdict=verdict,
            confidence=confidence,
            reasons=[
                f"{positive} metrics improved with stable effects",
                f"{negative} metrics showed no meaningful change",
                f"{unclear} metrics were ambiguous",
            ],
        )

