import uuid
from datetime import date
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import DimCampaign, DimChannel, FactPerformance


async def upsert_dim_campaign(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    source_id: uuid.UUID,
    external_id: str,
    name: str,
    channel: str | None = None,
) -> uuid.UUID:
    result = await session.execute(
        select(DimCampaign.id).where(
            DimCampaign.tenant_id == tenant_id,
            DimCampaign.source_id == source_id,
            DimCampaign.external_id == external_id,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        return row

    campaign = DimCampaign(
        tenant_id=tenant_id,
        source_id=source_id,
        external_id=external_id,
        name=name,
        channel=channel,
    )
    session.add(campaign)
    await session.flush()
    return campaign.id


async def upsert_dim_channel(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    name: str,
    category: str | None = None,
) -> uuid.UUID:
    result = await session.execute(
        select(DimChannel.id).where(
            DimChannel.tenant_id == tenant_id,
            DimChannel.name == name,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        return row

    channel = DimChannel(tenant_id=tenant_id, name=name, category=category)
    session.add(channel)
    await session.flush()
    return channel.id


async def bulk_upsert_performance(
    session: AsyncSession,
    rows: list[dict[str, Any]],
) -> int:
    """Bulk upsert fact_performance rows. Returns count of rows processed."""
    if not rows:
        return 0

    stmt = pg_insert(FactPerformance).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["tenant_id", "date_key", "campaign_id", "source_id"],
        set_={
            "impressions": stmt.excluded.impressions,
            "clicks": stmt.excluded.clicks,
            "spend": stmt.excluded.spend,
            "conversions": stmt.excluded.conversions,
            "revenue": stmt.excluded.revenue,
            "raw_data": stmt.excluded.raw_data,
            "ingested_at": text("now()"),
        },
    )
    await session.execute(stmt)
    return len(rows)
