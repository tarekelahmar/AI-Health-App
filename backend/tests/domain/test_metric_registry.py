from app.domain.metrics.registry import (
    get_metric_spec,
    list_metrics,
    METRIC_REGISTRY,
)


def test_registry_contains_sleep_duration():
    assert "sleep_duration" in METRIC_REGISTRY


def test_get_metric_spec_valid():
    spec = get_metric_spec("sleep_duration")
    assert spec.display_name == "Sleep Duration"


def test_get_metric_spec_invalid():
    try:
        get_metric_spec("unknown_metric")
        assert False, "Expected KeyError"
    except KeyError:
        assert True


def test_list_metrics():
    assert isinstance(list_metrics(), list)
    assert len(list_metrics()) > 0


