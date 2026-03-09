from __future__ import annotations

from fastapi import APIRouter

from app.integrations.registry import list_providers, get_provider_class

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/health", summary="List provider health")
async def list_provider_health() -> dict:
    """
    Minimal provider wiring / health introspection.

    Returns a simple view of registered providers and whether they are instantiable.
    This is NOT a full health check; it's a governance/debug tool to see wiring.
    """
    providers = []
    for name in list_providers():
        cls = get_provider_class(name)
        ok = True
        error: str | None = None
        try:
            # Try to instantiate with no args; if the provider requires args,
            # adapt its __init__ signature or create a default factory.
            cls()  # type: ignore[call-arg]
        except Exception as exc:  # pragma: no cover - debug info only
            ok = False
            error = str(exc)

        providers.append(
            {
                "name": name,
                "ok": ok,
                "error": error,
            }
        )

    return {"providers": providers}


