"""MCP tool: generate_content — run any prompt template with a content model."""
import json
import uuid
from typing import Any

from jinja2 import BaseLoader, Environment

from core.db import get_session
from core.registry import ContentModelRegistry, load_all_content_models
from insights.prompt_store import PromptStore

load_all_content_models()

_prompt_store = PromptStore()
_jinja_env = Environment(loader=BaseLoader(), autoescape=False)


async def generate_content(
    tenant_id: uuid.UUID,
    template_slug: str,
    context: dict[str, Any],
) -> dict:
    """
    Run a prompt template with the configured content model to generate marketing content.
    Available templates: ad_copy, email_copy, campaign_plan, weekly_insights.
    Tenants can override any platform template with their own version.

    Args:
        template_slug: Slug of the prompt template to use
        context: Variables to inject into the Jinja2 template (varies per slug)

    Returns:
        dict with generated content (structure varies by template) and usage stats
    """
    from core.content_models.base import ContentRequest

    async with get_session(tenant_id) as session:
        template = await _prompt_store.get(session, tenant_id, template_slug)

        rendered = _jinja_env.from_string(template.user_prompt_template).render(**context)
        model_cls = ContentModelRegistry.get(template.model_class)
        model = model_cls()

        response = await model.generate(ContentRequest(
            system_prompt=template.system_prompt,
            user_prompt=rendered,
        ))

        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        try:
            content_data = json.loads(raw)
        except json.JSONDecodeError:
            content_data = {"text": response.content}

        return {
            "template_slug": template_slug,
            "content": content_data,
            "model_used": response.model,
            "usage": response.usage,
        }
