"""Tests for IMDb crawler fallback extraction."""

from unittest.mock import patch, MagicMock
import json

import pytest

from app.services.imdb_crawler import fetch_imdb_top250, _fetch_imdb_id_from_douban_detail
from app.utils.douban_fetcher import AntiCrawlBlock, PageFetchTimeout


MOCK_MOVIES = [
    {"rank": 1, "title": "The Shawshank Redemption", "imdb_id": "tt0111161",
     "rating": 9.3, "year": 1994},
    {"rank": 2, "title": "The Godfather", "imdb_id": "tt0068646",
     "rating": 9.2, "year": 1972},
]


def _make_next_data(movies):
    """Build a __NEXT_DATA__ JSON string with the given movies."""
    edges = []
    for m in movies:
        edges.append({
            "currentRank": m["rank"],
            "node": {
                "id": m["imdb_id"],
                "titleText": {"text": m["title"]},
                "ratingsSummary": {"aggregateRating": m["rating"]},
                "releaseYear": {"year": m["year"]},
            },
        })
    return json.dumps({
        "props": {"pageProps": {"pageData": {"chartTitles": {"edges": edges}}}}
    })


def _mock_playwright_context(evaluate_return):
    """Create mock Playwright objects that raise on wait_for_selector."""
    from playwright._impl._errors import TimeoutError as PlaywrightTimeoutError
    mock_page = MagicMock()
    mock_page.wait_for_selector.side_effect = PlaywrightTimeoutError("Timeout 30000ms")
    mock_page.evaluate.return_value = evaluate_return

    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page

    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    mock_pw = MagicMock()
    mock_pw.chromium.launch.return_value = mock_browser

    return mock_pw


class TestFetchImdbTop250Fallback:
    """When wait_for_selector times out, extraction should fall through to
    __NEXT_DATA__ / JSON-LD / DOM fallbacks."""

    def test_extracts_via_next_data_when_selector_times_out(self):
        """Selector timeout should not abort — __NEXT_DATA__ should be tried."""
        next_data = _make_next_data(MOCK_MOVIES)
        mock_pw = _mock_playwright_context(next_data)

        with patch("playwright.sync_api.sync_playwright") as mock_sp:
            mock_sp.return_value.__enter__ = MagicMock(return_value=mock_pw)
            mock_sp.return_value.__exit__ = MagicMock(return_value=False)

            movies = fetch_imdb_top250()

        assert len(movies) == 2
        assert movies[0]["imdb_id"] == "tt0111161"
        assert movies[1]["imdb_id"] == "tt0068646"

    def test_non_timeout_error_propagates(self):
        """Non-Timeout Playwright errors (browser crash, page disconnect)
        should propagate — not be silently swallowed."""
        from playwright._impl._errors import TimeoutError as PlaywrightTimeoutError
        mock_pw = _mock_playwright_context(None)
        mock_page = mock_pw.chromium.launch.return_value.new_context.return_value.new_page.return_value
        mock_page.wait_for_selector.side_effect = [
            PlaywrightTimeoutError("Timeout 30000ms"),
            RuntimeError("Browser crashed"),
        ]

        with patch("playwright.sync_api.sync_playwright") as mock_sp:
            mock_sp.return_value.__enter__ = MagicMock(return_value=mock_pw)
            mock_sp.return_value.__exit__ = MagicMock(return_value=False)

            with pytest.raises(RuntimeError, match="Browser crashed"):
                fetch_imdb_top250()

    def test_playwright_timeout_error_is_caught(self):
        """Playwright's own TimeoutError (not Python built-in) should be
        caught and fall through to data extraction."""
        from playwright._impl._errors import TimeoutError as PlaywrightTimeoutError

        next_data = _make_next_data(MOCK_MOVIES)
        mock_pw = _mock_playwright_context(next_data)
        mock_page = mock_pw.chromium.launch.return_value.new_context.return_value.new_page.return_value
        mock_page.wait_for_selector.side_effect = PlaywrightTimeoutError("Timeout 30000ms")

        with patch("playwright.sync_api.sync_playwright") as mock_sp:
            mock_sp.return_value.__enter__ = MagicMock(return_value=mock_pw)
            mock_sp.return_value.__exit__ = MagicMock(return_value=False)

            movies = fetch_imdb_top250()

        assert len(movies) == 2


class TestFetchImdbIdFromDoubanDetailExceptions:
    """Verify _fetch_imdb_id_from_douban_detail exception behavior.

    AntiCrawlBlock should propagate immediately (no retry).
    PageFetchTimeout should be retried up to max_retries, then return (None, None).
    """

    def test_anticrawl_block_returns_none_no_retry(self):
        """AntiCrawlBlock should return (None, None) immediately — no retry, no propagation.

        This prevents the exception from escaping the candidate verification loop
        at imdb_crawler.py:536 and aborting the entire IMDb crawl.
        """
        with patch("app.utils.douban_fetcher.get_douban_fetcher") as mock_get:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch_page.side_effect = AntiCrawlBlock("PoW 挑战页")
            mock_get.return_value = mock_fetcher

            result = _fetch_imdb_id_from_douban_detail("1292052")

            assert result == (None, None)
            # 只调用了 1 次——不重试
            assert mock_fetcher.fetch_page.call_count == 1

    def test_page_fetch_timeout_retries_then_returns_none(self):
        """PageFetchTimeout should retry max_retries times, then return (None, None)."""
        from app.config import settings

        with patch("app.utils.douban_fetcher.get_douban_fetcher") as mock_get:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch_page.side_effect = PageFetchTimeout("超时")
            mock_get.return_value = mock_fetcher

            result = _fetch_imdb_id_from_douban_detail("1292052")

            assert result == (None, None)
            # 重试了 max_retries 次
            assert mock_fetcher.fetch_page.call_count == settings.max_retries

    def test_error_page_returns_none(self):
        """When the fetcher raises AntiCrawlBlock for error pages
        ('没有访问权限', PoW challenge, etc.), _fetch_imdb_id_from_douban_detail
        should return (None, None) without retrying — same as explicit anti-crawl.

        This covers HTTP 404/500 pages that the fetcher now detects.
        """
        with patch("app.utils.douban_fetcher.get_douban_fetcher") as mock_get:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch_page.side_effect = AntiCrawlBlock("没有访问权限: url")
            mock_get.return_value = mock_fetcher

            result = _fetch_imdb_id_from_douban_detail("1292052")

            assert result == (None, None)
            # 不重试
            assert mock_fetcher.fetch_page.call_count == 1
