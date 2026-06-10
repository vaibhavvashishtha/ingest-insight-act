import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base


class FactPerformance(Base):
    __tablename__ = "fact_performance"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    date_key: Mapped[date] = mapped_column(Date, ForeignKey("dim_date.date_key"), nullable=False)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("dim_campaign.id", ondelete="SET NULL"), nullable=True)
    channel_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("dim_channel.id", ondelete="SET NULL"), nullable=True)
    audience_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("dim_audience.id", ondelete="SET NULL"), nullable=True)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False)
    impressions: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    clicks: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    spend: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    conversions: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    revenue: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    # ctr/cpc/roas are generated columns in DB — not mapped here to avoid insert conflicts
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FactAttribution(Base):
    __tablename__ = "fact_attribution"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    date_key: Mapped[date] = mapped_column(Date, ForeignKey("dim_date.date_key"), nullable=False)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("dim_campaign.id", ondelete="SET NULL"), nullable=True)
    channel_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("dim_channel.id", ondelete="SET NULL"), nullable=True)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    attributed_conversions: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    attributed_revenue: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
