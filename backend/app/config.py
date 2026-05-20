import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/douban250.db"
    posters_dir: Path = Path("./posters")
    cron_expression: str = "0 3 * * 0"  # Weekly Sunday 3am
    douban_user_id: str = ""
    douban_cookie: str = ""
    douban_request_delay: float = 2.0
    max_retries: int = 3
    douban_user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
