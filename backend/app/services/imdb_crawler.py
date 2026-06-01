"""
IMDb Top 250 爬虫。

使用 Playwright 绕过 IMDb 的 AWS WAF 防护，获取 Top 250 排名数据。
自动通过豆瓣 suggest API 关联豆瓣词条，获取中文标题。
"""

import re
import time
import random
import logging

import httpx
from sqlalchemy.orm import Session

from app.models import Movie, Version, VersionEntry
from app.utils import now

logger = logging.getLogger(__name__)

DOUBAN_COOKIE = (
    'bid=PDbGNyM0sBU; ll="118172"; '
    'dbcl2="166675383:4IjQDlj9Pzs"; ck=FbZ8; '
    'frodotk_db="491df9104b5bc9efdb59eb30e2135dcd"'
)

_imdb_progress = {
    "status": "idle", "phase": "", "current": 0, "total": 250,
    "message": "", "matched": 0, "created": 0, "douban_searched": 0,
}


def get_imdb_progress() -> dict:
    return dict(_imdb_progress)


def _reset_imdb_progress():
    _imdb_progress.update({
        "status": "idle", "phase": "", "current": 0, "total": 250,
        "message": "", "matched": 0, "created": 0, "douban_searched": 0,
    })


def _update_progress(**kwargs):
    _imdb_progress.update(kwargs)


# ── IMDb 数据获取 ──────────────────────────────────────────────


def fetch_imdb_top250() -> list[dict]:
    """使用 Playwright 爬取 IMDb Top 250 页面，返回电影列表。"""
    import json
    from playwright.sync_api import sync_playwright

    movies = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/131.0.0.0 Safari/537.36",
            locale="en-US",
        )
        page = context.new_page()

        logger.info("Fetching IMDb Top 250...")
        page.goto("https://www.imdb.com/chart/top/",
                  wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        try:
            page.wait_for_selector(
                "li.ipc-metadata-list-summary-item", timeout=30000)
        except Exception:
            page.wait_for_timeout(10000)
            page.wait_for_selector(
                "li.ipc-metadata-list-summary-item", timeout=30000)

        # 从 __NEXT_DATA__ 提取（最可靠）
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
                node = edge.get("node", {})
                movies.append({
                    "rank": edge.get("currentRank", 0),
                    "title": node.get("titleText", {}).get("text", ""),
                    "imdb_id": node.get("id", ""),
                    "rating": float(
                        node.get("ratingsSummary", {})
                            .get("aggregateRating", 0) or 0),
                    "year": node.get("releaseYear", {}).get("year", 0) or 0,
                })

        # 降级：JSON-LD
        if not movies:
            ld_json = page.evaluate("""
                () => {
                    const el = document.querySelector(
                        'script[type="application/ld+json"]');
                    return el ? el.textContent : null;
                }
            """)
            if ld_json:
                for i, item in enumerate(
                        json.loads(ld_json).get("itemListElement", [])):
                    d = item.get("item", {})
                    m = re.search(r"/title/(tt\d+)/", d.get("url", ""))
                    movies.append({
                        "rank": i + 1,
                        "title": d.get("name", ""),
                        "imdb_id": m.group(1) if m else "",
                        "rating": float(
                            d.get("aggregateRating", {})
                             .get("ratingValue", 0)),
                        "year": _extract_year(
                            d.get("datePublished", "")),
                    })

        # 降级：DOM
        if not movies:
            movies = page.evaluate("""
                () => {
                    const items = document.querySelectorAll(
                        'li.ipc-metadata-list-summary-item');
                    return Array.from(items).map((el, i) => {
                        const t = el.querySelector('h3.ipc-title__text');
                        const a = el.querySelector('a[href*="/title/"]');
                        const r = el.querySelector(
                            '.ipc-rating-star--rating');
                        const txt = el.textContent || '';
                        const ym = txt.match(/\\b(19\\d{2}|20\\d{2})\\b/);
                        let title = t ? t.textContent.trim()
                            .replace(/^\\d+\\.\\s*/, '') : '';
                        const href = a ? a.getAttribute('href') : '';
                        const im = href.match(/\\/title\\/(tt\\d+)/);
                        return {
                            rank: i + 1, title,
                            imdb_id: im ? im[1] : '',
                            rating: r ? parseFloat(r.textContent) : 0,
                            year: ym ? parseInt(ym[1]) : 0,
                        };
                    });
                }
            """)

        browser.close()

    logger.info(f"Fetched {len(movies)} movies from IMDb Top 250")
    return movies


def _extract_year(date_str: str) -> int:
    if not date_str:
        return 0
    m = re.search(r"(\d{4})", date_str)
    return int(m.group(1)) if m else 0


# ── 标题标准化与匹配 ────────────────────────────────────────────


def _normalize(title: str) -> str:
    t = title.strip().lower()
    t = (t.replace("：", ":").replace("，", ",").replace("、", ",")
           .replace(" ", "").replace("-", "").replace("'", "")
           .replace("'", "").replace("·", ""))
    return t


def _titles_match(a: str, b: str) -> bool:
    """模糊匹配两个标题（支持中英文）。"""
    na, nb = _normalize(a), _normalize(b)
    if na == nb:
        return True
    lo = min(len(na), len(nb))
    hi = max(len(na), len(nb))
    if hi > 0 and lo / hi >= 0.6:
        if na in nb or nb in na:
            return True
    common = len(set(na) & set(nb))
    total = max(len(set(na)), len(set(nb)))
    return total > 0 and common / total >= 0.8


def _has_chinese(text: str) -> bool:
    return bool(re.search(r'[一-鿿]', text))


# ── 豆瓣 API ────────────────────────────────────────────────────


def _get_douban_client() -> httpx.Client:
    return httpx.Client(
        headers={
            'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                           'AppleWebKit/537.36'),
            'Cookie': DOUBAN_COOKIE,
            'Referer': 'https://movie.douban.com/',
        },
        follow_redirects=True,
        timeout=20,
    )


def _douban_suggest(client: httpx.Client, query: str) -> list[dict]:
    """调用豆瓣 suggest API，返回 [{id, title, sub_title, year}]。"""
    try:
        resp = client.get(
            'https://movie.douban.com/j/subject_suggest',
            params={'q': query})
        if resp.status_code == 200:
            return [
                {'id': r['id'],
                 'title': r.get('title', ''),
                 'sub_title': r.get('sub_title', ''),
                 'year': r.get('year', '')}
                for r in resp.json()
                if r.get('type') == 'movie' and r.get('id')
            ]
    except Exception:
        pass
    return []


def _douban_verify(client: httpx.Client, douban_id: str) -> str | None:
    """通过 abstract API 验证 douban_id，返回 title 或 None。"""
    try:
        resp = client.get(
            f'https://movie.douban.com/j/subject_abstract'
            f'?subject_id={douban_id}')
        if resp.status_code == 200:
            t = resp.json().get('subject', {}).get('title', '')
            if t and t != '未知':
                return t
    except Exception:
        pass
    return None


def _search_douban_for_movie(
    client: httpx.Client, imdb_title: str, year: int
) -> dict | None:
    """通过豆瓣 suggest API 搜索电影，返回 {douban_id, cn_title} 或 None。"""
    queries = [imdb_title]
    if ':' in imdb_title:
        queries.append(imdb_title.split(':')[0].strip())
    if len(imdb_title) > 30:
        queries.append(imdb_title[:30].strip())

    for query in queries:
        results = _douban_suggest(client, query)
        time.sleep(1.0 + random.random() * 2.0)

        for r in results:
            # 比对 title 和 sub_title
            if not _titles_match(imdb_title, r['title']) and \
               not _titles_match(imdb_title, r['sub_title']):
                continue
            # 年份校验
            if year and r.get('year'):
                try:
                    if abs(int(r['year']) - year) > 1:
                        continue
                except ValueError:
                    continue
            # 验证 douban_id
            verified = _douban_verify(client, r['id'])
            time.sleep(1.0 + random.random() * 2.0)
            if verified:
                return {
                    'douban_id': r['id'],
                    'cn_title': r['title'],  # 中文标题
                    'sub_title': r.get('sub_title', ''),  # 英文原名
                }
    return None


def _fetch_chinese_title(
    client: httpx.Client, douban_id: str
) -> str | None:
    """从豆瓣获取中文标题。"""
    return _douban_verify(client, douban_id)


# ── 数据库匹配 ──────────────────────────────────────────────────


def _find_in_db(db: Session, imdb_id: str, title: str,
                year: int) -> Movie | None:
    """在数据库中查找匹配电影（仅查库，不调外部 API）。"""
    # 1. imdb_id 精确
    if imdb_id:
        m = db.query(Movie).filter(Movie.imdb_id == imdb_id).first()
        if m:
            return m

    # 2. title + year
    if not title:
        return None
    norm = _normalize(title)

    for dy in [0, -1, 1]:
        if year + dy <= 0 and dy != 0:
            continue
        candidates = db.query(Movie).filter(
            Movie.year == year + dy).all()
        for movie in candidates:
            for mt in [movie.title, movie.original_title]:
                if mt and _titles_match(title, mt):
                    return movie
    return None


def _merge_movies(db: Session, keep: Movie, remove: Movie):
    """将 remove 的 version_entries 迁移到 keep，然后删除 remove。"""
    keep_versions = {
        e.version_id
        for e in db.query(VersionEntry)
                   .filter(VersionEntry.movie_id == keep.id).all()
    }
    for entry in db.query(VersionEntry).filter(
            VersionEntry.movie_id == remove.id).all():
        if entry.version_id in keep_versions:
            db.delete(entry)
        else:
            entry.movie_id = keep.id
    # 复制元数据
    for field in ('director', 'genre', 'country', 'summary',
                  'poster_path', 'douban_url', 'cast_members', 'tagline',
                  'original_title'):
        if not getattr(keep, field) and getattr(remove, field):
            setattr(keep, field, getattr(remove, field))
    db.flush()
    db.delete(remove)


# ── 主流程 ─────────────────────────────────────────────────────


def crawl_imdb_top250(db_factory) -> dict:
    """爬取 IMDb Top 250 并创建版本。"""
    _reset_imdb_progress()
    _update_progress(status="running", phase="fetching",
                     message="正在爬取 IMDb Top 250...")

    try:
        movies_data = fetch_imdb_top250()
        if not movies_data:
            _update_progress(status="error", message="未获取到任何电影数据")
            return _imdb_progress

        _update_progress(
            total=len(movies_data),
            message=f"获取到 {len(movies_data)} 部电影，开始匹配...")

        db = db_factory()
        douban_client = _get_douban_client()

        try:
            matched_movies = []  # (rank, movie_id, rating)
            _update_progress(phase="matching")

            for i, mdata in enumerate(movies_data):
                _update_progress(current=i + 1)
                rank = mdata.get("rank", i + 1)
                imdb_id = mdata.get("imdb_id", "")
                imdb_title = mdata.get("title", "")
                year = mdata.get("year", 0)

                # Step 1-2: 数据库匹配
                movie = _find_in_db(db, imdb_id, imdb_title, year)

                if not movie:
                    # Step 3: 豆瓣 suggest API 搜索
                    _update_progress(
                        message=f"搜索豆瓣: {imdb_title} ({i+1}/{len(movies_data)})")
                    douban_info = _search_douban_for_movie(
                        douban_client, imdb_title, year)
                    _imdb_progress["douban_searched"] += 1
                    time.sleep(3.0 + random.random() * 3.0)

                    if douban_info:
                        did = douban_info['douban_id']
                        # 查库中是否已有该 douban_id
                        existing = db.query(Movie).filter(
                            Movie.douban_id == did).first()
                        if existing:
                            movie = existing
                        else:
                            # Step 4a: 新建电影（有豆瓣信息）
                            movie = Movie(
                                douban_id=did,
                                imdb_id=imdb_id,
                                title=douban_info['cn_title'],
                                original_title=imdb_title,
                                year=year,
                                rating=mdata.get("rating"),
                            )
                            db.add(movie)
                            db.flush()
                            _imdb_progress["created"] += 1
                            logger.info(
                                f"Created: {douban_info['cn_title']} "
                                f"({imdb_id}, douban={did})")
                    else:
                        # Step 4b: 新建电影（无豆瓣信息）
                        movie = Movie(
                            imdb_id=imdb_id,
                            title=imdb_title,
                            year=year,
                            rating=mdata.get("rating"),
                        )
                        db.add(movie)
                        db.flush()
                        _imdb_progress["created"] += 1
                        logger.info(f"Created (no Douban): {imdb_title}")

                # 补充 imdb_id
                if imdb_id and not movie.imdb_id:
                    movie.imdb_id = imdb_id

                # Step 5: 标题修正 — 如果标题无中文，尝试获取中文名
                if not _has_chinese(movie.title):
                    cn = _fetch_chinese_title(douban_client, movie.douban_id)
                    if cn and _has_chinese(cn):
                        if not movie.original_title:
                            movie.original_title = movie.title
                        movie.title = cn
                        logger.info(
                            f"Title fixed: {movie.original_title} -> {cn}")

                matched_movies.append(
                    (rank, movie.id, mdata.get("rating")))
                _imdb_progress["matched"] += 1

                if (i + 1) % 10 == 0:
                    db.commit()

            db.commit()
            douban_client.close()

            # Phase 3: 创建版本
            _update_progress(phase="creating_version",
                             message="创建版本...")
            tag = now().strftime("%Y-%m-%d")
            suffix = 1
            base_tag = tag
            while db.query(Version).filter(Version.tag == tag).first():
                suffix += 1
                tag = f"{base_tag}-{suffix}"

            version = Version(
                tag=tag, source="imdb",
                crawled_at=now(), movie_count=len(matched_movies))
            db.add(version)
            db.flush()

            db.add_all([
                VersionEntry(
                    version_id=version.id,
                    movie_id=mid, rank=rk, rating=rt)
                for rk, mid, rt in matched_movies
            ])
            db.commit()

            _update_progress(
                status="done", phase="done",
                message=(
                    f"完成！版本 {tag}：{len(matched_movies)} 部电影，"
                    f"匹配 {_imdb_progress['matched']}，"
                    f"新建 {_imdb_progress['created']}，"
                    f"豆瓣检索 {_imdb_progress['douban_searched']}"))

        finally:
            douban_client.close()
            db.close()

    except Exception as e:
        logger.exception("IMDb crawl failed")
        _update_progress(status="error", message=f"爬取失败: {e}")

    return _imdb_progress
