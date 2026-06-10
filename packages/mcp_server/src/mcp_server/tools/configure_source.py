"""MCP tool: configure_source — create or update a data source."""
import uuid
from typing import Any

from core.connectors.base import ConnectorConfig
from core.db import get_session
from core.models import DataSource
from core.registry import ConnectorRegistry, load_all_connectors

load_all_connectors()


async def configure_source(
    tenant_id: uuid.UUID,
    connector_type: str,
    display_name: str,
    config: dict[str, Any],
    credentials: dict[str, Any] | None = None,
    source_id: str | None = None,
) -> dict:
    """
    Create or update a data source configuration.

    Args:
        connector_type: One of 'ga4', 'meta_ads', 'google_ads', 'hubspot'
        display_name: Human-readable name for this source
        config: Connector-specific config (e.g. {'property_id': '123456789'} for GA4)
        credentials: Auth credentials dict (service account JSON, API keys, etc.)
        source_id: If provided, update existing source instead of creating

    Returns:
        dict with source_id, connector_type, display_name, connected (bool)
    """
    available = ConnectorRegistry.list_types()
    if connector_type not in available:
        return {"error": f"Unknown connector_type '{connector_type}'. Available: {available}"}

    async with get_session(tenant_id) as session:
        if source_id:
            source = await session.get(DataSource, uuid.UUID(source_id))
            if not source:
                return {"error": f"Source {source_id} not found"}
            source.display_name = display_name
            source.config = config
            if credentials is not None:
                source.credentials = credentials
        else:
            source = DataSource(
                tenant_id=tenant_id,
                connector_type=connector_type,
                display_name=display_name,
                credentials=credentials or {},
                config=config,
            )
            session.add(source)
        await session.flush()

        # Test connection
        connector_cls = ConnectorRegistry.get(connector_type)
        connector = connector_cls(ConnectorConfig(
            connector_type=connector_type,
            credentials=credentials or {},
            config=config,
        ))
        connected = await connector.test_connection()

        return {
            "source_id": str(source.id),
            "connector_type": source.connector_type,
            "display_name": source.display_name,
            "connected": connected,
        }
