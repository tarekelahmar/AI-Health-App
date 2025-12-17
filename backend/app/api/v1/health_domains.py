from __future__ import annotations

from fastapi import HTTPException

from app.api.router_factory import make_v1_router
from app.api.schemas.health_domains import HealthDomainInfo, HealthDomainsResponse
from app.domain.health_domains import HEALTH_DOMAINS, HealthDomainKey

# Public, static metadata endpoint (safe to serve without user context).
# NOTE: This does not expose PHI; it exposes the canonical semantic map only.
router = make_v1_router(prefix="/api/v1/health-domains", tags=["health-domains"], public=True)


@router.get("", response_model=HealthDomainsResponse, summary="List canonical health domains (read-only)")
def list_health_domains() -> HealthDomainsResponse:
    items = []
    for dk, d in HEALTH_DOMAINS.items():
        items.append(
            HealthDomainInfo(
                key=dk,
                display_name=d.display_name,
                description=d.description,
                example_signals=list(d.signals[:3]),
            )
        )
    return HealthDomainsResponse(count=len(items), items=items)


@router.get("/{domain_key}", response_model=HealthDomainInfo, summary="Get a canonical health domain (read-only)")
def get_health_domain(domain_key: HealthDomainKey) -> HealthDomainInfo:
    d = HEALTH_DOMAINS.get(domain_key)
    if not d:
        raise HTTPException(status_code=404, detail="Domain not found")
    return HealthDomainInfo(
        key=domain_key,
        display_name=d.display_name,
        description=d.description,
        example_signals=list(d.signals[:3]),
    )


