"""Tests for douban_search_by_imdb_id using Playwright fetcher."""

import pytest
from unittest.mock import patch, MagicMock

from app.services.imdb_crawler import _douban_search_by_imdb_id
from app.utils.douban_fetcher import AntiCrawlBlock, PageFetchTimeout


SEARCH_RESULT_HTML = """<html><body>
<div class="item-root">
<a href="https://movie.douban.com/subject/1292052/" class="title">
肖申克的救赎 The Shawshank Redemption
</a>
</div>
<div class="item-root">
<a href="https://movie.douban.com/subject/9999999/" class="title">
另一部电影
</a>
</div>
</body></html>"""

EMPTY_SEARCH_HTML = """<html><body>
<div class="empty-result">没有搜索结果</div>
</body></html>"""


class TestDoubanSearchByImdbId:
    """Verify _douban_search_by_imdb_id uses Playwright fetcher."""

    def test_uses_playwright_fetcher(self):
        """Should call douban_fetcher.fetch_page instead of raw httpx."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_page.return_value = SEARCH_RESULT_HTML

        with patch("app.services.imdb_crawler.get_douban_fetcher",
                    return_value=mock_fetcher):
            result = _douban_search_by_imdb_id("tt0111161")

        assert result == "1292052"
        mock_fetcher.fetch_page.assert_called_once_with(
            "https://search.douban.com/movie/subject_search?search_text=tt0111161"
        )

    def test_empty_imdb_id_returns_none(self):
        """Empty/None imdb_id should short-circuit without calling fetcher."""
        mock_fetcher = MagicMock()

        with patch("app.services.imdb_crawler.get_douban_fetcher",
                    return_value=mock_fetcher):
            assert _douban_search_by_imdb_id("") is None
            assert _douban_search_by_imdb_id(None) is None

        mock_fetcher.fetch_page.assert_not_called()

    def test_no_subject_link_returns_none(self):
        """Search page with no subject/ links → None."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_page.return_value = EMPTY_SEARCH_HTML

        with patch("app.services.imdb_crawler.get_douban_fetcher",
                    return_value=mock_fetcher):
            result = _douban_search_by_imdb_id("tt9999999")

        assert result is None

    def test_anticrawl_block_retries_then_returns_none(self):
        """AntiCrawlBlock triggers retry; after max_retries → None."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_page.side_effect = AntiCrawlBlock("反爬封锁")

        with patch("app.services.imdb_crawler.get_douban_fetcher",
                    return_value=mock_fetcher), \
             patch("app.utils.douban_fetcher.time.sleep"):
            result = _douban_search_by_imdb_id("tt0111161")

        assert result is None
        assert mock_fetcher.fetch_page.call_count == 3

    def test_anticrawl_block_retries_then_succeeds(self):
        """AntiCrawlBlock on first 2 attempts, success on 3rd."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_page.side_effect = [
            AntiCrawlBlock("block 1"),
            AntiCrawlBlock("block 2"),
            SEARCH_RESULT_HTML,
        ]

        with patch("app.services.imdb_crawler.get_douban_fetcher",
                    return_value=mock_fetcher), \
             patch("app.utils.douban_fetcher.time.sleep"):
            result = _douban_search_by_imdb_id("tt0111161")

        assert result == "1292052"
        assert mock_fetcher.fetch_page.call_count == 3

    def test_page_fetch_timeout_retries_then_returns_none(self):
        """PageFetchTimeout triggers retry; after max_retries → None."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_page.side_effect = PageFetchTimeout("超时")

        with patch("app.services.imdb_crawler.get_douban_fetcher",
                    return_value=mock_fetcher), \
             patch("app.utils.douban_fetcher.time.sleep"):
            result = _douban_search_by_imdb_id("tt0111161")

        assert result is None
        assert mock_fetcher.fetch_page.call_count == 3

    def test_generic_exception_returns_none(self):
        """Any unexpected exception → None (not raise)."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_page.side_effect = RuntimeError("unexpected")

        with patch("app.services.imdb_crawler.get_douban_fetcher",
                    return_value=mock_fetcher):
            result = _douban_search_by_imdb_id("tt0111161")

        assert result is None
