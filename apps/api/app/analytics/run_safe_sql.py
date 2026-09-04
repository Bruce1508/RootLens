import time
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.analytics.schemas import ToolResult
from app.analytics.sql_guardrails import MAX_ROWS, STATEMENT_TIMEOUT_MS, validate_and_bound


def _json_safe(value: Any) -> Any:
    # Unlike the other analytics tools, this one runs an arbitrary
    # ad hoc query, so its result can carry Decimal/date/datetime values
    # the JSONB column's default json.dumps serializer can't handle —
    # the other tools avoid this by always building their own rows from
    # already-cast floats.
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


def run_safe_sql(session: Session, query: str, purpose: str) -> ToolResult:
    """FR-7's escape-valve tool for exceptional analyses the deterministic
    tools don't cover — every guardrail from FR-8 is enforced in
    app.analytics.sql_guardrails before this ever reaches the database.
    Raises app.analytics.sql_guardrails.UnsafeSqlError if the query fails
    validation; callers (app.investigations.engine) are responsible for
    the FR-8 "no more than two correction attempts" retry policy."""
    bounded_sql = validate_and_bound(query)

    started = time.perf_counter()
    session.execute(text(f"SET LOCAL statement_timeout = '{STATEMENT_TIMEOUT_MS}'"))
    result = session.execute(text(bounded_sql))
    columns = list(result.keys())
    rows = [
        {key: _json_safe(value) for key, value in row.items()} for row in result.mappings().all()
    ]
    elapsed_ms = (time.perf_counter() - started) * 1000

    return ToolResult(
        evidence_id=str(uuid.uuid4()),
        tool_name="run_safe_sql",
        params={"query": query, "purpose": purpose},
        sql=bounded_sql,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        execution_ms=elapsed_ms,
        warnings=([f"result truncated to {MAX_ROWS} rows"] if len(rows) == MAX_ROWS else []),
    )
