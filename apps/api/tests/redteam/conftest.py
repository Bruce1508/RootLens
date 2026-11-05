import os
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# Mirrors tests/integration/conftest.py's TEST_DATABASE_URL pattern — the
# red-team suite's DB-role defense-in-depth check needs its own rootlens_readonly
# connection, separate from the rootlens_app db_session used everywhere else.
_TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://rootlens_app:changeme_app@localhost:5432/rootlens_test",
)
_TEST_DATABASE_URL_READONLY = os.environ.get(
    "TEST_DATABASE_URL_READONLY",
    "postgresql+psycopg://rootlens_readonly:changeme_readonly@localhost:5432/rootlens_test",
)
_test_engine = create_engine(_TEST_DATABASE_URL)
_readonly_engine = create_engine(_TEST_DATABASE_URL_READONLY)
_TestSessionLocal = sessionmaker(bind=_test_engine)
_ReadonlySessionLocal = sessionmaker(bind=_readonly_engine)


@pytest.fixture
def readonly_engine() -> Engine:
    """Bypasses the app entirely — used only to probe what the DB role
    itself would stop if the sqlglot guardrail weren't there."""
    return _readonly_engine


@pytest.fixture
def db_session() -> Generator[Session]:
    """A rootlens_app session wrapped in a transaction that's always
    rolled back, so these tests never leave rows behind."""
    connection = _test_engine.connect()
    transaction = connection.begin()
    session = _TestSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def readonly_db_session() -> Generator[Session]:
    """The rootlens_readonly counterpart to db_session, for exercising
    app.investigations.engine's real readonly_session argument."""
    connection = _readonly_engine.connect()
    transaction = connection.begin()
    session = _ReadonlySessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
