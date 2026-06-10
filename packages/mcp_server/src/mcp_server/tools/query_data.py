"""MCP tool: query_data — query normalized marketing performance data."""
import uuid

from core.queries import query_performance


async def query_data(
    tenant_id: uuid.UUID,
    start_date: str,
    end_date: str,
    metrics: list[str] | None = None,
    group_by: str | None = None,
    source_ids: list[str] | None = None,
    limit: int = 50,
) -> dict:
    """Query normalized marketing performance data (MCP wrapper)."""
    return await query_performance(
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        metrics=metrics,
        group_by=group_by,
        source_ids=source_ids,
        limit=limit,
    )
