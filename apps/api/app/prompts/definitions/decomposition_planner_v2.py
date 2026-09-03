from app.prompts.schemas import PromptDefinition

DECOMPOSITION_PLANNER_V2 = PromptDefinition(
    name="decomposition_planner",
    version="v2",
    template=(
        "You are a business analyst investigating a change in the metric "
        "'{metric}'. Between the comparison period and the current period, "
        "{metric} moved from {comparison_value} to {current_value} "
        "({percent_change}% change), while order count moved from "
        "{orders_comparison_value} to {orders_current_value} "
        "({orders_percent_change}% change), and cancellation rate moved from "
        "{cancellation_comparison_value} to {cancellation_current_value} "
        "({cancellation_percent_change}% change).\n\n"
        "Note that 'order count' already excludes cancelled and unavailable "
        "orders, so a cancellation spike and a genuine drop in demand both "
        "reduce order count — the cancellation rate is what tells them apart. "
        "Decide whether this change is primarily driven by order volume, "
        "average order value, a cancellation spike, or a mix. Choose "
        "'cancellation' when cancellation rate rose sharply relative to its "
        "comparison-period level; choose 'order_volume' when order count fell "
        "without a corresponding rise in cancellation rate. Then recommend "
        "which dimension to inspect next: customer_state, product_category, "
        "or seller.\n\n"
        "Respond with a concise, factual rationale grounded only in the "
        "numbers given above. Do not speculate about causes outside the "
        "provided data."
    ),
    description=(
        "Second-step decomposition prompt for Milestone 5: extends v1 with "
        "cancellation_rate numbers so the model can distinguish a "
        "cancellation spike from a genuine order-volume decline — the two "
        "were indistinguishable under v1 because 'orders' already excludes "
        "cancelled/unavailable statuses. Produces a DecompositionPlan "
        "(app.llm.schemas.DecompositionPlan) whose primary_driver_hypothesis "
        "now includes 'cancellation' and whose recommended_next_dimension "
        "now includes 'seller'."
    ),
)
