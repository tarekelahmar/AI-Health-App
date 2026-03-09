"""
Forecasts API endpoint.

Surfaces metric predictions from the HealthForecaster engine
with confidence intervals for fan chart visualization.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth_mode import get_request_user_id
from app.api.consent_gate import require_user_and_consent
from app.api.router_factory import make_v1_router
from app.core.database import get_db
from app.domain.models.health_data_point import HealthDataPoint
from app.engine.forecasting.predictor import HealthForecaster

logger = logging.getLogger(__name__)

router = make_v1_router(prefix="/api/v1/forecasts", tags=["forecasts"])

FORECASTABLE_METRICS = [
    "hrv_rmssd_ms",
    "resting_heart_rate_bpm",
    "sleep_duration_minutes",
    "sleep_efficiency_pct",
    "respiratory_rate_brpm",
    "subjective_energy",
    "subjective_stress",
]


@router.get("/{metric_key}")
def get_forecast(
    metric_key: str,
    horizon: int = Query(7, ge=1, le=7),
    user_id: int = Depends(require_user_and_consent),
    db: Session = Depends(get_db),
):
    """
    Get forecast for a single metric with confidence intervals.

    Returns historical data + predicted values + CI bands for fan chart rendering.
    """
    if metric_key not in FORECASTABLE_METRICS:
        raise HTTPException(
            status_code=400,
            detail=f"Metric '{metric_key}' is not forecastable. Available: {FORECASTABLE_METRICS}",
        )

    try:
        # Fetch historical data (60 days for context, last 30 for training)
        since = date.today() - timedelta(days=60)
        rows = (
            db.query(HealthDataPoint.timestamp, HealthDataPoint.value)
            .filter(
                HealthDataPoint.user_id == user_id,
                HealthDataPoint.metric_type == metric_key,
                HealthDataPoint.timestamp >= since.isoformat(),
            )
            .order_by(HealthDataPoint.timestamp.asc())
            .all()
        )

        if len(rows) < 14:
            return {
                "metric_key": metric_key,
                "historical": [],
                "predictions": [],
                "message": f"Need at least 14 data points for forecasting, have {len(rows)}.",
            }

        values = [r.value for r in rows if r.value is not None]
        dates = [r.timestamp.date() if hasattr(r.timestamp, 'date') else r.timestamp for r in rows if r.value is not None]

        forecaster = HealthForecaster()
        forecast = forecaster.forecast(values, dates, metric_key, horizon=horizon)

        if forecast is None:
            return {
                "metric_key": metric_key,
                "historical": [],
                "predictions": [],
                "message": "Insufficient data for forecast.",
            }

        # Build historical data for chart
        historical = [
            {"date": d.isoformat(), "value": round(v, 2)}
            for d, v in zip(dates[-30:], values[-30:])
        ]

        # Build predictions with CIs
        predictions = [
            {
                "date": p.date.isoformat(),
                "predicted": round(p.predicted, 2),
                "ci_80_low": round(p.ci_80[0], 2),
                "ci_80_high": round(p.ci_80[1], 2),
                "ci_95_low": round(p.ci_95[0], 2),
                "ci_95_high": round(p.ci_95[1], 2),
            }
            for p in forecast.predictions
        ]

        return {
            "metric_key": metric_key,
            "historical": historical,
            "predictions": predictions,
            "metadata": {
                "training_points": forecast.metadata.get("training_points", len(values)),
                "method": forecast.metadata.get("method", "holt_smoothing"),
                "horizon": horizon,
            },
        }
    except Exception as e:
        logger.error(
            "forecast_failed",
            extra={"user_id": user_id, "metric_key": metric_key, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Forecast failed: {e}")


@router.get("")
def get_multi_forecast(
    user_id: int = Depends(require_user_and_consent),
    db: Session = Depends(get_db),
):
    """
    Get forecasts for all forecastable metrics (batch endpoint).
    Returns a summary with the latest value and forecast direction for each metric.
    """
    results = []
    for metric_key in FORECASTABLE_METRICS:
        try:
            since = date.today() - timedelta(days=30)
            rows = (
                db.query(HealthDataPoint.timestamp, HealthDataPoint.value)
                .filter(
                    HealthDataPoint.user_id == user_id,
                    HealthDataPoint.metric_type == metric_key,
                    HealthDataPoint.timestamp >= since.isoformat(),
                )
                .order_by(HealthDataPoint.timestamp.asc())
                .all()
            )

            values = [r.value for r in rows if r.value is not None]
            if len(values) < 14:
                results.append({
                    "metric_key": metric_key,
                    "available": False,
                    "current_value": values[-1] if values else None,
                })
                continue

            dates = [
                r.timestamp.date() if hasattr(r.timestamp, 'date') else r.timestamp
                for r in rows if r.value is not None
            ]
            forecaster = HealthForecaster()
            forecast = forecaster.forecast(values, dates, metric_key, horizon=3)

            if forecast and forecast.predictions:
                direction = "up" if forecast.predictions[-1].predicted > values[-1] else "down"
                if abs(forecast.predictions[-1].predicted - values[-1]) / (abs(values[-1]) + 1e-10) < 0.02:
                    direction = "stable"

                results.append({
                    "metric_key": metric_key,
                    "available": True,
                    "current_value": round(values[-1], 2),
                    "forecast_3d": round(forecast.predictions[-1].predicted, 2),
                    "direction": direction,
                })
            else:
                results.append({
                    "metric_key": metric_key,
                    "available": False,
                    "current_value": values[-1] if values else None,
                })
        except Exception:
            results.append({
                "metric_key": metric_key,
                "available": False,
            })

    return {"forecasts": results}
