# 豆瓣 Top 250 电影追踪与分析系统

前后端分离的 B/S 架构应用，用于自动爬取、追踪和分析豆瓣 Top 250 电影列表的变化。

## 功能特性

- **自动爬取** — 支持 Cron 定时或手动触发，爬取豆瓣 Top 250 电影列表及元数据（含海报）
- **版本追踪** — 每次爬取若列表有变化则自动创建新版本，列表相同则跳过
- **版本对比** — 对比任意两个版本，展示新增、移除、排名变化最大的电影
- **元数据自动补全** — 新电影自动抓取详情（导演、类型、演员、简介、海报等），已有电影定期补全
- **用户对比** — 配置豆瓣用户 ID 和 Cookie，自动同步"看过"列表，与 Top 250 做对比
- **Cookie 支持** — 配置豆瓣 Cookie 提升反爬能力，获取更完整的数据
- **可视化展示** — 海报视图、列表视图、气泡视图（一屏看 250 部电影）、排名历史折线图
- **排名变化** — 电影卡片和列表条目直观展示排名变动（新上榜 / 上升 / 下降）
- **灵活部署** — Docker 一键打包前后端，默认 SQLite，可配置 MySQL/PostgreSQL
- **时区** — 所有时间均为北京时间（UTC+8）

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11+ · FastAPI · SQLAlchemy · httpx · BeautifulSoup4 · APScheduler |
| 前端 | Vue 3 · Vite · Pinia · Vue Router · ECharts |
| 部署 | Docker · Docker Compose |
| 数据库 | SQLite（默认）· MySQL · PostgreSQL 可选 |

## 快速开始

### 方式一：Docker 部署（推荐）

```bash
docker compose up --build -d
```

启动后访问 http://localhost:8000

可通过环境变量配置（`.env` 文件或 `docker-compose.yml`）：

```bash
# .env
DOUBAN_USER_ID=你的豆瓣用户ID     # 可选
DOUBAN_COOKIE=你的豆瓣Cookie       # 可选，提升反爬能力
CRON_EXPRESSION=0 3 * * 0         # 每周日凌晨 3 点
DOUBAN_REQUEST_DELAY=2.0          # 请求间隔（秒）
```

### 方式二：本地开发

**后端**

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

**前端**

```bash
cd frontend
npm install
npm run dev
```

开发模式下前端会自动将 `/api` 和 `/posters` 请求代理到 `localhost:8000`

## 定时任务

系统内置三个定时任务（均支持在设置页面配置）：

| 任务 | 默认 Cron | 说明 |
|------|-----------|------|
| Top 250 爬取 | `0 3 * * 0`（周日 3:00） | 爬取列表，有变化时创建新版本并自动抓取新电影元数据 |
| 用户看过列表 | 默认不启用 | 配置后自动同步用户的"看过"列表 |
| 元数据补全 | `0 5 * * 0`（周日 5:00） | 定期补全缺失的电影元数据（导演、简介、海报等） |

## Cookie 配置

配置豆瓣 Cookie 可以：
- 突破反爬限制，提高爬取成功率
- 访问完整的用户"看过"列表
- 获取更丰富的电影元数据

获取方式：登录豆瓣 → 打开浏览器开发者工具（F12）→ Network → 复制请求头中的 `Cookie` 字段

Cookie 可在设置页面配置和验证，系统会自动检测 Cookie 是否过期。

## 项目结构

```
douban250/
├── backend/
│   ├── app/
│   │   ├── api/               # REST API 路由
│   │   │   ├── movies.py      # 电影列表、详情、气泡
│   │   │   ├── versions.py    # 版本列表、对比
│   │   │   ├── crawl.py       # 爬取触发、状态、元数据补全
│   │   │   └── users.py       # 设置、看过列表
│   │   ├── models/            # SQLAlchemy 数据模型
│   │   ├── schemas/           # Pydantic 请求/响应模型
│   │   ├── services/          # 业务逻辑
│   │   │   ├── crawler.py     # Top 250 爬虫
│   │   │   ├── user_scraper.py # 用户看过列表爬虫
│   │   │   ├── metadata.py    # 元数据补全、详情页解析
│   │   │   ├── scheduler.py   # APScheduler 定时任务
│   │   │   └── differ.py      # 版本差异计算
│   │   ├── utils/             # HTTP 客户端、HTML 解析
│   │   ├── config.py          # 配置管理（Pydantic Settings）
│   │   ├── database.py        # 数据库引擎
│   │   └── main.py            # FastAPI 应用入口
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/               # Axios 请求封装
│   │   ├── components/        # 通用组件
│   │   │   ├── MovieCard.vue  # 电影卡片（含排名变化）
│   │   │   ├── MovieBubble.vue# 气泡视图组件
│   │   │   ├── RankHistoryChart.vue # 排名历史折线图
│   │   │   ├── VersionDiff.vue# 版本对比展示
│   │   │   ├── CrawlStatus.vue# 爬取状态与进度
│   │   │   └── PaginationBar.vue # 分页组件
│   │   ├── stores/            # Pinia 状态管理
│   │   └── views/             # 页面视图
│   └── vite.config.js
├── docker/
│   └── entrypoint.sh
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## API 接口

### 电影

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/movies` | 电影列表（分页、筛选、搜索） |
| GET | `/api/movies/bubbles` | 气泡视图数据（250 部全量） |
| GET | `/api/movies/{id}` | 电影详情（按数据库 ID） |
| GET | `/api/movies/by-douban/{douban_id}` | 电影详情（按豆瓣 ID） |

### 版本

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/versions` | 版本列表（按时间倒序） |
| GET | `/api/versions/{id}` | 版本详情 |
| GET | `/api/versions/{id}/diff` | 版本对比（新增、移除、排名变化） |

### 爬取与任务

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/crawl` | 手动触发 Top 250 爬取 |
| POST | `/api/crawl/user-watched` | 手动触发用户看过列表同步 |
| POST | `/api/crawl/metadata` | 手动触发元数据补全（`?force=true` 强制重新抓取） |
| GET | `/api/crawl/progress` | 爬取实时进度 |
| GET | `/api/crawl/metadata/progress` | 元数据补全实时进度 |
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

## 数据库配置

默认使用 SQLite，数据存储在 `data/douban250.db`。

切换数据库需设置环境变量：

```bash
# MySQL
DATABASE_URL=mysql+pymysql://user:password@localhost/douban250

# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost/douban250
```

## 数据模型

- **Movie** — 电影实体（豆瓣 ID、标题、元数据、简介、海报等）
- **Version** — 版本快照（标签、爬取时间、电影数量）
- **VersionEntry** — 版本与电影的多对多关联（排名、评分）
- **WatchedMovie** — 用户已看电影记录
- **Setting** — 系统配置（Cron、Cookie 等）
- **CrawlLog** — 爬取日志（任务类型、状态、耗时）

## 注意事项

- 豆瓣有反爬机制，请求间隔默认 2 秒，可通过 `DOUBAN_REQUEST_DELAY` 调整
- 配置 Cookie 可显著提升爬取成功率和数据完整性
- 遇到验证码时会自动停止并记录错误日志
- Cookie 过期可在设置页面验证并更新
- 用户"看过"列表爬取需要配置豆瓣用户 ID
