from typing import Literal

from pydantic import BaseModel


class DecompositionPlan(BaseModel):
    metric: str
    primary_driver_hypothesis: Literal["order_volume", "average_order_value", "mixed"]
    rationale: str
    recommended_next_dimension: Literal["customer_state", "product_category"]
