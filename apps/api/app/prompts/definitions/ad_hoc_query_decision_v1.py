from app.prompts.schemas import PromptDefinition

_SCHEMA_DESCRIPTION = (
    "orders(order_id, customer_id, order_status, order_purchase_timestamp, "
    "order_approved_at, order_delivered_carrier_date, order_delivered_customer_date, "
    "order_estimated_delivery_date)\n"
    "order_items(order_id, order_item_id, product_id, seller_id, shipping_limit_date, "
    "price, freight_value)\n"
    "customers(customer_id, customer_unique_id, customer_zip_code_prefix, "
    "customer_city, customer_state)\n"
    "products(product_id, product_category_name, product_weight_g, "
    "product_length_cm, product_height_cm, product_width_cm)\n"
    "sellers(seller_id, seller_zip_code_prefix, seller_city, seller_state)\n"
    "payments(order_id, payment_sequential, payment_type, payment_installments, "
    "payment_value)\n"
    "reviews(review_id, order_id, review_score, review_creation_date, "
    "review_answer_timestamp)\n"
    "product_category_translations(product_category_name, product_category_name_english)"
)

AD_HOC_QUERY_DECISION_V1 = PromptDefinition(
    name="ad_hoc_query_decision",
    version="v1",
    template=(
        "You are investigating a change in '{metric}'. The evidence gathered "
        "so far was inconclusive: {hypothesis_statement}\n\n"
        "You may request exactly one additional read-only SQL query against "
        "these tables if — and only if — it would meaningfully clarify the "
        "primary driver:\n\n"
        f"{_SCHEMA_DESCRIPTION}\n\n"
        "Rules: a single SELECT statement only (a WITH ... SELECT CTE is "
        "fine), no other statement type, no comments, no more than 5 joins, "
        "no functions beyond simple aggregates (count, sum, avg, max, min, "
        "coalesce, cast, extract, abs, round). The current period is "
        "{current_period_start}..{current_period_end}, the comparison period "
        "is {comparison_period_start}..{comparison_period_end}.\n\n"
        "Set should_query to false if no additional query would help — do "
        "not force one. If should_query is true, both query and purpose are "
        "required."
    ),
    description=(
        "Milestone 6 ad hoc SQL decision prompt: offered only after "
        "_resolve_hypothesis leaves status 'inconclusive', giving the LLM "
        "one bounded opportunity to request app.analytics.run_safe_sql "
        "(FR-7) before the engine falls back to its existing "
        "abstain/interpret path. Produces an AdHocQueryDecision "
        "(app.llm.schemas.AdHocQueryDecision)."
    ),
)
