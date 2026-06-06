import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.database import SessionLocal
from app.models import Setting

logger = logging.getLogger(__name__)


class CrawlScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._top250_job_id = "crawl_top250"
        self._user_job_id = "crawl_user_watched"
        self._meta_job_id = "metadata_backfill"
        self._imdb_job_id = "crawl_imdb"

    def start(self):
        """Start the scheduler with configured cron expressions."""
        top250_cron = self._get_setting("cron_expression", settings.cron_expression)
        user_cron = self._get_setting("user_scrape_cron", "")
        meta_cron = self._get_setting("metadata_cron", "0 5 * * 0")  # Default: Sunday 5am

        self._schedule_top250(top250_cron)
        if user_cron:
            self._schedule_user(user_cron)
        if meta_cron:
            self._schedule_meta(meta_cron)

        imdb_cron = self._get_setting("imdb_cron", "")
        if imdb_cron:
            self._schedule_imdb(imdb_cron)

        self.scheduler.start()
        logger.info(f"Scheduler started. Top250: {top250_cron}, User: {user_cron or 'disabled'}, Metadata: {meta_cron}, IMDb: {imdb_cron or 'disabled'}")

    def shutdown(self, wait: bool = True):
        self.scheduler.shutdown(wait=wait)

    def reschedule(self, cron_expression: str):
        """Reschedule the top250 crawl job."""
        self._set_setting("cron_expression", cron_expression)
        try:
            self.scheduler.reschedule_job(self._top250_job_id, trigger=CronTrigger.from_crontab(cron_expression))
            logger.info(f"Top250 rescheduled to: {cron_expression}")
        except Exception:
            self._schedule_top250(cron_expression)

    def reschedule_user(self, cron_expression: str):
        """Reschedule the user watched scrape job."""
        self._set_setting("user_scrape_cron", cron_expression)
        try:
            self.scheduler.reschedule_job(self._user_job_id, trigger=CronTrigger.from_crontab(cron_expression))
            logger.info(f"User scrape rescheduled to: {cron_expression}")
        except Exception:
            self._schedule_user(cron_expression)

    def remove_user_job(self):
        """Remove the user scrape cron job."""
        self._set_setting("user_scrape_cron", "")
        try:
            self.scheduler.remove_job(self._user_job_id)
            logger.info("User scrape job removed")
        except Exception:
            pass

    def reschedule_meta(self, cron_expression: str):
        """Reschedule the metadata backfill job."""
        self._set_setting("metadata_cron", cron_expression)
        try:
            self.scheduler.reschedule_job(self._meta_job_id, trigger=CronTrigger.from_crontab(cron_expression))
            logger.info(f"Metadata backfill rescheduled to: {cron_expression}")
        except Exception:
            self._schedule_meta(cron_expression)

    def reschedule_imdb(self, cron_expression: str):
        """Reschedule the IMDb crawl job."""
        self._set_setting("imdb_cron", cron_expression)
        try:
            self.scheduler.reschedule_job(self._imdb_job_id, trigger=CronTrigger.from_crontab(cron_expression))
            logger.info(f"IMDb crawl rescheduled to: {cron_expression}")
        except Exception:
            self._schedule_imdb(cron_expression)

    def remove_imdb_job(self):
        """Remove the IMDb crawl cron job."""
        self._set_setting("imdb_cron", "")
        try:
            self.scheduler.remove_job(self._imdb_job_id)
            logger.info("IMDb crawl job removed")
        except Exception:
            pass

    def _get_setting(self, key: str, default: str = "") -> str:
        db = SessionLocal()
        try:
            setting = db.query(Setting).filter(Setting.key == key).first()
            return setting.value if setting and setting.value else default
        finally:
            db.close()

    def _set_setting(self, key: str, value: str):
        db = SessionLocal()
        try:
            setting = db.query(Setting).filter(Setting.key == key).first()
            if not setting:
                setting = Setting(key=key, value=value)
                db.add(setting)
            else:
                setting.value = value
            db.commit()
        finally:
            db.close()

    def _schedule_top250(self, cron_expression: str):
        parts = cron_expression.strip().split()
        self.scheduler.add_job(
            _run_top250,
            trigger=CronTrigger(
                minute=parts[0] if len(parts) > 0 else "*",
                hour=parts[1] if len(parts) > 1 else "*",
                day=parts[2] if len(parts) > 2 else "*",
                month=parts[3] if len(parts) > 3 else "*",
                day_of_week=parts[4] if len(parts) > 4 else "*",
            ),
            id=self._top250_job_id,
            replace_existing=True,
        )

    def _schedule_user(self, cron_expression: str):
        parts = cron_expression.strip().split()
        self.scheduler.add_job(
            _run_user_scrape,
            trigger=CronTrigger(
                minute=parts[0] if len(parts) > 0 else "*",
                hour=parts[1] if len(parts) > 1 else "*",
                day=parts[2] if len(parts) > 2 else "*",
                month=parts[3] if len(parts) > 3 else "*",
                day_of_week=parts[4] if len(parts) > 4 else "*",
            ),
            id=self._user_job_id,
            replace_existing=True,
        )

    def _schedule_meta(self, cron_expression: str):
        parts = cron_expression.strip().split()
        self.scheduler.add_job(
            _run_metadata,
            trigger=CronTrigger(
                minute=parts[0] if len(parts) > 0 else "*",
                hour=parts[1] if len(parts) > 1 else "*",
                day=parts[2] if len(parts) > 2 else "*",
                month=parts[3] if len(parts) > 3 else "*",
                day_of_week=parts[4] if len(parts) > 4 else "*",
            ),
            id=self._meta_job_id,
            replace_existing=True,
        )

    def _schedule_imdb(self, cron_expression: str):
        parts = cron_expression.strip().split()
        self.scheduler.add_job(
            _run_imdb,
            trigger=CronTrigger(
                minute=parts[0] if len(parts) > 0 else "*",
                hour=parts[1] if len(parts) > 1 else "*",
                day=parts[2] if len(parts) > 2 else "*",
                month=parts[3] if len(parts) > 3 else "*",
                day_of_week=parts[4] if len(parts) > 4 else "*",
            ),
            id=self._imdb_job_id,
            replace_existing=True,
        )


def _run_top250():
    from app.services.crawler import crawl_top250
    from app.services.crawler import crawl_progress

    if crawl_progress["active"]:
        logger.warning("Crawl already running, skipping scheduled top250 crawl")
        return

    logger.info("Starting scheduled top250 crawl...")
    try:
        result = crawl_top250()
        logger.info(f"Top 250 crawl completed: {result}")
    except Exception as e:
        logger.error(f"Top 250 crawl failed: {e}")


def _run_user_scrape():
    from app.services.user_scraper import scrape_user_watched
    from app.services.crawler import crawl_progress
    from app.models.user import User

    if crawl_progress["active"]:
        logger.warning("Crawl already running, skipping scheduled user scrape")
        return

    db = SessionLocal()
    try:
        users = db.query(User).filter(
            User.is_active == True,
            User.douban_user_id.isnot(None),
        ).all()

        if not users:
            logger.warning("No users with douban configuration, skipping user scrape")
            return

        for user in users:
            logger.info(f"Starting scheduled user scrape for {user.username} ({user.douban_user_id})...")
            try:
                result = scrape_user_watched(user.douban_user_id, full=False, cookie=user.douban_cookie or "")
                logger.info(f"User scrape completed for {user.username}: {result}")
            except Exception as e:
                logger.error(f"User scrape failed for {user.username}: {e}")
    finally:
        db.close()


def _run_metadata():
    from app.services.metadata import run_backfill, meta_progress
    from app.services.crawler import crawl_progress

    if meta_progress["active"] or crawl_progress["active"]:
        logger.warning("Crawl/backfill already running, skipping metadata backfill")
        return

    logger.info("Starting scheduled metadata backfill...")
    try:
        result = run_backfill()
        logger.info(f"Metadata backfill completed: {result}")
    except Exception as e:
        logger.error(f"Metadata backfill failed: {e}")


def _run_imdb():
    from app.services.imdb_crawler import crawl_imdb_top250, get_imdb_progress
    from app.services.crawler import crawl_progress

    progress = get_imdb_progress()
    if progress["status"] == "running" or crawl_progress["active"]:
        logger.warning("Crawl already running, skipping scheduled IMDb crawl")
        return

    logger.info("Starting scheduled IMDb Top 250 crawl...")
    try:
        result = crawl_imdb_top250(SessionLocal)
        logger.info(f"IMDb crawl completed: {result}")
    except Exception as e:
        logger.error(f"IMDb crawl failed: {e}")


scheduler = CrawlScheduler()
