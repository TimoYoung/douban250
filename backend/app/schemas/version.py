from datetime import datetime
from typing import Optional

from app.schemas import BeijingBaseModel


class VersionInfo(BeijingBaseModel):
    id: int
    tag: str
    crawled_at: datetime
    movie_count: int


class VersionUpdate(BeijingBaseModel):
    tag: str


class RankChange(BeijingBaseModel):
    douban_id: str
    title: str
    old_rank: int
    new_rank: int
    delta: int


class MovieInDiff(BeijingBaseModel):
    douban_id: str
    title: str
    rank: int
    rating: Optional[float] = None
    poster_path: Optional[str] = None


class VersionDiff(BeijingBaseModel):
    version_a: VersionInfo
    version_b: VersionInfo
    added: list[MovieInDiff]
    removed: list[MovieInDiff]
    rank_up: list[RankChange]
    rank_down: list[RankChange]
