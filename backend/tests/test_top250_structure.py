"""Tests for Top 250 page structure validation in douban_fetcher."""

import pytest
from unittest.mock import patch, MagicMock

from app.utils.douban_fetcher import (
    DoubanFetcher,
    get_douban_fetcher,
    reset_douban_fetcher,
    AntiCrawlBlock,
)


class TestTop250StructureValidation:
    """Verify that Top 250 pages without grid_view structure are detected."""

    def teardown_method(self):
        reset_douban_fetcher()

    def test_top250_page_without_grid_view_raises_anticrawl(self):
        """Top 250 URL that returns HTML without grid_view should raise AntiCrawlBlock.

        This catches cases where Douban returns a login wall, regional block,
        or other non-Top250 content that passes other anti-crawl checks.
        """
        fetcher = get_douban_fetcher()

        # Valid HTML but missing grid_view structure (e.g., login page)
        login_wall_html = """<html><head><title>登录豆瓣</title></head>
        <body><div class="login-form">请登录以继续</div></body></html>"""

        with patch.object(DoubanFetcher, '_init_browser') as mock_init, \
             patch.object(DoubanFetcher, '_shutdown'):
            mock_pw = MagicMock()
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 200
            mock_page.goto.return_value = mock_response
            mock_page.content.return_value = login_wall_html
            mock_page.url = "https://movie.douban.com/top250?start=0&filter="
            mock_init.return_value = (mock_pw, mock_browser, mock_context, mock_page)

            fetcher._ensure_worker()

            with pytest.raises(AntiCrawlBlock, match="页面结构异常"):
                fetcher.fetch_page("https://movie.douban.com/top250?start=0&filter=")

    def test_top250_page_with_grid_view_succeeds(self):
        """Top 250 URL that returns HTML with grid_view should succeed."""
        fetcher = get_douban_fetcher()

        # Valid Top 250 HTML with grid_view
        valid_html = """<html><head><title>豆瓣电影 Top 250</title></head>
        <body><ol class="grid_view"><li>电影1</li></ol></body></html>"""

        with patch.object(DoubanFetcher, '_init_browser') as mock_init, \
             patch.object(DoubanFetcher, '_shutdown'):
            mock_pw = MagicMock()
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 200
            mock_page.goto.return_value = mock_response
            mock_page.content.return_value = valid_html
            mock_page.url = "https://movie.douban.com/top250?start=0&filter="
            mock_init.return_value = (mock_pw, mock_browser, mock_context, mock_page)

            fetcher._ensure_worker()

            # Should NOT raise — page has grid_view
            html = fetcher.fetch_page("https://movie.douban.com/top250?start=0&filter=")
            assert "grid_view" in html

    def test_non_top250_page_without_grid_view_succeeds(self):
        """Non-Top250 URLs should NOT be checked for grid_view structure."""
        fetcher = get_douban_fetcher()

        # Non-Top250 page without grid_view (e.g., movie detail page)
        detail_html = """<html><head><title>肖申克的救赎 (豆瓣)</title></head>
        <body><div class="subject">电影详情</div></body></html>"""

        with patch.object(DoubanFetcher, '_init_browser') as mock_init, \
             patch.object(DoubanFetcher, '_shutdown'):
            mock_pw = MagicMock()
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 200
            mock_page.goto.return_value = mock_response
            mock_page.content.return_value = detail_html
            mock_page.url = "https://movie.douban.com/subject/1292052/"
            mock_init.return_value = (mock_pw, mock_browser, mock_context, mock_page)

            fetcher._ensure_worker()

            # Should NOT raise — not a top250 URL, so no grid_view check
            html = fetcher.fetch_page("https://movie.douban.com/subject/1292052/")
            assert "subject" in html
