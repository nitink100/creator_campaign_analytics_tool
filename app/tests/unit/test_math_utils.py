from __future__ import annotations

import pytest

from app.utils.math_utils import compute_engagement_rate, safe_float, safe_int


class TestSafeInt:
    def test_none(self):
        assert safe_int(None) is None

    def test_valid_string(self):
        assert safe_int("12345") == 12345

    def test_valid_int(self):
        assert safe_int(42) == 42

    def test_valid_float(self):
        assert safe_int(3.9) == 3

    def test_empty_string(self):
        assert safe_int("") is None

    def test_non_numeric_string(self):
        assert safe_int("abc") is None

    def test_zero(self):
        assert safe_int("0") == 0
        assert safe_int(0) == 0


class TestSafeFloat:
    def test_none(self):
        assert safe_float(None) is None

    def test_valid_string(self):
        assert safe_float("3.14") == pytest.approx(3.14)

    def test_int_input(self):
        assert safe_float(5) == 5.0

    def test_non_numeric(self):
        assert safe_float("abc") is None


class TestComputeEngagementRate:
    def test_normal(self):
        result = compute_engagement_rate(views=1000, likes=50, comments=10)
        assert result == pytest.approx(0.06, abs=1e-6)

    def test_zero_views_returns_none(self):
        assert compute_engagement_rate(views=0, likes=5, comments=5) is None

    def test_none_views_returns_none(self):
        assert compute_engagement_rate(views=None, likes=5, comments=5) is None

    def test_none_likes_treated_as_zero(self):
        result = compute_engagement_rate(views=100, likes=None, comments=10)
        assert result == pytest.approx(0.1, abs=1e-6)

    def test_none_comments_treated_as_zero(self):
        result = compute_engagement_rate(views=100, likes=10, comments=None)
        assert result == pytest.approx(0.1, abs=1e-6)

    def test_all_none_metrics_returns_none(self):
        assert compute_engagement_rate(views=None, likes=None, comments=None) is None

    def test_likes_and_comments_none_returns_none(self):
        assert compute_engagement_rate(views=100, likes=None, comments=None) is None

    def test_large_numbers(self):
        result = compute_engagement_rate(views=1_000_000, likes=50_000, comments=10_000)
        assert result == pytest.approx(0.06, abs=1e-6)
