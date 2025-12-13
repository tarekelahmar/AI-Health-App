from sqlalchemy.orm import Session

from app.domain.models.experiment_run import ExperimentRun
from app.domain.models.experiment_result import ExperimentResult
from app.engine.evaluation import evaluate_experiment
from app.core.signal import Signal


def run_evaluation(
    *,
    db: Session,
    experiment: ExperimentRun,
    signals: list[Signal],
) -> ExperimentResult:

    results = evaluate_experiment(experiment=experiment, signals=signals)

    row = ExperimentResult(
        experiment_run_id=experiment.id,
        baseline_mean=results["baseline_mean"],
        followup_mean=results["followup_mean"],
        delta=results["delta"],
        effect_size=results["effect_size"],
        confidence=results["confidence"],
        conclusion=results["conclusion"],
    )

    experiment.status = "complete"

    db.add(row)
    db.add(experiment)
    db.commit()

    return row

