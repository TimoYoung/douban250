import re
from bs4 import BeautifulSoup


def parse_top250_page(html: str) -> list[dict]:
    """Parse a Top 250 listing page and extract movie info."""
    soup = BeautifulSoup(html, "html.parser")
    movies = []

    for item in soup.select("ol.grid_view li"):
        movie = {}

        # Rank
        rank_span = item.select_one("em")
        if rank_span:
            movie["rank"] = int(rank_span.text.strip())

        # Title
        title_span = item.select_one("span.title")
        if title_span:
            movie["title"] = title_span.text.strip()

        # Alternative title (English)
        alt_spans = item.select("span.title")
        if len(alt_spans) > 1:
            movie["original_title"] = alt_spans[1].text.strip().strip("/ ")

        # Link and douban_id
        link = item.select_one("div.hd a")
        if link:
            href = link.get("href", "")
            movie["douban_url"] = href
            match = re.search(r"/subject/(\d+)/", href)
            if match:
                movie["douban_id"] = match.group(1)

        # Rating
        rating_span = item.select_one("span.rating_num")
        if rating_span:
            try:
                movie["rating"] = float(rating_span.text.strip())
            except ValueError:
                pass

        # Rating count
        rating_count_span = item.select_one("div.star span:last-child")
        if rating_count_span:
            count_text = rating_count_span.text.strip().replace("人评价", "")
            if count_text.isdigit():
                movie["rating_count"] = int(count_text)

        # Info line: year / country / genre
        info_div = item.select_one("div.bd p")
        if info_div:
            lines = [l.strip() for l in info_div.get_text("\n").split("\n") if l.strip()]
            if len(lines) >= 2:
                # First line: director / cast
                info_line = lines[0]
                parts = info_line.split("主演:")
                director_part = parts[0].replace("导演:", "").strip().rstrip("/")
                movie["director"] = director_part
                if len(parts) > 1:
                    cast_text = parts[1].strip().rstrip("/")
                    movie["cast_members"] = [c.strip() for c in cast_text.split(",") if c.strip()]

                # Second line: year / country / genre
                if len(lines) >= 2:
                    meta_parts = [p.strip() for p in lines[1].split("/")]
                    if meta_parts:
                        try:
                            movie["year"] = int(meta_parts[0])
                        except ValueError:
                            pass
                        if len(meta_parts) >= 2:
                            movie["country"] = meta_parts[1]
                        if len(meta_parts) >= 3:
                            movie["genre"] = meta_parts[2]

        # Tagline / quote
        quote_span = item.select_one("span.inq")
        if quote_span:
            movie["tagline"] = quote_span.text.strip()

        # Poster URL
        poster_img = item.select_one("div.pic img")
        if poster_img:
            movie["poster_url"] = poster_img.get("src", "")

        if movie.get("douban_id"):
            movies.append(movie)

    return movies


def parse_watched_page(html: str) -> tuple[list[dict], int]:
    """Parse a user's watched/collection page. Returns (movies, total_count)."""
    soup = BeautifulSoup(html, "html.parser")
    movies = []

    # Get total count from page header, e.g. "看过的影视(1027)"
    total_count = 0
    h1 = soup.select_one("div.info h1")
    if h1:
        match = re.search(r"\((\d+)\)", h1.text)
        if match:
            total_count = int(match.group(1))

    for item in soup.select("div.item"):
        movie = {}

        # Link and douban_id
        link = item.select_one("div.info li.title a")
        if not link:
            link = item.select_one("a.nbg")
        if link:
            href = link.get("href", "")
            movie["douban_url"] = href
            match = re.search(r"/subject/(\d+)/", href)
            if match:
                movie["douban_id"] = match.group(1)

        # Title
        title_link = item.select_one("div.info li.title a")
        if title_link:
            title_text = title_link.get_text(strip=True)
            movie["title"] = title_text.split("/")[0].strip()

        # Rating
        rating_span = item.select_one("span.rating_nums")
        if rating_span and rating_span.text.strip():
            try:
                movie["rating"] = float(rating_span.text.strip())
            except ValueError:
                pass

        # Date watched
        date_span = item.select_one("span.date")
        if date_span:
            movie["watched_date"] = date_span.text.strip()

        # Comment
        comment_span = item.select_one("span.comment")
        if comment_span:
            movie["user_comment"] = comment_span.text.strip()

        if movie.get("douban_id"):
            movies.append(movie)

    return movies, total_count
