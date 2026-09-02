import pytest


def test_get_metric_definition_returns_product_revenue_v1() -> None:
    from app.metrics.catalog import get_metric_definition

    definition = get_metric_definition("product_revenue")

    assert definition.name == "product_revenue"
    assert definition.version == "v1"
    assert definition.grain == "order_item"
    assert definition.excluded_statuses == ["canceled", "unavailable"]


def test_get_metric_definition_raises_for_unknown_metric() -> None:
    from app.metrics.catalog import get_metric_definition

    with pytest.raises(KeyError):
        get_metric_definition("nonexistent_metric")
