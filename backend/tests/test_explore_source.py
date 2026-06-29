"""Tests for the source filter feature on the explore endpoint."""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import get_db
from app.models.movie import Movie, Version, VersionEntry


@pytest.fixture
def db_session(db_factory):
    """Provide a transactional database session for each test."""
    session = db_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    """FastAPI test client with overridden database dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


NOW = datetime.now(timezone.utc)


def _seed_source_data(db: Session):
    """Create test movies, versions, and entries for source filtering."""
    # 3 movies: one douban-only, one imdb-only, one in both
    m1 = Movie(id=1, douban_id="1001", title="豆瓣独占", detail_fetched=True, rating=9.0)
    m2 = Movie(id=2, imdb_id="tt002", title="IMDb独占", detail_fetched=True, rating=8.5)
    m3 = Movie(id=3, douban_id="1003", imdb_id="tt003", title="两者都有", detail_fetched=True, rating=9.5)
    db.add_all([m1, m2, m3])

    v_douban = Version(id=1, tag="2024-01", source="douban", crawled_at=NOW, movie_count=250)
    v_imdb = Version(id=2, tag="2024-01", source="imdb", crawled_at=NOW, movie_count=250)
    db.add_all([v_douban, v_imdb])

    # m1 in douban only, m2 in imdb only, m3 in both
    db.add_all([
        VersionEntry(version_id=1, movie_id=1, rank=1, rating=9.0),
        VersionEntry(version_id=2, movie_id=2, rank=1, rating=8.5),
        VersionEntry(version_id=1, movie_id=3, rank=2, rating=9.5),
        VersionEntry(version_id=2, movie_id=3, rank=2, rating=9.5),
    ])
    db.commit()


class TestExploreSourceFilter:
    """Test source filtering on the explore endpoint."""

    def test_source_all_returns_all_movies(self, client, db_session):
        """source=all 应返回所有 detail_fetched 的电影（含不在任何版本中的）"""
        _seed_source_data(db_session)

        resp = client.get("/api/movies/explore", params={"source": "all"})
        assert resp.status_code == 200
        data = resp.json()
        titles = {m["title"] for m in data["items"]}
        assert titles == {"豆瓣独占", "IMDb独占", "两者都有"}

    def test_source_douban_returns_only_douban_movies(self, client, db_session):
        """source=douban 应只返回出现在豆瓣版本中的电影"""
        _seed_source_data(db_session)

        resp = client.get("/api/movies/explore", params={"source": "douban"})
        assert resp.status_code == 200
        data = resp.json()
        titles = {m["title"] for m in data["items"]}
        assert titles == {"豆瓣独占", "两者都有"}

    def test_source_imdb_returns_only_imdb_movies(self, client, db_session):
        """source=imdb 应只返回出现在 IMDb 版本中的电影"""
        _seed_source_data(db_session)

        resp = client.get("/api/movies/explore", params={"source": "imdb"})
        assert resp.status_code == 200
        data = resp.json()
        titles = {m["title"] for m in data["items"]}
        assert titles == {"IMDb独占", "两者都有"}

    def test_explore_filters_includes_sources(self, client, db_session):
        """explore/filters 应返回可用的来源列表"""
        _seed_source_data(db_session)

        resp = client.get("/api/movies/explore/filters")
        assert resp.status_code == 200
        data = resp.json()
        assert "sources" in data
        assert set(data["sources"]) == {"douban", "imdb"}
