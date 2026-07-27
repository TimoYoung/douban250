# 修复：Top 250 页面结构验证

## 问题

生产环境中 Playwright 成功获取了 Top 250 页面（无网络错误、无反爬检测触发），但解析返回 0 部电影。

**根本原因**：`douban_fetcher.py` 中的反爬检测只检查特定错误模式（如 PoW 挑战、HTTP 错误码），但不验证页面是否包含预期的内容结构。当豆瓣返回登录墙、地区限制页或其他非 Top 250 内容时，反爬检测不会触发，页面被当作"成功"返回，但解析时得到 0 部电影。

## 修复

### 1. 在 `_handle_fetch` 中添加页面结构验证

对于 Top 250 URL，检查 HTML 是否包含 `grid_view` 元素：

```python
if "top250" in url.lower():
    if "grid_view" not in html:
        # 记录诊断信息
        logger.error(...)
        raise AntiCrawlBlock(...)
```

### 2. 在 `crawler.py` 中添加解析结果验证

如果解析返回 0 部电影，立即失败并记录 HTML 片段：

```python
if len(page_movies) == 0:
    logger.error(f"HTML snippet: {html[:1000]}")
    raise RuntimeError(...)
```

### 3. 添加诊断脚本

`scripts/diagnose_playwright.py` 可在 Docker 环境中运行，捕获实际返回的 HTML 用于分析。

## 测试

新增 3 个测试用例：
- `test_top250_page_without_grid_view_raises_anticrawl`：验证缺少 grid_view 时抛出 AntiCrawlBlock
- `test_top250_page_with_grid_view_succeeds`：验证正常页面通过检查
- `test_non_top250_page_without_grid_view_succeeds`：验证非 Top 250 页面不受影响

全部 97 个测试通过。

## 下一步

部署此修复后：
1. 如果问题再次发生，日志将包含完整的 HTML 片段和页面标题
2. 可在 Docker 中运行诊断脚本：`docker exec -it <container> python /app/scripts/diagnose_playwright.py`
3. 根据 HTML 内容确定具体原因（登录墙？地区限制？Cookie 问题？）
