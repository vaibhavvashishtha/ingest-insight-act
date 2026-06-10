import uuid

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from api.dependencies import TenantId
from api.limits import limiter
from core.config import settings
from core.db import get_session
from core.models import Insight
from core.registry import load_all_content_models
from core.schemas.insights import GenerateInsightRequest, InsightRead
from insights.engine import InsightEngine
from insights.prompt_store import PromptStore

load_all_content_models()

router = APIRouter(prefix="/insights", tags=["insights"])

_prompt_store = PromptStore()


@router.post("/generate", response_model=InsightRead, status_code=201)
@limiter.limit(settings.rate_limit_llm)
async def generate_insight(request: Request, body: GenerateInsightRequest, tenant_id: TenantId):
    from core.content_models.claude_model import ClaudeContentModel

    engine = InsightEngine(
        prompt_store=_prompt_store,
        content_model=ClaudeContentModel(),
    )
    async with get_session(tenant_id) as session:
        insight = await engine.generate(
            session=session,
            tenant_id=tenant_id,
            source_ids=body.source_ids,
            start_date=body.start_date,
            end_date=body.end_date,
            template_slug=body.template_slug,
        )
        return insight


@router.get("/", response_model=list[InsightRead])
async def list_insights(tenant_id: TenantId):
    async with get_session(tenant_id) as session:
        result = await session.execute(
            select(Insight)
            .where(Insight.tenant_id == tenant_id)
            .order_by(Insight.created_at.desc())
            .limit(20)
        )
        return result.scalars().all()


@router.get("/{insight_id}", response_model=InsightRead)
async def get_insight(insight_id: uuid.UUID, tenant_id: TenantId):
    async with get_session(tenant_id) as session:
        insight = await session.get(Insight, insight_id)
        if not insight:
            raise HTTPException(status_code=404, detail="Insight not found")
        return insight
