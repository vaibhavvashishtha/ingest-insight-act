import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DataSourceCreate(BaseModel):
    connector_type: str
    display_name: str
    credentials: dict[str, Any] = {}
    config: dict[str, Any] = {}


class DataSourceUpdate(BaseModel):
    display_name: str | None = None
    credentials: dict[str, Any] | None = None
    config: dict[str, Any] | None = None


class DataSourceRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    connector_type: str
    display_name: str
    config: dict[str, Any]
    schema_map: list[dict] | None
    last_ingested_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
