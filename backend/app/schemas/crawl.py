from datetime import datetime
from typing import Optional

from app.schemas import BeijingBaseModel


class CrawlLogInfo(BeijingBaseModel):
    id: int
    job_type: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    new_version_created: bool = False
    error_message: Optional[str] = None
    movies_found: Optional[int] = None


class CrawlTriggerResponse(BeijingBaseModel):
    message: str
    triggered: bool


class DoulistImportRequest(BeijingBaseModel):
    url: str
    tag: str
