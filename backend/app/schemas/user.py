from app.schemas import BeijingBaseModel


class SettingsResponse(BeijingBaseModel):
    cron_expression: str
    user_scrape_cron: str = ""
    metadata_cron: str = ""
    imdb_cron: str = ""
    retry_interval: int = 3600
    max_retries: int = 3


class SettingsUpdate(BeijingBaseModel):
    cron_expression: str | None = None
    user_scrape_cron: str | None = None
    metadata_cron: str | None = None
    imdb_cron: str | None = None
    retry_interval: int | None = None
    max_retries: int | None = None


class UserWatchedResponse(BeijingBaseModel):
    douban_ids: list[str]
