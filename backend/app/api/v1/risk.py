"""
Risk assessment API endpoint.

Surfaces proactive risk alerts from the RiskWindowDetector engine.
Fetches recent metric values and baselines from the database,
then runs multi-signal risk scoring.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Tuple

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth_mode import get_request_user_id
from app.api.consent_gate import require_user_and_consent
from app.api.router_factory import make_v1_router
from app.core.database import get_db
from app.domain.models.baseline import Baseline
from app.engine.forecasting.risk_detector import RiskWindowDetector
from app.engine.signal_builder import fetch_recent_values

logger = logging.getLogger(__name__)

router = make_v1_router(prefix="/api/v1/risk", tags=["risk"])

# Metrics used by the risk detector
RISK_METRICS = [
    "hrv_rmssd_ms",
    "resting_heart_rate_bpm",
    "sleep_duration_minutes",
    "sleep_efficiency_pct",
    "respiratory_rate_brpm",
    "subjective_energy",
    "subjective_stress",
]


def _fetch_baselines(db: Session, user_id: int) -> Dict[str, Tuple[float, float]]:
    """Fetch personal baselines for risk-relevant metrics."""
    rows = (
        db.query(Baseline)
        .filter(
            Baseline.user_id == user_id,
            Baseline.metric_type.in_(RISK_METRICS),
        )
        .all()
    )
    return {r.metric_type: (r.mean, r.std) for r in rows if r.mean is not None}


def _fetch_recent(db: Session, user_id: int) -> Dict[str, float]:
    """Fetch the most recent value for each risk-relevant metric."""
    recent: Dict[str, float] = {}
    for metric_key in RISK_METRICS:
        values = fetch_recent_values(
            db=db, user_id=user_id, metric_key=metric_key, window_days=3
        )
        if values:
            recent[metric_key] = values[-1]  # Most recent
    return recent


def _fetch_history(db: Session, user_id: int) -> Dict[str, List[float]]:
    """Fetch 7-day history for trend detection."""
    history: Dict[str, List[float]] = {}
    for metric_key in RISK_METRICS:
        values = fetch_recent_values(
            db=db, user_id=user_id, metric_key=metric_key, window_days=7
        )
        if len(values) >= 3:
            history[metric_key] = values
    return history


@router.get("/assess")
def assess_risk(
    user_id: int = Depends(require_user_and_consent),
    db: Session = Depends(get_db),
):
    """
    Assess all risk types for the authenticated user.

    Returns risk assessments sorted by score (highest first).
    Requires: Authentication + valid consent.
    """
    try:
        baselines = _fetch_baselines(db, user_id)
        recent = _fetch_recent(db, user_id)
        history = _fetch_history(db, user_id)

        if not recent or not baselines:
            return {
                "assessments": [],
                "message": "Insufficient data for risk assessment. More baseline data needed.",
            }

        detector = RiskWindowDetector()
        assessments = detector.detect_all(recent, baselines, history)

        return {
            "assessments": [
                {
                    "risk_type": a.risk_type,
                    "risk_level": a.risk_level.value,
                    "risk_score": a.risk_score,
                    "description": a.description,
                    "recommended_actions": a.recommended_actions,
                    "contributing_factors": [
                        {
                            "metric": f.metric,
                            "current_value": f.current_value,
                            "baseline_value": f.baseline_value,
                            "deviation_pct": f.deviation_pct,
                            "direction": f.direction,
                        }
                        for f in a.contributing_factors
                    ],
                }
                for a in assessments
            ],
        }
    except Exception as e:
        logger.error(
            "risk_assessment_failed",
            extra={"user_id": user_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Risk assessment failed: {e}")
