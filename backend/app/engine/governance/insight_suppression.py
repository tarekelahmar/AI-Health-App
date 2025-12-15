from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.domain.models.decision_signal import DecisionSignal
from app.domain.models.insight import Insight

logger = logging.getLogger(__name__)


class InsightSuppressionService:
    """
    Insight Fatigue & Noise Control
    
    Suppression rules:
    - Do not repeat same insight < N days
    - Suppress low-confidence repeats
    - Cap daily surfaced insights
    """
    
    MIN_DAYS_BETWEEN_REPEATS = 7  # Don't show same insight within 7 days
    MIN_CONFIDENCE_FOR_REPEAT = 0.7  # Only repeat if confidence >= 0.7
    MAX_DAILY_INSIGHTS = 10  # Cap daily surfaced insights
    
    def __init__(self, db: Session):
        self.db = db
    
    def should_suppress_insight(
        self,
        user_id: int,
        insight: Insight,
        today: Optional[datetime] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Determine if an insight should be suppressed.
        
        Returns:
            (should_suppress, reason)
        """
        if today is None:
            today = datetime.utcnow()
        
        # Check for recent duplicate insights
        recent_duplicate = self._find_recent_duplicate(user_id, insight, today)
        if recent_duplicate:
            days_since = (today - recent_duplicate.created_at).days
            if days_since < self.MIN_DAYS_BETWEEN_REPEATS:
                if insight.confidence_score < self.MIN_CONFIDENCE_FOR_REPEAT:
                    return True, f"Low-confidence repeat (confidence={insight.confidence_score:.2f}) within {days_since} days"
                # High confidence repeats are allowed after MIN_DAYS_BETWEEN_REPEATS
                return False, None
        
        # Check daily cap
        today_count = self._count_today_insights(user_id, today)
        if today_count >= self.MAX_DAILY_INSIGHTS:
            # Suppress lowest confidence insights first
            if insight.confidence_score < 0.6:
                return True, f"Daily cap reached ({today_count} insights today), suppressing low-confidence"
        
        return False, None
    
    def _find_recent_duplicate(
        self,
        user_id: int,
        insight: Insight,
        today: datetime,
    ) -> Optional[Insight]:
        """Find a recent duplicate insight"""
        # Check for insights with same metric_key and similar title/description
        metric_key = getattr(insight, "metric_key", None) or (
            insight.metadata_json.get("metric_key") if isinstance(insight.metadata_json, dict) else None
        )
        
        if not metric_key:
            return None
        
        # Look for recent insights with same metric
        cutoff = today - timedelta(days=self.MIN_DAYS_BETWEEN_REPEATS)
        
        recent = (
            self.db.query(Insight)
            .filter(
                Insight.user_id == user_id,
                Insight.metric_key == metric_key,
                Insight.created_at >= cutoff,
                Insight.id != insight.id,  # Exclude self
            )
            .order_by(Insight.created_at.desc())
            .first()
        )
        
        return recent
    
    def _count_today_insights(self, user_id: int, today: datetime) -> int:
        """Count insights surfaced today"""
        start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        return (
            self.db.query(Insight)
            .filter(
                Insight.user_id == user_id,
                Insight.created_at >= start_of_day,
                Insight.created_at < end_of_day,
            )
            .count()
        )
    
    def mark_suppressed(
        self,
        user_id: int,
        source_type: str,
        source_id: int,
        reason: str,
        suppress_until: Optional[datetime] = None,
    ) -> None:
        """Mark a signal as suppressed"""
        if suppress_until is None:
            suppress_until = datetime.utcnow() + timedelta(days=self.MIN_DAYS_BETWEEN_REPEATS)
        
        signal = DecisionSignal(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            level=1,  # Default level
            level_name="observational",
            confidence=0.0,
            evidence_count=0,
            is_suppressed=True,
            suppression_reason=reason,
            suppression_until=suppress_until,
        )
        self.db.add(signal)
        self.db.commit()

