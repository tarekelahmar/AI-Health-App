from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from app.domain.models.questionnaire import Questionnaire


class QuestionnaireRepository:
    """Data access for Questionnaire responses."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: int,
        questionnaire_type: str,
        responses: dict,
        completed_at: Optional[datetime] = None,
    ) -> Questionnaire:
        q = Questionnaire(
            user_id=user_id,
            questionnaire_type=questionnaire_type,
            responses=responses,
            completed_at=completed_at or datetime.utcnow(),
        )
        self.db.add(q)
        self.db.commit()
        self.db.refresh(q)
        return q

    def get_latest_for_user(
        self,
        user_id: int,
        questionnaire_type: Optional[str] = None,
    ) -> Optional[Questionnaire]:
        q = self.db.query(Questionnaire).filter(
            Questionnaire.user_id == user_id,
        )
        if questionnaire_type:
            q = q.filter(Questionnaire.questionnaire_type == questionnaire_type)
        return q.order_by(Questionnaire.completed_at.desc()).first()

    def list_for_user(
        self,
        user_id: int,
        limit: int = 50,
    ) -> List[Questionnaire]:
        return (
            self.db.query(Questionnaire)
            .filter(Questionnaire.user_id == user_id)
            .order_by(Questionnaire.completed_at.desc())
            .limit(limit)
            .all()
        )

