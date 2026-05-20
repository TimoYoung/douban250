from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils import now


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    douban_id = Column(String(20), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    original_title = Column(String(500))
    year = Column(Integer)
    country = Column(String(200))
    genre = Column(String(200))
    director = Column(String(500))
    cast_members = Column(JSON)  # list of names
    rating = Column(Float)
    rating_count = Column(Integer)
    tagline = Column(Text)
    summary = Column(Text)
    poster_path = Column(String(500))
    douban_url = Column(String(500))
    detail_fetched = Column(Boolean, default=False)  # True if detail page was successfully parsed
    created_at = Column(DateTime(timezone=True), default=now)
    updated_at = Column(DateTime(timezone=True), default=now, onupdate=now)

    version_entries = relationship("VersionEntry", back_populates="movie")


class Version(Base):
    __tablename__ = "versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tag = Column(String(20), unique=True, nullable=False)
    crawled_at = Column(DateTime(timezone=True), nullable=False)
    movie_count = Column(Integer, nullable=False, default=250)

    entries = relationship("VersionEntry", back_populates="version", order_by="VersionEntry.rank")


class VersionEntry(Base):
    __tablename__ = "version_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version_id = Column(Integer, ForeignKey("versions.id"), nullable=False, index=True)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False, index=True)
    rank = Column(Integer, nullable=False)
    rating = Column(Float)

    __table_args__ = (
        UniqueConstraint("version_id", "movie_id"),
        UniqueConstraint("version_id", "rank"),
    )

    version = relationship("Version", back_populates="entries")
    movie = relationship("Movie", back_populates="version_entries")


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text)
    updated_at = Column(DateTime(timezone=True), default=now, onupdate=now)
