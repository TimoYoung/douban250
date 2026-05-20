from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey

from app.database import Base


class CrawlLog(Base):
    __tablename__ = "crawl_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_type = Column(String(20), nullable=False)  # "top250" or "user_watched"
    status = Column(String(20), nullable=False)  # "running", "success", "failed"
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime)
    version_id = Column(Integer, ForeignKey("versions.id"), nullable=True)
    new_version_created = Column(Boolean, default=False)
    error_message = Column(Text)
    movies_found = Column(Integer)
