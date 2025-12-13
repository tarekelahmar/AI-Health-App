from typing import List

from app.engine.change_detection import ChangeEvent
from app.engine.hypothesis_map import HYPOTHESIS_MAP, HypothesisCandidate
from app.core.signal import Signal


class GeneratedHypothesis:
    def __init__(
        self,
        trigger_metric: str,
        factor: str,
        prior_strength: float,
        supporting_evidence: List[str],
        rationale: str,
    ):
        self.trigger_metric = trigger_metric
        self.factor = factor
        self.prior_strength = prior_strength
        self.supporting_evidence = supporting_evidence
        self.rationale = rationale


def generate_hypotheses(
    *,
    change: ChangeEvent,
    signals: List[Signal],
) -> List[GeneratedHypothesis]:

    candidates = HYPOTHESIS_MAP.get(change.metric_key, [])

    hypotheses: List[GeneratedHypothesis] = []

    for candidate in candidates:
        evidence = [
            f"{candidate.factor} observed"
            for s in signals
            if s.metric_key == candidate.factor
        ]

        hypotheses.append(
            GeneratedHypothesis(
                trigger_metric=change.metric_key,
                factor=candidate.factor,
                prior_strength=candidate.prior_strength,
                supporting_evidence=evidence,
                rationale=candidate.rationale,
            )
        )

    return hypotheses

