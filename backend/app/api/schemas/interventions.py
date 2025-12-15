from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal

class InterventionCreate(BaseModel):
    user_id: int
    key: str
    name: str
    category: Optional[str] = None
    dosage: Optional[str] = None
    schedule: Optional[str] = None
    notes: Optional[str] = None

    # Optional safety context provided by UI (MVP)
    # (K3) this is NOT medical data; it's flags like pregnancy/meds, etc.
    user_flags: Optional[Dict[str, Any]] = None

class InterventionResponse(BaseModel):
    id: int
    user_id: int
    key: str
    name: str
    category: Optional[str] = None
    dosage: Optional[str] = None
    schedule: Optional[str] = None
    notes: Optional[str] = None

    # Safety persisted + returned (K3)
    safety_risk_level: Optional[Literal["low","moderate","high"]] = None
    safety_evidence_grade: Optional[Literal["A","B","C","D"]] = None
    safety_boundary: Optional[Literal["informational","lifestyle","experiment"]] = None
    safety_issues: Optional[List[Dict[str, Any]]] = None
    safety_notes: Optional[str] = None

    class Config:
        from_attributes = True
