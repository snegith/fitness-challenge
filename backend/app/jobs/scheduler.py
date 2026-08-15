"""
APScheduler configuration — this module owns ALL scheduler concerns.

main.py's only interaction with this module is:
    from app.jobs.scheduler import start_scheduler
    start_scheduler(app)   ← called once in the FastAPI lifespan

This module is solely responsible for:
    - Creating the APScheduler instance.
    - Registering the daily snapshot job with a CronTrigger at 00:00 IST.
    - Computing target_date = (current IST date − 1 day) before passing to the
      snapshot service.
    - Starting and stopping the scheduler.

main.py has zero knowledge of job functions, timezones, or trigger types.
"""

import atexit
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI

from app.config import settings

logger = logging.getLogger(__name__)

_IST = ZoneInfo(settings.timezone)
_scheduler: BackgroundScheduler | None = None


def _run_daily_snapshot() -> None:
    """
    Job function invoked by APScheduler at 00:00 IST.

    Computes target_date = yesterday IST, opens a DB session, and calls
    generate_daily_snapshot().
    """
    from app.db.database import SessionLocal
    from app.services.snapshot_service import generate_daily_snapshot

    yesterday = datetime.now(tz=_IST).date() - timedelta(days=1)
    logger.info("Scheduler firing snapshot job for target_date=%s", yesterday)

    db = SessionLocal()
    try:
        generate_daily_snapshot(db, yesterday)
    except Exception:
        logger.exception("Snapshot job failed for target_date=%s", yesterday)
    finally:
        db.close()


def start_scheduler(app: FastAPI) -> None:
    """
    Start the APScheduler background scheduler and register the daily snapshot job.

    Called once from app.main lifespan.
    """
    global _scheduler

    _scheduler = BackgroundScheduler(timezone=_IST)
    _scheduler.add_job(
        _run_daily_snapshot,
        trigger=CronTrigger(hour=0, minute=0, timezone=_IST),
        id="daily_snapshot",
        replace_existing=True,
    )
    _scheduler.start()
    atexit.register(
        lambda: _scheduler.shutdown(wait=False)
        if _scheduler and _scheduler.running
        else None
    )
    logger.info("Scheduler started — daily snapshot job registered at 00:00 IST.")
