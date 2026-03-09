from app.integrations.providers.whoop_provider import WhoopProvider
from app.integrations.base import HealthDataProvider


def test_whoop_provider_is_subclass():
    assert issubclass(WhoopProvider, HealthDataProvider)


def test_whoop_provider_supported_metrics_non_empty():
    provider = WhoopProvider()
    metrics = provider.get_supported_metrics()
    assert isinstance(metrics, list)
    assert len(metrics) > 0


