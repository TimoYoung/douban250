#!/usr/bin/env python3
"""
Cookie 注入深度诊断：验证 Playwright 是否真正发送了 Cookie。

问题背景：
  - 诊断发现 /mine 页面有/无 Cookie 结果相同（都报"没有访问权限"）
  - 但同一 Cookie 在浏览器中可以正常访问
  → 怀疑 Cookie 未正确注入到 Playwright 请求中

诊断方法：
  直接用 Playwright（不走 fetcher dispatch 线程）做两件事：
  1. 用 context.add_cookies() 注入 → 访问 → 检查请求头中的 Cookie
  2. 用 document.cookie 注入 → 访问 → 检查请求头中的 Cookie
  3. 对比两种方式的结果
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def parse_cookie_fields(cookie_str: str) -> list:
    """解析 Cookie 字符串，返回字段名列表。"""
    fields = []
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            name = part.split("=", 1)[0].strip()
            fields.append(name)
    return fields


def main():
    from app.utils.http_client import _get_cookie
    from app.config import settings
    from playwright.sync_api import sync_playwright

    cookie_str = _get_cookie()
    if not cookie_str:
        print("❌ 未配置 Cookie，无法诊断")
        return

    expected_fields = parse_cookie_fields(cookie_str)

    print("=" * 60)
    print("  Cookie 注入深度诊断")
    print("=" * 60)
    print(f"\nCookie 长度: {len(cookie_str)} 字符")
    print(f"字段数: {len(expected_fields)}")
    print(f"字段: {', '.join(expected_fields)}")

    # ── 测试 1: context.add_cookies() ──
    print(f"\n{'─' * 60}")
    print("测试 1: context.add_cookies() 注入")
    print(f"{'─' * 60}")

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

        # 注入 Cookie
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

        print(f"\n注入 {len(cookies)} 个 cookie...")
        if cookies:
            context.add_cookies(cookies)

        # 验证 context 中的 cookies
        ctx_cookies = context.cookies(["https://movie.douban.com/"])
        print(f"context.cookies() 返回 {len(ctx_cookies)} 个")
        for c in ctx_cookies:
            val_preview = c['value'][:40] + "..." if len(c['value']) > 40 else c['value']
            print(f"  {c['name']} = {val_preview}")
            print(f"    domain={c.get('domain')}, path={c.get('path')}, httpOnly={c.get('httpOnly')}, secure={c.get('secure')}")

        # 访问 /mine
        captured.clear()
        print(f"\n访问 /mine?status=collect ...")
        try:
            page.goto(
                "https://movie.douban.com/mine?status=collect",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"  导航异常: {e}")

        # 分析发送的 Cookie
        sent_cookie = captured.get("cookie", "")
        sent_fields = parse_cookie_fields(sent_cookie) if sent_cookie else []

        print(f"\n实际请求头中的 Cookie:")
        print(f"  长度: {len(sent_cookie)} 字符")
        print(f"  字段数: {len(sent_fields)}")
        if sent_fields:
            print(f"  字段: {', '.join(sent_fields)}")
        else:
            print(f"  ⚠️  无 Cookie 发送！")

        # 对比
        missing = set(expected_fields) - set(sent_fields)
        if missing:
            print(f"\n  ⚠️  预期但未发送的字段: {', '.join(missing)}")

        # 页面结果
        import re
        html = page.content()
        title_m = re.search(r'<title[^>]*>([^<]+)</title>', html[:2000])
        title = title_m.group(1).strip() if title_m else "N/A"
        print(f"\n页面标题: {title}")

        # ── 测试 2: 对比 Top 250 页面 ──
        print(f"\n{'─' * 60}")
        print("测试 2: 同一 Cookie 访问 Top 250")
        print(f"{'─' * 60}")

        captured.clear()
        print(f"访问 Top 250 ...")
        try:
            page.goto(
                "https://movie.douban.com/top250?start=0&filter=",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"  导航异常: {e}")

        sent_cookie2 = captured.get("cookie", "")
        sent_fields2 = parse_cookie_fields(sent_cookie2) if sent_cookie2 else []
        print(f"请求头 Cookie 字段数: {len(sent_fields2)}")

        html2 = page.content()
        title_m2 = re.search(r'<title[^>]*>([^<]+)</title>', html2[:2000])
        title2 = title_m2.group(1).strip() if title_m2 else "N/A"
        has_grid = "grid_view" in html2
        print(f"页面标题: {title2}")
        print(f"包含 grid_view: {has_grid}")

        # ── 测试 3: 通过 JS 设置 cookie 后访问 /mine ──
        print(f"\n{'─' * 60}")
        print("测试 3: document.cookie 注入（对照组）")
        print(f"{'─' * 60}")

        # 先导航到 douban 域
        page.goto("https://movie.douban.com/", wait_until="domcontentloaded")
        page.wait_for_timeout(1000)

        # 通过 JS 设置
        set_count = 0
        for part in cookie_str.split(";"):
            part = part.strip()
            if "=" in part:
                name, value = part.split("=", 1)
                page.evaluate(
                    f'document.cookie = "{name.strip()}={value.strip()}; path=/; domain=.douban.com"'
                )
                set_count += 1

        print(f"通过 JS 设置了 {set_count} 个 cookie")

        # 检查 document.cookie
        doc_cookies = page.evaluate("document.cookie")
        doc_fields = parse_cookie_fields(doc_cookies) if doc_cookies else []
        print(f"document.cookie 包含 {len(doc_fields)} 个字段: {', '.join(doc_fields)}")

        # 重新访问 /mine
        captured.clear()
        print(f"\n重新访问 /mine ...")
        try:
            page.goto(
                "https://movie.douban.com/mine?status=collect",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"  导航异常: {e}")

        sent_cookie3 = captured.get("cookie", "")
        sent_fields3 = parse_cookie_fields(sent_cookie3) if sent_cookie3 else []
        print(f"请求头 Cookie 字段数: {len(sent_fields3)}")

        html3 = page.content()
        title_m3 = re.search(r'<title[^>]*>([^<]+)</title>', html3[:2000])
        title3 = title_m3.group(1).strip() if title_m3 else "N/A"
        print(f"页面标题: {title3}")

        # ── 结论 ──
        print(f"\n{'=' * 60}")
        print("  诊断结论")
        print(f"{'=' * 60}")

        mine_ok1 = "登录" not in title and "访问权限" not in title
        mine_ok3 = "登录" not in title3 and "访问权限" not in title3

        print(f"\n测试 1 (context.add_cookies): /mine → {'✅ 正常' if mine_ok1 else '❌ 异常'} ({title})")
        print(f"  发送 Cookie 字段: {len(sent_fields)}/{len(expected_fields)}")
        print(f"测试 3 (document.cookie):    /mine → {'✅ 正常' if mine_ok3 else '❌ 异常'} ({title3})")
        print(f"  发送 Cookie 字段: {len(sent_fields3)}/{len(expected_fields)}")

        if not mine_ok1 and not mine_ok3:
            if len(sent_fields) == 0 and len(sent_fields3) == 0:
                print("\n🔍 两种方法都没有发送 Cookie → Playwright 请求拦截可能有误")
                print("   但页面仍返回了登录/权限错误，说明豆瓣检测到了无 cookie 访问")
            elif len(sent_fields) > 0:
                print(f"\n🔍 Cookie 已发送但页面仍拒绝 → 可能是 cookie 值不被豆瓣接受")
                print("   常见原因：dbcl2 包含设备绑定 token，与 Playwright 浏览器指纹不匹配")
                # 检查 dbcl2
                if "dbcl2" in expected_fields:
                    print("   dbcl2 字段存在于 Cookie 中 — 这是设备绑定 cookie")
                    print("   建议：在浏览器中重新登录后获取新 Cookie")

        if not mine_ok1 and mine_ok3:
            print("\n🔍 context.add_cookies 失败但 document.cookie 成功")
            print("   → Playwright 的 context.add_cookies API 有 bug 或 cookie 属性不匹配")

        if mine_ok1 and not mine_ok3:
            print("\n🔍 context.add_cookies 成功但 document.cookie 失败")
            print("   → document.cookie 无法设置 HttpOnly 的 cookie（正常行为）")

        browser.close()
    finally:
        pw.stop()


if __name__ == "__main__":
    main()
