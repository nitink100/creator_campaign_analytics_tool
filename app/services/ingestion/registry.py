from __future__ import annotations

from app.core.enums import PlatformEnum, SourceTypeEnum
from app.core.exceptions import ConfigurationError
from app.services.ingestion.base_adapter import BaseIngestionAdapter
from app.services.ingestion.youtube_api_adapter import YouTubeAPIAdapter


class IngestionAdapterRegistry:
    def __init__(self) -> None:
        self._registry: dict[tuple[str, str], type[BaseIngestionAdapter]] = {
            (PlatformEnum.YOUTUBE.value, SourceTypeEnum.API.value): YouTubeAPIAdapter,
        }

    def get_adapter_class(self, *, platform: str, source_type: str) -> type[BaseIngestionAdapter]:
        adapter_class = self._registry.get((platform, source_type))
        if not adapter_class:
            raise ConfigurationError(
                f"No ingestion adapter registered for platform='{platform}', source_type='{source_type}'"
            )
        return adapter_class