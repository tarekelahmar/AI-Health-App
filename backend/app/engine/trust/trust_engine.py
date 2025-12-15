from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.domain.models.trust_score import TrustScore
from app.domain.models.health_data_point import HealthDataPoint
from app.domain.models.adherence_event import AdherenceEvent
from app.domain.models.evaluation_result import EvaluationResult
from app.domain.models.causal_memory import CausalMemory

logger = logging.getLogger(__name__)


class TrustEngine:
    """
    Trust Engine
    
    Updates trust weekly.
    Trust gates:
    - Low trust → conservative recommendations
    - High trust → stronger protocol confidence
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def compute_trust_score(self, user_id: int) -> TrustScore:
        """
        Compute trust score for a user.
        
        Components:
        1. Data coverage score - how much data we have
        2. Adherence score - how well user follows protocols
        3. Evaluation success rate - % of positive outcomes
        4. Stability score - consistency of patterns
        """
        # 1. Data Coverage Score
        data_coverage = self._compute_data_coverage_score(user_id)
        
        # 2. Adherence Score
        adherence = self._compute_adherence_score(user_id)
        
        # 3. Evaluation Success Rate
        success_rate = self._compute_evaluation_success_rate(user_id)
        
        # 4. Stability Score
        stability = self._compute_stability_score(user_id)
        
        # Overall trust score (weighted average)
        overall_score = (
            data_coverage * 0.3 +
            adherence * 0.25 +
            success_rate * 0.25 +
            stability * 0.2
        )
        
        # Get or create trust score
        trust_score = (
            self.db.query(TrustScore)
            .filter(TrustScore.user_id == user_id)
            .first()
        )
        
        if trust_score:
            trust_score.score = overall_score
            trust_score.data_coverage_score = data_coverage
            trust_score.adherence_score = adherence
            trust_score.evaluation_success_rate = success_rate
            trust_score.stability_score = stability
            trust_score.last_updated_at = datetime.utcnow()
            self.db.add(trust_score)
            self.db.commit()
            self.db.refresh(trust_score)
        else:
            trust_score = TrustScore(
                user_id=user_id,
                score=overall_score,
                data_coverage_score=data_coverage,
                adherence_score=adherence,
                evaluation_success_rate=success_rate,
                stability_score=stability,
            )
            self.db.add(trust_score)
            self.db.commit()
            self.db.refresh(trust_score)
        
        return trust_score
    
    def _compute_data_coverage_score(self, user_id: int) -> float:
        """Compute data coverage score [0-100]"""
        # Check last 30 days
        cutoff = datetime.utcnow() - timedelta(days=30)
        
        data_points = (
            self.db.query(HealthDataPoint)
            .filter(
                HealthDataPoint.user_id == user_id,
                HealthDataPoint.timestamp >= cutoff,
            )
            .count()
        )
        
        # Expected: at least 1 data point per day for 30 days = 30 points
        # More is better, cap at 100
        coverage = min(100.0, (data_points / 30.0) * 100.0)
        return coverage
    
    def _compute_adherence_score(self, user_id: int) -> float:
        """Compute adherence score [0-100]"""
        # Check last 30 days
        cutoff = datetime.utcnow() - timedelta(days=30)
        
        adherence_events = (
            self.db.query(AdherenceEvent)
            .filter(
                AdherenceEvent.user_id == user_id,
                AdherenceEvent.timestamp >= cutoff,
            )
            .all()
        )
        
        if not adherence_events:
            return 0.0
        
        taken_count = sum(1 for e in adherence_events if e.taken)
        total_count = len(adherence_events)
        
        if total_count == 0:
            return 0.0
        
        adherence_rate = (taken_count / total_count) * 100.0
        return adherence_rate
    
    def _compute_evaluation_success_rate(self, user_id: int) -> float:
        """Compute evaluation success rate [0-100]"""
        evaluations = (
            self.db.query(EvaluationResult)
            .filter(EvaluationResult.user_id == user_id)
            .all()
        )
        
        if not evaluations:
            return 50.0  # Neutral if no evaluations yet
        
        # Count positive outcomes
        positive_verdicts = ["helpful", "positive", "improved"]
        positive_count = sum(
            1 for e in evaluations
            if e.verdict and e.verdict.lower() in positive_verdicts
        )
        
        success_rate = (positive_count / len(evaluations)) * 100.0
        return success_rate
    
    def _compute_stability_score(self, user_id: int) -> float:
        """Compute stability score [0-100] based on memory consistency"""
        memories = (
            self.db.query(CausalMemory)
            .filter(
                CausalMemory.user_id == user_id,
                CausalMemory.status == "confirmed",
            )
            .all()
        )
        
        if not memories:
            return 50.0  # Neutral if no confirmed memories
        
        # Stability is based on:
        # 1. How many confirmed memories we have (more = more stable)
        # 2. Average confidence of memories
        # 3. How many have high evidence_count
        
        avg_confidence = sum(m.confidence for m in memories) / len(memories)
        high_evidence_count = sum(1 for m in memories if m.evidence_count >= 3)
        
        # Combine factors
        stability = (
            avg_confidence * 50.0 +  # Confidence contributes 50%
            min(50.0, (high_evidence_count / max(1, len(memories))) * 50.0)  # Evidence count contributes 50%
        )
        
        return min(100.0, stability)
    
    def get_trust_level(self, user_id: int) -> str:
        """Get trust level category"""
        trust_score = (
            self.db.query(TrustScore)
            .filter(TrustScore.user_id == user_id)
            .first()
        )
        
        if not trust_score:
            return "low"
        
        score = trust_score.score
        
        if score >= 75:
            return "high"
        elif score >= 50:
            return "medium"
        else:
            return "low"

