import os
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Integration tests talk to a real Postgres instance, never the app's
# runtime Settings — TEST_DATABASE_URL is test-only infrastructure and
# deliberately isn't a Settings field (app.main never needs it).
_TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://rootlens_app:changeme_app@localhost:5432/rootlens_test",
)
_test_engine = create_engine(_TEST_DATABASE_URL)
_TestSessionLocal = sessionmaker(bind=_test_engine)


@pytest.fixture
def db_session() -> Generator[Session]:
    """A DB session wrapped in a transaction that's always rolled back,
    so integration tests never leave rows behind for the next test."""
    connection = _test_engine.connect()
    transaction = connection.begin()
    session = _TestSessionLocal(bind=connection)

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
