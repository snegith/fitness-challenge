"""
Snapshot service — daily leaderboard snapshot generation.

Public API:
    generate_daily_snapshot(db: Session, target_date: date) -> None

This function is the SINGLE implementation shared by both the APScheduler job
and the CLI trigger (SRS NFR-7, FR-16).  There is no separate "demo mode" path.

Snapshot semantics (SRS FR-12, §1.3, R13):
    target_date is the COMPLETED IST calendar day being summarised.
    Example: the job running at 00:00 IST on Aug 14 passes target_date = Aug 13.

    target_date must be < today's IST date.  Generating a snapshot for the
    still-in-progress current day is rejected.

Leaderboard scope for the snapshot (SRS §5 US-9):
    Only activities whose activity_date <= target_date are included.
    Activities from the day just starting (Aug 14+) must NOT be included.
    Users registered on or before target_date with zero qualifying activities
    still receive an entry at totalPoints=0.

Idempotency contract:
    1. Query leaderboard_snapshots WHERE snapshot_date = target_date.
       If a row already exists → log "snapshot already exists" and return.
    2. Aggregate leaderboard data limited to activity_date <= target_date.
    3. Assign ranks with the standard tie-break (SRS §9.2).
    4. BEGIN TRANSACTION
         INSERT leaderboard_snapshots(snapshot_date=target_date)
         INSERT leaderboard_entries (one per user registered on or before target_date)
       COMMIT
    5. On IntegrityError (UNIQUE violation from a concurrent race):
         log "concurrent snapshot detected, treating as no-op" and return.

The UNIQUE INDEX idx_snapshot_date on leaderboard_snapshots(snapshot_date) is the
final database-level guard and must not be removed (SRS US-9).
"""

import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Activity, LeaderboardEntry, LeaderboardSnapshot, User

logger = logging.getLogger(__name__)

_IST = ZoneInfo(settings.timezone)


class SnapshotDateError(Exception):
    """Raised when target_date is not a valid completed IST calendar day."""


def generate_daily_snapshot(db: Session, target_date: date) -> None:
    """
    Generate and persist the leaderboard snapshot for a completed IST calendar day.

    Args:
        db: SQLAlchemy session.
        target_date: The COMPLETED IST calendar day to snapshot (must be < today IST).

    Raises:
        SnapshotDateError: if target_date >= today's IST date.
    """
    # ── Guard: target_date must be a completed day (strictly before today IST)
    today_ist = datetime.now(tz=_IST).date()
    if target_date >= today_ist:
        raise SnapshotDateError(
            f"target_date {target_date} is not a completed IST day "
            f"(today IST is {today_ist}). Only past days may be snapshotted."
        )

    target_date_str = target_date.isoformat()  # 'YYYY-MM-DD'

    # ── 1. Idempotency check — does a snapshot already exist for this date?
    existing = (
        db.query(LeaderboardSnapshot)
        .filter(LeaderboardSnapshot.snapshot_date == target_date_str)
        .first()
    )
    if existing is not None:
        logger.info(
            "Snapshot for %s already exists (id=%d), skipping.",
            target_date_str,
            existing.id,
        )
        return

    # ── 2. Aggregate leaderboard for activities with activity_date <= target_date
    #        Include ALL users registered on or before target_date via LEFT JOIN.
    point_subq = (
        db.query(
            Activity.user_id,
            func.coalesce(func.sum(Activity.points), 0).label("total_points"),
        )
        .filter(Activity.activity_date <= target_date_str)
        .group_by(Activity.user_id)
        .subquery()
    )

    # Only include users whose created_at <= end of target_date
    # created_at is stored as UTC text; target_date end in UTC = target_date 18:30 UTC
    # (since IST = UTC+5:30, end of IST day N = N+1 00:00 IST = N 18:30 UTC)
    # But since created_at includes a time component and we want users registered
    # on or before the target_date in IST terms, we compare created_at against
    # the start of the next IST day expressed in UTC.
    # Next IST day start in UTC: target_date+1 at 00:00 IST = target_date at 18:30 UTC
    # So: created_at < 'target_date+1 day' at 00:00 IST in UTC
    # Simpler: since created_at is UTC and IST = UTC+5:30, a user created at
    # UTC time T is in IST day = date(T + 5:30). We want IST day <= target_date.
    # This means T + 5:30 is still on target_date or earlier, i.e.
    # T < target_date+1 00:00 IST = target_date 18:30 UTC.
    from datetime import timedelta, timezone

    next_day_ist_midnight = (
        datetime(target_date.year, target_date.month, target_date.day, tzinfo=_IST)
        + timedelta(days=1)
    )
    cutoff_utc_str = next_day_ist_midnight.astimezone(timezone.utc).strftime(  # noqa: UP017
        "%Y-%m-%dT%H:%M:%SZ"
    )

    rows = (
        db.query(
            User.id,
            func.coalesce(point_subq.c.total_points, 0).label("total_points"),
            User.created_at,
        )
        .filter(User.created_at < cutoff_utc_str)
        .outerjoin(point_subq, User.id == point_subq.c.user_id)
        .order_by(
            func.coalesce(point_subq.c.total_points, 0).desc(),
            User.created_at.asc(),
            User.id.asc(),
        )
        .all()
    )

    # ── 3. Persist snapshot + entries atomically
    snapshot = LeaderboardSnapshot(snapshot_date=target_date_str)
    db.add(snapshot)

    try:
        db.flush()  # get snapshot.id
    except IntegrityError:
        # Concurrent race: another process inserted the snapshot between our
        # check and our insert.
        db.rollback()
        logger.info(
            "Concurrent snapshot detected for %s, treating as no-op.",
            target_date_str,
        )
        return

    snapshot_id = snapshot.id

    for idx, row in enumerate(rows, start=1):
        entry = LeaderboardEntry(
            snapshot_id=snapshot_id,
            user_id=row.id,
            rank=idx,
            total_points=row.total_points,
        )
        db.add(entry)

    db.commit()
    logger.info(
        "Snapshot for %s created (id=%d, %d entries).",
        target_date_str,
        snapshot_id,
        len(rows),
    )
