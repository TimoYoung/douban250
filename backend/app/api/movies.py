from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Movie, Version, VersionEntry, WatchedMovie, Setting
from app.schemas.movie import MovieListItem, MovieDetail, MovieBubble, PaginatedMovies
from app.config import settings

router = APIRouter()


def _get_user_id(db: Session) -> str:
    """Read douban_user_id from DB setting, fall back to env config."""
    row = db.query(Setting).filter(Setting.key == "douban_user_id").first()
    if row and row.value:
        return row.value
    return settings.douban_user_id


def _get_previous_ranks(db: Session, version_id: int) -> dict[str, int]:
    """Get {douban_id: rank} from the version immediately before the given one (by tag date)."""
    current = db.query(Version).filter(Version.id == version_id).first()
    if not current:
        return {}

    prev = (
        db.query(Version)
        .filter(Version.tag < current.tag)
        .order_by(Version.tag.desc())
        .first()
    )
    if not prev:
        return {}

    entries = (
        db.query(VersionEntry, Movie)
        .join(Movie, VersionEntry.movie_id == Movie.id)
        .filter(VersionEntry.version_id == prev.id)
        .all()
    )
    return {movie.douban_id: entry.rank for entry, movie in entries}


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
        old_rank = prev_ranks.get(movie.douban_id)
        if old_rank is None:
            rank_change = None  # New movie
        else:
            rank_change = old_rank - entry.rank  # positive = moved up

        items.append(MovieListItem(
            id=movie.id,
            douban_id=movie.douban_id,
            title=movie.title,
            year=movie.year,
            rating=movie.rating,
            poster_path=movie.poster_path,
            rank=entry.rank,
            watched=movie.douban_id in watched_ids,
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
            title=movie.title,
            rank=entry.rank,
            watched=movie.douban_id in watched_ids,
        )
        for entry, movie in entries
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
                "rank": entry.rank,
                "rating": entry.rating,
                "dropped": False,
            })
        else:
            history.append({
                "version_id": v.id,
                "tag": v.tag,
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
    watched = db.query(WatchedMovie).filter(
        WatchedMovie.douban_user_id == _get_user_id(db),
        WatchedMovie.douban_movie_id == movie.douban_id,
    ).first() is not None

    return MovieDetail(
        id=movie.id,
        douban_id=movie.douban_id,
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
