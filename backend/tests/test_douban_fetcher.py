"""Tests for Playwright dispatch-thread fetcher and cookie validation."""

import threading
import time
from unittest.mock import patch, MagicMock

import pytest

from app.utils.douban_fetcher import (
    DoubanFetcher,
    get_douban_fetcher,
    reset_douban_fetcher,
    PageFetchTimeout,
    AntiCrawlBlock,
)
from app.services.metadata import check_cookie_valid


class TestDispatchThread:
    """Verify dispatch-thread architecture: all Playwright ops on one thread."""

    def teardown_method(self):
        reset_douban_fetcher()

    def test_cross_thread_fetch_no_greenlet_error(self):
        """Bug repro: fetching from a different thread than the one that
        created the browser must NOT raise 'Cannot switch to a different thread'.

        This was the root cause of both metadata fetch failures and cookie
        validation failures in production.
        """
        results = {}
        errors = {}

        def fetch_from_thread(thread_name):
            try:
                fetcher = get_douban_fetcher()
                # Mock the Playwright internals to return known HTML
                # (avoid real network calls)
                html = fetcher.fetch_page("https://movie.douban.com/subject/1292052/")
                results[thread_name] = html
            except Exception as e:
                errors[thread_name] = e

        # Patch the internal Playwright operations to avoid real browser
        with patch.object(DoubanFetcher, '_init_browser') as mock_init, \
             patch.object(DoubanFetcher, '_handle_fetch') as mock_fetch, \
             patch.object(DoubanFetcher, '_shutdown'):
            mock_init.return_value = (MagicMock(), MagicMock(), MagicMock(), MagicMock())
            mock_fetch.return_value = "<html>test page</html>"

            # Thread A creates the fetcher
            t1 = threading.Thread(target=fetch_from_thread, args=("A",))
            # Thread B uses the same fetcher from a different thread
            t2 = threading.Thread(target=fetch_from_thread, args=("B",))

            t1.start()
            t1.join(timeout=10)
            t2.start()
            t2.join(timeout=10)

        # Both threads should succeed — no greenlet error
        assert "A" not in errors, f"Thread A failed: {errors.get('A')}"
        assert "B" not in errors, f"Thread B failed: {errors.get('B')}"
        assert results.get("A") == "<html>test page</html>"
        assert results.get("B") == "<html>test page</html>"

    def test_cookie_injected_on_every_fetch(self):
        """Bug repro: fetch_page_with_cookie must inject the cookie on every
        call, even when the browser already exists. Previously, cookies were
        only injected at browser creation time.
        """
        fetcher = get_douban_fetcher()
        captured_cookies = []

        def mock_handle_fetch(self, page, context, url, cookie):
            captured_cookies.append(cookie)
            return "<html>ok</html>"

        with patch.object(DoubanFetcher, '_init_browser') as mock_init, \
             patch.object(DoubanFetcher, '_handle_fetch', mock_handle_fetch), \
             patch.object(DoubanFetcher, '_shutdown'):
            mock_init.return_value = (MagicMock(), MagicMock(), MagicMock(), MagicMock())

            # Fetch with no cookie
            fetcher.fetch_page("https://movie.douban.com/subject/1/")
            # Fetch with custom cookie
            fetcher.fetch_page_with_cookie(
                "https://movie.douban.com/mine?status=collect",
                "bid=abc123; ll=108288",
            )
            # Fetch again with different cookie
            fetcher.fetch_page_with_cookie(
                "https://movie.douban.com/mine?status=collect",
                "bid=new_cookie; ll=999",
            )

        # Each call should pass the correct cookie to _handle_fetch
        assert len(captured_cookies) == 3
        assert captured_cookies[0] is None          # fetch_page → None
        assert captured_cookies[1] == "bid=abc123; ll=108288"
        assert captured_cookies[2] == "bid=new_cookie; ll=999"

    def test_exception_propagated_not_returned_as_value(self):
        """Bug fix: exceptions from _handle_fetch must be RAISED to the caller,
        not returned as the future's result value. Previously used
        future.set_result(exception) which returned the exception object.
        """
        fetcher = get_douban_fetcher()

        with patch.object(DoubanFetcher, '_init_browser') as mock_init, \
             patch.object(DoubanFetcher, '_handle_fetch') as mock_fetch, \
             patch.object(DoubanFetcher, '_shutdown'):
            mock_init.return_value = (MagicMock(), MagicMock(), MagicMock(), MagicMock())
            mock_fetch.side_effect = PageFetchTimeout("模拟超时")

            with pytest.raises(PageFetchTimeout, match="模拟超时"):
                fetcher.fetch_page("https://movie.douban.com/subject/1/")

    def test_worker_crash_auto_recovers(self):
        """Bug fix: when the dispatch thread dies (e.g., Chromium OOM),
        the next fetch_page call should auto-respawn the worker instead
        of permanently raising '请重启后端'.
        """
        fetcher = get_douban_fetcher()

        with patch.object(DoubanFetcher, '_init_browser') as mock_init, \
             patch.object(DoubanFetcher, '_handle_fetch') as mock_fetch, \
             patch.object(DoubanFetcher, '_shutdown'):
            mock_init.return_value = (MagicMock(), MagicMock(), MagicMock(), MagicMock())
            mock_fetch.return_value = "<html>recovered</html>"

            # Start worker
            fetcher._ensure_worker()
            original_worker = fetcher._worker_thread
            assert original_worker.is_alive()

            # Simulate worker death (e.g., Chromium OOM-kill)
            # Kill the worker thread by exiting its loop
            fetcher._cmd_queue.put(('close',))
            original_worker.join(timeout=5)
            assert not original_worker.is_alive()
            # _started is still True (the bug condition)
            assert fetcher._started is True

            # Next fetch should auto-respawn, NOT raise PageFetchTimeout
            html = fetcher.fetch_page("https://movie.douban.com/subject/1/")
            assert html == "<html>recovered</html>"
            # Worker was respawned
            assert fetcher._worker_thread is not original_worker
            assert fetcher._worker_thread.is_alive()

    def test_close_prevents_respawn(self):
        """Bug fix: after close(), fetch_page should raise PageFetchTimeout
        rather than silently respawning a new worker. Without a _closed flag,
        concurrent fetch_page() after close() could respawn, violating shutdown.
        """
        fetcher = get_douban_fetcher()

        with patch.object(DoubanFetcher, '_init_browser') as mock_init, \
             patch.object(DoubanFetcher, '_handle_fetch') as mock_fetch, \
             patch.object(DoubanFetcher, '_shutdown'):
            mock_init.return_value = (MagicMock(), MagicMock(), MagicMock(), MagicMock())
            mock_fetch.return_value = "<html>should not reach</html>"

            fetcher._ensure_worker()
            assert fetcher._started is True

            # Close
            fetcher.close()
            time.sleep(0.2)

            # After close, fetch_page should NOT respawn — should raise
            with pytest.raises(PageFetchTimeout):
                fetcher.fetch_page("https://movie.douban.com/subject/1/")

    def test_pow_challenge_page_raises_anticrawl(self):
        """Bug fix: if PoW challenge page is still present after the wait
        (Playwright failed to solve within timeout), the fetcher should
        raise AntiCrawlBlock instead of returning challenge HTML as valid.

        Uses realistic PoW page structure matching http_client.py's detection:
        <input name="cha"> + <input name="tok"> + sha512 JS.
        """
        fetcher = get_douban_fetcher()

        # Realistic PoW challenge page (matches http_client.py detection)
        pow_html = """<html><body>
        <form><input name="cha" value="abc123"><input name="tok" value="def456"></form>
        <script>function solve(){var sha512=..."}</script>
        </body></html>"""

        with patch.object(DoubanFetcher, '_init_browser') as mock_init, \
             patch.object(DoubanFetcher, '_shutdown'):
            mock_pw = MagicMock()
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_page.content.return_value = pow_html
            mock_page.url = "https://movie.douban.com/subject/1292052/"
            mock_init.return_value = (mock_pw, mock_browser, mock_context, mock_page)

            fetcher._ensure_worker()

            with pytest.raises(AntiCrawlBlock):
                fetcher.fetch_page("https://movie.douban.com/subject/1292052/")

    def test_normal_page_with_tok_param_does_not_trigger_pow(self):
        """False positive prevention: a normal movie page that has
        name="tok" (form field) + sha512 (SRI attribute) but NOT name="cha"
        should NOT be classified as a PoW challenge page.

        PoW detection requires ALL THREE: name="tok" AND name="cha" AND sha512.
        This test verifies partial matches don't trigger false positives.
        """
        fetcher = get_douban_fetcher()

        # Partial PoW match: has name="tok" + sha512, but NO name="cha"
        # Real PoW pages need both name="tok" AND name="cha"
        normal_html = """<html><head><title>肖申克的救赎 (豆瓣)</title>
        <script integrity="sha512-abc123..."></script></head>
        <body>
        <form><input name="tok" value="session_token"></form>
        <a href="?tok=abc123">link</a>
        <div class="movie">电影详情内容</div></body></html>"""

        with patch.object(DoubanFetcher, '_init_browser') as mock_init, \
             patch.object(DoubanFetcher, '_shutdown'):
            mock_pw = MagicMock()
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_page.content.return_value = normal_html
            mock_page.url = "https://movie.douban.com/subject/1292052/"
            mock_init.return_value = (mock_pw, mock_browser, mock_context, mock_page)

            fetcher._ensure_worker()

            # Should NOT raise — partial match is not a PoW page
            html = fetcher.fetch_page("https://movie.douban.com/subject/1292052/")
            assert "肖申克的救赎" in html

    def test_no_access_page_raises_anticrawl(self):
        """Bug fix: '没有访问权限' page should raise AntiCrawlBlock in the
        fetcher (not just in check_cookie_valid). Otherwise metadata backfill
        treats it as valid → parse fails → 30-day skip.
        """
        fetcher = get_douban_fetcher()

        no_access_html = "<html><head><title>没有访问权限</title></head><body>您没有访问权限</body></html>"

        with patch.object(DoubanFetcher, '_init_browser') as mock_init, \
             patch.object(DoubanFetcher, '_shutdown'):
            mock_pw = MagicMock()
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_page.content.return_value = no_access_html
            mock_page.url = "https://movie.douban.com/subject/1292052/"
            mock_init.return_value = (mock_pw, mock_browser, mock_context, mock_page)

            fetcher._ensure_worker()

            with pytest.raises(AntiCrawlBlock):
                fetcher.fetch_page("https://movie.douban.com/subject/1292052/")

    def test_detects_abnormal_request_raises_anticrawl(self):
        """'检测到有异常请求' page should raise AntiCrawlBlock in the fetcher.
        This is the third anti-crawl detection pattern (alongside
        '没有访问权限' and PoW challenge).
        """
        fetcher = get_douban_fetcher()

        abnormal_html = "<html><head><title>异常请求</title></head><body>检测到有异常请求，请稍后再试</body></html>"

        with patch.object(DoubanFetcher, '_init_browser') as mock_init, \
             patch.object(DoubanFetcher, '_shutdown'):
            mock_pw = MagicMock()
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_page.content.return_value = abnormal_html
            mock_page.url = "https://movie.douban.com/subject/1292052/"
            mock_init.return_value = (mock_pw, mock_browser, mock_context, mock_page)

            fetcher._ensure_worker()

            with pytest.raises(AntiCrawlBlock, match="反爬封锁"):
                fetcher.fetch_page("https://movie.douban.com/subject/1292052/")

    def test_http_429_response_raises_anticrawl(self):
        """HTTP 429 status must raise AntiCrawlBlock, NOT return the
        429 error page HTML. Otherwise parse_detail_page extracts
        '429 Too Many Requests' as the movie title — data corruption.
        """
        fetcher = get_douban_fetcher()

        error_429_html = "<html><head><title>429 Too Many Requests</title></head><body>Too many requests</body></html>"

        with patch.object(DoubanFetcher, '_init_browser') as mock_init, \
             patch.object(DoubanFetcher, '_shutdown'):
            mock_pw = MagicMock()
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            # Simulate: page.goto returns a response with status 429
            mock_response = MagicMock()
            mock_response.status = 429
            mock_page.goto.return_value = mock_response
            mock_page.content.return_value = error_429_html
            mock_page.url = "https://movie.douban.com/subject/36808876/"
            mock_init.return_value = (mock_pw, mock_browser, mock_context, mock_page)

            fetcher._ensure_worker()

            with pytest.raises(AntiCrawlBlock, match="HTTP 429"):
                fetcher.fetch_page("https://movie.douban.com/subject/36808876/")

    def test_429_in_page_content_raises_anticrawl(self):
        """When response status is None/200 but page body contains
        '429 Too Many Requests' (e.g., after redirect), the fetcher
        must still detect it via content check.
        """
        fetcher = get_douban_fetcher()

        error_429_html = "<html><head><title>429 Too Many Requests</title></head><body>Too many requests</body></html>"

        with patch.object(DoubanFetcher, '_init_browser') as mock_init, \
             patch.object(DoubanFetcher, '_shutdown'):
            mock_pw = MagicMock()
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            # Status is 200 but content is 429 error page
            mock_response = MagicMock()
            mock_response.status = 200
            mock_page.goto.return_value = mock_response
            mock_page.content.return_value = error_429_html
            mock_page.url = "https://movie.douban.com/subject/36808876/"
            mock_init.return_value = (mock_pw, mock_browser, mock_context, mock_page)

            fetcher._ensure_worker()

            with pytest.raises(AntiCrawlBlock, match="429"):
                fetcher.fetch_page("https://movie.douban.com/subject/36808876/")

    def test_503_in_page_content_raises_anticrawl(self):
        """Content-based fallback must detect ALL HTTP error statuses,
        not just 429. When a 503 error page arrives via redirect (status=200
        but body is 503 error), the content check must catch it.
        """
        fetcher = get_douban_fetcher()

        error_html = "<html><head><title>503 Service Unavailable</title></head><body></body></html>"

        with patch.object(DoubanFetcher, '_init_browser') as mock_init, \
             patch.object(DoubanFetcher, '_shutdown'):
            mock_pw = MagicMock()
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 200  # status OK (redirected)
            mock_page.goto.return_value = mock_response
            mock_page.content.return_value = error_html
            mock_page.url = "https://movie.douban.com/subject/1292052/"
            mock_init.return_value = (mock_pw, mock_browser, mock_context, mock_page)

            fetcher._ensure_worker()

            with pytest.raises(AntiCrawlBlock, match="503"):
                fetcher.fetch_page("https://movie.douban.com/subject/1292052/")

    def test_http_503_response_raises_anticrawl(self):
        """HTTP 502/503/504 error pages should also raise AntiCrawlBlock.
        Otherwise parse_detail_page returns empty info, but metadata.py
        still sets last_meta_fetch → movie skipped for 30 days with
        no metadata obtained.
        """
        fetcher = get_douban_fetcher()

        error_html = "<html><head><title>503 Service Unavailable</title></head><body></body></html>"

        with patch.object(DoubanFetcher, '_init_browser') as mock_init, \
             patch.object(DoubanFetcher, '_shutdown'):
            mock_pw = MagicMock()
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 503
            mock_page.goto.return_value = mock_response
            mock_page.content.return_value = error_html
            mock_page.url = "https://movie.douban.com/subject/1292052/"
            mock_init.return_value = (mock_pw, mock_browser, mock_context, mock_page)

            fetcher._ensure_worker()

            with pytest.raises(AntiCrawlBlock, match="HTTP 503"):
                fetcher.fetch_page("https://movie.douban.com/subject/1292052/")

    def test_http_200_does_not_raise(self):
        """Normal 200 response must NOT raise AntiCrawlBlock."""
        fetcher = get_douban_fetcher()

        normal_html = "<html><head><title>肖申克的救赎 (豆瓣)</title></head><body>内容</body></html>"

        with patch.object(DoubanFetcher, '_init_browser') as mock_init, \
             patch.object(DoubanFetcher, '_shutdown'):
            mock_pw = MagicMock()
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 200
            mock_page.goto.return_value = mock_response
            mock_page.content.return_value = normal_html
            mock_page.url = "https://movie.douban.com/subject/1292052/"
            mock_init.return_value = (mock_pw, mock_browser, mock_context, mock_page)

            fetcher._ensure_worker()

            # Should NOT raise — 200 is a normal response
            html = fetcher.fetch_page("https://movie.douban.com/subject/1292052/")
            assert "肖申克的救赎" in html

    def test_waits_for_load_state_before_reading_content(self):
        """Bug fix: page.content() was called while the page was still
        navigating (e.g., after a JS redirect), causing:
        'Page.content: Unable to retrieve content because the page is
        navigating and changing the content.'

        The fix calls page.wait_for_load_state("load") after the initial
        goto + PoW wait, ensuring the load event has fired before reading
        the HTML. Without wait_for_load_state, content() throws mid-nav.
        """
        fetcher = get_douban_fetcher()
        normal_html = "<html><head><title>浪客剑心 (豆瓣)</title></head><body>内容</body></html>"

        with patch.object(DoubanFetcher, '_init_browser') as mock_init, \
             patch.object(DoubanFetcher, '_shutdown'):
            mock_pw = MagicMock()
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()

            mock_response = MagicMock()
            mock_response.status = 200
            mock_page.goto.return_value = mock_response
            mock_page.url = "https://movie.douban.com/subject/1421721/"

            # Simulate the real bug: content() raises while navigating
            def content_side_effect():
                if not mock_page.wait_for_load_state.called:
                    raise Exception(
                        "Page.content: Unable to retrieve content "
                        "because the page is navigating and changing "
                        "the content."
                    )
                return normal_html

            mock_page.content.side_effect = content_side_effect

            mock_init.return_value = (
                mock_pw, mock_browser, mock_context, mock_page
            )
            fetcher._ensure_worker()

            # Should NOT raise — wait_for_load_state("load") must be
            # called before content()
            result = fetcher.fetch_page(
                "https://movie.douban.com/subject/1421721/"
            )

            assert result == normal_html
            mock_page.wait_for_load_state.assert_called_once()
            # Verify state parameter and timeout
            call_args = mock_page.wait_for_load_state.call_args
            assert call_args[0][0] == "load"
            assert "timeout" in call_args[1]
            # Verify ordering: wait_for_load_state called BEFORE content
            # by checking the call counts after success
            assert mock_page.content.call_count >= 1

    def test_wait_for_load_state_timeout_raises_page_fetch_timeout(self):
        """If wait_for_load_state('load') itself times out (e.g., page
        stuck in a redirect loop), the error should be wrapped as
        PageFetchTimeout, not leak the raw Playwright exception.
        """
        from playwright.sync_api import TimeoutError as PlaywrightTimeout

        fetcher = get_douban_fetcher()

        with patch.object(DoubanFetcher, '_init_browser') as mock_init, \
             patch.object(DoubanFetcher, '_shutdown'):
            mock_pw = MagicMock()
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()

            mock_response = MagicMock()
            mock_response.status = 200
            mock_page.goto.return_value = mock_response
            mock_page.url = "https://movie.douban.com/subject/1421721/"

            # wait_for_load_state times out (page stuck navigating)
            mock_page.wait_for_load_state.side_effect = PlaywrightTimeout(
                "Timeout 30000ms exceeded."
            )

            mock_init.return_value = (
                mock_pw, mock_browser, mock_context, mock_page
            )
            fetcher._ensure_worker()

            with pytest.raises(PageFetchTimeout):
                fetcher.fetch_page(
                    "https://movie.douban.com/subject/1421721/"
                )

    def test_wait_for_load_state_uses_configured_timeout(self):
        """wait_for_load_state must use the same timeout as page.goto
        (settings.playwright_timeout_ms), not Playwright's default 30s.
        Otherwise the total fetch time could exceed the future's timeout,
        producing a generic 'Dispatch 线程超时' error instead of the more
        specific 'Playwright 超时' error.
        """
        from app.config import settings

        fetcher = get_douban_fetcher()
        normal_html = "<html><head><title>Test</title></head><body>内容</body></html>"

        with patch.object(DoubanFetcher, '_init_browser') as mock_init, \
             patch.object(DoubanFetcher, '_shutdown'):
            mock_pw = MagicMock()
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()

            mock_response = MagicMock()
            mock_response.status = 200
            mock_page.goto.return_value = mock_response
            mock_page.url = "https://movie.douban.com/subject/1292052/"
            mock_page.content.return_value = normal_html

            mock_init.return_value = (
                mock_pw, mock_browser, mock_context, mock_page
            )
            fetcher._ensure_worker()

            fetcher.fetch_page("https://movie.douban.com/subject/1292052/")

            # Verify wait_for_load_state was called with explicit timeout
            mock_page.wait_for_load_state.assert_called_once()
            call_args = mock_page.wait_for_load_state.call_args
            assert call_args[0][0] == "load"
            # Timeout should match settings.playwright_timeout_ms
            assert call_args[1].get("timeout") == settings.playwright_timeout_ms

    def test_close_stops_worker_thread(self):
        """close() should stop the dispatch thread cleanly."""
        fetcher = get_douban_fetcher()

        with patch.object(DoubanFetcher, '_init_browser') as mock_init, \
             patch.object(DoubanFetcher, '_shutdown'):
            mock_init.return_value = (MagicMock(), MagicMock(), MagicMock(), MagicMock())

            # Trigger worker start
            fetcher._ensure_worker()
            assert fetcher._started is True
            worker = fetcher._worker_thread
            assert worker is not None
            assert worker.is_alive()

            # Close
            fetcher.close()
            assert fetcher._started is False
            # Worker thread should exit (it's a daemon, but check it's not alive)
            time.sleep(0.2)  # Give it time to process the close command
            assert not worker.is_alive()


class TestCheckCookieValid:
    """Verify check_cookie_valid correctly detects various page states."""

    def teardown_method(self):
        reset_douban_fetcher()

    def test_detects_no_access_page(self):
        """'没有访问权限' page means cookie is invalid — should return valid=False.

        The fetcher raises AntiCrawlBlock for '没有访问权限' pages.
        check_cookie_valid must catch it and return a friendly message,
        NOT the generic 'Cookie 验证失败: ...'.
        """
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_page_with_cookie.side_effect = AntiCrawlBlock(
            "没有访问权限: https://movie.douban.com/mine?status=collect"
        )

        with patch("app.services.metadata.get_douban_fetcher",
                    return_value=mock_fetcher):
            result = check_cookie_valid("bid=test; ll=108288")

        assert result["valid"] is False
        # Positive assertion: verify specific message mapping
        assert "无效" in result["message"]
        # Negative assertions: should NOT contain raw URL or generic error text
        assert "验证失败" not in result["message"]
        assert "movie.douban.com" not in result["message"]

    def test_detects_anticrawl_page_from_fetcher(self):
        """When fetcher raises AntiCrawlBlock for '检测到有异常请求',
        check_cookie_valid should return a friendly message.
        """
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_page_with_cookie.side_effect = AntiCrawlBlock(
            "豆瓣反爬封锁: https://movie.douban.com/mine?status=collect"
        )

        with patch("app.services.metadata.get_douban_fetcher",
                    return_value=mock_fetcher):
            result = check_cookie_valid("bid=test; ll=108288")

        assert result["valid"] is False
        assert "反爬" in result["message"]
        assert "验证失败" not in result["message"]

    def test_detects_pow_challenge_from_fetcher(self):
        """When fetcher raises AntiCrawlBlock for PoW challenge,
        check_cookie_valid should return a specific PoW message.
        """
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_page_with_cookie.side_effect = AntiCrawlBlock(
            "PoW 挑战页未解出: https://movie.douban.com/mine?status=collect"
        )

        with patch("app.services.metadata.get_douban_fetcher",
                    return_value=mock_fetcher):
            result = check_cookie_valid("bid=test; ll=108288")

        assert result["valid"] is False
        assert "反爬挑战" in result["message"]
        # PoW message "Cookie 验证失败：反爬挑战未通过" contains "验证失败",
        # so we check for "触发反爬机制" (the generic fallback) instead
        assert "触发反爬机制" not in result["message"]

    def test_detects_login_page(self):
        """Login page (with '登录' AND '注册') means cookie expired."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_page_with_cookie.return_value = (
            "<html><head><title>登录豆瓣</title></head>"
            "<body>登录 注册 <form>...</form></body></html>"
        )

        with patch("app.services.metadata.get_douban_fetcher",
                    return_value=mock_fetcher):
            result = check_cookie_valid("bid=test; ll=108288")

        assert result["valid"] is False
        assert "过期" in result["message"]

    def test_detects_login_redirect_page(self):
        """Login redirect page (title contains '登录跳转') means cookie expired.

        This catches the case where Douban returns a '登录跳转页' instead of
        a standard login page. The page may not contain both '登录' and '注册'.
        """
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_page_with_cookie.return_value = (
            "<html><head><title>豆瓣 - 登录跳转页</title></head>"
            "<body><div>需要登录</div></body></html>"
        )

        with patch("app.services.metadata.get_douban_fetcher",
                    return_value=mock_fetcher):
            result = check_cookie_valid("bid=test; ll=108288")

        assert result["valid"] is False
        assert "过期" in result["message"]

    def test_detects_login_page_by_title_only(self):
        """Login page detected when title contains '登录', even without '注册'."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_page_with_cookie.return_value = (
            "<html><head><title>请登录 - 豆瓣</title></head>"
            "<body>请登录后继续</body></html>"
        )

        with patch("app.services.metadata.get_douban_fetcher",
                    return_value=mock_fetcher):
            result = check_cookie_valid("bid=test; ll=108288")

        assert result["valid"] is False
        assert "过期" in result["message"]

    def test_detects_captcha_from_fetcher(self):
        """When fetcher raises AntiCrawlBlock for CAPTCHA,
        check_cookie_valid should return a CAPTCHA-specific message.
        """
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_page_with_cookie.side_effect = AntiCrawlBlock(
            "CAPTCHA page: https://movie.douban.com/mine?status=collect"
        )

        with patch("app.services.metadata.get_douban_fetcher",
                    return_value=mock_fetcher):
            result = check_cookie_valid("bid=test; ll=108288")

        assert result["valid"] is False
        assert "验证码" in result["message"]
        assert "验证失败" not in result["message"]

    def test_detects_rate_limit_from_fetcher(self):
        """When fetcher raises AntiCrawlBlock for HTTP 429/503,
        check_cookie_valid should return a rate-limit-specific message,
        NOT a cookie-invalid message. 429 means the IP is throttled,
        not that the cookie is bad.
        """
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_page_with_cookie.side_effect = AntiCrawlBlock(
            "HTTP 429 错误: https://movie.douban.com/mine?status=collect"
        )

        with patch("app.services.metadata.get_douban_fetcher",
                    return_value=mock_fetcher):
            result = check_cookie_valid("bid=test; ll=108288")

        assert result["valid"] is False
        assert "限流" in result["message"] or "频繁" in result["message"]
        # Should NOT say cookie is invalid — the cookie is fine, just rate-limited
        assert "无效" not in result["message"]
        assert "过期" not in result["message"]

    def test_unknown_anticrawl_returns_generic_message(self):
        """When fetcher raises AntiCrawlBlock with an unknown message,
        check_cookie_valid should return a generic message WITHOUT
        leaking the raw URL.
        """
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_page_with_cookie.side_effect = AntiCrawlBlock(
            "IP 被封禁: https://movie.douban.com/mine?status=collect"
        )

        with patch("app.services.metadata.get_douban_fetcher",
                    return_value=mock_fetcher):
            result = check_cookie_valid("bid=test; ll=108288")

        assert result["valid"] is False
        assert "反爬" in result["message"]
        # Fallback should NOT leak the raw URL
        assert "movie.douban.com" not in result["message"]

    def test_valid_cookie_returns_true(self):
        """A page with user's collection should return valid=True."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_page_with_cookie.return_value = (
            "<html><head><title>我的收藏</title></head>"
            "<body>我的电影列表 ...</body></html>"
        )

        with patch("app.services.metadata.get_douban_fetcher",
                    return_value=mock_fetcher):
            result = check_cookie_valid("bid=test; ll=108288")

        assert result["valid"] is True

    def test_exception_returns_false(self):
        """Any exception from the fetcher should return valid=False."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_page_with_cookie.side_effect = PageFetchTimeout("超时")

        with patch("app.services.metadata.get_douban_fetcher",
                    return_value=mock_fetcher):
            result = check_cookie_valid("bid=test; ll=108288")

        assert result["valid"] is False
        assert "验证失败" in result["message"]

    def test_exception_does_not_leak_url(self):
        """Exception catch-all should NOT leak internal URLs to the user.
        PageFetchTimeout messages contain URLs like
        'Playwright 获取失败: https://movie.douban.com/...'
        which should be stripped from the user-facing message.
        """
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_page_with_cookie.side_effect = PageFetchTimeout(
            "Playwright 获取失败: https://movie.douban.com/mine?status=collect"
        )

        with patch("app.services.metadata.get_douban_fetcher",
                    return_value=mock_fetcher):
            result = check_cookie_valid("bid=test; ll=108288")

        assert result["valid"] is False
        # Should NOT leak the raw URL
        assert "movie.douban.com" not in result["message"]
