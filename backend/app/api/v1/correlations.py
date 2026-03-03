"""
Cross-domain correlations API endpoint.

Surfaces relationships between health domains discovered by the
cross-domain correlator engine.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth_mode import get_request_user_id
from app.api.consent_gate import require_user_and_consent
from app.api.router_factory import make_v1_router
from app.core.database import get_db
from app.domain.health_domains import HealthDomainKey
from app.engine.reasoning.cross_domain_correlator import cross_domain_scan
from app.engine.signal_builder import fetch_recent_values

logger = logging.getLogger(__name__)

router = make_v1_router(prefix="/api/v1/correlations", tags=["correlations"])

# Map metrics to their domain
METRIC_DOMAIN_MAP = {
    "sleep_duration_minutes": HealthDomainKey.SLEEP,
    "sleep_efficiency_pct": HealthDomainKey.SLEEP,
    "hrv_rmssd_ms": HealthDomainKey.STRESS_NERVOUS_SYSTEM,
    "resting_heart_rate_bpm": HealthDomainKey.CARDIOMETABOLIC,
    "respiratory_rate_brpm": HealthDomainKey.INFLAMMATION_IMMUNE,
    "subjective_energy": HealthDomainKey.ENERGY_FATIGUE,
    "subjective_stress": HealthDomainKey.STRESS_NERVOUS_SYSTEM,
}


@router.get("/cross-domain")
def get_cross_domain_correlations(
    user_id: int = Depends(require_user_and_consent),
    db: Session = Depends(get_db),
):
    """
    Scan for cross-domain correlations in the user's data.

    Finds relationships like "sleep quality correlates with HRV 1 day later".
    """
    try:
        # Fetch 30 days of data for each metric
        metric_series = {}
        for metric_key in METRIC_DOMAIN_MAP:
            values = fetch_recent_values(
                db=db, user_id=user_id, metric_key=metric_key, window_days=30
            )
            if len(values) >= 14:
                metric_series[metric_key] = values

        if len(metric_series) < 2:
            return {
                "correlations": [],
                "message": "Need at least 2 metrics with 14+ data points for cross-domain analysis.",
            }

        correlations = cross_domain_scan(
            metric_series=metric_series,
            metric_to_domain=METRIC_DOMAIN_MAP,
            max_lag=5,
        )

        return {
            "correlations": [
                {
                    "source_domain": c.source_domain.value,
                    "target_domain": c.target_domain.value,
                    "metric_x": c.metric_x,
                    "metric_y": c.metric_y,
                    "best_lag_days": c.best_lag_days,
                    "correlation": round(c.correlation, 3),
                    "p_value": round(c.p_value, 4),
                    "mechanism": c.mechanism,
                    "confidence": round(c.confidence, 3),
                }
                for c in correlations
            ],
        }
    except Exception as e:
        logger.error(
            "cross_domain_scan_failed",
            extra={"user_id": user_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Cross-domain scan failed: {e}")
