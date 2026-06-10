import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class GenerateInsightRequest(BaseModel):
    source_ids: list[uuid.UUID]
    start_date: date
    end_date: date
    template_slug: str = "weekly_insights"


class InsightRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    source_ids: list[uuid.UUID]
    date_range_start: date | None
    date_range_end: date | None
    content: dict[str, Any]
    model_used: str
    created_at: datetime

    model_config = {"from_attributes": True}
