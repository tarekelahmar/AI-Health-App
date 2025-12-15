from __future__ import annotations

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.domain.models.explanation_edge import ExplanationEdge


class ExplanationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_edge(
        self,
        target_type: str,
        target_id: int,
        source_type: str,
        source_id: Optional[int],
        contribution_weight: float = 1.0,
        description: Optional[str] = None,
    ) -> ExplanationEdge:
        """Create an explanation edge"""
        edge = ExplanationEdge(
            target_type=target_type,
            target_id=target_id,
            source_type=source_type,
            source_id=source_id,
            contribution_weight=contribution_weight,
            description=description,
        )
        self.db.add(edge)
        self.db.commit()
        self.db.refresh(edge)
        return edge

    def get_for_target(
        self,
        target_type: str,
        target_id: int,
    ) -> List[ExplanationEdge]:
        """Get all explanation edges for a target (insight/evaluation/narrative)"""
        return (
            self.db.query(ExplanationEdge)
            .filter(
                ExplanationEdge.target_type == target_type,
                ExplanationEdge.target_id == target_id,
            )
            .order_by(desc(ExplanationEdge.contribution_weight))
            .all()
        )

    def get_by_source(
        self,
        source_type: str,
        source_id: int,
    ) -> List[ExplanationEdge]:
        """Get all explanation edges from a source"""
        return (
            self.db.query(ExplanationEdge)
            .filter(
                ExplanationEdge.source_type == source_type,
                ExplanationEdge.source_id == source_id,
            )
            .all()
        )

