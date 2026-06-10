"""MCP tool: publish_report — compile insights into a published report."""
import uuid
from datetime import datetime

from sqlalchemy import select

from core.db import get_session
from core.models import Insight, Report


async def publish_report(
    tenant_id: uuid.UUID,
    title: str,
    insight_ids: list[str],
    format: str = "markdown",
) -> dict:
    """
    Compile one or more insights into a published report.

    Args:
        title: Report title
        insight_ids: List of insight UUIDs to include
        format: Output format — 'markdown', 'html', or 'json'

    Returns:
        dict with report_id, title, published_at, and report content
    """
    iids = [uuid.UUID(i) for i in insight_ids]

    async with get_session(tenant_id) as session:
        result = await session.execute(
            select(Insight).where(Insight.id.in_(iids))
        )
        insights = result.scalars().all()

        if len(insights) != len(iids):
            return {"error": "One or more insight IDs not found"}

        sections = []
        for insight in insights:
            sections.append({
                "insight_id": str(insight.id),
                "date_range": {
                    "start": str(insight.date_range_start),
                    "end": str(insight.date_range_end),
                },
                "content": insight.content,
            })

        report = Report(
            tenant_id=tenant_id,
            title=title,
            insight_ids=iids,
            content={"sections": sections, "format": format},
            format=format,
            published_at=datetime.utcnow(),
        )
        session.add(report)
        await session.flush()

        return {
            "report_id": str(report.id),
            "title": report.title,
            "published_at": report.published_at.isoformat(),
            "sections_count": len(sections),
            "content": report.content,
        }
