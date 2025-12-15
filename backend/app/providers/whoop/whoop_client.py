from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Any, Optional, List

import requests

WHOOP_API_BASE = "https://api.prod.whoop.com/developer/v1"


class WhoopClient:
    def __init__(self, access_token: str):
        self.access_token = access_token

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    def get_cycles(self, since: Optional[datetime] = None, limit: int = 50) -> List[Dict[str, Any]]:
        # WHOOP endpoints are paginated. We'll do minimal paging for MVP.
        params: Dict[str, Any] = {"limit": limit}
        if since:
            # WHOOP uses RFC3339 timestamps
            params["start"] = since.replace(microsecond=0).isoformat() + "Z"
        r = requests.get(f"{WHOOP_API_BASE}/cycle", headers=self._headers(), params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data.get("records", data if isinstance(data, list) else [])

    def get_sleep(self, since: Optional[datetime] = None, limit: int = 50) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": limit}
        if since:
            params["start"] = since.replace(microsecond=0).isoformat() + "Z"
        r = requests.get(f"{WHOOP_API_BASE}/activity/sleep", headers=self._headers(), params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data.get("records", data if isinstance(data, list) else [])

    def get_recovery(self, since: Optional[datetime] = None, limit: int = 50) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": limit}
        if since:
            params["start"] = since.replace(microsecond=0).isoformat() + "Z"
        r = requests.get(f"{WHOOP_API_BASE}/recovery", headers=self._headers(), params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data.get("records", data if isinstance(data, list) else [])

