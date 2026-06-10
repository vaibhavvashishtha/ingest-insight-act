import hashlib
import json
import uuid
from datetime import date

from jinja2 import BaseLoader, Environment
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.content_models.base import BaseContentModel, ContentRequest
from core.models import FactPerformance, Insight
from insights.prompt_store import PromptStore

_jinja_env = Environment(loader=BaseLoader(), autoescape=False)


class InsightEngine:
    def __init__(
        self,
        prompt_store: PromptStore,
        content_model: BaseContentModel,
    ) -> None:
        self._prompt_store = prompt_store
        self._content_model = content_model

    async def generate(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        source_ids: list[uuid.UUID],
        start_date: date,
        end_date: date,
        template_slug: str = "weekly_insights",
    ) -> Insight:
        # Build aggregated metrics for the period
        metrics = await self._query_metrics(session, tenant_id, source_ids, start_date, end_date)
        top_campaigns = await self._query_top_campaigns(session, tenant_id, source_ids, start_date, end_date)

        # Hash the data to allow cache-skip
        data_payload = json.dumps({"metrics": metrics, "top_campaigns": top_campaigns}, sort_keys=True, default=str)
        data_hash = hashlib.sha256(data_payload.encode()).hexdigest()

        existing = await session.execute(
            select(Insight).where(
                Insight.tenant_id == tenant_id,
                Insight.input_data_hash == data_hash,
            ).limit(1)
        )
        cached = existing.scalar_one_or_none()
        if cached:
            return cached

        template = await self._prompt_store.get(session, tenant_id, template_slug)

        context = {
            "date_range_start": str(start_date),
            "date_range_end": str(end_date),
            "metrics_json": json.dumps(metrics, indent=2),
            "top_campaigns_json": json.dumps(top_campaigns, indent=2),
        }
        rendered_user_prompt = _jinja_env.from_string(template.user_prompt_template).render(**context)

        llm_response = await self._content_model.generate(
            ContentRequest(
                system_prompt=template.system_prompt,
                user_prompt=rendered_user_prompt,
            )
        )

        # Parse JSON from response
        raw_text = llm_response.content.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        content_data = json.loads(raw_text)

        insight = Insight(
            tenant_id=tenant_id,
            source_ids=source_ids,
            date_range_start=start_date,
            date_range_end=end_date,
            prompt_template_id=template.id,
            input_data_hash=data_hash,
            content=content_data,
            raw_llm_response=llm_response.content,
            model_used=llm_response.model,
        )
        session.add(insight)
        await session.flush()
        return insight

    async def _query_metrics(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        source_ids: list[uuid.UUID],
        start_date: date,
        end_date: date,
    ) -> dict:
        result = await session.execute(
            select(
                func.sum(FactPerformance.impressions).label("total_impressions"),
                func.sum(FactPerformance.clicks).label("total_clicks"),
                func.sum(FactPerformance.spend).label("total_spend"),
                func.sum(FactPerformance.conversions).label("total_conversions"),
                func.sum(FactPerformance.revenue).label("total_revenue"),
            ).where(
                FactPerformance.tenant_id == tenant_id,
                FactPerformance.source_id.in_(source_ids),
                FactPerformance.date_key >= start_date,
                FactPerformance.date_key <= end_date,
            )
        )
        row = result.one()
        return {
            "total_impressions": int(row.total_impressions or 0),
            "total_clicks": int(row.total_clicks or 0),
            "total_spend": float(row.total_spend or 0),
            "total_conversions": float(row.total_conversions or 0),
            "total_revenue": float(row.total_revenue or 0),
            "ctr": round(int(row.total_clicks or 0) / max(int(row.total_impressions or 0), 1), 6),
            "roas": round(float(row.total_revenue or 0) / max(float(row.total_spend or 0), 0.01), 2),
        }

    async def _query_top_campaigns(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        source_ids: list[uuid.UUID],
        start_date: date,
        end_date: date,
        limit: int = 10,
    ) -> list[dict]:
        from core.models import DimCampaign

        result = await session.execute(
            select(
                DimCampaign.name,
                func.sum(FactPerformance.spend).label("spend"),
                func.sum(FactPerformance.conversions).label("conversions"),
                func.sum(FactPerformance.revenue).label("revenue"),
            )
            .join(DimCampaign, FactPerformance.campaign_id == DimCampaign.id)
            .where(
                FactPerformance.tenant_id == tenant_id,
                FactPerformance.source_id.in_(source_ids),
                FactPerformance.date_key >= start_date,
                FactPerformance.date_key <= end_date,
            )
            .group_by(DimCampaign.name)
            .order_by(func.sum(FactPerformance.spend).desc())
            .limit(limit)
        )
        return [
            {
                "name": r.name,
                "spend": float(r.spend or 0),
                "conversions": float(r.conversions or 0),
                "revenue": float(r.revenue or 0),
                "roas": round(float(r.revenue or 0) / max(float(r.spend or 0), 0.01), 2),
            }
            for r in result.all()
        ]
