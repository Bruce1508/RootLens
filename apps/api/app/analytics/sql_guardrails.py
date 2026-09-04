"""FR-8 SQL AST guardrails for app.analytics.run_safe_sql — the one place
in RootLens that ever executes LLM-generated SQL. Every other analytics
tool (compare_periods, segment_metric, calculate_contribution) is a
parameterized, hand-written query and never touches this module.

Default-deny on tables (an explicit allowlist of business tables) and on
functions: sqlglot parses every SQL construct it recognizes — including
things that aren't "functions" in any dangerous sense, like boolean OR/
AND/NOT, CASE/WHEN, and BETWEEN — into a *specific* expression class
(exp.Or, exp.Case, exp.Between, ...), several of which happen to subclass
exp.Func. A real, unrecognized function call — the shape genuinely
dangerous things like pg_sleep or dblink take — is the one case sqlglot
can't classify, surfacing as exp.Anonymous. So the guardrail here isn't
"is this Func type in an allowlist" (that rejects completely ordinary
queries — verified against a real Ollama-generated query that used CASE
WHEN and OR and got wrongly blocked before this was caught): it's simply
"reject exp.Anonymous," full stop, and allow every construct sqlglot
already had a name for.
"""

import sqlglot
from sqlglot import exp

MAX_JOINS = 5
MAX_ROWS = 500
STATEMENT_TIMEOUT_MS = 5000

_ALLOWED_TABLES = {
    "customers",
    "orders",
    "order_items",
    "payments",
    "products",
    "sellers",
    "reviews",
    "product_category_translations",
}


class UnsafeSqlError(ValueError):
    """Raised when a query fails an FR-8 guardrail. The message is safe
    to surface to the LLM for a correction attempt or to a user — it
    never contains connection strings or credentials."""


def _reject_comment_smuggling(query: str) -> None:
    if "--" in query or "/*" in query:
        raise UnsafeSqlError("query must not contain SQL comments")


def _parse_single_select(query: str) -> exp.Select:
    try:
        statements = sqlglot.parse(query, dialect="postgres")
    except Exception as exc:
        raise UnsafeSqlError(f"query failed to parse: {exc}") from exc

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise UnsafeSqlError("exactly one SQL statement is required")

    statement = statements[0]
    if not isinstance(statement, exp.Select):
        raise UnsafeSqlError(
            f"only a single SELECT (or CTE) statement is allowed, got {type(statement).__name__}"
        )
    return statement


def _check_tables(statement: exp.Select) -> None:
    for table in statement.find_all(exp.Table):
        # An unqualified reference to a CTE name (e.g. `x` in `WITH x AS
        # (...) SELECT * FROM x`) parses as an exp.Table too, with no
        # schema — allow those; only reject real schema-qualified escapes
        # and unqualified names outside the business-table allowlist.
        is_cte_alias = table.db == "" and any(
            cte.alias == table.name for cte in statement.find_all(exp.CTE)
        )
        if is_cte_alias:
            continue
        if table.db not in ("", "public") or table.name not in _ALLOWED_TABLES:
            raise UnsafeSqlError(f"table not allowed: {table.sql()}")


def _check_functions(statement: exp.Select) -> None:
    for func in statement.find_all(exp.Anonymous):
        raise UnsafeSqlError(f"function not allowed: {func.name}")


def _check_joins(statement: exp.Select) -> None:
    join_count = len(list(statement.find_all(exp.Join)))
    if join_count > MAX_JOINS:
        raise UnsafeSqlError(f"too many joins ({join_count} > {MAX_JOINS})")


def _bound_rows(statement: exp.Select) -> exp.Select:
    existing_limit = statement.args.get("limit")
    if existing_limit is not None:
        current = existing_limit.expression.this
        if int(current) <= MAX_ROWS:
            return statement
    return statement.limit(MAX_ROWS)


def validate_and_bound(query: str) -> str:
    """Returns a safe-to-execute, row-bounded SQL string, or raises
    UnsafeSqlError with the specific reason (FR-8: "Log validation
    failures" — callers should log str(exc), never the raw query alone
    if it might embed sensitive values, though in practice these queries
    only ever touch business data, not credentials)."""
    _reject_comment_smuggling(query)
    statement = _parse_single_select(query)
    _check_tables(statement)
    _check_functions(statement)
    _check_joins(statement)
    bounded = _bound_rows(statement)
    return bounded.sql(dialect="postgres")
