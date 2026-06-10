"""MCP tool: explore_schema — AI-powered field mapping for a data source."""
import uuid

from core.db import get_session
from core.models import DataSource


async def explore_schema(tenant_id: uuid.UUID, source_id: str) -> dict:
    """
    Trigger AI-powered schema exploration for a configured data source.
    Discovers all available fields and uses Claude to map them to the canonical marketing schema.
    The result is persisted to data_sources.schema_map.

    Args:
        source_id: UUID of the data source to explore

    Returns:
        dict with task_id, status, and a preview of discovered mappings once complete
    """
    async with get_session(tenant_id) as session:
        source = await session.get(DataSource, uuid.UUID(source_id))
        if not source:
            return {"error": f"Source {source_id} not found"}

    from etl.tasks.schema_explore import explore_schema_task
    task = explore_schema_task.delay(str(tenant_id), source_id)

    return {
        "task_id": task.id,
        "source_id": source_id,
        "status": "queued",
        "message": "Schema exploration started. Poll /ingestion/jobs or call get_task_result(task_id) to check progress.",
    }
