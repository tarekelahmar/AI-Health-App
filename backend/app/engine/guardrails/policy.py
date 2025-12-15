from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class GuardrailPolicy:
    min_confidence: float
    min_coverage: float
    min_effect_size: float
    require_multi_signal: bool


DEFAULT_POLICY = GuardrailPolicy(
    min_confidence=0.6,
    min_coverage=0.5,
    min_effect_size=0.2,
    require_multi_signal=True,
)


METRIC_POLICIES: Dict[str, GuardrailPolicy] = {
    "sleep_duration": GuardrailPolicy(
        min_confidence=0.6,
        min_coverage=0.6,
        min_effect_size=0.2,
        require_multi_signal=True,
    ),
    "resting_hr": GuardrailPolicy(
        min_confidence=0.7,
        min_coverage=0.5,
        min_effect_size=0.25,
        require_multi_signal=True,
    ),
}


def get_policy(metric_key: str) -> GuardrailPolicy:
    return METRIC_POLICIES.get(metric_key, DEFAULT_POLICY)

