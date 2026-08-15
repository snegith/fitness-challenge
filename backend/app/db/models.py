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
    Double,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ── Users ─────────────────────────────────────────────────────────────────────

class User(Base):
    """
    Registered participant.

    name_key is the normalised deduplication key:
        lower(trim(first_name)) + '|' + lower(trim(last_name))
    with internal whitespace collapsed.  Computed by the application layer
    (auth_service.py) before insert — never derived in SQL.

    UNIQUE INDEX idx_users_name_key enforces the case/whitespace-insensitive
    duplicate-user requirement at the database level (SRS FR-2, NFR-2).
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(Text, nullable=False)
    last_name = Column(Text, nullable=False)
    # Normalised key: lower+trim both names, collapse internal whitespace, join with '|'
    name_key = Column(Text, nullable=False)
    # Stored in UTC (ISO 8601).  SQLite default used for server-side generation.
    created_at = Column(
        Text,
        nullable=False,
        server_default=func.datetime("now"),
    )

    # Relationships
    activities = relationship("Activity", back_populates="user", lazy="select")
    leaderboard_entries = relationship(
        "LeaderboardEntry", back_populates="user", lazy="select"
    )

    __table_args__ = (
        Index("idx_users_name_key", "name_key", unique=True),
    )


# ── Activities ────────────────────────────────────────────────────────────────

class Activity(Base):
    """
    A single logged fitness activity.

    Structural validity (correct metric field populated for the sport type) is
    enforced at the database level via a CHECK constraint mirroring SRS §7.
    Business validity (e.g. distanceKm > 0) is enforced separately by the API
    layer (SRS R7 — intentional layering).

    recorded_at — UTC ISO 8601 string, always server-generated (SRS R11).
    activity_date — IST calendar date 'YYYY-MM-DD', written by application code
                    using zoneinfo; never computed by SQL (SRS §2.3, R12).

    Daily-steps uniqueness (SRS FR-10):
        idx_daily_steps_unique is a partial UNIQUE index on (user_id, activity_date)
        WHERE sport_type = 'daily_steps'.  This enforces exactly one daily-steps
        row per user per IST calendar day at the database level.
    """

    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sport_type = Column(
        Text,
        nullable=False,
        # Structural CHECK: only known sport types accepted
        # Business-level value validation is still done in the API layer.
    )
    metric_type = Column(Text, nullable=False)
    # Metric columns — exactly one must be non-NULL per row (enforced by CHECK below)
    distance_km = Column(Double, nullable=True)   # distance sports only
    duration_sec = Column(Integer, nullable=True)  # duration sports only
    step_count = Column(Integer, nullable=True)    # daily_steps only
    points = Column(Integer, nullable=False)
    # UTC ISO 8601 — server-generated only, never client-supplied (SRS R11)
    recorded_at = Column(Text, nullable=False)
    # IST calendar date 'YYYY-MM-DD' — written by application layer via zoneinfo
    # NEVER computed via SQL expressions (SRS §2.3, R12)
    activity_date = Column(Text, nullable=False)
    created_at = Column(
        Text,
        nullable=False,
        server_default=func.datetime("now"),
    )

    # Relationships
    user = relationship("User", back_populates="activities")

    __table_args__ = (
        # Structural validity: correct metric field populated for the sport type.
        # API layer enforces business validity (value > 0 etc.) separately.
        CheckConstraint(
            "(metric_type = 'distance' AND distance_km IS NOT NULL"
            "  AND duration_sec IS NULL AND step_count IS NULL)"
            " OR (metric_type = 'duration' AND duration_sec IS NOT NULL"
            "  AND distance_km IS NULL AND step_count IS NULL)"
            " OR (metric_type = 'count' AND step_count IS NOT NULL"
            "  AND distance_km IS NULL AND duration_sec IS NULL)",
            name="ck_activities_metric_fields",
        ),
        # sport_type domain constraint
        CheckConstraint(
            "sport_type IN ('running','walking','cycling','swimming','gym','daily_steps')",
            name="ck_activities_sport_type",
        ),
        # metric_type domain constraint
        CheckConstraint(
            "metric_type IN ('distance','duration','count')",
            name="ck_activities_metric_type",
        ),
        # Performance indexes
        Index("idx_activities_user_recorded", "user_id", "recorded_at"),
        Index("idx_activities_user_date", "user_id", "activity_date"),
        # Daily-steps uniqueness: one row per user per IST calendar day (SRS FR-10)
        # This is a partial index — only rows where sport_type = 'daily_steps'.
        Index(
            "idx_daily_steps_unique",
            "user_id",
            "activity_date",
            unique=True,
            sqlite_where=Column("sport_type") == "daily_steps",
        ),
    )


# ── Leaderboard Snapshots ─────────────────────────────────────────────────────

class LeaderboardSnapshot(Base):
    """
    Header row for a daily leaderboard snapshot.

    snapshot_date is the COMPLETED IST calendar day this snapshot represents
    (SRS FR-12, R13):
        - The job running at 00:00 IST on Aug 14 stores snapshot_date = 'Aug 13'.
        - This is enforced by generate_daily_snapshot() in snapshot_service.py,
          not here.

    UNIQUE INDEX idx_snapshot_date prevents duplicate snapshots for the same date
    (SRS US-9).  This constraint is the final database-level guard for idempotency.
    """

    __tablename__ = "leaderboard_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # IST calendar date 'YYYY-MM-DD' — the COMPLETED day this snapshot covers
    snapshot_date = Column(Text, nullable=False)
    created_at = Column(
        Text,
        nullable=False,
        server_default=func.datetime("now"),
    )

    # Relationships
    entries = relationship(
        "LeaderboardEntry", back_populates="snapshot", lazy="select"
    )

    __table_args__ = (
        Index("idx_snapshot_date", "snapshot_date", unique=True),
    )


# ── Leaderboard Entries ───────────────────────────────────────────────────────

class LeaderboardEntry(Base):
    """
    One user's rank and point total within a specific daily snapshot.

    UNIQUE INDEX idx_entries_snapshot_user prevents a user appearing more than
    once in the same snapshot.
    """

    __tablename__ = "leaderboard_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(
        Integer, ForeignKey("leaderboard_snapshots.id"), nullable=False
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rank = Column(Integer, nullable=False)
    total_points = Column(Integer, nullable=False)

    # Relationships
    snapshot = relationship("LeaderboardSnapshot", back_populates="entries")
    user = relationship("User", back_populates="leaderboard_entries")

    __table_args__ = (
        Index("idx_entries_snapshot_user", "snapshot_id", "user_id", unique=True),
        Index("idx_entries_user", "user_id"),
    )
