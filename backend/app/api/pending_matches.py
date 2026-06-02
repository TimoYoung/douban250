import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.movie import (
    PendingMatch, Movie, Version, VersionEntry)
from app.schemas.pending_match import (
    PendingMatchListResponse, PendingMatchMovie, PendingMatchVersion,
    PendingMatchResolve)

router = APIRouter(tags=["pending-matches"])
logger = logging.getLogger(__name__)


def _resolve_imdb_id(
    db: Session, imdb_id: str, douban_id: str | None,
) -> Movie:
    """根据 imdb_id 解析或创建 Movie 记录。"""
    movie = db.query(Movie).filter(Movie.imdb_id == imdb_id).first()
    if movie:
        if douban_id and not movie.douban_id:
            movie.douban_id = douban_id
        return movie

    # 查找 douban_id 是否已被其他记录使用
    if douban_id:
        existing = db.query(Movie).filter(
            Movie.douban_id == douban_id).first()
        if existing:
            if not existing.imdb_id:
                existing.imdb_id = imdb_id
            return existing

    # 从 pending match 取标题信息
    pm = db.query(PendingMatch).filter(
        PendingMatch.imdb_id == imdb_id).first()
    title = pm.imdb_title if pm else imdb_id
    year = pm.year if pm else None

    movie = Movie(
        douban_id=douban_id,
        imdb_id=imdb_id,
        title=title,
        year=year,
    )
    db.add(movie)
    db.flush()
    return movie


@router.get("", response_model=PendingMatchListResponse)
def list_pending_matches(db: Session = Depends(get_db)):
    """返回按 imdb_id 去重的待匹配电影列表。"""
    all_pm = db.query(PendingMatch).filter(
        PendingMatch.status == "pending"
    ).order_by(PendingMatch.rank).all()

    # 按 imdb_id 去重，收集每个 imdb_id 的版本和候选
    by_imdb: dict[str, dict] = {}
    for pm in all_pm:
        if pm.imdb_id not in by_imdb:
            by_imdb[pm.imdb_id] = {
                "imdb_id": pm.imdb_id,
                "imdb_title": pm.imdb_title,
                "year": pm.year,
                "candidates": pm.candidates or [],
                "versions": [],
            }
        entry = by_imdb[pm.imdb_id]
        if pm.version_id and pm.version:
            entry["versions"].append({
                "version_id": pm.version_id,
                "tag": pm.version.tag,
                "rank": pm.rank,
            })

    movies = []
    for data in by_imdb.values():
        movies.append(PendingMatchMovie(
            imdb_id=data["imdb_id"],
            imdb_title=data["imdb_title"],
            year=data["year"],
            candidates=data["candidates"],
            versions=[PendingMatchVersion(**v) for v in data["versions"]],
        ))

    pending_version_count = db.query(
        func.count(func.distinct(PendingMatch.version_id))
    ).filter(
        PendingMatch.status == "pending",
        PendingMatch.version_id.isnot(None),
    ).scalar() or 0

    return PendingMatchListResponse(
        movies=movies,
        total=len(movies),
        pending_version_count=pending_version_count,
    )


@router.post("/resolve")
def resolve_pending_match(
    body: PendingMatchResolve, db: Session = Depends(get_db),
):
    """按 imdb_id 解析，自动应用到所有版本中该电影的 pending match。

    action:
      - accept: 使用候选中的 douban_id (candidate_douban_id)
      - input: 用户手动输入 douban_id (manual_douban_id)
      - skip: 创建 IMDb-only 条目（无 douban_id）
    """
    if body.action not in ("accept", "input", "skip"):
        raise HTTPException(400, f"无效操作: {body.action}")

    douban_id = None
    if body.action == "accept":
        if not body.candidate_douban_id:
            raise HTTPException(400, "accept 操作需要 candidate_douban_id")
        douban_id = body.candidate_douban_id
    elif body.action == "input":
        if not body.manual_douban_id:
            raise HTTPException(400, "input 操作需要 manual_douban_id")
        douban_id = body.manual_douban_id

    # 查找所有该 imdb_id 的 pending match
    pms = db.query(PendingMatch).filter(
        PendingMatch.imdb_id == body.imdb_id,
        PendingMatch.status == "pending",
    ).all()
    if not pms:
        raise HTTPException(404, f"未找到 imdb_id={body.imdb_id} 的待确认记录")

    # 创建或获取 Movie
    movie = _resolve_imdb_id(db, body.imdb_id, douban_id)

    # 收集需要更新状态的版本 ID
    affected_version_ids = set()

    for pm in pms:
        if pm.version_id:
            affected_version_ids.add(pm.version_id)
            # 检查该版本是否已有该电影或该排名的 VersionEntry
            existing_ve = db.query(VersionEntry).filter(
                VersionEntry.version_id == pm.version_id,
                (VersionEntry.movie_id == movie.id) |
                (VersionEntry.rank == pm.rank),
            ).first()
            if not existing_ve:
                db.add(VersionEntry(
                    version_id=pm.version_id,
                    movie_id=movie.id,
                    rank=pm.rank,
                ))
        pm.status = "confirmed"
        pm.resolved_douban_id = douban_id
        pm.resolved_movie_id = movie.id

    # 检查受影响的版本是否所有 pending 都已处理，自动 finalize
    db.flush()  # 确保 pending match 状态变更写入数据库
    for vid in affected_version_ids:
        remaining = db.query(PendingMatch).filter(
            PendingMatch.version_id == vid,
            PendingMatch.status == "pending",
        ).count()
        if remaining == 0:
            version = db.query(Version).filter(Version.id == vid).first()
            if version and version.status == "pending_confirmation":
                version.status = "confirmed"
                # 更新 movie_count 为实际 entries 数量
                actual_count = db.query(VersionEntry).filter(
                    VersionEntry.version_id == vid).count()
                version.movie_count = actual_count
                logger.info(
                    f"版本 {version.tag} 自动确认，"
                    f"movie_count 更新为 {actual_count}")

    db.commit()

    label = {"accept": "接受候选", "input": "手动输入", "skip": "跳过"}
    return {
        "ok": True,
        "message": f"已{label[body.action]}: {body.imdb_id} "
                   f"-> {douban_id or 'IMDb-only'}",
        "movie_id": movie.id,
    }
