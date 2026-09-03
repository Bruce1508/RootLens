from datetime import date
from typing import Literal

from pydantic import BaseModel

Template = Literal["cancellation_spike", "order_volume_decline", "seller_category_decline"]
Split = Literal["dev", "held_out"]

# Ground-truth driver vocabulary is deliberately the *engine's* vocabulary
# (app.llm.schemas.DecompositionPlan.primary_driver_hypothesis), not the
# incident template name — a seller/category decline is still, at the
# primary_driver_hypothesis level, a genuine order_volume decline; what
# makes it a distinct template is *where* the decline is localized
# (dimensions), not a different top-level driver type the engine could
# express. Root-cause accuracy compares against this vocabulary;
# dimension accuracy compares separately against `dimensions`.
PrimaryDriver = Literal["order_volume", "cancellation"]

# Sentinel for a `dimensions` value that isn't known until seed time —
# seller IDs are opaque dataset values, so seller-flavored
# seller_category_decline scenarios describe *how* to pick one (the top
# seller within a given product_category during the incident month) rather
# than naming one; app.evaluation.seed resolves it against real data.
SELLER_TO_RESOLVE = "<resolve:top_seller_in_category>"


class ScenarioSpec(BaseModel):
    scenario_id: str
    template: Template
    metric: str = "product_revenue"
    current_period_start: date
    current_period_end: date
    comparison_period_start: date
    comparison_period_end: date
    split: Split
    seed: int
    severity: Literal["low", "medium", "high"] | None = None
    is_unanswerable: bool = False
    question: str | None = None

    # Ground truth (app.evaluation.seed writes these into
    # eval.eval_ground_truth; None fields apply only to unanswerable
    # scenarios, which are scored on abstention accuracy alone).
    direction: Literal["increase", "decrease"] | None = None
    primary_driver: PrimaryDriver | None = None
    dimensions: dict[str, str] = {}
    notes: str | None = None
