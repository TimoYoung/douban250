import time
import httpx

from app.config import settings


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


def fetch_page(url: str, cookie: str = "") -> str:
    """Fetch a page with retry and delay. Optionally pass cookie for auth."""
    if not cookie:
        cookie = _get_cookie()
    headers = get_headers(cookie)
    last_error = None

    for attempt in range(settings.max_retries):
        try:
            with httpx.Client(headers=headers, follow_redirects=True, timeout=30) as client:
                resp = client.get(url)
                resp.raise_for_status()

                # Check for CAPTCHA/block
                if "检测到有异常请求" in resp.text or "captcha" in resp.url.path.lower():
                    raise RuntimeError(f"CAPTCHA or block detected for {url}")

                time.sleep(settings.douban_request_delay)
                return resp.text
        except Exception as e:
            last_error = e
            if attempt < settings.max_retries - 1:
                time.sleep(settings.douban_request_delay * (attempt + 1))

    raise RuntimeError(f"Failed to fetch {url} after {settings.max_retries} retries: {last_error}")


def fetch_binary(url: str) -> bytes:
    """Fetch binary content (e.g., images) with retry."""
    headers = get_headers()
    last_error = None

    for attempt in range(settings.max_retries):
        try:
            with httpx.Client(headers=headers, follow_redirects=True, timeout=30) as client:
                resp = client.get(url)
                resp.raise_for_status()
                time.sleep(settings.douban_request_delay)
                return resp.content
        except Exception as e:
            last_error = e
            if attempt < settings.max_retries - 1:
                time.sleep(settings.douban_request_delay * (attempt + 1))

    raise RuntimeError(f"Failed to fetch {url} after {settings.max_retries} retries: {last_error}")
