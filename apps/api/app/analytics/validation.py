from datetime import date, timedelta

from app.analytics.schemas import DateRange


def exclusive_end(period: DateRange) -> date:
    # order_purchase_timestamp is a DateTime; period.end is a date. Using
    # a half-open range [start, end + 1 day) includes every timestamp on
    # the end date without needing to know its time-of-day granularity.
    return period.end + timedelta(days=1)


def validate_non_overlapping(current: DateRange, comparison: DateRange) -> None:
    if current.start <= comparison.end and comparison.start <= current.end:
        raise ValueError(
            f"periods overlap: current={current.start}..{current.end}, "
            f"comparison={comparison.start}..{comparison.end}"
        )
