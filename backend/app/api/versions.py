from pathlib import Path
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Version
from app.models.movie import Movie, VersionEntry, PendingMatch
from app.schemas.version import VersionInfo, VersionUpdate

router = APIRouter()


@router.get("", response_model=list[VersionInfo])
def list_versions(db: Session = Depends(get_db)):
    versions = db.query(Version).order_by(Version.tag.desc()).all()
    return [VersionInfo.model_validate(v) for v in versions]


@router.get("/compare")
def compare_versions(
    version_a_id: int = Query(..., description="Version A ID"),
    version_b_id: int = Query(..., description="Version B ID"),
    top_n: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """统一版本对比：同源返回时间线差异，跨源返回平台差异。"""
    va = db.query(Version).filter(Version.id == version_a_id).first()
    vb = db.query(Version).filter(Version.id == version_b_id).first()
    if not va or not vb:
        raise HTTPException(status_code=404, detail="Version not found")

    same_source = va.source == vb.source

    entries_a = (
        db.query(VersionEntry, Movie)
        .join(Movie, VersionEntry.movie_id == Movie.id)
        .filter(VersionEntry.version_id == version_a_id)
        .all()
    )
    entries_b = (
        db.query(VersionEntry, Movie)
        .join(Movie, VersionEntry.movie_id == Movie.id)
        .filter(VersionEntry.version_id == version_b_id)
        .all()
    )

    map_a = {movie.id: (entry, movie) for entry, movie in entries_a}
    map_b = {movie.id: (entry, movie) for entry, movie in entries_b}

    ids_a = set(map_a.keys())
    ids_b = set(map_b.keys())

    only_a = []
    for mid in sorted(ids_a - ids_b, key=lambda x: map_a[x][0].rank):
        entry, movie = map_a[mid]
        only_a.append({
            "movie_id": mid,
            "title": movie.title,
            "douban_id": movie.douban_id,
            "imdb_id": movie.imdb_id,
            "poster_path": movie.poster_path,
            "rank": entry.rank,
        })

    only_b = []
    for mid in sorted(ids_b - ids_a, key=lambda x: map_b[x][0].rank):
        entry, movie = map_b[mid]
        only_b.append({
            "movie_id": mid,
            "title": movie.title,
            "douban_id": movie.douban_id,
            "imdb_id": movie.imdb_id,
            "poster_path": movie.poster_path,
            "rank": entry.rank,
        })

    common = []
    for mid in ids_a & ids_b:
        ea, ma = map_a[mid]
        eb, mb = map_b[mid]
        common.append({
            "movie_id": mid,
            "title": ma.title,
            "douban_id": ma.douban_id,
            "imdb_id": ma.imdb_id,
            "poster_path": ma.poster_path,
            "rank_a": ea.rank,
            "rank_b": eb.rank,
            "delta": ea.rank - eb.rank,
        })
    common.sort(key=lambda x: abs(x["delta"]), reverse=True)

    rank_up = [m for m in common if m["delta"] > 0][:top_n]
    rank_down = [m for m in common if m["delta"] < 0][:top_n]

    return {
        "version_a": {"id": va.id, "tag": va.tag, "source": va.source},
        "version_b": {"id": vb.id, "tag": vb.tag, "source": vb.source},
        "same_source": same_source,
        "only_a": only_a,
        "only_b": only_b,
        "common": common,
        "rank_up": rank_up,
        "rank_down": rank_down,
        "summary": {
            "only_a_count": len(only_a),
            "only_b_count": len(only_b),
            "common_count": len(common),
        },
    }


@router.get("/{version_id}", response_model=VersionInfo)
def get_version(version_id: int, db: Session = Depends(get_db)):
    version = db.query(Version).filter(Version.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return VersionInfo.model_validate(version)


@router.patch("/{version_id}", response_model=VersionInfo)
def update_version(version_id: int, body: VersionUpdate, db: Session = Depends(get_db)):
    version = db.query(Version).filter(Version.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    existing = db.query(Version).filter(
        Version.tag == body.tag,
        Version.source == version.source,
        Version.id != version_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Tag already exists")

    version.tag = body.tag
    db.commit()
    db.refresh(version)
    return VersionInfo.model_validate(version)


@router.get("/{version_id}/delete-preview")
def delete_preview(version_id: int, db: Session = Depends(get_db)):
    """预览删除某版本会影响多少孤立电影和待确认匹配"""
    version = db.query(Version).filter(Version.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    movie_ids = [
        r[0] for r in
        db.query(VersionEntry.movie_id)
        .filter(VersionEntry.version_id == version_id)
        .all()
    ]

    orphan_count = 0
    for mid in movie_ids:
        has_other = db.query(VersionEntry).filter(
            VersionEntry.movie_id == mid,
            VersionEntry.version_id != version_id,
        ).first()
        if not has_other:
            orphan_count += 1

    pending_count = db.query(PendingMatch).filter(
        PendingMatch.version_id == version_id,
        PendingMatch.status == "pending",
    ).count()

    return {
        "movie_count": len(movie_ids),
        "orphan_movie_count": orphan_count,
        "pending_match_count": pending_count,
    }


@router.delete("/{version_id}")
def delete_version(version_id: int, db: Session = Depends(get_db)):
    version = db.query(Version).filter(Version.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    tag = version.tag
    source = version.source

    # 记录该版本关联的 movie_id
    movie_ids = [
        r[0] for r in
        db.query(VersionEntry.movie_id)
        .filter(VersionEntry.version_id == version_id)
        .all()
    ]

    # 删除版本（cascade 会删除 version_entries）
    db.delete(version)
    db.flush()

    # 删除该版本关联的待确认匹配
    pending_deleted = db.query(PendingMatch).filter(
        PendingMatch.version_id == version_id,
    ).delete()

    # 清理无任何版本关联的电影
    orphan_count = 0
    poster_count = 0
    for mid in movie_ids:
        has_other = db.query(VersionEntry).filter(
            VersionEntry.movie_id == mid).first()
        if not has_other:
            movie = db.query(Movie).filter(Movie.id == mid).first()
            if movie:
                # 删除海报文件
                if movie.poster_path:
                    poster_file = settings.posters_dir / movie.poster_path
                    if poster_file.exists():
                        poster_file.unlink()
                        poster_count += 1
                db.delete(movie)
                orphan_count += 1

    db.commit()
    return {
        "message": "ok",
        "orphan_movies_deleted": orphan_count,
        "posters_deleted": poster_count,
        "pending_matches_deleted": pending_deleted,
    }
