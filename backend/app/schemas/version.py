from datetime import datetime

from app.schemas import BeijingBaseModel


class VersionInfo(BeijingBaseModel):
    id: int
    tag: str
    source: str = 'douban'
    status: str = 'confirmed'
    crawled_at: datetime
    movie_count: int


class VersionUpdate(BeijingBaseModel):
    tag: str
