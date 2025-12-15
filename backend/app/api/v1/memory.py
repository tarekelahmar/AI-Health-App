from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router
from app.domain.repositories.causal_memory_repository import CausalMemoryRepository

router = make_v1_router(prefix="/api/v1/memory", tags=["memory"])


@router.get("")
def get_causal_memory(
    user_id: int = Depends(get_request_user_id),
    status: Optional[str] = Query(None, description="Filter by status: tentative, confirmed, deprecated"),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Get user's causal memory - what the system has learned about what works for them"""
    repo = CausalMemoryRepository(db)
    memories = repo.list_by_user(user_id=user_id, status=status, limit=limit)
    
    return {
        "count": len(memories),
        "items": [
            {
                "id": m.id,
                "driver_type": m.driver_type,
                "driver_key": m.driver_key,
                "metric_key": m.metric_key,
                "direction": m.direction,
                "avg_effect_size": m.avg_effect_size,
                "confidence": m.confidence,
                "evidence_count": m.evidence_count,
                "status": m.status,
                "first_seen_at": m.first_seen_at.isoformat(),
                "last_confirmed_at": m.last_confirmed_at.isoformat() if m.last_confirmed_at else None,
                "supporting_evaluations": m.supporting_evaluations_json,
            }
            for m in memories
        ],
    }


@router.get("/{driver_key}")
def get_driver_memory(
    driver_key: str,
    user_id: int = Depends(get_request_user_id),
    metric_key: Optional[str] = Query(None, description="Optional metric filter"),
    db: Session = Depends(get_db),
):
    """Get causal memory for a specific driver (optionally filtered by metric)"""
    repo = CausalMemoryRepository(db)
    
    if metric_key:
        memory = repo.get_for_driver_metric(user_id=user_id, driver_key=driver_key, metric_key=metric_key)
        if not memory:
            return {"found": False}
        
        return {
            "found": True,
            "memory": {
                "id": memory.id,
                "driver_type": memory.driver_type,
                "driver_key": memory.driver_key,
                "metric_key": memory.metric_key,
                "direction": memory.direction,
                "avg_effect_size": memory.avg_effect_size,
                "confidence": memory.confidence,
                "evidence_count": memory.evidence_count,
                "status": memory.status,
                "first_seen_at": memory.first_seen_at.isoformat(),
                "last_confirmed_at": memory.last_confirmed_at.isoformat() if memory.last_confirmed_at else None,
                "supporting_evaluations": memory.supporting_evaluations_json,
            },
        }
    else:
        # Get all memories for this driver
        all_memories = repo.list_by_user(user_id=user_id, limit=200)
        driver_memories = [m for m in all_memories if m.driver_key == driver_key]
        
        return {
            "count": len(driver_memories),
            "items": [
                {
                    "id": m.id,
                    "driver_type": m.driver_type,
                    "driver_key": m.driver_key,
                    "metric_key": m.metric_key,
                    "direction": m.direction,
                    "avg_effect_size": m.avg_effect_size,
                    "confidence": m.confidence,
                    "evidence_count": m.evidence_count,
                    "status": m.status,
                    "first_seen_at": m.first_seen_at.isoformat(),
                    "last_confirmed_at": m.last_confirmed_at.isoformat() if m.last_confirmed_at else None,
                }
                for m in driver_memories
            ],
        }

