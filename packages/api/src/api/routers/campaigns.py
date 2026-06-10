import json
import uuid

from fastapi import APIRouter, HTTPException, Request
from jinja2 import BaseLoader, Environment
from sqlalchemy import select

from api.dependencies import TenantId
from api.limits import limiter
from core.config import settings
from core.db import get_session
from core.models import CampaignPlan
from core.registry import load_all_content_models
from core.schemas.campaigns import (
    CampaignPlanRead,
    CreateCampaignPlanRequest,
    GenerateContentRequest,
    GeneratedContentRead,
)
from insights.prompt_store import PromptStore

load_all_content_models()

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

_prompt_store = PromptStore()
_jinja_env = Environment(loader=BaseLoader(), autoescape=False)


@router.post("/plans", response_model=CampaignPlanRead, status_code=201)
@limiter.limit(settings.rate_limit_llm)
async def create_campaign_plan(request: Request, body: CreateCampaignPlanRequest, tenant_id: TenantId):
    from core.content_models.claude_model import ClaudeContentModel
    from core.content_models.base import ContentRequest

    async with get_session(tenant_id) as session:
        template = await _prompt_store.get(session, tenant_id, body.template_slug)

        context = {
            "objective": body.objective,
            "budget": body.budget or "Not specified",
            "channels": ", ".join(body.channels) if body.channels else "All relevant channels",
            "duration_weeks": body.duration_weeks,
            "historical_data_json": "{}",  # can be enriched with actual data
        }
        rendered = _jinja_env.from_string(template.user_prompt_template).render(**context)

        model = ClaudeContentModel()
        response = await model.generate(ContentRequest(
            system_prompt=template.system_prompt,
            user_prompt=rendered,
        ))

        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        plan_content = json.loads(raw)

        plan = CampaignPlan(
            tenant_id=tenant_id,
            title=body.title,
            objective=body.objective,
            budget=body.budget,
            channels=body.channels,
            prompt_template_id=template.id,
            plan_content=plan_content,
            status="draft",
        )
        session.add(plan)
        await session.flush()
        return plan


@router.post("/content/generate", response_model=GeneratedContentRead)
@limiter.limit(settings.rate_limit_llm)
async def generate_content(request: Request, body: GenerateContentRequest, tenant_id: TenantId):
    from core.content_models.claude_model import ClaudeContentModel
    from core.content_models.base import ContentRequest

    async with get_session(tenant_id) as session:
        template = await _prompt_store.get(session, tenant_id, body.template_slug)

        rendered = _jinja_env.from_string(template.user_prompt_template).render(**body.context)

        # Resolve content model from template
        from core.registry import ContentModelRegistry
        model_cls = ContentModelRegistry.get(template.model_class)
        model = model_cls()

        response = await model.generate(ContentRequest(
            system_prompt=template.system_prompt,
            user_prompt=rendered,
        ))

        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        content_data = json.loads(raw)

        return GeneratedContentRead(
            content=content_data,
            model_used=response.model,
            usage=response.usage,
        )


@router.get("/plans", response_model=list[CampaignPlanRead])
async def list_plans(tenant_id: TenantId):
    async with get_session(tenant_id) as session:
        result = await session.execute(
            select(CampaignPlan).where(CampaignPlan.tenant_id == tenant_id).order_by(CampaignPlan.created_at.desc()).limit(20)
        )
        return result.scalars().all()


@router.get("/plans/{plan_id}", response_model=CampaignPlanRead)
async def get_plan(plan_id: uuid.UUID, tenant_id: TenantId):
    async with get_session(tenant_id) as session:
        plan = await session.get(CampaignPlan, plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Campaign plan not found")
        return plan
