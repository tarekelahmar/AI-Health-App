from __future__ import annotations

import logging
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.domain.models.daily_checkin import DailyCheckIn
from app.domain.models.adherence_event import AdherenceEvent
from app.domain.models.health_data_point import HealthDataPoint
from app.domain.models.personal_driver import PersonalDriver
from app.domain.models.intervention import Intervention
from app.domain.models.experiment import Experiment
from app.domain.repositories.personal_driver_repository import PersonalDriverRepository
from app.domain.driver_registry import DRIVER_REGISTRY, get_driver_spec, get_drivers_for_outcome
from app.domain.metric_registry import METRICS
from app.engine.attribution.guardrails import apply_attribution_guardrails

logger = logging.getLogger(__name__)


class CrossSignalAttributionEngine:
    """
    Cross-signal attribution engine.
    
    Identifies which inputs (behaviors, supplements, labs, interventions) 
    actually explain changes in outcomes (sleep, HRV, energy, mood) per user.
    
    Uses regression and partial correlation - pure math, no LLM.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.driver_repo = PersonalDriverRepository(db)
    
    def compute_personal_drivers(
        self,
        user_id: int,
        window_days: int = 28,
    ) -> List[PersonalDriver]:
        """
        Compute personal drivers for a user.
        
        Args:
            user_id: User ID
            window_days: Number of days to analyze
            
        Returns:
            List of PersonalDriver objects
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=window_days)
        
        # Build daily feature matrix
        feature_matrix = self._build_feature_matrix(user_id, start_date, end_date)
        
        # Build outcome series
        outcome_series = self._build_outcome_series(user_id, start_date, end_date)
        
        drivers: List[PersonalDriver] = []
        
        # For each outcome metric
        for outcome_metric in outcome_series.keys():
            if outcome_metric not in METRICS:
                continue
            
            # Get all drivers that can affect this outcome
            driver_specs = get_drivers_for_outcome(outcome_metric)
            
            # For each driver
            for spec in driver_specs:
                # Test different lags
                for lag_days in range(0, spec.max_lag_days + 1):
                    driver = self._compute_attribution(
                        user_id=user_id,
                        driver_spec=spec,
                        outcome_metric=outcome_metric,
                        lag_days=lag_days,
                        feature_matrix=feature_matrix,
                        outcome_series=outcome_series,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    
                    if driver:
                        drivers.append(driver)
        
        # Upsert all drivers
        for driver in drivers:
            self.driver_repo.upsert_driver(driver)
        
        return drivers
    
    def _build_feature_matrix(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> Dict[date, Dict[str, float]]:
        """
        Build daily feature matrix.
        
        Returns:
            Dict[date, Dict[driver_key, value]]
        """
        features: Dict[date, Dict[str, float]] = defaultdict(dict)
        
        # Initialize all dates
        current = start_date
        while current <= end_date:
            features[current] = {}
            current += timedelta(days=1)
        
        # Load check-ins (behaviors)
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
            if checkin.checkin_date in features:
                behaviors = checkin.behaviors_json or {}
                if isinstance(behaviors, dict):
                    for key, value in behaviors.items():
                        # Convert to float (1/0 for binary, or count)
                        if isinstance(value, bool):
                            features[checkin.checkin_date][key] = 1.0 if value else 0.0
                        elif isinstance(value, (int, float)):
                            features[checkin.checkin_date][key] = float(value)
        
        # Load adherence events (interventions)
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
            if event_date in features:
                # Get intervention key
                if hasattr(event, "intervention_id") and event.intervention_id:
                    intervention = (
                        self.db.query(Intervention)
                        .filter(Intervention.id == event.intervention_id)
                        .first()
                    )
                    if intervention and hasattr(intervention, "key"):
                        features[event_date][intervention.key] = 1.0 if event.taken else 0.0
        
        # Load active experiments (interventions as flags)
        experiments = (
            self.db.query(Experiment)
            .filter(
                Experiment.user_id == user_id,
                Experiment.status == "active",
            )
            .all()
        )
        
        for exp in experiments:
            if hasattr(exp, "intervention_id") and exp.intervention_id:
                intervention = (
                    self.db.query(Intervention)
                    .filter(Intervention.id == exp.intervention_id)
                    .first()
                )
                if intervention and hasattr(intervention, "key"):
                    # Mark as active during experiment window
                    exp_start = exp.started_at.date() if hasattr(exp, "started_at") else start_date
                    exp_end = exp.ended_at.date() if (hasattr(exp, "ended_at") and exp.ended_at) else end_date
                    
                    current = max(exp_start, start_date)
                    while current <= min(exp_end, end_date):
                        if current in features:
                            features[current][intervention.key] = 1.0
                        current += timedelta(days=1)
        
        return features
    
    def _build_outcome_series(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> Dict[str, List[Tuple[date, float]]]:
        """
        Build outcome series for each metric.
        
        Returns:
            Dict[metric_key, List[(date, value)]]
        """
        outcomes: Dict[str, List[Tuple[date, float]]] = defaultdict(list)
        
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # Load health data points
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
        daily_metrics: Dict[date, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        for point in points:
            point_date = point.timestamp.date()
            if start_date <= point_date <= end_date:
                daily_metrics[point_date][point.metric_type].append(point.value)
        
        # Compute daily means
        for point_date, metrics in daily_metrics.items():
            for metric_key, values in metrics.items():
                if values:
                    outcomes[metric_key].append((point_date, sum(values) / len(values)))
        
        # Sort by date
        for metric_key in outcomes:
            outcomes[metric_key].sort(key=lambda x: x[0])
        
        return outcomes
    
    def _compute_attribution(
        self,
        user_id: int,
        driver_spec,
        outcome_metric: str,
        lag_days: int,
        feature_matrix: Dict[date, Dict[str, float]],
        outcome_series: Dict[str, List[Tuple[date, float]]],
        start_date: date,
        end_date: date,
    ) -> Optional[PersonalDriver]:
        """
        Compute attribution for a driver → outcome with lag.
        
        Uses simple regression and partial correlation.
        """
        if outcome_metric not in outcome_series:
            return None
        
        # Build aligned series
        driver_values: List[float] = []
        outcome_values: List[float] = []
        
        current = start_date
        while current <= end_date:
            outcome_date = current
            driver_date = current - timedelta(days=lag_days)
            
            # Get outcome value (interpolate if missing)
            outcome_val = self._get_outcome_value(outcome_series[outcome_metric], outcome_date)
            if outcome_val is None:
                current += timedelta(days=1)
                continue
            
            # Get driver value
            driver_val = feature_matrix.get(driver_date, {}).get(driver_spec.driver_key, 0.0)
            
            driver_values.append(driver_val)
            outcome_values.append(outcome_val)
            
            current += timedelta(days=1)
        
        # Check minimum data requirement
        if len(driver_values) < driver_spec.min_data_days:
            return None
        
        # Check that we have variation in driver
        if len(set(driver_values)) < 2:
            return None  # No variation
        
        # Simple regression: outcome = alpha + beta * driver
        beta, alpha, r_squared = self._simple_regression(driver_values, outcome_values)
        
        if beta is None or math.isnan(beta):
            return None
        
        # Compute effect size (standardized)
        effect_size = self._compute_effect_size(driver_values, outcome_values)
        
        # Determine direction
        if abs(effect_size) < 0.1:
            direction = "neutral"
        elif effect_size > 0:
            direction = "positive"
        else:
            direction = "negative"
        
        # Compute variance explained (R²)
        variance_explained = max(0.0, min(1.0, r_squared))
        
        # Compute stability (consistency across rolling windows)
        stability = self._compute_stability(driver_values, outcome_values)
        
        # Compute base confidence
        coverage = len([v for v in driver_values if v > 0]) / len(driver_values) if driver_values else 0.0
        effect_magnitude = min(abs(effect_size) / 2.0, 1.0)
        base_confidence = (coverage * 0.3 + effect_magnitude * 0.4 + stability * 0.3)
        base_confidence = max(0.0, min(1.0, base_confidence))
        
        # SECURITY FIX (Risk #8): Apply guardrails to prevent false positives
        # Estimate number of comparisons (drivers × outcomes × lags)
        # This is approximate; in practice, we'd track this more precisely
        n_comparisons = len(get_drivers_for_outcome(outcome_metric)) * (driver_spec.max_lag_days + 1)
        
        guardrail_result = apply_attribution_guardrails(
            effect_size=effect_size,
            confidence=base_confidence,
            stability=stability,
            variance_explained=variance_explained,
            sample_size=len(driver_values),
            n_comparisons=n_comparisons,
            r_squared=r_squared,
        )
        
        # Use adjusted confidence from guardrails
        final_confidence = guardrail_result.adjusted_confidence if guardrail_result.adjusted_confidence is not None else base_confidence
        
        # SECURITY FIX: Skip if guardrails fail (don't create driver)
        if not guardrail_result.passed:
            logger.debug(
                f"Attribution guardrails failed for user_id={user_id}, driver={driver_spec.driver_key}, "
                f"outcome={outcome_metric}, reason={guardrail_result.reason}"
            )
            return None
        
        return PersonalDriver(
            user_id=user_id,
            driver_type=driver_spec.driver_type,
            driver_key=driver_spec.driver_key,
            outcome_metric=outcome_metric,
            lag_days=lag_days,
            effect_size=effect_size,
            direction=direction,
            variance_explained=variance_explained,
            confidence=final_confidence,  # Use guardrail-adjusted confidence
            stability=stability,
            sample_size=len(driver_values),
        )
    
    def _get_outcome_value(
        self,
        outcome_series: List[Tuple[date, float]],
        target_date: date,
    ) -> Optional[float]:
        """Get outcome value for a date (interpolate if missing)"""
        # Exact match
        for d, v in outcome_series:
            if d == target_date:
                return v
        
        # Interpolate from nearest neighbors
        before = None
        after = None
        
        for d, v in outcome_series:
            if d < target_date:
                if before is None or d > before[0]:
                    before = (d, v)
            elif d > target_date:
                if after is None or d < after[0]:
                    after = (d, v)
        
        if before and after:
            # Linear interpolation
            days_diff = (after[0] - before[0]).days
            if days_diff > 0:
                weight = (target_date - before[0]).days / days_diff
                return before[1] * (1 - weight) + after[1] * weight
        
        if before:
            return before[1]
        if after:
            return after[1]
        
        return None
    
    def _simple_regression(
        self,
        x: List[float],
        y: List[float],
    ) -> Tuple[Optional[float], Optional[float], float]:
        """
        Simple linear regression: y = alpha + beta * x
        
        Returns:
            (beta, alpha, r_squared)
        """
        n = len(x)
        if n < 2:
            return None, None, 0.0
        
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return None, None, 0.0
        
        beta = numerator / denominator
        alpha = y_mean - beta * x_mean
        
        # Compute R²
        y_pred = [alpha + beta * x[i] for i in range(n)]
        ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((y[i] - y_mean) ** 2 for i in range(n))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        
        return beta, alpha, r_squared
    
    def _compute_effect_size(
        self,
        x: List[float],
        y: List[float],
    ) -> float:
        """Compute Cohen's d effect size"""
        # Split by x > 0 vs x == 0
        exposed = [y[i] for i in range(len(x)) if x[i] > 0]
        unexposed = [y[i] for i in range(len(x)) if x[i] == 0]
        
        if not exposed or not unexposed:
            return 0.0
        
        mean_exposed = sum(exposed) / len(exposed)
        mean_unexposed = sum(unexposed) / len(unexposed)
        
        var_exposed = sum((v - mean_exposed) ** 2 for v in exposed) / len(exposed)
        var_unexposed = sum((v - mean_unexposed) ** 2 for v in unexposed) / len(unexposed)
        
        pooled_std = ((var_exposed + var_unexposed) / 2) ** 0.5
        if pooled_std == 0:
            return 0.0
        
        return (mean_exposed - mean_unexposed) / pooled_std
    
    def _compute_stability(
        self,
        x: List[float],
        y: List[float],
        window_size: int = 7,
    ) -> float:
        """
        Compute stability across rolling windows.
        
        Returns consistency of effect across different time windows.
        """
        if len(x) < window_size * 2:
            return 0.5  # Not enough data
        
        effects: List[float] = []
        
        for i in range(len(x) - window_size + 1):
            x_window = x[i:i+window_size]
            y_window = y[i:i+window_size]
            
            if len(set(x_window)) < 2:
                continue  # No variation in this window
            
            effect = self._compute_effect_size(x_window, y_window)
            if not math.isnan(effect):
                effects.append(effect)
        
        if len(effects) < 2:
            return 0.5
        
        # Compute coefficient of variation (lower = more stable)
        mean_effect = sum(effects) / len(effects)
        if mean_effect == 0:
            return 0.5
        
        std_effect = (sum((e - mean_effect) ** 2 for e in effects) / len(effects)) ** 0.5
        cv = abs(std_effect / mean_effect) if mean_effect != 0 else 1.0
        
        # Convert to stability score [0, 1] (lower CV = higher stability)
        stability = max(0.0, min(1.0, 1.0 - cv))
        
        return stability

