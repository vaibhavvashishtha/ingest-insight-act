from collections.abc import AsyncIterator
from typing import Any

from core.connectors.base import BaseConnector, CanonicalMapping

_BATCH_SIZE = 500


async def extract_batches(
    connector: BaseConnector,
    start_date: str,
    end_date: str,
    mappings: list[CanonicalMapping],
) -> AsyncIterator[list[dict[str, Any]]]:
    """Yield 500-row batches of raw rows from the connector."""
    raw_fields = [m.raw_field for m in mappings]
    batch: list[dict[str, Any]] = []

    async for row in connector.fetch_data(start_date, end_date, raw_fields):
        batch.append(row)
        if len(batch) >= _BATCH_SIZE:
            yield batch
            batch = []

    if batch:
        yield batch
