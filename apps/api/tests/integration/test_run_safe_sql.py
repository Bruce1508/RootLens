from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.analytics.run_safe_sql import run_safe_sql
from app.analytics.sql_guardrails import UnsafeSqlError
from app.models import Customer, Order


def test_run_safe_sql_executes_a_valid_query_and_returns_a_tool_result(
    db_session: Session,
) -> None:
    db_session.add(
        Customer(
            customer_id="cust-1",
            customer_unique_id="cust-1-u",
            customer_zip_code_prefix="0",
            customer_city="c",
            customer_state="SP",
        )
    )
    db_session.add(
        Order(
            order_id="order-1",
            customer_id="cust-1",
            order_status="delivered",
            order_purchase_timestamp=datetime(2018, 1, 10),
            order_estimated_delivery_date=datetime(2018, 1, 20),
        )
    )
    db_session.flush()

    result = run_safe_sql(
        db_session, "SELECT order_id, order_status FROM orders", "inspect order statuses"
    )

    assert result.tool_name == "run_safe_sql"
    assert result.columns == ["order_id", "order_status"]
    assert result.rows == [{"order_id": "order-1", "order_status": "delivered"}]
    assert result.row_count == 1
    assert result.evidence_id
    assert "LIMIT" in result.sql


def test_run_safe_sql_raises_unsafe_sql_error_for_ddl(db_session: Session) -> None:
    with pytest.raises(UnsafeSqlError):
        run_safe_sql(db_session, "DROP TABLE orders", "malicious")


def test_run_safe_sql_raises_unsafe_sql_error_for_hidden_schema(db_session: Session) -> None:
    with pytest.raises(UnsafeSqlError):
        run_safe_sql(db_session, "SELECT * FROM eval.eval_scenarios", "peek at ground truth")
