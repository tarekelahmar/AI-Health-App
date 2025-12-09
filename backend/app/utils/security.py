"""Security utilities: authentication, encryption, etc."""
from passlib.context import CryptContext
from typing import Optional
import secrets


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def generate_api_key() -> str:
    """Generate a secure API key"""
    return secrets.token_urlsafe(32)


def encrypt_sensitive_data(data: str) -> str:
    """Encrypt sensitive health data"""
    # TODO: Implement encryption (AES, etc.)
    return data


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """Decrypt sensitive health data"""
    # TODO: Implement decryption
    return encrypted_data

