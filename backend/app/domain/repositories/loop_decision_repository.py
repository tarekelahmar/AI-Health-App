from sqlalchemy.orm import Session

from app.domain.models.loop_decision import LoopDecision


class LoopDecisionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, decision: LoopDecision) -> LoopDecision:
        self.db.add(decision)
        self.db.commit()
        self.db.refresh(decision)
        return decision

