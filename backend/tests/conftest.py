"""Shared test fixtures for douban250 backend tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base


@pytest.fixture
def db_factory(tmp_path):
    """Create an in-memory SQLite database factory for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    return TestSession
