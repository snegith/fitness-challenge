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
from datetime import date

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """Parse arguments and invoke generate_daily_snapshot()."""
    parser = argparse.ArgumentParser(
        description="Manually trigger daily leaderboard snapshot generation."
    )
    parser.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        help="Target date to snapshot (default: yesterday IST)",
        default=None,
    )
    args = parser.parse_args()

    # TODO: resolve target_date (parse args.date or compute yesterday IST via zoneinfo)
    # TODO: open a DB session
    # TODO: call snapshot_service.generate_daily_snapshot(db, target_date)
    # TODO: log result and close session
    logger.info("CLI snapshot trigger — not yet implemented")
    sys.exit(0)


if __name__ == "__main__":
    main()
