from __future__ import annotations

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.domain.models.health_data_point import HealthDataPoint

logger = logging.getLogger(__name__)


class SignalReconciliation:
    """
    Provider Reconciliation Layer.
    
    Problem solved: WHOOP says sleep improved, user says it didn't.
    
    Rules:
    - Wearables ≠ subjective truth
    - Labs ≠ symptoms
    - Conflicts are surfaced, not hidden
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def detect_conflict(
        self,
        user_id: int,
        metric_key: str,
        wearable_metric_key: Optional[str] = None,
        subjective_metric_key: Optional[str] = None,
        days: int = 14,
    ) -> Optional[Dict[str, Any]]:
        """
        Detect conflicts between wearable and subjective signals.
        
        Example:
        - metric_key: "sleep_quality"
        - wearable_metric_key: "sleep_duration" (if available)
        - subjective_metric_key: "sleep_quality" (user-reported)
        
        Returns conflict report if mismatch detected, None otherwise.
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get wearable data
        wearable_points = []
        if wearable_metric_key:
            wearable_points = (
                self.db.query(HealthDataPoint)
                .filter(
                    HealthDataPoint.user_id == user_id,
                    HealthDataPoint.metric_type == wearable_metric_key,
                    HealthDataPoint.source == "wearable",
                    HealthDataPoint.timestamp >= start_date,
                    HealthDataPoint.timestamp <= end_date,
                )
                .order_by(HealthDataPoint.timestamp.asc())
                .all()
            )
        
        # Get subjective data
        subjective_points = []
        if subjective_metric_key:
            subjective_points = (
                self.db.query(HealthDataPoint)
                .filter(
                    HealthDataPoint.user_id == user_id,
                    HealthDataPoint.metric_type == subjective_metric_key,
                    HealthDataPoint.source.in_(["manual", "questionnaire"]),
                    HealthDataPoint.timestamp >= start_date,
                    HealthDataPoint.timestamp <= end_date,
                )
                .order_by(HealthDataPoint.timestamp.asc())
                .all()
            )
        
        if not wearable_points or not subjective_points:
            return None  # Can't detect conflict without both
        
        # Compute trends
        wearable_trend = self._compute_trend(wearable_points)
        subjective_trend = self._compute_trend(subjective_points)
        
        # Check for conflict
        if wearable_trend["direction"] != subjective_trend["direction"]:
            return {
                "metric": metric_key,
                "conflict": True,
                "wearable_trend": wearable_trend["direction"],
                "wearable_metric": wearable_metric_key,
                "subjective_trend": subjective_trend["direction"],
                "subjective_metric": subjective_metric_key,
                "wearable_change": wearable_trend["change_percent"],
                "subjective_change": subjective_trend["change_percent"],
                "resolution": "flag_for_user_review",
                "message": (
                    f"Your {wearable_metric_key or 'wearable'} metrics show {wearable_trend['direction']}, "
                    f"but you reported {subjective_trend['direction']} {subjective_metric_key or 'subjective experience'}. "
                    f"This mismatch matters."
                ),
            }
        
        return None
    
    def _compute_trend(self, points: List[HealthDataPoint]) -> Dict[str, Any]:
        """Compute trend direction and magnitude from data points."""
        if len(points) < 2:
            return {"direction": "insufficient_data", "change_percent": 0.0}
        
        # Split into first half and second half
        mid = len(points) // 2
        first_half = [p.value for p in points[:mid]]
        second_half = [p.value for p in points[mid:]]
        
        first_avg = sum(first_half) / len(first_half) if first_half else 0
        second_avg = sum(second_half) / len(second_half) if second_half else 0
        
        if first_avg == 0:
            change_percent = 0.0
        else:
            change_percent = ((second_avg - first_avg) / first_avg) * 100
        
        if abs(change_percent) < 5:
            direction = "stable"
        elif change_percent > 0:
            direction = "improving"
        else:
            direction = "worsening"
        
        return {
            "direction": direction,
            "change_percent": round(change_percent, 1),
        }
    
    def reconcile_for_insight(
        self,
        user_id: int,
        metric_key: str,
        days: int = 14,
    ) -> Dict[str, Any]:
        """
        Generate reconciliation report for an insight.
        
        Checks for conflicts between wearable and subjective data.
        """
        # Common mappings
        mappings = {
            "sleep_quality": {
                "wearable": "sleep_duration",
                "subjective": "sleep_quality",
            },
            "energy": {
                "wearable": "resting_hr",
                "subjective": "energy",
            },
        }
        
        mapping = mappings.get(metric_key)
        if not mapping:
            return {"conflict": False, "message": None}
        
        conflict = self.detect_conflict(
            user_id=user_id,
            metric_key=metric_key,
            wearable_metric_key=mapping.get("wearable"),
            subjective_metric_key=mapping.get("subjective"),
            days=days,
        )
        
        if conflict:
            return {
                "conflict": True,
                "message": conflict["message"],
                "details": conflict,
            }
        
        return {"conflict": False, "message": None}

