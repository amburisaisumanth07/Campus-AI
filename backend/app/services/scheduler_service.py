"""
Background Scheduler Service for Periodic Website Synchronization.
Uses APScheduler (with graceful fallback if not installed) to periodically trigger crawler jobs.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from sqlalchemy.orm import Session

from backend.app.core.logging import logger
from backend.app.db.models import WebsiteSource, WebsiteSourceStatus
from backend.app.db.session import SessionLocal

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
    APSCHEDULER_AVAILABLE = True
except ImportError:
    BackgroundScheduler = Any  # type: ignore
    IntervalTrigger = Any  # type: ignore
    EVENT_JOB_EXECUTED = 0  # type: ignore
    EVENT_JOB_ERROR = 0  # type: ignore
    APSCHEDULER_AVAILABLE = False

_scheduler: Optional[Any] = None


class DummyScheduler:
    """Fallback scheduler when APScheduler is not installed."""
    def start(self):
        logger.info("[SCHEDULER] Dummy scheduler started (APScheduler not installed).")

    def shutdown(self, wait=True):
        pass

    def add_job(self, *args, **kwargs):
        pass

    def remove_job(self, *args, **kwargs):
        pass

    def get_job(self, *args, **kwargs):
        return None

    def add_listener(self, *args, **kwargs):
        pass


def _on_job_event(event: Any) -> None:
    """Listener called when a scheduler job finishes execution."""
    if not event or not getattr(event, "job_id", None):
        return
    job_id = str(event.job_id)
    if job_id.startswith("website_sync_"):
        try:
            source_id = int(job_id.replace("website_sync_", ""))
            scheduler = get_scheduler()
            job = scheduler.get_job(job_id)
            if SessionLocal and job and getattr(job, "next_run_time", None):
                db: Session = SessionLocal()
                try:
                    src = db.query(WebsiteSource).filter(WebsiteSource.id == source_id).first()
                    if src:
                        src.next_scheduled_sync_at = job.next_run_time
                        db.commit()
                        logger.info(f"[SCHEDULER] Updated next_scheduled_sync_at for source {source_id}: {job.next_run_time}")
                finally:
                    db.close()
        except Exception as exc:
            logger.warning(f"[SCHEDULER] Error in job event listener for {job_id}: {exc}")


def get_scheduler() -> Any:
    global _scheduler
    if _scheduler is None:
        if APSCHEDULER_AVAILABLE:
            _scheduler = BackgroundScheduler(daemon=True)
            _scheduler.add_listener(_on_job_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        else:
            _scheduler = DummyScheduler()
    return _scheduler


def _parse_interval_hours(interval_str: str) -> int:
    """Parse '1h', '6h', '12h', '24h' into integer hours."""
    val = interval_str.lower().strip()
    if val == "1h":
        return 1
    elif val == "6h":
        return 6
    elif val == "12h":
        return 12
    elif val == "24h":
        return 24
    return 6


def run_scheduled_sync(source_id: int) -> None:
    """Job callback triggered periodically by scheduler."""
    logger.info(f"[SCHEDULER] Triggering scheduled sync for source {source_id}...")
    if SessionLocal is None:
        logger.error("[SCHEDULER] SessionLocal is not initialized.")
        return

    db: Session = SessionLocal()
    try:
        source = db.query(WebsiteSource).filter(WebsiteSource.id == source_id).first()
        if not source or not source.active or not getattr(source, "auto_sync_enabled", True):
            logger.info(f"[SCHEDULER] Source {source_id} is inactive or auto-sync disabled. Skipping.")
            return

        # Recover stale crawling status if last checked > 15 mins ago
        now = datetime.now(timezone.utc)
        if source.status in [WebsiteSourceStatus.CRAWLING.value, WebsiteSourceStatus.QUEUED.value, WebsiteSourceStatus.SYNCING.value]:
            if source.last_checked_at and (now - source.last_checked_at) > timedelta(minutes=15):
                logger.warning(f"[SCHEDULER] Source {source_id} was stuck in {source.status}. Resetting to IDLE.")
                source.status = WebsiteSourceStatus.IDLE.value
                db.commit()

        from backend.app.services.crawler_service import synchronize_website_source
        synchronize_website_source(db, source_id)

        # Update next_scheduled_sync_at after execution
        scheduler = get_scheduler()
        job = scheduler.get_job(f"website_sync_{source_id}")
        if job and getattr(job, "next_run_time", None):
            source.next_scheduled_sync_at = job.next_run_time
            db.commit()

    except Exception as exc:
        logger.error(f"[SCHEDULER] Scheduled sync failed for source {source_id}: {exc}")
    finally:
        db.close()


def schedule_source_sync(source_or_id: Any, interval_str: Optional[str] = None) -> None:
    """Register or update a recurring sync job for a specific WebsiteSource."""
    if hasattr(source_or_id, "id"):
        source_id = source_or_id.id
        interval_str = getattr(source_or_id, "sync_interval", "6h") or "6h"
    else:
        source_id = int(source_or_id)
        if interval_str is None:
            interval_str = "6h"

    if not APSCHEDULER_AVAILABLE:
        logger.info(f"[SCHEDULER] APScheduler unavailable; skipping recurring schedule for source {source_id}.")
        return

    scheduler = get_scheduler()
    job_id = f"website_sync_{source_id}"
    hours = _parse_interval_hours(interval_str)

    try:
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
            logger.info(f"[SCHEDULER] Removed previous job {job_id}.")

        job = scheduler.add_job(
            run_scheduled_sync,
            trigger=IntervalTrigger(hours=hours),
            id=job_id,
            name=f"Periodic Sync for WebsiteSource {source_id}",
            args=[source_id],
            replace_existing=True,
        )
        logger.info(f"[SCHEDULER] Registered job {job_id} to run every {hours} hour(s). Next run: {job.next_run_time}")
        
        # Update next_scheduled_sync_at in DB if available
        if SessionLocal:
            db_s = SessionLocal()
            try:
                src_db = db_s.query(WebsiteSource).filter(WebsiteSource.id == source_id).first()
                if src_db:
                    src_db.next_scheduled_sync_at = job.next_run_time
                    src_db.auto_sync_enabled = True
                    db_s.commit()
            except Exception:
                pass
            finally:
                db_s.close()
    except Exception as exc:
        logger.error(f"[SCHEDULER] Failed to register job {job_id}: {exc}")


def unschedule_source_sync(source_id: int) -> None:
    """Remove a recurring sync job."""
    if not APSCHEDULER_AVAILABLE:
        return
    scheduler = get_scheduler()
    job_id = f"website_sync_{source_id}"
    try:
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
            logger.info(f"[SCHEDULER] Unscheduled job {job_id}.")
    except Exception as exc:
        logger.warning(f"[SCHEDULER] Could not remove job {job_id}: {exc}")


remove_source_sync = unschedule_source_sync


def pause_source_sync(source_id: int, db: Optional[Session] = None) -> None:
    """Pause automatic synchronization for a source."""
    unschedule_source_sync(source_id)
    close_db = False
    if db is None and SessionLocal:
        db = SessionLocal()
        close_db = True
    if db:
        try:
            source = db.query(WebsiteSource).filter(WebsiteSource.id == source_id).first()
            if source:
                source.auto_sync_enabled = False
                source.next_scheduled_sync_at = None
                db.commit()
                logger.info(f"[SCHEDULER] Paused auto-sync for source {source_id}.")
        finally:
            if close_db:
                db.close()


def resume_source_sync(source_id: int, db: Optional[Session] = None) -> None:
    """Resume automatic synchronization for a source."""
    close_db = False
    if db is None and SessionLocal:
        db = SessionLocal()
        close_db = True
    if db:
        try:
            source = db.query(WebsiteSource).filter(WebsiteSource.id == source_id).first()
            if source:
                source.auto_sync_enabled = True
                db.commit()
                schedule_source_sync(source)
                logger.info(f"[SCHEDULER] Resumed auto-sync for source {source_id}.")
        finally:
            if close_db:
                db.close()


def init_active_source_schedules(db: Session) -> None:
    """Load all active sources from DB, recover any stale statuses, and schedule them."""
    try:
        # Recover any stuck crawling sources on startup
        stuck_sources = db.query(WebsiteSource).filter(
            WebsiteSource.status.in_([WebsiteSourceStatus.CRAWLING.value, WebsiteSourceStatus.QUEUED.value, WebsiteSourceStatus.SYNCING.value])
        ).all()
        for s in stuck_sources:
            s.status = WebsiteSourceStatus.IDLE.value
        if stuck_sources:
            db.commit()
            logger.info(f"[SCHEDULER] Recovered {len(stuck_sources)} stuck sources to IDLE.")

        active_sources = db.query(WebsiteSource).filter(
            WebsiteSource.active == True,
            WebsiteSource.auto_sync_enabled == True
        ).all()
        logger.info(f"[SCHEDULER] Found {len(active_sources)} active auto-sync sources to schedule.")
        for source in active_sources:
            schedule_source_sync(source)
    except Exception as exc:
        logger.error(f"[SCHEDULER] Failed to init active schedules: {exc}")


def start_scheduler() -> None:
    """Initialize and start the background scheduler."""
    scheduler = get_scheduler()
    try:
        scheduler.start()
        logger.info("[SCHEDULER] Background scheduler started successfully.")
    except Exception as exc:
        logger.error(f"[SCHEDULER] Could not start scheduler: {exc}")


def stop_scheduler() -> None:
    """Shutdown background scheduler gracefully."""
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
            logger.info("[SCHEDULER] Background scheduler stopped.")
        except Exception as exc:
            logger.warning(f"[SCHEDULER] Error during shutdown: {exc}")
        _scheduler = None


shutdown_scheduler = stop_scheduler
