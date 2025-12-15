from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple, Optional, Literal
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.domain.models.daily_checkin import DailyCheckIn
from app.domain.models.adherence_event import AdherenceEvent
from app.domain.models.health_data_point import HealthDataPoint
from app.domain.models.driver_finding import DriverFinding
from app.domain.repositories.driver_finding_repository import DriverFindingRepository
from app.domain.metric_registry import METRICS, get_metric_spec

logger = logging.getLogger(__name__)


@dataclass
class DailyExposure:
    """Exposure data for a single day"""
    date: date
    behaviors: Dict[str, bool]  # from DailyCheckIn.behaviors_json
    interventions: Dict[str, bool]  # from AdherenceEvent


@dataclass
class DailyOutcome:
    """Outcome data for a single day"""
    date: date
    metric_values: Dict[str, float]  # metric_key -> aggregated value


class DriverDiscoveryService:
    """
    Deterministic driver discovery engine.
    
    Detects associations between behaviors/interventions and metric impacts.
    MUST NOT claim causality. Output must be phrased as "associated with".
    """
    
    MIN_EXPOSED_DAYS = 6
    MIN_TOTAL_DAYS = 14
    MIN_COVERAGE = 0.6
    
    def __init__(self, db: Session):
        self.db = db
        self.finding_repo = DriverFindingRepository(db)
    
    def discover_drivers(
        self,
        user_id: int,
        window_days: int = 28,
        lags: Tuple[int, ...] = (0, 1, 2, 3),
        max_findings: int = 50,
    ) -> List[DriverFinding]:
        """
        Discover driver associations for a user.
        
        Args:
            user_id: User ID
            window_days: Number of days to analyze
            lags: Lag days to test (0..3)
            max_findings: Maximum number of findings to return
            
        Returns:
            List of DriverFinding objects, sorted by confidence * abs(effect_size)
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=window_days)
        
        # Build daily exposure table
        exposures = self._build_exposure_table(user_id, start_date, end_date)
        
        # Build daily outcome table
        outcomes = self._build_outcome_table(user_id, start_date, end_date)
        
        findings: List[DriverFinding] = []
        
        # Get all unique exposure keys
        exposure_keys = set()
        for exp in exposures.values():
            exposure_keys.update(exp.behaviors.keys())
            exposure_keys.update(exp.interventions.keys())
        
        # Get all unique metric keys from outcomes
        metric_keys = set()
        for outcome in outcomes.values():
            metric_keys.update(outcome.metric_values.keys())
        
        # For each exposure_key x metric_key x lag
        for exposure_key in exposure_keys:
            # Determine exposure type
            exposure_type = "behavior"
            for exp in exposures.values():
                if exposure_key in exp.interventions:
                    exposure_type = "intervention"
                    break
            
            for metric_key in metric_keys:
                if metric_key not in METRICS:
                    continue  # Skip unknown metrics
                
                for lag_days in lags:
                    finding = self._compute_association(
                        user_id=user_id,
                        exposure_key=exposure_key,
                        exposure_type=exposure_type,
                        metric_key=metric_key,
                        lag_days=lag_days,
                        exposures=exposures,
                        outcomes=outcomes,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    
                    if finding:
                        findings.append(finding)
        
        # Sort by confidence * abs(effect_size)
        findings.sort(key=lambda f: f.confidence * abs(f.effect_size), reverse=True)
        
        # Upsert top findings
        for finding in findings[:max_findings]:
            self.finding_repo.upsert_finding(finding)
        
        return findings[:max_findings]
    
    def _build_exposure_table(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> Dict[date, DailyExposure]:
        """Build daily exposure table from check-ins and adherence events"""
        exposures: Dict[date, DailyExposure] = {}
        
        # Initialize all dates
        current = start_date
        while current <= end_date:
            exposures[current] = DailyExposure(
                date=current,
                behaviors={},
                interventions={},
            )
            current += timedelta(days=1)
        
        # Load check-ins
        checkins = (
            self.db.query(DailyCheckIn)
            .filter(
                DailyCheckIn.user_id == user_id,
                DailyCheckIn.checkin_date >= start_date,
                DailyCheckIn.checkin_date <= end_date,
            )
            .all()
        )
        
        for checkin in checkins:
            if checkin.checkin_date in exposures:
                behaviors = checkin.behaviors_json or {}
                if isinstance(behaviors, dict):
                    exposures[checkin.checkin_date].behaviors = {
                        k: bool(v) for k, v in behaviors.items()
                    }
        
        # Load adherence events
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        adherence_events = (
            self.db.query(AdherenceEvent)
            .filter(
                AdherenceEvent.user_id == user_id,
                AdherenceEvent.timestamp >= start_datetime,
                AdherenceEvent.timestamp <= end_datetime,
            )
            .all()
        )
        
        for event in adherence_events:
            event_date = event.timestamp.date()
            if event_date in exposures:
                # Get intervention key from experiment (if relationship exists)
                intervention_key = None
                if hasattr(event, "experiment_id") and event.experiment_id:
                    from app.domain.models.experiment import Experiment
                    experiment = self.db.query(Experiment).filter(Experiment.id == event.experiment_id).first()
                    if experiment:
                        # Try to get intervention key from experiment
                        if hasattr(experiment, "intervention_key"):
                            intervention_key = experiment.intervention_key
                        elif hasattr(experiment, "intervention_id"):
                            from app.domain.models.intervention import Intervention
                            intervention = self.db.query(Intervention).filter(Intervention.id == experiment.intervention_id).first()
                            if intervention:
                                intervention_key = intervention.key
                
                if intervention_key:
                    # Consider "taken=True" as exposed
                    exposures[event_date].interventions[intervention_key] = event.taken
        
        return exposures
    
    def _build_outcome_table(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> Dict[date, DailyOutcome]:
        """Build daily outcome table from health data points"""
        outcomes: Dict[date, DailyOutcome] = {}
        
        # Initialize all dates
        current = start_date
        while current <= end_date:
            outcomes[current] = DailyOutcome(
                date=current,
                metric_values={},
            )
            current += timedelta(days=1)
        
        # Load health data points
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        points = (
            self.db.query(HealthDataPoint)
            .filter(
                HealthDataPoint.user_id == user_id,
                HealthDataPoint.timestamp >= start_datetime,
                HealthDataPoint.timestamp <= end_datetime,
            )
            .all()
        )
        
        # Aggregate by date and metric
        daily_metrics: Dict[date, Dict[str, List[float]]] = {}
        for point in points:
            point_date = point.timestamp.date()
            if start_date <= point_date <= end_date:
                if point_date not in daily_metrics:
                    daily_metrics[point_date] = {}
                if point.metric_type not in daily_metrics[point_date]:
                    daily_metrics[point_date][point.metric_type] = []
                daily_metrics[point_date][point.metric_type].append(point.value)
        
        # Compute daily means
        for point_date, metrics in daily_metrics.items():
            if point_date in outcomes:
                for metric_key, values in metrics.items():
                    if values:
                        outcomes[point_date].metric_values[metric_key] = sum(values) / len(values)
        
        return outcomes
    
    def _compute_association(
        self,
        user_id: int,
        exposure_key: str,
        exposure_type: str,
        metric_key: str,
        lag_days: int,
        exposures: Dict[date, DailyExposure],
        outcomes: Dict[date, DailyOutcome],
        start_date: date,
        end_date: date,
    ) -> Optional[DriverFinding]:
        """
        Compute association between exposure and metric outcome with lag.
        
        Returns DriverFinding if association meets thresholds, None otherwise.
        """
        # Build exposed vs unexposed day lists
        exposed_days: List[date] = []
        unexposed_days: List[date] = []
        
        current = start_date
        while current <= end_date:
            outcome_date = current
            exposure_date = current - timedelta(days=lag_days)
            
            # Check if we have outcome data
            if outcome_date not in outcomes:
                current += timedelta(days=1)
                continue
            
            if metric_key not in outcomes[outcome_date].metric_values:
                current += timedelta(days=1)
                continue
            
            # Check if exposure occurred
            if exposure_date in exposures:
                if exposure_type == "behavior":
                    is_exposed = exposures[exposure_date].behaviors.get(exposure_key, False)
                else:
                    is_exposed = exposures[exposure_date].interventions.get(exposure_key, False)
                
                if is_exposed:
                    exposed_days.append(outcome_date)
                else:
                    unexposed_days.append(outcome_date)
            
            current += timedelta(days=1)
        
        # Check thresholds
        n_exposed = len(exposed_days)
        n_unexposed = len(unexposed_days)
        n_total = n_exposed + n_unexposed
        
        if n_exposed < self.MIN_EXPOSED_DAYS:
            return None
        
        if n_total < self.MIN_TOTAL_DAYS:
            return None
        
        coverage = n_exposed / n_total if n_total > 0 else 0.0
        if coverage < self.MIN_COVERAGE:
            return None
        
        # Compute means and stds
        exposed_values = [
            outcomes[d].metric_values[metric_key]
            for d in exposed_days
            if metric_key in outcomes[d].metric_values
        ]
        unexposed_values = [
            outcomes[d].metric_values[metric_key]
            for d in unexposed_days
            if metric_key in outcomes[d].metric_values
        ]
        
        if not exposed_values or not unexposed_values:
            return None
        
        mean_exposed = sum(exposed_values) / len(exposed_values)
        mean_unexposed = sum(unexposed_values) / len(unexposed_values)
        
        # Compute stds
        var_exposed = sum((x - mean_exposed) ** 2 for x in exposed_values) / len(exposed_values)
        var_unexposed = sum((x - mean_unexposed) ** 2 for x in unexposed_values) / len(unexposed_values)
        std_exposed = var_exposed ** 0.5
        std_unexposed = var_unexposed ** 0.5
        
        # Pooled std for Cohen's d
        pooled_std = ((var_exposed + var_unexposed) / 2) ** 0.5
        if pooled_std == 0:
            return None  # No variance, can't compute effect size
        
        # Cohen's d
        effect_size = (mean_exposed - mean_unexposed) / pooled_std
        
        # Determine direction based on metric registry
        spec = get_metric_spec(metric_key)
        # Assume higher is better for most metrics (can be overridden in registry)
        higher_is_better = True  # Default assumption
        
        # For stress, lower is better
        if "stress" in metric_key.lower():
            higher_is_better = False
        
        # Determine direction
        if abs(effect_size) < 0.2:  # Small effect
            direction = "unclear"
        elif higher_is_better:
            direction = "improves" if effect_size > 0 else "worsens"
        else:
            direction = "worsens" if effect_size > 0 else "improves"
        
        # Compute confidence
        # Combine coverage, effect size magnitude, and sample size
        effect_magnitude = min(abs(effect_size) / 2.0, 1.0)  # Normalize to [0,1]
        sample_factor = min(n_exposed / 20.0, 1.0)  # More samples = higher confidence
        confidence = (coverage * 0.4 + effect_magnitude * 0.4 + sample_factor * 0.2)
        confidence = max(0.0, min(1.0, confidence))  # Clamp to [0,1]
        
        # Build details JSON
        details = {
            "mean_exposed": mean_exposed,
            "mean_unexposed": mean_unexposed,
            "std_exposed": std_exposed,
            "std_unexposed": std_unexposed,
            "pooled_std": pooled_std,
            "n_exposed": n_exposed,
            "n_unexposed": n_unexposed,
            "higher_is_better": higher_is_better,
            "thresholds": {
                "min_exposed_days": self.MIN_EXPOSED_DAYS,
                "min_total_days": self.MIN_TOTAL_DAYS,
                "min_coverage": self.MIN_COVERAGE,
            },
        }
        
        finding = DriverFinding(
            user_id=user_id,
            exposure_type=exposure_type,
            exposure_key=exposure_key,
            metric_key=metric_key,
            lag_days=lag_days,
            direction=direction,
            effect_size=effect_size,
            confidence=confidence,
            coverage=coverage,
            n_exposure_days=n_exposed,
            n_total_days=n_total,
            window_start=start_date,
            window_end=end_date,
            details_json=json.dumps(details),
        )
        
        return finding

