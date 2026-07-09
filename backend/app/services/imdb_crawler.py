"""
IMDb Top 250 爬虫。

使用 Playwright 绕过 IMDb 的 AWS WAF 防护，获取 Top 250 排名数据。
匹配策略（按优先级）：
1. 数据库 imdb_id 精确匹配
2. 用 IMDb ID 直接搜索豆瓣搜索页（search.douban.com），提取 douban_id
3. 降级到 suggest API 搜索标题 + 详情页验证 imdb_id
未匹配的电影进入 pending_matches 等待用户手动确认。
"""

import re
import time
import random
import logging
import threading

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Movie, Version, VersionEntry, PendingMatch
from app.utils import now
from app.utils.http_client import _get_cookie, get_headers

logger = logging.getLogger(__name__)


def _get_retry_manager():
    """延迟导入重试管理器，避免循环导入"""
    from app.services.retry_manager import get_retry_manager
    return get_retry_manager()

_imdb_progress = {
    "status": "idle", "phase": "", "current": 0, "total": 250,
    "message": "", "matched": 0, "created": 0, "douban_searched": 0,
    "pending": 0, "new_version": None,
}


def get_imdb_progress() -> dict:
    return dict(_imdb_progress)


def _reset_imdb_progress():
    _imdb_progress.update({
        "status": "idle", "phase": "", "current": 0, "total": 250,
        "message": "", "matched": 0, "created": 0, "douban_searched": 0,
        "pending": 0, "new_version": None,
    })


def _update_progress(**kwargs):
    _imdb_progress.update(kwargs)


# ── IMDb 数据获取 ──────────────────────────────────────────────


def fetch_imdb_top250() -> list[dict]:
    """使用 Playwright 爬取 IMDb Top 250 页面，返回电影列表。"""
    import json
    from playwright.sync_api import sync_playwright
    from playwright.sync_api import TimeoutError as PlaywrightTimeout

    movies = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=settings.playwright_headless)
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
                "li.ipc-metadata-list-summary-item", timeout=settings.playwright_timeout_ms)
        except Exception as e:
            logger.warning(f"Selector wait failed: {e}, retrying...")
            try:
                page.wait_for_timeout(10000)
                page.wait_for_selector(
                    "li.ipc-metadata-list-summary-item", timeout=settings.playwright_timeout_ms)
            except Exception as e2:
                if not isinstance(e2, PlaywrightTimeout):
                    raise
                logger.warning(f"Selector retry also timed out, falling back to data extraction")

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
    """创建豆瓣 HTTP 客户端，使用设置中的 cookie 和统一请求头。"""
    cookie = _get_cookie()
    headers = get_headers(cookie)
    return httpx.Client(
        headers=headers,
        follow_redirects=True,
        timeout=30,
    )


def _douban_delay(base: float = None):
    """反爬延时：基础延时 + 随机抖动。"""
    if base is None:
        base = settings.douban_request_delay
    time.sleep(base + random.random() * base * 0.5)


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


def _douban_search_by_imdb_id(
    client: httpx.Client, imdb_id: str
) -> str | None:
    """通过豆瓣搜索页用 IMDb ID 直接查询 douban_id。

    使用 search.douban.com/movie/subject_search?search_text={imdb_id}，
    从搜索结果的 subject 链接中提取第一个 douban_id。
    """
    if not imdb_id:
        return None
    try:
        resp = client.get(
            'https://search.douban.com/movie/subject_search',
            params={'search_text': imdb_id},
        )
        if resp.status_code != 200:
            logger.warning(f"豆瓣搜索页返回 {resp.status_code}: {imdb_id}")
            return None
        text = resp.text
        # 检测反爬
        if '检测到有异常请求' in text or '验证码' in text:
            logger.warning(f"豆瓣搜索页被拦截: {imdb_id}")
            return None
        if 'name="tok"' in text and 'sha512' in text:
            logger.warning(f"豆瓣搜索页 PoW 挑战: {imdb_id}")
            return None
        # 提取第一个 subject 链接中的 douban_id
        m = re.search(r'subject/(\d+)', text)
        if m:
            return m.group(1)
    except Exception as e:
        logger.warning(f"豆瓣搜索页请求失败: {imdb_id} - {e}")
    return None


def _parse_cn_title(raw: str) -> str:
    """从 subject_abstract 的拼接标题中提取干净中文名。

    输入格式: "中文名 英文名\\u200e(年份)" 或 "中文名\\u200e(年份)"
    返回: "中文名"
    """
    t = raw.replace('‎', '').strip()
    # 去掉末尾 (年份)
    t = re.sub(r'\s*\(\d{4}\)\s*$', '', t).strip()
    # 从第一个拉丁字母处截断（中文标题不会以拉丁字母开头）
    m = re.search(r'[A-Za-z]', t)
    if m:
        t = t[:m.start()].strip()
    # 去掉尾部残留的数字和标点（如 "三傻大闹宝莱坞 3" → "三傻大闹宝莱坞"）
    t = re.sub(r'[\s\d:：\-/]+$', '', t).strip()
    return t or raw.strip()


def _douban_verify(
    client: httpx.Client,
    douban_id: str,
) -> tuple[str, str | None] | None:
    """通过 abstract API 验证 douban_id，返回 (clean_title, imdb_id) 或 None。

    仅使用 subject_abstract 接口（轻量、不易触发反爬），
    从拼接标题中解析出干净中文名，不额外请求详情页。
    """
    try:
        resp = client.get(
            f'https://movie.douban.com/j/subject_abstract'
            f'?subject_id={douban_id}')
        if resp.status_code != 200:
            return None
        data = resp.json().get('subject', {})
        raw_title = data.get('title', '')
        if not raw_title or raw_title == '未知':
            return None
        clean_title = _parse_cn_title(raw_title)
        return (clean_title, None)
    except Exception:
        return None


def _fetch_imdb_id_from_douban_detail(douban_id: str) -> tuple[str | None, str | None]:
    """访问豆瓣详情页（通过 Playwright 绕过 PoW），返回 (imdb_id, page_text)。

    包含重试循环：瞬态网络故障/超时最多重试 max_retries 次，指数退避。
    反爬封锁（AntiCrawlBlock）不重试，返回 (None, None)——
    该候选无法验证，调用方继续尝试下一个候选。
    """
    from app.utils.douban_fetcher import get_douban_fetcher, AntiCrawlBlock

    url = f'https://movie.douban.com/subject/{douban_id}/'
    fetcher = get_douban_fetcher()

    for attempt in range(settings.douban_http_max_retries):
        try:
            text = fetcher.fetch_page(url)
            # 格式1: 链接形式 imdb.com/title/ttXXXXXXX
            m = re.search(r'imdb\.com/title/(tt\d+)', text)
            if m:
                return (m.group(1), text)
            # 格式2: 纯文本形式 IMDb:</span> ttXXXXXXX
            m = re.search(r'IMDb:</span>\s*(tt\d+)', text)
            if m:
                return (m.group(1), text)
            return (None, text)
        except AntiCrawlBlock as e:
            logger.warning(f"详情页反爬封锁（跳过该候选）: {url} - {e}")
            return (None, None)  # 不重试，该候选无法验证
        except Exception as e:
            if attempt < settings.douban_http_max_retries - 1:
                logger.warning(f"详情页请求失败 (重试 {attempt+1}): {url} - {e}")
                time.sleep(settings.douban_request_delay * (attempt + 1))
            else:
                logger.error(f"详情页请求失败: {url} - {e}")
    return (None, None)


def _search_douban_candidates(
    client: httpx.Client, imdb_title: str, year: int
) -> list[dict]:
    """搜索豆瓣 suggest，返回所有可能的候选 [{douban_id, title, sub_title, year}]。
    不做 imdb_id 验证，仅过滤明显不相关的。"""
    queries = [imdb_title]
    if ':' in imdb_title:
        queries.append(imdb_title.split(':')[0].strip())
    if len(imdb_title) > 30:
        queries.append(imdb_title[:30].strip())

    seen_ids = set()
    candidates = []

    for query in queries:
        results = _douban_suggest(client, query)
        _douban_delay()

        for r in results:
            if r['id'] in seen_ids:
                continue
            # suggest API 本身就是相关性搜索，不做标题过滤
            # 真正的验证在后续详情页 imdb_id 匹配
            # 仅做宽松年份过滤（±3年，豆瓣和 IMDb 年份常有差异）
            if year and r.get('year'):
                try:
                    if abs(int(r['year']) - year) > 3:
                        continue
                except ValueError:
                    continue
            seen_ids.add(r['id'])
            candidates.append(r)

    return candidates


# ── 数据库匹配 ──────────────────────────────────────────────────


def _find_in_db_by_imdb_id(db: Session, imdb_id: str) -> Movie | None:
    """仅通过 imdb_id 在数据库中查找。"""
    if imdb_id:
        return db.query(Movie).filter(Movie.imdb_id == imdb_id).first()
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
    """爬取 IMDb Top 250 并创建版本。严格匹配：imdb_id 必须一致。"""
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
            pending_items = []   # 待确认列表
            seen_movie_ids = set()  # deduplicate movie_id
            _update_progress(phase="matching")

            for i, mdata in enumerate(movies_data):
                _update_progress(current=i + 1)
                rank = mdata.get("rank", i + 1)
                imdb_id = mdata.get("imdb_id", "")
                imdb_title = mdata.get("title", "")
                year = mdata.get("year", 0)

                # Step 1: 数据库 imdb_id 精确匹配
                movie = _find_in_db_by_imdb_id(db, imdb_id)

                if movie:
                    # 已有记录，直接使用
                    pass
                else:
                    verified_candidates = []  # 候选列表（用于 pending）
                    # Step 2: 用 IMDb ID 直接搜索豆瓣（首选）
                    _update_progress(
                        message=f"IMDb ID 搜索豆瓣: {imdb_title} ({i+1}/{len(movies_data)})")
                    _douban_delay()
                    douban_id = _douban_search_by_imdb_id(
                        douban_client, imdb_id)
                    _imdb_progress["douban_searched"] += 1

                    if douban_id:
                        # 搜索页返回了结果，访问详情页验证并获取干净标题
                        existing = db.query(Movie).filter(
                            Movie.douban_id == douban_id).first()
                        if existing:
                            movie = existing
                            if imdb_id and not movie.imdb_id:
                                movie.imdb_id = imdb_id
                        else:
                            result = _douban_verify(
                                douban_client, douban_id)
                            _douban_delay()
                            if result:
                                cn_title, _detail_imdb_id = result
                                movie = Movie(
                                    douban_id=douban_id,
                                    imdb_id=imdb_id,
                                    title=cn_title,
                                    original_title=imdb_title,
                                )
                                db.add(movie)
                                db.flush()
                                _imdb_progress["created"] += 1
                                logger.info(
                                    f"Created (IMDb search): {cn_title} "
                                    f"({imdb_id}, douban={douban_id})")

                    if not movie:
                        # Step 3: 降级到 suggest API + 详情页验证
                        _update_progress(
                            message=f"搜索豆瓣 suggest: {imdb_title} ({i+1}/{len(movies_data)})")
                        candidates = _search_douban_candidates(
                            douban_client, imdb_title, year)
                        _douban_delay(3.0)

                        matched_candidate = None
                        verified_candidates = []

                        for cand in candidates:
                            detail_imdb_id, _ = \
                                _fetch_imdb_id_from_douban_detail(cand['id'])
                            _douban_delay(2.0)

                            cand_info = {
                                'douban_id': cand['id'],
                                'title': cand['title'],
                                'year': cand.get('year', ''),
                                'imdb_id_from_detail': detail_imdb_id,
                            }
                            verified_candidates.append(cand_info)

                            if detail_imdb_id and imdb_id and \
                               detail_imdb_id == imdb_id:
                                matched_candidate = cand
                                break

                        if matched_candidate:
                            did = matched_candidate['id']
                            existing = db.query(Movie).filter(
                                Movie.douban_id == did).first()
                            if existing:
                                movie = existing
                                if imdb_id and not movie.imdb_id:
                                    movie.imdb_id = imdb_id
                            else:
                                result = _douban_verify(
                                    douban_client, did)
                                _douban_delay()
                                cn_title = result[0] if result else None
                                movie = Movie(
                                    douban_id=did,
                                    imdb_id=imdb_id,
                                    title=cn_title or matched_candidate['title'],
                                    original_title=imdb_title,
                                )
                                db.add(movie)
                                db.flush()
                                _imdb_progress["created"] += 1
                                logger.info(
                                    f"Created (suggest): {cn_title} "
                                    f"({imdb_id}, douban={did})")

                    if not movie:
                        # 所有方式均未匹配 → pending
                        _imdb_progress["pending"] += 1
                        pending_items.append({
                            'imdb_id': imdb_id,
                            'imdb_title': imdb_title,
                            'year': year,
                            'rank': rank,
                            'candidates': verified_candidates,
                        })
                        logger.info(
                            f"Pending: {imdb_title} ({imdb_id})")
                        continue

                # 冲突：同一部豆瓣电影被多部 IMDb 电影关联 → 两者都进待确认
                if movie and movie.id in seen_movie_ids:
                    logger.warning(
                        f"Conflict: {imdb_title} ({imdb_id}) "
                        f"-> movie_id={movie.id} already matched by another IMDb entry")
                    _imdb_progress["pending"] += 1
                    pending_items.append({
                        'imdb_id': imdb_id,
                        'imdb_title': imdb_title,
                        'year': year,
                        'rank': rank,
                        'candidates': [{
                            'douban_id': movie.douban_id,
                            'title': movie.title,
                            'year': str(movie.year) if movie.year else '',
                            'imdb_id_from_detail': movie.imdb_id,
                        }],
                    })
                    continue
                if movie:
                    seen_movie_ids.add(movie.id)
                    matched_movies.append(
                        (rank, movie.id, mdata.get("rating")))
                    _imdb_progress["matched"] += 1

                if (i + 1) % 10 == 0:
                    db.commit()

            # Phase 3: 检查是否有变化，无变化则不创建版本
            _update_progress(phase="creating_version",
                             message="检查版本变化...")

            has_pending = len(pending_items) > 0
            current_movie_ids = [mid for _, mid, _ in matched_movies]

            # 获取最新的 IMDb 版本
            latest_imdb = db.query(Version).filter(
                Version.source == "imdb"
            ).order_by(Version.tag.desc()).first()

            version_created = True
            if latest_imdb:
                latest_entries = (
                    db.query(VersionEntry)
                    .filter(VersionEntry.version_id == latest_imdb.id)
                    .order_by(VersionEntry.rank)
                    .all()
                )
                latest_movie_ids = [e.movie_id for e in latest_entries]

                if current_movie_ids == latest_movie_ids:
                    # 电影列表完全相同，不创建新版本
                    version_created = False
                    logger.info(
                        f"IMDb list unchanged vs {latest_imdb.tag}, "
                        f"skipping version creation")
                    # pending matches 仍然保存到最新版本上
                    if has_pending:
                        for pi in pending_items:
                            pm = PendingMatch(
                                version_id=latest_imdb.id,
                                imdb_id=pi['imdb_id'],
                                imdb_title=pi['imdb_title'],
                                year=pi['year'],
                                rank=pi['rank'],
                                candidates=pi['candidates'],
                                status='pending',
                            )
                            db.add(pm)
                        db.commit()
                    _update_progress(
                        status="done", phase="done", new_version=False,
                        message=(
                            f"榜单无变化（与 {latest_imdb.tag} 一致），未创建新版本。"
                            + (f" {len(pending_items)} 部电影待确认。"
                               if has_pending else "")))
                else:
                    # 有变化，记录 diff
                    current_set = set(current_movie_ids)
                    latest_set = set(latest_movie_ids)
                    added = current_set - latest_set
                    removed = latest_set - current_set
                    if added:
                        added_movies = db.query(Movie).filter(Movie.id.in_(added)).all()
                        logger.info(f"New movies: {[m.title for m in added_movies]}")
                    if removed:
                        removed_movies = db.query(Movie).filter(Movie.id.in_(removed)).all()
                        logger.info(f"Removed movies: {[m.title for m in removed_movies]}")

            if version_created:
                tag = now().strftime("%Y-%m-%d")
                suffix = 1
                base_tag = tag
                while db.query(Version).filter(
                        Version.tag == tag,
                        Version.source == "imdb").first():
                    suffix += 1
                    tag = f"{base_tag}-{suffix}"

                version = Version(
                    tag=tag, source="imdb",
                    status="pending_confirmation" if has_pending else "confirmed",
                    crawled_at=now(), movie_count=len(matched_movies))
                db.add(version)
                db.flush()

                for pi in pending_items:
                    pm = PendingMatch(
                        version_id=version.id,
                        imdb_id=pi['imdb_id'],
                        imdb_title=pi['imdb_title'],
                        year=pi['year'],
                        rank=pi['rank'],
                        candidates=pi['candidates'],
                        status='pending',
                    )
                    db.add(pm)

                db.add_all([
                    VersionEntry(
                        version_id=version.id,
                        movie_id=mid, rank=rk, rating=rt)
                    for rk, mid, rt in matched_movies
                ])
                db.commit()

                if has_pending:
                    _update_progress(
                        status="done", phase="done", new_version=True,
                        message=(
                            f"版本 {tag} 已创建（{len(matched_movies)} 部），"
                            f"{len(pending_items)} 部电影待确认。"
                            f"请前往控制台处理待确认匹配。"))
                else:
                    _update_progress(
                        status="done", phase="done", new_version=True,
                        message=(
                            f"完成！版本 {tag}：{len(matched_movies)} 部电影，"
                            f"匹配 {_imdb_progress['matched']}，"
                            f"新建 {_imdb_progress['created']}"))

        finally:
            douban_client.close()
            db.close()

        # 新版本创建后自动触发增量元数据补全（从详情页获取干净中文标题等）
        if _imdb_progress.get("new_version"):
            _trigger_metadata_backfill()

        # 成功后取消等待中的重试
        try:
            retry_mgr = _get_retry_manager()
            retry_mgr.cancel_retry("imdb")
        except Exception as e:
            logger.warning(f"Failed to cancel retry: {e}")

    except Exception as e:
        logger.exception("IMDb crawl failed")
        _update_progress(status="error", message=f"爬取失败: {e}")

    return _imdb_progress


def _trigger_metadata_backfill():
    """在后台线程启动元数据补全，用于获取干净中文标题等。"""
    from app.services.metadata import run_backfill, meta_progress

    if meta_progress.get("active"):
        logger.info("Metadata backfill already active, skipping auto-trigger")
        return

    # 立即标记为活跃，防止定时任务在窗口期内重复触发
    meta_progress["active"] = True

    def _run():
        try:
            logger.info("Auto-triggering metadata backfill after IMDb crawl...")
            result = run_backfill()
            logger.info(f"Metadata backfill completed: {result}")
        except Exception as e:
            logger.error(f"Metadata backfill failed: {e}")
        finally:
            # 防御性复位：run_backfill() 内部已在成功/异常路径复位 active，
            # 此处保险防止 run_backfill 重构时遗漏复位导致 active 永久卡死。
            meta_progress["active"] = False

    thread = threading.Thread(target=_run, daemon=True, name="meta-backfill")
    thread.start()
    logger.info("Metadata backfill thread started")
