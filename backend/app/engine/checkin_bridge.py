"""
Bridge module: syncs DailyCheckIn subjective data into HealthDataPoint rows.

This allows journal entries to flow into the standard metric pipeline
(baselines, insights, forecasts) without duplicating logic.

Supports both V1 and V2 check-in formats:

V2 (1.0-10.0 float, step 0.5):
  Formula: metric_value = 1 + ((value - 1) / 9) * 4
    - checkin 1.0  -> metric 1.0
    - checkin 5.5  -> metric 3.0
    - checkin 10.0 -> metric 5.0

V1 (0-10 int, deprecated):
  Formula: metric_value = 1 + (value / 10) * 4
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

# ── V2 metric map (1.0-10.0 scale) ─────────────────────────────
V2_CHECKIN_METRIC_MAP = {
    "overall_wellbeing": "overall_wellbeing",
    "energy": "energy",
    "mood": "mood",
    "focus": "focus",
    "connection": "connection",
}

# ── V1 metric map (0-10 scale, deprecated) ──────────────────────
V1_CHECKIN_METRIC_MAP = {
    "energy": "energy",
    "mood": "mood",
    "stress": "stress",
    "sleep_quality": "sleep_quality",
    "focus": "focus",
}

# Units for all metrics
METRIC_UNITS = {
    "overall_wellbeing": "score_1_5",
    "energy": "score_1_5",
    "mood": "score_1_5",
    "focus": "score_1_5",
    "connection": "score_1_5",
    "stress": "score_1_5",
    "sleep_quality": "score_1_5",
}


def _convert_v2_to_1_5(value: float) -> float:
    """Convert V2 1.0-10.0 check-in scale to 1-5 metric scale."""
    return 1.0 + ((value - 1.0) / 9.0) * 4.0


def _convert_v1_to_1_5(value: int) -> float:
    """Convert V1 0-10 check-in scale to 1-5 metric scale."""
    return 1.0 + (value / 10.0) * 4.0


def sync_checkin_to_datapoints(db: Session, checkin: DailyCheckIn) -> int:
    """
    Sync a DailyCheckIn's subjective fields into HealthDataPoint rows.

    Detects V1 vs V2 entries by presence of overall_wellbeing field.
    For each non-null subjective field, upserts a HealthDataPoint with
    the converted 1-5 scale value. Idempotent — safe to call multiple
    times for the same check-in.

    Returns the number of data points upserted.
    """
    if not checkin or not checkin.user_id:
        return 0

    # Use noon on the check-in date as the timestamp
    ts = datetime.combine(checkin.checkin_date, datetime.min.time().replace(hour=12))

    # Detect V1 vs V2 by presence of overall_wellbeing
    is_v2 = checkin.overall_wellbeing is not None
    metric_map = V2_CHECKIN_METRIC_MAP if is_v2 else V1_CHECKIN_METRIC_MAP
    convert_fn = _convert_v2_to_1_5 if is_v2 else _convert_v1_to_1_5

    count = 0
    for field_name, metric_key in metric_map.items():
        raw_value = getattr(checkin, field_name, None)
        if raw_value is None:
            continue

        converted_value = convert_fn(raw_value)

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
                "version": "v2" if is_v2 else "v1",
            },
        )

    return count
