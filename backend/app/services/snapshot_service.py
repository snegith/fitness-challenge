"""
Snapshot service — daily leaderboard snapshot generation.

Public API:
    generate_daily_snapshot(db: Session, target_date: date) -> None

This function is the SINGLE implementation shared by both the APScheduler job
and the CLI trigger (SRS NFR-7, FR-16).  There is no separate "demo mode" path.

Snapshot semantics (SRS FR-12, §1.3, R13):
    target_date is the COMPLETED IST calendar day being summarised.
    Example: the job running at 00:00 IST on Aug 14 passes target_date = Aug 13.

Leaderboard scope for the snapshot (SRS §5 US-9):
    Only activities whose activity_date <= target_date are included.
    Activities from the day just starting (Aug 14+) must NOT be included.

Idempotency contract (approved scaffolding decision):
    1. Query leaderboard_snapshots WHERE snapshot_date = target_date.
       If a row already exists → log "snapshot already exists" and return.
    2. Aggregate leaderboard data limited to activity_date <= target_date.
    3. Assign ranks with the standard tie-break (SRS §9.2).
    4. BEGIN TRANSACTION
         INSERT leaderboard_snapshots(snapshot_date=target_date)
         INSERT leaderboard_entries (one per user)
       COMMIT
    5. On IntegrityError (UNIQUE violation from a concurrent race):
         log "concurrent snapshot detected, treating as no-op" and return.

The UNIQUE INDEX idx_snapshot_date on leaderboard_snapshots(snapshot_date) is the
final database-level guard and must not be removed (SRS US-9).
"""

import logging
from datetime import date

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# TODO: implement generate_daily_snapshot(db, target_date)
