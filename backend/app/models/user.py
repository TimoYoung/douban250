from sqlalchemy import Column, Integer, String, Boolean, Date, Text, DateTime, UniqueConstraint

from app.database import Base
from app.utils import now


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(200), nullable=False)
    role = Column(String(20), nullable=False, default="user")  # "user" or "admin"
    douban_user_id = Column(String(20), nullable=True)
    douban_cookie = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=now)
    updated_at = Column(DateTime(timezone=True), default=now, onupdate=now)


class WatchedMovie(Base):
    __tablename__ = "watched_movies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    douban_user_id = Column(String(20), nullable=False, index=True)
    douban_movie_id = Column(String(20), nullable=False)
    watched_date = Column(Date)
    user_comment = Column(Text)
    scraped_at = Column(DateTime(timezone=True), default=now)

    __table_args__ = (
        UniqueConstraint("douban_user_id", "douban_movie_id"),
    )
