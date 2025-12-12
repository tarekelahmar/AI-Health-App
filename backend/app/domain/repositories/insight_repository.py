from typing import Optional, List
from sqlalchemy.orm import Session
from app.domain.models.insight import Insight


class InsightRepository:
    """Data access for generated Insights."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: int,
        insight_type: str,
        title: str,
        description: str,
        confidence_score: float,
        metadata_json: str = "",
    ) -> Insight:
        insight = Insight(
            user_id=user_id,
            insight_type=insight_type,
            title=title,
            description=description,
            confidence_score=confidence_score,
            metadata_json=metadata_json,
        )
        self.db.add(insight)
        self.db.commit()
        self.db.refresh(insight)
        return insight

    def list_for_user(
        self,
        user_id: int,
        insight_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Insight]:
        q = self.db.query(Insight).filter(Insight.user_id == user_id)
        if insight_type:
            q = q.filter(Insight.insight_type == insight_type)
        return (
            q.order_by(Insight.generated_at.desc())
            .limit(limit)
            .all()
        )

    def get_recent_for_user(
        self,
        user_id: int,
        limit: int = 10,
    ) -> List[Insight]:
        return (
            self.db.query(Insight)
            .filter(Insight.user_id == user_id)
            .order_by(Insight.generated_at.desc())
            .limit(limit)
            .all()
        )

