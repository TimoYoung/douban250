from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils import now


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    douban_id = Column(String(20), unique=True, nullable=True, index=True)
    imdb_id = Column(String(20), unique=True, nullable=True, index=True)
    title = Column(String(500), nullable=False)
    original_title = Column(String(500))
    year = Column(Integer)
    country = Column(String(200))
    genre = Column(String(200))
    director = Column(String(500))
    cast_members = Column(JSON)  # list of names
    duration = Column(Integer, nullable=True)  # 电影时长（分钟）
    rating = Column(Float)
    rating_count = Column(Integer)
    tagline = Column(Text)
    summary = Column(Text)
    poster_path = Column(String(500))
    douban_url = Column(String(500))
    detail_fetched = Column(Boolean, default=False)  # True if detail page was successfully parsed
    last_meta_fetch = Column(DateTime(timezone=True), nullable=True)  # 上次成功获取元数据的时间
    created_at = Column(DateTime(timezone=True), default=now)
    updated_at = Column(DateTime(timezone=True), default=now, onupdate=now)

    version_entries = relationship("VersionEntry", back_populates="movie")


class Version(Base):
    __tablename__ = "versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tag = Column(String(20), nullable=False)
    source = Column(String(20), nullable=False, default='douban')
    # confirmed = 正常版本, pending_confirmation = 待确认匹配
    status = Column(String(30), nullable=False, default='confirmed')
    crawled_at = Column(DateTime(timezone=True), nullable=False)
    movie_count = Column(Integer, nullable=False, default=250)

    __table_args__ = (
        UniqueConstraint("tag", "source"),
    )

    entries = relationship("VersionEntry", back_populates="version", order_by="VersionEntry.rank", cascade="all, delete-orphan")


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


class PendingMatch(Base):
    """待确认的 IMDb 电影匹配记录"""
    __tablename__ = "pending_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version_id = Column(Integer, ForeignKey("versions.id"), nullable=True, index=True)
    imdb_id = Column(String(20), nullable=False, index=True)
    imdb_title = Column(String(500), nullable=False)
    year = Column(Integer)
    rank = Column(Integer)  # IMDb 榜单排名
    # 候选列表: [{douban_id, title, year, rating, poster_url, imdb_id_from_detail}, ...]
    candidates = Column(JSON, nullable=True)
    # pending / confirmed / rejected
    status = Column(String(20), nullable=False, default='pending')
    # 用户确认后的结果
    resolved_douban_id = Column(String(20), nullable=True)  # 用户手动输入或接受的 douban_id
    resolved_movie_id = Column(Integer, ForeignKey("movies.id"), nullable=True)  # 最终关联的 movie.id
    created_at = Column(DateTime(timezone=True), default=now)
    updated_at = Column(DateTime(timezone=True), default=now, onupdate=now)

    version = relationship("Version")
    resolved_movie = relationship("Movie", foreign_keys=[resolved_movie_id])


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text)
    updated_at = Column(DateTime(timezone=True), default=now, onupdate=now)
