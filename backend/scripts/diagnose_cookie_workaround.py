#!/usr/bin/env python3
"""
快速验证：通过 set_extra_http_headers 直接注入 Cookie 请求头。
绕过 context.add_cookies()，直接将 Cookie 作为 HTTP header 发送。
"""
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from app.utils.http_client import _get_cookie
    from app.config import settings
    from playwright.sync_api import sync_playwright

    cookie_str = _get_cookie()
    if not cookie_str:
        print("❌ 未配置 Cookie")
        return

    print(f"Cookie 长度: {len(cookie_str)} 字符")

    captured = {}

    def on_request(request):
        if "douban.com" in request.url:
            captured["cookie"] = request.headers.get("cookie", "")
            captured["url"] = request.url

    pw = sync_playwright().start()
    try:
        browser = pw.chromium.launch(headless=settings.playwright_headless)
        context = browser.new_context(
            user_agent=settings.douban_user_agent,
            locale="zh-CN",
        )
        page = context.new_page()
        page.on("request", on_request)

        # ── 方案 A: context.add_cookies()（当前方式） ──
        print(f"\n{'─' * 50}")
        print("方案 A: context.add_cookies()")
        print(f"{'─' * 50}")

        context.clear_cookies()
        cookies = []
        for part in cookie_str.split(";"):
            part = part.strip()
            if "=" in part:
                name, value = part.split("=", 1)
                cookies.append({
                    "name": name.strip(),
                    "value": value.strip(),
                    "domain": ".douban.com",
                    "path": "/",
                })
        context.add_cookies(cookies)

        captured.clear()
        page.goto("https://movie.douban.com/mine?status=collect",
                   wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

        html = page.content()
        title_m = re.search(r'<title[^>]*>([^<]+)</title>', html[:2000])
        title = title_m.group(1).strip() if title_m else "N/A"
        sent = captured.get("cookie", "")
        print(f"  请求 Cookie 长度: {len(sent)}")
        print(f"  页面标题: {title}")

        # ── 方案 B: set_extra_http_headers（绕过 cookie API） ──
        print(f"\n{'─' * 50}")
        print("方案 B: set_extra_http_headers()")
        print(f"{'─' * 50}")

        # 清除之前的 cookies 和 headers
        context.clear_cookies()
        page.set_extra_http_headers({})

        # 直接设置 Cookie header
        page.set_extra_http_headers({"Cookie": cookie_str})

        captured.clear()
        page.goto("https://movie.douban.com/mine?status=collect",
                   wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

        html2 = page.content()
        title_m2 = re.search(r'<title[^>]*>([^<]+)</title>', html2[:2000])
        title2 = title_m2.group(1).strip() if title_m2 else "N/A"
        sent2 = captured.get("cookie", "")
        print(f"  请求 Cookie 长度: {len(sent2)}")
        print(f"  页面标题: {title2}")
        print(f"  grid_view: {'grid_view' in html2}")

        # ── 结论 ──
        print(f"\n{'=' * 50}")
        if len(sent) == 0 and len(sent2) > 0:
            print("✅ 方案 B 成功发送了 Cookie！")
            if "登录" not in title2 and "访问权限" not in title2:
                print(f"✅ 方案 B 成功访问了 /mine 页面！")
                print(f"   建议：在 douban_fetcher.py 中改用 set_extra_http_headers")
            else:
                print(f"   但页面仍返回: {title2}")
                print(f"   → Cookie 已发送但被豆瓣拒绝（可能设备绑定问题）")
        elif len(sent) == 0 and len(sent2) == 0:
            print("❌ 两种方案都没有发送 Cookie")
            print("   → 可能是 Playwright 版本 bug 或 Chromium 配置问题")
        elif len(sent) > 0:
            print("✅ 方案 A 也能发送 Cookie（之前可能是误报）")

        browser.close()
    finally:
        pw.stop()


if __name__ == "__main__":
    main()
