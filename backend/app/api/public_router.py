from fastapi import APIRouter


def public_router(*, prefix: str, tags: list[str]) -> APIRouter:
    """
    Router with NO auth dependencies.
    Used for MVP/demo endpoints.
    """
    return APIRouter(prefix=prefix, tags=tags)

