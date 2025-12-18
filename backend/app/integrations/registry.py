from __future__ import annotations

from typing import Dict, List, Type

from app.integrations.base import HealthDataProvider

# Simple in-memory registry. For now, no dynamic import magic – explicit wiring is safer.
_PROVIDER_REGISTRY: Dict[str, Type[HealthDataProvider]] = {}


def register_provider(name: str, provider_cls: Type[HealthDataProvider]) -> None:
    key = name.lower()
    if key in _PROVIDER_REGISTRY and _PROVIDER_REGISTRY[key] is not provider_cls:
        # Hard fail if we try to double-register with a different class.
        raise ValueError(f"Provider '{key}' already registered with a different class")
    _PROVIDER_REGISTRY[key] = provider_cls


def get_provider_class(name: str) -> Type[HealthDataProvider]:
    key = name.lower()
    if key not in _PROVIDER_REGISTRY:
        raise KeyError(f"Provider not registered: {name}")
    return _PROVIDER_REGISTRY[key]


def list_providers() -> List[str]:
    return sorted(_PROVIDER_REGISTRY.keys())


