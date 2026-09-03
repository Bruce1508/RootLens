import re
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings

_SCHEMA_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def scenario_schema_name(scenario_id: str) -> str:
    name = f"scenario_{scenario_id.replace('-', '_')}"
    if not _SCHEMA_NAME_RE.match(name):
        raise ValueError(f"unsafe schema name derived from scenario_id: {scenario_id!r}")
    return name


def provision_scenario_schema(session: Session, schema_name: str) -> None:
    """Clones `orders` only — the other business tables are untouched and
    resolved from `public` via the search_path fallback (Milestone 5 plan's
    scenario-isolation design; all three incident templates only ever
    mutate orders)."""
    session.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
    session.execute(text(f'DROP TABLE IF EXISTS "{schema_name}".orders'))
    session.execute(text(f'CREATE TABLE "{schema_name}".orders AS TABLE public.orders'))
    session.commit()


def teardown_scenario_schema(session: Session, schema_name: str) -> None:
    session.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
    session.commit()


@contextmanager
def scenario_session(schema_name: str) -> Iterator[Session]:
    """A write-role session whose connections resolve unqualified table
    names against `schema_name` first, falling back to `public` — set via
    the connection's startup `search_path` option rather than a `SET
    search_path` statement, because run_investigation() commits multiple
    times and each commit returns the connection to the pool; only
    connect-time options are guaranteed to reapply on the next checkout
    from this dedicated engine."""
    settings = Settings()
    engine: Engine = create_engine(
        settings.database_url,
        connect_args={"options": f"-c search_path={schema_name},public"},
    )
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = session_local()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
