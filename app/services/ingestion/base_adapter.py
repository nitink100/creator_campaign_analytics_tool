from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.ingestion.normalizer import NormalizedIngestionPayload


class BaseIngestionAdapter(ABC):
    platform: str
    source_type: str

    @abstractmethod
    async def ingest(self, channel_ids: list[str] | None = None) -> NormalizedIngestionPayload:
        """
        Fetch raw data from the source, normalize it into internal DTOs,
        and return a structured ingestion payload.
        """
        raise NotImplementedError