from typing import Literal

from pydantic import BaseModel


class DecompositionPlan(BaseModel):
    metric: str
    primary_driver_hypothesis: Literal[
        "order_volume", "average_order_value", "cancellation", "mixed"
    ]
    rationale: str
    recommended_next_dimension: Literal["customer_state", "product_category", "seller"]


class AdHocQueryDecision(BaseModel):
    """Milestone 6: the one point in the investigation loop where the LLM
    may request a guarded ad hoc SQL query (FR-7's run_safe_sql), offered
    only when the standard typed tools left the hypothesis inconclusive.
    query/purpose are required together with should_query=True."""

    should_query: bool
    query: str | None = None
    purpose: str | None = None
