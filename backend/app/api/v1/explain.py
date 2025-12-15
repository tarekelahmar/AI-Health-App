from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router
from app.domain.repositories.explanation_repository import ExplanationRepository
from app.domain.models.insight import Insight
from app.domain.models.narrative import Narrative

router = make_v1_router(prefix="/api/v1/explain", tags=["explain"])


@router.get("/insight/{insight_id}")
def explain_insight(
    insight_id: int,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """Get explanation graph for an insight - why am I seeing this?"""
    # Verify insight belongs to user
    insight = db.query(Insight).filter(Insight.id == insight_id, Insight.user_id == user_id).first()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    
    # Get explanation edges
    explanation_repo = ExplanationRepository(db)
    edges = explanation_repo.get_for_target("insight", insight_id)
    
    return {
        "insight_id": insight_id,
        "insight_title": insight.title,
        "explanation": {
            "edges": [
                {
                    "id": e.id,
                    "source_type": e.source_type,
                    "source_id": e.source_id,
                    "contribution_weight": e.contribution_weight,
                    "description": e.description,
                }
                for e in edges
            ],
            "summary": _generate_explanation_summary(edges),
        },
    }


@router.get("/narrative/{narrative_id}")
def explain_narrative(
    narrative_id: int,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """Get explanation graph for a narrative"""
    # Verify narrative belongs to user
    narrative = db.query(Narrative).filter(Narrative.id == narrative_id, Narrative.user_id == user_id).first()
    if not narrative:
        raise HTTPException(status_code=404, detail="Narrative not found")
    
    # Get explanation edges
    explanation_repo = ExplanationRepository(db)
    edges = explanation_repo.get_for_target("narrative", narrative_id)
    
    return {
        "narrative_id": narrative_id,
        "narrative_title": narrative.title,
        "explanation": {
            "edges": [
                {
                    "id": e.id,
                    "source_type": e.source_type,
                    "source_id": e.source_id,
                    "contribution_weight": e.contribution_weight,
                    "description": e.description,
                }
                for e in edges
            ],
            "summary": _generate_explanation_summary(edges),
        },
    }


def _generate_explanation_summary(edges) -> str:
    """Generate a human-readable summary of explanation edges"""
    if not edges:
        return "No explanation data available."
    
    # Group by source type
    by_type = {}
    for edge in edges:
        if edge.source_type not in by_type:
            by_type[edge.source_type] = []
        by_type[edge.source_type].append(edge)
    
    parts = []
    for source_type, type_edges in by_type.items():
        count = len(type_edges)
        total_weight = sum(e.contribution_weight for e in type_edges)
        
        if source_type == "metric":
            parts.append(f"{count} metric data point(s) (weight: {total_weight:.2f})")
        elif source_type == "experiment":
            parts.append(f"{count} experiment(s) (weight: {total_weight:.2f})")
        elif source_type == "evaluation":
            parts.append(f"{count} evaluation(s) (weight: {total_weight:.2f})")
        elif source_type == "checkin":
            parts.append(f"{count} check-in(s) (weight: {total_weight:.2f})")
        elif source_type == "memory":
            parts.append(f"{count} confirmed memory/pattern(s) (weight: {total_weight:.2f})")
        else:
            parts.append(f"{count} {source_type}(s) (weight: {total_weight:.2f})")
    
    return "Based on: " + ", ".join(parts) + "."

