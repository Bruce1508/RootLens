from datetime import date

from pydantic import BaseModel, model_validator


class DateRange(BaseModel):
    start: date
    end: date

    @model_validator(mode="after")
    def check_start_before_end(self) -> "DateRange":
        if self.start >= self.end:
            raise ValueError("start must be strictly before end")
        return self


class ToolResult(BaseModel):
    evidence_id: str
    tool_name: str
    params: dict
    sql: str
    columns: list[str]
    rows: list[dict]
    row_count: int
    execution_ms: float
    warnings: list[str] = []
