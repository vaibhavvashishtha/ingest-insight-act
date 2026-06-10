import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class PublishReportRequest(BaseModel):
    title: str
    insight_ids: list[uuid.UUID]
    format: str = "markdown"


class ReportRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    insight_ids: list[uuid.UUID]
    content: dict[str, Any]
    format: str
    published_at: datetime | None
    published_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
