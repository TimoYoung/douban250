from datetime import datetime
from typing import Optional

from app.schemas import BeijingBaseModel


class MovieBase(BeijingBaseModel):
    douban_id: Optional[str] = None
    imdb_id: Optional[str] = None
    title: str
    original_title: Optional[str] = None
    year: Optional[int] = None
    country: Optional[str] = None
    genre: Optional[str] = None
    director: Optional[str] = None
    cast_members: Optional[list[str]] = None
    duration: Optional[int] = None
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    tagline: Optional[str] = None
    summary: Optional[str] = None
    poster_path: Optional[str] = None
    douban_url: Optional[str] = None


class MovieListItem(BeijingBaseModel):
    id: int
    douban_id: Optional[str] = None
    imdb_id: Optional[str] = None
    title: str
    year: Optional[int] = None
    rating: Optional[float] = None
    poster_path: Optional[str] = None
    rank: Optional[int] = None
    watched: bool = False
    director: Optional[str] = None
    genre: Optional[str] = None
    duration: Optional[int] = None
    rank_change: Optional[int] = None  # None=new, >0=up, <0=down, 0=same


class CurrentRank(BeijingBaseModel):
    """某平台的最新排名"""
    source: str  # 'douban' or 'imdb'
    tag: str     # 版本日期
    rank: int


class MovieDetail(MovieBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    rank_history: list[dict] = []
    current_ranks: list[CurrentRank] = []
    watched: bool = False


class MovieBubble(BeijingBaseModel):
    douban_id: Optional[str] = None
    imdb_id: Optional[str] = None
    title: str
    rank: int
    watched: bool = False


class PaginatedMovies(BeijingBaseModel):
    items: list[MovieListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class GlobalSearchResult(BeijingBaseModel):
    movie_id: int
    douban_id: Optional[str] = None
    imdb_id: Optional[str] = None
    title: str
    year: Optional[int] = None
    poster_path: Optional[str] = None
    latest_version_id: int
    latest_version_tag: str
    rank: int
    source: str = 'douban'


class ExploreFilters(BeijingBaseModel):
    """探索页面可用的筛选维度"""
    genres: list[str]
    countries: list[str]
    year_min: int
    year_max: int
    rating_min: float
    rating_max: float
    duration_min: int
    duration_max: int
    sources: list[str] = []
