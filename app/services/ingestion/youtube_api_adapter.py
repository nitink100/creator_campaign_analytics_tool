from __future__ import annotations

import json
import re
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.core.enums import ContentTypeEnum, PlatformEnum, SourceTypeEnum
from app.core.exceptions import ConfigurationError, ExternalServiceError
from app.services.ingestion.base_adapter import BaseIngestionAdapter
from app.services.ingestion.normalizer import (
    NormalizedContentRecord,
    NormalizedCreatorRecord,
    NormalizedIngestionPayload,
    NormalizedMetricRecord,
)
from app.services.ingestion.quota_tracker import QuotaTracker
from app.utils.datetime_utils import parse_iso_datetime, utc_now
from app.utils.math_utils import safe_int

# Quota costs per YouTube API endpoint
QUOTA_COSTS = {
    "channels": 1,
    "playlistItems": 1,
    "videos": 1,
    "videoCategories": 1,
    "search": 100,
}


class YouTubeAPIAdapter(BaseIngestionAdapter):
    platform = PlatformEnum.YOUTUBE.value
    source_type = SourceTypeEnum.API.value
    base_url = "https://www.googleapis.com/youtube/v3"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.api_key = self.settings.YOUTUBE_API_KEY

        if not self.api_key:
            raise ConfigurationError("YOUTUBE_API_KEY is not configured")



    async def _get(
        self,
        client: httpx.AsyncClient,
        *,
        endpoint: str,
        params: dict,
    ) -> dict:
        final_params = {**params, "key": self.api_key}
        cost = QUOTA_COSTS.get(endpoint, 1)
        await QuotaTracker().record(cost)

        try:
            response = await client.get(f"{self.base_url}/{endpoint}", params=final_params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            try:
                data = exc.response.json()
                msg = data.get("error", {}).get("message", exc.response.text)
            except Exception:
                msg = exc.response.text
            raise ExternalServiceError(
                f"YouTube API error [{exc.response.status_code}]: {msg}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"YouTube API network error on {endpoint}: {exc}") from exc

    async def _fetch_channels(
        self,
        client: httpx.AsyncClient,
        *,
        channel_ids: list[str],
    ) -> list[dict]:
        if not channel_ids:
            return []

        data = await self._get(
            client,
            endpoint="channels",
            params={
                "part": "snippet,contentDetails,statistics",
                "id": ",".join(channel_ids),
                "maxResults": len(channel_ids),
            },
        )
        return data.get("items", [])

    async def _fetch_playlist_video_ids(
        self,
        client: httpx.AsyncClient,
        *,
        uploads_playlist_id: str,
        max_results: int,
    ) -> list[str]:
        video_ids: list[str] = []
        next_page = None

        while len(video_ids) < max_results:
            fetch_count = min(50, max_results - len(video_ids))
            params = {
                "part": "contentDetails",
                "playlistId": uploads_playlist_id,
                "maxResults": fetch_count,
            }
            if next_page:
                params["pageToken"] = str(next_page) # Ensure string

            data = await self._get(
                client,
                endpoint="playlistItems",
                params=params,
            )

            items = data.get("items", [])
            if not items:
                break

            for item in items:
                content_details = item.get("contentDetails", {})
                video_id = content_details.get("videoId")
                if video_id:
                    video_ids.append(video_id)

            next_page = data.get("nextPageToken")
            if not next_page:
                break

        return video_ids[:int(max_results)]

    async def _fetch_videos(
        self,
        client: httpx.AsyncClient,
        *,
        video_ids: list[str],
    ) -> list[dict]:
        if not video_ids:
            return []

        all_items = []
        for i in range(0, len(video_ids), 50):
            batched_ids = video_ids[i:i + 50]
            data = await self._get(
                client,
                endpoint="videos",
                params={
                    "part": "snippet,statistics",
                    "id": ",".join(batched_ids),
                    "maxResults": len(batched_ids),
                },
            )
            all_items.extend(data.get("items", []))
            
        return all_items

    # ── Discovery methods ────────────────────────────────────

    @staticmethod
    def _parse_input(query: str) -> tuple[str, str]:
        """Detect input type and return (method, value).

        Returns one of:
            ('id', 'UCxxx...')      — raw channel ID
            ('handle', 'MrBeast')   — YouTube handle
            ('search', 'tech ...')  — keyword fallback
        """
        q = query.strip()
        if not q:
            return ('search', q)

        # Raw channel ID
        if q.startswith('UC') and len(q) == 24:
            return ('id', q)

        # Handle with @
        if q.startswith('@'):
            return ('handle', q.lstrip('@'))

        # YouTube URL patterns
        url_match = re.match(
            r'(?:https?://)?(?:www\.)?youtube\.com/(?:channel/|@|c/)([@\w-]+)',
            q,
        )
        if url_match:
            value = url_match.group(1)
            if value.startswith('UC') and len(value) == 24:
                return ('id', value)
            return ('handle', value.lstrip('@'))

        # Plain text — could be a handle without @ or a keyword
        if re.match(r'^[\w.-]+$', q) and len(q) <= 40:
            return ('handle', q)  # Try as handle first; caller falls back to search

        return ('search', q)

    async def resolve_channel(self, query: str) -> dict | None:
        """Resolve a handle, URL, or ID to a channel info dict.

        Returns {channel_id, name, handle, subscribers, thumbnail_url} or None.
        """
        method, value = self._parse_input(query)

        async with httpx.AsyncClient(timeout=15.0) as client:
            if method == 'id':
                items = await self._fetch_channels(client, channel_ids=[value])
            elif method == 'handle':
                data = await self._get(
                    client,
                    endpoint='channels',
                    params={'part': 'snippet,statistics', 'forHandle': value},
                )
                items = data.get('items', [])
                # If handle fails, try as search
                if not items:
                    return await self._search_single(client, query)
            else:
                return await self._search_single(client, query)

        if not items:
            return None

        return self._channel_item_to_preview(items[0])

    async def _search_single(self, client: httpx.AsyncClient, query: str) -> dict | None:
        """Search for a single channel by keyword (100 units)."""
        results = await self._search_channels(client, query=query, limit=1)
        return results[0] if results else None

    async def _search_channels(
        self,
        client: httpx.AsyncClient,
        *,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """Search YouTube channels by keyword."""
        data = await self._get(
            client,
            endpoint='search',
            params={
                'part': 'snippet',
                'type': 'channel',
                'q': query,
                'maxResults': min(limit, 10),
            },
        )

        channel_ids = [
            item['snippet']['channelId']
            for item in data.get('items', [])
            if 'snippet' in item and 'channelId' in item['snippet']
        ]
        if not channel_ids:
            return []

        if not channel_ids:
            # We found items in search, but none had channelIds (rare)
            return []
            
        # Fetch full channel info (1 unit) for subscriber counts etc.
        full_items = await self._fetch_channels(client, channel_ids=channel_ids)
        return [self._channel_item_to_preview(ch) for ch in full_items]

    async def search_channels(self, query: str, limit: int = 5) -> list[dict]:
        """Public method: search channels by keyword."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            return await self._search_channels(client, query=query, limit=limit)

    async def fetch_categories(self, region_code: str = 'US') -> list[dict]:
        """Fetch YouTube video categories."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            data = await self._get(
                client,
                endpoint='videoCategories',
                params={'part': 'snippet', 'regionCode': region_code},
            )

        return [
            {
                'id': item['id'],
                'title': item['snippet']['title'],
                'assignable': item['snippet'].get('assignable', False),
            }
            for item in data.get('items', [])
            if item.get('snippet', {}).get('assignable', False)
        ]

    async def fetch_trending_by_category(
        self,
        category_id: str,
        region_code: str = 'US',
        max_results: int = 50,
    ) -> list[dict]:
        """Fetch trending creators for a category.

        Step 1: Get trending videos in category (1 unit)
        Step 2: Get unique channel info (1 unit)
        Total: 2 units
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Step 1: trending videos — some categories return 404
            try:
                data = await self._get(
                    client,
                    endpoint='videos',
                    params={
                        'part': 'snippet,statistics',
                        'chart': 'mostPopular',
                        'videoCategoryId': category_id,
                        'regionCode': region_code,
                        'maxResults': min(max_results, 50),
                    },
                )
            except ExternalServiceError as exc:
                if '404' in str(exc):
                    return []  # Category has no trending videos
                raise

            # Step 2: extract unique channel IDs
            seen: set[str] = set()
            channel_ids: list[str] = []
            for video in data.get('items', []):
                ch_id = video.get('snippet', {}).get('channelId')
                if ch_id and ch_id not in seen:
                    seen.add(ch_id)
                    channel_ids.append(ch_id)

            if not channel_ids:
                return []

            # Step 3: fetch full channel info
            full_items = await self._fetch_channels(client, channel_ids=channel_ids)

        return [self._channel_item_to_preview(ch) for ch in full_items]

    @staticmethod
    def _channel_item_to_preview(channel: dict) -> dict:
        """Convert a raw YouTube channel API item to a preview dict."""
        snippet = channel.get('snippet', {})
        statistics = channel.get('statistics', {})
        return {
            'channel_id': channel.get('id', ''),
            'name': snippet.get('title', ''),
            'handle': snippet.get('customUrl', ''),
            'description': (snippet.get('description', '') or '')[:150],
            'subscribers': safe_int(statistics.get('subscriberCount')),
            'thumbnail_url': (
                snippet.get('thumbnails', {}).get('medium', {}).get('url')
                or snippet.get('thumbnails', {}).get('default', {}).get('url')
                or ''
            ),
        }

    async def ingest(self, channel_ids: list[str] | None = None) -> NormalizedIngestionPayload:
        payload = NormalizedIngestionPayload()
        if not channel_ids:
            return payload
            
        raw_seeds = channel_ids[:self.settings.YOUTUBE_MAX_CHANNELS_PER_RUN]
        ingested_at = utc_now()

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 0: Resolve handles/URLs to real UC channel IDs
            resolved_ids: list[str] = []
            for seed in raw_seeds:
                seed = seed.strip()
                if seed.startswith('UC') and len(seed) == 24:
                    resolved_ids.append(seed)
                elif seed.startswith('@') or (re.match(r'^[\w.-]+$', seed) and len(seed) <= 40):
                    # Handle — resolve via forHandle
                    handle = seed.lstrip('@')
                    try:
                        data = await self._get(
                            client,
                            endpoint='channels',
                            params={'part': 'id', 'forHandle': handle},
                        )
                        items = data.get('items', [])
                        if items:
                            resolved_ids.append(items[0]['id'])
                        else:
                            payload.warnings.append(f"Handle @{handle} could not be resolved")
                    except Exception as exc:
                        payload.warnings.append(f"Failed to resolve handle @{handle}: {exc}")
                elif 'youtube.com' in seed:
                    # URL — extract via _parse_input
                    method, value = self._parse_input(seed)
                    if method == 'id':
                        resolved_ids.append(value)
                    elif method == 'handle':
                        try:
                            data = await self._get(
                                client,
                                endpoint='channels',
                                params={'part': 'id', 'forHandle': value},
                            )
                            items = data.get('items', [])
                            if items:
                                resolved_ids.append(items[0]['id'])
                        except Exception:
                            payload.warnings.append(f"Failed to resolve URL seed: {seed}")
                else:
                    resolved_ids.append(seed)  # Unknown format, try as-is

            # Deduplicate
            seen: set[str] = set()
            channel_ids = []
            for cid in resolved_ids:
                if cid not in seen:
                    seen.add(cid)
                    channel_ids.append(cid)

            if not channel_ids:
                payload.warnings.append("No valid channel IDs after resolution")
                return payload

            channel_items = await self._fetch_channels(client, channel_ids=channel_ids)

            all_video_ids: list[str] = []
            for channel in channel_items:
                uploads_playlist_id = (
                    channel.get("contentDetails", {})
                    .get("relatedPlaylists", {})
                    .get("uploads")
                )
                if not uploads_playlist_id:
                    payload.warnings.append(
                        f"Channel {channel.get('id')} missing uploads playlist ID"
                    )
                    continue

                try:
                    video_ids = await self._fetch_playlist_video_ids(
                        client,
                        uploads_playlist_id=uploads_playlist_id,
                        max_results=self.settings.YOUTUBE_MAX_VIDEOS_PER_CHANNEL,
                    )
                    all_video_ids.extend(video_ids)
                except Exception as exc:
                    payload.warnings.append(
                        f"Channel {channel.get('id')} failed to fetch videos: {exc}"
                    )

            video_items = await self._fetch_videos(client, video_ids=all_video_ids)

        for channel in channel_items:
            snippet = channel.get("snippet", {})
            statistics = channel.get("statistics", {})
            content_details = channel.get("contentDetails", {})

            creator = NormalizedCreatorRecord(
                platform=self.platform,
                source_type=self.source_type,
                platform_creator_id=channel.get("id", ""),
                creator_name=snippet.get("title", ""),
                creator_handle=snippet.get("customUrl"),
                channel_url=(
                    f"https://www.youtube.com/channel/{channel.get('id')}"
                    if channel.get("id")
                    else None
                ),
                creator_description=snippet.get("description"),
                country_code=snippet.get("country"),
                created_at_platform=parse_iso_datetime(snippet.get("publishedAt")),
                subscriber_count=safe_int(statistics.get("subscriberCount")),
                channel_view_count=safe_int(statistics.get("viewCount")),
                video_count=safe_int(statistics.get("videoCount")),
                uploads_playlist_id=(
                    content_details.get("relatedPlaylists", {}).get("uploads")
                ),
                thumbnail_url=(
                    snippet.get("thumbnails", {})
                    .get("high", {})
                    .get("url")
                    or snippet.get("thumbnails", {}).get("default", {}).get("url")
                ),
                extra_metrics=None,
                raw_payload=channel,
                ingested_at=ingested_at,
            )
            payload.creators.append(creator)

        for video in video_items:
            snippet = video.get("snippet", {})
            statistics = video.get("statistics", {})
            platform_content_id = video.get("id", "")

            content_item = NormalizedContentRecord(
                platform=self.platform,
                platform_creator_id=snippet.get("channelId", ""),
                platform_content_id=platform_content_id,
                content_type=ContentTypeEnum.VIDEO.value,
                title=snippet.get("title", ""),
                description=snippet.get("description"),
                published_at=parse_iso_datetime(snippet.get("publishedAt")),
                content_url=(
                    f"https://www.youtube.com/watch?v={platform_content_id}"
                    if platform_content_id
                    else None
                ),
                category_id=snippet.get("categoryId"),
                channel_title_snapshot=snippet.get("channelTitle"),
                thumbnail_url=(
                    snippet.get("thumbnails", {})
                    .get("high", {})
                    .get("url")
                    or snippet.get("thumbnails", {}).get("default", {}).get("url")
                ),
                tags_json=snippet.get("tags"),
                extra_metrics=None,
                raw_payload=video,
                ingested_at=ingested_at,
            )
            payload.content_items.append(content_item)

            metric = NormalizedMetricRecord(
                platform_content_id=platform_content_id,
                captured_at=ingested_at,
                views=safe_int(statistics.get("viewCount")),
                likes=safe_int(statistics.get("likeCount")),
                comments=safe_int(statistics.get("commentCount")),
                extra_metrics=None,
                raw_payload=statistics,
            )
            payload.metric_snapshots.append(metric)

        payload.records_seen = (
            len(payload.creators)
            + len(payload.content_items)
            + len(payload.metric_snapshots)
        )
        return payload