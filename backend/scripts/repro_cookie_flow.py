#!/usr/bin/env python3
"""
Reproduce user's exact flow: paste cookie → save via API-like call → check → crawl.

Usage:
  uv run python scripts/repro_cookie_flow.py "cookie_string_here"

This simulates what happens when user pastes a cookie in the UI.
"""
import sys
import re

if len(sys.argv) < 2:
    print("Usage: uv run python scripts/repro_cookie_flow.py \"cookie_string\"")
    sys.exit(1)

INPUT_COOKIE = sys.argv[1]
print(f"输入 Cookie 长度: {len(INPUT_COOKIE)}")
print(f"输入 Cookie: {INPUT_COOKIE[:80]}...")

# ── Step 1: 模拟 UI 保存（PUT /api/auth/douban-settings）──
print(f"\n{'='*60}")
print("Step 1: 保存 Cookie 到 admin User（模拟 UI 保存）")
print(f"{'='*60}")

from app.database import SessionLocal
from app.models import User

db = SessionLocal()
admin = db.query(User).filter(User.role == "admin").first()
if not admin:
    print("❌ 未找到 admin 用户")
    sys.exit(2)

admin.douban_cookie = INPUT_COOKIE
db.commit()
print(f"✅ 已保存到 admin (id={admin.id})")

# ── Step 2: 验证数据库存储 ──
print(f"\n{'='*60}")
print("Step 2: 从数据库读回并对比")
print(f"{'='*60}")

db.expire_all()
db.refresh(admin)
stored = admin.douban_cookie
print(f"存储长度: {len(stored) if stored else 0}")
print(f"与输入一致: {stored == INPUT_COOKIE}")
if stored != INPUT_COOKIE:
    print(f"❌ Cookie 被篡改！")
    print(f"  输入:  {INPUT_COOKIE[:80]}")
    print(f"  存储:  {(stored or '')[:80]}")
db.close()

# ── Step 3: 验证 _get_cookie() 解析 ──
print(f"\n{'='*60}")
print("Step 3: _get_cookie() 返回值")
print(f"{'='*60}")

from app.utils.http_client import _get_cookie
resolved = _get_cookie()
print(f"_get_cookie() 长度: {len(resolved)}")
print(f"与输入一致: {resolved == INPUT_COOKIE}")

# ── Step 4: 模拟 cookie 检查 ──
print(f"\n{'='*60}")
print("Step 4: check_cookie_valid (admin cookie)")
print(f"{'='*60}")

from app.utils.douban_fetcher import reset_douban_fetcher
reset_douban_fetcher()

from app.services.metadata import check_cookie_valid
result = check_cookie_valid(cookie=resolved)
print(f"valid: {result['valid']}")
print(f"message: {result['message']}")

# ── Step 5: 直接用 fetcher 测试 Top 250 ──
print(f"\n{'='*60}")
print("Step 5: fetcher.fetch_page Top 250")
print(f"{'='*60}")

reset_douban_fetcher()
from app.utils.douban_fetcher import get_douban_fetcher
fetcher = get_douban_fetcher()
try:
    html = fetcher.fetch_page("https://movie.douban.com/top250?start=0&filter=")
    title_m = re.search(r'<title[^>]*>([^<]+)</title>', html[:1000])
    title = title_m.group(1).strip() if title_m else "N/A"
    print(f"标题: {title}")
    print(f"grid_view: {'grid_view' in html}")
    print(f"HTML: {len(html)} 字节")
    STEP5_OK = "grid_view" in html
except Exception as e:
    print(f"❌ {type(e).__name__}: {e}")
    STEP5_OK = False
fetcher.close()

# ── Step 6: 对比直接用 Playwright（绕过 fetcher）──
print(f"\n{'='*60}")
print("Step 6: 直接用 Playwright（绕过 fetcher 单例）")
print(f"{'='*60}")

from playwright.sync_api import sync_playwright
from app.config import settings

pw = sync_playwright().start()
try:
    browser = pw.chromium.launch(headless=settings.playwright_headless)
    context = browser.new_context(
        user_agent=settings.douban_user_agent, locale="zh-CN")
    page = context.new_page()
    page.set_extra_http_headers({"Cookie": resolved})
    page.goto(
        "https://movie.douban.com/top250?start=0&filter=",
        wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(5000)
    html = page.content()
    title_m = re.search(r'<title[^>]*>([^<]+)</title>', html[:1000])
    title = title_m.group(1).strip() if title_m else "N/A"
    print(f"标题: {title}")
    print(f"grid_view: {'grid_view' in html}")
    print(f"HTML: {len(html)} 字节")
    STEP6_OK = "grid_view" in html
    browser.close()
finally:
    pw.stop()

# ── 总结 ──
print(f"\n{'='*60}")
print("诊断总结")
print(f"{'='*60}")
print(f"  存储一致:      {'✅' if stored == INPUT_COOKIE else '❌'}")
print(f"  _get_cookie:   {'✅' if resolved == INPUT_COOKIE else '❌'}")
print(f"  cookie check:  {'✅' if result['valid'] else '❌'} ({result['message']})")
print(f"  fetcher 爬取:  {'✅' if STEP5_OK else '❌'}")
print(f"  直接 Playwright: {'✅' if STEP6_OK else '❌'}")

if STEP6_OK and not STEP5_OK:
    print("\n🔍 直接 Playwright 成功但 fetcher 失败 → fetcher 内部有 bug")
elif STEP6_OK and STEP5_OK and not result["valid"]:
    print("\n🔍 爬取成功但 cookie check 失败 → check_cookie_valid 有 bug")
elif stored != INPUT_COOKIE:
    print("\n🔍 Cookie 存储被篡改 → API 或 DB 层有 bug")
elif resolved != INPUT_COOKIE:
    print("\n🔍 _get_cookie 返回错误值 → 解析逻辑有 bug")
elif not STEP6_OK:
    print("\n🔍 直接 Playwright 也失败 → Cookie 本身无效或 IP 被封")
