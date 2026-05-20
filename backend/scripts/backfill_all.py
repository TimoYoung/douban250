"""
Backfill ALL missing metadata for all movies: director, genre, country, cast, summary, tagline, poster.
"""
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bs4 import BeautifulSoup
from app.utils.http_client import fetch_page, fetch_binary
from app.config import settings
from app.database import SessionLocal, init_db
from app.models import Movie
from app.utils import now


def parse_detail_page(html: str) -> dict:
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

    # Year fallback
    if "year" not in info:
        year_span = soup.select_one("span.year")
        if year_span:
            m = re.search(r"(\d{4})", year_span.text)
            if m:
                info["year"] = int(m.group(1))

    # Tagline (短评)
    tagline_el = soup.select_one("#content h1 span:last-child")
    if not tagline_el:
        tagline_el = soup.select_one("span[property='v:alternative']")
    # The tagline is usually in the quote section
    quote_el = soup.select_one("span.inq")
    if quote_el:
        info["tagline"] = quote_el.text.strip()

    # Synopsis (简介)
    summary_el = soup.select_one("span[property='v:summary']")
    if summary_el:
        text = summary_el.text.strip()
        if text:
            info["summary"] = text
    else:
        summary_div = soup.select_one("#link-report-intra")
        if summary_div:
            text = summary_div.text.strip()
            if text:
                info["summary"] = text

    # Poster
    poster = soup.select_one("#mainpic img")
    if poster:
        info["poster_url"] = poster.get("src", "")

    return info


def needs_fetch(movie: Movie) -> bool:
    """Check if a movie needs any metadata fetched."""
    return (
        not movie.director
        or not movie.genre
        or not movie.country
        or not movie.summary
        or not movie.cast_members
        or not movie.poster_path
    )


def main():
    init_db()
    db = SessionLocal()
    try:
        movies = db.query(Movie).all()
        to_fetch = [m for m in movies if needs_fetch(m)]

        print(f"Total movies: {len(movies)}")
        print(f"Need metadata: {len(to_fetch)}")

        success = 0
        failed = 0

        for idx, movie in enumerate(to_fetch):
            missing = []
            if not movie.director: missing.append("director")
            if not movie.genre: missing.append("genre")
            if not movie.country: missing.append("country")
            if not movie.summary: missing.append("summary")
            if not movie.cast_members: missing.append("cast")
            if not movie.poster_path: missing.append("poster")

            print(f"[{idx + 1}/{len(to_fetch)}] {movie.title} ({movie.douban_id}) missing: {', '.join(missing)}", end="")

            try:
                url = f"https://movie.douban.com/subject/{movie.douban_id}/"
                html = fetch_page(url)
                info = parse_detail_page(html)

                updated = False
                if info.get("director") and not movie.director:
                    movie.director = info["director"]
                    updated = True
                if info.get("genre") and not movie.genre:
                    movie.genre = info["genre"]
                    updated = True
                if info.get("country") and not movie.country:
                    movie.country = info["country"]
                    updated = True
                if info.get("cast_members") and not movie.cast_members:
                    movie.cast_members = info["cast_members"]
                    updated = True
                if info.get("year") and not movie.year:
                    movie.year = info["year"]
                    updated = True
                if info.get("tagline") and not movie.tagline:
                    movie.tagline = info["tagline"]
                    updated = True
                if info.get("summary") and not movie.summary:
                    movie.summary = info["summary"]
                    updated = True

                # Poster
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

                if updated:
                    movie.updated_at = now()
                    success += 1
                    print(" OK")
                else:
                    print(" NO DATA")

            except Exception as e:
                failed += 1
                print(f" FAIL: {e}")

            if (idx + 1) % 20 == 0:
                db.commit()
                print(f"  [committed {idx + 1}]")

        db.commit()
        print(f"\nDone! Updated: {success}, Failed: {failed}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
