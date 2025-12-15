"""Repository for OAuth state tokens."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.domain.models.oauth_state import OAuthState


class OAuthStateRepository:
    """Repository for OAuth state tokens."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(
        self,
        *,
        user_id: int,
        provider: str,
        state_token: str,
        ttl_seconds: int = 600,  # 10 minutes default
    ) -> OAuthState:
        """Create a new OAuth state token."""
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        state = OAuthState(
            user_id=user_id,
            provider=provider,
            state_token=state_token,
            expires_at=expires_at,
        )
        self.db.add(state)
        self.db.commit()
        self.db.refresh(state)
        return state
    
    def get_and_consume(
        self,
        *,
        user_id: int,
        provider: str,
        state_token: str,
    ) -> Optional[OAuthState]:
        """
        Get and consume (delete) an OAuth state token.
        Returns None if not found or expired.
        """
        now = datetime.utcnow()
        state = (
            self.db.query(OAuthState)
            .filter(
                and_(
                    OAuthState.user_id == user_id,
                    OAuthState.provider == provider,
                    OAuthState.state_token == state_token,
                    OAuthState.expires_at > now,  # Not expired
                )
            )
            .first()
        )
        
        if state:
            # Consume (delete) the state token (one-time use)
            self.db.delete(state)
            self.db.commit()
        
        return state
    
    def cleanup_expired(self) -> int:
        """Delete expired state tokens. Returns count deleted."""
        now = datetime.utcnow()
        deleted = (
            self.db.query(OAuthState)
            .filter(OAuthState.expires_at <= now)
            .delete()
        )
        self.db.commit()
        return deleted

