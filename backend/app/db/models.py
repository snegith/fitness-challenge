"""
SQLAlchemy ORM models — mirrors the finalized schema in SRS §7 exactly.

Tables:
    users
    activities
    leaderboard_snapshots
    leaderboard_entries

IMPORTANT — activity_date:
    activity_date is a plain TEXT column ('YYYY-MM-DD').
    It is ALWAYS written by the application layer (activity_service.py) by
    converting the server-generated UTC recorded_at into an IST calendar date
    using zoneinfo.ZoneInfo(settings.timezone).
    SQL timezone expressions or SQLite date() functions must NEVER be used to
    compute or derive activity_date (SRS §2.3, R12).

WAL mode:
    Not enabled — see database.py for the rationale.

All timestamp columns store UTC text in ISO 8601 format.
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    Real,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# TODO: implement User, Activity, LeaderboardSnapshot, LeaderboardEntry models
#       following the SRS §7 schema.  Indexes and CHECK constraints must match
#       the schema exactly, including:
#           idx_users_name_key          UNIQUE on users(name_key)
#           idx_daily_steps_unique      UNIQUE partial on activities(user_id, activity_date)
#                                       WHERE sport_type = 'daily_steps'
#           idx_snapshot_date           UNIQUE on leaderboard_snapshots(snapshot_date)
#           idx_entries_snapshot_user   UNIQUE on leaderboard_entries(snapshot_id, user_id)
