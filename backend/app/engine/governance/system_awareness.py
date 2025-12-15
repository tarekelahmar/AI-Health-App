from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.domain.models.insight import Insight
from app.domain.models.personal_driver import PersonalDriver
from app.domain.models.evaluation_result import EvaluationResult


@dataclass
class SystemAwarenessSignal:
    """Signal about system self-awareness (uncertainty, conflicts, etc.)"""
    type: str  # "insufficient_data" | "conflicting_signals" | "too_many_changes" | "high_uncertainty"
    message: str
    details: Dict[str, Any]
    severity: str  # "info" | "warning" | "error"


class SystemAwarenessService:
    """
    System Self-Awareness
    
    Explicitly surfaces:
    - "Insufficient data"
    - "Conflicting signals"
    - "Too many changes to isolate effect"
    
    This builds trust.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def check_insufficient_data(
        self,
        user_id: int,
        metric_key: str,
        window_days: int = 14,
    ) -> Optional[SystemAwarenessSignal]:
        """Check if there's insufficient data for a metric"""
        from app.domain.repositories.health_data_repository import HealthDataRepository
        
        repo = HealthDataRepository(self.db)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=window_days)
        
        points = repo.list_for_user_in_range(
            user_id=user_id,
            data_type=metric_key,
            start=start_date,
            end=end_date,
        )
        
        if len(points) < 5:  # Minimum threshold
            return SystemAwarenessSignal(
                type="insufficient_data",
                message=f"Insufficient data for {metric_key}. Only {len(points)} data points in the last {window_days} days.",
                details={
                    "metric_key": metric_key,
                    "data_points": len(points),
                    "window_days": window_days,
                    "minimum_required": 5,
                },
                severity="warning",
            )
        
        return None
    
    def check_conflicting_signals(
        self,
        user_id: int,
        metric_key: str,
    ) -> Optional[SystemAwarenessSignal]:
        """Check for conflicting signals (e.g., wearable vs subjective)"""
        # Get recent insights for this metric
        insights = (
            self.db.query(Insight)
            .filter(
                Insight.user_id == user_id,
                Insight.metric_key == metric_key,
            )
            .order_by(Insight.created_at.desc())
            .limit(10)
            .all()
        )
        
        if len(insights) < 2:
            return None
        
        # Check for conflicting directions
        directions = []
        for insight in insights:
            evidence = insight.metadata_json if isinstance(insight.metadata_json, dict) else {}
            direction = evidence.get("direction")
            if direction:
                directions.append(direction)
        
        if len(set(directions)) > 1:  # Multiple different directions
            return SystemAwarenessSignal(
                type="conflicting_signals",
                message=f"Conflicting signals detected for {metric_key}. Some insights suggest improvement, others suggest decline.",
                details={
                    "metric_key": metric_key,
                    "directions": list(set(directions)),
                    "insight_count": len(insights),
                },
                severity="warning",
            )
        
        return None
    
    def check_too_many_changes(
        self,
        user_id: int,
        window_days: int = 14,
    ) -> Optional[SystemAwarenessSignal]:
        """Check if too many simultaneous changes make it hard to isolate effects"""
        # Count active interventions
        from app.domain.models.experiment import Experiment
        
        active_experiments = (
            self.db.query(Experiment)
            .filter(
                Experiment.user_id == user_id,
                Experiment.status == "active",
            )
            .count()
        )
        
        # Count recent insights
        cutoff = datetime.utcnow() - timedelta(days=window_days)
        recent_insights = (
            self.db.query(Insight)
            .filter(
                Insight.user_id == user_id,
                Insight.created_at >= cutoff,
            )
            .count()
        )
        
        if active_experiments > 3 or recent_insights > 15:
            return SystemAwarenessSignal(
                type="too_many_changes",
                message="Multiple simultaneous changes detected. It may be difficult to isolate which factor is causing observed effects.",
                details={
                    "active_experiments": active_experiments,
                    "recent_insights": recent_insights,
                    "window_days": window_days,
                },
                severity="info",
            )
        
        return None
    
    def check_high_uncertainty(
        self,
        user_id: int,
        metric_key: str,
    ) -> Optional[SystemAwarenessSignal]:
        """Check if uncertainty is high for a metric"""
        # Get recent personal drivers
        drivers = (
            self.db.query(PersonalDriver)
            .filter(
                PersonalDriver.user_id == user_id,
                PersonalDriver.outcome_metric == metric_key,
            )
            .order_by(PersonalDriver.created_at.desc())
            .limit(5)
            .all()
        )
        
        if not drivers:
            return None
        
        # Check average confidence
        avg_confidence = sum(d.confidence for d in drivers) / len(drivers)
        
        if avg_confidence < 0.5:
            return SystemAwarenessSignal(
                type="high_uncertainty",
                message=f"High uncertainty for {metric_key}. Confidence scores are low, suggesting limited or conflicting data.",
                details={
                    "metric_key": metric_key,
                    "average_confidence": avg_confidence,
                    "driver_count": len(drivers),
                },
                severity="info",
            )
        
        return None
    
    def get_awareness_signals(
        self,
        user_id: int,
        metric_key: Optional[str] = None,
    ) -> List[SystemAwarenessSignal]:
        """Get all system awareness signals for a user"""
        signals: List[SystemAwarenessSignal] = []
        
        if metric_key:
            # Check specific metric
            insufficient = self.check_insufficient_data(user_id, metric_key)
            if insufficient:
                signals.append(insufficient)
            
            conflicting = self.check_conflicting_signals(user_id, metric_key)
            if conflicting:
                signals.append(conflicting)
            
            uncertainty = self.check_high_uncertainty(user_id, metric_key)
            if uncertainty:
                signals.append(uncertainty)
        else:
            # Check general system state
            too_many = self.check_too_many_changes(user_id)
            if too_many:
                signals.append(too_many)
        
        return signals

