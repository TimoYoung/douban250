from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Movie, Version, VersionEntry, WatchedMovie, Setting
from app.schemas.movie import MovieListItem, MovieDetail, MovieBubble, PaginatedMovies, GlobalSearchResult
from app.config import settings

router = APIRouter()


def _get_user_id(db: Session) -> str:
    """Read douban_user_id from DB setting, fall back to env config."""
    row = db.query(Setting).filter(Setting.key == "douban_user_id").first()
    if row and row.value:
        return row.value
    return settings.douban_user_id


def _get_previous_ranks(db: Session, version_id: int) -> dict[int, int]:
    """Get {movie_id: rank} from the previous version of the same source."""
    current = db.query(Version).filter(Version.id == version_id).first()
    if not current:
        return {}

    prev = (
        db.query(Version)
        .filter(Version.tag < current.tag, Version.source == current.source)
        .order_by(Version.tag.desc())
        .first()
    )
    if not prev:
        return {}

    entries = (
        db.query(VersionEntry)
        .filter(VersionEntry.version_id == prev.id)
        .all()
    )
    return {e.movie_id: e.rank for e in entries}


@router.get("", response_model=PaginatedMovies)
def list_movies(
    version_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    watched_filter: str = Query("all", pattern="^(all|watched|unwatched)$"),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
):
    # Get the version to use
    if version_id is None:
        version = db.query(Version).order_by(Version.id.desc()).first()
        if not version:
            return PaginatedMovies(items=[], total=0, page=page, page_size=page_size, total_pages=0)
        version_id = version.id

    # Base query: join version_entries with movies
    query = (
        db.query(VersionEntry, Movie)
        .join(Movie, VersionEntry.movie_id == Movie.id)
        .filter(VersionEntry.version_id == version_id)
    )

    # Search filter
    if search:
        query = query.filter(
            or_(
                Movie.title.ilike(f"%{search}%"),
                Movie.original_title.ilike(f"%{search}%"),
                Movie.director.ilike(f"%{search}%"),
            )
        )

    # Get watched IDs
    watched_ids = set(
        r[0] for r in db.query(WatchedMovie.douban_movie_id).filter(
            WatchedMovie.douban_user_id == _get_user_id(db)
        ).all()
    )

    if watched_filter == "watched":
        query = query.filter(Movie.douban_id.in_(watched_ids))
    elif watched_filter == "unwatched":
        query = query.filter(~Movie.douban_id.in_(watched_ids))

    total = query.count()
    total_pages = (total + page_size - 1) // page_size

    entries = query.order_by(VersionEntry.rank).offset((page - 1) * page_size).limit(page_size).all()

    # Get previous version rank lookup for rank_change
    prev_ranks = _get_previous_ranks(db, version_id)

    items = []
    for entry, movie in entries:
        old_rank = prev_ranks.get(movie.id)
        if old_rank is None:
            rank_change = None  # New movie
        else:
            rank_change = old_rank - entry.rank  # positive = moved up

        items.append(MovieListItem(
            id=movie.id,
            douban_id=movie.douban_id,
            imdb_id=movie.imdb_id,
            title=movie.title,
            year=movie.year,
            rating=movie.rating,
            poster_path=movie.poster_path,
            rank=entry.rank,
            watched=(movie.douban_id or "") in watched_ids,
            director=movie.director,
            genre=movie.genre,
            rank_change=rank_change,
        ))

    return PaginatedMovies(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/bubbles", response_model=list[MovieBubble])
def get_bubbles(
    version_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    if version_id is None:
        version = db.query(Version).order_by(Version.id.desc()).first()
        if not version:
            return []
        version_id = version.id

    entries = (
        db.query(VersionEntry, Movie)
        .join(Movie, VersionEntry.movie_id == Movie.id)
        .filter(VersionEntry.version_id == version_id)
        .order_by(VersionEntry.rank)
        .all()
    )

    watched_ids = set(
        r[0] for r in db.query(WatchedMovie.douban_movie_id).filter(
            WatchedMovie.douban_user_id == _get_user_id(db)
        ).all()
    )

    return [
        MovieBubble(
            douban_id=movie.douban_id,
            imdb_id=movie.imdb_id,
            title=movie.title,
            rank=entry.rank,
            watched=(movie.douban_id or "") in watched_ids,
        )
        for entry, movie in entries
    ]


@router.get("/compare")
def compare_platforms(
    version_a_id: int = Query(..., description="Version A ID"),
    version_b_id: int = Query(..., description="Version B ID"),
    db: Session = Depends(get_db),
):
    """Compare two versions from different platforms."""
    from app.schemas.version import MovieInDiff

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

    common = []
    for mid in sorted(ids_a & ids_b):
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

    va = db.query(Version).filter(Version.id == version_a_id).first()
    vb = db.query(Version).filter(Version.id == version_b_id).first()

    return {
        "version_a": {"id": va.id, "tag": va.tag, "source": va.source} if va else None,
        "version_b": {"id": vb.id, "tag": vb.tag, "source": vb.source} if vb else None,
        "common": common,
        "only_a": only_a,
        "only_b": only_b,
    }


@router.get("/search", response_model=list[GlobalSearchResult])
def global_search(
    q: str = Query("", min_length=0),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    if not q.strip():
        return []

    # Subquery: for each movie, find the latest version that contains it
    latest = (
        db.query(
            VersionEntry.movie_id,
            func.max(Version.tag).label("latest_tag"),
        )
        .join(Version, VersionEntry.version_id == Version.id)
        .group_by(VersionEntry.movie_id)
        .subquery()
    )

    rows = (
        db.query(Movie, VersionEntry, Version)
        .join(latest, Movie.id == latest.c.movie_id)
        .join(
            VersionEntry,
            (VersionEntry.movie_id == Movie.id)
            & (
                VersionEntry.version_id
                == db.query(Version.id)
                .filter(Version.tag == latest.c.latest_tag)
                .correlate(latest)
                .scalar_subquery()
            ),
        )
        .join(Version, VersionEntry.version_id == Version.id)
        .filter(
            or_(
                Movie.title.ilike(f"%{q}%"),
                Movie.original_title.ilike(f"%{q}%"),
                Movie.director.ilike(f"%{q}%"),
            )
        )
        .order_by(Version.tag.desc(), VersionEntry.rank)
        .limit(limit)
        .all()
    )

    return [
        GlobalSearchResult(
            movie_id=movie.id,
            douban_id=movie.douban_id,
            imdb_id=movie.imdb_id,
            title=movie.title,
            year=movie.year,
            poster_path=movie.poster_path,
            latest_version_id=version.id,
            latest_version_tag=version.tag,
            rank=entry.rank,
            source=version.source,
        )
        for movie, entry, version in rows
    ]


@router.get("/by-douban/{douban_id}", response_model=MovieDetail)
def get_movie_by_douban(douban_id: str, db: Session = Depends(get_db)):
    movie = db.query(Movie).filter(Movie.douban_id == douban_id).first()
    if not movie:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Movie not found")

    return _build_movie_detail(movie, db)


@router.get("/{movie_id}", response_model=MovieDetail)
def get_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Movie not found")

    return _build_movie_detail(movie, db)


def _build_movie_detail(movie: Movie, db: Session) -> MovieDetail:
    # Get ALL versions sorted by tag
    all_versions = db.query(Version).order_by(Version.tag).all()

    # Get this movie's entries
    entries = (
        db.query(VersionEntry)
        .filter(VersionEntry.movie_id == movie.id)
        .all()
    )
    entry_map = {e.version_id: e for e in entries}

    # Build full history across all versions, marking dropped periods
    history = []
    for v in all_versions:
        entry = entry_map.get(v.id)
        if entry:
            history.append({
                "version_id": v.id,
                "tag": v.tag,
                "source": v.source,
                "rank": entry.rank,
                "rating": entry.rating,
                "dropped": False,
            })
        else:
            history.append({
                "version_id": v.id,
                "tag": v.tag,
                "source": v.source,
                "rank": None,
                "rating": None,
                "dropped": True,
            })

    current_rank = None
    for h in reversed(history):
        if h["rank"] is not None:
            current_rank = h["rank"]
            break

    # Check watched
    watched = False
    if movie.douban_id:
        watched = db.query(WatchedMovie).filter(
            WatchedMovie.douban_user_id == _get_user_id(db),
            WatchedMovie.douban_movie_id == movie.douban_id,
        ).first() is not None

    return MovieDetail(
        id=movie.id,
        douban_id=movie.douban_id,
        imdb_id=movie.imdb_id,
        title=movie.title,
        original_title=movie.original_title,
        year=movie.year,
        country=movie.country,
        genre=movie.genre,
        director=movie.director,
        cast_members=movie.cast_members,
        rating=movie.rating,
        rating_count=movie.rating_count,
        tagline=movie.tagline,
        summary=movie.summary,
        poster_path=movie.poster_path,
        douban_url=movie.douban_url,
        created_at=movie.created_at,
        updated_at=movie.updated_at,
        rank_history=history,
        current_rank=current_rank,
        watched=watched,
    )


@router.post("/merge")
def merge_movies(
    keep_id: int = Query(..., description="Movie ID to keep"),
    merge_id: int = Query(..., description="Movie ID to merge into keep_id"),
    db: Session = Depends(get_db),
):
    """合并两个电影实体：将 merge_id 的所有 VersionEntry 迁移到 keep_id，保留两者的 douban_id/imdb_id。"""
    from fastapi import HTTPException

    keep = db.query(Movie).filter(Movie.id == keep_id).first()
    merge = db.query(Movie).filter(Movie.id == merge_id).first()
    if not keep or not merge:
        raise HTTPException(status_code=404, detail="Movie not found")
    if keep_id == merge_id:
        raise HTTPException(status_code=400, detail="Cannot merge a movie with itself")

    # Transfer imdb_id if keep doesn't have one
    if merge.imdb_id and not keep.imdb_id:
        keep.imdb_id = merge.imdb_id

    # Transfer douban_id if keep doesn't have one
    if merge.douban_id and not keep.douban_id:
        keep.douban_id = merge.douban_id

    # Migrate VersionEntries: update movie_id from merge_id to keep_id
    # Handle conflicts (same version_id) by keeping the keep_id entry
    merge_entries = db.query(VersionEntry).filter(VersionEntry.movie_id == merge_id).all()
    keep_entry_versions = {
        e.version_id for e in db.query(VersionEntry).filter(VersionEntry.movie_id == keep_id).all()
    }

    migrated = 0
    for entry in merge_entries:
        if entry.version_id in keep_entry_versions:
            # Conflict: keep_id already has an entry for this version, delete merge's
            db.delete(entry)
        else:
            entry.movie_id = keep_id
            migrated += 1

    # Delete the merged movie
    db.delete(merge)
    db.commit()

    return {"message": f"Merged movie {merge_id} into {keep_id}", "migrated_entries": migrated}
