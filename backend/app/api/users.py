from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Setting
from app.models.user import User
from app.schemas.user import SettingsResponse, SettingsUpdate, UserWatchedResponse
from app.dependencies import require_user, require_admin

router = APIRouter()


@router.get("/settings", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    cron = _get_setting(db, "cron_expression", "0 9 * * 1")
    user_cron = _get_setting(db, "user_scrape_cron", "")
    meta_cron = _get_setting(db, "metadata_cron", "")
    imdb_cron = _get_setting(db, "imdb_cron", "0 4 * * *")
    retry_interval = _get_setting(db, "retry_interval", "3600")
    max_retries = _get_setting(db, "max_retries", "3")
    return SettingsResponse(
        cron_expression=cron,
        user_scrape_cron=user_cron,
        metadata_cron=meta_cron,
        imdb_cron=imdb_cron,
        retry_interval=int(retry_interval),
        max_retries=int(max_retries),
    )


@router.put("/settings", response_model=SettingsResponse)
def update_settings(data: SettingsUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    from app.services.scheduler import scheduler

    if data.cron_expression is not None:
        _set_setting(db, "cron_expression", data.cron_expression)
        if data.cron_expression.strip():
            scheduler.reschedule(data.cron_expression)
        else:
            scheduler.remove_top250_job()

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
        else:
            scheduler.remove_meta_job()

    if data.imdb_cron is not None:
        _set_setting(db, "imdb_cron", data.imdb_cron)
        if data.imdb_cron.strip():
            scheduler.reschedule_imdb(data.imdb_cron)
        else:
            scheduler.remove_imdb_job()

    if data.retry_interval is not None:
        _set_setting(db, "retry_interval", str(data.retry_interval))

    if data.max_retries is not None:
        _set_setting(db, "max_retries", str(data.max_retries))

    return get_settings(db=db, admin=admin)


@router.get("/user/watched", response_model=UserWatchedResponse)
def get_watched(db: Session = Depends(get_db), user: User = Depends(require_user)):
    from app.services.user_scraper import get_watched_ids
    if not user.douban_user_id:
        return UserWatchedResponse(douban_ids=[])
    return UserWatchedResponse(douban_ids=get_watched_ids(db, user.douban_user_id))


def _get_setting(db: Session, key: str, default: str = "") -> str:
    setting = db.query(Setting).filter(Setting.key == key).first()
    # 区分 '行不存在'(→ default) vs '行存在但值为空字符串'(→ 返回空字符串)
    # 同时防护 value=NULL（手动编辑 DB 或迁移问题）
    if setting is None or setting.value is None:
        return default
    return setting.value


def _set_setting(db: Session, key: str, value: str):
    setting = db.query(Setting).filter(Setting.key == key).first()
    if not setting:
        setting = Setting(key=key, value=value)
        db.add(setting)
    else:
        setting.value = value
    db.commit()
