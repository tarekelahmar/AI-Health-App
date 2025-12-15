from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from app.providers.base import NormalizedPoint

logger = logging.getLogger(__name__)


@dataclass
class DataQualityScore:
    """Data quality score breakdown (0-1 for each dimension)"""
    overall: float
    completeness: float
    consistency: float
    timeliness: float
    stability: float
    duplication: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "overall": self.overall,
            "completeness": self.completeness,
            "consistency": self.consistency,
            "timeliness": self.timeliness,
            "stability": self.stability,
            "duplication": self.duplication,
        }


class DataQualityService:
    """
    Data Quality Scoring Engine.
    
    Each batch ingestion produces a Data Quality Report.
    Dimensions scored 0-1:
    - Completeness – % expected fields present
    - Consistency – unit & range adherence
    - Timeliness – delay from event → ingestion
    - Stability – abnormal variance spikes
    - Duplication – repeated timestamps
    """
    
    MIN_INSIGHT_QUALITY = 0.6  # Hard stop: insights cannot use data below this
    
    def __init__(self):
        pass
    
    def score_completeness(self, points: List[NormalizedPoint]) -> float:
        """
        Completeness: % expected fields present.
        Expected fields: metric_type, value, unit, timestamp, source
        """
        if not points:
            return 0.0
        
        total_fields = len(points) * 5  # 5 expected fields per point
        present_fields = 0
        
        for p in points:
            if p.metric_type:
                present_fields += 1
            if p.value is not None:
                present_fields += 1
            if p.unit:
                present_fields += 1
            if p.timestamp:
                present_fields += 1
            if p.source:
                present_fields += 1
        
        return present_fields / total_fields if total_fields > 0 else 0.0
    
    def score_consistency(self, points: List[NormalizedPoint], metric_specs: Dict[str, Any]) -> float:
        """
        Consistency: unit & range adherence.
        Checks if units match expected and values are within valid ranges.
        """
        if not points:
            return 0.0
        
        consistent = 0
        for p in points:
            try:
                spec = metric_specs.get(p.metric_type)
                if not spec:
                    continue  # Skip if no spec (will be rejected elsewhere)
                
                # Unit check
                if p.unit != spec.unit:
                    continue
                
                # Range check
                if spec.min_value is not None and p.value < spec.min_value:
                    continue
                if spec.max_value is not None and p.value > spec.max_value:
                    continue
                
                consistent += 1
            except Exception:
                continue
        
        return consistent / len(points) if points else 0.0
    
    def score_timeliness(self, points: List[NormalizedPoint], ingestion_time: datetime) -> float:
        """
        Timeliness: delay from event → ingestion.
        Penalizes data that is too old (e.g., > 7 days old).
        """
        if not points:
            return 0.0
        
        timely = 0
        for p in points:
            age_days = (ingestion_time - p.timestamp).total_seconds() / 86400
            # Data < 7 days old is considered timely
            if age_days <= 7:
                timely += 1
        
        return timely / len(points) if points else 0.0
    
    def score_stability(self, points: List[NormalizedPoint]) -> float:
        """
        Stability: abnormal variance spikes.
        Checks for sudden large changes that might indicate data errors.
        """
        if len(points) < 2:
            return 1.0  # Can't assess stability with < 2 points
        
        # Sort by timestamp
        sorted_points = sorted(points, key=lambda p: p.timestamp)
        
        # Calculate relative changes
        changes = []
        for i in range(1, len(sorted_points)):
            if sorted_points[i-1].value == 0:
                continue
            change = abs((sorted_points[i].value - sorted_points[i-1].value) / sorted_points[i-1].value)
            changes.append(change)
        
        if not changes:
            return 1.0
        
        # If > 50% change, flag as potentially unstable
        # Score decreases as more points have large changes
        stable_count = sum(1 for c in changes if c <= 0.5)
        return stable_count / len(changes) if changes else 1.0
    
    def score_duplication(self, points: List[NormalizedPoint]) -> float:
        """
        Duplication: repeated timestamps.
        Penalizes duplicate timestamps (same metric, same timestamp).
        """
        if not points:
            return 1.0
        
        seen = set()
        duplicates = 0
        
        for p in points:
            key = (p.metric_type, p.timestamp.isoformat())
            if key in seen:
                duplicates += 1
            else:
                seen.add(key)
        
        unique = len(points) - duplicates
        return unique / len(points) if points else 1.0
    
    def compute_quality_score(
        self,
        points: List[NormalizedPoint],
        metric_specs: Dict[str, Any],
        ingestion_time: Optional[datetime] = None,
    ) -> DataQualityScore:
        """
        Compute overall quality score for a batch of points.
        """
        if ingestion_time is None:
            ingestion_time = datetime.utcnow()
        
        completeness = self.score_completeness(points)
        consistency = self.score_consistency(points, metric_specs)
        timeliness = self.score_timeliness(points, ingestion_time)
        stability = self.score_stability(points)
        duplication = self.score_duplication(points)
        
        # Overall score: weighted average (completeness and consistency are most important)
        overall = (
            completeness * 0.3 +
            consistency * 0.3 +
            timeliness * 0.15 +
            stability * 0.15 +
            duplication * 0.10
        )
        
        return DataQualityScore(
            overall=round(overall, 2),
            completeness=round(completeness, 2),
            consistency=round(consistency, 2),
            timeliness=round(timeliness, 2),
            stability=round(stability, 2),
            duplication=round(duplication, 2),
        )
    
    def should_reject_point(
        self,
        point: NormalizedPoint,
        metric_spec: Any,
        existing_timestamps: List[datetime],
    ) -> tuple[bool, Optional[str]]:
        """
        Quality Gates (Hard Stops).
        
        Returns (should_reject, reason) tuple.
        """
        # Missing metric spec
        if not metric_spec:
            return True, "Missing metric spec"
        
        # Unit mismatch
        if point.unit != metric_spec.unit:
            return True, f"Unit mismatch: got {point.unit}, expected {metric_spec.unit}"
        
        # Impossible values (out of range)
        if metric_spec.min_value is not None and point.value < metric_spec.min_value:
            return True, f"Value below min: {point.value} < {metric_spec.min_value}"
        if metric_spec.max_value is not None and point.value > metric_spec.max_value:
            return True, f"Value above max: {point.value} > {metric_spec.max_value}"
        
        # Duplicate timestamp
        point_ts = point.timestamp.replace(second=0, microsecond=0)  # Round to minute
        if any(ts.replace(second=0, microsecond=0) == point_ts for ts in existing_timestamps):
            return True, "Duplicate timestamp"
        
        return False, None

