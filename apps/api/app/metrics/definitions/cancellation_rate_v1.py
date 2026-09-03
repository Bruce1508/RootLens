from app.metrics.schemas import MetricDefinition

CANCELLATION_RATE_V1 = MetricDefinition(
    name="cancellation_rate",
    version="v1",
    display_name="Cancellation rate",
    sql_expression="COUNT(orders WHERE status IN ('canceled', 'unavailable')) / COUNT(orders)",
    grain="order",
    excluded_statuses=["canceled", "unavailable"],
    description=(
        "Cancelled or unavailable orders divided by all orders in the period, "
        "attributed by order_purchase_timestamp (PRD §10). Unlike product_revenue "
        "and orders, this metric's denominator includes cancelled/unavailable "
        "orders — excluded_statuses here names the numerator's statuses, not "
        "rows to exclude from the denominator."
    ),
)
