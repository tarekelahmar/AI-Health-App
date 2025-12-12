from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Dict, Literal, Optional, Sequence

from app.domain.repositories.lab_result_repository import LabResultRepository
from app.domain.repositories.wearable_repository import WearableRepository
from app.domain.repositories.health_data_repository import HealthDataRepository
from app.domain.repositories.symptom_repository import SymptomRepository
from app.domain.repositories.insight_repository import InsightRepository

from app.engine.analytics.time_series import (
    DailyMetric,
    build_wearable_daily_series,
    build_lab_daily_series,
    build_health_data_daily_series,
)
from app.engine.analytics.rolling_metrics import (
    compute_rolling_stats,
)
from app.engine.analytics.correlation import (
    compute_metric_correlation,
    CorrelationResult,
)


TrendDirection = Literal["improving", "worsening", "stable", "unknown"]


@dataclass
class MetricSummary:
    metric_name: str
    source: Literal["wearable", "lab", "health_data"]
    window_days: int
    latest_value: Optional[float]
    mean_value: Optional[float]
    trend: TrendDirection
    trend_delta: Optional[float]  # mean(last 1/3) - mean(first 1/3)
    unit: Optional[str] = None


@dataclass
class CorrelationSummary:
    metric_x: str
    metric_y: str
    r: float
    n: int
    strength: str
    direction: str
    is_reliable: bool


@dataclass
class GeneratedInsight:
    """Structured insight ready for DB + LLM + API."""

    user_id: int
    category: str           # "sleep", "stress", "metabolic", etc.
    title: str
    description: str        # short machine-generated explanation
    metric_summaries: List[MetricSummary]
    correlations: List[CorrelationSummary]
    window_days: int


def _compute_trend(series: Sequence[DailyMetric]) -> tuple[TrendDirection, Optional[float]]:
    """Determine simple trend by comparing early vs late averages."""
    if len(series) < 6:  # too little to say anything
        return "unknown", None

    values = [dm.value for dm in series]
    n = len(values)
    third = max(1, n // 3)

    first_segment = values[:third]
    last_segment = values[-third:]

    first_mean = sum(first_segment) / len(first_segment)
    last_mean = sum(last_segment) / len(last_segment)
    delta = last_mean - first_mean

    # simple thresholds – later you can tune.
    threshold = abs(first_mean) * 0.05 if first_mean != 0 else 0.05

    if delta > threshold:
        direction: TrendDirection = "worsening"  # e.g. symptom score, glucose, etc.
    elif delta < -threshold:
        direction = "improving"
    else:
        direction = "stable"

    return direction, delta


def _safe_latest(series: Sequence[DailyMetric]) -> Optional[float]:
    return series[-1].value if series else None


def _safe_mean(series: Sequence[DailyMetric]) -> Optional[float]:
    if not series:
        return None
    return sum(dm.value for dm in series) / len(series)


class InsightEngine:
    """
    The reasoning layer sitting on top of the analytics engine.

    This does NOT produce final text for the user – it creates structured
    insight objects that the LLM + UI can then turn into human-friendly narratives.
    """

    def __init__(
        self,
        lab_repo: LabResultRepository,
        wearable_repo: WearableRepository,
        health_data_repo: HealthDataRepository,
        symptom_repo: SymptomRepository,
        insight_repo: InsightRepository,
    ) -> None:
        self.lab_repo = lab_repo
        self.wearable_repo = wearable_repo
        self.health_data_repo = health_data_repo
        self.symptom_repo = symptom_repo
        self.insight_repo = insight_repo

    # -------- Core metric summary builders -------- #

    def summarise_wearable_metric(
        self,
        *,
        user_id: int,
        metric_name: str,
        unit: Optional[str],
        window_days: int,
        end: Optional[datetime] = None,
    ) -> Optional[MetricSummary]:
        end = end or datetime.utcnow()
        start = end - timedelta(days=window_days)

        series = build_wearable_daily_series(
            user_id=user_id,
            metric_type=metric_name,
            start=start,
            end=end,
            wearable_repo=self.wearable_repo,
            aggregation="mean",
        )

        if not series:
            return None

        trend, delta = _compute_trend(series)
        latest = _safe_latest(series)
        avg = _safe_mean(series)

        return MetricSummary(
            metric_name=metric_name,
            source="wearable",
            window_days=window_days,
            latest_value=latest,
            mean_value=avg,
            trend=trend,
            trend_delta=delta,
            unit=unit,
        )

    def summarise_lab_metric(
        self,
        *,
        user_id: int,
        test_name: str,
        window_days: int,
        end: Optional[datetime] = None,
    ) -> Optional[MetricSummary]:
        end = end or datetime.utcnow()
        start = end - timedelta(days=window_days)

        series = build_lab_daily_series(
            user_id=user_id,
            test_name=test_name,
            start=start,
            end=end,
            lab_repo=self.lab_repo,
            aggregation="last",
        )

        if not series:
            return None

        trend, delta = _compute_trend(series)
        latest = _safe_latest(series)
        avg = _safe_mean(series)

        # You could look up units from ontology later; left as optional for now.
        return MetricSummary(
            metric_name=test_name,
            source="lab",
            window_days=window_days,
            latest_value=latest,
            mean_value=avg,
            trend=trend,
            trend_delta=delta,
            unit=None,
        )

    def summarise_health_data_metric(
        self,
        *,
        user_id: int,
        data_type: str,
        window_days: int,
        end: Optional[datetime] = None,
        unit: Optional[str] = None,
    ) -> Optional[MetricSummary]:
        end = end or datetime.utcnow()
        start = end - timedelta(days=window_days)

        series = build_health_data_daily_series(
            user_id=user_id,
            data_type=data_type,
            start=start,
            end=end,
            health_data_repo=self.health_data_repo,
            aggregation="mean",
        )

        if not series:
            return None

        trend, delta = _compute_trend(series)
        latest = _safe_latest(series)
        avg = _safe_mean(series)

        return MetricSummary(
            metric_name=data_type,
            source="health_data",
            window_days=window_days,
            latest_value=latest,
            mean_value=avg,
            trend=trend,
            trend_delta=delta,
            unit=unit,
        )

    # -------- Correlation builders -------- #

    def correlate_daily_metrics(
        self,
        *,
        metric_x_name: str,
        metric_y_name: str,
        series_x: Sequence[DailyMetric],
        series_y: Sequence[DailyMetric],
    ) -> Optional[CorrelationSummary]:
        corr = compute_metric_correlation(
            metric_x_name,
            metric_y_name,
            series_x,
            series_y,
        )
        if not corr:
            return None

        return CorrelationSummary(
            metric_x=corr.metric_x,
            metric_y=corr.metric_y,
            r=corr.r,
            n=corr.n,
            strength=corr.strength,
            direction=corr.direction,
            is_reliable=corr.is_reliable,
        )

    # -------- High-level insight builders -------- #

    def generate_sleep_insights(
        self,
        user_id: int,
        window_days: int = 30,
    ) -> Optional[GeneratedInsight]:
        """
        Example high-level insight: sleep quality & its relationship with HRV / activity.

        You can extend this pattern to stress, glycaemic control, mood, etc.
        """
        end = datetime.utcnow()
        start = end - timedelta(days=window_days)

        # 1) build series
        sleep_series = build_wearable_daily_series(
            user_id=user_id,
            metric_type="sleep_duration",
            start=start,
            end=end,
            wearable_repo=self.wearable_repo,
            aggregation="mean",
        )
        hrv_series = build_wearable_daily_series(
            user_id=user_id,
            metric_type="hrv",
            start=start,
            end=end,
            wearable_repo=self.wearable_repo,
            aggregation="mean",
        )
        activity_series = build_wearable_daily_series(
            user_id=user_id,
            metric_type="activity_minutes",
            start=start,
            end=end,
            wearable_repo=self.wearable_repo,
            aggregation="sum",
        )

        if not sleep_series:
            return None

        # 2) metric summaries
        metric_summaries: List[MetricSummary] = []

        sleep_summary = self.summarise_wearable_metric(
            user_id=user_id,
            metric_name="sleep_duration",
            unit="hours",
            window_days=window_days,
            end=end,
        )
        if sleep_summary:
            metric_summaries.append(sleep_summary)

        hrv_summary = self.summarise_wearable_metric(
            user_id=user_id,
            metric_name="hrv",
            unit="ms",
            window_days=window_days,
            end=end,
        )
        if hrv_summary:
            metric_summaries.append(hrv_summary)

        activity_summary = self.summarise_wearable_metric(
            user_id=user_id,
            metric_name="activity_minutes",
            unit="minutes",
            window_days=window_days,
            end=end,
        )
        if activity_summary:
            metric_summaries.append(activity_summary)

        # 3) correlations
        correlations: List[CorrelationSummary] = []

        if hrv_series:
            corr_sleep_hrv = self.correlate_daily_metrics(
                metric_x_name="sleep_duration",
                metric_y_name="hrv",
                series_x=sleep_series,
                series_y=hrv_series,
            )
            if corr_sleep_hrv:
                correlations.append(corr_sleep_hrv)

        if activity_series:
            corr_sleep_activity = self.correlate_daily_metrics(
                metric_x_name="sleep_duration",
                metric_y_name="activity_minutes",
                series_x=sleep_series,
                series_y=activity_series,
            )
            if corr_sleep_activity:
                correlations.append(corr_sleep_activity)

        # 4) simple machine-generated description
        # This is intentionally terse; the LLM will later expand on it.

        desc_parts: List[str] = []
        if sleep_summary:
            if sleep_summary.trend == "improving":
                desc_parts.append("Average sleep duration is improving over the last month.")
            elif sleep_summary.trend == "worsening":
                desc_parts.append("Average sleep duration is decreasing over the last month.")
            elif sleep_summary.trend == "stable":
                desc_parts.append("Average sleep duration is relatively stable.")

        for c in correlations:
            if not c.is_reliable:
                continue
            if c.metric_y == "hrv":
                if c.direction == "positive":
                    desc_parts.append(
                        "Better sleep duration tends to be associated with higher HRV."
                    )
                elif c.direction == "negative":
                    desc_parts.append(
                        "Longer sleep duration tends to be associated with lower HRV."
                    )
            if c.metric_y == "activity_minutes":
                if c.direction == "positive":
                    desc_parts.append(
                        "On days with more activity, sleep duration tends to be longer."
                    )
                elif c.direction == "negative":
                    desc_parts.append(
                        "On days with more activity, sleep duration tends to be shorter."
                    )

        description = " ".join(desc_parts) or "Sleep metrics analysed over the recent period."

        return GeneratedInsight(
            user_id=user_id,
            category="sleep",
            title="Sleep pattern insights",
            description=description,
            metric_summaries=metric_summaries,
            correlations=correlations,
            window_days=window_days,
        )

    # -------- Persistence helpers -------- #

    def persist_insight(self, insight: GeneratedInsight) -> None:
        """Store a GeneratedInsight into the database using InsightRepository."""
        # You can decide how much to keep as structured vs text.
        # Here we store a compact version + metadata JSON.

        from json import dumps

        metadata = {
            "metric_summaries": [asdict(ms) for ms in insight.metric_summaries],
            "correlations": [
                {
                    "metric_x": c.metric_x,
                    "metric_y": c.metric_y,
                    "r": c.r,
                    "n": c.n,
                    "strength": c.strength,
                    "direction": c.direction,
                    "is_reliable": c.is_reliable,
                }
                for c in insight.correlations
            ],
            "window_days": insight.window_days,
        }

        self.insight_repo.create(
            user_id=insight.user_id,
            insight_type=insight.category,
            title=insight.title,
            description=insight.description,
            confidence_score=0.7,  # you can refine this using ontology / evals later
            metadata_json=dumps(metadata),
        )


# ---------- Helper functions for external callers ---------- #

def generated_insight_to_dict(insight: GeneratedInsight) -> Dict:
    """Convert GeneratedInsight into a dict ready for API / LLM context."""
    return {
        "user_id": insight.user_id,
        "category": insight.category,
        "title": insight.title,
        "description": insight.description,
        "window_days": insight.window_days,
        "metric_summaries": [
            asdict(ms) for ms in insight.metric_summaries
        ],
        "correlations": [
            {
                "metric_x": c.metric_x,
                "metric_y": c.metric_y,
                "r": c.r,
                "n": c.n,
                "strength": c.strength,
                "direction": c.direction,
                "is_reliable": c.is_reliable,
            }
            for c in insight.correlations
        ],
    }

