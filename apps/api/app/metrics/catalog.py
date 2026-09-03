from app.metrics.definitions.cancellation_rate_v1 import CANCELLATION_RATE_V1
from app.metrics.definitions.product_revenue_v1 import PRODUCT_REVENUE_V1
from app.metrics.schemas import MetricDefinition

_CATALOG: dict[str, MetricDefinition] = {
    PRODUCT_REVENUE_V1.name: PRODUCT_REVENUE_V1,
    CANCELLATION_RATE_V1.name: CANCELLATION_RATE_V1,
}


def get_metric_definition(name: str) -> MetricDefinition:
    return _CATALOG[name]


def list_metric_names() -> list[str]:
    return list(_CATALOG.keys())
