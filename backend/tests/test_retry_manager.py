"""Tests for RetryManager retry execution."""

from unittest.mock import patch, MagicMock

import pytest

from app.services.retry_manager import RetryManager


class TestExecuteRetry:
    """Tests for RetryManager._execute_retry dispatching."""

    @pytest.fixture
    def retry_mgr(self):
        scheduler = MagicMock()
        return RetryManager(scheduler)

    def test_imdb_retry_passes_db_factory(self, retry_mgr):
        """_execute_retry('imdb') should call crawl_imdb_top250 with db_factory."""
        with patch("app.services.retry_manager.SessionLocal") as mock_sl, \
             patch("app.services.imdb_crawler.crawl_imdb_top250") as mock_crawl:
            mock_crawl.return_value = {"status": "done"}

            retry_mgr._execute_retry("imdb")

            mock_crawl.assert_called_once_with(mock_sl)

    def test_top250_retry_calls_without_args(self, retry_mgr):
        """_execute_retry('top250') should call crawl_top250 with no arguments."""
        with patch("app.services.crawler.crawl_top250") as mock_crawl:
            mock_crawl.return_value = {"status": "done"}

            retry_mgr._execute_retry("top250")

            mock_crawl.assert_called_once_with()

    def test_imdb_retry_does_not_clear_state_on_soft_failure(self, retry_mgr):
        """When crawl_imdb_top250 returns error status without throwing,
        _execute_retry should NOT clear the retry state."""
        with patch("app.services.retry_manager.SessionLocal"), \
             patch("app.services.imdb_crawler.crawl_imdb_top250") as mock_crawl, \
             patch.object(retry_mgr, "schedule_retry") as mock_schedule:
            mock_crawl.return_value = {"status": "error", "message": "网络超时"}

            retry_mgr._execute_retry("imdb")

            mock_schedule.assert_called_once()

    def test_imdb_retry_schedules_exactly_once_on_failure(self, retry_mgr):
        """When crawl_imdb_top250 returns error, schedule_retry should be
        called exactly once (by _handle_retry_result, not by crawl itself)."""
        with patch("app.services.retry_manager.SessionLocal"), \
             patch("app.services.imdb_crawler.crawl_imdb_top250") as mock_crawl, \
             patch.object(retry_mgr, "schedule_retry",
                          wraps=retry_mgr.schedule_retry) as mock_schedule:
            mock_crawl.return_value = {"status": "error", "message": "网络超时"}

            retry_mgr._execute_retry("imdb")

            assert mock_schedule.call_count == 1, (
                f"schedule_retry called {mock_schedule.call_count} times, expected 1")
