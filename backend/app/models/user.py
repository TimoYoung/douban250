from sqlalchemy import Column, Integer, String, Date, Text, DateTime, UniqueConstraint

from app.database import Base
from app.utils import now


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
