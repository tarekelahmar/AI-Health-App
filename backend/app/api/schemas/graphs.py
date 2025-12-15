from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


DriverKind = Literal["metric", "intervention", "behavior"]


class GraphDriverEdge(BaseModel):
    driver_key: str
    driver_kind: DriverKind
    target_metric_key: str
    lag_days: int
    direction: str
    effect_size: float
    confidence: float = Field(ge=0.0, le=1.0)
    coverage: float = Field(ge=0.0, le=1.0)
    confounder_penalty: float
    interaction_boost: float
    score: float
    details: Dict[str, Any]


class DriversResponse(BaseModel):
    user_id: int
    target_metric_key: str
    items: List[GraphDriverEdge]


class SnapshotResponse(BaseModel):
    user_id: int
    snapshot: Dict[str, Any]

