import uuid
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from api.dependencies import TenantId
from core.db import get_session
from core.models import DataSource, IngestionJob
from core.schemas.ingestion import IngestionJobRead, TriggerIngestionRequest

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


class ExploreSchemaRequest(BaseModel):
    source_id: uuid.UUID


@router.post("/explore", status_code=status.HTTP_202_ACCEPTED)
async def explore_schema(body: ExploreSchemaRequest, tenant_id: TenantId):
    """Trigger AI-powered schema exploration for a data source."""
    async with get_session(tenant_id) as session:
        source = await session.get(DataSource, body.source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

    from etl.tasks.schema_explore import explore_schema_task
    task = explore_schema_task.delay(str(tenant_id), str(body.source_id))
    return {"task_id": task.id, "source_id": str(body.source_id), "status": "queued"}


@router.post("/trigger", response_model=IngestionJobRead, status_code=status.HTTP_202_ACCEPTED)
async def trigger_ingestion(body: TriggerIngestionRequest, tenant_id: TenantId):
    async with get_session(tenant_id) as session:
        source = await session.get(DataSource, body.source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        if not source.schema_map:
            raise HTTPException(status_code=400, detail="Run explore_schema before ingestion")

        job = IngestionJob(
            tenant_id=tenant_id,
            source_id=body.source_id,
            status="pending",
            date_range_start=body.start_date,
            date_range_end=body.end_date,
        )
        session.add(job)
        await session.flush()

        from etl.tasks.ingest import ingest_source_task
        task = ingest_source_task.delay(
            job_id=str(job.id),
            tenant_id=str(tenant_id),
            source_id=str(body.source_id),
            start_date=str(body.start_date),
            end_date=str(body.end_date),
        )
        job.celery_task_id = task.id
        await session.flush()
        return job


@router.get("/jobs/{job_id}", response_model=IngestionJobRead)
async def get_job(job_id: uuid.UUID, tenant_id: TenantId):
    async with get_session(tenant_id) as session:
        job = await session.get(IngestionJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job


@router.get("/jobs", response_model=list[IngestionJobRead])
async def list_jobs(tenant_id: TenantId, source_id: uuid.UUID | None = None):
    async with get_session(tenant_id) as session:
        query = select(IngestionJob).where(IngestionJob.tenant_id == tenant_id)
        if source_id:
            query = query.where(IngestionJob.source_id == source_id)
        result = await session.execute(query.order_by(IngestionJob.created_at.desc()).limit(50))
        return result.scalars().all()
