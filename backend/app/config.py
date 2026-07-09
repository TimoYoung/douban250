import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/douban250.db"
    posters_dir: Path = Path("./posters")
    douban_user_id: str = ""
    douban_cookie: str = ""
    douban_request_delay: float = 2.0
    douban_page_delay: float = 3.0       # Playwright 详情页请求间隔（秒）
    playwright_timeout_ms: int = 45000   # Playwright 页面加载超时（毫秒）
    playwright_headless: bool = True     # Playwright 无头模式
    douban_http_max_retries: int = 3  # HTTP 请求重试次数（区别于 DB Setting 的任务级 max_retries）
    douban_user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
    secret_key: str = "CHANGE-ME-IN-PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    default_admin_password: str = "admin123"
    log_level: str = "INFO"
    log_dir: Path = Path("./data/logs")
    log_max_bytes: int = 10 * 1024 * 1024  # 10MB per file
    log_backup_count: int = 5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
