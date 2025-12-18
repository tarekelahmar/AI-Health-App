from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List

from app.domain.metrics.registry import get_metric_spec


@dataclass
class QualityAssessment:
    """
    Lightweight per-value quality assessment.

    Phase 1.3 scope:
    - validity: range check based on registry valid_range
    - timeliness_seconds: ingest_time - measurement_time
    - completeness / consistency / anomaly are placeholders for later phases
    """

    completeness: float            # 0–1 coverage in window
    validity: bool                 # within metric range?
    timeliness_seconds: int        # ingest timestamp - measure timestamp
    consistency_flag: bool         # future: provider agreement
    anomaly_flag: bool             # statistical anomaly detection placeholder
    score: float                   # 0–1 overall quality score


class DataQualityService:
    """
    Inline data quality assessment for metric ingestion.

    Design notes:
    - Pure Python (no numpy/pandas) to keep this cheap and easy to reason about.
    - NEVER rejects data on its own; only tags rows so governance code can act.
    - Scoring is intentionally simple; later phases can refine weights/fields.
    """

    def assess_single_value(
        self,
        metric_key: str,
        timestamp: datetime,
        value: float,
        ingested_at: datetime,
    ) -> QualityAssessment:
        """
        Quick inline quality assessment.

        - validity from metric spec valid_range
        - timeliness = ingest_time - timestamp (seconds)
        - completeness + anomaly_flag determined later (placeholder)
        """

        spec = get_metric_spec(metric_key)

        lo, hi = spec.valid_range
        validity = (lo <= value <= hi)
        timeliness = int((ingested_at - timestamp).total_seconds())

        # Initial scoring logic: validity + timeliness weighting only.
        # More sophisticated scoring will come in a later phase.
        base_score = 1.0
        if not validity:
            base_score -= 0.5
        if timeliness > 86400:  # older than 24h
            base_score -= 0.2

        if base_score < 0:
            base_score = 0.0

        return QualityAssessment(
            completeness=1.0,          # future computation
            validity=validity,
            timeliness_seconds=timeliness,
            consistency_flag=False,    # Phase 4
            anomaly_flag=False,        # Phase 2
            score=base_score,
        )

    def assess_coverage(
        self,
        timestamps: List[datetime],
        expected_per_day: int = 1,
        window_days: int = 7,
    ) -> float:
        """
        Computes simple coverage rate over a sliding time window.
        """
        if not timestamps:
            return 0.0

        window_start = max(timestamps) - timedelta(days=window_days)
        count = sum(1 for t in timestamps if t >= window_start)
        expected_count = expected_per_day * window_days

        if expected_count <= 0:
            return 1.0

        cov = count / expected_count
        return min(cov, 1.0)


