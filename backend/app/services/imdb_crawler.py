"""
IMDb Top 250 爬虫。

使用 Playwright 绕过 IMDb 的 AWS WAF 防护，获取 Top 250 排名数据。
匹配已有 Movie 记录（通过 imdb_id 或 title+year），未匹配的创建新记录。
创建 source='imdb' 的 Version + VersionEntry。
"""

import re
import time
import random
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Movie, Version, VersionEntry
from app.utils import now

logger = logging.getLogger(__name__)

# 进度跟踪
_imdb_progress = {
    "status": "idle",
    "phase": "",
    "current": 0,
    "total": 250,
    "message": "",
    "matched": 0,
    "created": 0,
    "skipped": 0,
}


def get_imdb_progress() -> dict:
    return dict(_imdb_progress)


def _reset_imdb_progress():
    _imdb_progress.update({
        "status": "idle", "phase": "", "current": 0, "total": 250,
        "message": "", "matched": 0, "created": 0, "skipped": 0,
    })


def _update_progress(**kwargs):
    _imdb_progress.update(kwargs)


def fetch_imdb_top250() -> list[dict]:
    """使用 Playwright 爬取 IMDb Top 250 页面，返回电影列表。"""
    import json
    from playwright.sync_api import sync_playwright

    movies = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="en-US",
        )
        page = context.new_page()

        logger.info("Fetching IMDb Top 250...")
        page.goto("https://www.imdb.com/chart/top/", wait_until="domcontentloaded", timeout=60000)

        # 等待页面加载（WAF 挑战通常几秒内完成）
        page.wait_for_timeout(5000)

        # 等待电影列表出现
        try:
            page.wait_for_selector("li.ipc-metadata-list-summary-item", timeout=30000)
        except Exception:
            page.wait_for_timeout(10000)
            page.wait_for_selector("li.ipc-metadata-list-summary-item", timeout=30000)

        # 从 __NEXT_DATA__ 提取结构化数据（最可靠）
        next_data_raw = page.evaluate("""
            () => {
                const el = document.querySelector('script#__NEXT_DATA__');
                return el ? el.textContent : null;
            }
        """)

        if next_data_raw:
            data = json.loads(next_data_raw)
            edges = (data.get("props", {})
                         .get("pageProps", {})
                         .get("pageData", {})
                         .get("chartTitles", {})
                         .get("edges", []))

            for edge in edges:
                rank = edge.get("currentRank", 0)
                node = edge.get("node", {})
                title_info = node.get("titleText", {})
                release_year = node.get("releaseYear", {})
                ratings = node.get("ratingsSummary", {})

                movies.append({
                    "rank": rank,
                    "title": title_info.get("text", ""),
                    "imdb_id": node.get("id", ""),
                    "rating": float(ratings.get("aggregateRating", 0) or 0),
                    "year": release_year.get("year", 0) or 0,
                })

        # 降级方案：从 JSON-LD 提取
        if not movies:
            ld_json = page.evaluate("""
                () => {
                    const el = document.querySelector('script[type="application/ld+json"]');
                    return el ? el.textContent : null;
                }
            """)
            if ld_json:
                ld_data = json.loads(ld_json)
                items = ld_data.get("itemListElement", [])
                for i, item in enumerate(items):
                    item_data = item.get("item", {})
                    url = item_data.get("url", "")
                    imdb_id_match = re.search(r"/title/(tt\d+)/", url)
                    movies.append({
                        "rank": i + 1,
                        "title": item_data.get("name", ""),
                        "imdb_id": imdb_id_match.group(1) if imdb_id_match else "",
                        "rating": float(item_data.get("aggregateRating", {}).get("ratingValue", 0)),
                        "year": _extract_year(item_data.get("datePublished", "")),
                    })

        # 降级方案：从 DOM 解析
        if not movies:
            dom_movies = page.evaluate("""
                () => {
                    const items = document.querySelectorAll('li.ipc-metadata-list-summary-item');
                    return Array.from(items).map((el, i) => {
                        const titleEl = el.querySelector('h3.ipc-title__text');
                        const linkEl = el.querySelector('a[href*="/title/"]');
                        const ratingEl = el.querySelector('.ipc-rating-star--rating');
                        const text = el.textContent || '';
                        const yearMatch = text.match(/\\b(19\\d{2}|20\\d{2})\\b/);

                        let title = titleEl ? titleEl.textContent.trim().replace(/^\\d+\\.\\s*/, '') : '';
                        const href = linkEl ? linkEl.getAttribute('href') : '';
                        const idMatch = href.match(/\\/title\\/(tt\\d+)/);

                        return {
                            rank: i + 1,
                            title,
                            imdb_id: idMatch ? idMatch[1] : '',
                            rating: ratingEl ? parseFloat(ratingEl.textContent) : 0,
                            year: yearMatch ? parseInt(yearMatch[1]) : 0,
                        };
                    });
                }
            """)
            movies = dom_movies

        browser.close()

    logger.info(f"Fetched {len(movies)} movies from IMDb Top 250")
    return movies


def _extract_year(date_str: str) -> int:
    if not date_str:
        return 0
    match = re.search(r"(\d{4})", date_str)
    return int(match.group(1)) if match else 0


def _normalize_title(title: str) -> str:
    """标准化标题用于匹配。"""
    title = title.strip()
    title = title.replace("：", ":").replace("，", ",").replace("、", ",")
    title = re.sub(r"\s+", "", title)
    return title.lower()


def _find_matching_movie(db: Session, movie_data: dict) -> Movie | None:
    """在数据库中查找匹配的电影。优先 imdb_id，其次 title+year。"""
    imdb_id = movie_data.get("imdb_id", "")

    # 1. 按 imdb_id 精确匹配
    if imdb_id:
        movie = db.query(Movie).filter(Movie.imdb_id == imdb_id).first()
        if movie:
            return movie

    # 2. 按 title + year 匹配
    title = movie_data.get("title", "")
    year = movie_data.get("year", 0)
    if not title:
        return None

    norm_title = _normalize_title(title)

    # 精确 title 匹配
    candidates = db.query(Movie).filter(
        Movie.year == year,
    ).all()

    for movie in candidates:
        movie_titles = [_normalize_title(movie.title)]
        if movie.original_title:
            movie_titles.append(_normalize_title(movie.original_title))

        for mt in movie_titles:
            if not mt:
                continue
            # 完全匹配
            if norm_title == mt:
                return movie
            # 子串匹配（长度比 >= 0.7）
            min_len = min(len(norm_title), len(mt))
            max_len = max(len(norm_title), len(mt))
            if max_len > 0 and min_len / max_len >= 0.7:
                if norm_title in mt or mt in norm_title:
                    return movie

    # 容忍 1 年偏差
    if year > 0:
        for dy in [-1, 1]:
            candidates = db.query(Movie).filter(Movie.year == year + dy).all()
            for movie in candidates:
                movie_titles = [_normalize_title(movie.title)]
                if movie.original_title:
                    movie_titles.append(_normalize_title(movie.original_title))
                for mt in movie_titles:
                    if norm_title == mt:
                        return movie

    return None


def crawl_imdb_top250(db_factory) -> dict:
    """爬取 IMDb Top 250 并创建版本。"""
    _reset_imdb_progress()
    _update_progress(status="running", phase="fetching", message="正在爬取 IMDb Top 250...")

    try:
        # Phase 1: 获取数据
        movies_data = fetch_imdb_top250()
        if not movies_data:
            _update_progress(status="error", message="未获取到任何电影数据")
            return _imdb_progress

        _update_progress(total=len(movies_data), message=f"获取到 {len(movies_data)} 部电影，开始匹配...")

        # Phase 2: 匹配和创建电影
        db = db_factory()
        try:
            matched_movies = []  # (rank, movie_id, rating)
            _update_progress(phase="matching")

            for i, mdata in enumerate(movies_data):
                _update_progress(current=i + 1)
                rank = mdata.get("rank", i + 1)

                movie = _find_matching_movie(db, mdata)

                if movie:
                    # 匹配到已有电影，补充 imdb_id
                    if mdata.get("imdb_id") and not movie.imdb_id:
                        movie.imdb_id = mdata["imdb_id"]
                    matched_movies.append((rank, movie.id, mdata.get("rating")))
                    _imdb_progress["matched"] += 1
                else:
                    # 创建新电影记录
                    new_movie = Movie(
                        imdb_id=mdata.get("imdb_id", ""),
                        title=mdata.get("title", ""),
                        year=mdata.get("year"),
                        rating=mdata.get("rating"),
                    )
                    db.add(new_movie)
                    db.flush()
                    matched_movies.append((rank, new_movie.id, mdata.get("rating")))
                    _imdb_progress["created"] += 1
                    logger.info(f"Created new movie: {mdata.get('title')} (imdb_id={mdata.get('imdb_id')})")

            db.commit()

            # Phase 3: 创建版本
            _update_progress(phase="creating_version", message="创建版本...")
            tag = now().strftime("%Y-%m-%d")

            # 检查是否已有同日版本
            suffix = 1
            base_tag = tag
            while db.query(Version).filter(Version.tag == tag).first():
                suffix += 1
                tag = f"{base_tag}-{suffix}"

            version = Version(
                tag=tag,
                source="imdb",
                crawled_at=now(),
                movie_count=len(matched_movies),
            )
            db.add(version)
            db.flush()

            entries = []
            for rank, movie_id, rating in matched_movies:
                entries.append(VersionEntry(
                    version_id=version.id,
                    movie_id=movie_id,
                    rank=rank,
                    rating=rating,
                ))

            db.add_all(entries)
            db.commit()

            _update_progress(
                status="done",
                phase="done",
                message=f"完成！版本 {tag}：{len(matched_movies)} 部电影，"
                        f"匹配 {_imdb_progress['matched']}，新建 {_imdb_progress['created']}",
            )

        finally:
            db.close()

    except Exception as e:
        logger.exception("IMDb crawl failed")
        _update_progress(status="error", message=f"爬取失败: {e}")

    return _imdb_progress
