"""Shared test fixtures for douban250 backend tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base


@pytest.fixture
def db_factory():
    """Create an in-memory SQLite database factory for testing.

    Uses StaticPool to share a single connection across threads
    (required because FastAPI TestClient runs requests in a separate thread).
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    return TestSession
