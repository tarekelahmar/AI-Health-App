from datetime import date, timedelta, datetime
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.domain.models.insight_summary import InsightSummary
from app.domain.repositories.insight_summary_repository import InsightSummaryRepository
from app.domain.repositories.insight_repository import InsightRepository
from app.domain.repositories.evaluation_repository import EvaluationRepository
from app.domain.repositories.adherence_repository import AdherenceRepository
from app.domain.repositories.experiment_repository import ExperimentRepository
from app.engine.synthesis.insight_synthesizer import InsightSynthesizer


class SynthesisService:
    def __init__(self, db: Session):
        self.db = db
        self.insight_repo = InsightRepository(db)
        self.evaluation_repo = EvaluationRepository(db)
        self.adherence_repo = AdherenceRepository(db)
        self.summary_repo = InsightSummaryRepository(db)

    def run_daily(self, user_id: int) -> InsightSummary:
        # Get recent data (using existing repository methods)
        # Get recent insights (last 1 day)
        cutoff = datetime.utcnow() - timedelta(days=1)
        all_insights = self.insight_repo.list_by_user(user_id=user_id, limit=100)
        insights = []
        for i in all_insights:
            created = getattr(i, 'generated_at', None) or getattr(i, 'created_at', None)
            if created and created >= cutoff:
                insights.append(i)
        
        # Get recent evaluations (last 7 days)
        eval_cutoff = datetime.utcnow() - timedelta(days=7)
        all_evaluations = self.evaluation_repo.list_by_user(user_id=user_id, limit=50)
        evaluations = []
        for e in all_evaluations:
            created = getattr(e, 'created_at', datetime.utcnow())
            if created >= eval_cutoff:
                evaluations.append(e)
        
        # Get recent adherence (last 7 days) - need to get via experiments
        exp_repo = ExperimentRepository(self.db)
        user_experiments = exp_repo.list_by_user(user_id=user_id, limit=20)
        adherence = []
        for exp in user_experiments:
            exp_adherence = self.adherence_repo.list_by_experiment(experiment_id=exp.id, limit=50)
            for a in exp_adherence:
                created = getattr(a, 'timestamp', None) or getattr(a, 'created_at', None)
                if created and created >= eval_cutoff:
                    adherence.append(a)

        # Synthesize
        synthesizer = InsightSynthesizer()
        payload = synthesizer.synthesize(
            user_id=user_id,
            insights=insights,
            evaluations=evaluations,
            adherence_events=adherence,
            period="daily",
        )

        # Create summary
        summary = InsightSummary(
            user_id=user_id,
            period="daily",
            summary_date=date.today(),
            headline=payload["headline"],
            narrative=payload["narrative"],
            key_metrics=payload["key_metrics"],
            drivers=payload["drivers"],
            interventions=payload["interventions"],
            outcomes=payload["outcomes"],
            confidence=payload["confidence"],
        )

        return self.summary_repo.create(summary)
