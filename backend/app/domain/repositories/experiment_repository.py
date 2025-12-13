from datetime import datetime
from sqlalchemy.orm import Session
from app.domain.models.experiment_run import ExperimentRun


class ExperimentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_due_for_evaluation(
        self,
        user_id: int,
        now: datetime,
    ) -> list[ExperimentRun]:
        return (
            self.db.query(ExperimentRun)
            .filter(
                ExperimentRun.user_id == user_id,
                ExperimentRun.status == "running",
                ExperimentRun.followup_end <= now,
            )
            .all()
        )

