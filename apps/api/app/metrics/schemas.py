from typing import Literal

from pydantic import BaseModel


class MetricDefinition(BaseModel):
    name: str
    version: str
    display_name: str
    sql_expression: str
    grain: Literal["order", "order_item"]
    excluded_statuses: list[str] = []
    description: str
