from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class ContentRequest(BaseModel):
    system_prompt: str
    user_prompt: str
    context_data: dict[str, Any] | None = None
    max_tokens: int = 4096
    temperature: float = 0.3


class ContentResponse(BaseModel):
    content: str
    usage: dict[str, Any]
    model: str


class BaseContentModel(ABC):
    model_class: str  # must be set as a class-level constant

    @abstractmethod
    async def generate(self, request: ContentRequest) -> ContentResponse:
        ...
