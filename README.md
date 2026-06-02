# 豆瓣 Top 250 电影追踪与分析系统

前后端分离的 B/S 架构应用，用于自动爬取、追踪和分析豆瓣 / IMDb Top 250 电影列表的变化。

## 功能特性

- **双平台爬取** — 支持豆瓣和 IMDb 两个平台的 Top 250 排行榜爬取，各自独立 Cron 定时
- **版本追踪** — 每次爬取若列表有变化则自动创建新版本，列表相同则跳过
- **版本对比** — 统一对比页面，自动识别同源时间对比 / 跨平台对比，支持任意两个版本的对比
- **IMDb 自动关联** — 优先用 IMDb ID 直接搜索豆瓣，降级到 suggest API + 详情页验证
- **待确认匹配** — 未自动关联的 IMDb 电影进入待确认队列，支持候选词条一键关联或手动输入
- **元数据自动补全** — 新电影自动抓取详情（导演、类型、演员、简介、海报等），已有电影定期补全
- **用户对比** — 配置豆瓣用户 ID 和 Cookie，自动同步"看过"列表，与 Top 250 做对比
- **增量同步** — 看过列表支持增量同步（仅抓取新标记）和全量同步（扫描全部并清理已删除）
- **Cookie 支持** — 配置豆瓣 Cookie 提升反爬能力，获取更完整的数据，支持手动验证有效性
- **可视化展示** — 海报视图、列表视图、气泡视图（一屏看 250 部电影）、排名历史折线图（按平台分图）
- **排名历史图** — 时间轴按实际日期比例展示，豆瓣和 IMDb 分别展示，禁用缩放手势
- **智能搜索** — 全局搜索支持跨平台结果，标注来源（豆瓣/IMDb），显示平台排名
- **版本管理** — 版本列表支持筛选平台、编辑日期、删除（含二次确认、孤立电影和海报自动清理）
- **Docker 部署** — 多阶段构建，一键启动，前后端打包为单一镜像
- **手动导入 Doulist** — 在设置页面输入豆瓣豆列链接和日期版本，手动创建历史版本
- **时区** — 所有时间均为北京时间（UTC+8）

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.12 · FastAPI · SQLAlchemy · httpx · BeautifulSoup4 · APScheduler · Playwright |
| 前端 | Vue 3 · Vite · Pinia · Vue Router · ECharts |
| 部署 | Docker · Docker Compose |
| 数据库 | SQLite（默认）· MySQL · PostgreSQL 可选 |

## 快速开始

### 方式一：Docker 部署（推荐）

**快速启动（无需克隆仓库）**

```bash
docker run -d \
  --name douban250 \
  -p 8000:8000 \
  -v ./data:/app/data \
  -v ./posters:/app/posters \
  -e DOUBAN_USER_ID=你的豆瓣用户ID \
  -e DOUBAN_COOKIE=你的Cookie \
  --restart unless-stopped \
  timoyoung/douban250:latest
```

启动后访问 http://localhost:8000

**或使用 Docker Compose（克隆仓库后）**

```bash
git clone https://github.com/TimoYoung/douban250.git
cd douban250
docker compose up -d
```

### 方式二：本地开发

**后端**

```bash
cd backend
uv sync
playwright install chromium
uv run uvicorn app.main:app --reload
```

**前端**

```bash
cd frontend
npm install
npm run dev
```

开发模式下前端会自动将 `/api` 和 `/posters` 请求代理到 `localhost:8000`

## 环境变量

在 `.env` 文件或 `docker-compose.yml` 中配置：

```bash
# 数据库（默认 SQLite）
DATABASE_URL=sqlite:///./data/douban250.db

# 豆瓣用户 ID（可选）
DOUBAN_USER_ID=

# 豆瓣 Cookie（可选）
DOUBAN_COOKIE=

# 豆瓣 Top 250 爬取定时任务（默认：每周日凌晨 3 点）
CRON_EXPRESSION=0 3 * * 0

# 请求间隔（秒），建议 2-5
DOUBAN_REQUEST_DELAY=2.0
```

## 定时任务

系统内置四个定时任务（均支持在设置页面配置）：

| 任务 | 默认 Cron | 说明 |
|------|-----------|------|
| 豆瓣 Top 250 爬取 | `0 3 * * 0`（周日 3:00） | 爬取列表，有变化时创建新版本并自动抓取新电影元数据 |
| IMDb Top 250 爬取 | 留空（不启用） | 爬取 IMDb 排行榜，自动关联豆瓣电影，未匹配的进入待确认队列 |
| 用户看过列表 | 默认不启用 | 配置后自动同步用户的"看过"列表（增量模式） |
| 元数据补全 | `0 5 * * 0`（周日 5:00） | 定期补全缺失的电影元数据（简介、导演、海报等） |

## Cookie 配置

配置豆瓣 Cookie 可以：
- 突破反爬限制，提高爬取成功率
- 访问完整的用户"看过"列表
- 获取更丰富的电影元数据

获取方式：登录豆瓣 → 打开浏览器开发者工具（F12）→ Network → 复制请求头中的 `Cookie` 字段

Cookie 可在设置页面配置和验证（支持手动检查有效性），系统会自动检测 Cookie 是否过期。

## 项目结构

```
douban250/
├── backend/
│   ├── app/
│   │   ├── api/               # REST API 路由
│   │   │   ├── movies.py      # 电影列表、详情、气泡、搜索
│   │   │   ├── versions.py    # 版本 CRUD、对比、删除预览
│   │   │   ├── crawl.py       # 爬取触发、状态、元数据补全
│   │   │   ├── users.py       # 设置、看过列表
│   │   │   └── pending_matches.py # 待确认匹配管理
│   │   ├── models/            # SQLAlchemy 数据模型
│   │   ├── schemas/           # Pydantic 请求/响应模型
│   │   ├── services/          # 业务逻辑
│   │   │   ├── crawler.py     # 豆瓣 Top 250 爬虫
│   │   │   ├── imdb_crawler.py # IMDb Top 250 爬虫（Playwright + 豆瓣关联）
│   │   │   ├── user_scraper.py # 用户看过列表爬虫（增量/全量）
│   │   │   ├── metadata.py    # 元数据补全、详情页解析
│   │   │   ├── doulist_importer.py # Doulist 导入服务
│   │   │   └── scheduler.py   # APScheduler 定时任务
│   │   ├── utils/             # HTTP 客户端、HTML 解析
│   │   ├── config.py          # 配置管理（Pydantic Settings）
│   │   ├── database.py        # 数据库引擎、自动迁移
│   │   └── main.py            # FastAPI 应用入口
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/               # Axios 请求封装
│   │   ├── components/        # 通用组件（ConfirmModal、PendingMatches 等）
│   │   ├── stores/            # Pinia 状态管理
│   │   └── views/             # 页面视图（MovieList、MovieDetail、Compare、Settings）
│   └── vite.config.js
├── docker/
│   └── entrypoint.sh
├── .github/workflows/
│   └── docker-publish.yml     # CI/CD：构建、推送、Release
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## API 接口

### 电影

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/movies` | 电影列表（分页、筛选、搜索） |
| GET | `/api/movies/search?q=xxx` | 全局搜索（跨版本跨平台，返回来源和排名） |
| GET | `/api/movies/bubbles` | 气泡视图数据（250 部全量） |
| GET | `/api/movies/{id}` | 电影详情（按数据库 ID） |
| GET | `/api/movies/by-douban/{douban_id}` | 电影详情（按豆瓣 ID） |

### 版本

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/versions` | 版本列表（按时间倒序） |
| GET | `/api/versions/{id}` | 版本详情 |
| PATCH | `/api/versions/{id}` | 修改版本日期 |
| DELETE | `/api/versions/{id}` | 删除版本（级联清理孤立电影、海报、待确认匹配） |
| GET | `/api/versions/{id}/delete-preview` | 删除预览（返回关联电影数、孤立数、待确认数） |
| GET | `/api/versions/compare` | 版本对比（同源：新增/移除/排名变化；跨源：仅A/仅B/排名差异） |

### 待确认匹配

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/pending-matches` | 待确认匹配列表（按 imdb_id 去重） |
| POST | `/api/pending-matches/resolve` | 处理匹配（accept/input/skip，按 imdb_id 全局生效） |

### 爬取与任务

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/crawl` | 手动触发豆瓣 Top 250 爬取 |
| POST | `/api/crawl/imdb` | 手动触发 IMDb Top 250 爬取 |
| POST | `/api/crawl/user-watched?full=false` | 手动触发用户看过列表同步（增量/全量） |
| POST | `/api/crawl/metadata?force=false` | 手动触发元数据补全 |
| POST | `/api/crawl/doulist` | 手动导入 Doulist 创建版本（body: `{url, tag}`） |
| GET | `/api/crawl/progress` | 豆瓣爬取实时进度 |
| GET | `/api/crawl/imdb/progress` | IMDb 爬取实时进度 |
| GET | `/api/crawl/metadata/progress` | 元数据补全实时进度 |
| GET | `/api/crawl/doulist/progress` | Doulist 导入实时进度 |
| GET | `/api/crawl/status` | 最近一次爬取状态 |
| GET | `/api/crawl/status/top250` | Top 250 爬取状态 |
| GET | `/api/crawl/status/user-watched` | 用户爬取状态 |
| GET | `/api/crawl/metadata/status` | 元数据补全状态 |
| GET | `/api/crawl/cookie-check` | Cookie 有效性检查 |
| GET | `/api/crawl/logs` | 爬取日志列表 |

### 配置与用户

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/settings` | 读取配置 |
| PUT | `/api/settings` | 更新配置（Cron、用户 ID、Cookie 等） |
| GET | `/api/user/watched` | 用户已看电影列表 |
| GET | `/api/health` | 健康检查 |

## 数据模型

- **Movie** — 电影实体（豆瓣 ID、IMDb ID、标题、元数据、简介、海报、detail_fetched 标记）
- **Version** — 版本快照（标签、来源平台 douban/imdb、状态、爬取时间、电影数量）
- **VersionEntry** — 版本与电影的多对多关联（排名、评分）
- **PendingMatch** — 待确认的 IMDb 匹配（关联版本、IMDb ID、候选列表、状态）
- **WatchedMovie** — 用户已看电影记录
- **Setting** — 系统配置（Cron、Cookie 等）
- **CrawlLog** — 爬取日志（任务类型、状态、耗时）

## 注意事项

- 豆瓣有反爬机制，请求间隔默认 2 秒，可通过 `DOUBAN_REQUEST_DELAY` 调整
- 配置 Cookie 可显著提升爬取成功率和数据完整性
- 遇到验证码时会自动停止并记录错误日志
- Cookie 过期可在设置页面手动检查并更新
- 用户"看过"列表爬取需要配置豆瓣用户 ID
- 元数据补全对纪录片等缺少演员字段的电影会自动跳过，不会无限重试
- IMDb 爬取依赖 Playwright（需安装 Chromium），首次运行需执行 `playwright install chromium`
- IMDb 爬取后未自动关联的电影会进入待确认队列，需在控制台手动处理
- 版本删除会自动清理无关联的电影条目和海报文件
