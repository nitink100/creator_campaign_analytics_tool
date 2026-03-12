from __future__ import annotations

from app.core.platform_config import PLATFORM_CONFIG
from app.schemas.platform import (
    FilterConfigGroup,
    IngestionCaps,
    PlatformConfigItem,
    SortConfigGroup,
)


class PlatformService:
    def list_platforms(self) -> list[str]:
        return list(PLATFORM_CONFIG.keys())

    def get_filter_config(self) -> dict[str, PlatformConfigItem]:
        response: dict[str, PlatformConfigItem] = {}

        for platform, config in PLATFORM_CONFIG.items():
            response[platform] = PlatformConfigItem(
                enabled_sources=config["enabled_sources"],
                default_source=config["default_source"],
                supported_filters=FilterConfigGroup(
                    content=config["supported_filters"]["content"],
                    creator=config["supported_filters"]["creator"],
                ),
                supported_sort_fields=SortConfigGroup(
                    content=config["supported_sort_fields"]["content"],
                    creator=config["supported_sort_fields"]["creator"],
                ),
                display_only_extra_fields=config["display_only_extra_fields"],
                ingestion_caps=IngestionCaps(
                    max_channels_per_run=config["ingestion_caps"]["max_channels_per_run"],
                    max_videos_per_channel=config["ingestion_caps"]["max_videos_per_channel"],
                ),
            )

        return response