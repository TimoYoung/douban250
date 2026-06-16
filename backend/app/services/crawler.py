import logging
import re
import threading
from pathlib import Path

from sqlalchemy.orm import Session
from bs4 import BeautifulSoup

from app.config import settings
from app.database import SessionLocal
from app.models import Movie, Version, VersionEntry, CrawlLog
from app.utils import now
from app.utils.http_client import fetch_page, fetch_binary
from app.utils.html_parser import parse_top250_page

logger = logging.getLogger(__name__)


def _get_retry_manager():
    """延迟导入重试管理器，避免循环导入"""
    from app.services.retry_manager import get_retry_manager
    return get_retry_manager()


# In-memory progress state for real-time tracking
crawl_progress = {
    "active": False,
    "job_type": None,  # "top250" or "user_watched"
    "phase": "",  # "fetching_pages", "saving_movies", "downloading_posters", "creating_version", "done"
    "page_current": 0,
    "page_total": 0,
    "movies_found": 0,
    "posters_done": 0,
    "posters_total": 0,
    "message": "",
}


def _reset_progress(job_type: str):
    global crawl_progress
    crawl_progress.update({
        "active": True,
        "job_type": job_type,
        "phase": "",
        "page_current": 0,
        "page_total": 0,
        "movies_found": 0,
        "posters_done": 0,
        "posters_total": 0,
        "message": "",
    })


def get_progress() -> dict:
    return dict(crawl_progress)


def crawl_top250() -> dict:
    """Crawl the Top 250 movie list. Returns result dict."""
    db = SessionLocal()
    log = CrawlLog(
        job_type="top250",
        status="running",
        started_at=now(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    _reset_progress("top250")

    try:
        # Phase 1: Fetch pages
        crawl_progress.update({"phase": "fetching_pages", "page_total": 10})
        all_movies = []
        for i, start in enumerate(range(0, 250, 25)):
            crawl_progress["page_current"] = i + 1
            crawl_progress["message"] = f"正在爬取第 {i + 1}/10 页 (start={start})"
            logger.info(f"Fetching Top 250 page: start={start} ({i + 1}/10)")

            url = f"https://movie.douban.com/top250?start={start}&filter="
            html = fetch_page(url)
            page_movies = parse_top250_page(html)
            all_movies.extend(page_movies)
            crawl_progress["movies_found"] = len(all_movies)

        if len(all_movies) != 250:
            raise RuntimeError(f"Expected 250 movies, got {len(all_movies)}")

        # Phase 2: Save/update movies
        crawl_progress.update({"phase": "saving_movies", "message": "正在保存电影数据..."})
        logger.info("Saving movies to database...")

        # Bulk load existing movies to detect new ones and avoid N+1 queries
        existing_movies = {m.douban_id: m for m in db.query(Movie).filter(Movie.douban_id.in_([d["douban_id"] for d in all_movies])).all()}
        existing_ids = set(existing_movies.keys())

        movie_objects = []
        for data in all_movies:
            movie = existing_movies.get(data["douban_id"])
            if not movie:
                movie = Movie(douban_id=data["douban_id"])
                db.add(movie)

            movie.title = data.get("title", movie.title)
            movie.original_title = data.get("original_title", movie.original_title)
            movie.year = data.get("year", movie.year)
            movie.country = data.get("country", movie.country)
            movie.genre = data.get("genre", movie.genre)
            movie.director = data.get("director", movie.director)
            movie.cast_members = data.get("cast_members", movie.cast_members)
            movie.rating = data.get("rating", movie.rating)
            movie.rating_count = data.get("rating_count", movie.rating_count)
            movie.tagline = data.get("tagline", movie.tagline)
            movie.douban_url = data.get("douban_url", movie.douban_url)
            movie.updated_at = now()

            movie_objects.append((movie, data))

        db.commit()

        # Phase 3: Check version changes FIRST
        crawl_progress.update({"phase": "creating_version", "message": "正在检查版本变化..."})
        logger.info("Checking version changes...")

        result = _create_version_if_changed(db, movie_objects)

        if not result["new_version"]:
            logger.info("No version changes, skipping poster/detail download")
            log.status = "success"
            log.finished_at = now()
            log.movies_found = len(all_movies)
            log.new_version_created = False
            log.version_id = result["version_id"]
            db.commit()
            crawl_progress.update({"phase": "done", "active": False, "message": "列表未变化，无需更新"})
            return result

        # Phase 4: Fetch details for new movies
        new_movies = [(m, d) for m, d in movie_objects if m.douban_id not in existing_ids]
        if new_movies:
            crawl_progress.update({
                "phase": "fetching_details",
                "message": f"发现 {len(new_movies)} 部新电影，正在抓取详细信息...",
            })
            logger.info(f"Fetching detail pages for {len(new_movies)} new movies...")

            for idx, (movie, data) in enumerate(new_movies):
                crawl_progress["message"] = f"正在抓取新电影 {idx + 1}/{len(new_movies)}: {movie.title}"
                logger.info(f"Fetching detail {idx + 1}/{len(new_movies)}: {movie.title} ({movie.douban_id})")
                try:
                    _fetch_and_update_detail(db, movie)
                except Exception as e:
                    logger.warning(f"Failed to fetch detail for {movie.title}: {e}")

            db.commit()

        # Phase 5: Download posters (only for movies without posters)
        movies_need_poster = [(m, d) for m, d in movie_objects if not m.poster_path and d.get("poster_url")]
        if movies_need_poster:
            crawl_progress.update({
                "phase": "downloading_posters",
                "posters_total": len(movies_need_poster),
                "posters_done": 0,
            })

            for idx, (movie, data) in enumerate(movies_need_poster):
                crawl_progress["posters_done"] = idx + 1
                crawl_progress["message"] = f"正在下载海报 {idx + 1}/{len(movies_need_poster)}: {movie.title}"
                logger.info(f"Downloading poster {idx + 1}/{len(movies_need_poster)}: {movie.title}")

                try:
                    poster_filename = f"{movie.douban_id}.jpg"
                    poster_full_path = settings.posters_dir / poster_filename
                    if not poster_full_path.exists():
                        content = fetch_binary(data["poster_url"])
                        poster_full_path.write_bytes(content)
                    movie.poster_path = poster_filename
                except Exception as e:
                    logger.warning(f"Failed to download poster for {movie.title}: {e}")

            db.commit()

        log.status = "success"
        log.finished_at = now()
        log.movies_found = len(all_movies)
        log.new_version_created = result["new_version"]
        if result.get("version_id"):
            log.version_id = result["version_id"]
        db.commit()

        crawl_progress.update({"phase": "done", "active": False, "message": "爬取完成"})
        logger.info(f"Top 250 crawl completed: {result}")

        # 成功后取消等待中的重试
        try:
            retry_mgr = _get_retry_manager()
            retry_mgr.cancel_retry("top250")
        except Exception as e:
            logger.warning(f"Failed to cancel retry: {e}")

        # 新版本创建后自动触发增量元数据补全
        if result.get("new_version"):
            _trigger_metadata_backfill()

        return result

    except Exception as e:
        logger.error(f"Crawl failed: {e}")
        log.status = "failed"
        log.finished_at = now()
        log.error_message = str(e)
        db.commit()
        crawl_progress.update({"phase": "done", "active": False, "message": f"爬取失败: {e}"})

        # 安排重试
        try:
            retry_mgr = _get_retry_manager()
            retry_mgr.schedule_retry("top250", str(e), log.id)
        except Exception as retry_err:
            logger.error(f"Failed to schedule retry: {retry_err}")

        raise
    finally:
        db.close()


def _trigger_metadata_backfill():
    """在后台线程启动增量元数据补全。"""
    from app.services.metadata import run_backfill, meta_progress

    if meta_progress.get("active"):
        logger.info("Metadata backfill already active, skipping auto-trigger")
        return

    def _run():
        try:
            logger.info("Auto-triggering metadata backfill after Douban crawl...")
            result = run_backfill()
            logger.info(f"Metadata backfill completed: {result}")
        except Exception as e:
            logger.error(f"Metadata backfill failed: {e}")

    threading.Thread(target=_run, daemon=True, name="meta-backfill").start()
    logger.info("Metadata backfill thread started")


def _create_version_if_changed(db: Session, movie_objects: list) -> dict:
    """Create a new version if the movie list has changed."""
    current_ids = [m.douban_id for m, _ in movie_objects]

    # Get latest douban version by tag date
    latest_version = db.query(Version).filter(
        Version.source == "douban"
    ).order_by(Version.tag.desc()).first()

    if latest_version:
        # Get ordered list of douban_ids from latest version
        latest_entries = (
            db.query(VersionEntry, Movie)
            .join(Movie, VersionEntry.movie_id == Movie.id)
            .filter(VersionEntry.version_id == latest_version.id)
            .order_by(VersionEntry.rank)
            .all()
        )
        latest_ids = [movie.douban_id for _, movie in latest_entries]

        if current_ids == latest_ids:
            logger.info(f"Movie list unchanged vs {latest_version.tag}, skipping version creation")
            return {"new_version": False, "version_id": latest_version.id, "message": "No changes"}

        # Log diff for debugging
        current_set = set(current_ids)
        latest_set = set(latest_ids)
        added = current_set - latest_set
        removed = latest_set - current_set
        if added:
            added_titles = [m.title for m, _ in movie_objects if m.douban_id in added]
            logger.info(f"New movies: {added_titles}")
        if removed:
            removed_movies = db.query(Movie).filter(Movie.douban_id.in_(removed)).all()
            logger.info(f"Removed movies: {[m.title for m in removed_movies]}")

    # Create new version
    today = now().strftime("%Y-%m-%d")
    tag = today
    # Ensure unique tag per source
    suffix = 1
    while db.query(Version).filter(
            Version.tag == tag,
            Version.source == "douban").first():
        suffix += 1
        tag = f"{today}-{suffix}"

    version = Version(
        tag=tag,
        crawled_at=now(),
        movie_count=len(movie_objects),
    )
    db.add(version)
    db.flush()

    for movie, data in movie_objects:
        entry = VersionEntry(
            version_id=version.id,
            movie_id=movie.id,
            rank=data["rank"],
            rating=data.get("rating"),
        )
        db.add(entry)

    db.commit()
    logger.info(f"Created new version: {tag}")
    return {"new_version": True, "version_id": version.id, "tag": tag}


def _fetch_and_update_detail(db: Session, movie: Movie):
    """Fetch a movie's detail page and update all metadata fields."""
    from app.services.metadata import parse_detail_page

    url = f"https://movie.douban.com/subject/{movie.douban_id}/"
    html = fetch_page(url)
    info = parse_detail_page(html)

    for field in ["director", "genre", "country", "year", "tagline", "summary", "douban_url"]:
        if info.get(field) and not getattr(movie, field):
            setattr(movie, field, info[field])

    if info.get("cast_members") and not movie.cast_members:
        movie.cast_members = info["cast_members"]

    if not movie.poster_path and info.get("poster_url"):
        try:
            fn = f"{movie.douban_id}.jpg"
            fp = settings.posters_dir / fn
            if not fp.exists():
                fp.write_bytes(fetch_binary(info["poster_url"]))
            movie.poster_path = fn
        except Exception:
            pass

    if movie.director and movie.genre and movie.country and movie.summary and movie.poster_path and movie.douban_url:
        movie.detail_fetched = True
    movie.updated_at = now()
    db.flush()
