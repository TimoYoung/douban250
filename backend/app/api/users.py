from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Setting
from app.schemas.user import SettingsResponse, SettingsUpdate, UserWatchedResponse
from app.config import settings

router = APIRouter()


@router.get("/settings", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    cron = _get_setting(db, "cron_expression", settings.cron_expression)
    user_id = _get_setting(db, "douban_user_id", settings.douban_user_id)
    cookie = _get_setting(db, "douban_cookie", settings.douban_cookie)
    user_cron = _get_setting(db, "user_scrape_cron", "")
    meta_cron = _get_setting(db, "metadata_cron", "0 5 * * 0")
    return SettingsResponse(
        cron_expression=cron,
        douban_user_id=user_id,
        douban_cookie=cookie,
        user_scrape_cron=user_cron,
        metadata_cron=meta_cron,
    )


@router.put("/settings", response_model=SettingsResponse)
def update_settings(data: SettingsUpdate, db: Session = Depends(get_db)):
    from app.services.scheduler import scheduler

    if data.cron_expression is not None:
        _set_setting(db, "cron_expression", data.cron_expression)
        scheduler.reschedule(data.cron_expression)

    if data.douban_user_id is not None:
        _set_setting(db, "douban_user_id", data.douban_user_id)

    if data.douban_cookie is not None:
        _set_setting(db, "douban_cookie", data.douban_cookie)

    if data.user_scrape_cron is not None:
        _set_setting(db, "user_scrape_cron", data.user_scrape_cron)
        if data.user_scrape_cron.strip():
            scheduler.reschedule_user(data.user_scrape_cron)
        else:
            scheduler.remove_user_job()

    if data.metadata_cron is not None:
        _set_setting(db, "metadata_cron", data.metadata_cron)
        if data.metadata_cron.strip():
            scheduler.reschedule_meta(data.metadata_cron)

    return get_settings(db)


@router.get("/user/watched", response_model=UserWatchedResponse)
def get_watched(db: Session = Depends(get_db)):
    from app.services.user_scraper import get_watched_ids
    user_id = _get_setting(db, "douban_user_id", settings.douban_user_id)
    if not user_id:
        return UserWatchedResponse(douban_ids=[])
    return UserWatchedResponse(douban_ids=get_watched_ids(db, user_id))


def _get_setting(db: Session, key: str, default: str = "") -> str:
    setting = db.query(Setting).filter(Setting.key == key).first()
    return setting.value if setting and setting.value else default


def _set_setting(db: Session, key: str, value: str):
    setting = db.query(Setting).filter(Setting.key == key).first()
    if not setting:
        setting = Setting(key=key, value=value)
        db.add(setting)
    else:
        setting.value = value
    db.commit()
