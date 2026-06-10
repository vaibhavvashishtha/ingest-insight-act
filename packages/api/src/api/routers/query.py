"""Simple query endpoint for the dev harness (and production use)."""
from typing import Annotated

from fastapi import APIRouter, Query

from api.dependencies import TenantId
from core.queries import query_performance

router = APIRouter(prefix="/query", tags=["query"])


@router.get("/")
async def query_performance_route(
    tenant_id: TenantId,
    start_date: str = Query(...),
    end_date: str = Query(...),
    metrics: Annotated[list[str] | None, Query()] = None,
    group_by: str | None = None,
    source_ids: Annotated[list[str] | None, Query()] = None,
    limit: int = 50,
):
    return await query_performance(
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        metrics=metrics,
        group_by=group_by,
        source_ids=source_ids,
        limit=limit,
    )
