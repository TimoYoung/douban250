#!/usr/bin/env python3
"""
诊断脚本：检查 Playwright 在 Docker 中返回的 HTML 结构

用法：
  docker exec -it douban250-backend-1 uv run python /app/scripts/diagnose_playwright.py

此脚本会：
1. 使用 Playwright 获取 Top 250 第一页
2. 检查 HTML 中是否包含关键选择器
3. 保存 HTML 到 /tmp/top250_diagnose.html
4. 输出详细的诊断信息
"""
import sys
import os

# 确保可以导入 app 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bs4 import BeautifulSoup
from app.utils.douban_fetcher import get_douban_fetcher
from app.utils.html_parser import parse_top250_page


def diagnose():
    print("=" * 70)
    print("Playwright Top 250 诊断工具")
    print("=" * 70)

    fetcher = get_douban_fetcher()

    try:
        print("\n[1/4] 获取 Top 250 第一页...")
        html = fetcher.fetch_page("https://movie.douban.com/top250?start=0&filter=")
        print(f"✅ 成功获取 HTML，长度: {len(html)} 字符")

        # 保存 HTML 到文件
        output_file = "/tmp/top250_diagnose.html"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"💾 HTML 已保存到: {output_file}")

        print("\n[2/4] 检查关键 HTML 结构...")
        soup = BeautifulSoup(html, "html.parser")

        checks = {
            "ol.grid_view": soup.select_one("ol.grid_view"),
            "ol.grid_view li": soup.select("ol.grid_view li"),
            "span.title": soup.select("span.title"),
            "span.rating_num": soup.select("span.rating_num"),
            "div.hd a": soup.select("div.hd a"),
        }

        all_passed = True
        for selector, result in checks.items():
            if isinstance(result, list):
                count = len(result)
                status = "✅" if count > 0 else "❌"
                print(f"{status} {selector}: {count} 个元素")
                if count == 0:
                    all_passed = False
            else:
                status = "✅" if result else "❌"
                print(f"{status} {selector}: {'存在' if result else '不存在'}")
                if not result:
                    all_passed = False

        print("\n[3/4] 尝试解析电影列表...")
        movies = parse_top250_page(html)
        print(f"解析结果: {len(movies)} 部电影")

        if len(movies) > 0:
            print(f"✅ 第一部电影: {movies[0].get('title', 'N/A')}")
        else:
            print("❌ 解析失败，未找到任何电影")

        print("\n[4/4] 检查页面标题和内容特征...")
        title_tag = soup.find("title")
        if title_tag:
            print(f"页面标题: {title_tag.text.strip()}")

        # 检查是否包含关键文本
        key_texts = ["电影", "Top 250", "肖申克的救赎", "rating_num"]
        for text in key_texts:
            found = text in html
            status = "✅" if found else "❌"
            print(f"{status} 包含文本 '{text}': {found}")

        print("\n" + "=" * 70)
        if all_passed and len(movies) == 25:
            print("✅ 诊断通过：HTML 结构正常，解析成功")
            print(f"\n💡 提示：你可以使用以下命令查看保存的 HTML：")
            print(f"   docker exec -it douban250-backend-1 head -n 100 {output_file}")
            return 0
        else:
            print("❌ 诊断失败：HTML 结构异常或解析失败")
            print(f"\n💡 建议操作：")
            print(f"   1. 查看保存的 HTML 文件:")
            print(f"      docker exec -it douban250-backend-1 cat {output_file}")
            print(f"   2. 检查 Docker 日志中的 HTML 片段")
            print(f"   3. 对比本地和 Docker 中的 Chromium 版本:")
            print(f"      docker exec -it douban250-backend-1 chromium --version")
            return 1

    except Exception as e:
        print(f"\n❌ 诊断过程出错: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 2
    finally:
        fetcher.close()


if __name__ == "__main__":
    sys.exit(diagnose())
