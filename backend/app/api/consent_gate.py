"""
Global consent and identity gate for safety-critical endpoints.

This module provides a dependency that enforces:
1. Authentication (401 if missing in private mode)
2. Valid consent (403 if missing or revoked)
3. Optional consent scope checks (provider-specific)

Usage:
    @router.post("/insights/run")
    def run_insights(
        user_id: int = Depends(require_user_and_consent),
        db: Session = Depends(get_db)
    ):
        # user_id is guaranteed to be authenticated and consented
        ...
"""
from __future__ import annotations

from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth_mode import get_request_user_id, is_private_mode, get_current_user_optional
from app.core.database import get_db
from app.domain.repositories.consent_repository import ConsentRepository


class ConsentGateError(HTTPException):
    """Machine-readable consent error with reason code"""
    def __init__(self, reason: str, detail: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            headers={"X-Consent-Error-Reason": reason}
        )


def require_user_and_consent(
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
    required_scope: Optional[str] = None,
) -> int:
    """
    Global gate: requires authentication + valid consent.
    
    Args:
        user_id: From get_request_user_id (already enforces auth in private mode)
        db: Database session
        required_scope: Optional consent scope to check:
            - "data_analysis": Requires consents_to_data_analysis
            - "experiments": Requires understands_recommendations_experimental
            - "whoop", "fitbit", "oura": Requires provider-specific consent
    
    Returns:
        user_id: Guaranteed to be authenticated and consented
    
    Raises:
        HTTPException 401: In private mode, if no valid JWT
        HTTPException 403: If consent missing, revoked, or scope not granted
            Headers include X-Consent-Error-Reason for machine-readable error codes
    """
    # Authentication is already enforced by get_request_user_id in private mode
    # In public mode, user_id is required as query param
    
    # Check consent validity
    consent_repo = ConsentRepository(db)
    consent = consent_repo.get_latest(user_id)
    
    if not consent:
        raise ConsentGateError(
            reason="no_consent",
            detail="Consent required. Please complete onboarding and provide consent before using this feature."
        )
    
    # Check if consent is revoked
    if consent.revoked_at:
        raise ConsentGateError(
            reason="consent_revoked",
            detail=f"Consent has been revoked. Reason: {consent.revocation_reason or 'Not specified'}"
        )
    
    # Check required scope
    if required_scope:
        scope_lower = required_scope.lower()
        
        if scope_lower == "data_analysis":
            if not consent.consents_to_data_analysis:
                raise ConsentGateError(
                    reason="scope_data_analysis_denied",
                    detail="Consent for data analysis is required for this operation."
                )
        
        elif scope_lower == "experiments":
            if not consent.understands_recommendations_experimental:
                raise ConsentGateError(
                    reason="scope_experiments_denied",
                    detail="Consent for experimental recommendations is required for this operation."
                )
        
        elif scope_lower in ("whoop", "fitbit", "oura"):
            # Provider-specific consent check
            provider_consent_map = {
                "whoop": consent.consents_to_whoop_ingestion,
                "fitbit": consent.consents_to_fitbit_ingestion,
                "oura": consent.consents_to_oura_ingestion,
            }
            if not provider_consent_map.get(scope_lower, False):
                raise ConsentGateError(
                    reason=f"scope_provider_{scope_lower}_denied",
                    detail=f"Consent for {scope_lower.upper()} data ingestion is required for this operation."
                )
        
        else:
            # Unknown scope - default to requiring general data analysis consent
            if not consent.consents_to_data_analysis:
                raise ConsentGateError(
                    reason="scope_unknown_denied",
                    detail="Consent for data analysis is required for this operation."
                )
    else:
        # No specific scope required, but general data analysis consent is always required
        if not consent.consents_to_data_analysis:
            raise ConsentGateError(
                reason="scope_data_analysis_denied",
                detail="Consent for data analysis is required for this operation."
            )
    
    return user_id


# Convenience functions for common consent scopes
def require_user_and_consent_for_experiments(
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
) -> int:
    """
    Requires authentication + consent with experiments scope.
    
    Use for endpoints that create/run experiments or protocols.
    """
    return require_user_and_consent(user_id=user_id, db=db, required_scope="experiments")


def require_user_and_consent_for_whoop(
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
) -> int:
    """
    Requires authentication + consent with WHOOP provider scope.
    
    Use for endpoints that sync or access WHOOP data.
    """
    return require_user_and_consent(user_id=user_id, db=db, required_scope="whoop")

