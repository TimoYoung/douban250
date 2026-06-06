import threading

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CrawlLog
from app.models.user import User
from app.schemas.crawl import CrawlLogInfo, CrawlTriggerResponse
from app.services.crawler import crawl_progress
from app.services.metadata import meta_progress, get_meta_progress
from app.dependencies import require_user, require_admin

router = APIRouter()


@router.post("", response_model=CrawlTriggerResponse)
def trigger_crawl(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if crawl_progress["active"]:
        raise HTTPException(status_code=409, detail="A crawl is already running")

    thread = threading.Thread(target=_run_top250, daemon=True)
    thread.start()

    return CrawlTriggerResponse(message="Top 250 crawl triggered", triggered=True)


@router.post("/user-watched", response_model=CrawlTriggerResponse)
def trigger_user_scrape(full: bool = Query(False), user: User = Depends(require_user)):
    if crawl_progress["active"]:
        raise HTTPException(status_code=409, detail="A crawl is already running")

    if not user.douban_user_id:
        raise HTTPException(status_code=400, detail="请先在账户设置中配置您的豆瓣用户 ID")

    thread = threading.Thread(
        target=_run_user_scrape,
        args=(user.douban_user_id, full, user.douban_cookie or ""),
        daemon=True,
    )
    thread.start()
    msg = "User watched full sync triggered" if full else "User watched incremental sync triggered"

    return CrawlTriggerResponse(message=msg, triggered=True)


def _run_top250():
    from app.services.crawler import crawl_top250
    try:
        crawl_top250()
    except Exception:
        pass  # Already logged in crawler


def _run_user_scrape(user_id: str, full: bool = False, cookie: str = ""):
    from app.services.user_scraper import scrape_user_watched
    try:
        scrape_user_watched(user_id, full=full, cookie=cookie)
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
def trigger_metadata_backfill(force: bool = Query(False), mode: str = Query("incremental"), admin: User = Depends(require_admin)):
    if meta_progress["active"]:
        raise HTTPException(status_code=409, detail="Metadata backfill is already running")
    if crawl_progress["active"]:
        raise HTTPException(status_code=409, detail="A crawl is already running")

    thread = threading.Thread(target=_run_metadata, args=(force, mode), daemon=True)
    thread.start()
    label = "全量覆盖" if mode == "full" else ("强制补全" if force else "增量补全")
    return CrawlTriggerResponse(message=f"元数据{label}已启动", triggered=True)


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
def check_cookie(user: User = Depends(require_user)):
    from app.services.metadata import check_cookie_valid
    if not user.douban_cookie:
        return {"valid": False, "message": "未配置 Cookie"}
    return check_cookie_valid(cookie=user.douban_cookie)


def _run_metadata(force: bool = False, mode: str = "incremental"):
    from app.services.metadata import run_backfill
    try:
        run_backfill(force=force, mode=mode)
    except Exception:
        pass


# --- IMDb Top 250 ---

@router.post("/imdb", response_model=CrawlTriggerResponse)
def trigger_imdb_crawl(admin: User = Depends(require_admin)):
    from app.services.imdb_crawler import get_imdb_progress
    progress = get_imdb_progress()
    if progress["status"] == "running":
        raise HTTPException(status_code=409, detail="An IMDb crawl is already running")
    if crawl_progress["active"]:
        raise HTTPException(status_code=409, detail="A Douban crawl is already running")

    thread = threading.Thread(target=_run_imdb_crawl, daemon=True)
    thread.start()
    return CrawlTriggerResponse(message="IMDb Top 250 crawl triggered", triggered=True)


@router.get("/imdb/progress")
def get_imdb_crawl_progress():
    from app.services.imdb_crawler import get_imdb_progress
    return get_imdb_progress()


def _run_imdb_crawl():
    from app.services.imdb_crawler import crawl_imdb_top250
    from app.database import SessionLocal
    try:
        crawl_imdb_top250(SessionLocal)
    except Exception:
        pass
