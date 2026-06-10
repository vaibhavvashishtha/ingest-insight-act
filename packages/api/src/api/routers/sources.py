import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from api.dependencies import TenantId
from core.connectors.base import ConnectorConfig
from core.db import get_session
from core.models import DataSource
from core.registry import ConnectorRegistry, load_all_connectors
from core.schemas.source import DataSourceCreate, DataSourceRead, DataSourceUpdate

load_all_connectors()

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/", response_model=list[DataSourceRead])
async def list_sources(tenant_id: TenantId):
    async with get_session(tenant_id) as session:
        result = await session.execute(
            select(DataSource).where(DataSource.tenant_id == tenant_id).order_by(DataSource.created_at.desc())
        )
        return result.scalars().all()


@router.post("/", response_model=DataSourceRead, status_code=status.HTTP_201_CREATED)
async def create_source(body: DataSourceCreate, tenant_id: TenantId):
    if body.connector_type not in ConnectorRegistry.list_types():
        raise HTTPException(status_code=400, detail=f"Unknown connector_type '{body.connector_type}'")

    source = DataSource(
        tenant_id=tenant_id,
        connector_type=body.connector_type,
        display_name=body.display_name,
        credentials=body.credentials,
        config=body.config,
    )
    async with get_session(tenant_id) as session:
        session.add(source)
        await session.flush()
        return source


@router.get("/{source_id}", response_model=DataSourceRead)
async def get_source(source_id: uuid.UUID, tenant_id: TenantId):
    async with get_session(tenant_id) as session:
        source = await session.get(DataSource, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        return source


@router.patch("/{source_id}", response_model=DataSourceRead)
async def update_source(source_id: uuid.UUID, body: DataSourceUpdate, tenant_id: TenantId):
    async with get_session(tenant_id) as session:
        source = await session.get(DataSource, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        for field, value in body.model_dump(exclude_none=True).items():
            setattr(source, field, value)
        await session.flush()
        return source


@router.post("/{source_id}/test")
async def test_source_connection(source_id: uuid.UUID, tenant_id: TenantId):
    async with get_session(tenant_id) as session:
        source = await session.get(DataSource, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        connector_cls = ConnectorRegistry.get(source.connector_type)
        connector = connector_cls(ConnectorConfig(
            connector_type=source.connector_type,
            credentials=source.credentials or {},
            config=source.config or {},
        ))
        ok = await connector.test_connection()
        return {"connected": ok}
