import logging
from datetime import datetime, date
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import WatchedMovie, CrawlLog
from app.utils import now
from app.utils.http_client import fetch_page
from app.utils.html_parser import parse_watched_page
from app.services.crawler import crawl_progress

logger = logging.getLogger(__name__)

PAGE_SIZE = 15


def scrape_user_watched(user_id: str, full: bool = False) -> dict:
    """Scrape a Douban user's watched/collection list.

    Args:
        full: If True, scrape all pages and remove stale entries (deletions).
              If False, stop early when encountering only known movies.
    """
    db = SessionLocal()
    log = CrawlLog(
        job_type="user_watched",
        status="running",
        started_at=now(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    # Load existing watched IDs for early-stop optimization
    existing_ids = set(
        r[0] for r in db.query(WatchedMovie.douban_movie_id)
        .filter(WatchedMovie.douban_user_id == user_id)
        .all()
    )

    crawl_progress.update({
        "active": True,
        "job_type": "user_watched",
        "phase": "fetching_pages",
        "page_current": 0,
        "page_total": 0,
        "movies_found": 0,
        "message": f"正在同步用户 {user_id} 的看过列表...",
    })

    try:
        all_movies = []
        seen_ids = set()
        start = 0
        page_num = 0
        total_count = 0
        stopped_early = False

        while True:
            page_num += 1
            crawl_progress.update({
                "page_current": page_num,
                "message": f"正在爬取看过列表第 {page_num} 页 (start={start})",
            })
            logger.info(f"Fetching watched page {page_num}: start={start}")

            url = f"https://movie.douban.com/people/{user_id}/collect?start={start}&sort=time&rating=&filter=all&mode=grid"
            html = fetch_page(url)
            page_movies, page_total = parse_watched_page(html)

            if page_total > 0:
                total_count = page_total

            if not page_movies:
                if len(all_movies) >= total_count > 0 or start > total_count + PAGE_SIZE:
                    break
                start += PAGE_SIZE
                continue

            # Check if all items on this page are already known (early stop)
            if not full:
                page_ids = {m.get("douban_id") for m in page_movies if m.get("douban_id")}
                if page_ids and page_ids <= existing_ids:
                    logger.info(f"All {len(page_movies)} items on page {page_num} already known, stopping early")
                    stopped_early = True
                    break

            # Collect new items
            new_count = 0
            for m in page_movies:
                did = m.get("douban_id")
                if did and did not in seen_ids:
                    seen_ids.add(did)
                    all_movies.append(m)
                    new_count += 1

            crawl_progress["movies_found"] = len(all_movies)
            logger.info(f"Page {page_num}: {len(page_movies)} items, {new_count} new, total={len(all_movies)}/{total_count}")

            if len(all_movies) >= total_count > 0:
                break

            if new_count == 0 and start > total_count:
                break

            start += PAGE_SIZE

        # Save to database
        crawl_progress.update({"phase": "saving", "message": f"正在保存 {len(all_movies)} 部看过电影..."})
        logger.info(f"Saving {len(all_movies)} watched movies for user {user_id}")

        saved_count = 0
        for data in all_movies:
            watched = (
                db.query(WatchedMovie)
                .filter(
                    WatchedMovie.douban_user_id == user_id,
                    WatchedMovie.douban_movie_id == data["douban_id"],
                )
                .first()
            )

            if not watched:
                watched = WatchedMovie(
                    douban_user_id=user_id,
                    douban_movie_id=data["douban_id"],
                )
                db.add(watched)

            watched.watched_date = _parse_date(data.get("watched_date"))
            watched.user_comment = data.get("user_comment")
            watched.scraped_at = now()
            saved_count += 1

        # Full sync: remove entries no longer in the scraped list
        deleted_count = 0
        if full and seen_ids:
            stale = db.query(WatchedMovie).filter(
                WatchedMovie.douban_user_id == user_id,
                ~WatchedMovie.douban_movie_id.in_(seen_ids),
            ).all()
            for w in stale:
                db.delete(w)
                deleted_count += 1
            if deleted_count:
                logger.info(f"Removed {deleted_count} stale watched entries")

        db.commit()

        # Get total watched count for this user
        total_watched = db.query(WatchedMovie).filter(
            WatchedMovie.douban_user_id == user_id,
        ).count()

        if full:
            mode_msg = "全量"
        elif stopped_early:
            mode_msg = "增量"
        else:
            mode_msg = "增量"

        msg = f"{mode_msg}同步完成，共 {total_watched} 部"
        if deleted_count:
            msg += f"，删除 {deleted_count} 部"
        log.status = "success"
        log.finished_at = now()
        log.movies_found = total_watched
        db.commit()

        crawl_progress.update({"phase": "done", "active": False, "message": msg})
        logger.info(f"User scrape done ({mode_msg}): {total_watched} total, {saved_count} saved, {deleted_count} deleted")
        return {"success": True, "movies_found": total_watched, "deleted": deleted_count}

    except Exception as e:
        logger.error(f"User scrape failed: {e}")
        log.status = "failed"
        log.finished_at = now()
        log.error_message = str(e)
        db.commit()
        crawl_progress.update({"phase": "done", "active": False, "message": f"同步失败: {e}"})
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def get_watched_ids(db: Session, user_id: str) -> list[str]:
    """Get list of douban_ids the user has watched."""
    results = (
        db.query(WatchedMovie.douban_movie_id)
        .filter(WatchedMovie.douban_user_id == user_id)
        .all()
    )
    return [r[0] for r in results]


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse date string from douban format."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None
