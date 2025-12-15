from datetime import date, timedelta, datetime

from typing import List, Dict

from statistics import mean, pstdev

from app.domain.repositories.health_data_repository import HealthDataRepository

from app.domain.repositories.experiment_repository import ExperimentRepository

from app.domain.repositories.adherence_repository import AdherenceRepository

from app.engine.attribution.attribution_types import AttributionResult


MAX_LAG_DAYS = 3

MIN_POINTS = 5


def cohens_d(a: List[float], b: List[float]) -> float:
    if len(a) < 2 or len(b) < 2:
        return 0.0

    mean_a, mean_b = mean(a), mean(b)
    std_a, std_b = pstdev(a), pstdev(b)

    pooled_std = ((std_a ** 2 + std_b ** 2) / 2) ** 0.5
    if pooled_std == 0:
        return 0.0

    return (mean_b - mean_a) / pooled_std


class LaggedEffectEngine:
    """
    Computes lagged attribution effects for a single experiment + metric.
    """

    def __init__(
        self,
        health_repo: HealthDataRepository,
        experiment_repo: ExperimentRepository,
        adherence_repo: AdherenceRepository,
    ):
        self.health_repo = health_repo
        self.experiment_repo = experiment_repo
        self.adherence_repo = adherence_repo

    def run(
        self,
        experiment_id: int,
        metric_key: str,
        baseline_days: int = 14,
    ) -> List[AttributionResult]:

        experiment = self.experiment_repo.get(experiment_id)
        if not experiment:
            return []

        user_id = experiment.user_id
        # Experiment model uses started_at/ended_at, not start_date/end_date
        start_date = experiment.started_at.date() if isinstance(experiment.started_at, datetime) else experiment.started_at
        end_date = (experiment.ended_at.date() if isinstance(experiment.ended_at, datetime) else experiment.ended_at) if experiment.ended_at else date.today()

        baseline_start = start_date - timedelta(days=baseline_days)
        baseline_end = start_date - timedelta(days=1)

        baseline_points = self._load_metric(
            user_id, metric_key, baseline_start, baseline_end
        )

        if len(baseline_points) < MIN_POINTS:
            return []

        results: List[AttributionResult] = []

        for lag in range(0, MAX_LAG_DAYS + 1):
            lagged_start = start_date + timedelta(days=lag)
            lagged_end = end_date + timedelta(days=lag)

            intervention_points = self._load_metric(
                user_id, metric_key, lagged_start, lagged_end
            )

            if len(intervention_points) < MIN_POINTS:
                continue

            d = cohens_d(baseline_points, intervention_points)

            direction = (
                "improved" if d > 0.2 else
                "worsened" if d < -0.2 else
                "no_change"
            )

            coverage = len(intervention_points) / max(
                (end_date - start_date).days + 1, 1
            )

            confidence = min(
                1.0,
                0.4 * coverage +
                0.6 * min(abs(d), 1.0)
            )

            results.append(
                AttributionResult(
                    user_id=user_id,
                    metric_key=metric_key,
                    intervention_id=experiment.intervention_id,
                    lag_days=lag,
                    effect_size=round(d, 3),
                    direction=direction,
                    confidence=round(confidence, 2),
                    coverage=round(coverage, 2),
                    interaction=None,
                    details={
                        "baseline_mean": round(mean(baseline_points), 2),
                        "intervention_mean": round(mean(intervention_points), 2),
                        "n_baseline": len(baseline_points),
                        "n_intervention": len(intervention_points),
                    },
                )
            )

        return results

    def _load_metric(
        self,
        user_id: int,
        metric_key: str,
        start: date,
        end: date,
    ) -> List[float]:

        # Convert date to datetime for the repository method
        start_dt = datetime.combine(start, datetime.min.time())
        end_dt = datetime.combine(end, datetime.max.time())

        # Use HealthDataRepository's get_by_time_range method
        # Note: The repository uses data_type, but HealthDataPoint model maps metric_type to data_type column
        points = self.health_repo.get_by_time_range(
            user_id=user_id,
            start_date=start_dt,
            end_date=end_dt,
            data_type=metric_key,  # metric_type maps to data_type column
        )

        return [p.value for p in points if p.value is not None]

