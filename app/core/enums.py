from enum import Enum


class PlatformEnum(str, Enum):
    YOUTUBE = "youtube"


class SourceTypeEnum(str, Enum):
    API = "api"
    DATASET = "dataset"
    RSS = "rss"
    SCRAPER = "scraper"


class IngestionTriggerEnum(str, Enum):
    MANUAL = "manual"
    CRON = "cron"
    CLI = "cli"


class IngestionStatusEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


class ContentTypeEnum(str, Enum):
    VIDEO = "video"


class SortDirectionEnum(str, Enum):
    ASC = "asc"
    DESC = "desc"


class ContentSortFieldEnum(str, Enum):
    PUBLISHED_AT = "published_at"
    VIEWS = "views"
    LIKES = "likes"
    COMMENTS = "comments"
    ENGAGEMENT_RATE = "engagement_rate"
    CREATOR_NAME = "creator_name"
    SUBSCRIBER_COUNT = "subscriber_count"


class CreatorSortFieldEnum(str, Enum):
    CREATOR_NAME = "creator_name"
    SUBSCRIBER_COUNT = "subscriber_count"
    CHANNEL_VIEW_COUNT = "channel_view_count"
    VIDEO_COUNT = "video_count"
    CREATED_AT_PLATFORM = "created_at_platform"