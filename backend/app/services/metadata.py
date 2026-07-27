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
from app.utils.http_client import fetch_binary, _get_cookie
from app.utils.douban_fetcher import AntiCrawlBlock, PageFetchTimeout, get_douban_fetcher

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
    (within 30 days). Successfully fetched movies are skipped even if some
    fields are empty — that means the source genuinely has no data for them.

    Only selects movies with numeric douban_id (excludes placeholders like
    "blocked_vendetta").
    """
    cutoff = now() - timedelta(days=30)
    numeric_id = Movie.douban_id.op("GLOB")("[0-9][0-9]*")  # 1+ 位纯数字
    return or_(
        # 缺少字段且从未获取过，或距上次成功获取超过 30 天
        (
            (
                or_(Movie.director.is_(None), Movie.director == "") |
                or_(Movie.genre.is_(None), Movie.genre == "") |
                or_(Movie.country.is_(None), Movie.country == "") |
                or_(Movie.summary.is_(None), Movie.summary == "") |
                or_(Movie.poster_path.is_(None), Movie.poster_path == "") |
                or_(Movie.douban_url.is_(None), Movie.douban_url == "") |
                Movie.rating.is_(None) |
                Movie.rating_count.is_(None) |
                Movie.duration.is_(None)
            ) &
            numeric_id &
            (Movie.last_meta_fetch.is_(None) | (Movie.last_meta_fetch < cutoff))
        ),
        # 有 douban_id 但缺少 imdb_id 且未标记已获取（仅数字 ID）
        (numeric_id & Movie.imdb_id.is_(None) & Movie.detail_fetched.isnot(True))
    )


def should_retry_now(movie) -> bool:
    """Whether a movie should be retried now.

    Returns True when:
    - No previous attempt (last_meta_attempt is None)
    - No recorded failures (meta_fetch_failures = 0) — 无需退避
    - 退避时间已过: min(2^failures, 72) 小时
    """
    if movie.last_meta_attempt is None:
        return True
    failures = movie.meta_fetch_failures or 0
    if failures == 0:
        return True  # 无失败记录，不应用退避
    hours = min(2 ** failures, 72)
    # SQLite 返回 naive datetime（无时区），now() 返回 aware
    # 比较前统一为 naive（去掉时区信息）
    last_attempt = movie.last_meta_attempt.replace(tzinfo=None)
    cutoff = now().replace(tzinfo=None) - timedelta(hours=hours)
    return last_attempt < cutoff


def check_cookie_valid(cookie: str = "") -> dict:
    """Check if the Douban cookie is still valid. Returns {valid, message}.

    使用 Playwright 获取 Top 250 页面（与爬取目标一致），能自动处理 PoW 挑战。
    检查 Top 250 页面（而非 /mine）确保 Cookie 对实际爬取目标有效。
    每次调用都会清除浏览器旧 cookie 并注入当前 cookie，确保 cookie 始终生效。
    """
    if not cookie:
        cookie = _get_cookie()
    if not cookie:
        return {"valid": False, "message": "未配置豆瓣 Cookie"}

    try:
        fetcher = get_douban_fetcher()
        # 使用 Top 250 URL（与实际爬取目标一致），确保 Cookie 对该页面有效
        html = fetcher.fetch_page_with_cookie(
            "https://movie.douban.com/top250?start=0&filter=", cookie)

        head = html[:2000]
        # 检查登录页或登录跳转页
        # 豆瓣登录相关页面可能包含以下特征之一：
        # - "登录" 和 "注册" 同时出现（标准登录页）
        # - "登录跳转" （登录重定向页）
        # - title 中包含 "登录"（各种登录页面）
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', head)
        page_title = title_match.group(1) if title_match else ""

        if ("登录" in head and "注册" in head) or \
           "登录跳转" in head or \
           "登录" in page_title:
            return {"valid": False, "message": "Cookie 已过期，请在设置页面更新"}
        return {"valid": True, "message": "Cookie 有效"}
    except AntiCrawlBlock as e:
        # fetcher 在 _handle_fetch 中已检测到反爬/无效页面并抛出
        # 根据异常消息提供友好提示
        msg = str(e)
        if "没有访问权限" in msg:
            return {"valid": False, "message": "Cookie 无效，无法访问该页面"}
        if "页面结构异常" in msg:
            # Top 250 页面缺少 grid_view 元素——几乎总是登录墙或地区限制
            # _handle_fetch 会把页面标题结构化地附在异常对象上，不依赖字符串解析
            page_title = getattr(e, "page_title", "") or ""
            if "登录" in page_title:
                return {"valid": False, "message": "Cookie 已过期，豆瓣要求登录才能访问榜单"}
            return {"valid": False, "message": "Cookie 已过期或无法访问 Top 250 页面"}
        if "反爬封锁" in msg:
            return {"valid": False, "message": "Cookie 触发反爬机制"}
        if "PoW" in msg:
            return {"valid": False, "message": "Cookie 验证失败：反爬挑战未通过"}
        if "CAPTCHA" in msg:
            return {"valid": False, "message": "Cookie 触发验证码"}
        if re.search(r'HTTP\s+(?:429|502|503|504)\b', msg):
            return {"valid": False, "message": "请求过于频繁，豆瓣限流中，请稍后重试"}
        logger.warning(f"check_cookie_valid: 未识别的 AntiCrawlBlock: {msg}")
        return {"valid": False, "message": "Cookie 触发反爬机制，请稍后重试"}
    except Exception:
        # 通用异常（网络错误/Playwright 崩溃等）——不向用户暴露内部 URL/异常细节
        logger.exception("check_cookie_valid: 验证异常")
        return {"valid": False, "message": "Cookie 验证失败，请检查网络后重试"}


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
    elif key == "片长":
        # 解析时长，格式如 "142分钟" 或 "142 分钟"
        m = re.search(r"(\d+)", val)
        if m:
            info["duration"] = int(m.group(1))
    # 年份不再从上映日期提取（重映日期会排在前面导致年份错误）
    # 年份统一由 span.year 提取，见 parse_detail_page


def parse_detail_page(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    info = {}

    # 从 <title> 标签提取干净中文标题（格式: "中文名 (豆瓣)"）
    head_title = soup.find("title")
    if head_title:
        t = head_title.get_text(strip=True)
        # 去掉末尾 " (豆瓣)" 或 " 电影 (豆瓣)" 等后缀
        t = re.sub(r'\s*(?:电影|电视剧|综艺|纪录片)?\s*\(豆瓣\)\s*$', '', t).strip()
        # 拒绝 HTTP 错误页标题（如 "429 Too Many Requests"、"503 Service Unavailable"）
        # 这类页面不是真正的电影详情页，提取的标题会污染数据库
        if t and not re.match(r'^\d{3}\s+\w', t):
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

    # Year: 优先从 span.year 提取（豆瓣展示的原始创作年份，语义最准确）
    # fallback 到上映日期字段（取最早年份，避免重映日期干扰）
    year_span = soup.select_one("span.year")
    if year_span:
        m = re.search(r"(\d{4})", year_span.text)
        if m:
            info["year"] = int(m.group(1))
    if "year" not in info:
        # 从上映日期取所有年份，选最小的（即原始上映年份）
        info_div_el = soup.select_one("#info")
        if info_div_el:
            release_text = info_div_el.get_text()
            years = [int(y) for y in re.findall(r"(\d{4})", release_text)]
            # 过滤合理范围的年份（1888-当前年份+5，电影史最早1888）
            valid_years = [y for y in years if 1888 <= y <= 2035]
            if valid_years:
                info["year"] = min(valid_years)

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


def run_backfill(force: bool = False, mode: str = "incremental") -> dict:
    """Fetch missing metadata for all movies that need it.

    mode:
      - 'incremental': only fetch movies with missing fields (default)
      - 'full': refetch all movies, always update title/rating/rating_count
    """
    db = SessionLocal()
    fetcher = get_douban_fetcher()
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
            # 过滤掉非数字 douban_id（占位符如 "blocked_vendetta" 无法构造合法 URL）
            to_fetch = [m for m in to_fetch if m.douban_id and m.douban_id.isdigit()]
        else:
            to_fetch = db.query(Movie).filter(_needs_metadata_query()).all()

        # 指数退避过滤：失败次数越多，重试间隔越长
        # force=True 和 mode='full' 跳过退避——用户明确要求立即处理
        if not force and mode != "full":
            to_fetch = [m for m in to_fetch if should_retry_now(m)]

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
                url = f"https://movie.douban.com/subject/{movie.douban_id}/"
                html = fetcher.fetch_page(url)

                try:
                    info = parse_detail_page(html)
                except Exception as parse_err:
                    # 解析失败是确定性 bug——递增退避永远无法修复
                    # 标记为已获取（30天后再试），不递增 meta_fetch_failures
                    logger.warning(f"  详情页解析失败: {parse_err}")
                    movie.last_meta_fetch = now()
                    movie.last_meta_attempt = now()
                    meta_progress["failed"] += 1
                    continue

                updated = False

                # 标题：详情页标题始终为准（修正 abstract API 拼接格式）
                if info.get("title") and info["title"] != movie.title:
                    movie.title = info["title"]
                    updated = True

                # 评分、打分人数、年份：full 模式下始终覆盖
                # （年份需要覆盖，因为重映日期可能导致之前解析出错误年份）
                for field in ["rating", "rating_count", "year"]:
                    val = info.get(field)
                    if val and (mode == "full" or not getattr(movie, field)):
                        if getattr(movie, field) != val:
                            setattr(movie, field, val)
                            updated = True

                # 其他字段：仅填充空值
                for field in ["director", "genre", "country", "tagline", "summary", "douban_url"]:
                    if info.get(field) and not getattr(movie, field):
                        setattr(movie, field, info[field])
                        updated = True

                # 时长：仅填充空值
                if info.get("duration") and not movie.duration:
                    movie.duration = info["duration"]
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
                # 空字段视为来源确实没有该数据，30 天内不重试
                movie.last_meta_fetch = now()
                movie.last_meta_attempt = now()
                movie.meta_fetch_failures = 0  # 成功时重置失败计数
                if updated and not movie.detail_fetched:
                    movie.detail_fetched = True
                movie.updated_at = now()
                meta_progress["updated"] += 1

            except (AntiCrawlBlock, PageFetchTimeout) as e:
                # 冷却策略：反爬封锁 30-60s，超时 5-10s
                cooldown_range = (30, 60) if isinstance(e, AntiCrawlBlock) else (5, 10)
                label = "反爬封锁" if isinstance(e, AntiCrawlBlock) else "超时/网络错误"
                logger.warning(f"  {label}: {e}")
                movie.last_meta_attempt = now()
                movie.meta_fetch_failures = (movie.meta_fetch_failures or 0) + 1
                meta_progress["failed"] += 1
                cooldown = cooldown_range[0] + random.random() * (cooldown_range[1] - cooldown_range[0])
                logger.info(f"  冷却 {cooldown:.0f}s 后继续...")
                time.sleep(cooldown)
            except Exception as e:
                logger.warning(f"  Failed: {e}")
                movie.last_meta_attempt = now()
                movie.meta_fetch_failures = (movie.meta_fetch_failures or 0) + 1
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
