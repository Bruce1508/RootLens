from app.prompts.schemas import PromptDefinition

DECOMPOSITION_PLANNER_V1 = PromptDefinition(
    name="decomposition_planner",
    version="v1",
    template=(
        "You are a business analyst investigating a change in the metric "
        "'{metric}'. Between the comparison period and the current period, "
        "{metric} moved from {comparison_value} to {current_value} "
        "({percent_change}% change), while order count moved from "
        "{orders_comparison_value} to {orders_current_value} "
        "({orders_percent_change}% change).\n\n"
        "Decide whether this change is primarily driven by order volume, "
        "average order value, or a mix of both. Then recommend which "
        "dimension to inspect next: customer_state or product_category.\n\n"
        "Respond with a concise, factual rationale grounded only in the "
        "numbers given above. Do not speculate about causes outside the "
        "provided data."
    ),
    description=(
        "First-step decomposition prompt for Milestone 2: given a metric's "
        "period-over-period change, produces a DecompositionPlan "
        "(app.llm.schemas.DecompositionPlan) identifying whether order "
        "volume or average order value is the primary driver, per FR-5's "
        "instruction to 'start with decomposition into order volume and "
        "average order value.'"
    ),
)
