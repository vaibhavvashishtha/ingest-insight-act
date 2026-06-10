"""MCP tool: trigger_ingestion — queue an ETL job for a data source."""
import uuid

from core.db import get_session
from core.models import DataSource, IngestionJob


async def trigger_ingestion(
    tenant_id: uuid.UUID,
    source_id: str,
    start_date: str,
    end_date: str,
) -> dict:
    """
    Queue a data ingestion job for a configured source.
    Requires explore_schema to have been run first.

    Args:
        source_id: UUID of the data source
        start_date: ISO date string YYYY-MM-DD
        end_date: ISO date string YYYY-MM-DD

    Returns:
        dict with job_id and status
    """
    from datetime import date

    sid = uuid.UUID(source_id)
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    async with get_session(tenant_id) as session:
        source = await session.get(DataSource, sid)
        if not source:
            return {"error": f"Source {source_id} not found"}
        if not source.schema_map:
            return {"error": "Run explore_schema before triggering ingestion"}

        job = IngestionJob(
            tenant_id=tenant_id,
            source_id=sid,
            status="pending",
            date_range_start=start,
            date_range_end=end,
        )
        session.add(job)
        await session.flush()

        from etl.tasks.ingest import ingest_source_task
        task = ingest_source_task.delay(
            job_id=str(job.id),
            tenant_id=str(tenant_id),
            source_id=source_id,
            start_date=start_date,
            end_date=end_date,
        )
        job.celery_task_id = task.id
        await session.flush()

        return {
            "job_id": str(job.id),
            "celery_task_id": task.id,
            "status": "queued",
            "date_range": {"start": start_date, "end": end_date},
        }
