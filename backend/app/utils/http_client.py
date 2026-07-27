import time
import random
import logging
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _get_cookie() -> str:
    """Read douban_cookie from DB setting, fall back to env config."""
    try:
        from app.database import SessionLocal
        from app.models import Setting
        db = SessionLocal()
        try:
            row = db.query(Setting).filter(Setting.key == "douban_cookie").first()
            if row and row.value:
                return row.value
        finally:
            db.close()
    except Exception:
        pass
    return settings.douban_cookie


def get_headers(cookie: str = "") -> dict:
    h = {
        "User-Agent": settings.douban_user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://movie.douban.com/",
        "Connection": "keep-alive",
    }
    if cookie:
        h["Cookie"] = cookie
    return h


def _check_waf_redirect(resp: httpx.Response, url: str) -> None:
    """检查响应是否经过 sec.douban.com WAF 重定向。

    Args:
        resp: HTTP 响应对象
        url: 原始请求 URL（用于错误消息）

    Raises:
        RuntimeError: 如果检测到 WAF 封锁
    """
    if any("sec.douban.com" in str(r.url) for r in resp.history):
        raise RuntimeError(f"豆瓣 WAF 封锁 (sec.douban.com 重定向): {url}")
    if "sec.douban.com" in str(resp.url):
        raise RuntimeError(f"豆瓣 WAF 封锁 (sec.douban.com): {url}")


def fetch_page(url: str, cookie: str = "") -> str:
    """Fetch a page with retry, exponential backoff and jitter. Optionally pass cookie for auth."""
    if not cookie:
        cookie = _get_cookie()
    headers = get_headers(cookie)
    last_error = None

    for attempt in range(settings.douban_http_max_retries):
        try:
            with httpx.Client(headers=headers, follow_redirects=True, timeout=30) as client:
                resp = client.get(url)

                # 检测 WAF 封锁
                _check_waf_redirect(resp, url)

                resp.raise_for_status()

                text = resp.text

                # 反爬检测
                if "检测到有异常请求" in text:
                    raise RuntimeError(f"豆瓣反爬封锁: {url}")
                if 'name="tok"' in text and 'name="cha"' in text and 'sha512' in text:
                    raise RuntimeError(f"豆瓣 PoW 挑战页: {url}")
                if "captcha" in resp.url.path.lower():
                    raise RuntimeError(f"CAPTCHA page: {url}")
                if len(text) < 1000 and "电影" not in text and "title" not in text.lower():
                    raise RuntimeError(f"疑似封锁 (响应过短 {len(text)} 字节): {url}")

                # 成功后延时（随机抖动防检测）
                delay = settings.douban_request_delay * (1 + random.random())
                time.sleep(delay)
                return text
        except RuntimeError:
            raise  # 反爬封锁直接抛出，不重试
        except Exception as e:
            last_error = e
            if attempt < settings.douban_http_max_retries - 1:
                # 指数退避 + 随机抖动
                backoff = settings.douban_request_delay * (2 ** attempt) * (1 + random.random())
                logger.warning(f"请求失败 (重试 {attempt+1}/{settings.douban_http_max_retries}): {url} - {e}, 等待 {backoff:.1f}s")
                time.sleep(backoff)

    raise RuntimeError(f"Failed to fetch {url} after {settings.douban_http_max_retries} retries: {last_error}")


def fetch_binary(url: str) -> bytes:
    """Fetch binary content (e.g., images) with retry and cookie."""
    cookie = _get_cookie()
    headers = get_headers(cookie)
    last_error = None

    for attempt in range(settings.douban_http_max_retries):
        try:
            with httpx.Client(headers=headers, follow_redirects=True, timeout=30) as client:
                resp = client.get(url)

                # 检测 WAF 封锁
                _check_waf_redirect(resp, url)

                resp.raise_for_status()
                time.sleep(settings.douban_request_delay)
                return resp.content
        except RuntimeError:
            raise  # 反爬封锁直接抛出，不重试
        except Exception as e:
            last_error = e
            if attempt < settings.douban_http_max_retries - 1:
                time.sleep(settings.douban_request_delay * (attempt + 1))

    raise RuntimeError(f"Failed to fetch {url} after {settings.douban_http_max_retries} retries: {last_error}")
