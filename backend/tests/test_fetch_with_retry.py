"""Tests for fetch_with_retry — shared Playwright retry utility."""

import time

import pytest
from unittest.mock import patch

from app.utils.douban_fetcher import (
    fetch_with_retry,
    AntiCrawlBlock,
    PageFetchTimeout,
)


class TestFetchWithRetry:
    """Verify the generic callable-based retry wrapper."""

    def test_success_on_first_try(self):
        """fetch_fn succeeds immediately → return result, call once."""
        fetch_fn = lambda: "<html>ok</html>"
        result = fetch_with_retry(fetch_fn)
        assert result == "<html>ok</html>"

    def test_retries_on_anticrawl_block(self):
        """AntiCrawlBlock triggers retry; success on 3rd attempt."""
        call_count = 0

        def flaky_fetch():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise AntiCrawlBlock("WAF block")
            return "<html>recovered</html>"

        with patch("app.utils.douban_fetcher.time.sleep"):
            result = fetch_with_retry(flaky_fetch)

        assert result == "<html>recovered</html>"
        assert call_count == 3

    def test_retries_on_page_fetch_timeout(self):
        """PageFetchTimeout triggers retry; success on 2nd attempt."""
        call_count = 0

        def flaky_fetch():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise PageFetchTimeout("timeout")
            return "<html>ok</html>"

        with patch("app.utils.douban_fetcher.time.sleep"):
            result = fetch_with_retry(flaky_fetch)

        assert result == "<html>ok</html>"
        assert call_count == 2

    def test_raises_runtime_error_after_max_retries(self):
        """All attempts fail → RuntimeError with last error chained."""
        def always_fail():
            raise AntiCrawlBlock("persistent block")

        with patch("app.utils.douban_fetcher.time.sleep"):
            with pytest.raises(RuntimeError, match="persistent block"):
                fetch_with_retry(always_fail, max_retries=3)

    def test_uses_long_backoff_for_anticrawl(self):
        """AntiCrawlBlock should use 30-60s backoff (not the short 5-10s)."""
        sleeps = []

        def always_fail():
            raise AntiCrawlBlock("WAF")

        with patch("app.utils.douban_fetcher.time.sleep", side_effect=lambda s: sleeps.append(s)):
            with pytest.raises(RuntimeError):
                fetch_with_retry(always_fail, max_retries=3)

        # 2 sleeps (after attempt 0 and 1, no sleep after last attempt)
        assert len(sleeps) == 2
        assert all(30 <= s <= 60 for s in sleeps)

    def test_uses_short_backoff_for_timeout(self):
        """PageFetchTimeout should use 5-10s backoff."""
        sleeps = []

        def always_fail():
            raise PageFetchTimeout("timeout")

        with patch("app.utils.douban_fetcher.time.sleep", side_effect=lambda s: sleeps.append(s)):
            with pytest.raises(RuntimeError):
                fetch_with_retry(always_fail, max_retries=3)

        assert len(sleeps) == 2
        assert all(5 <= s <= 10 for s in sleeps)

    def test_does_not_retry_other_exceptions(self):
        """Non-fetcher exceptions (RuntimeError, ValueError) propagate immediately."""
        call_count = 0

        def raise_other():
            nonlocal call_count
            call_count += 1
            raise ValueError("unexpected")

        with pytest.raises(ValueError, match="unexpected"):
            fetch_with_retry(raise_other)

        assert call_count == 1  # no retry

    def test_custom_max_retries(self):
        """max_retries parameter controls attempt count."""
        call_count = 0

        def always_fail():
            nonlocal call_count
            call_count += 1
            raise AntiCrawlBlock("block")

        with patch("app.utils.douban_fetcher.time.sleep"):
            with pytest.raises(RuntimeError):
                fetch_with_retry(always_fail, max_retries=5)

        assert call_count == 5

    def test_context_tag_appears_in_runtime_error(self):
        """When context is provided, RuntimeError message includes it."""
        def always_fail():
            raise AntiCrawlBlock("block")

        with patch("app.utils.douban_fetcher.time.sleep"):
            with pytest.raises(RuntimeError, match="top250_list.*block"):
                fetch_with_retry(always_fail, context="top250_list")

    def test_context_none_works(self):
        """context=None should work (no context in error message)."""
        def always_fail():
            raise AntiCrawlBlock("block")

        with patch("app.utils.douban_fetcher.time.sleep"):
            with pytest.raises(RuntimeError, match="block"):
                fetch_with_retry(always_fail, context=None)
