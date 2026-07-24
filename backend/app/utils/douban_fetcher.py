"""
Playwright-based Douban page fetcher (dispatch-thread architecture).

绕过豆瓣 PoW（SHA-512 工作量证明）反爬机制。
PoW 要求浏览器端执行 JavaScript 计算哈希碰撞，
纯 HTTP 客户端无法完成，需要真实浏览器引擎。

线程安全：Playwright 的 sync API 绑定到创建它的 greenlet/线程。
所有浏览器操作通过一个专用 dispatch 线程执行，外部调用通过 queue 提交任务，
通过 future 获取结果。保证单 Chromium 实例、无跨线程竞争。
"""
import queue
import re
import threading
import logging
import time

from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from app.config import settings

logger = logging.getLogger(__name__)


class PageFetchTimeout(Exception):
    """页面加载超时（区别于反爬封锁）。

    metadata backfill 使用短冷却（5-10s）并递增 meta_fetch_failures。
    与 AntiCrawlBlock 相同，多次超时会触发指数退避（最长 72 小时）。
    """
    pass


class AntiCrawlBlock(Exception):
    """豆瓣反爬封锁（PoW/CAPTCHA/异常请求检测）。

    metadata backfill 应使用长冷却并递增 meta_fetch_failures。
    """
    pass


_fetcher = None
_lock = threading.Lock()


def get_douban_fetcher():
    """获取全局单例 DoubanFetcher（线程安全，惰性初始化）。

    单例内部使用 dispatch thread 架构：所有 Playwright 操作
    在同一个专用线程中执行，外部调用通过 queue 提交任务。
    """
    global _fetcher
    with _lock:
        if _fetcher is None:
            _fetcher = DoubanFetcher()
        return _fetcher


def reset_douban_fetcher():
    """重置全局实例（用于测试或错误恢复）。"""
    global _fetcher
    with _lock:
        if _fetcher is not None:
            _fetcher.close()
            _fetcher = None


class DoubanFetcher:
    """Playwright 驱动的豆瓣页面获取器（dispatch-thread 架构）。

    专用 dispatch 线程运行 Chromium 浏览器。所有页面操作通过
    _cmd_queue 提交，通过 concurrent.futures.Future 返回结果。
    保证 Playwright 始终在同一个 greenlet 中执行，避免跨线程错误。

    每次 fetch 前会清除旧 cookie 并注入当前 cookie，
    确保 fetch_page_with_cookie 的 cookie 始终生效。
    """

    def __init__(self):
        self._cmd_queue = queue.Queue()
        self._worker_thread = None
        self._started = False
        self._closed = False
        self._start_lock = threading.Lock()

    def _ensure_worker(self):
        """确保 dispatch 线程正在运行。死线程自动 respawn。已关闭后拒绝启动。"""
        if self._closed:
            raise PageFetchTimeout("Fetcher 已关闭")

        if self._started and (
            self._worker_thread is None or not self._worker_thread.is_alive()
        ):
            # Worker 已崩溃——重置状态以便 respawn
            logger.warning("Dispatch 线程已崩溃，自动重启...")
            self._started = False
            self._worker_thread = None

        if not self._started:
            with self._start_lock:
                # 双重检查：锁内再次验证，防止 close() 并发修改
                if not self._started and not self._closed:
                    self._worker_thread = threading.Thread(
                        target=self._worker_loop,
                        daemon=True,
                        name="douban-fetcher-dispatch",
                    )
                    self._worker_thread.start()
                    self._started = True

    def fetch_page(self, url: str) -> str:
        """
        获取页面 HTML（自动处理 PoW 挑战）。

        Playwright 自动执行 PoW 页面的 JavaScript，
        浏览器完成 SHA-512 哈希碰撞后自动跳转回目标页。

        使用默认 Cookie（DOUBAN_COOKIE 环境变量或 http_client 配置）。

        Raises:
            AntiCrawlBlock: 检测到反爬封锁
            PageFetchTimeout: 页面加载超时或其他错误
        """
        return self.fetch_page_with_cookie(url, None)

    def fetch_page_with_cookie(self, url: str, cookie: str = None) -> str:
        """
        获取页面 HTML（使用指定 cookie）。

        cookie=None 时使用默认 cookie（环境变量）。
        每次调用都会在 dispatch 线程中清除旧 cookie 并注入新 cookie，
        确保 cookie 始终生效（即使浏览器已初始化）。

        Raises:
            AntiCrawlBlock: 检测到反爬封锁
            PageFetchTimeout: 页面加载超时或其他错误
        """
        self._ensure_worker()

        from concurrent.futures import Future
        future = Future()
        # cmd: ('fetch', url, cookie, future)
        self._cmd_queue.put(('fetch', url, cookie, future))

        timeout_ms = settings.playwright_timeout_ms
        try:
            return future.result(timeout=(timeout_ms / 1000) + 30)
        except TimeoutError:
            raise PageFetchTimeout(
                f"Dispatch 线程超时: {url}"
            )

    def close(self):
        """关闭浏览器释放资源，停止 dispatch 线程。

        设置 _closed=True 阻止后续 _ensure_worker 自动 respawn。
        如需重新使用，调用 reset_douban_fetcher() 后重新 get_douban_fetcher()。
        """
        self._closed = True
        if self._started:
            self._cmd_queue.put(('close',))
            if self._worker_thread and self._worker_thread.is_alive():
                self._worker_thread.join(timeout=10)
            self._started = False
            self._worker_thread = None

    # ── Dispatch 线程内部方法（以下全部在 _worker_thread 中执行） ──

    def _worker_loop(self):
        """Dispatch 线程主循环：初始化浏览器 → 处理命令 → 清理。"""
        pw = None
        browser = None
        context = None
        page = None
        init_error = None

        try:
            pw, browser, context, page = self._init_browser()
        except Exception as e:
            logger.error(f"Dispatch 线程浏览器初始化失败: {e}")
            init_error = e

        try:
            while True:
                cmd = self._cmd_queue.get()
                if cmd[0] == 'close':
                    break

                if cmd[0] != 'fetch':
                    continue

                _, url, cookie, future = cmd

                if init_error is not None:
                    if not future.done():
                        future.set_exception(
                            PageFetchTimeout(
                                f"浏览器初始化失败: {init_error}"
                            )
                        )
                    continue

                try:
                    html = self._handle_fetch(page, context, url, cookie)
                    if not future.done():
                        future.set_result(html)
                except Exception as e:
                    if not future.done():
                        future.set_exception(e)
        except Exception as e:
            logger.error(f"Dispatch 线程异常退出: {e}")
        finally:
            self._shutdown(pw, browser, context, page)

    def _init_browser(self):
        """初始化 Playwright + Chromium + context + page。"""
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=settings.playwright_headless)
        context = browser.new_context(
            user_agent=settings.douban_user_agent,
            locale="zh-CN",
        )
        page = context.new_page()
        return pw, browser, context, page

    def _shutdown(self, pw, browser, context, page):
        """关闭所有资源（容错）。"""
        for obj, name in [
            (page, "page"),
            (context, "context"),
            (browser, "browser"),
        ]:
            if obj:
                try:
                    obj.close()
                except Exception as e:
                    logger.warning(f"关闭 {name} 异常: {e}")
        if pw:
            try:
                pw.stop()
            except Exception as e:
                logger.warning(f"关闭 Playwright 异常: {e}")

    def _handle_fetch(self, page, context, url, cookie):
        """在 dispatch 线程中执行单次页面获取。

        每次调用前清除旧 cookie 并注入当前 cookie，
        确保 fetch_page_with_cookie 的 cookie 始终生效。
        """
        # 注入 cookie（每次 fetch 前刷新，不使用浏览器缓存的旧 cookie）
        context.clear_cookies()
        resolved_cookie = cookie if cookie else self._get_default_cookie()
        if resolved_cookie:
            cookies = []
            for part in resolved_cookie.split(";"):
                part = part.strip()
                if "=" in part:
                    name, value = part.split("=", 1)
                    cookies.append({
                        "name": name.strip(),
                        "value": value.strip(),
                        "domain": ".douban.com",
                        "path": "/",
                    })
            if cookies:
                context.add_cookies(cookies)

        try:
            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=settings.playwright_timeout_ms,
            )

            # HTTP 级别反爬/错误检测（429 限流、5xx 服务端错误等）
            if response and response.status in (429, 502, 503, 504):
                raise AntiCrawlBlock(
                    f"HTTP {response.status} 错误: {url}")

            # 等待 PoW 挑战完成（如果有）
            page.wait_for_timeout(3000)

            html = page.content()

            # 反爬/无效页面检测（仅检查页面头部，避免影评等正文内容误触发）
            head = html[:2000]
            if "检测到有异常请求" in head:
                raise AntiCrawlBlock(f"豆瓣反爬封锁: {url}")
            if "没有访问权限" in head:
                raise AntiCrawlBlock(f"没有访问权限: {url}")
            if "captcha" in page.url.lower():
                raise AntiCrawlBlock(f"CAPTCHA page: {url}")
            # PoW 挑战页未解出（Playwright 未能在等待期间完成哈希碰撞）
            # 使用与 http_client.py 一致的模式：name="tok" + name="cha" + sha512
            if 'name="tok"' in head and 'name="cha"' in head and "sha512" in head:
                raise AntiCrawlBlock(f"PoW 挑战页未解出: {url}")
            # 兜底：HTTP 错误页（当 status 未被捕获时，如页面重定向后的错误页）
            m = re.search(r'<title>\s*(429|502|503|504)\s+\w', head)
            if m:
                raise AntiCrawlBlock(
                    f"HTTP {m.group(1)} 错误页面: {url}")

            # 请求间隔
            time.sleep(settings.douban_page_delay)

            return html

        except PlaywrightTimeout:
            raise PageFetchTimeout(f"Playwright 超时: {url}")
        except (AntiCrawlBlock, PageFetchTimeout):
            raise
        except Exception as e:
            logger.error(f"Playwright 获取失败: {url} - {e}")
            raise PageFetchTimeout(f"Playwright 获取失败: {url}") from e

    @staticmethod
    def _get_default_cookie() -> str:
        """获取默认 cookie（环境变量）。"""
        from app.utils.http_client import _get_cookie
        return _get_cookie()
