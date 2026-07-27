"""Tests for user_scraper using Playwright fetcher."""

import pytest
from unittest.mock import patch, MagicMock

from app.utils.douban_fetcher import AntiCrawlBlock, PageFetchTimeout


# Realistic HTML from a watched list page (minimal structure for parser)
WATCHED_PAGE_HTML = """<html><body>
<div class="info">
<span class="count">共 100 部</span>
</div>
<div class="grid-view">
<div class="item">
<a href="https://movie.douban.com/subject/1292052/" class="title">肖申克的救赎</a>
<span class="date">2024-01-15 看过</span>
</div>
<div class="item">
<a href="https://movie.douban.com/subject/1291546/" class="title">霸王别姬</a>
<span class="date">2024-01-10 看过</span>
</div>
</div>
</body></html>"""

EMPTY_WATCHED_HTML = """<html><body>
<div class="info"><span class="count">共 0 部</span></div>
<div class="grid-view"></div>
</body></html>"""


class TestUserScraperUsesPlaywright:
    """Verify scrape_user_watched uses Playwright fetcher with per-user cookie."""

    @patch("app.services.user_scraper.parse_watched_page")
    @patch("app.services.user_scraper.SessionLocal")
    def test_passes_user_cookie_to_fetcher(self, mock_session_factory, mock_parse):
        """User's per-user cookie must be passed to fetcher.fetch_page_with_cookie."""
        from app.services.user_scraper import scrape_user_watched

        # Setup: DB session with no existing watched movies
        mock_db = MagicMock()
        mock_session_factory.return_value = mock_db
        mock_db.query.return_value.filter.return_value.all.return_value = []

        # Parse returns empty → loop breaks immediately
        mock_parse.return_value = ([], 0)

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_page_with_cookie.return_value = EMPTY_WATCHED_HTML

        with patch("app.services.user_scraper.get_douban_fetcher",
                    return_value=mock_fetcher):
            scrape_user_watched(
                user_id="test_user",
                cookie="bid=abc123; ll=108288",
            )

        # Verify fetcher was called with the user's cookie
        assert mock_fetcher.fetch_page_with_cookie.call_count >= 1
        call_args = mock_fetcher.fetch_page_with_cookie.call_args_list[0]
        url_arg = call_args[0][0]
        cookie_arg = call_args[1].get("cookie") or call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("cookie")
        assert "test_user" in url_arg
        assert cookie_arg == "bid=abc123; ll=108288"

    @patch("app.services.user_scraper.parse_watched_page")
    @patch("app.services.user_scraper.SessionLocal")
    def test_retries_on_anticrawl_block(self, mock_session_factory, mock_parse):
        """AntiCrawlBlock should trigger retry before giving up."""
        from app.services.user_scraper import scrape_user_watched

        mock_db = MagicMock()
        mock_session_factory.return_value = mock_db
        mock_db.query.return_value.filter.return_value.all.return_value = []
        # Return 1 movie so `len(all_movies)(1) >= total_count(1) > 0` → True → break
        mock_parse.return_value = ([{"douban_id": "1292052"}], 1)

        mock_fetcher = MagicMock()
        # Fail twice with AntiCrawlBlock, then succeed
        mock_fetcher.fetch_page_with_cookie.side_effect = [
            AntiCrawlBlock("WAF block"),
            AntiCrawlBlock("WAF block again"),
            EMPTY_WATCHED_HTML,
        ]

        with patch("app.services.user_scraper.get_douban_fetcher",
                    return_value=mock_fetcher), \
             patch("app.utils.douban_fetcher.time.sleep"):  # retry now in douban_fetcher
            result = scrape_user_watched(
                user_id="test_user",
                cookie="bid=test",
            )

        assert mock_fetcher.fetch_page_with_cookie.call_count == 3
        assert result["success"] is True

    @patch("app.services.user_scraper.parse_watched_page")
    @patch("app.services.user_scraper.SessionLocal")
    def test_retries_on_page_fetch_timeout(self, mock_session_factory, mock_parse):
        """PageFetchTimeout should trigger retry."""
        from app.services.user_scraper import scrape_user_watched

        mock_db = MagicMock()
        mock_session_factory.return_value = mock_db
        mock_db.query.return_value.filter.return_value.all.return_value = []
        # Return 1 movie so `len(all_movies)(1) >= total_count(1) > 0` → True → break
        mock_parse.return_value = ([{"douban_id": "1292052"}], 1)

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_page_with_cookie.side_effect = [
            PageFetchTimeout("timeout"),
            EMPTY_WATCHED_HTML,
        ]

        with patch("app.services.user_scraper.get_douban_fetcher",
                    return_value=mock_fetcher), \
             patch("app.utils.douban_fetcher.time.sleep"):
            result = scrape_user_watched(
                user_id="test_user",
                cookie="bid=test",
            )

        assert mock_fetcher.fetch_page_with_cookie.call_count == 2
        assert result["success"] is True

    @patch("app.services.user_scraper.parse_watched_page")
    @patch("app.services.user_scraper.SessionLocal")
    def test_gives_up_after_max_retries(self, mock_session_factory, mock_parse):
        """If all retries fail, scrape should report failure."""
        from app.services.user_scraper import scrape_user_watched

        mock_db = MagicMock()
        mock_session_factory.return_value = mock_db
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_parse.return_value = ([], 0)

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_page_with_cookie.side_effect = AntiCrawlBlock("persistent block")

        with patch("app.services.user_scraper.get_douban_fetcher",
                    return_value=mock_fetcher), \
             patch("app.utils.douban_fetcher.time.sleep"):
            result = scrape_user_watched(
                user_id="test_user",
                cookie="bid=test",
            )

        assert result["success"] is False
        assert "error" in result
