from typing import Any

from sqlalchemy import Select
from sqlalchemy.orm import InstrumentedAttribute

from app.models import Customer, Order, OrderItem, Product

# Dimension name -> (join clause producer, group-by column). Kept small
# and explicit for Milestone 1's two supported dimensions; more are added
# alongside their FR-7 tool coverage, not preemptively.
DIMENSIONS: dict[str, str] = {
    "customer_state": "Customer state",
    "product_category": "Product category (English name not resolved here; raw category slug)",
}


def list_available_dimensions() -> list[str]:
    return list(DIMENSIONS.keys())


def dimension_column(dimension: str) -> InstrumentedAttribute[Any]:
    if dimension == "customer_state":
        return Customer.customer_state
    if dimension == "product_category":
        return Product.product_category_name
    raise NotImplementedError(f"unsupported dimension: {dimension!r}")


def apply_dimension_joins(stmt: Select, dimension: str) -> Select:
    if dimension == "customer_state":
        return stmt.join(Customer, Customer.customer_id == Order.customer_id)
    if dimension == "product_category":
        return stmt.join(Product, Product.product_id == OrderItem.product_id)
    raise NotImplementedError(f"unsupported dimension: {dimension!r}")
