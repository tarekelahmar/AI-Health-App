from __future__ import annotations

from datetime import datetime

from typing import Optional

from pydantic import BaseModel, Field


class AdherenceLog(BaseModel):
    user_id: int
    experiment_id: int
    intervention_id: int
    taken: bool = True
    dose: Optional[str] = None
    dose_unit: Optional[str] = None
    notes: Optional[str] = None
    timestamp: Optional[datetime] = None


class AdherenceOut(BaseModel):
    id: int
    user_id: int
    experiment_id: int
    intervention_id: int
    taken: bool
    dose: Optional[str] = None
    dose_unit: Optional[str] = None
    notes: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True

