"""Tests for scheduler retry behavior after crawl failure."""

from unittest.mock import patch, MagicMock

import pytest

from app.services.scheduler import _run_imdb, _run_top250


class TestRunImdbRetry:
    """Tests that _run_imdb schedules retry when crawl fails."""

    def test_schedules_retry_on_crawl_error(self):
        """When crawl_imdb_top250 returns error status,
        _run_imdb should schedule a retry."""
        mock_retry_mgr = MagicMock()
        mock_retry_mgr.has_pending_retry.return_value = False

        with patch("app.services.retry_manager.get_retry_manager",
                   return_value=mock_retry_mgr), \
             patch("app.services.imdb_crawler.get_imdb_progress",
                   return_value={"status": "idle"}), \
             patch("app.services.crawler.crawl_progress",
                   {"active": False}), \
             patch("app.services.imdb_crawler.crawl_imdb_top250") as mock_crawl:
            mock_crawl.return_value = {"status": "error", "message": "网络超时"}

            _run_imdb()

            mock_retry_mgr.schedule_retry.assert_called_once_with(
                "imdb", "网络超时")


    def test_handles_get_retry_manager_failure(self):
        """When get_retry_manager() fails, _run_imdb should not crash
        with UnboundLocalError — the crawl should complete normally."""
        with patch("app.services.retry_manager.get_retry_manager",
                   side_effect=RuntimeError("db locked")), \
             patch("app.services.imdb_crawler.get_imdb_progress",
                   return_value={"status": "idle"}), \
             patch("app.services.crawler.crawl_progress",
                   {"active": False}), \
             patch("app.services.imdb_crawler.crawl_imdb_top250") as mock_crawl:
            mock_crawl.return_value = {"status": "error", "message": "网络超时"}

            # Should not raise any exception
            _run_imdb()


class TestRunTop250Retry:
    """Tests that _run_top250 schedules retry when crawl fails."""

    def test_schedules_retry_on_crawl_failure(self):
        """When crawl_top250 raises an exception,
        _run_top250 should schedule a retry."""
        mock_retry_mgr = MagicMock()
        mock_retry_mgr.has_pending_retry.return_value = False

        with patch("app.services.retry_manager.get_retry_manager",
                   return_value=mock_retry_mgr), \
             patch("app.services.crawler.crawl_progress",
                   {"active": False}), \
             patch("app.services.crawler.crawl_top250") as mock_crawl:
            mock_crawl.side_effect = RuntimeError("network error")

            _run_top250()

            mock_retry_mgr.schedule_retry.assert_called_once()
