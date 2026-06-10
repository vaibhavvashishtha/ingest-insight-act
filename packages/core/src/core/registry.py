from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connectors.base import BaseConnector
    from core.content_models.base import BaseContentModel


class ConnectorRegistry:
    _registry: dict[str, type["BaseConnector"]] = {}

    @classmethod
    def register(cls, connector_cls: type["BaseConnector"]) -> None:
        cls._registry[connector_cls.connector_type] = connector_cls

    @classmethod
    def get(cls, connector_type: str) -> type["BaseConnector"]:
        if connector_type not in cls._registry:
            raise KeyError(f"No connector registered for type '{connector_type}'. "
                           f"Available: {list(cls._registry)}")
        return cls._registry[connector_type]

    @classmethod
    def list_types(cls) -> list[str]:
        return list(cls._registry)


class ContentModelRegistry:
    _registry: dict[str, type["BaseContentModel"]] = {}

    @classmethod
    def register(cls, model_cls: type["BaseContentModel"]) -> None:
        cls._registry[model_cls.model_class] = model_cls

    @classmethod
    def get(cls, model_class: str) -> type["BaseContentModel"]:
        if model_class not in cls._registry:
            raise KeyError(f"No content model registered for class '{model_class}'. "
                           f"Available: {list(cls._registry)}")
        return cls._registry[model_class]

    @classmethod
    def list_classes(cls) -> list[str]:
        return list(cls._registry)


def load_all_connectors() -> None:
    """Import all connector modules so they self-register."""
    import core.connectors.ga4  # noqa: F401


def load_all_content_models() -> None:
    """Import all content model modules so they self-register."""
    import core.content_models.claude_model  # noqa: F401
