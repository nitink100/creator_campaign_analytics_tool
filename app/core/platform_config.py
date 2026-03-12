PLATFORM_CONFIG = {
    "youtube": {
        "enabled_sources": ["api"],
        "default_source": "api",
        "supported_filters": {
            "content": [
                "creator_name",
                "published_after",
                "published_before",
                "min_subscriber_count",
                "max_subscriber_count",
                "min_views",
                "max_views",
                "min_likes",
                "max_likes",
                "min_comments",
                "max_comments",
                "min_engagement_rate",
                "max_engagement_rate",
            ],
            "creator": [
                "creator_name",
                "min_subscriber_count",
                "max_subscriber_count",
                "min_channel_view_count",
                "max_channel_view_count",
                "min_video_count",
                "max_video_count",
            ],
        },
        "supported_sort_fields": {
            "content": [
                "published_at",
                "views",
                "likes",
                "comments",
                "engagement_rate",
                "subscriber_count",
                "creator_name",
            ],
            "creator": [
                "creator_name",
                "subscriber_count",
                "channel_view_count",
                "video_count",
                "created_at_platform",
            ],
        },
        "display_only_extra_fields": [
            "default_language",
            "topic_categories",
            "thumbnails",
        ],
        "ingestion_caps": {
            "max_channels_per_run": 25,
            "max_videos_per_channel": 100,
        },
    }
}