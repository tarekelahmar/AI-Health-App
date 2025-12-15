from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
import logging

from app.domain.models.provider_token import ProviderToken
from app.core.encryption import get_encryption_service

logger = logging.getLogger(__name__)


class ProviderTokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: int, provider: str) -> Optional[ProviderToken]:
        """
        Get provider token and decrypt it.
        
        SECURITY FIX (Risk #3): Tokens are encrypted at rest, decrypted on read.
        """
        token = (
            self.db.query(ProviderToken)
            .filter(ProviderToken.user_id == user_id, ProviderToken.provider == provider)
            .first()
        )
        
        if token:
            # Decrypt tokens before returning
            enc_service = get_encryption_service()
            try:
                token.access_token = enc_service.decrypt(token.access_token)
                if token.refresh_token:
                    token.refresh_token = enc_service.decrypt(token.refresh_token)
            except Exception as e:
                logger.error(f"Token decryption failed for user_id={user_id}, provider={provider}: {e}")
                # Return token anyway (may be unencrypted legacy)
        
        return token

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
        """
        Upsert provider token with encryption.
        
        SECURITY FIX (Risk #3): Tokens are encrypted before storing.
        """
        # SECURITY: Encrypt tokens before storing
        enc_service = get_encryption_service()
        encrypted_access_token = enc_service.encrypt(access_token)
        encrypted_refresh_token = enc_service.encrypt(refresh_token) if refresh_token else None
        
        # SECURITY: Redact tokens from logs
        logger.info(
            "provider_token_upserted",
            extra={
                "user_id": user_id,
                "provider": provider,
                "access_token": enc_service.redact(access_token),
                "has_refresh_token": bool(refresh_token),
            },
        )
        
        existing = (
            self.db.query(ProviderToken)
            .filter(ProviderToken.user_id == user_id, ProviderToken.provider == provider)
            .first()
        )
        
        if existing:
            existing.access_token = encrypted_access_token
            existing.refresh_token = encrypted_refresh_token
            existing.token_type = token_type
            existing.scope = scope
            existing.expires_at = expires_at
            self.db.add(existing)
            self.db.commit()
            self.db.refresh(existing)
            
            # Decrypt for return (so caller gets plaintext)
            existing.access_token = access_token
            if refresh_token:
                existing.refresh_token = refresh_token
            return existing

        token = ProviderToken(
            user_id=user_id,
            provider=provider,
            access_token=encrypted_access_token,  # Store encrypted
            refresh_token=encrypted_refresh_token,  # Store encrypted
            token_type=token_type,
            scope=scope,
            expires_at=expires_at,
        )
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        
        # Decrypt for return (so caller gets plaintext)
        token.access_token = access_token
        if refresh_token:
            token.refresh_token = refresh_token
        return token

    def delete(self, user_id: int, provider: str) -> None:
        existing = self.get(user_id=user_id, provider=provider)
        if existing:
            self.db.delete(existing)
            self.db.commit()
