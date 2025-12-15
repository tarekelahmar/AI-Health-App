from typing import List, Optional
from pydantic import BaseModel


class JobOut(BaseModel):
    id: str
    name: Optional[str] = None
    next_run_time: Optional[str] = None
    trigger: str


class JobsListOut(BaseModel):
    ok: bool = True
    enabled: bool
    running: bool
    jobs: List[JobOut]

