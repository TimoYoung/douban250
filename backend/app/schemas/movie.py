from datetime import datetime
from typing import Optional

from app.schemas import BeijingBaseModel


class MovieBase(BeijingBaseModel):
    douban_id: str
    title: str
    original_title: Optional[str] = None
    year: Optional[int] = None
    country: Optional[str] = None
    genre: Optional[str] = None
    director: Optional[str] = None
    cast_members: Optional[list[str]] = None
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    tagline: Optional[str] = None
    summary: Optional[str] = None
    poster_path: Optional[str] = None
    douban_url: Optional[str] = None


class MovieListItem(BeijingBaseModel):
    id: int
    douban_id: str
    title: str
    year: Optional[int] = None
    rating: Optional[float] = None
    poster_path: Optional[str] = None
    rank: Optional[int] = None
    watched: bool = False
    director: Optional[str] = None
    genre: Optional[str] = None
    rank_change: Optional[int] = None  # None=new, >0=up, <0=down, 0=same


class MovieDetail(MovieBase):
    id: int
    created_at: datetime
    updated_at: datetime
    rank_history: list[dict] = []
    current_rank: Optional[int] = None
    watched: bool = False


class MovieBubble(BeijingBaseModel):
    douban_id: str
    title: str
    rank: int
    watched: bool = False


class PaginatedMovies(BeijingBaseModel):
    items: list[MovieListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
