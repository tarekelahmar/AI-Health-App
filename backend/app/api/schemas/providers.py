from __future__ import annotations

from pydantic import BaseModel
from typing import Optional, Dict, Any


class ProviderConnectResponse(BaseModel):
    provider: str
    authorize_url: str


class ProviderCallbackResponse(BaseModel):
    provider: str
    connected: bool


class ProviderSyncResponse(BaseModel):
    provider: str
    inserted: int
    rejected: int
    errors: list


class ProviderStatusResponse(BaseModel):
    provider: str
    connected: bool

