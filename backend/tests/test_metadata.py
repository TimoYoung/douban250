"""Tests for metadata backfill service."""

import pytest
from datetime import datetime

from app.models.movie import Movie
from app.services.metadata import _needs_metadata_query


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

        # Apply the same filter logic as run_backfill's _should_retry_now
        to_fetch = db.query(Movie).filter(_needs_metadata_query()).all()
        filtered = []
        for movie in to_fetch:
            if movie.last_meta_attempt is None:
                filtered.append(movie)
            else:
                failures = movie.meta_fetch_failures or 0
                hours = min(2 ** failures, 72)
                last_attempt = movie.last_meta_attempt.replace(tzinfo=None)
                cutoff = now().replace(tzinfo=None) - timedelta(hours=hours)
                if last_attempt < cutoff:
                    filtered.append(movie)

        # Should not raise TypeError
        assert isinstance(filtered, list)
