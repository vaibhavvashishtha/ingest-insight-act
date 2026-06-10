import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt

from core.config import settings


async def get_tenant_id(
    authorization: Annotated[str | None, Header()] = None,
    x_dev_tenant_id: Annotated[str | None, Header()] = None,
) -> uuid.UUID:
    """Extract tenant_id from Supabase JWT, or from X-Dev-Tenant-ID header in dev mode."""

    # Dev bypass: only active when DEV_TENANT_ID env var is set
    if settings.dev_tenant_id and x_dev_tenant_id:
        if x_dev_tenant_id != settings.dev_tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dev tenant ID mismatch")
        try:
            return uuid.UUID(x_dev_tenant_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid dev tenant UUID") from exc

    # Normal JWT path
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = authorization.removeprefix("Bearer ")
    try:
        payload = jwt.decode(token, settings.supabase_service_role_key, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    app_metadata = payload.get("app_metadata", {})
    tenant_id_str = app_metadata.get("tenant_id")
    if not tenant_id_str:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenant_id in token")

    try:
        return uuid.UUID(tenant_id_str)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid tenant_id") from exc


TenantId = Annotated[uuid.UUID, Depends(get_tenant_id)]
