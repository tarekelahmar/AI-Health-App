from __future__ import annotations

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.domain.models.causal_memory import CausalMemory


class CausalMemoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert_from_evaluation(
        self,
        user_id: int,
        driver_type: str,
        driver_key: str,
        metric_key: str,
        direction: str,
        effect_size: float,
        evaluation_id: int,
        confidence: float = 0.5,
    ) -> CausalMemory:
        """
        Upsert causal memory from an evaluation result.
        
        Updates existing memory or creates new one, accumulating evidence.
        """
        existing = (
            self.db.query(CausalMemory)
            .filter(
                CausalMemory.user_id == user_id,
                CausalMemory.driver_key == driver_key,
                CausalMemory.metric_key == metric_key,
            )
            .first()
        )

        if existing:
            # Update existing memory
            # Accumulate effect sizes
            total_effect = existing.avg_effect_size * existing.evidence_count + effect_size
            new_count = existing.evidence_count + 1
            existing.avg_effect_size = total_effect / new_count
            existing.evidence_count = new_count
            
            # Update direction if needed
            if existing.direction != direction:
                if existing.direction == "mixed":
                    pass  # Already mixed
                elif direction == "mixed":
                    existing.direction = "mixed"
                else:
                    # Check if we should switch to mixed
                    # If we have conflicting directions, mark as mixed
                    existing.direction = "mixed"
            
            # Update confidence (weighted average)
            existing.confidence = (existing.confidence * existing.evidence_count + confidence) / new_count
            
            # Update supporting evaluations
            evals = existing.supporting_evaluations_json or []
            evals.append({
                "evaluation_id": evaluation_id,
                "effect_size": effect_size,
                "direction": direction,
                "confidence": confidence,
                "timestamp": datetime.utcnow().isoformat(),
            })
            existing.supporting_evaluations_json = evals
            
            existing.last_confirmed_at = datetime.utcnow()
            
            # Promote to confirmed if we have enough evidence
            if existing.evidence_count >= 3 and existing.confidence >= 0.7:
                existing.status = "confirmed"
            elif existing.evidence_count >= 2 and existing.confidence >= 0.6:
                existing.status = "confirmed"
            
            existing.updated_at = datetime.utcnow()
            self.db.add(existing)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new memory
            new_memory = CausalMemory(
                user_id=user_id,
                driver_type=driver_type,
                driver_key=driver_key,
                metric_key=metric_key,
                direction=direction,
                avg_effect_size=effect_size,
                confidence=confidence,
                evidence_count=1,
                first_seen_at=datetime.utcnow(),
                last_confirmed_at=datetime.utcnow(),
                status="tentative",
                supporting_evaluations_json=[{
                    "evaluation_id": evaluation_id,
                    "effect_size": effect_size,
                    "direction": direction,
                    "confidence": confidence,
                    "timestamp": datetime.utcnow().isoformat(),
                }],
            )
            self.db.add(new_memory)
            self.db.commit()
            self.db.refresh(new_memory)
            return new_memory

    def list_by_user(
        self,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[CausalMemory]:
        """List causal memories for a user, optionally filtered by status"""
        query = self.db.query(CausalMemory).filter(CausalMemory.user_id == user_id)
        
        if status:
            query = query.filter(CausalMemory.status == status)
        
        return query.order_by(desc(CausalMemory.confidence)).limit(limit).all()

    def get_for_driver_metric(
        self,
        user_id: int,
        driver_key: str,
        metric_key: str,
    ) -> Optional[CausalMemory]:
        """Get causal memory for a specific driver-metric pair"""
        return (
            self.db.query(CausalMemory)
            .filter(
                CausalMemory.user_id == user_id,
                CausalMemory.driver_key == driver_key,
                CausalMemory.metric_key == metric_key,
            )
            .first()
        )

    def deprecate_contradictory(
        self,
        user_id: int,
        driver_key: str,
        metric_key: str,
        reason: str,
    ) -> Optional[CausalMemory]:
        """Deprecate a memory due to contradictory evidence"""
        memory = self.get_for_driver_metric(user_id, driver_key, metric_key)
        if memory:
            memory.status = "deprecated"
            memory.updated_at = datetime.utcnow()
            # Store deprecation reason in supporting_evaluations_json
            evals = memory.supporting_evaluations_json or []
            evals.append({
                "action": "deprecated",
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat(),
            })
            memory.supporting_evaluations_json = evals
            self.db.add(memory)
            self.db.commit()
            self.db.refresh(memory)
        return memory

