from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, List, Optional, Dict, Any


@dataclass(frozen=True)
class NormalizedPoint:
    metric_type: str           # must match metric_registry key
    value: float
    unit: str
    timestamp: datetime
    source: str                # "whoop"
    metadata: Dict[str, Any]   # raw ids, etc.


class ProviderAdapter(Protocol):
    provider_name: str

    def build_authorize_url(self, state: str) -> str: ...
    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]: ...
    def refresh_access_token_if_needed(self, user_id: int) -> None: ...
    def fetch_and_normalize(self, user_id: int, since: Optional[datetime] = None) -> List[NormalizedPoint]: ...
