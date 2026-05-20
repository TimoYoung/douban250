"""
Metadata backfill service: periodically fetch missing metadata for all movies.
"""
import logging
import re

from bs4 import BeautifulSoup
from sqlalchemy import or_

from app.config import settings
from app.database import SessionLocal
from app.models import Movie, CrawlLog
from app.utils import now
from app.utils.http_client import fetch_page, fetch_binary, _get_cookie

logger = logging.getLogger(__name__)

# In-memory progress for metadata backfill
meta_progress = {
    "active": False,
    "total": 0,
    "done": 0,
    "updated": 0,
    "failed": 0,
    "current_movie": "",
    "message": "",
}


def get_meta_progress() -> dict:
    return dict(meta_progress)


def _needs_metadata_query():
    """SQLAlchemy filter for movies needing metadata backfill.

    Required fields must be non-empty. detail_fetched is ignored for these
    since they should always be present regardless of source availability.
    """
    return (
        or_(Movie.director.is_(None), Movie.director == "") |
        or_(Movie.genre.is_(None), Movie.genre == "") |
        or_(Movie.country.is_(None), Movie.country == "") |
        or_(Movie.summary.is_(None), Movie.summary == "") |
        or_(Movie.poster_path.is_(None), Movie.poster_path == "") |
        or_(Movie.douban_url.is_(None), Movie.douban_url == "")
    )


def check_cookie_valid() -> dict:
    """Check if the Douban cookie is still valid. Returns {valid, message}."""
    cookie = _get_cookie()
    if not cookie:
        return {"valid": False, "message": "未配置豆瓣 Cookie"}

    try:
        html = fetch_page("https://movie.douban.com/mine?status=collect", cookie=cookie)
        if "登录" in html[:2000] and "注册" in html[:2000]:
            return {"valid": False, "message": "Cookie 已过期，请在设置页面更新"}
        if "检测到有异常请求" in html:
            return {"valid": False, "message": "Cookie 触发反爬机制"}
        return {"valid": True, "message": "Cookie 有效"}
    except Exception as e:
        return {"valid": False, "message": f"Cookie 验证失败: {e}"}


def _clean_summary(text: str) -> str:
    """Clean up synopsis text: normalize whitespace and indentation."""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        # Remove leading/trailing whitespace and fullwidth spaces
        line = line.replace("　", " ").strip()
        if line:
            cleaned.append(line)
    return "\n".join(cleaned)


def _save_info_field(info: dict, key: str, val: str):
    """Save a parsed info field."""
    val = val.strip().rstrip("/").strip()
    if key == "导演":
        info["director"] = val
    elif key == "主演":
        info["cast_members"] = [v.strip() for v in val.split("/")[:5]]
    elif key == "类型":
        info["genre"] = val.replace(" / ", " ").replace("/", " ").strip()
    elif key == "制片国家/地区":
        info["country"] = val
    elif key == "上映日期":
        m = re.search(r"(\d{4})", val)
        if m:
            info["year"] = int(m.group(1))


def parse_detail_page(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    info = {}

    info_div = soup.select_one("#info")
    if info_div:
        # Two formats:
        # 1. <span>导演:弗兰克·德拉邦特</span> (key:value in same span)
        # 2. <span class="pl">类型:</span><span>剧情</span> (key and value in separate spans)

        for child in info_div.children:
            if not hasattr(child, 'get_text'):
                continue

            text = child.get_text(strip=True)

            # Format 1: key:value in same span
            if ":" in text or "：" in text:
                sep = ":" if ":" in text else "："
                key, _, val = text.partition(sep)
                key = key.strip()
                val = val.strip()
                if key and val:
                    _save_info_field(info, key, val)

        # Format 2: span.pl keys with separate value spans
        current_key = None
        current_val_parts = []

        for child in info_div.children:
            if not hasattr(child, 'get_text'):
                continue

            classes = child.get('class', []) if hasattr(child, 'get') else []
            text = child.get_text(strip=True)

            if 'pl' in classes:
                # Save previous
                if current_key and current_val_parts:
                    _save_info_field(info, current_key, " ".join(current_val_parts))
                current_key = text.rstrip(':').strip()
                current_val_parts = []
            elif text and text != '/' and current_key:
                current_val_parts.append(text)

        # Save last
        if current_key and current_val_parts:
            _save_info_field(info, current_key, " ".join(current_val_parts))

    # Year fallback
    if "year" not in info:
        year_span = soup.select_one("span.year")
        if year_span:
            m = re.search(r"(\d{4})", year_span.text)
            if m:
                info["year"] = int(m.group(1))

    quote_el = soup.select_one("span.inq")
    if quote_el:
        info["tagline"] = quote_el.text.strip()

    # Douban URL
    og_url = soup.select_one("meta[property='og:url']")
    if og_url:
        info["douban_url"] = og_url.get("content", "")

    summary_el = soup.select_one("span[property='v:summary']")
    if summary_el:
        text = _clean_summary(summary_el.text)
        if text:
            info["summary"] = text
    else:
        summary_div = soup.select_one("#link-report-intra")
        if summary_div:
            text = _clean_summary(summary_div.text)
            if text:
                info["summary"] = text

    poster = soup.select_one("#mainpic img")
    if poster:
        info["poster_url"] = poster.get("src", "")

    return info


def _needs_metadata(movie: Movie, force: bool = False) -> bool:
    """Check if a movie needs metadata. Required fields must be present."""
    return (
        not movie.director
        or not movie.genre
        or not movie.country
        or not movie.summary
        or not movie.poster_path
        or not movie.douban_url
    )


def run_backfill(force: bool = False) -> dict:
    """Fetch missing metadata for all movies that need it."""
    db = SessionLocal()
    log = CrawlLog(
        job_type="metadata",
        status="running",
        started_at=now(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    try:
        total_movies = db.query(Movie).count()
        if force:
            to_fetch = db.query(Movie).all()
        else:
            to_fetch = db.query(Movie).filter(_needs_metadata_query()).all()

        meta_progress.update({
            "active": True,
            "total": len(to_fetch),
            "done": 0,
            "updated": 0,
            "failed": 0,
            "current_movie": "",
            "message": f"开始补全 {len(to_fetch)} 部电影的元数据...",
        })

        logger.info(f"Metadata backfill: {len(to_fetch)}/{total_movies} movies need data")

        for idx, movie in enumerate(to_fetch):
            meta_progress.update({
                "done": idx + 1,
                "current_movie": movie.title,
                "message": f"正在处理 {idx + 1}/{len(to_fetch)}: {movie.title}",
            })
            logger.info(f"[{idx + 1}/{len(to_fetch)}] {movie.title} ({movie.douban_id})")

            try:
                url = f"https://movie.douban.com/subject/{movie.douban_id}/"
                html = fetch_page(url)
                info = parse_detail_page(html)

                updated = False
                for field in ["director", "genre", "country", "year", "tagline", "summary", "douban_url"]:
                    if info.get(field) and not getattr(movie, field):
                        setattr(movie, field, info[field])
                        updated = True

                if info.get("cast_members") and not movie.cast_members:
                    movie.cast_members = info["cast_members"]
                    updated = True

                if not movie.poster_path and info.get("poster_url"):
                    try:
                        fn = f"{movie.douban_id}.jpg"
                        fp = settings.posters_dir / fn
                        if not fp.exists():
                            fp.write_bytes(fetch_binary(info["poster_url"]))
                        movie.poster_path = fn
                        updated = True
                    except Exception:
                        pass

                # Only mark detail_fetched when all required fields are present
                if movie.director and movie.genre and movie.country and movie.summary and movie.poster_path and movie.douban_url:
                    movie.detail_fetched = True
                movie.updated_at = now()
                meta_progress["updated"] += 1

            except Exception as e:
                logger.warning(f"  Failed: {e}")
                meta_progress["failed"] += 1

            if (idx + 1) % 10 == 0:
                db.commit()

        db.commit()

        log.status = "success"
        log.finished_at = now()
        log.movies_found = meta_progress["updated"]
        db.commit()

        result = {
            "success": True,
            "total": len(to_fetch),
            "updated": meta_progress["updated"],
            "failed": meta_progress["failed"],
        }
        meta_progress.update({"active": False, "message": f"完成：更新 {meta_progress['updated']} 部，失败 {meta_progress['failed']} 部"})
        logger.info(f"Metadata backfill done: {result}")
        return result

    except Exception as e:
        logger.error(f"Metadata backfill failed: {e}")
        log.status = "failed"
        log.finished_at = now()
        log.error_message = str(e)
        db.commit()
        meta_progress.update({"active": False, "message": f"失败: {e}"})
        return {"success": False, "error": str(e)}
    finally:
        db.close()
