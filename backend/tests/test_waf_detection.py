"""Tests for sec.douban.com WAF detection in http_client."""

import pytest
from unittest.mock import patch, MagicMock
import httpx

from app.utils.http_client import fetch_page, fetch_binary


class TestWAFDetection:
    """Verify sec.douban.com WAF redirect detection in both fetch_page and fetch_binary."""

    def _make_mock_response(self, final_url, history_urls):
        """Create a mock httpx response with redirect history."""
        mock_resp = MagicMock()
        mock_resp.url = httpx.URL(final_url)
        mock_resp.history = [MagicMock(url=httpx.URL(u)) for u in history_urls]
        mock_resp.status_code = 403
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "403 Forbidden",
            request=MagicMock(),
            response=mock_resp
        )
        return mock_resp

    @patch("app.utils.http_client.httpx.Client")
    def test_fetch_page_detects_waf_in_redirect_history(self, mock_client_cls):
        """fetch_page should detect sec.douban.com in redirect history."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        # 302 movie.douban.com → sec.douban.com → 403 sec.douban.com/b
        # history contains the intermediate sec.douban.com redirect
        mock_client.get.return_value = self._make_mock_response(
            "https://sec.douban.com/b",
            ["https://movie.douban.com/top250", "https://sec.douban.com/b?r=..."]
        )
        mock_client_cls.return_value = mock_client

        with pytest.raises(RuntimeError, match="sec.douban.com"):
            fetch_page("https://movie.douban.com/top250")

    @patch("app.utils.http_client.httpx.Client")
    def test_fetch_page_detects_waf_in_final_url(self, mock_client_cls):
        """fetch_page should detect sec.douban.com as final URL."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = self._make_mock_response(
            "https://sec.douban.com/blocked",
            []
        )
        mock_client_cls.return_value = mock_client

        with pytest.raises(RuntimeError, match="sec.douban.com"):
            fetch_page("https://movie.douban.com/top250")

    @patch("app.utils.http_client.httpx.Client")
    def test_fetch_binary_detects_waf_in_redirect_history(self, mock_client_cls):
        """fetch_binary should detect sec.douban.com in redirect history."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = self._make_mock_response(
            "https://sec.douban.com/b",
            ["https://img.doubanio.com/poster.jpg", "https://sec.douban.com/b?r=..."]
        )
        mock_client_cls.return_value = mock_client

        with pytest.raises(RuntimeError, match="sec.douban.com"):
            fetch_binary("https://img.doubanio.com/poster.jpg")

    @patch("app.utils.http_client.httpx.Client")
    def test_fetch_binary_detects_waf_in_final_url(self, mock_client_cls):
        """fetch_binary should detect sec.douban.com as final URL."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = self._make_mock_response(
            "https://sec.douban.com/blocked",
            []
        )
        mock_client_cls.return_value = mock_client

        with pytest.raises(RuntimeError, match="sec.douban.com"):
            fetch_binary("https://img.doubanio.com/poster.jpg")

    @patch("app.utils.http_client.httpx.Client")
    def test_fetch_page_no_waf_detection_for_normal_redirect(self, mock_client_cls):
        """fetch_page should NOT detect WAF for normal redirects."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_resp = MagicMock()
        mock_resp.url = httpx.URL("https://movie.douban.com/top250")
        mock_resp.history = [MagicMock(url=httpx.URL("https://movie.douban.com/top250/"))]
        mock_resp.status_code = 200
        mock_resp.text = "<html>电影 content</html>"
        mock_resp.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        # Should not raise
        result = fetch_page("https://movie.douban.com/top250/")
        assert result == "<html>电影 content</html>"
