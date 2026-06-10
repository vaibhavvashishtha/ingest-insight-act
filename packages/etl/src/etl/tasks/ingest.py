import asyncio
import uuid
from datetime import datetime

from sqlalchemy import select, update

from core.connectors.base import CanonicalMapping, ConnectorConfig
from core.db import get_session
from core.models import DataSource, IngestionJob
from core.registry import load_all_connectors
from etl.celery_app import celery_app
from etl.pipeline.extract import extract_batches
from etl.pipeline.load import bulk_upsert_performance, upsert_dim_campaign, upsert_dim_channel
from etl.pipeline.transform import apply_mapping, coerce_metrics

load_all_connectors()


@celery_app.task(bind=True, name="etl.ingest_source", max_retries=3, default_retry_delay=60)
def ingest_source_task(
    self,
    job_id: str,
    tenant_id: str,
    source_id: str,
    start_date: str,
    end_date: str,
) -> dict:
    return asyncio.get_event_loop().run_until_complete(
        _run_ingestion(self, job_id, tenant_id, source_id, start_date, end_date)
    )


async def _run_ingestion(
    task,
    job_id: str,
    tenant_id: str,
    source_id: str,
    start_date: str,
    end_date: str,
) -> dict:
    tid = uuid.UUID(tenant_id)
    sid = uuid.UUID(source_id)
    jid = uuid.UUID(job_id)

    async with get_session(tid) as session:
        # Mark job as running
        await session.execute(
            update(IngestionJob)
            .where(IngestionJob.id == jid)
            .values(status="running", started_at=datetime.utcnow(), celery_task_id=task.request.id)
        )
        await session.flush()

        try:
            source = await session.get(DataSource, sid)
            if not source:
                raise ValueError(f"DataSource {sid} not found")
            if not source.schema_map:
                raise ValueError("schema_map is empty — run explore_schema first")

            mappings = [CanonicalMapping(**m) for m in source.schema_map]
            connector_cls = __import__("core.registry", fromlist=["ConnectorRegistry"]).ConnectorRegistry.get(source.connector_type)
            connector = connector_cls(ConnectorConfig(
                connector_type=source.connector_type,
                credentials=source.credentials or {},
                config=source.config or {},
            ))

            total_rows = 0
            async for batch in extract_batches(connector, start_date, end_date, mappings):
                perf_rows = []
                for raw_row in batch:
                    canonical = apply_mapping(raw_row, mappings)
                    canonical = coerce_metrics(canonical)

                    # Resolve campaign dimension
                    campaign_id = None
                    if "campaign_name" in canonical:
                        campaign_id = await upsert_dim_campaign(
                            session=session,
                            tenant_id=tid,
                            source_id=sid,
                            external_id=canonical.get("campaign_name", "unknown"),
                            name=canonical.get("campaign_name", "unknown"),
                            channel=canonical.get("channel"),
                        )

                    # Resolve channel dimension
                    channel_id = None
                    if "channel" in canonical:
                        channel_id = await upsert_dim_channel(
                            session=session,
                            tenant_id=tid,
                            name=canonical["channel"],
                        )

                    from datetime import date as date_cls
                    date_key = canonical.get("date_key")
                    if date_key and isinstance(date_key, str):
                        try:
                            date_key = date_cls.fromisoformat(date_key.replace(":", "-"))
                        except ValueError:
                            date_key = None

                    if not date_key:
                        continue

                    perf_rows.append({
                        "id": uuid.uuid4(),
                        "tenant_id": tid,
                        "date_key": date_key,
                        "campaign_id": campaign_id,
                        "channel_id": channel_id,
                        "source_id": sid,
                        "impressions": canonical.get("impressions", 0),
                        "clicks": canonical.get("clicks", 0),
                        "spend": canonical.get("spend", 0.0),
                        "conversions": canonical.get("conversions", 0.0),
                        "revenue": canonical.get("revenue", 0.0),
                        "raw_data": canonical.get("_raw"),
                    })

                rows_written = await bulk_upsert_performance(session, perf_rows)
                total_rows += rows_written

            # Update job and source
            await session.execute(
                update(IngestionJob)
                .where(IngestionJob.id == jid)
                .values(status="success", completed_at=datetime.utcnow(), rows_ingested=total_rows)
            )
            await session.execute(
                update(DataSource)
                .where(DataSource.id == sid)
                .values(last_ingested_at=datetime.utcnow())
            )

            return {"status": "success", "rows_ingested": total_rows}

        except Exception as exc:
            await session.execute(
                update(IngestionJob)
                .where(IngestionJob.id == jid)
                .values(status="failed", completed_at=datetime.utcnow(), error_message=str(exc))
            )
            raise
