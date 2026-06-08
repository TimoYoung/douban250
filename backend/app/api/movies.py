from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Movie, Version, VersionEntry, WatchedMovie
from app.models.user import User
from app.schemas.movie import MovieListItem, MovieDetail, MovieBubble, PaginatedMovies, GlobalSearchResult, ExploreFilters
from app.dependencies import get_current_user, require_admin

router = APIRouter()


def _get_watched_ids(db: Session, current_user: User | None) -> set[str]:
    """Return set of watched douban_movie_ids for the current user. Empty for guests."""
    if current_user is None or not current_user.douban_user_id:
        return set()
    return set(
        r[0] for r in db.query(WatchedMovie.douban_movie_id).filter(
            WatchedMovie.douban_user_id == current_user.douban_user_id
        ).all()
    )


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
    current_user: User | None = Depends(get_current_user),
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

    # Get watched IDs (per-user, empty for guests)
    watched_ids = _get_watched_ids(db, current_user)

    if watched_ids and watched_filter == "watched":
        query = query.filter(Movie.douban_id.in_(watched_ids))
    elif watched_ids and watched_filter == "unwatched":
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
    current_user: User | None = Depends(get_current_user),
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

    watched_ids = _get_watched_ids(db, current_user)

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


@router.get("/search", response_model=list[GlobalSearchResult])
def global_search(
    q: str = Query("", min_length=0),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    if not q.strip():
        return []

    # Subquery: for each movie+source, find the latest version that contains it
    latest = (
        db.query(
            VersionEntry.movie_id,
            Version.source,
            func.max(Version.tag).label("latest_tag"),
        )
        .join(Version, VersionEntry.version_id == Version.id)
        .group_by(VersionEntry.movie_id, Version.source)
        .subquery()
    )

    rows = (
        db.query(Movie, VersionEntry, Version)
        .join(latest, Movie.id == latest.c.movie_id)
        .join(
            VersionEntry,
            (VersionEntry.movie_id == Movie.id)
            & (VersionEntry.version_id == Version.id),
        )
        .join(
            Version,
            (Version.id == VersionEntry.version_id)
            & (Version.tag == latest.c.latest_tag)
            & (Version.source == latest.c.source),
        )
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


@router.get("/explore/filters", response_model=ExploreFilters)
def get_explore_filters(db: Session = Depends(get_db)):
    """返回探索页面的筛选维度元数据：所有类型、所有地区、年份范围、评分范围"""
    movies = db.query(Movie).filter(Movie.detail_fetched == True).all()

    # 解析所有类型（格式："剧情 科幻 冒险"，空格分隔）
    # 排除纯数字年份、括号内的地区信息等非类型数据
    _EXCLUDE_GENRES = {"中国大陆", "美国", "日本", "韩国", "英国", "法国", "德国", "意大利",
                       "中国香港", "中国台湾", "印度", "澳大利亚", "加拿大", "西班牙",
                       "苏联", "西德", "东德", "瑞典", "丹麦", "波兰", "捷克", "巴西",
                       "阿根廷", "墨西哥", "伊朗", "泰国", "越南", "印尼", "马来西亚",
                       "新西兰", "爱尔兰", "比利时", "荷兰", "瑞士", "奥地利", "挪威",
                       "芬兰", "匈牙利", "希腊", "葡萄牙", "土耳其", "以色列", "南非",
                       "古巴", "智利", "哥伦比亚", "委内瑞拉", "埃及", "摩洛哥", "突尼斯"}
    genre_set: set[str] = set()
    for m in movies:
        if m.genre:
            for g in m.genre.split():
                g = g.strip()
                # 跳过空字符串、纯数字（年份）、括号内容、已知地区名
                if g and not g.isdigit() and g not in _EXCLUDE_GENRES and "大陆" not in g:
                    genre_set.add(g)

    # 解析所有地区（格式："美国 英国 加拿大"，空格分隔）
    country_set: set[str] = set()
    for m in movies:
        if m.country:
            for c in m.country.split():
                c = c.strip()
                # 跳过空字符串、纯数字（年份误入）、斜杠、含括号的年份标注
                if c and not c.isdigit() and c != "/" and "(" not in c:
                    country_set.add(c)

    # 年份范围
    year_stats = db.query(func.min(Movie.year), func.max(Movie.year)).filter(Movie.year.isnot(None)).first()
    year_min = year_stats[0] or 1900
    year_max = year_stats[1] or 2026

    # 评分范围
    rating_stats = db.query(func.min(Movie.rating), func.max(Movie.rating)).filter(Movie.rating.isnot(None)).first()
    rating_min = round(rating_stats[0] or 0, 1)
    rating_max = round(rating_stats[1] or 10, 1)

    return ExploreFilters(
        genres=sorted(genre_set),
        countries=sorted(country_set),
        year_min=year_min,
        year_max=year_max,
        rating_min=rating_min,
        rating_max=rating_max,
    )


@router.get("/explore", response_model=PaginatedMovies)
def explore_movies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    rating_min: float | None = Query(None, ge=0, le=10),
    rating_max: float | None = Query(None, ge=0, le=10),
    genres: str | None = Query(None, description="逗号分隔的类型列表，如 '剧情,科幻'"),
    countries: str | None = Query(None, description="逗号分隔的地区列表，如 '美国,日本'"),
    year_min: int | None = Query(None),
    year_max: int | None = Query(None),
    watched_filter: str = Query("all", pattern="^(all|watched|unwatched)$"),
    sort_by: str = Query("rating", pattern="^(rating|year|rank|title)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """探索页面：多维度筛选电影，支持评分/类型/地区/年份/看过状态筛选 + 排序"""
    query = db.query(Movie).filter(Movie.detail_fetched == True)

    # 评分筛选
    if rating_min is not None:
        query = query.filter(Movie.rating >= rating_min)
    if rating_max is not None:
        query = query.filter(Movie.rating <= rating_max)

    # 类型筛选（genre 字段格式："剧情 科幻 冒险"，空格分隔，支持多选 AND 逻辑）
    if genres:
        genre_list = [g.strip() for g in genres.split(",") if g.strip()]
        for g in genre_list:
            query = query.filter(Movie.genre.ilike(f"%{g}%"))

    # 地区筛选（country 字段格式："美国 英国"，空格分隔，支持多选 OR 逻辑）
    if countries:
        country_list = [c.strip() for c in countries.split(",") if c.strip()]
        if country_list:
            country_filters = [Movie.country.ilike(f"%{c}%") for c in country_list]
            query = query.filter(or_(*country_filters))

    # 年份筛选
    if year_min is not None:
        query = query.filter(Movie.year >= year_min)
    if year_max is not None:
        query = query.filter(Movie.year <= year_max)

    # 看过筛选
    watched_ids = _get_watched_ids(db, current_user)
    if watched_filter == "watched":
        if not watched_ids:
            return PaginatedMovies(items=[], total=0, page=page, page_size=page_size, total_pages=0)
        query = query.filter(Movie.douban_id.in_(watched_ids))
    elif watched_filter == "unwatched":
        if watched_ids:
            query = query.filter(~Movie.douban_id.in_(watched_ids))

    # 排序
    sort_column_map = {
        "rating": Movie.rating,
        "year": Movie.year,
        "title": Movie.title,
        "rank": Movie.rating,  # rank 需要特殊处理，先用 rating 作为默认
    }
    sort_col = sort_column_map.get(sort_by, Movie.rating)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc().nullslast())
    else:
        query = query.order_by(sort_col.desc().nullslast())

    total = query.count()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    movies = query.offset((page - 1) * page_size).limit(page_size).all()

    # 获取最新版本的排名信息
    latest_version = db.query(Version).order_by(Version.id.desc()).first()
    rank_map = {}
    if latest_version:
        entries = db.query(VersionEntry).filter(VersionEntry.version_id == latest_version.id).all()
        rank_map = {e.movie_id: e.rank for e in entries}

    items = []
    for movie in movies:
        items.append(MovieListItem(
            id=movie.id,
            douban_id=movie.douban_id,
            imdb_id=movie.imdb_id,
            title=movie.title,
            year=movie.year,
            rating=movie.rating,
            poster_path=movie.poster_path,
            rank=rank_map.get(movie.id),
            watched=(movie.douban_id or "") in watched_ids,
            director=movie.director,
            genre=movie.genre,
            rank_change=None,  # 探索页面不展示排名变化
        ))

    return PaginatedMovies(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/by-douban/{douban_id}", response_model=MovieDetail)
def get_movie_by_douban(
    douban_id: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    movie = db.query(Movie).filter(Movie.douban_id == douban_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    return _build_movie_detail(movie, db, current_user)


@router.get("/{movie_id}", response_model=MovieDetail)
def get_movie(
    movie_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    return _build_movie_detail(movie, db, current_user)


def _build_movie_detail(movie: Movie, db: Session, current_user: User | None = None) -> MovieDetail:
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

    # 每个平台取最新排名
    current_ranks = {}
    for h in reversed(history):
        if h["rank"] is not None:
            src = h["source"] or "douban"
            if src not in current_ranks:
                current_ranks[src] = {"source": src, "tag": h["tag"], "rank": h["rank"]}

    # Check watched
    watched = False
    if movie.douban_id and current_user and current_user.douban_user_id:
        watched = db.query(WatchedMovie).filter(
            WatchedMovie.douban_user_id == current_user.douban_user_id,
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
        current_ranks=list(current_ranks.values()),
        watched=watched,
    )


@router.post("/merge")
def merge_movies(
    keep_id: int = Query(..., description="Movie ID to keep"),
    merge_id: int = Query(..., description="Movie ID to merge into keep_id"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
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
