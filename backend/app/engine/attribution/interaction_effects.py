from typing import List, Optional

from statistics import mean, pstdev

from datetime import timedelta, date, datetime

from app.engine.attribution.attribution_types import AttributionResult

from app.domain.models.daily_checkin import DailyCheckIn

from app.domain.repositories.health_data_repository import HealthDataRepository

from app.domain.repositories.experiment_repository import ExperimentRepository


class InteractionAttributionResult(AttributionResult):
    confounder_key: str
    subgroup: str  # "present" | "absent"
    delta_vs_control: float


class InteractionAttributionEngine:
    """
    Splits intervention windows by confounder presence and compares effects.
    Example: magnesium × caffeine_pm → sleep_duration
    """

    def __init__(
        self,
        health_repo: HealthDataRepository,
        experiment_repo: ExperimentRepository,
    ):
        self.health_repo = health_repo
        self.experiment_repo = experiment_repo

    def run(
        self,
        *,
        base_attributions: List[AttributionResult],
        daily_checkins: List[DailyCheckIn],
        confounder_key: str,
        experiment_id: int,
    ) -> List[InteractionAttributionResult]:

        # Get experiment to determine time windows
        experiment = self.experiment_repo.get(experiment_id)
        if not experiment:
            return []

        user_id = experiment.user_id
        start_date = experiment.started_at.date() if isinstance(experiment.started_at, datetime) else experiment.started_at
        end_date = (experiment.ended_at.date() if isinstance(experiment.ended_at, datetime) else experiment.ended_at) if experiment.ended_at else date.today()

        # Build sets of days where confounder was present/absent
        present_days = {
            c.checkin_date
            for c in daily_checkins
            if c.behaviors_json.get(confounder_key) is True
        }

        absent_days = {
            c.checkin_date
            for c in daily_checkins
            if c.behaviors_json.get(confounder_key) is False
        }

        results = []

        for attr in base_attributions:
            if not attr.details:
                continue

            # Fetch raw values for the intervention period with this lag
            lagged_start = start_date + timedelta(days=attr.lag_days)
            lagged_end = end_date + timedelta(days=attr.lag_days)

            start_dt = datetime.combine(lagged_start, datetime.min.time())
            end_dt = datetime.combine(lagged_end, datetime.max.time())

            # Fetch raw health data points
            points = self.health_repo.get_by_time_range(
                user_id=user_id,
                start_date=start_dt,
                end_date=end_dt,
                data_type=attr.metric_key,
            )

            # Convert to list of {date, value} dicts
            values = [
                {"date": p.timestamp.date(), "value": p.value}
                for p in points
                if p.value is not None
            ]

            if len(values) < 8:  # Need at least 8 points to split meaningfully
                continue

            # Split by confounder presence
            present = [v for v in values if v["date"] in present_days]
            absent = [v for v in values if v["date"] in absent_days]

            if len(present) < 4 or len(absent) < 4:
                continue

            mean_present = mean(v["value"] for v in present)
            mean_absent = mean(v["value"] for v in absent)

            pooled_std = pstdev(
                [v["value"] for v in present + absent]
            ) or 1.0

            delta = (mean_absent - mean_present) / pooled_std

            results.append(
                InteractionAttributionResult(
                    user_id=attr.user_id,
                    metric_key=attr.metric_key,
                    intervention_id=attr.intervention_id,
                    lag_days=attr.lag_days,
                    effect_size=attr.effect_size,
                    direction=attr.direction,
                    confidence=attr.confidence,
                    coverage=attr.coverage,
                    interaction=attr.interaction,
                    details={
                        **attr.details,
                        "interaction": {
                            "confounder_key": confounder_key,
                            "mean_present": round(mean_present, 2),
                            "mean_absent": round(mean_absent, 2),
                            "delta_vs_control": round(delta, 3),
                            "n_present": len(present),
                            "n_absent": len(absent),
                        },
                    },
                    confounder_key=confounder_key,
                    subgroup="absent",
                    delta_vs_control=round(delta, 3),
                )
            )

        return results

