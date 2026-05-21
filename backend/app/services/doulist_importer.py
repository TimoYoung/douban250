import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Movie, Version, VersionEntry
from app.utils import now
from app.utils.http_client import fetch_page, fetch_binary

logger = logging.getLogger(__name__)

# In-memory progress state
doulist_import_progress = {
    "active": False,
    "phase": "",  # "fetching_pages", "saving_movies", "downloading_posters", "creating_version", "done"
    "page_current": 0,
    "page_total": 10,
    "movies_found": 0,
    "posters_done": 0,
    "posters_total": 0,
    "message": "",
    "success": False,
    "error": "",
}


def _reset_progress():
    doulist_import_progress.update({
        "active": True,
        "phase": "",
        "page_current": 0,
        "page_total": 10,
        "movies_found": 0,
        "posters_done": 0,
        "posters_total": 0,
        "message": "",
        "success": False,
        "error": "",
    })


def get_progress() -> dict:
    return dict(doulist_import_progress)


def _extract_doulist_id(url: str) -> str:
    """Extract doulist ID from a doulist URL."""
    m = re.search(r"/doulist/(\d+)", url)
    if not m:
        raise ValueError(f"无法从 URL 中提取 doulist ID: {url}")
    return m.group(1)


def scrape_doulist(url: str) -> list[dict]:
    """Scrape all movies from a doulist (up to 250, 10 pages of 25)."""
    doulist_id = _extract_doulist_id(url)
    base_url = f"https://www.douban.com/doulist/{doulist_id}/?start={{start}}&sort=seq&playable=0&sub_type="

    all_movies = []
    for page_idx in range(10):
        start = page_idx * 25
        page_url = base_url.format(start=start)
        doulist_import_progress.update({
            "page_current": page_idx + 1,
            "message": f"正在爬取第 {page_idx + 1}/10 页...",
        })
        logger.info(f"Fetching doulist page {page_idx + 1}/10 (start={start})")

        html = fetch_page(page_url)
        soup = BeautifulSoup(html, "html.parser")
        items = soup.select(".doulist-item")
        logger.info(f"  Got {len(items)} items")

        if not items:
            logger.info(f"  No more items at page {page_idx + 1}, stopping pagination")
            break

        for item in items:
            movie = {}

            # Rank
            pos = item.select_one(".pos")
            if pos:
                try:
                    movie["rank"] = int(pos.text.strip())
                except ValueError:
                    pass

            # Title and douban_id
            title_a = item.select_one(".title a")
            if not title_a:
                title_a = item.select_one("a[href*='/subject/']")
            if title_a:
                href = title_a.get("href", "")
                m = re.search(r"/subject/(\d+)", href)
                if m:
                    movie["douban_id"] = m.group(1)
                full_title = title_a.text.strip()
                movie["title"] = full_title.split("/")[0].strip().split(" ")[0]

            # Rating
            rating_el = item.select_one(".rating_nums")
            if rating_el:
                try:
                    movie["rating"] = float(rating_el.text.strip())
                except ValueError:
                    pass

            # Poster
            img = item.select_one(".doulist-post img")
            if img:
                movie["poster_url"] = img.get("src", "")

            if movie.get("douban_id"):
                all_movies.append(movie)

        doulist_import_progress["movies_found"] = len(all_movies)

    logger.info(f"Total movies scraped: {len(all_movies)}")
    return all_movies


def save_as_version(movies: list[dict], tag: str, db: Session):
    """Save movies to DB and create a version with the given tag."""
    # Check if version already exists — delete and recreate
    existing = db.query(Version).filter(Version.tag == tag).first()
    if existing:
        logger.info(f"Version '{tag}' already exists (id={existing.id}), deleting old entries...")
        db.query(VersionEntry).filter(VersionEntry.version_id == existing.id).delete()
        db.delete(existing)
        db.commit()

    # Create/update movie records
    doulist_import_progress.update({"phase": "saving_movies", "message": "正在保存电影数据..."})
    movie_map = {}
    for data in movies:
        movie = db.query(Movie).filter(Movie.douban_id == data["douban_id"]).first()
        if not movie:
            movie = Movie(douban_id=data["douban_id"])
            db.add(movie)

        movie.title = data.get("title", movie.title)
        if data.get("rating"):
            movie.rating = data["rating"]
        db.flush()
        movie_map[data["douban_id"]] = movie

    db.commit()

    # Download posters
    movies_need_poster = [d for d in movies if movie_map[d["douban_id"]].poster_path is None and d.get("poster_url")]
    if movies_need_poster:
        doulist_import_progress.update({
            "phase": "downloading_posters",
            "posters_total": len(movies_need_poster),
            "posters_done": 0,
        })

        for idx, data in enumerate(movies_need_poster):
            doulist_import_progress["posters_done"] = idx + 1
            doulist_import_progress["message"] = f"正在下载海报 {idx + 1}/{len(movies_need_poster)}: {data.get('title', '')}"
            movie = movie_map[data["douban_id"]]
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

    # Create version
    doulist_import_progress.update({"phase": "creating_version", "message": "正在创建版本..."})
    version = Version(
        tag=tag,
        crawled_at=now(),
        movie_count=len(movies),
    )
    db.add(version)
    db.flush()

    for data in movies:
        movie = movie_map[data["douban_id"]]
        entry = VersionEntry(
            version_id=version.id,
            movie_id=movie.id,
            rank=data.get("rank", 0),
            rating=data.get("rating"),
        )
        db.add(entry)

    db.commit()
    logger.info(f"Created version '{tag}' (id={version.id}) with {len(movies)} entries")


def import_doulist(url: str, tag: str):
    """Main entry: scrape a doulist and save as a version. Runs in a background thread."""
    _reset_progress()
    db = SessionLocal()
    try:
        doulist_import_progress.update({"phase": "fetching_pages", "message": "正在爬取豆瓣列表..."})
        movies = scrape_doulist(url)

        if not movies:
            raise RuntimeError("未爬取到任何电影，请检查链接是否正确")

        save_as_version(movies, tag, db)
        doulist_import_progress.update({
            "phase": "done",
            "active": False,
            "success": True,
            "message": f"导入完成，共 {len(movies)} 部电影",
        })

    except Exception as e:
        logger.error(f"Doulist import failed: {e}")
        db.rollback()
        doulist_import_progress.update({
            "phase": "done",
            "active": False,
            "success": False,
            "error": str(e),
            "message": f"导入失败: {e}",
        })
    finally:
        db.close()
