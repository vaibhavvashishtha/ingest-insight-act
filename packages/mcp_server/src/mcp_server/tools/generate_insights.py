"""MCP tool: generate_insights — LLM-powered insight generation."""
import uuid

from core.db import get_session
from core.registry import load_all_content_models
from insights.engine import InsightEngine
from insights.prompt_store import PromptStore

load_all_content_models()

_prompt_store = PromptStore()


async def generate_insights(
    tenant_id: uuid.UUID,
    source_ids: list[str],
    start_date: str,
    end_date: str,
    template_slug: str = "weekly_insights",
) -> dict:
    """
    Generate AI-powered insights from ingested marketing data.
    Results are cached by data hash — identical data won't re-call the LLM.

    Args:
        source_ids: List of data source UUIDs to include
        start_date: ISO date YYYY-MM-DD
        end_date: ISO date YYYY-MM-DD
        template_slug: Prompt template to use. Options: weekly_insights, campaign_plan

    Returns:
        dict with insight_id and the structured insight content
    """
    from datetime import date as date_cls
    from core.content_models.claude_model import ClaudeContentModel

    sids = [uuid.UUID(s) for s in source_ids]
    start = date_cls.fromisoformat(start_date)
    end = date_cls.fromisoformat(end_date)

    engine = InsightEngine(
        prompt_store=_prompt_store,
        content_model=ClaudeContentModel(),
    )

    async with get_session(tenant_id) as session:
        insight = await engine.generate(
            session=session,
            tenant_id=tenant_id,
            source_ids=sids,
            start_date=start,
            end_date=end,
            template_slug=template_slug,
        )
        return {
            "insight_id": str(insight.id),
            "date_range": {"start": start_date, "end": end_date},
            "model_used": insight.model_used,
            "content": insight.content,
        }
