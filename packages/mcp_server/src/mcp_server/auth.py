import uuid

from jose import JWTError, jwt

from core.config import settings


def resolve_tenant_from_token(token: str) -> uuid.UUID:
    """Decode a Supabase JWT and extract the tenant_id from app_metadata."""
    try:
        payload = jwt.decode(token, settings.supabase_service_role_key, algorithms=["HS256"])
    except JWTError as exc:
        raise PermissionError(f"Invalid JWT: {exc}") from exc

    app_metadata = payload.get("app_metadata", {})
    tenant_id_str = app_metadata.get("tenant_id")
    if not tenant_id_str:
        raise PermissionError("No tenant_id in token app_metadata")

    return uuid.UUID(tenant_id_str)


def get_tenant_from_env() -> uuid.UUID:
    """For local dev / stdio transport: read TENANT_ID from environment."""
    import os
    tid = os.environ.get("TENANT_ID")
    if not tid:
        raise PermissionError("TENANT_ID environment variable not set")
    return uuid.UUID(tid)
