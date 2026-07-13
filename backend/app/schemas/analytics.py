from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas import BeijingBaseModel


# ── Dashboard V2 ──


class KpiChanges(BaseModel):
    """KPI 专用: latest vs 上一版本的变动计数"""
    added: int = 0
    removed: int = 0


class LatestChanges(BaseModel):
    """某源最新 vs 上一个有电影进出的版本的变动摘要"""
    added: int = 0
    removed: int = 0
    avg_rating_delta: float = 0.0
    # 变动涉及的具体电影
    added_movies: list[dict] = []   # [{movie_id, douban_id, title, poster_path, rank}]
    removed_movies: list[dict] = []
    risers_top10: list[dict] = []   # [{movie_id, douban_id, title, poster_path, rank_change, current_rank}]
    fallers_top10: list[dict] = []


class SourceDetail(BeijingBaseModel):
    latest_tag: Optional[str] = None
    latest_crawled_at: Optional[datetime] = None
    latest_version_id: Optional[int] = None
    next_fire_time: Optional[datetime] = None          # 下次计划爬取时间 (from APScheduler)
    prev_tag: Optional[str] = None                      # 上一版本 tag
    prev_version_id: Optional[int] = None
    prev_changed_tag: Optional[str] = None              # 上一个有电影进出的版本 tag (变动卡片用)
    prev_changed_version_id: Optional[int] = None
    version_count: int = 0
    kpi_changes: KpiChanges = KpiChanges()              # KPI: latest vs prev_ver
    changes: LatestChanges = LatestChanges()            # 变动卡片: latest vs prev_changed


class DashboardSummaryV2(BeijingBaseModel):
    douban: SourceDetail = SourceDetail()
    imdb: SourceDetail = SourceDetail()
    total_movies: int = 0


# ── Cross-Platform (保留给 Dashboard Venn 区使用) ──


class OverlapData(BeijingBaseModel):
    only_douban: int = 0
    only_imdb: int = 0
    both: int = 0


class MovieBrief(BeijingBaseModel):
    """简化电影信息，用于列表展示"""
    movie_id: int
    douban_id: Optional[str] = None
    title: str
    poster_path: Optional[str] = None
    rank: Optional[int] = None


class UniqueMoviesReport(BeijingBaseModel):
    only_douban: list[MovieBrief] = []
    only_imdb: list[MovieBrief] = []


# ── Distribution ──


class DistributionData(BeijingBaseModel):
    genres: dict[str, int] = {}
    countries: dict[str, int] = {}
    years: dict[str, int] = {}
    source: str = "douban"
    tag: Optional[str] = None


class CompareDistribution(BeijingBaseModel):
    douban: DistributionData = DistributionData()
    imdb: DistributionData = DistributionData()
    all_labels: dict[str, list[str]] = {}   # {"genres": [...], "countries": [...], "years": [...]}


# ── Timeline Snapshot ──


class SnapshotEntry(BeijingBaseModel):
    movie_id: int
    douban_id: Optional[str] = None
    title: str
    poster_path: Optional[str] = None
    rank: int = 0
    rating: Optional[float] = None


class TimelineSnapshot(BeijingBaseModel):
    tag: str = ""
    source: str = ""
    movies: list[SnapshotEntry] = []


# ── Version Tags ──


class VersionTagInfo(BeijingBaseModel):
    id: int
    tag: str
    movie_count: int = 0
    crawled_at: datetime
