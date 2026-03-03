"""
Regime classification API endpoint.

Surfaces the user's current health regime (normal, illness, stress, etc.)
from the RegimeClassifier engine.
"""
from __future__ import annotations

import logging
from typing import Dict, Tuple

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth_mode import get_request_user_id
from app.api.consent_gate import require_user_and_consent
from app.api.router_factory import make_v1_router
from app.core.database import get_db
from app.domain.models.baseline import Baseline
from app.engine.memory.regime_classifier import RegimeClassifier
from app.engine.signal_builder import fetch_recent_values

logger = logging.getLogger(__name__)

router = make_v1_router(prefix="/api/v1/regime", tags=["regime"])

# Metrics the regime classifier expects (different key names from risk detector)
REGIME_METRICS = {
    "resting_hr": "resting_heart_rate_bpm",
    "hrv_rmssd": "hrv_rmssd_ms",
    "sleep_duration": "sleep_duration_minutes",
    "energy": "subjective_energy",
    "stress": "subjective_stress",
}


@router.get("/current")
def get_current_regime(
    user_id: int = Depends(require_user_and_consent),
    db: Session = Depends(get_db),
):
    """
    Get the user's current health regime classification.

    Returns: regime type, confidence, contributing signals, and context.
    Requires: Authentication + valid consent.
    """
    try:
        # Fetch recent values using the DB metric keys
        features: Dict[str, float] = {}
        for regime_key, db_key in REGIME_METRICS.items():
            values = fetch_recent_values(
                db=db, user_id=user_id, metric_key=db_key, window_days=3
            )
            if values:
                features[regime_key] = values[-1]

        # Fetch baselines using DB metric keys, mapped to regime keys
        baselines: Dict[str, Tuple[float, float]] = {}
        baseline_rows = (
            db.query(Baseline)
            .filter(
                Baseline.user_id == user_id,
                Baseline.metric_type.in_(list(REGIME_METRICS.values())),
            )
            .all()
        )
        # Reverse map: db_key -> regime_key
        db_to_regime = {v: k for k, v in REGIME_METRICS.items()}
        for row in baseline_rows:
            regime_key = db_to_regime.get(row.metric_type)
            if regime_key and row.mean is not None:
                baselines[regime_key] = (row.mean, row.std)

        if not features:
            return {
                "regime": "normal",
                "confidence": 0.0,
                "contributing_signals": [],
                "context": "Insufficient data for regime classification.",
            }

        classifier = RegimeClassifier()
        classification = classifier.classify(features, baselines)

        return {
            "regime": classification.regime.value,
            "confidence": round(classification.confidence, 3),
            "contributing_signals": classification.contributing_signals,
            "context": classifier.get_regime_context(classification.regime),
            "date": classification.date.isoformat(),
        }
    except Exception as e:
        logger.error(
            "regime_classification_failed",
            extra={"user_id": user_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Regime classification failed: {e}"
        )
