"""Tests for IMDb crawler fallback extraction."""

from unittest.mock import patch, MagicMock
import json

import pytest

from app.services.imdb_crawler import fetch_imdb_top250


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
