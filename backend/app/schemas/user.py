from app.schemas import BeijingBaseModel


class SettingsResponse(BeijingBaseModel):
    cron_expression: str
    user_scrape_cron: str = ""
    metadata_cron: str = ""
    imdb_cron: str = ""


class SettingsUpdate(BeijingBaseModel):
    cron_expression: str | None = None
    user_scrape_cron: str | None = None
    metadata_cron: str | None = None
    imdb_cron: str | None = None


class UserWatchedResponse(BeijingBaseModel):
    douban_ids: list[str]
