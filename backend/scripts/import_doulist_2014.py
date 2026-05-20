"""
Import douban doulist 3936288 as version 2014-04-14,
then supplement metadata for all movies missing it.
"""
import re
import sys
import os
import logging
import time as time_module

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bs4 import BeautifulSoup
from app.utils.http_client import fetch_page, fetch_binary
from app.config import settings
from app.database import SessionLocal, init_db
from app.models import Movie, Version, VersionEntry
from app.utils import now

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

DOULIST_URL = "https://www.douban.com/doulist/3936288/?start={start}&sort=time&playable=0&sub_type="
VERSION_TAG = "2014-04-14"


def scrape_doulist() -> list[dict]:
    all_movies = []
    for page_idx in range(10):
        start = page_idx * 25
        url = DOULIST_URL.format(start=start)
        logger.info(f"Fetching page {page_idx + 1}/10 (start={start})...")
        html = fetch_page(url)
        soup = BeautifulSoup(html, "html.parser")
        items = soup.select(".doulist-item")
        logger.info(f"  Got {len(items)} items")

        for item in items:
            movie = {}
            pos = item.select_one(".pos")
            if pos:
                try:
                    movie["rank"] = int(pos.text.strip())
                except ValueError:
                    pass

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

            rating_el = item.select_one(".rating_nums")
            if rating_el:
                try:
                    movie["rating"] = float(rating_el.text.strip())
                except ValueError:
                    pass

            img = item.select_one(".doulist-post img")
            if img:
                movie["poster_url"] = img.get("src", "")

            if movie.get("douban_id"):
                all_movies.append(movie)

    logger.info(f"Total movies scraped: {len(all_movies)}")

    # Ensure all movies have sequential ranks
    for i, movie in enumerate(all_movies):
        if not movie.get("rank"):
            movie["rank"] = i + 1

    return all_movies


def save_doulist(movies: list[dict]):
    db = SessionLocal()
    try:
        existing = db.query(Version).filter(Version.tag == VERSION_TAG).first()
        if existing:
            logger.info(f"Version '{VERSION_TAG}' exists, deleting...")
            db.query(VersionEntry).filter(VersionEntry.version_id == existing.id).delete()
            db.delete(existing)
            db.commit()

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

        # Download posters
        for idx, data in enumerate(movies):
            movie = movie_map[data["douban_id"]]
            if movie.poster_path:
                continue
            poster_url = data.get("poster_url")
            if poster_url:
                try:
                    fn = f"{movie.douban_id}.jpg"
                    fp = settings.posters_dir / fn
                    if not fp.exists():
                        fp.write_bytes(fetch_binary(poster_url))
                    movie.poster_path = fn
                except Exception:
                    pass

        db.commit()

        version = Version(tag=VERSION_TAG, crawled_at=now(), movie_count=len(movies))
        db.add(version)
        db.flush()

        for data in movies:
            movie = movie_map[data["douban_id"]]
            db.add(VersionEntry(
                version_id=version.id,
                movie_id=movie.id,
                rank=data.get("rank", 0),
                rating=data.get("rating"),
            ))

        db.commit()
        logger.info(f"Version '{VERSION_TAG}' created: id={version.id}, {len(movies)} entries")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def parse_detail_page(html: str) -> dict:
    """Parse a movie detail page to extract metadata."""
    soup = BeautifulSoup(html, "html.parser")
    info = {}

    # Main info block
    info_div = soup.select_one("#info")
    if info_div:
        text = info_div.get_text("\n")
        for line in text.split("\n"):
            line = line.strip()
            if ":" in line or "：" in line:
                key, _, val = line.partition(":") if ":" in line else line.partition("：")
                key = key.strip()
                val = val.strip()
                if key == "导演":
                    info["director"] = val
                elif key == "编剧":
                    pass  # skip
                elif key == "主演":
                    info["cast_members"] = [v.strip() for v in val.split("/")[:5]]
                elif key == "类型":
                    info["genre"] = val.replace(" / ", " ").replace("/", " ").strip()
                elif key == "制片国家/地区":
                    info["country"] = val
                elif key == "语言":
                    pass
                elif key == "上映日期":
                    m = re.search(r"(\d{4})", val)
                    if m:
                        info["year"] = int(m.group(1))
                elif key == "片长":
                    pass
                elif key == "又名":
                    pass
                elif key == "IMDb":
                    pass

    # Year from title if not found
    if "year" not in info:
        year_span = soup.select_one("span.year")
        if year_span:
            m = re.search(r"(\d{4})", year_span.text)
            if m:
                info["year"] = int(m.group(1))

    # Tagline
    tagline = soup.select_one("span[property='v:summary']")
    if not tagline:
        tagline = soup.select_one(".related-info span")
    if tagline:
        t = tagline.text.strip()
        if t and len(t) < 200:
            info["tagline"] = t

    # Synopsis (简介)
    summary_el = soup.select_one("span[property='v:summary']")
    if summary_el:
        info["summary"] = summary_el.text.strip()
    else:
        # Fallback: look for the all hidden content div
        summary_div = soup.select_one("#link-report-intra")
        if summary_div:
            info["summary"] = summary_div.text.strip()

    # Poster
    poster = soup.select_one("#mainpic img")
    if poster:
        info["poster_url"] = poster.get("src", "")

    return info


def supplement_metadata():
    """Fetch metadata for movies missing it from both imported versions."""
    db = SessionLocal()
    try:
        # Find movies without metadata (no year, no director)
        movies = db.query(Movie).filter(
            (Movie.year.is_(None)) | (Movie.director.is_(None))
        ).all()

        logger.info(f"\nMovies needing metadata: {len(movies)}")

        for idx, movie in enumerate(movies):
            logger.info(f"[{idx + 1}/{len(movies)}] Fetching: {movie.title} ({movie.douban_id})")

            try:
                url = f"https://movie.douban.com/subject/{movie.douban_id}/"
                html = fetch_page(url)
                info = parse_detail_page(html)

                if info.get("year"):
                    movie.year = info["year"]
                if info.get("director"):
                    movie.director = info["director"]
                if info.get("country"):
                    movie.country = info["country"]
                if info.get("genre"):
                    movie.genre = info["genre"]
                if info.get("cast_members"):
                    movie.cast_members = info["cast_members"]
                if info.get("tagline") and not movie.tagline:
                    movie.tagline = info["tagline"]
                if info.get("summary") and not movie.summary:
                    movie.summary = info["summary"]

                # Download poster if missing
                if not movie.poster_path and info.get("poster_url"):
                    try:
                        fn = f"{movie.douban_id}.jpg"
                        fp = settings.posters_dir / fn
                        if not fp.exists():
                            fp.write_bytes(fetch_binary(info["poster_url"]))
                        movie.poster_path = fn
                    except Exception:
                        pass

                movie.updated_at = now()

            except Exception as e:
                logger.warning(f"  Failed: {e}")

            # Commit every 20 movies
            if (idx + 1) % 20 == 0:
                db.commit()
                logger.info(f"  Committed batch ({idx + 1})")

        db.commit()
        logger.info(f"Done! Metadata supplemented for {len(movies)} movies.")

    finally:
        db.close()


if __name__ == "__main__":
    init_db()

    logger.info("=== Step 1: Import doulist 3936288 as version 2014-04-14 ===")
    movies = scrape_doulist()
    if movies:
        save_doulist(movies)

    logger.info("\n=== Step 2: Supplement metadata for all imported movies ===")
    supplement_metadata()
