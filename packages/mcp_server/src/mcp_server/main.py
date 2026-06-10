"""
ingest-insight-act MCP Server

Exposes 8 tools covering the full marketing data lifecycle:
configure_source → explore_schema → trigger_ingestion → query_data
→ generate_insights → publish_report → create_campaign_plan → generate_content

Transport:
  stdio (default): for Claude Desktop — set TENANT_ID env var for auth
  sse: for remote/web — pass Bearer <supabase_jwt> in Authorization header
"""
import os
import uuid
from typing import Any

from fastmcp import FastMCP

from mcp_server.auth import get_tenant_from_env
from mcp_server.tools.configure_source import configure_source as _configure_source
from mcp_server.tools.create_campaign_plan import create_campaign_plan as _create_campaign_plan
from mcp_server.tools.explore_schema import explore_schema as _explore_schema
from mcp_server.tools.generate_content import generate_content as _generate_content
from mcp_server.tools.generate_insights import generate_insights as _generate_insights
from mcp_server.tools.publish_report import publish_report as _publish_report
from mcp_server.tools.query_data import query_data as _query_data
from mcp_server.tools.trigger_ingestion import trigger_ingestion as _trigger_ingestion

mcp = FastMCP(
    name="ingest-insight-act",
    instructions=(
        "Marketing data platform. Use these tools to: configure data sources, "
        "explore and map schemas, ingest data, query performance metrics, "
        "generate AI insights, publish reports, and create campaign plans."
    ),
)


def _get_tenant() -> uuid.UUID:
    return get_tenant_from_env()


@mcp.tool()
async def configure_source(
    connector_type: str,
    display_name: str,
    config: dict[str, Any],
    credentials: dict[str, Any] | None = None,
    source_id: str | None = None,
) -> dict:
    """Create or update a marketing data source. connector_type: 'ga4' | 'meta_ads' | 'google_ads' | 'hubspot'"""
    return await _configure_source(
        tenant_id=_get_tenant(),
        connector_type=connector_type,
        display_name=display_name,
        config=config,
        credentials=credentials,
        source_id=source_id,
    )


@mcp.tool()
async def explore_schema(source_id: str) -> dict:
    """Trigger AI-powered schema exploration. Discovers source fields and maps them to the canonical marketing schema."""
    return await _explore_schema(tenant_id=_get_tenant(), source_id=source_id)


@mcp.tool()
async def trigger_ingestion(source_id: str, start_date: str, end_date: str) -> dict:
    """Queue a data ingestion job. Requires explore_schema to have been run first. Dates: YYYY-MM-DD."""
    return await _trigger_ingestion(
        tenant_id=_get_tenant(),
        source_id=source_id,
        start_date=start_date,
        end_date=end_date,
    )


@mcp.tool()
async def query_data(
    start_date: str,
    end_date: str,
    metrics: list[str] | None = None,
    group_by: str | None = None,
    source_ids: list[str] | None = None,
    limit: int = 50,
) -> dict:
    """Query normalized marketing data. group_by: 'campaign' | 'channel' | 'date'. metrics: impressions, clicks, spend, conversions, revenue."""
    return await _query_data(
        tenant_id=_get_tenant(),
        start_date=start_date,
        end_date=end_date,
        metrics=metrics,
        group_by=group_by,
        source_ids=source_ids,
        limit=limit,
    )


@mcp.tool()
async def generate_insights(
    source_ids: list[str],
    start_date: str,
    end_date: str,
    template_slug: str = "weekly_insights",
) -> dict:
    """Generate AI-powered insights from ingested data. Results are cached by data hash."""
    return await _generate_insights(
        tenant_id=_get_tenant(),
        source_ids=source_ids,
        start_date=start_date,
        end_date=end_date,
        template_slug=template_slug,
    )


@mcp.tool()
async def publish_report(
    title: str,
    insight_ids: list[str],
    format: str = "markdown",
) -> dict:
    """Compile insights into a published report. format: 'markdown' | 'html' | 'json'."""
    return await _publish_report(
        tenant_id=_get_tenant(),
        title=title,
        insight_ids=insight_ids,
        format=format,
    )


@mcp.tool()
async def create_campaign_plan(
    title: str,
    objective: str,
    channels: list[str] | None = None,
    budget: float | None = None,
    duration_weeks: int = 4,
) -> dict:
    """Generate a comprehensive AI-powered campaign plan with phases, tactics, KPIs, and copy brief."""
    return await _create_campaign_plan(
        tenant_id=_get_tenant(),
        title=title,
        objective=objective,
        channels=channels,
        budget=budget,
        duration_weeks=duration_weeks,
    )


@mcp.tool()
async def generate_content(
    template_slug: str,
    context: dict[str, Any],
) -> dict:
    """Generate marketing content using a prompt template. Slugs: ad_copy, email_copy, campaign_plan."""
    return await _generate_content(
        tenant_id=_get_tenant(),
        template_slug=template_slug,
        context=context,
    )


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        host = os.environ.get("MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("MCP_PORT", "8001"))
        mcp.run(transport="sse", host=host, port=port)
    else:
        mcp.run(transport="stdio")
