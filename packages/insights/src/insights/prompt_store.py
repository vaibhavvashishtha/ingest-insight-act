import time
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import PromptTemplate

_TTL_SECONDS = 60


@dataclass
class _CacheEntry:
    template: PromptTemplate
    expires_at: float


class PromptStore:
    def __init__(self) -> None:
        self._cache: dict[str, _CacheEntry] = {}

    async def get(self, session: AsyncSession, tenant_id: uuid.UUID, slug: str) -> PromptTemplate:
        """Return the active template for the given slug, preferring tenant-specific over platform default."""
        cache_key = f"{tenant_id}:{slug}"
        entry = self._cache.get(cache_key)
        if entry and entry.expires_at > time.monotonic():
            return entry.template

        # Prefer tenant-specific, then fall back to platform default (tenant_id IS NULL)
        result = await session.execute(
            select(PromptTemplate)
            .where(
                PromptTemplate.slug == slug,
                PromptTemplate.is_active.is_(True),
                (PromptTemplate.tenant_id == tenant_id) | (PromptTemplate.tenant_id.is_(None)),
            )
            .order_by(PromptTemplate.tenant_id.nulls_last(), PromptTemplate.version.desc())
            .limit(1)
        )
        template = result.scalar_one_or_none()
        if not template:
            raise ValueError(f"No active prompt template found for slug '{slug}'")

        self._cache[cache_key] = _CacheEntry(
            template=template,
            expires_at=time.monotonic() + _TTL_SECONDS,
        )
        return template
