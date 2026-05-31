# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

豆瓣电影 Top 250 排行榜历史追踪系统。自动定期爬取豆瓣 Top 250 并保存版本，支持版本对比、用户"看过"列表同步、Doulist 历史榜单导入。

## Commands

### Backend (Python)
```bash
cd backend
uv sync                                          # Install dependencies
uv run uvicorn app.main:app --reload             # Dev server on :8000
uv run python -m uvicorn app.main:app --reload    # Alternative if above fails
```

### Frontend (Vue 3)
```bash
cd frontend
npm install    # Install dependencies
npm run dev    # Dev server on :5173, proxies /api + /posters to :8000
npm run build  # Build to backend/static/
```

### Docker
```bash
docker compose up -d                              # Full stack
docker run -d --name douban250 -p 8000:8000 timoyoung/douban250:latest
```

## Architecture

### Backend (`backend/app/`)
分层架构：API → Services → Models

- **`api/`** — FastAPI 路由：`movies.py`（电影列表/详情/气泡图）、`versions.py`（版本 CRUD + diff）、`crawl.py`（爬取触发/进度）、`users.py`（设置/看过列表）
- **`services/`** — 业务逻辑：`crawler.py`（Top 250 爬取）、`doulist_importer.py`（Doulist 导入）、`user_scraper.py`（用户看过同步）、`metadata.py`（元数据补全）、`differ.py`（版本 diff 计算）、`scheduler.py`（APScheduler 定时任务）
- **`models/`** — SQLAlchemy 模型：`Movie`、`Version`（`tag` 唯一）、`VersionEntry`（多对多 join 表，`version_id+movie_id` 和 `version_id+rank` 唯一约束）、`Setting`（KV 存储）、`CrawlLog`
- **`schemas/`** — Pydantic 请求/响应模型，继承 `BeijingBaseModel`（自动 UTC+8 时区）
- **`config.py`** — Pydantic Settings，环境变量驱动
- **`database.py`** — SQLAlchemy engine，启动时自动 `init_db()` 建表

### Frontend (`frontend/src/`)
Vue 3 Composition API + Pinia + Vue Router

- **`api/index.js`** — Axios 封装，所有后端调用集中在这里
- **`stores/`** — `movies.js`（电影列表/分页/过滤）、`settings.js`（控制台：爬取/导入/版本管理/账户）、`versions.js`（版本选择/diff）
- **`views/`** — `MovieListView.vue`（海报/列表/气泡三种视图）、`MovieDetailView.vue`（详情+排名历史图表）、`SettingsView.vue`（控制台：版本管理+数据维护+账户）、`VersionDiffView.vue`（版本对比）
- **`components/`** — `MovieCard.vue`、`MovieListTable.vue`、`BubbleGrid.vue`、`PaginationBar.vue`、`VersionSelector.vue`、`VersionDiff.vue`、`RankHistoryChart.vue`（ECharts）

### 关键数据流
1. 爬取/导入 → 创建 `Version` + `VersionEntry` 记录 → 新电影自动获取详情
2. 前端轮询 `/api/crawl/progress` 等端点实现实时进度展示（2s 间隔）
3. 版本 diff 由 `differ.py` 计算：新增/移除/排名升降

## Environment Variables

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | 数据库连接 | `sqlite:///./data/douban250.db` |
| `DOUBAN_USER_ID` | 豆瓣用户 ID（看过列表同步） | — |
| `DOUBAN_COOKIE` | 豆瓣 Cookie（反爬） | — |
| `DOUBAN_REQUEST_DELAY` | 请求间隔秒数 | `2.0` |

## Conventions

- 时间统一 UTC+8，通过 `app.utils.now()` 获取
- 所有爬取操作（crawl/metadata/doulist）用内存 dict 跟踪进度，前端轮询
- 长耗时操作在后台线程执行（`threading.Thread`），不阻塞 API 响应
- 后端 API 前缀 `/api`，前端 Vite dev server 代理到 `localhost:8000`
- Python 包管理用 `uv`，不用 pip
