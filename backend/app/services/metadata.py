"""
Metadata backfill service: periodically fetch missing metadata for all movies.
"""
import logging
import random
import re
import time
from datetime import timedelta

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

    Selects movies with missing fields that haven't been fetched recently
    (within 7 days). Successfully fetched movies are skipped even if some
    fields are empty — that means the source genuinely has no data for them.
    """
    cutoff = now() - timedelta(days=7)
    return or_(
        # 缺少字段且从未获取过，或距上次获取超过 7 天
        (
            (
                or_(Movie.director.is_(None), Movie.director == "") |
                or_(Movie.genre.is_(None), Movie.genre == "") |
                or_(Movie.country.is_(None), Movie.country == "") |
                or_(Movie.summary.is_(None), Movie.summary == "") |
                or_(Movie.poster_path.is_(None), Movie.poster_path == "") |
                or_(Movie.douban_url.is_(None), Movie.douban_url == "") |
                Movie.rating.is_(None) |
                Movie.rating_count.is_(None)
            ) &
            (Movie.last_meta_fetch.is_(None) | (Movie.last_meta_fetch < cutoff))
        ),
        # 有 douban_id 但缺少 imdb_id 且未标记已获取
        (Movie.douban_id.isnot(None) & Movie.imdb_id.is_(None) & Movie.detail_fetched.isnot(True))
    )


def check_cookie_valid(cookie: str = "") -> dict:
    """Check if the Douban cookie is still valid. Returns {valid, message}."""
    if not cookie:
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

    # 从 <title> 标签提取干净中文标题（格式: "中文名 (豆瓣)"）
    head_title = soup.find("title")
    if head_title:
        t = head_title.get_text(strip=True)
        # 去掉末尾 " (豆瓣)" 或 " 电影 (豆瓣)" 等后缀
        t = re.sub(r'\s*(?:电影|电视剧|综艺|纪录片)?\s*\(豆瓣\)\s*$', '', t).strip()
        if t:
            info["title"] = t

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

    # Rating
    rating_el = soup.select_one('strong.rating_num[property="v:average"]')
    if rating_el:
        try:
            r = float(rating_el.text.strip())
            if r > 0:
                info["rating"] = r
        except (ValueError, TypeError):
            pass

    # Rating count
    votes_el = soup.select_one('span[property="v:votes"]')
    if votes_el:
        try:
            info["rating_count"] = int(votes_el.text.strip())
        except (ValueError, TypeError):
            pass

    # Extract IMDb ID from #info section
    info_div_for_imdb = soup.select_one("#info")
    if info_div_for_imdb:
        # Look for IMDb link: <a href="https://www.imdb.com/title/tt.../">...</a>
        imdb_link = info_div_for_imdb.select_one('a[href*="imdb.com/title/"]')
        if imdb_link:
            href = imdb_link.get("href", "")
            m = re.search(r"(tt\d+)", href)
            if m:
                info["imdb_id"] = m.group(1)
        # Fallback: look for text pattern "IMDb: tt..." or "IMDb链接: tt..."
        if "imdb_id" not in info:
            text = info_div_for_imdb.get_text()
            m = re.search(r"IMDb[:\s：]*(tt\d+)", text, re.IGNORECASE)
            if m:
                info["imdb_id"] = m.group(1)

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


def run_backfill(force: bool = False, mode: str = "incremental") -> dict:
    """Fetch missing metadata for all movies that need it.

    mode:
      - 'incremental': only fetch movies with missing fields (default)
      - 'full': refetch all movies, always update title/rating/rating_count
    """
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
        if mode == "full":
            to_fetch = db.query(Movie).filter(
                Movie.douban_id.isnot(None),
                Movie.douban_id != "",
            ).all()
            # 过滤掉非数字 douban_id
            to_fetch = [m for m in to_fetch if m.douban_id and m.douban_id.isdigit()]
        elif force:
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
            "message": f"开始{'全量覆盖' if mode == 'full' else '补全'} {len(to_fetch)} 部电影的元数据...",
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
                # Skip movies with non-numeric douban_id (e.g. placeholders)
                if movie.douban_id and not movie.douban_id.isdigit():
                    logger.info(f"  Skipping (non-numeric douban_id: {movie.douban_id})")
                    movie.last_meta_fetch = now()  # 标记已处理，避免重复选中
                    meta_progress["failed"] += 1
                    continue

                url = f"https://movie.douban.com/subject/{movie.douban_id}/"
                html = fetch_page(url)
                info = parse_detail_page(html)

                updated = False

                # 标题：详情页标题始终为准（修正 abstract API 拼接格式）
                if info.get("title") and info["title"] != movie.title:
                    movie.title = info["title"]
                    updated = True

                # 评分和打分人数：full 模式下始终覆盖
                for field in ["rating", "rating_count"]:
                    val = info.get(field)
                    if val and (mode == "full" or not getattr(movie, field)):
                        if getattr(movie, field) != val:
                            setattr(movie, field, val)
                            updated = True

                # 其他字段：仅填充空值
                for field in ["director", "genre", "country", "year", "tagline", "summary", "douban_url"]:
                    if info.get(field) and not getattr(movie, field):
                        setattr(movie, field, info[field])
                        updated = True

                if info.get("cast_members") and not movie.cast_members:
                    movie.cast_members = info["cast_members"]
                    updated = True

                if info.get("imdb_id") and not movie.imdb_id:
                    movie.imdb_id = info["imdb_id"]
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

                # 成功获取页面后标记时间戳，无论是否所有字段都有值
                # 空字段视为来源确实没有该数据，7 天内不重试
                movie.last_meta_fetch = now()
                if updated and not movie.detail_fetched:
                    movie.detail_fetched = True
                movie.updated_at = now()
                meta_progress["updated"] += 1

            except RuntimeError as e:
                logger.warning(f"  反爬封锁: {e}")
                meta_progress["failed"] += 1
                # 被封锁后长冷却，避免持续触发
                cooldown = 30 + random.random() * 30
                logger.info(f"  冷却 {cooldown:.0f}s 后继续...")
                time.sleep(cooldown)
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
