from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_readonly_session
from app.models import Order

router = APIRouter()


@router.get("/api/metadata/date-range")
def get_date_range(
    session: Annotated[Session, Depends(get_readonly_session)],
) -> dict[str, str | None]:
    stmt = select(
        func.min(Order.order_purchase_timestamp), func.max(Order.order_purchase_timestamp)
    )
    min_dt, max_dt = session.execute(stmt).one()

    return {
        "min_date": min_dt.date().isoformat() if min_dt else None,
        "max_date": max_dt.date().isoformat() if max_dt else None,
    }
