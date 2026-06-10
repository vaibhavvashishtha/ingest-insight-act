from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from pydantic import BaseModel


class SchemaField(BaseModel):
    raw_name: str
    raw_type: str
    description: str | None = None
    sample_values: list[Any] = []
    ui_name: str | None = None


class CanonicalMapping(BaseModel):
    raw_field: str
    canonical_field: str  # e.g. "impressions", "spend", "campaign_name"
    transform: str | None = None  # optional python expression applied during transform


class ConnectorConfig(BaseModel):
    connector_type: str
    credentials: dict[str, Any]
    config: dict[str, Any] = {}


class BaseConnector(ABC):
    connector_type: str  # must be set as a class-level constant

    def __init__(self, config: ConnectorConfig) -> None:
        self.config = config

    @abstractmethod
    async def test_connection(self) -> bool:
        """Verify credentials and connectivity."""
        ...

    @abstractmethod
    async def list_schema_fields(self) -> list[SchemaField]:
        """Return all available fields from the source. Used by explore_schema."""
        ...

    @abstractmethod
    async def fetch_data(
        self,
        start_date: str,
        end_date: str,
        fields: list[str],
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield raw rows for the date range."""
        ...
