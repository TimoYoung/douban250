"""Tests for metadata backfill service."""

import pytest
from datetime import datetime

from app.models.movie import Movie
from app.services.metadata import _needs_metadata_query, should_retry_now


class TestNeedsMetadataQuery:
    """Tests for _needs_metadata_query() SQLAlchemy filter."""

    def test_skips_non_numeric_douban_id(self, db_factory):
        """Movies with non-numeric douban_id (like 'blocked_vendetta')
        should NOT be selected by _needs_metadata_query()."""
        db = db_factory()
        # Create a movie with non-numeric douban_id
        m = Movie(
            douban_id="blocked_vendetta",
            title="V for Vendetta",
            # Missing required fields (director, genre, etc.)
        )
        db.add(m)
        db.commit()

        result = db.query(Movie).filter(_needs_metadata_query()).all()
        assert result == [], (
            f"Expected empty list but got {len(result)} movies. "
            "Non-numeric douban_id should be filtered out."
        )

    def test_selects_numeric_douban_id_with_missing_fields(self, db_factory):
        """Movies with numeric douban_id and missing fields SHOULD be selected."""
        db = db_factory()
        m = Movie(
            douban_id="1292052",
            title="肖申克的救赎",
            # Missing required fields
        )
        db.add(m)
        db.commit()

        result = db.query(Movie).filter(_needs_metadata_query()).all()
        assert len(result) == 1
        assert result[0].douban_id == "1292052"

    def test_skips_recently_fetched_movie(self, db_factory):
        """Movies successfully fetched within 30 days should NOT be selected."""
        db = db_factory()
        from app.utils import now
        m = Movie(
            douban_id="1292052",
            imdb_id="tt0111161",
            title="肖申克的救赎",
            director="弗兰克·德拉邦特",  # Has director
            genre="剧情",  # Has genre
            # But missing other fields (country, summary, etc.)
            detail_fetched=True,  # 已标记为成功获取
            last_meta_fetch=now(),  # 最近获取
        )
        db.add(m)
        db.commit()

        result = db.query(Movie).filter(_needs_metadata_query()).all()
        assert result == [], (
            "Movie fetched recently should not be selected even with missing fields."
        )

    def test_selects_old_fetched_movie_with_missing_fields(self, db_factory):
        """Movies fetched more than 30 days ago with missing fields SHOULD be selected."""
        db = db_factory()
        from app.utils import now
        from datetime import timedelta
        m = Movie(
            douban_id="1292052",
            imdb_id="tt0111161",
            title="肖申克的救赎",
            # Missing required fields
            last_meta_fetch=now() - timedelta(days=31),  # Fetched > 30 days ago
        )
        db.add(m)
        db.commit()

        result = db.query(Movie).filter(_needs_metadata_query()).all()
        assert len(result) == 1
        assert result[0].douban_id == "1292052"


class TestShouldRetryNowTimezone:
    """Verify _should_retry_now handles naive datetimes from SQLite correctly.

    Bug: SQLite stores datetimes without timezone info. When last_meta_attempt
    is loaded from DB, it's offset-naive. now() returns offset-aware (UTC+8).
    Comparing them raises TypeError.
    """

    def test_naive_last_meta_attempt_does_not_raise(self, db_factory):
        """_should_retry_now must not raise when last_meta_attempt is naive."""
        from datetime import datetime, timedelta
        from app.utils import now

        db = db_factory()
        # Create a movie with missing fields and a NAIVE last_meta_attempt
        # (simulating what SQLite returns)
        naive_dt = datetime(2026, 7, 1, 12, 0, 0)  # no tzinfo
        m = Movie(
            douban_id="9999999",
            title="Test Movie",
            last_meta_attempt=naive_dt,  # naive datetime from SQLite
            meta_fetch_failures=1,
        )
        db.add(m)
        db.commit()

        # Apply should_retry_now to the selected movies
        to_fetch = db.query(Movie).filter(_needs_metadata_query()).all()
        filtered = [m for m in to_fetch if should_retry_now(m)]

        # Should not raise TypeError
        assert isinstance(filtered, list)


class TestShouldRetryNowBackoff:
    """should_retry_now applies exponential backoff based on failure count.

    Bug: when meta_fetch_failures=0 but last_meta_attempt is recent
    (e.g., a 429 was silently swallowed by the old fetcher and counted
    as "success"), the 2^0=1h backoff blocks the movie for 1 hour.
    With 0 failures there should be NO backoff — the movie should be
    retried immediately.
    """

    def test_no_backoff_when_failures_zero(self, db_factory):
        """When meta_fetch_failures=0, should_retry_now returns True
        regardless of how recent last_meta_attempt is."""
        from app.utils import now

        db = db_factory()
        m = Movie(
            douban_id="9999999",
            title="Test Movie",
            last_meta_attempt=now(),  # just attempted
            meta_fetch_failures=0,    # no failures recorded
        )
        db.add(m)
        db.commit()

        assert should_retry_now(m) is True

    def test_backoff_applies_when_failures_positive(self, db_factory):
        """When meta_fetch_failures > 0 and not enough time elapsed,
        should_retry_now returns False."""
        from app.utils import now

        db = db_factory()
        m = Movie(
            douban_id="9999999",
            title="Test Movie",
            last_meta_attempt=now(),  # just attempted
            meta_fetch_failures=2,    # 2 failures → 4h backoff
        )
        db.add(m)
        db.commit()

        assert should_retry_now(m) is False


class TestParseDetailPageRejectsHttpErrors:
    """parse_detail_page must NOT extract titles from HTTP error pages.

    Bug: when Douban returns 429, the HTML <title> is "429 Too Many Requests".
    parse_detail_page extracted it as the movie title → data corruption.
    """

    def test_rejects_429_title(self):
        from app.services.metadata import parse_detail_page
        html = "<html><head><title>429 Too Many Requests</title></head><body></body></html>"
        info = parse_detail_page(html)
        assert info.get("title") != "429 Too Many Requests"
        assert not info.get("title", "").startswith("429")

    def test_rejects_503_title(self):
        from app.services.metadata import parse_detail_page
        html = "<html><head><title>503 Service Unavailable</title></head><body></body></html>"
        info = parse_detail_page(html)
        assert not info.get("title", "").startswith("503")

    def test_rejects_502_title(self):
        from app.services.metadata import parse_detail_page
        html = "<html><head><title>502 Bad Gateway</title></head><body></body></html>"
        info = parse_detail_page(html)
        assert not info.get("title", "").startswith("502")

    def test_accepts_normal_chinese_title(self):
        from app.services.metadata import parse_detail_page
        html = '<html><head><title>肖申克的救赎 (豆瓣)</title></head><body></body></html>'
        info = parse_detail_page(html)
        assert info.get("title") == "肖申克的救赎"

    def test_accepts_title_starting_with_number(self):
        """Titles like '1917' or '2001太空漫游' must NOT be rejected.
        Only HTTP error pattern (3 digits + space + word) should be rejected.
        """
        from app.services.metadata import parse_detail_page
        html = '<html><head><title>2001太空漫游 (豆瓣)</title></head><body></body></html>'
        info = parse_detail_page(html)
        assert info.get("title") == "2001太空漫游"

    def test_accepts_title_1917(self):
        """'1917' is a valid movie title — just digits, no space+word."""
        from app.services.metadata import parse_detail_page
        html = '<html><head><title>1917 (豆瓣)</title></head><body></body></html>'
        info = parse_detail_page(html)
        assert info.get("title") == "1917"
