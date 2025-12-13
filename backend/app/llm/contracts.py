from typing import TypedDict, Literal, Dict, Any


class LLMInsightInput(TypedDict):
    title: str
    summary: str
    metric_key: str
    confidence: float
    status: Literal["detected", "evaluated", "suggested"]
    evidence: Dict[str, Any]


class LLMInsightOutput(TypedDict):
    explanation: str
    uncertainty: str
    suggested_next_step: str

