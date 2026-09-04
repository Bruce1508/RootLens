import pytest

from app.analytics.sql_guardrails import MAX_ROWS, UnsafeSqlError, validate_and_bound


def test_accepts_simple_select_on_an_allowed_table() -> None:
    result = validate_and_bound("SELECT order_id FROM orders WHERE order_status = 'delivered'")
    assert "orders" in result
    assert f"LIMIT {MAX_ROWS}" in result


def test_accepts_cte_referencing_allowed_tables() -> None:
    result = validate_and_bound("WITH recent AS (SELECT order_id FROM orders) SELECT * FROM recent")
    assert "recent" in result


def test_rejects_ddl() -> None:
    with pytest.raises(UnsafeSqlError, match="only a single SELECT"):
        validate_and_bound("DROP TABLE orders")


def test_rejects_dml() -> None:
    with pytest.raises(UnsafeSqlError, match="only a single SELECT"):
        validate_and_bound("INSERT INTO orders SELECT * FROM orders")


def test_rejects_multiple_statements() -> None:
    with pytest.raises(UnsafeSqlError, match="exactly one SQL statement"):
        validate_and_bound("SELECT * FROM orders; SELECT * FROM customers")


def test_rejects_comment_smuggling() -> None:
    with pytest.raises(UnsafeSqlError, match="comments"):
        validate_and_bound("SELECT * FROM orders -- sneaky\n")


def test_rejects_hidden_eval_schema() -> None:
    with pytest.raises(UnsafeSqlError, match="table not allowed"):
        validate_and_bound("SELECT * FROM eval.eval_scenarios")


def test_rejects_system_catalog() -> None:
    with pytest.raises(UnsafeSqlError, match="table not allowed"):
        validate_and_bound("SELECT * FROM pg_catalog.pg_tables")


def test_rejects_unknown_table() -> None:
    with pytest.raises(UnsafeSqlError, match="table not allowed"):
        validate_and_bound("SELECT * FROM investigations")


def test_rejects_unallowlisted_function() -> None:
    with pytest.raises(UnsafeSqlError, match="function not allowed"):
        validate_and_bound("SELECT pg_sleep(5)")


def test_allows_known_safe_aggregate_functions() -> None:
    result = validate_and_bound("SELECT count(*), sum(price) FROM order_items")
    assert "COUNT" in result
    assert "SUM" in result


def test_allows_boolean_or_and_not_in_where_clause() -> None:
    # Regression: sqlglot parses OR/AND/NOT into dedicated expression
    # classes that happen to subclass exp.Func — a real Ollama-generated
    # query using OR was wrongly rejected as "function not allowed: OR"
    # before this was caught and fixed.
    result = validate_and_bound(
        "SELECT * FROM orders WHERE order_status = 'delivered' "
        "OR order_status = 'shipped' AND NOT order_status = 'canceled'"
    )
    assert "orders" in result


def test_allows_case_when_expressions() -> None:
    result = validate_and_bound(
        "SELECT SUM(CASE WHEN order_status = 'delivered' THEN 1 ELSE 0 END) FROM orders"
    )
    assert "CASE" in result


def test_allows_between() -> None:
    result = validate_and_bound(
        "SELECT * FROM orders WHERE order_purchase_timestamp BETWEEN '2018-01-01' AND '2018-01-31'"
    )
    assert "BETWEEN" in result


def test_rejects_too_many_joins() -> None:
    query = (
        "SELECT o.order_id FROM orders o "
        "JOIN order_items oi ON oi.order_id = o.order_id "
        "JOIN customers c ON c.customer_id = o.customer_id "
        "JOIN products p ON p.product_id = oi.product_id "
        "JOIN sellers s ON s.seller_id = oi.seller_id "
        "JOIN payments pay ON pay.order_id = o.order_id "
        "JOIN reviews r ON r.order_id = o.order_id"
    )
    with pytest.raises(UnsafeSqlError, match="too many joins"):
        validate_and_bound(query)


def test_lowers_an_excessive_limit_to_the_max() -> None:
    result = validate_and_bound("SELECT * FROM orders LIMIT 1000000")
    assert f"LIMIT {MAX_ROWS}" in result


def test_keeps_a_limit_already_under_the_max() -> None:
    result = validate_and_bound("SELECT * FROM orders LIMIT 10")
    assert "LIMIT 10" in result


def test_rejects_invalid_sql() -> None:
    with pytest.raises(UnsafeSqlError):
        validate_and_bound("not valid sql at all (((")
