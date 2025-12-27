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
            # Insight model uses generated_at (not created_at)
            dup_ts = getattr(recent_duplicate, "generated_at", None) or getattr(recent_duplicate, "created_at", None)
            if dup_ts is None:
                return True, "Duplicate check failed (missing timestamp)"
            days_since = (today - dup_ts).days
            if days_since < self.MIN_DAYS_BETWEEN_REPEATS:
                # Always suppress duplicates within the repeat window
                return True, f"Duplicate insight for same metric within {days_since} days (min: {self.MIN_DAYS_BETWEEN_REPEATS})"

        # NOTE: Daily cap is enforced as a batch in loop_runner (top-N by confidence),
        # so we don't do per-item cap checks here (it would be order-dependent and
        # would count newly-created insights in the same run).

        return False, None
    
    def _find_recent_duplicate(
        self,
        user_id: int,
        insight: Insight,
        today: datetime,
    ) -> Optional[Insight]:
        """Find a recent duplicate insight"""
        # Metric key is stored in metadata_json for this model
        metric_key: Optional[str] = None
        try:
            meta = insight.metadata_json
            if isinstance(meta, dict):
                metric_key = meta.get("metric_key")
            elif isinstance(meta, str) and meta:
                import json
                metric_key = json.loads(meta).get("metric_key")
        except Exception:
            metric_key = None
        
        if not metric_key:
            return None
        
        # Look for recent insights within window; filter by metric_key in metadata_json (Python-side)
        cutoff = today - timedelta(days=self.MIN_DAYS_BETWEEN_REPEATS)
        
        candidates = (
            self.db.query(Insight)
            .filter(
                Insight.user_id == user_id,
                Insight.generated_at >= cutoff,
                Insight.id != insight.id,  # Exclude self
            )
            .order_by(Insight.generated_at.desc())
            .limit(50)
            .all()
        )

        def _extract_metric_key(m: object) -> Optional[str]:
            try:
                meta = getattr(m, "metadata_json", None)
                if isinstance(meta, dict):
                    return meta.get("metric_key")
                if isinstance(meta, str) and meta:
                    import json
                    return json.loads(meta).get("metric_key")
            except Exception:
                return None
            return None

        for cand in candidates:
            if _extract_metric_key(cand) == metric_key:
                return cand
        return None
    
    def _count_today_insights(self, user_id: int, today: datetime) -> int:
        """Count insights surfaced today"""
        start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        return (
            self.db.query(Insight)
            .filter(
                Insight.user_id == user_id,
                Insight.generated_at >= start_of_day,
                Insight.generated_at < end_of_day,
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

