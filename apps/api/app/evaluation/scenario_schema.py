import re
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings

_SCHEMA_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_READONLY_ROLE = "rootlens_readonly"


def scenario_schema_name(scenario_id: str) -> str:
    name = f"scenario_{scenario_id.replace('-', '_')}"
    if not _SCHEMA_NAME_RE.match(name):
        raise ValueError(f"unsafe schema name derived from scenario_id: {scenario_id!r}")
    return name


def provision_scenario_schema(session: Session, schema_name: str) -> None:
    """Clones `orders` only — the other business tables are untouched and
    resolved from `public` via the search_path fallback (Milestone 5 plan's
    scenario-isolation design; all three incident templates only ever
    mutate orders). Also grants rootlens_readonly access to the new
    schema (Milestone 6): ADR-0004's default privileges only ever covered
    `public`, so without this, switching the engine's analytics reads to
    the readonly role (ADR-0007) would make every scenario investigation
    fail with permission-denied on its own clone."""
    session.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
    session.execute(text(f'DROP TABLE IF EXISTS "{schema_name}".orders'))
    session.execute(text(f'CREATE TABLE "{schema_name}".orders AS TABLE public.orders'))
    session.execute(text(f'GRANT USAGE ON SCHEMA "{schema_name}" TO {_READONLY_ROLE}'))
    session.execute(
        text(f'GRANT SELECT ON ALL TABLES IN SCHEMA "{schema_name}" TO {_READONLY_ROLE}')
    )
    session.commit()


def teardown_scenario_schema(session: Session, schema_name: str) -> None:
    session.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
    session.commit()


@contextmanager
def scenario_sessions(schema_name: str) -> Iterator[tuple[Session, Session]]:
    """Yields (write_session, readonly_session), both bound to engines
    whose connections resolve unqualified table names against
    `schema_name` first, falling back to `public` — set via each
    connection's startup `search_path` option rather than a `SET
    search_path` statement, because run_investigation() commits multiple
    times and each commit returns the connection to the pool; only
    connect-time options are guaranteed to reapply on the next checkout
    from these dedicated engines."""
    settings = Settings()
    search_path_option = {"options": f"-c search_path={schema_name},public"}
    write_engine: Engine = create_engine(settings.database_url, connect_args=search_path_option)
    readonly_engine: Engine = create_engine(
        settings.database_url_readonly, connect_args=search_path_option
    )
    write_session = sessionmaker(bind=write_engine, autoflush=False, expire_on_commit=False)()
    readonly_session = sessionmaker(bind=readonly_engine, autoflush=False, expire_on_commit=False)()
    try:
        yield write_session, readonly_session
    finally:
        write_session.close()
        readonly_session.close()
        write_engine.dispose()
        readonly_engine.dispose()
