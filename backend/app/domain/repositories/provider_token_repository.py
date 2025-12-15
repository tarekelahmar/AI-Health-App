from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.domain.models.provider_token import ProviderToken


class ProviderTokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: int, provider: str) -> Optional[ProviderToken]:
        return (
            self.db.query(ProviderToken)
            .filter(ProviderToken.user_id == user_id, ProviderToken.provider == provider)
            .first()
        )

    def upsert(
        self,
        user_id: int,
        provider: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        token_type: Optional[str] = None,
        scope: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> ProviderToken:
        existing = self.get(user_id=user_id, provider=provider)
        if existing:
            existing.access_token = access_token
            existing.refresh_token = refresh_token
            existing.token_type = token_type
            existing.scope = scope
            existing.expires_at = expires_at
            self.db.add(existing)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        token = ProviderToken(
            user_id=user_id,
            provider=provider,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=token_type,
            scope=scope,
            expires_at=expires_at,
        )
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def delete(self, user_id: int, provider: str) -> None:
        existing = self.get(user_id=user_id, provider=provider)
        if existing:
            self.db.delete(existing)
            self.db.commit()
