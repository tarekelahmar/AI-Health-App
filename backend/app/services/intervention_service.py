from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.domain.models.intervention import Intervention
from app.domain.models.experiment_run import ExperimentRun
from app.engine.hypothesis_generation import GeneratedHypothesis


def start_intervention(
    *,
    db: Session,
    user_id: int,
    hypothesis: GeneratedHypothesis,
    target_metric: str,
) -> ExperimentRun:

    now = datetime.utcnow()

    intervention = Intervention(
        user_id=user_id,
        hypothesis_factor=hypothesis.factor,
        intervention_type="supplement",
        name="Magnesium (trial)",
        dose="200",
        unit="mg",
        schedule="nightly",
        start_date=now,
        confidence_before=hypothesis.prior_strength,
    )

    db.add(intervention)
    db.flush()

    experiment = ExperimentRun(
        user_id=user_id,
        intervention_id=intervention.id,
        target_metric=target_metric,
        baseline_start=now - timedelta(days=14),
        baseline_end=now,
        followup_start=now,
        followup_end=now + timedelta(days=14),
    )

    db.add(experiment)
    db.commit()

    return experiment

