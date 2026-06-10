import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from api.dependencies import TenantId
from core.db import get_session
from core.models import Insight, Report
from core.schemas.reports import PublishReportRequest, ReportRead

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/", response_model=ReportRead, status_code=201)
async def publish_report(body: PublishReportRequest, tenant_id: TenantId):
    async with get_session(tenant_id) as session:
        # Fetch all referenced insights
        result = await session.execute(
            select(Insight).where(Insight.id.in_(body.insight_ids))
        )
        insights = result.scalars().all()
        if len(insights) != len(body.insight_ids):
            raise HTTPException(status_code=404, detail="One or more insights not found")

        # Build report content from insights
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
            title=body.title,
            insight_ids=body.insight_ids,
            content={"sections": sections},
            format=body.format,
            published_at=datetime.utcnow(),
        )
        session.add(report)
        await session.flush()
        return report


@router.get("/", response_model=list[ReportRead])
async def list_reports(tenant_id: TenantId):
    async with get_session(tenant_id) as session:
        result = await session.execute(
            select(Report).where(Report.tenant_id == tenant_id).order_by(Report.created_at.desc()).limit(20)
        )
        return result.scalars().all()


@router.get("/{report_id}", response_model=ReportRead)
async def get_report(report_id: uuid.UUID, tenant_id: TenantId):
    async with get_session(tenant_id) as session:
        report = await session.get(Report, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return report
