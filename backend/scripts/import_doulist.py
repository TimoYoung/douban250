"""One-time script: import douban doulist 46283778 as version 2017-11-30."""
import re
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bs4 import BeautifulSoup
from app.utils.http_client import fetch_page, fetch_binary
from app.config import settings
from app.database import SessionLocal, init_db
from app.models import Movie, Version, VersionEntry

DOULIST_URL = "https://www.douban.com/doulist/46283778/?start={start}&sort=seq&playable=0&sub_type="
VERSION_TAG = "2017-11-30"


def scrape_doulist() -> list[dict]:
    """Scrape all 250 movies from the doulist."""
    all_movies = []
    for page_idx in range(10):  # 10 pages of 25
        start = page_idx * 25
        url = DOULIST_URL.format(start=start)
        print(f"Fetching page {page_idx + 1}/10 (start={start})...")
        html = fetch_page(url)
        soup = BeautifulSoup(html, "html.parser")
        items = soup.select(".doulist-item")
        print(f"  Got {len(items)} items")

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

    print(f"\nTotal movies scraped: {len(all_movies)}")
    return all_movies


def save_to_db(movies: list[dict]):
    """Save movies and create version."""
    db = SessionLocal()
    try:
        # Check if version already exists
        existing = db.query(Version).filter(Version.tag == VERSION_TAG).first()
        if existing:
            print(f"Version '{VERSION_TAG}' already exists (id={existing.id}), deleting old entries...")
            db.query(VersionEntry).filter(VersionEntry.version_id == existing.id).delete()
            db.delete(existing)
            db.commit()

        # Create/update movie records
        print("Saving movies...")
        movie_map = {}  # douban_id -> Movie object
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
        print("Downloading posters...")
        for idx, data in enumerate(movies):
            movie = movie_map[data["douban_id"]]
            if movie.poster_path:
                continue
            poster_url = data.get("poster_url")
            if poster_url:
                try:
                    poster_filename = f"{movie.douban_id}.jpg"
                    poster_full_path = settings.posters_dir / poster_filename
                    if not poster_full_path.exists():
                        content = fetch_binary(poster_url)
                        poster_full_path.write_bytes(content)
                    movie.poster_path = poster_filename
                except Exception as e:
                    print(f"  Poster failed for {movie.title}: {e}")
            if (idx + 1) % 50 == 0:
                print(f"  {idx + 1}/{len(movies)} posters done")

        db.commit()

        # Create version
        print(f"Creating version '{VERSION_TAG}'...")
        version = Version(
            tag=VERSION_TAG,
            crawled_at=__import__("datetime").datetime(2017, 11, 30),
            movie_count=len(movies),
        )
        db.add(version)
        db.flush()

        for data in movies:
            movie = movie_map[data["douban_id"]]
            rank = data.get("rank", 0)
            entry = VersionEntry(
                version_id=version.id,
                movie_id=movie.id,
                rank=rank,
                rating=data.get("rating"),
            )
            db.add(entry)

        db.commit()
        print(f"Done! Version id={version.id}, {len(movies)} entries created.")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    movies = scrape_doulist()
    if movies:
        save_to_db(movies)
    else:
        print("No movies scraped!")
