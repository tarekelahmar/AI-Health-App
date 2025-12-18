import asyncio
from datetime import datetime, timedelta

from app.integrations.providers.demo import DemoProvider
from app.integrations.base import HealthDataProvider


def test_demo_provider_is_subclass():
    assert issubclass(DemoProvider, HealthDataProvider)


def test_demo_provider_supported_metrics_non_empty():
    provider = DemoProvider()
    metrics = provider.get_supported_metrics()
    assert isinstance(metrics, list)
    assert len(metrics) > 0


def test_demo_provider_fetch_data_shapes():
    provider = DemoProvider(seed=123)
    end = datetime.utcnow()
    start = end - timedelta(days=3)

    async def _run():
        return await provider.fetch_data(
            user_id=1,
            start=start,
            end=end,
            metrics=provider.get_supported_metrics(),
        )

    points = asyncio.run(_run())
    assert len(points) > 0
    # All points should have correct user_id/source and metric types in supported list.
    supported = set(provider.get_supported_metrics())
    for p in points:
        assert p.user_id == 1
        assert p.source == "demo"
        assert p.metric_type in supported


