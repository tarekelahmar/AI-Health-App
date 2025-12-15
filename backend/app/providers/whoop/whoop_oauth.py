from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import requests

WHOOP_OAUTH_AUTHORIZE = "https://api.prod.whoop.com/oauth/oauth2/auth"
WHOOP_OAUTH_TOKEN = "https://api.prod.whoop.com/oauth/oauth2/token"


def build_whoop_authorize_url(client_id: str, redirect_uri: str, state: str, scope: str) -> str:
    # WHOOP uses standard OAuth2 authorize flow
    # response_type=code
    return (
        f"{WHOOP_OAUTH_AUTHORIZE}"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={scope}"
        f"&state={state}"
    )


def exchange_code_for_token(client_id: str, client_secret: str, code: str, redirect_uri: str) -> Dict[str, Any]:
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    r = requests.post(WHOOP_OAUTH_TOKEN, data=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def refresh_token(client_id: str, client_secret: str, refresh_token_value: str) -> Dict[str, Any]:
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token_value,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    r = requests.post(WHOOP_OAUTH_TOKEN, data=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def compute_expires_at(expires_in_seconds: Optional[int]) -> Optional[datetime]:
    if not expires_in_seconds:
        return None
    return datetime.utcnow() + timedelta(seconds=int(expires_in_seconds))

