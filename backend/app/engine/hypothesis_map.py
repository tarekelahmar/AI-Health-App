from typing import List


class HypothesisCandidate:
    def __init__(
        self,
        factor: str,
        prior_strength: float,  # 0.0 – 1.0
        rationale: str,
    ):
        self.factor = factor
        self.prior_strength = prior_strength
        self.rationale = rationale


HYPOTHESIS_MAP = {

    # ── Sleep degradation ──────────────────────
    "sleep_duration": [
        HypothesisCandidate(
            factor="magnesium_serum",
            prior_strength=0.6,
            rationale="Magnesium plays a role in sleep regulation",
        ),
        HypothesisCandidate(
            factor="vitamin_d_25oh",
            prior_strength=0.3,
            rationale="Low vitamin D is sometimes associated with sleep issues",
        ),
        HypothesisCandidate(
            factor="sleep_quality",
            prior_strength=0.5,
            rationale="Subjective sleep quality aligns with objective duration",
        ),
    ],

    # ── Recovery ───────────────────────────────
    "hrv_rmssd": [
        HypothesisCandidate(
            factor="magnesium_serum",
            prior_strength=0.5,
            rationale="Magnesium affects autonomic nervous system balance",
        ),
    ],

}

