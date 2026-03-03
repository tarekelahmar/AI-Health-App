"""
Bridge module: syncs DailyCheckIn subjective data into HealthDataPoint rows.

This allows journal entries to flow into the standard metric pipeline
(baselines, insights, forecasts) without duplicating logic.

Scale conversion: DailyCheckIn uses 0-10, metric registry uses 1-5.
Formula: metric_value = 1 + (checkin_value / 10) * 4
  - checkin 0  -> metric 1.0
  - checkin 5  -> metric 3.0
  - checkin 10 -> metric 5.0
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.domain.models.daily_checkin import DailyCheckIn
from app.domain.models.health_data_point import HealthDataPoint

logger = logging.getLogger(__name__)

# Maps DailyCheckIn field name -> metric_type key in registry
CHECKIN_METRIC_MAP = {
    "energy": "energy",
    "mood": "mood",
    "stress": "stress",
    "sleep_quality": "sleep_quality",
    "focus": "focus",
}

# Units for each metric
METRIC_UNITS = {
    "energy": "score_1_5",
    "mood": "score_1_5",
    "stress": "score_1_5",
    "sleep_quality": "score_1_5",
    "focus": "score_1_5",
}


def _convert_0_10_to_1_5(value: int) -> float:
    """Convert 0-10 check-in scale to 1-5 metric scale."""
    return 1.0 + (value / 10.0) * 4.0


def sync_checkin_to_datapoints(db: Session, checkin: DailyCheckIn) -> int:
    """
    Sync a DailyCheckIn's subjective fields into HealthDataPoint rows.

    For each non-null subjective field, upserts a HealthDataPoint with
    the converted 1-5 scale value. Idempotent — safe to call multiple
    times for the same check-in.

    Returns the number of data points upserted.
    """
    if not checkin or not checkin.user_id:
        return 0

    # Use noon on the check-in date as the timestamp
    ts = datetime.combine(checkin.checkin_date, datetime.min.time().replace(hour=12))

    count = 0
    for field_name, metric_key in CHECKIN_METRIC_MAP.items():
        raw_value = getattr(checkin, field_name, None)
        if raw_value is None:
            continue

        converted_value = _convert_0_10_to_1_5(raw_value)

        # Find existing data point for this user/metric/date
        existing = (
            db.query(HealthDataPoint)
            .filter(
                HealthDataPoint.user_id == checkin.user_id,
                HealthDataPoint.metric_type == metric_key,
                HealthDataPoint.source == "checkin",
                HealthDataPoint.timestamp >= datetime.combine(checkin.checkin_date, datetime.min.time()),
                HealthDataPoint.timestamp < datetime.combine(checkin.checkin_date, datetime.max.time()),
            )
            .first()
        )

        if existing:
            existing.value = converted_value
            existing.timestamp = ts
        else:
            dp = HealthDataPoint(
                user_id=checkin.user_id,
                metric_type=metric_key,
                value=converted_value,
                unit=METRIC_UNITS[metric_key],
                timestamp=ts,
                source="checkin",
            )
            db.add(dp)

        count += 1

    if count > 0:
        db.commit()
        logger.info(
            "checkin_bridge_synced",
            extra={
                "user_id": checkin.user_id,
                "checkin_date": str(checkin.checkin_date),
                "metrics_synced": count,
            },
        )

    return count
