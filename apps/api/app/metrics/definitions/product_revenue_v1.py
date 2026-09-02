from app.metrics.schemas import MetricDefinition

PRODUCT_REVENUE_V1 = MetricDefinition(
    name="product_revenue",
    version="v1",
    display_name="Product revenue",
    sql_expression="SUM(order_items.price)",
    grain="order_item",
    excluded_statuses=["canceled", "unavailable"],
    description=(
        "Sum of order_items.price for orders whose status is not "
        "'canceled' or 'unavailable', attributed by order_purchase_timestamp. "
        "Excludes freight_value and payment totals (§10 of the PRD: 'must not "
        "silently mix payment value with product revenue')."
    ),
)
