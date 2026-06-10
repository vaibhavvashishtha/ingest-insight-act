"""Dev-only endpoints for the test harness. Guarded by DEV_TENANT_ID env var."""
import random
import uuid
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException

from api.dependencies import TenantId
from core.config import settings
from core.db import get_session
from core.models import DataSource, DimCampaign, DimChannel, FactPerformance

router = APIRouter(prefix="/dev", tags=["dev"])


@router.post("/seed")
async def seed_mock_data(tenant_id: TenantId):
    """
    Insert a stub data source + 30 days of fake fact_performance rows.
    Lets the harness skip steps 2-4 (which require real GA4 credentials) and exercise steps 5-8.

    Only callable when DEV_TENANT_ID env var is set on the API.
    """
    if not settings.dev_tenant_id:
        raise HTTPException(status_code=403, detail="Dev endpoints disabled (DEV_TENANT_ID not set)")

    async with get_session(tenant_id) as session:
        # Clear prior mock data for idempotency
        from sqlalchemy import delete, select
        # Delete fact rows first, then dim rows, then sources (FK cascade should handle most)
        prior_sources = await session.execute(
            select(DataSource.id).where(
                DataSource.tenant_id == tenant_id,
                DataSource.display_name.like("[MOCK]%"),
            )
        )
        prior_ids = [row[0] for row in prior_sources.all()]
        if prior_ids:
            await session.execute(delete(FactPerformance).where(FactPerformance.source_id.in_(prior_ids)))
            await session.execute(delete(DimCampaign).where(DimCampaign.source_id.in_(prior_ids)))
            await session.execute(delete(DataSource).where(DataSource.id.in_(prior_ids)))
        # Channels aren't FK'd to source; clean by name
        await session.execute(delete(DimChannel).where(DimChannel.tenant_id == tenant_id))
        await session.flush()

        # Create a stub GA4 source with a pre-baked schema_map
        source = DataSource(
            tenant_id=tenant_id,
            connector_type="ga4",
            display_name="[MOCK] GA4 Test Property",
            credentials={},
            config={"property_id": "999999999"},
            schema_map=[
                {"raw_field": "date", "canonical_field": "date_key", "transform": None},
                {"raw_field": "campaignName", "canonical_field": "campaign_name", "transform": None},
                {"raw_field": "sessionMedium", "canonical_field": "channel", "transform": None},
                {"raw_field": "screenPageViews", "canonical_field": "impressions", "transform": None},
                {"raw_field": "sessions", "canonical_field": "clicks", "transform": None},
                {"raw_field": "advertiserAdCost", "canonical_field": "spend", "transform": None},
                {"raw_field": "conversions", "canonical_field": "conversions", "transform": None},
                {"raw_field": "purchaseRevenue", "canonical_field": "revenue", "transform": None},
            ],
        )
        session.add(source)
        await session.flush()

        # Seed dimensions
        channels = ["paid_search", "paid_social", "email", "organic"]
        channel_ids: dict[str, uuid.UUID] = {}
        for ch in channels:
            obj = DimChannel(tenant_id=tenant_id, name=ch, category="acquisition")
            session.add(obj)
            await session.flush()
            channel_ids[ch] = obj.id

        campaigns = [
            ("Summer Sale 2026", "paid_search"),
            ("Brand Awareness Q2", "paid_social"),
            ("Retargeting", "paid_social"),
            ("Newsletter Promo", "email"),
            ("Organic SEO Push", "organic"),
        ]
        campaign_records = []
        for ext_id, (name, channel) in enumerate(campaigns):
            obj = DimCampaign(
                tenant_id=tenant_id,
                source_id=source.id,
                external_id=f"camp_{ext_id}",
                name=name,
                channel=channel,
                status="active",
            )
            session.add(obj)
            await session.flush()
            campaign_records.append((obj.id, channel))

        # Seed 30 days of fact rows: 5 campaigns × 30 days = 150 rows
        end = date.today()
        start = end - timedelta(days=29)
        rng = random.Random(42)  # deterministic

        rows_created = 0
        cur = start
        while cur <= end:
            for campaign_id, channel in campaign_records:
                impressions = rng.randint(500, 50000)
                clicks = int(impressions * rng.uniform(0.005, 0.08))
                spend = round(clicks * rng.uniform(0.3, 3.5), 2)
                conversions = int(clicks * rng.uniform(0.01, 0.12))
                revenue = round(conversions * rng.uniform(15, 250), 2)

                fact = FactPerformance(
                    tenant_id=tenant_id,
                    date_key=cur,
                    campaign_id=campaign_id,
                    channel_id=channel_ids[channel],
                    source_id=source.id,
                    impressions=impressions,
                    clicks=clicks,
                    spend=spend,
                    conversions=conversions,
                    revenue=revenue,
                    raw_data={"_mock": True},
                )
                session.add(fact)
                rows_created += 1
            cur += timedelta(days=1)

        return {
            "source_id": str(source.id),
            "schema_map_fields": len(source.schema_map),
            "campaigns_created": len(campaign_records),
            "channels_created": len(channel_ids),
            "fact_rows_created": rows_created,
            "date_range": {"start": str(start), "end": str(end)},
            "message": "Mock data seeded. Steps 2-4 can be marked complete — jump to step 5.",
        }
