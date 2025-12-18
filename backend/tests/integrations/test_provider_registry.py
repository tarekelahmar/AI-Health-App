from app.integrations.registry import (
    register_provider,
    get_provider_class,
    list_providers,
)
from app.integrations.base import HealthDataProvider


class DummyProvider(HealthDataProvider):
    name = "dummy"

    async def authenticate(self, auth_payload: dict):
        raise NotImplementedError

    async def fetch_data(self, user_id: int, start, end, metrics):
        return []

    def get_supported_metrics(self):
        return []

    def get_rate_limits(self):
        from app.integrations.base import RateLimitConfig

        return RateLimitConfig(requests_per_minute=1, burst_size=1)


def test_register_and_get_provider():
    # Register and retrieve a dummy provider; this should be idempotent.
    register_provider(DummyProvider.name, DummyProvider)
    cls = get_provider_class("dummy")
    assert cls is DummyProvider
    assert "dummy" in list_providers()


