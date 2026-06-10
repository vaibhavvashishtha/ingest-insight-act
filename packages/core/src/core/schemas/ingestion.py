import uuid
from datetime import date, datetime

from pydantic import BaseModel


class TriggerIngestionRequest(BaseModel):
    source_id: uuid.UUID
    start_date: date
    end_date: date


class IngestionJobRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    source_id: uuid.UUID
    celery_task_id: str | None
    status: str
    date_range_start: date | None
    date_range_end: date | None
    rows_ingested: int | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
