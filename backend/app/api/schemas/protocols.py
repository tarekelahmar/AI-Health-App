from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Literal

class ProtocolCreate(BaseModel):
    user_id: int
    title: str
    description: Optional[str] = None
    interventions: Optional[List[Dict[str, Any]]] = None  # MVP: list of intervention payloads

class ProtocolResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str] = None
    status: str
    version: int
    interventions: Optional[List[Dict[str, Any]]] = None
    safety_summary: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
