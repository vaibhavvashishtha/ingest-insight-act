import asyncio
import json
import uuid

import anthropic
from sqlalchemy import update

from core.config import settings
from core.connectors.base import CanonicalMapping, ConnectorConfig
from core.db import get_session
from core.models import DataSource
from core.registry import load_all_connectors
from etl.celery_app import celery_app

load_all_connectors()

_SYSTEM_PROMPT = """You are a data engineering expert specializing in marketing analytics schemas.
Given a list of raw field names from a marketing data source, map them to the canonical marketing schema fields.

Canonical fields available:
- date_key: date of the data point (YYYY-MM-DD)
- campaign_name: name of the campaign
- channel: marketing channel (paid_search, paid_social, email, organic, display)
- audience_name: audience or segment name
- impressions: number of ad impressions
- clicks: number of clicks or sessions
- spend: advertising cost in source currency
- conversions: number of conversions (purchases, leads, sign-ups)
- revenue: revenue attributed to the campaign
- source_name: traffic source
- device_category: device type (desktop, mobile, tablet)
- country: country code or name
- city: city name

Return ONLY valid JSON — an array of mapping objects. No explanation.
"""


@celery_app.task(name="etl.explore_schema")
def explore_schema_task(tenant_id: str, source_id: str) -> dict:
    return asyncio.get_event_loop().run_until_complete(
        _run_explore(tenant_id, source_id)
    )


async def _run_explore(tenant_id: str, source_id: str) -> dict:
    tid = uuid.UUID(tenant_id)
    sid = uuid.UUID(source_id)

    async with get_session(tid) as session:
        source = await session.get(DataSource, sid)
        if not source:
            raise ValueError(f"DataSource {sid} not found")

        from core.registry import ConnectorRegistry
        connector_cls = ConnectorRegistry.get(source.connector_type)
        connector = connector_cls(ConnectorConfig(
            connector_type=source.connector_type,
            credentials=source.credentials or {},
            config=source.config or {},
        ))

        fields = await connector.list_schema_fields()
        field_descriptions = [
            f"- {f.raw_name} (type: {f.raw_type})"
            + (f" — {f.description}" if f.description else "")
            + (f" [{f.ui_name}]" if f.ui_name else "")
            for f in fields
        ]

        # Include known hints as examples
        hints_text = ""
        if hasattr(connector, "get_canonical_hints"):
            hints = connector.get_canonical_hints()
            hint_examples = [f"  {k} → {v}" for k, v in list(hints.items())[:10]]
            hints_text = "\n\nKnown hint mappings (use as reference):\n" + "\n".join(hint_examples)

        user_prompt = (
            f"Source type: {source.connector_type}\n\n"
            f"Available fields:\n" + "\n".join(field_descriptions)
            + hints_text
            + "\n\nReturn the mappings as a JSON array:\n"
            '[\n  {"raw_field": "fieldName", "canonical_field": "canonical_name", "transform": null},\n  ...\n]'
        )

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_response = response.content[0].text
        # Strip markdown code fences if present
        clean = raw_response.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        mappings_data = json.loads(clean)
        # Validate via pydantic
        mappings = [CanonicalMapping(**m) for m in mappings_data]

        await session.execute(
            update(DataSource)
            .where(DataSource.id == sid)
            .values(schema_map=[m.model_dump() for m in mappings])
        )

        return {
            "source_id": source_id,
            "fields_discovered": len(fields),
            "mappings_created": len(mappings),
            "mappings": [m.model_dump() for m in mappings],
        }
