"""Shared query helpers — used by both the API router and the MCP tool."""
import uuid
from typing import Any

from sqlalchemy import func, select

from core.db import get_session
from core.models import DimCampaign, DimChannel, FactPerformance


async def query_performance(
    tenant_id: uuid.UUID,
    start_date: str,
    end_date: str,
    metrics: list[str] | None = None,
    group_by: str | None = None,
    source_ids: list[str] | None = None,
    limit: int = 50,
) -> dict:
    """Query normalized marketing performance data."""
    from datetime import date as date_cls

    start = date_cls.fromisoformat(start_date)
    end = date_cls.fromisoformat(end_date)
    metrics = metrics or ["impressions", "clicks", "spend", "conversions", "revenue"]

    metric_map: dict[str, Any] = {
        "impressions": func.sum(FactPerformance.impressions),
        "clicks": func.sum(FactPerformance.clicks),
        "spend": func.sum(FactPerformance.spend),
        "conversions": func.sum(FactPerformance.conversions),
        "revenue": func.sum(FactPerformance.revenue),
    }
    selected = [metric_map[m].label(m) for m in metrics if m in metric_map]

    async with get_session(tenant_id) as session:
        if group_by == "campaign":
            stmt = (
                select(DimCampaign.name.label("campaign"), *selected)
                .join(DimCampaign, FactPerformance.campaign_id == DimCampaign.id)
                .where(
                    FactPerformance.tenant_id == tenant_id,
                    FactPerformance.date_key >= start,
                    FactPerformance.date_key <= end,
                )
                .group_by(DimCampaign.name)
                .order_by(func.sum(FactPerformance.spend).desc())
                .limit(limit)
            )
        elif group_by == "channel":
            stmt = (
                select(DimChannel.name.label("channel"), *selected)
                .join(DimChannel, FactPerformance.channel_id == DimChannel.id)
                .where(
                    FactPerformance.tenant_id == tenant_id,
                    FactPerformance.date_key >= start,
                    FactPerformance.date_key <= end,
                )
                .group_by(DimChannel.name)
                .order_by(func.sum(FactPerformance.spend).desc())
                .limit(limit)
            )
        elif group_by == "date":
            stmt = (
                select(FactPerformance.date_key.label("date"), *selected)
                .where(
                    FactPerformance.tenant_id == tenant_id,
                    FactPerformance.date_key >= start,
                    FactPerformance.date_key <= end,
                )
                .group_by(FactPerformance.date_key)
                .order_by(FactPerformance.date_key)
                .limit(limit)
            )
        else:
            stmt = (
                select(*selected)
                .where(
                    FactPerformance.tenant_id == tenant_id,
                    FactPerformance.date_key >= start,
                    FactPerformance.date_key <= end,
                )
            )
            if source_ids:
                stmt = stmt.where(FactPerformance.source_id.in_([uuid.UUID(s) for s in source_ids]))

        result = await session.execute(stmt)
        rows = [dict(zip(result.keys(), row)) for row in result.all()]

        for row in rows:
            for k, v in row.items():
                if hasattr(v, "__float__"):
                    row[k] = float(v)
                elif hasattr(v, "isoformat"):
                    row[k] = v.isoformat()

        return {"rows": rows, "count": len(rows), "group_by": group_by}
