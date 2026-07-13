from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Movie, Version, VersionEntry
from app.schemas.analytics import (
    DashboardSummaryV2,
    SourceDetail,
    LatestChanges,
    KpiChanges,
    OverlapData,
    MovieBrief,
    UniqueMoviesReport,
    DistributionData,
    CompareDistribution,
    TimelineSnapshot,
    SnapshotEntry,
    VersionTagInfo,
)

router = APIRouter()


# ── Helpers ──


def _latest_confirmed_version(db: Session, source: str) -> Version | None:
    """取某 source 最新的 confirmed version"""
    return (
        db.query(Version)
        .filter(Version.source == source, Version.status == "confirmed")
        .order_by(Version.tag.desc())
        .first()
    )


def _version_by_tag(db: Session, source: str, tag: str) -> Version | None:
    """取指定 source + tag 的 confirmed version"""
    return (
        db.query(Version)
        .filter(Version.source == source, Version.status == "confirmed", Version.tag == tag)
        .first()
    )


def _version_entries_map(db: Session, version_id: int) -> dict[int, VersionEntry]:
    """取某 version 的全部 entries → {movie_id: entry}"""
    entries = (
        db.query(VersionEntry)
        .filter(VersionEntry.version_id == version_id)
        .all()
    )
    return {e.movie_id: e for e in entries}


def _movie_metadata_map(db: Session, movie_ids: set[int]) -> dict[int, Movie]:
    """批量获取电影元数据 → {movie_id: movie}"""
    if not movie_ids:
        return {}
    movies = db.query(Movie).filter(Movie.id.in_(movie_ids)).all()
    return {m.id: m for m in movies}


def _get_next_fire_time(job_id: str):
    """从 APScheduler 获取任务的下次执行时间"""
    try:
        from app.services.scheduler import scheduler
        for job in scheduler.scheduler.get_jobs():
            if job.id == job_id:
                return job.next_run_time
    except Exception:
        pass
    return None


def _find_prev_changed_version(db: Session, source: str, latest_ver: Version) -> Version | None:
    """从 latest_ver 往前遍历，找到最近一个电影集合与 latest_ver 不同的版本。"""
    latest_entries = _version_entries_map(db, latest_ver.id)
    latest_ids = set(latest_entries.keys())

    prev_versions = (
        db.query(Version)
        .filter(Version.source == source, Version.status == "confirmed", Version.tag < latest_ver.tag)
        .order_by(Version.tag.desc())
        .all()
    )

    for prev_ver in prev_versions:
        prev_entries = _version_entries_map(db, prev_ver.id)
        prev_ids = set(prev_entries.keys())
        if prev_ids != latest_ids:
            return prev_ver

    return None



# 复用: 排除已知的国家名（类型字段中混入的地区）
_EXCLUDE_GENRES = {
    "中国大陆", "美国", "日本", "韩国", "英国", "法国", "德国", "意大利",
    "中国香港", "中国台湾", "印度", "澳大利亚", "加拿大", "西班牙",
    "苏联", "西德", "东德", "瑞典", "丹麦", "波兰", "捷克", "巴西",
    "阿根廷", "墨西哥", "伊朗", "泰国", "越南", "印尼", "马来西亚",
    "新西兰", "爱尔兰", "比利时", "荷兰", "瑞士", "奥地利", "挪威",
    "芬兰", "匈牙利", "希腊", "葡萄牙", "土耳其", "以色列", "南非",
    "古巴", "智利", "哥伦比亚", "委内瑞拉", "埃及", "摩洛哥", "突尼斯",
}

# 年代排序常量（新→旧），前端 reverse 后图表显示旧→新从上到下
_YEAR_ORDER = ["2020s", "2010s", "2000s", "1990s", "1990以前"]


def _compute_distribution(db: Session, ver: Version) -> DistributionData:
    """计算单个版本的 genre/country/year 分布"""
    entries = db.query(VersionEntry).filter(VersionEntry.version_id == ver.id).all()
    movie_ids = {e.movie_id for e in entries}
    meta_map = _movie_metadata_map(db, movie_ids)

    genres: dict[str, int] = {}
    countries: dict[str, int] = {}
    years: dict[str, int] = {}

    for mid in movie_ids:
        m = meta_map.get(mid)
        if not m:
            continue

        # 类型分布
        if m.genre:
            for g in m.genre.split():
                g = g.strip()
                if g and not g.isdigit() and g not in _EXCLUDE_GENRES and "大陆" not in g:
                    genres[g] = genres.get(g, 0) + 1

        # 国家分布
        if m.country:
            for c in m.country.split():
                c = c.strip()
                if c and not c.isdigit() and c != "/" and "(" not in c:
                    countries[c] = countries.get(c, 0) + 1

        # 年代分布 (固定分组)
        if m.year:
            if m.year >= 2020:
                label = "2020s"
            elif m.year >= 2010:
                label = "2010s"
            elif m.year >= 2000:
                label = "2000s"
            elif m.year >= 1990:
                label = "1990s"
            else:
                label = "1990以前"
            years[label] = years.get(label, 0) + 1

    # 年代固定排序（新→旧，前端 reverse 后在图表上显示为旧→新从上到下）
    sorted_years = {k: years[k] for k in _YEAR_ORDER if k in years}

    return DistributionData(
        genres=dict(sorted(genres.items(), key=lambda x: x[1], reverse=True)),
        countries=dict(sorted(countries.items(), key=lambda x: x[1], reverse=True)),
        years=sorted_years,
        source=ver.source,
        tag=ver.tag,
    )


def _apply_limit(dist: DistributionData, limit: int) -> DistributionData:
    """对分布数据应用 limit 截断（limit=0 不截断）"""
    if limit <= 0:
        return dist
    return DistributionData(
        genres=dict(list(dist.genres.items())[:limit]),
        countries=dict(list(dist.countries.items())[:limit]),
        years=dict(list(dist.years.items())[:limit]),
        source=dist.source,
        tag=dist.tag,
    )


# ── Dashboard ──


@router.get("/dashboard", response_model=DashboardSummaryV2)
def get_dashboard(db: Session = Depends(get_db)):
    """概览仪表盘 V2：按两榜分别展示"""
    douban_ver = _latest_confirmed_version(db, "douban")
    imdb_ver = _latest_confirmed_version(db, "imdb")

    # 去重后总电影数
    total_movies = db.query(func.count(func.distinct(VersionEntry.movie_id))).scalar() or 0

    # 各源版本数
    douban_count = (
        db.query(func.count(Version.id))
        .filter(Version.source == "douban", Version.status == "confirmed")
        .scalar() or 0
    )
    imdb_count = (
        db.query(func.count(Version.id))
        .filter(Version.source == "imdb", Version.status == "confirmed")
        .scalar() or 0
    )

    # 各源详情
    def _build_source_detail(source: str, ver: Version | None, ver_count: int, job_id: str) -> SourceDetail:
        if not ver:
            return SourceDetail(version_count=ver_count)

        # 下次抓取时间
        next_fire = _get_next_fire_time(job_id)

        # 上一版本 (KPI 用)
        prev_ver = (
            db.query(Version)
            .filter(Version.source == source, Version.status == "confirmed", Version.tag < ver.tag)
            .order_by(Version.tag.desc())
            .first()
        )

        # 上一个有电影进出的版本 (变动卡片用)
        prev_changed = _find_prev_changed_version(db, source, ver)

        # ── KPI: latest vs prev_ver (仅计数) ──
        kpi_changes = KpiChanges()
        if prev_ver:
            cur_ids_kpi = set(_version_entries_map(db, ver.id).keys())
            prev_ids_kpi = set(_version_entries_map(db, prev_ver.id).keys())
            kpi_changes = KpiChanges(
                added=len(cur_ids_kpi - prev_ids_kpi),
                removed=len(prev_ids_kpi - cur_ids_kpi),
            )

        # ── 变动卡片: latest vs prev_changed (详细) ──
        changes = LatestChanges()
        compare_ver = prev_changed  # 变动卡片用 prev_changed
        if compare_ver:
            cur_entries = _version_entries_map(db, ver.id)
            prev_entries = _version_entries_map(db, compare_ver.id)
            cur_ids = set(cur_entries.keys())
            prev_ids = set(prev_entries.keys())

            added_ids = cur_ids - prev_ids
            removed_ids = prev_ids - cur_ids
            common_ids = cur_ids & prev_ids

            # 批量获取元数据
            all_ids = added_ids | removed_ids | common_ids
            meta_map = _movie_metadata_map(db, all_ids)

            # 新进电影
            added_movies = []
            for mid in added_ids:
                m = meta_map.get(mid)
                if m:
                    added_movies.append({
                        "movie_id": mid,
                        "douban_id": m.douban_id,
                        "title": m.title,
                        "poster_path": m.poster_path,
                        "rank": cur_entries[mid].rank,
                    })
            added_movies.sort(key=lambda x: x["rank"])

            # 跌出电影
            removed_movies = []
            for mid in removed_ids:
                m = meta_map.get(mid)
                if m:
                    removed_movies.append({
                        "movie_id": mid,
                        "douban_id": m.douban_id,
                        "title": m.title,
                        "poster_path": m.poster_path,
                        "rank": prev_entries[mid].rank,
                    })
            removed_movies.sort(key=lambda x: x["rank"])

            # 排名升降 Top 10 (仅计算共同在榜的)
            risers = []
            fallers = []
            for mid in common_ids:
                delta = prev_entries[mid].rank - cur_entries[mid].rank  # 正=上升
                if delta != 0:
                    m = meta_map.get(mid)
                    entry = {
                        "movie_id": mid,
                        "douban_id": m.douban_id if m else None,
                        "title": m.title if m else "Unknown",
                        "poster_path": m.poster_path if m else None,
                        "rank_change": delta,
                        "current_rank": cur_entries[mid].rank,
                    }
                    if delta > 0:
                        risers.append(entry)
                    else:
                        fallers.append(entry)
            risers.sort(key=lambda x: x["rank_change"], reverse=True)
            fallers.sort(key=lambda x: x["rank_change"])

            # 平均评分变化
            if common_ids:
                deltas = [
                    cur_entries[mid].rating - prev_entries[mid].rating
                    for mid in common_ids
                    if cur_entries[mid].rating is not None and prev_entries[mid].rating is not None
                ]
                avg_delta = sum(deltas) / len(deltas) if deltas else 0.0
            else:
                avg_delta = 0.0

            changes = LatestChanges(
                added=len(added_ids),
                removed=len(removed_ids),
                avg_rating_delta=round(avg_delta, 3),
                added_movies=added_movies,
                removed_movies=removed_movies,
                risers_top10=risers[:10],
                fallers_top10=fallers[:10],
            )

        return SourceDetail(
            latest_tag=ver.tag,
            latest_crawled_at=ver.crawled_at,
            latest_version_id=ver.id,
            next_fire_time=next_fire,
            prev_tag=prev_ver.tag if prev_ver else None,
            prev_version_id=prev_ver.id if prev_ver else None,
            prev_changed_tag=prev_changed.tag if prev_changed else None,
            prev_changed_version_id=prev_changed.id if prev_changed else None,
            version_count=ver_count,
            kpi_changes=kpi_changes,
            changes=changes,
        )

    douban_detail = _build_source_detail("douban", douban_ver, douban_count, "crawl_top250")
    imdb_detail = _build_source_detail("imdb", imdb_ver, imdb_count, "crawl_imdb")

    return DashboardSummaryV2(
        douban=douban_detail,
        imdb=imdb_detail,
        total_movies=total_movies,
    )


# ── Cross-Platform (简化版，保留给 Dashboard 使用) ──


def _get_cross_platform_data(db: Session) -> tuple[dict, dict, dict]:
    """获取双榜交叉数据: (douban_entries, imdb_entries, movie_meta)"""
    douban_ver = _latest_confirmed_version(db, "douban")
    imdb_ver = _latest_confirmed_version(db, "imdb")
    if not douban_ver or not imdb_ver:
        return {}, {}, {}

    douban_map = _version_entries_map(db, douban_ver.id)
    imdb_map = _version_entries_map(db, imdb_ver.id)

    all_ids = set(douban_map.keys()) | set(imdb_map.keys())
    meta_map = _movie_metadata_map(db, all_ids)

    return douban_map, imdb_map, meta_map


@router.get("/cross-platform/overlap", response_model=OverlapData)
def get_overlap(db: Session = Depends(get_db)):
    """双榜重叠率"""
    douban_map, imdb_map, _ = _get_cross_platform_data(db)
    if not douban_map or not imdb_map:
        return OverlapData()

    d_ids = set(douban_map.keys())
    i_ids = set(imdb_map.keys())

    return OverlapData(
        only_douban=len(d_ids - i_ids),
        only_imdb=len(i_ids - d_ids),
        both=len(d_ids & i_ids),
    )


@router.get("/cross-platform/unique-movies", response_model=UniqueMoviesReport)
def get_unique_movies(
    top_n: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """仅上榜一个榜单的电影，按该榜单排名排序"""
    douban_map, imdb_map, meta_map = _get_cross_platform_data(db)
    if not douban_map or not imdb_map:
        return UniqueMoviesReport()

    d_ids = set(douban_map.keys())
    i_ids = set(imdb_map.keys())

    # 仅豆瓣
    only_douban_ids = d_ids - i_ids
    only_douban = []
    for mid in only_douban_ids:
        m = meta_map.get(mid)
        if m:
            only_douban.append(MovieBrief(
                movie_id=mid,
                douban_id=m.douban_id,
                title=m.title,
                poster_path=m.poster_path,
                rank=douban_map[mid].rank,
            ))
    only_douban.sort(key=lambda x: x.rank or 999)

    # 仅 IMDb
    only_imdb_ids = i_ids - d_ids
    only_imdb = []
    for mid in only_imdb_ids:
        m = meta_map.get(mid)
        if m:
            only_imdb.append(MovieBrief(
                movie_id=mid,
                douban_id=m.douban_id,
                title=m.title,
                poster_path=m.poster_path,
                rank=imdb_map[mid].rank,
            ))
    only_imdb.sort(key=lambda x: x.rank or 999)

    return UniqueMoviesReport(
        only_douban=only_douban[:top_n],
        only_imdb=only_imdb[:top_n],
    )


# ── Distribution ──


@router.get("/distribution")
def get_distribution(
    source: str = Query("douban", pattern="^(douban|imdb|compare)$"),
    tag: str | None = Query(None, description="指定版本 tag，默认取最新"),
    limit: int = Query(20, ge=0, description="返回条数限制，0=不限制"),
    douban_tag: str | None = Query(None, description="compare 模式下豆瓣版本 tag"),
    imdb_tag: str | None = Query(None, description="compare 模式下 IMDb 版本 tag"),
    db: Session = Depends(get_db),
):
    """类型/国家/年代分布统计，支持 compare 模式"""
    if source == "compare":
        # 支持指定特定版本 tag，默认取最新
        if douban_tag:
            douban_ver = _version_by_tag(db, "douban", douban_tag)
        else:
            douban_ver = _latest_confirmed_version(db, "douban")
        if imdb_tag:
            imdb_ver = _version_by_tag(db, "imdb", imdb_tag)
        else:
            imdb_ver = _latest_confirmed_version(db, "imdb")
        if not douban_ver or not imdb_ver:
            return CompareDistribution()

        douban_dist = _compute_distribution(db, douban_ver)
        imdb_dist = _compute_distribution(db, imdb_ver)

        # 标签取并集（在截断之前，避免一侧被截断后标签丢失）
        all_genres = sorted(
            set(douban_dist.genres.keys()) | set(imdb_dist.genres.keys())
        )
        all_countries = sorted(
            set(douban_dist.countries.keys()) | set(imdb_dist.countries.keys())
        )

        # 按两榜合计数量降序 (genres/countries)
        def _combined_sort(labels: list[str], d_data: dict, i_data: dict) -> list[str]:
            return sorted(labels, key=lambda k: d_data.get(k, 0) + i_data.get(k, 0), reverse=True)

        sorted_genres = _combined_sort(all_genres, douban_dist.genres, imdb_dist.genres)
        sorted_countries = _combined_sort(all_countries, douban_dist.countries, imdb_dist.countries)

        # 年代保持时间序（新→旧），不按数量排序；前端 reverse 后图表显示旧→新从上到下
        all_year_keys = set(douban_dist.years.keys()) | set(imdb_dist.years.keys())
        all_years = [y for y in _YEAR_ORDER if y in all_year_keys]

        # 截断（在并集计算之后，保证两榜使用相同的标签集）
        if limit > 0:
            douban_dist = _apply_limit(douban_dist, limit)
            imdb_dist = _apply_limit(imdb_dist, limit)
            sorted_genres = sorted_genres[:limit]
            sorted_countries = sorted_countries[:limit]
            all_years = all_years[:limit]

        return CompareDistribution(
            douban=douban_dist,
            imdb=imdb_dist,
            all_labels={
                "genres": sorted_genres,
                "countries": sorted_countries,
                "years": all_years,
            },
        )

    else:
        # 单源模式
        if tag:
            ver = _version_by_tag(db, source, tag)
            if not ver:
                raise HTTPException(status_code=404, detail=f"Version {tag}/{source} not found")
        else:
            ver = _latest_confirmed_version(db, source)

        if not ver:
            return DistributionData(source=source)

        dist = _compute_distribution(db, ver)
        return _apply_limit(dist, limit)


# ── Version Tags ──


@router.get("/version-tags", response_model=list[VersionTagInfo])
def get_version_tags(
    source: str = Query("douban", pattern="^(douban|imdb)$"),
    db: Session = Depends(get_db),
):
    """返回指定 source 的所有 confirmed version tags，用于时间轴"""
    versions = (
        db.query(Version)
        .filter(Version.source == source, Version.status == "confirmed")
        .order_by(Version.tag)
        .all()
    )
    return [VersionTagInfo(id=v.id, tag=v.tag, movie_count=v.movie_count, crawled_at=v.crawled_at) for v in versions]


# ── Timeline Snapshot ──


@router.get("/timeline-snapshot", response_model=TimelineSnapshot)
def get_timeline_snapshot(
    tag: str = Query(...),
    source: str = Query("douban", pattern="^(douban|imdb)$"),
    db: Session = Depends(get_db),
):
    """指定时间点的榜单快照"""
    version = (
        db.query(Version)
        .filter(Version.tag == tag, Version.source == source, Version.status == "confirmed")
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail=f"Version {tag}/{source} not found")

    entries = (
        db.query(VersionEntry, Movie)
        .join(Movie, VersionEntry.movie_id == Movie.id)
        .filter(VersionEntry.version_id == version.id)
        .order_by(VersionEntry.rank)
        .all()
    )

    movies = []
    for entry, movie in entries:
        movies.append(SnapshotEntry(
            movie_id=movie.id,
            douban_id=movie.douban_id,
            title=movie.title,
            poster_path=movie.poster_path,
            rank=entry.rank,
            rating=entry.rating,
        ))

    return TimelineSnapshot(tag=tag, source=source, movies=movies)
