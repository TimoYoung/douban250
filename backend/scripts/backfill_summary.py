"""Backfill synopsis (简介) for all movies missing it."""
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bs4 import BeautifulSoup
from app.utils.http_client import fetch_page
from app.database import SessionLocal, init_db
from app.models import Movie
from app.utils import now


def parse_synopsis(html: str) -> str | None:
    """Extract synopsis from a Douban movie detail page."""
    soup = BeautifulSoup(html, "html.parser")

    # Primary: span[property='v:summary']
    el = soup.select_one("span[property='v:summary']")
    if el:
        text = el.text.strip()
        if text:
            return text

    # Fallback: hidden div
    el = soup.select_one("#link-report-intra")
    if el:
        text = el.text.strip()
        if text:
            return text

    # Fallback: look for "剧情简介" section
    for header in soup.select("h2, .pl"):
        if "简介" in header.text or "剧情" in header.text:
            sib = header.find_next_sibling()
            if sib:
                text = sib.text.strip()
                if text:
                    return text

    return None


def main():
    init_db()
    db = SessionLocal()
    try:
        movies = db.query(Movie).filter(
            (Movie.summary.is_(None)) | (Movie.summary == "")
        ).all()

        print(f"Movies needing synopsis: {len(movies)}")

        for idx, movie in enumerate(movies):
            print(f"[{idx + 1}/{len(movies)}] {movie.title} ({movie.douban_id})", end="")

            try:
                url = f"https://movie.douban.com/subject/{movie.douban_id}/"
                html = fetch_page(url)
                synopsis = parse_synopsis(html)

                if synopsis:
                    movie.summary = synopsis
                    print(f" OK ({len(synopsis)} chars)")
                else:
                    print(" NOT FOUND")

            except Exception as e:
                print(f" FAILED: {e}")

            if (idx + 1) % 20 == 0:
                db.commit()
                print(f"  [committed {idx + 1}]")

        db.commit()
        print(f"\nDone! {len(movies)} movies processed.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
