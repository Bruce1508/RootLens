from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings

_settings = Settings()

# Owner/write engine — Alembic migrations, the ingestion CLI, and (since
# Milestone 3) the investigations API for creating/updating investigation
# state, events, and hypotheses.
write_engine: Engine = create_engine(_settings.database_url)
WriteSessionLocal = sessionmaker(bind=write_engine, autoflush=False, expire_on_commit=False)

# Read-only engine — every FastAPI query endpoint and analytics tool (ADR-0004).
readonly_engine: Engine = create_engine(_settings.database_url_readonly)
ReadOnlySessionLocal = sessionmaker(bind=readonly_engine, autoflush=False, expire_on_commit=False)


def get_write_session() -> Generator[Session]:
    session = WriteSessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_readonly_session() -> Generator[Session]:
    session = ReadOnlySessionLocal()
    try:
        yield session
    finally:
        session.close()
