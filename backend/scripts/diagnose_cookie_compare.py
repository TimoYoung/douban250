#!/usr/bin/env python3
"""
对比诊断脚本：在两个环境（本机 vs 生产 NAS）上运行，找出差异点。

用法：
  # 在 Docker 容器中：
  docker exec -it douban250-app-1 uv run python /app/scripts/diagnose_cookie_compare.py

  # 在本机开发环境：
  cd backend
  uv run python scripts/diagnose_cookie_compare.py

  # 指定 cookie（覆盖数据库中的值）：
  uv run python scripts/diagnose_cookie_compare.py --cookie "bid=xxx; ll=xxx"

此脚本会：
1. 检查 Cookie 来源（环境变量 vs 数据库）
2. 对比多个 URL 的返回结果
3. 测试有/无 Cookie 时的行为差异
4. 输出详细的诊断信息（Cookie 长度、页面标题、关键特征）

注意：脚本不会输出完整的 Cookie 值（安全考虑），只输出长度和部分字段名。
"""
import sys
import os
import re
import argparse

# 确保可以导入 app 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def print_section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def extract_title(html: str) -> str:
    m = re.search(r'<title[^>]*>([^<]+)</title>', html[:2000])
    return m.group(1).strip() if m else "N/A"


def analyze_cookie(cookie: str) -> dict:
    """分析 Cookie 结构（不输出完整值）。"""
    if not cookie:
        return {"length": 0, "fields": [], "summary": "未配置"}
    fields = []
    for part in cookie.split(";"):
        part = part.strip()
        if "=" in part:
            name = part.split("=", 1)[0].strip()
            fields.append(name)
    return {
        "length": len(cookie),
        "fields": fields,
        "summary": f"长度 {len(cookie)} 字符，字段: {', '.join(fields)}",
    }


def get_cookie_sources():
    """检查 Cookie 的多个来源。"""
    sources = {}

    # 1. 环境变量
    env_cookie = os.environ.get("DOUBAN_COOKIE", "")
    sources["env"] = {
        "value": env_cookie,
        "analysis": analyze_cookie(env_cookie),
    }

    # 2. 数据库
    try:
        from app.database import SessionLocal
        from app.models import Setting
        db = SessionLocal()
        try:
            row = db.query(Setting).filter(Setting.key == "douban_cookie").first()
            db_cookie = row.value if row and row.value else ""
            sources["db"] = {
                "value": db_cookie,
                "analysis": analyze_cookie(db_cookie),
            }
        finally:
            db.close()
    except Exception as e:
        sources["db"] = {"value": "", "analysis": {"summary": f"数据库读取失败: {e}"}}

    # 3. _get_cookie() 的最终结果（DB 优先，env 兜底）
    try:
        from app.utils.http_client import _get_cookie
        final_cookie = _get_cookie()
        sources["final"] = {
            "value": final_cookie,
            "analysis": analyze_cookie(final_cookie),
        }
    except Exception as e:
        sources["final"] = {"value": "", "analysis": {"summary": f"获取失败: {e}"}}

    return sources


def test_url(fetcher, url: str, cookie: str = None, label: str = ""):
    """测试单个 URL 的返回结果。"""
    try:
        if cookie is not None:
            html = fetcher.fetch_page_with_cookie(url, cookie)
        else:
            html = fetcher.fetch_page(url)

        title = extract_title(html)
        has_grid = "grid_view" in html
        has_login = "登录" in html[:2000]
        has_register = "注册" in html[:2000]
        has_pow = 'name="tok"' in html[:2000] and 'name="cha"' in html[:2000]
        html_len = len(html)

        status = "✅" if (has_grid or (not has_login and "top250" not in url)) else "❌"

        print(f"{status} {label or url}")
        print(f"   标题: {title}")
        print(f"   HTML 长度: {html_len}")
        print(f"   特征: grid_view={has_grid}, 登录={has_login}, 注册={has_register}, PoW={has_pow}")

        return {
            "title": title,
            "html_len": html_len,
            "has_grid_view": has_grid,
            "has_login": has_login,
            "html": html,
        }
    except Exception as e:
        print(f"❌ {label or url}")
        print(f"   错误: {type(e).__name__}: {e}")
        return {"error": str(e), "title": "ERROR"}


def main():
    parser = argparse.ArgumentParser(description="Cookie 和环境对比诊断")
    parser.add_argument("--cookie", type=str, default="",
                        help="指定 Cookie 值（覆盖数据库/环境变量中的值）")
    args = parser.parse_args()

    print_section("环境信息")
    print(f"Python: {sys.version}")
    print(f"工作目录: {os.getcwd()}")
    print(f"脚本路径: {os.path.abspath(__file__)}")

    # 检查 Playwright/Chromium 版本
    try:
        import playwright
        print(f"Playwright 版本: {playwright.__version__}")
    except Exception as e:
        print(f"Playwright 版本: 未知 ({e})")

    print_section("Cookie 来源分析")
    sources = get_cookie_sources()
    for name, info in sources.items():
        label = {"env": "环境变量 DOUBAN_COOKIE",
                 "db": "数据库 Setting",
                 "final": "_get_cookie() 最终结果"}.get(name, name)
        print(f"\n  [{label}]")
        print(f"  {info['analysis']['summary']}")

    # 检查各来源是否一致
    env_val = sources["env"]["value"]
    db_val = sources["db"]["value"]
    final_val = sources["final"]["value"]

    if env_val and db_val:
        if env_val == db_val:
            print(f"\n  ✅ 环境变量和数据库 Cookie 一致")
        else:
            print(f"\n  ⚠️  环境变量和数据库 Cookie 不一致！")
            print(f"     环境变量长度: {len(env_val)}, 数据库长度: {len(db_val)}")

    # 确定要使用的 Cookie
    test_cookie = args.cookie if args.cookie else final_val
    if args.cookie:
        print(f"\n  使用 --cookie 参数覆盖: {analyze_cookie(args.cookie)['summary']}")

    print_section("URL 测试（使用当前 Cookie）")
    from app.utils.douban_fetcher import get_douban_fetcher
    fetcher = get_douban_fetcher()

    urls = [
        ("https://movie.douban.com/top250?start=0&filter=", "Top 250 第 1 页"),
        ("https://movie.douban.com/mine?status=collect", "我的看过页"),
        ("https://movie.douban.com/", "豆瓣电影首页"),
    ]

    results = {}
    for url, label in urls:
        results[label] = test_url(fetcher, url, cookie=test_cookie, label=label)

    print_section("URL 测试（无 Cookie）")
    results_no_cookie = {}
    for url, label in urls:
        results_no_cookie[label] = test_url(fetcher, url, cookie="", label=f"{label}（无 Cookie）")

    # 对比结果
    print_section("诊断结论")

    top250 = results.get("Top 250 第 1 页", {})
    mine = results.get("我的看过页", {})
    top250_no_cookie = results_no_cookie.get("Top 250 第 1 页（无 Cookie）", {})

    if top250.get("has_grid_view"):
        print("✅ Top 250 页面正常（包含 grid_view），Cookie 有效且爬取应该成功")
    elif top250.get("title") == "ERROR":
        print(f"❌ Top 250 获取失败: {top250.get('error', '')}")
        if "登录" in top250.get("error", ""):
            print("   可能是登录墙或地区限制")
    else:
        title = top250.get("title", "N/A")
        if "登录" in title:
            print(f"❌ Top 250 返回登录页: {title}")
            # 对比无 Cookie 的情况
            if top250_no_cookie.get("title") == title:
                print("   ⚠️  有/无 Cookie 返回相同的登录页 → Cookie 可能未正确注入")
            else:
                print(f"   无 Cookie 时返回: {top250_no_cookie.get('title', 'N/A')}")
                print("   → Cookie 有差异但都不够，可能豆瓣要求重新登录")
        else:
            print(f"❌ Top 250 返回非预期页面: {title}")

    if mine.get("has_login") and not mine.get("has_grid_view"):
        print(f"\n⚠️  看过页也显示登录: {mine.get('title', 'N/A')}")
        print("   → Cookie 确实已过期")
    else:
        print(f"\n✅ 看过页正常: {mine.get('title', 'N/A')}")
        if top250.get("title") != mine.get("title") and "登录" in top250.get("title", ""):
            print("   → 看过页正常但 Top 250 要求登录，可能是豆瓣对 Top 250 的特殊限制")

    print_section("建议操作")
    if top250.get("has_grid_view"):
        print("✅ 环境正常，无需操作")
    else:
        print("""
1. 对比两个环境的输出差异，特别关注：
   - Cookie 来源（环境变量 vs 数据库）
   - Top 250 页面标题
   - 有/无 Cookie 的行为差异

2. 如果"有 Cookie"和"无 Cookie"返回相同的登录页：
   → Cookie 未正确注入到 Playwright 浏览器
   → 检查 Playwright 初始化是否有问题

3. 如果"有 Cookie"能访问看过页但不能访问 Top 250：
   → 豆瓣对 Top 250 有更严格的登录要求
   → 尝试在浏览器中手动访问 Top 250，确认是否需要登录

4. 如果需要手动测试，可以将 HTML 保存到文件：
   docker exec -it douban250-app-1 bash
   uv run python -c "
from app.utils.douban_fetcher import get_douban_fetcher
f = get_douban_fetcher()
html = f.fetch_page('https://movie.douban.com/top250?start=0&filter=')
open('/tmp/top250.html', 'w').write(html)
print('Saved to /tmp/top250.html, length:', len(html))
"
   # 然后查看 HTML
   head -n 50 /tmp/top250.html
""")

    fetcher.close()


if __name__ == "__main__":
    main()
