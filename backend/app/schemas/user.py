from app.schemas import BeijingBaseModel


class SettingsResponse(BeijingBaseModel):
    cron_expression: str
    douban_user_id: str
    douban_cookie: str = ""
    user_scrape_cron: str = ""
    metadata_cron: str = ""


class SettingsUpdate(BeijingBaseModel):
    cron_expression: str | None = None
    douban_user_id: str | None = None
    douban_cookie: str | None = None
    user_scrape_cron: str | None = None
    metadata_cron: str | None = None


class UserWatchedResponse(BeijingBaseModel):
    douban_ids: list[str]
