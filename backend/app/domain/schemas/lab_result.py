from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class LabResultCreate(BaseModel):
    test_name: str
    value: float
    unit: str
    reference_range: Optional[str] = None
    lab_name: Optional[str] = None

class LabResultResponse(BaseModel):
    id: int
    user_id: int
    test_name: str
    value: float
    unit: str
    reference_range: Optional[str]
    timestamp: datetime
    lab_name: Optional[str]

