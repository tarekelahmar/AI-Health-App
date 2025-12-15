"""
Token encryption service for provider tokens.

SECURITY FIX (Risk #3): Encrypt provider tokens at rest.
Uses Fernet symmetric encryption (MVP). Production should use KMS/Envelope encryption.
"""

from __future__ import annotations

import os
import base64
import logging
from typing import Optional

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    Fernet = None  # type: ignore

logger = logging.getLogger(__name__)


class TokenEncryptionService:
    """
    Encrypts/decrypts provider tokens.
    
    SECURITY: Uses Fernet symmetric encryption with key derived from SECRET_KEY.
    For production, consider using AWS KMS, Google Cloud KMS, or similar.
    """
    
    def __init__(self):
        if not CRYPTOGRAPHY_AVAILABLE:
            logger.warning("cryptography library not available. Token encryption disabled.")
            self._fernet: Optional[Fernet] = None
            return
        
        # Derive encryption key from SECRET_KEY
        secret_key = os.getenv("SECRET_KEY", "")
        if not secret_key:
            logger.warning("SECRET_KEY not set. Token encryption disabled.")
            self._fernet = None
            return
        
        try:
            # Derive a 32-byte key from SECRET_KEY using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"provider_token_encryption_salt",  # Fixed salt for MVP (should be random in production)
                iterations=100000,
                backend=default_backend(),
            )
            key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
            self._fernet = Fernet(key)
        except Exception as e:
            logger.error(f"Failed to initialize token encryption: {e}")
            self._fernet = None
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a token.
        
        Returns encrypted string, or original if encryption unavailable.
        """
        if not self._fernet or not plaintext:
            return plaintext
        
        try:
            encrypted = self._fernet.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Token encryption failed: {e}")
            # SECURITY: Fail safe - don't store unencrypted tokens
            raise ValueError(f"Token encryption failed: {e}")
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a token.
        
        Returns decrypted string, or original if decryption unavailable.
        """
        if not self._fernet or not ciphertext:
            return ciphertext
        
        try:
            decrypted = self._fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Token decryption failed: {e}")
            # If decryption fails, token may be unencrypted (legacy) or corrupted
            # For MVP, return original (but log warning)
            logger.warning("Token decryption failed - may be unencrypted legacy token")
            return ciphertext
    
    def redact(self, token: Optional[str]) -> str:
        """
        Redact token for logging (show only first/last 4 chars).
        
        Returns redacted string safe for logging.
        """
        if not token:
            return "[empty]"
        if len(token) <= 8:
            return "[redacted]"
        return f"{token[:4]}...{token[-4:]}"


# Global instance
_encryption_service: Optional[TokenEncryptionService] = None


def get_encryption_service() -> TokenEncryptionService:
    """Get or create encryption service instance."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = TokenEncryptionService()
    return _encryption_service

