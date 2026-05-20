import threading

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CrawlLog
from app.schemas.crawl import CrawlLogInfo, CrawlTriggerResponse
from app.services.crawler import crawl_progress
from app.services.metadata import meta_progress, get_meta_progress

router = APIRouter()


@router.post("", response_model=CrawlTriggerResponse)
def trigger_crawl(db: Session = Depends(get_db)):
    if crawl_progress["active"]:
        raise HTTPException(status_code=409, detail="A crawl is already running")

    thread = threading.Thread(target=_run_top250, daemon=True)
    thread.start()

    return CrawlTriggerResponse(message="Top 250 crawl triggered", triggered=True)


@router.post("/user-watched", response_model=CrawlTriggerResponse)
def trigger_user_scrape(full: bool = Query(False), db: Session = Depends(get_db)):
    if crawl_progress["active"]:
        raise HTTPException(status_code=409, detail="A crawl is already running")

    from app.config import settings
    user_id = settings.douban_user_id
    if not user_id:
        # Try from DB
        from app.models import Setting
        setting = db.query(Setting).filter(Setting.key == "douban_user_id").first()
        user_id = setting.value if setting and setting.value else ""

    if not user_id:
        raise HTTPException(status_code=400, detail="No douban_user_id configured")

    thread = threading.Thread(target=_run_user_scrape, args=(user_id, full), daemon=True)
    thread.start()
    msg = "User watched full sync triggered" if full else "User watched incremental sync triggered"

    return CrawlTriggerResponse(message=msg, triggered=True)


def _run_top250():
    from app.services.crawler import crawl_top250
    try:
        crawl_top250()
    except Exception:
        pass  # Already logged in crawler


def _run_user_scrape(user_id: str, full: bool = False):
    from app.services.user_scraper import scrape_user_watched
    try:
        scrape_user_watched(user_id, full=full)
    except Exception:
        pass  # Already logged in user_scraper


@router.get("/status")
def get_crawl_status(db: Session = Depends(get_db)):
    latest = db.query(CrawlLog).order_by(CrawlLog.started_at.desc()).first()
    if not latest:
        return {"status": "never_run"}
    return CrawlLogInfo.model_validate(latest)


@router.get("/status/top250")
def get_top250_status(db: Session = Depends(get_db)):
    latest = (
        db.query(CrawlLog)
        .filter(CrawlLog.job_type == "top250")
        .order_by(CrawlLog.started_at.desc())
        .first()
    )
    if not latest:
        return {"status": "never_run"}
    return CrawlLogInfo.model_validate(latest)


@router.get("/status/user-watched")
def get_user_watched_status(db: Session = Depends(get_db)):
    latest = (
        db.query(CrawlLog)
        .filter(CrawlLog.job_type == "user_watched")
        .order_by(CrawlLog.started_at.desc())
        .first()
    )
    if not latest:
        return {"status": "never_run"}
    return CrawlLogInfo.model_validate(latest)


@router.get("/progress")
def get_crawl_progress():
    return crawl_progress


@router.get("/logs", response_model=list[CrawlLogInfo])
def get_crawl_logs(limit: int = 20, db: Session = Depends(get_db)):
    logs = db.query(CrawlLog).order_by(CrawlLog.started_at.desc()).limit(limit).all()
    return [CrawlLogInfo.model_validate(log) for log in logs]


# --- Metadata backfill ---

@router.post("/metadata", response_model=CrawlTriggerResponse)
def trigger_metadata_backfill(force: bool = Query(False)):
    if meta_progress["active"]:
        raise HTTPException(status_code=409, detail="Metadata backfill is already running")
    if crawl_progress["active"]:
        raise HTTPException(status_code=409, detail="A crawl is already running")

    thread = threading.Thread(target=_run_metadata, args=(force,), daemon=True)
    thread.start()
    msg = "Metadata backfill triggered (force)" if force else "Metadata backfill triggered"
    return CrawlTriggerResponse(message=msg, triggered=True)


@router.get("/metadata/progress")
def get_metadata_progress():
    return get_meta_progress()


@router.get("/metadata/status")
def get_metadata_status(db: Session = Depends(get_db)):
    latest = (
        db.query(CrawlLog)
        .filter(CrawlLog.job_type == "metadata")
        .order_by(CrawlLog.started_at.desc())
        .first()
    )
    if not latest:
        return {"status": "never_run"}
    return CrawlLogInfo.model_validate(latest)


@router.get("/cookie-check")
def check_cookie():
    from app.services.metadata import check_cookie_valid
    return check_cookie_valid()


def _run_metadata(force: bool = False):
    from app.services.metadata import run_backfill
    try:
        run_backfill(force=force)
    except Exception:
        pass
