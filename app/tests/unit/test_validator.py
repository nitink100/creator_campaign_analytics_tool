from __future__ import annotations

import pytest
from datetime import datetime, timezone

from app.core.enums import ContentTypeEnum, PlatformEnum, SourceTypeEnum
from app.core.exceptions import ValidationError
from app.services.ingestion.normalizer import (
    NormalizedContentRecord,
    NormalizedCreatorRecord,
    NormalizedMetricRecord,
)
from app.services.ingestion.validator import (
    validate_content_record,
    validate_creator_record,
    validate_metric_record,
)


class TestValidateCreatorRecord:
    def _make_creator(self, **overrides) -> NormalizedCreatorRecord:
        defaults = {
            "platform": PlatformEnum.YOUTUBE.value,
            "source_type": SourceTypeEnum.API.value,
            "platform_creator_id": "UC123",
            "creator_name": "Test Creator",
        }
        defaults.update(overrides)
        return NormalizedCreatorRecord(**defaults)

    def test_valid_record(self):
        record = self._make_creator()
        result = validate_creator_record(record)
        assert result.platform_creator_id == "UC123"

    def test_missing_platform_creator_id(self):
        with pytest.raises(ValidationError, match="platform_creator_id"):
            validate_creator_record(self._make_creator(platform_creator_id=""))

    def test_missing_creator_name(self):
        with pytest.raises(ValidationError, match="creator_name"):
            validate_creator_record(self._make_creator(creator_name=""))

    def test_unsupported_platform(self):
        with pytest.raises(ValidationError, match="unsupported platform"):
            validate_creator_record(self._make_creator(platform="tiktok"))

    def test_unsupported_source_type(self):
        with pytest.raises(ValidationError, match="unsupported source_type"):
            validate_creator_record(self._make_creator(source_type="magic"))


class TestValidateContentRecord:
    def _make_content(self, **overrides) -> NormalizedContentRecord:
        defaults = {
            "platform": PlatformEnum.YOUTUBE.value,
            "platform_creator_id": "UC123",
            "platform_content_id": "vid_abc",
            "content_type": ContentTypeEnum.VIDEO.value,
            "title": "Test Video",
        }
        defaults.update(overrides)
        return NormalizedContentRecord(**defaults)

    def test_valid_record(self):
        record = self._make_content()
        result = validate_content_record(record)
        assert result.title == "Test Video"

    def test_missing_platform_content_id(self):
        with pytest.raises(ValidationError, match="platform_content_id"):
            validate_content_record(self._make_content(platform_content_id=""))

    def test_missing_title(self):
        with pytest.raises(ValidationError, match="title"):
            validate_content_record(self._make_content(title=""))

    def test_unsupported_content_type(self):
        with pytest.raises(ValidationError, match="unsupported content_type"):
            validate_content_record(self._make_content(content_type="podcast"))


class TestValidateMetricRecord:
    def _make_metric(self, **overrides) -> NormalizedMetricRecord:
        defaults = {
            "platform_content_id": "vid_abc",
            "captured_at": datetime.now(timezone.utc),
            "views": 100,
            "likes": 10,
            "comments": 5,
        }
        defaults.update(overrides)
        return NormalizedMetricRecord(**defaults)

    def test_valid_record_computes_engagement_rate(self):
        record = self._make_metric(views=1000, likes=50, comments=10)
        result = validate_metric_record(record)
        assert result.engagement_rate == pytest.approx(0.06, abs=1e-6)

    def test_missing_platform_content_id(self):
        with pytest.raises(ValidationError, match="platform_content_id"):
            validate_metric_record(self._make_metric(platform_content_id=""))

    def test_negative_views(self):
        with pytest.raises(ValidationError, match="negative views"):
            validate_metric_record(self._make_metric(views=-1))

    def test_negative_likes(self):
        with pytest.raises(ValidationError, match="negative likes"):
            validate_metric_record(self._make_metric(likes=-1))

    def test_negative_comments(self):
        with pytest.raises(ValidationError, match="negative comments"):
            validate_metric_record(self._make_metric(comments=-1))

    def test_zero_views_engagement_rate_is_none(self):
        record = self._make_metric(views=0, likes=5, comments=5)
        result = validate_metric_record(record)
        assert result.engagement_rate is None
