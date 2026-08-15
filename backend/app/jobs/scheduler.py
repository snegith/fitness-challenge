"""
APScheduler configuration — this module owns ALL scheduler concerns.

main.py's only interaction with this module is:
    from app.jobs.scheduler import start_scheduler
    start_scheduler(app)   ← called once in the FastAPI lifespan

This module is solely responsible for:
    - Creating the APScheduler instance.
    - Registering the daily snapshot job with a CronTrigger at 00:00 IST.
    - Binding the trigger to snapshot_service.generate_daily_snapshot.
    - Computing target_date = (current IST date − 1 day) before passing to the
      service, so the snapshot represents the completed previous day (SRS FR-12,
      R13).
    - Starting and stopping the scheduler.

main.py must NOT contain any of the above — it only calls start_scheduler(app).

Scheduler configuration:
    Trigger : CronTrigger(hour=0, minute=0, timezone="Asia/Kolkata")
    Job     : generate_daily_snapshot(db, target_date=yesterday_ist)
    In-process: APScheduler runs inside the FastAPI process (single-server scope).

Known trade-off (concern C2):
    If the server restarts at exactly 00:00 IST, the scheduled job could be missed.
    Acceptable at assignment scale; the CLI trigger covers manual recovery.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

logger = logging.getLogger(__name__)

# TODO: implement start_scheduler(app: FastAPI) -> None
#       - create BackgroundScheduler with Asia/Kolkata timezone
#       - register snapshot job with CronTrigger(hour=0, minute=0)
#       - job wrapper: open a DB session, compute target_date = yesterday IST,
#         call snapshot_service.generate_daily_snapshot(db, target_date)
#       - scheduler.start()
#       - register shutdown on FastAPI shutdown event or atexit
