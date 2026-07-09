"""Tests for RetryManager retry execution."""

from unittest.mock import patch, MagicMock

import pytest

from app.services.retry_manager import RetryManager, RetryState


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
             patch("app.services.retry_manager.RetryManager._save_retry_state_to_db"), \
             patch("app.services.imdb_crawler.crawl_imdb_top250") as mock_crawl, \
             patch.object(retry_mgr, "schedule_retry",
                          wraps=retry_mgr.schedule_retry) as mock_schedule:
            mock_crawl.return_value = {"status": "error", "message": "网络超时"}

            retry_mgr._execute_retry("imdb")

            assert mock_schedule.call_count == 1, (
                f"schedule_retry called {mock_schedule.call_count} times, expected 1")


class TestRetryStateFixes:
    """Tests for the EXHAUSTED state deadlock fix."""

    @pytest.fixture
    def retry_mgr(self):
        scheduler = MagicMock()
        return RetryManager(scheduler)

    def test_default_state_is_idle(self, retry_mgr):
        """_default_retry_state() should return IDLE, not EXHAUSTED."""
        state = retry_mgr._default_retry_state()
        assert state["status"] == RetryState.IDLE
        assert state["retry_count"] == 0

    def test_cancel_retry_clears_exhausted(self, retry_mgr):
        """cancel_retry() should clear EXHAUSTED state (fix deadlock)."""
        # Simulate the stuck EXHAUSTED state
        retry_mgr._retry_states["imdb"] = {
            "status": RetryState.EXHAUSTED,
            "retry_count": 3,
            "next_retry": None,
            "last_error": "some error",
            "crawl_log_id": None,
        }

        with patch.object(retry_mgr, "_save_retry_state_to_db"):
            result = retry_mgr.cancel_retry("imdb")

        assert result is True
        assert retry_mgr._retry_states["imdb"]["status"] == RetryState.IDLE

    def test_cancel_retry_clears_failed(self, retry_mgr):
        """cancel_retry() should also clear FAILED state."""
        retry_mgr._retry_states["top250"] = {
            "status": RetryState.FAILED,
            "retry_count": 1,
            "next_retry": None,
            "last_error": "scheduler add_job failed",
            "crawl_log_id": None,
        }

        with patch.object(retry_mgr, "_save_retry_state_to_db"):
            result = retry_mgr.cancel_retry("top250")

        assert result is True
        assert retry_mgr._retry_states["top250"]["status"] == RetryState.IDLE

    def test_cancel_retry_clears_cancelled(self, retry_mgr):
        """cancel_retry() should clear stale CANCELLED state from old Setting rows."""
        retry_mgr._retry_states["imdb"] = {
            "status": RetryState.CANCELLED,
            "retry_count": 0,
            "next_retry": None,
            "last_error": None,
            "crawl_log_id": None,
        }

        with patch.object(retry_mgr, "_save_retry_state_to_db"):
            result = retry_mgr.cancel_retry("imdb")

        assert result is True
        assert retry_mgr._retry_states["imdb"]["status"] == RetryState.IDLE

    def test_cancel_retry_idle_returns_false(self, retry_mgr):
        """cancel_retry() on IDLE state should return False (nothing to cancel)."""
        # IDLE is the default, so no state set means IDLE
        result = retry_mgr.cancel_retry("imdb")
        assert result is False

    def test_save_retry_state_to_db_persists(self, retry_mgr):
        """_save_retry_state_to_db() should write to Setting table."""
        state = {
            "status": RetryState.PENDING,
            "retry_count": 2,
            "next_retry": None,
            "last_error": "test error",
            "crawl_log_id": 42,
        }

        mock_db = MagicMock()
        # first() returns None → code creates new Setting
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("app.services.retry_manager.SessionLocal", return_value=mock_db):
            retry_mgr._save_retry_state_to_db("imdb", state)

        # Verify it wrote to the Setting table
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_clear_retry_state_persists_idle(self, retry_mgr):
        """_clear_retry_state() should persist IDLE to Setting table, not just delete from memory.

        This is the regression test for the stale-state bug: after a successful retry,
        _clear_retry_state deleted from memory but left the old PENDING/EXHAUSTED row
        in Setting table. On restart, _load_retry_state_from_db loaded the stale row.
        """
        # Simulate a PENDING state in memory AND in Setting table
        retry_mgr._retry_states["imdb"] = {
            "status": RetryState.PENDING,
            "retry_count": 2,
            "next_retry": None,
            "last_error": "network timeout",
            "crawl_log_id": 42,
        }

        saved_states = []

        def capture_save(job_type, state):
            saved_states.append((job_type, dict(state)))

        with patch.object(retry_mgr, "_save_retry_state_to_db", side_effect=capture_save):
            retry_mgr._clear_retry_state("imdb")

        # Verify it persisted IDLE (not just deleted from memory)
        assert len(saved_states) == 1
        job_type, state = saved_states[0]
        assert job_type == "imdb"
        assert state["status"] == RetryState.IDLE

    def test_cancel_all_retries_does_not_deadlock(self, retry_mgr):
        """cancel_all_retries() must not deadlock when it holds _lock and
        calls cancel_retry() which also acquires _lock.

        Regression: threading.Lock is non-reentrant, so calling cancel_retry
        from within cancel_all_retries (which holds the lock) caused a
        permanent deadlock.
        """
        import threading

        # Set up multiple job types with stale states
        for job_type, status in [("imdb", RetryState.EXHAUSTED),
                                  ("top250", RetryState.PENDING)]:
            retry_mgr._retry_states[job_type] = {
                "status": status,
                "retry_count": 1,
                "next_retry": None,
                "last_error": "test",
                "crawl_log_id": None,
            }

        result = [None]
        error = [None]

        def run():
            try:
                with patch.object(retry_mgr, "_save_retry_state_to_db"):
                    retry_mgr.cancel_all_retries()
                result[0] = True
            except Exception as e:
                error[0] = e

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        thread.join(timeout=3.0)  # 3 秒超时——死锁的话线程不会结束

        assert not thread.is_alive(), "cancel_all_retries() deadlocked!"
        assert result[0] is True, f"Error: {error[0]}"
        # 验证所有状态都重置为 IDLE
        for job_type in retry_mgr._retry_states:
            assert retry_mgr._retry_states[job_type]["status"] == RetryState.IDLE
