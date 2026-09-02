from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Customer, Order, OrderItem

_FIXTURES_DIR = Path(__file__).resolve().parents[4] / "data" / "fixtures"


def test_run_import_loads_all_fixture_tables(db_session: Session) -> None:
    from app.ingestion.cli import _LOAD_STEPS
    from app.ingestion.manifest import REQUIRED_FILES

    # Run every loader directly against the fixture directory, in the
    # same FK-respecting order the CLI uses, reusing the transactional
    # db_session fixture so nothing is left behind.
    for key, loader in _LOAD_STEPS:
        filename = str(REQUIRED_FILES[key]["filename"])
        loader(db_session, _FIXTURES_DIR / filename)

    assert db_session.execute(select(func.count()).select_from(Customer)).scalar_one() == 4
    assert db_session.execute(select(func.count()).select_from(Order)).scalar_one() == 8
    assert db_session.execute(select(func.count()).select_from(OrderItem)).scalar_one() == 8
