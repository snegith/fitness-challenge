"""
CLI entry point for manual snapshot generation.

Usage:
    python -m app.jobs
    python -m app.jobs --date 2026-08-13   (optional: override target_date for testing)

Calls generate_daily_snapshot() with the same logic as the scheduled job —
no divergent demo-mode path (SRS NFR-7, FR-16).

Default target_date (when --date is not supplied):
    The most recently completed IST calendar day (i.e. yesterday IST at the
    moment the command is run) — identical to what the scheduler would use.

The CLI is the approved path for manual/test execution.
No HTTP endpoint exists for snapshot generation (SRS §6, R9).
"""

import argparse
import logging
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """Parse arguments and invoke generate_daily_snapshot()."""
    from app.config import settings
    from app.db.database import SessionLocal
    from app.db.init_db import init_db
    from app.services.snapshot_service import SnapshotDateError, generate_daily_snapshot

    parser = argparse.ArgumentParser(
        description="Manually trigger daily leaderboard snapshot generation."
    )
    parser.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        help="Target date to snapshot (default: yesterday IST). Must be a past completed day.",
        default=None,
    )
    args = parser.parse_args()

    ist = ZoneInfo(settings.timezone)

    if args.date is not None:
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError:
            logger.error("Invalid date format: %s (expected YYYY-MM-DD)", args.date)
            sys.exit(1)
    else:
        target_date = datetime.now(tz=ist).date() - timedelta(days=1)

    logger.info("Generating snapshot for target_date=%s", target_date)

    init_db()
    db = SessionLocal()
    try:
        generate_daily_snapshot(db, target_date)
        logger.info("Done.")
    except SnapshotDateError as exc:
        logger.error("Rejected: %s", exc)
        sys.exit(1)
    except Exception:
        logger.exception("Snapshot generation failed.")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
