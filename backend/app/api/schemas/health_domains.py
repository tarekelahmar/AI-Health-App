from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from app.domain.health_domains import HealthDomainKey, InterventionType


class HealthDomainInfo(BaseModel):
    """
    Read-only domain explanation for interpretability.

    IMPORTANT:
    - Static metadata sourced from the canonical HEALTH_DOMAINS registry.
    - Non-diagnostic and non-prescriptive by design.
    """

    key: HealthDomainKey
    display_name: str
    description: str
    example_signals: List[str] = Field(default_factory=list)


class HealthDomainsResponse(BaseModel):
    count: int
    items: List[HealthDomainInfo]


