# 豆瓣 Top 250 电影追踪与分析系统

前后端分离的 B/S 架构应用，用于自动爬取、追踪和分析豆瓣 / IMDb Top 250 电影列表的变化。

## 功能特性

- **多用户系统** — JWT 认证，角色分级（管理员 / 普通用户），每个用户独立维护豆瓣 ID 和 Cookie
- **看过标记** — 登录用户可在电影列表、详情、气泡视图中看到自己的"看过"标记，游客无标记
- **双平台爬取** — 支持豆瓣和 IMDb 两个平台的 Top 250 排行榜爬取，各自独立 Cron 定时
- **版本追踪** — 每次爬取若列表有变化则自动创建新版本，列表相同则跳过
- **版本对比** — 统一对比页面，自动识别同源时间对比 / 跨平台对比，支持任意两个版本的对比
- **版本选择器** — 可折叠下拉组件，默认只展示当前年份，支持展开全部 / 按年收起
- **IMDb 自动关联** — 用 IMDb ID 直接搜索豆瓣，关联成功后自动触发元数据补全获取干净中文标题
- **待确认匹配** — 未自动关联的 IMDb 电影进入待确认队列，支持候选词条一键关联或手动输入
- **元数据自动补全** — 从详情页获取干净中文标题、导演、类型、演员、简介、海报等，已有电影定期补全
- **用户对比** — 配置豆瓣用户 ID 和 Cookie，自动同步"看过"列表，与 Top 250 做对比
- **增量同步** — 看过列表支持增量同步（仅抓取新标记）和全量同步（扫描全部并清理已删除）
- **Cookie 可选** — 配置豆瓣 Cookie 提升反爬能力，无 Cookie 也能正常使用基础功能
- **可视化展示** — 海报视图、列表视图、气泡视图（一屏看 250 部电影）、排名历史折线图（按平台分图）
- **排名历史图** — 时间轴按实际日期比例展示，豆瓣和 IMDb 分别展示，禁用缩放手势
- **智能搜索** — 全局搜索支持跨平台结果，标注来源（豆瓣/IMDb），显示平台排名
- **版本管理** — 版本列表支持筛选平台、编辑日期、删除（含二次确认、孤立电影和海报自动清理）
- **Docker 部署** — 多阶段构建，一键启动，前后端打包为单一镜像
- **时区** — 所有时间均为北京时间（UTC+8）

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.12 · FastAPI · SQLAlchemy · httpx · BeautifulSoup4 · APScheduler · Playwright · PyJWT · passlib |
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
  --restart unless-stopped \
  timoyoung/douban250:latest
```

启动后访问 http://localhost:8000，使用默认管理员账号登录：

- 用户名：`admin`
- 密码：`admin123`

> 首次登录后请立即修改密码。

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

## 用户与权限

系统有三种访问级别：

| 角色 | 说明 |
|------|------|
| 游客 | 可浏览电影列表、版本对比，不显示"看过"标记，无法访问控制台 |
| 普通用户 | 可管理自己的豆瓣配置、同步看过列表、修改密码 |
| 管理员 | 拥有全部功能：版本管理、元数据补全、爬取触发、用户管理、定时任务配置 |

管理员可在控制台的"用户管理"区域创建、编辑、删除用户。每个用户独立维护自己的豆瓣用户 ID 和 Cookie。

## 环境变量

在 `.env` 文件或 `docker-compose.yml` 中配置：

```bash
# 数据库（默认 SQLite）
DATABASE_URL=sqlite:///./data/douban250.db

# JWT 密钥（生产环境务必修改）
SECRET_KEY=CHANGE-ME-IN-PRODUCTION

# 默认管理员密码（仅首次启动时生效）
DEFAULT_ADMIN_PASSWORD=admin123

# 豆瓣 Top 250 爬取定时任务（默认：每周日凌晨 3 点）
CRON_EXPRESSION=0 3 * * 0

# 请求间隔（秒），建议 2-5
DOUBAN_REQUEST_DELAY=2.0
```

## 定时任务

系统内置四个定时任务（管理员可在控制台配置）：

| 任务 | 默认 Cron | 说明 |
|------|-----------|------|
| 豆瓣 Top 250 爬取 | `0 3 * * 0`（周日 3:00） | 爬取列表，有变化时创建新版本并自动抓取新电影元数据 |
| IMDb Top 250 爬取 | 留空（不启用） | 爬取 IMDb 排行榜，自动关联豆瓣电影，未匹配的进入待确认队列 |
| 用户看过列表 | 默认不启用 | 配置后自动同步所有活跃用户的"看过"列表（增量模式） |
| 元数据补全 | `0 5 * * 0`（周日 5:00） | 定期补全缺失的电影元数据（简介、导演、海报等） |

## 项目结构

```
douban250/
├── backend/
│   ├── app/
│   │   ├── api/               # REST API 路由
│   │   │   ├── auth.py        # 认证、用户管理端点
│   │   │   ├── movies.py      # 电影列表、详情、气泡、搜索
│   │   │   ├── versions.py    # 版本 CRUD、对比、删除预览
│   │   │   ├── crawl.py       # 爬取触发、状态、元数据补全
│   │   │   ├── users.py       # 全局设置、看过列表
│   │   │   └── pending_matches.py # 待确认匹配管理
│   │   ├── models/            # SQLAlchemy 数据模型
│   │   ├── schemas/           # Pydantic 请求/响应模型
│   │   ├── services/          # 业务逻辑
│   │   │   ├── crawler.py     # 豆瓣 Top 250 爬虫
│   │   │   ├── imdb_crawler.py # IMDb Top 250 爬虫（Playwright + 豆瓣关联）
│   │   │   ├── user_scraper.py # 用户看过列表爬虫（增量/全量）
│   │   │   ├── metadata.py    # 元数据补全、详情页解析
│   │   │   └── scheduler.py   # APScheduler 定时任务
│   │   ├── utils/             # HTTP 客户端、HTML 解析
│   │   ├── auth.py            # JWT 工具、密码哈希
│   │   ├── dependencies.py    # 认证依赖注入（get_current_user 等）
│   │   ├── config.py          # 配置管理（Pydantic Settings）
│   │   ├── database.py        # 数据库引擎、自动迁移
│   │   └── main.py            # FastAPI 应用入口
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/               # Axios 请求封装（含 JWT 拦截器）
│   │   ├── components/        # 通用组件（VersionDropdown、ConfirmModal、PendingMatches 等）
│   │   ├── stores/            # Pinia 状态管理（auth、movies、settings、versions）
│   │   └── views/             # 页面视图（MovieList、MovieDetail、Compare、Settings、Login）
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

### 认证

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/api/auth/login` | 公开 | 登录，返回 JWT |
| GET | `/api/auth/me` | 登录 | 获取当前用户信息 |
| PUT | `/api/auth/password` | 登录 | 修改密码 |
| PUT | `/api/auth/douban-settings` | 登录 | 修改自己的豆瓣配置 |
| GET | `/api/auth/users` | 管理员 | 用户列表 |
| POST | `/api/auth/users` | 管理员 | 创建用户 |
| PUT | `/api/auth/users/{id}` | 管理员 | 修改用户 |
| DELETE | `/api/auth/users/{id}` | 管理员 | 删除用户 |

### 电影

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/movies` | 电影列表（分页、筛选、搜索，登录用户返回看过状态） |
| GET | `/api/movies/search?q=xxx` | 全局搜索（跨版本跨平台，返回来源和排名） |
| GET | `/api/movies/bubbles` | 气泡视图数据（250 部全量） |
| GET | `/api/movies/{id}` | 电影详情（按数据库 ID） |
| GET | `/api/movies/by-douban/{douban_id}` | 电影详情（按豆瓣 ID） |

### 版本

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/api/versions` | 公开 | 版本列表（按时间倒序） |
| GET | `/api/versions/{id}` | 公开 | 版本详情 |
| PATCH | `/api/versions/{id}` | 管理员 | 修改版本日期 |
| DELETE | `/api/versions/{id}` | 管理员 | 删除版本（级联清理孤立电影、海报、待确认匹配） |
| GET | `/api/versions/{id}/delete-preview` | 管理员 | 删除预览 |
| GET | `/api/versions/compare` | 公开 | 版本对比 |

### 待确认匹配

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/api/pending-matches` | 管理员 | 待确认匹配列表（按 imdb_id 去重） |
| POST | `/api/pending-matches/resolve` | 管理员 | 处理匹配（accept/input/skip） |

### 爬取与任务

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/api/crawl` | 管理员 | 手动触发豆瓣 Top 250 爬取 |
| POST | `/api/crawl/imdb` | 管理员 | 手动触发 IMDb Top 250 爬取 |
| POST | `/api/crawl/user-watched` | 登录 | 手动触发看过列表同步（只需豆瓣用户 ID，Cookie 可选） |
| POST | `/api/crawl/metadata` | 管理员 | 手动触发元数据补全 |
| GET | `/api/crawl/progress` | 公开 | 实时进度 |
| GET | `/api/crawl/cookie-check` | 登录 | Cookie 有效性检查 |
| GET | `/api/crawl/logs` | 公开 | 爬取日志列表 |

### 配置

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/api/settings` | 管理员 | 读取全局配置（Cron） |
| PUT | `/api/settings` | 管理员 | 更新全局配置 |
| GET | `/api/health` | 公开 | 健康检查 |

## 数据模型

- **User** — 用户（用户名、密码哈希、角色、豆瓣 ID、Cookie、启用状态）
- **Movie** — 电影实体（豆瓣 ID、IMDb ID、标题、元数据、简介、海报）
- **Version** — 版本快照（标签、来源平台 douban/imdb、状态、爬取时间、电影数量）
- **VersionEntry** — 版本与电影的多对多关联（排名、评分）
- **PendingMatch** — 待确认的 IMDb 匹配（关联版本、IMDb ID、候选列表、状态）
- **WatchedMovie** — 用户已看电影记录（按豆瓣用户 ID 隔离）
- **Setting** — 系统全局配置（Cron 表达式等）
- **CrawlLog** — 爬取日志（任务类型、状态、耗时）

## 注意事项

- 豆瓣有反爬机制，请求间隔默认 2 秒，可通过 `DOUBAN_REQUEST_DELAY` 调整
- 系统采用指数退避 + 随机抖动策略应对反爬，遇到 PoW 挑战页会自动冷却等待
- Cookie 可选配置：有 Cookie 反爬保护更强，无 Cookie 也能访问豆瓣公开页面
- 看过列表同步只需配置豆瓣用户 ID，Cookie 可选（有则携带，无也能同步）
- 元数据补全对纪录片等缺少演员字段的电影会自动跳过，不会无限重试
- IMDb 爬取依赖 Playwright（需安装 Chromium），首次运行需执行 `playwright install chromium`
- IMDb 爬取使用豆瓣 abstract API 轻量验证，干净中文标题由元数据补全从详情页获取
- IMDb 爬取完成后自动触发元数据补全（后台线程）
- 版本删除会自动清理无关联的电影条目和海报文件
- 首次部署默认管理员账号 `admin` / `admin123`，请及时修改密码
- 生产环境请修改 `SECRET_KEY` 环境变量
