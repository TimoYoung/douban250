from typing import Optional
from pydantic import BaseModel


class PendingMatchCandidate(BaseModel):
    """单条候选匹配"""
    douban_id: str
    title: str
    year: Optional[int] = None
    rating: Optional[float] = None
    poster_url: Optional[str] = None
    imdb_id_from_detail: Optional[str] = None  # 从豆瓣详情页拿到的 imdb_id


class PendingMatchVersion(BaseModel):
    """待匹配电影在某个版本中的信息"""
    version_id: int
    tag: str
    rank: int


class PendingMatchMovie(BaseModel):
    """按 imdb_id 去重的待匹配电影"""
    imdb_id: str
    imdb_title: str
    year: Optional[int] = None
    candidates: list[PendingMatchCandidate] = []
    versions: list[PendingMatchVersion] = []

    class Config:
        from_attributes = True


class PendingMatchResolve(BaseModel):
    """用户确认匹配（按 imdb_id 操作，全局生效）"""
    imdb_id: str
    action: str  # 'accept' / 'input' / 'skip'
    # accept: 使用 candidates 中的一个，需要 candidate_douban_id
    # input: 用户手动输入 douban_id
    # skip: 标记为 IMDb-only，仅创建 imdb_id 记录
    candidate_douban_id: Optional[str] = None  # accept 时使用
    manual_douban_id: Optional[str] = None  # input 时使用


class PendingMatchListResponse(BaseModel):
    movies: list[PendingMatchMovie]
    total: int
    pending_version_count: int  # 有待确认条目的版本数
