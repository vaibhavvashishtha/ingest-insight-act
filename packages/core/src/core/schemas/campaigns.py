import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CreateCampaignPlanRequest(BaseModel):
    title: str
    objective: str
    budget: float | None = None
    channels: list[str] = []
    duration_weeks: int = 4
    template_slug: str = "campaign_plan"


class GenerateContentRequest(BaseModel):
    template_slug: str
    context: dict[str, Any]


class CampaignPlanRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    objective: str | None
    budget: float | None
    channels: list[str]
    plan_content: dict[str, Any]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class GeneratedContentRead(BaseModel):
    content: dict[str, Any]
    model_used: str
    usage: dict[str, Any]
