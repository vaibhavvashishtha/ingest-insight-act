"""MCP tool: create_campaign_plan — generate an AI-powered campaign plan."""
import json
import uuid

from jinja2 import BaseLoader, Environment

from core.db import get_session
from core.models import CampaignPlan
from core.registry import load_all_content_models
from insights.prompt_store import PromptStore

load_all_content_models()

_prompt_store = PromptStore()
_jinja_env = Environment(loader=BaseLoader(), autoescape=False)


async def create_campaign_plan(
    tenant_id: uuid.UUID,
    title: str,
    objective: str,
    channels: list[str] | None = None,
    budget: float | None = None,
    duration_weeks: int = 4,
    template_slug: str = "campaign_plan",
) -> dict:
    """
    Generate a comprehensive AI-powered campaign plan with phases, tactics, KPIs, and copy brief.

    Args:
        title: Campaign plan title
        objective: Campaign objective (e.g. 'increase brand awareness', 'drive purchases')
        channels: List of channels to use (e.g. ['paid_search', 'paid_social', 'email'])
        budget: Total budget in your currency
        duration_weeks: Campaign duration in weeks
        template_slug: Prompt template to use (default: campaign_plan)

    Returns:
        dict with plan_id and the full structured plan content
    """
    from core.content_models.claude_model import ClaudeContentModel
    from core.content_models.base import ContentRequest

    async with get_session(tenant_id) as session:
        template = await _prompt_store.get(session, tenant_id, template_slug)

        context = {
            "objective": objective,
            "budget": budget or "Not specified",
            "channels": ", ".join(channels) if channels else "All relevant channels",
            "duration_weeks": duration_weeks,
            "historical_data_json": "{}",
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
            title=title,
            objective=objective,
            budget=budget,
            channels=channels or [],
            prompt_template_id=template.id,
            plan_content=plan_content,
            status="draft",
        )
        session.add(plan)
        await session.flush()

        return {
            "plan_id": str(plan.id),
            "title": plan.title,
            "status": plan.status,
            "plan_content": plan_content,
        }
