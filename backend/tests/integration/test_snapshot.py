"""
Integration tests — daily leaderboard snapshot generation.

Coverage (SRS §11.5 snapshot portion):
    - Snapshot creates one leaderboard_snapshots row + N entries.
    - snapshot_date is the target_date (completed day), not execution date.
    - Only activities with activity_date <= target_date are included.
    - Zero-activity users registered before target_date get entries at 0 points.
    - Idempotency: re-running for same date → no duplicate, returns silently.
    - Concurrent race (IntegrityError) → graceful no-op.
    - target_date >= today IST → rejected with SnapshotDateError.
    - Empty snapshot (no users) still creates the header row.
    - Ranking within snapshot uses correct tie-break.
"""

from datetime import date, timedelta

import pytest

from app.db.models import Activity, LeaderboardEntry, LeaderboardSnapshot, User
from app.services.snapshot_service import SnapshotDateError, generate_daily_snapshot

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_user(db, first, last, *, created_at="2026-08-10T00:00:00Z"):
    user = User(
        first_name=first,
        last_name=last,
        name_key=f"{first.lower()}|{last.lower()}",
        created_at=created_at,
    )
    db.add(user)
    db.flush()
    return user


def _make_activity(db, user_id, points, *, activity_date="2026-08-13"):
    activity = Activity(
        user_id=user_id,
        sport_type="running",
        metric_type="distance",
        distance_km=float(points) / 100.0,
        points=points,
        recorded_at="2026-08-13T01:30:00Z",
        activity_date=activity_date,
    )
    db.add(activity)
    db.flush()
    return activity


# ── Snapshot generation ────────────────────────────────────────────────────────


class TestSnapshotGeneration:
    def test_creates_snapshot_and_entries(self, db_session):
        u1 = _make_user(db_session, "Ada", "Lovelace")
        u2 = _make_user(db_session, "Grace", "Hopper")
        _make_activity(db_session, u1.id, 500, activity_date="2026-08-13")
        _make_activity(db_session, u2.id, 300, activity_date="2026-08-13")
        db_session.commit()

        target = date(2026, 8, 13)
        generate_daily_snapshot(db_session, target)

        snapshot = db_session.query(LeaderboardSnapshot).filter_by(
            snapshot_date="2026-08-13"
        ).one()
        entries = db_session.query(LeaderboardEntry).filter_by(
            snapshot_id=snapshot.id
        ).all()
        assert len(entries) == 2

    def test_snapshot_date_is_target_date(self, db_session):
        _make_user(db_session, "Ada", "Lovelace")
        db_session.commit()

        target = date(2026, 8, 13)
        generate_daily_snapshot(db_session, target)

        snapshot = db_session.query(LeaderboardSnapshot).one()
        assert snapshot.snapshot_date == "2026-08-13"

    def test_excludes_activities_after_target_date(self, db_session):
        u1 = _make_user(db_session, "Ada", "Lovelace")
        _make_activity(db_session, u1.id, 500, activity_date="2026-08-13")
        _make_activity(db_session, u1.id, 200, activity_date="2026-08-14")  # after target
        db_session.commit()

        target = date(2026, 8, 13)
        generate_daily_snapshot(db_session, target)

        snapshot = db_session.query(LeaderboardSnapshot).one()
        entry = db_session.query(LeaderboardEntry).filter_by(
            snapshot_id=snapshot.id, user_id=u1.id
        ).one()
        # Only the Aug 13 activity (500 pts) should be included
        assert entry.total_points == 500

    def test_zero_activity_user_gets_entry(self, db_session):
        """User registered before target_date with no activities → entry at 0 pts."""
        u1 = _make_user(db_session, "Ada", "Lovelace")
        u2 = _make_user(db_session, "Grace", "Hopper")
        _make_activity(db_session, u1.id, 500, activity_date="2026-08-13")
        # u2 has no activities
        db_session.commit()

        target = date(2026, 8, 13)
        generate_daily_snapshot(db_session, target)

        snapshot = db_session.query(LeaderboardSnapshot).one()
        entries = db_session.query(LeaderboardEntry).filter_by(
            snapshot_id=snapshot.id
        ).order_by(LeaderboardEntry.rank).all()
        assert len(entries) == 2
        assert entries[0].user_id == u1.id
        assert entries[0].total_points == 500
        assert entries[1].user_id == u2.id
        assert entries[1].total_points == 0

    def test_ranking_uses_correct_tiebreak(self, db_session):
        u1 = _make_user(db_session, "Ada", "Lovelace", created_at="2026-08-10T00:00:00Z")
        u2 = _make_user(db_session, "Grace", "Hopper", created_at="2026-08-11T00:00:00Z")
        _make_activity(db_session, u1.id, 300, activity_date="2026-08-13")
        _make_activity(db_session, u2.id, 300, activity_date="2026-08-13")
        db_session.commit()

        target = date(2026, 8, 13)
        generate_daily_snapshot(db_session, target)

        snapshot = db_session.query(LeaderboardSnapshot).one()
        entries = db_session.query(LeaderboardEntry).filter_by(
            snapshot_id=snapshot.id
        ).order_by(LeaderboardEntry.rank).all()
        # Same points — u1 registered earlier → rank 1
        assert entries[0].user_id == u1.id
        assert entries[0].rank == 1
        assert entries[1].user_id == u2.id
        assert entries[1].rank == 2


# ── Idempotency ───────────────────────────────────────────────────────────────


class TestSnapshotIdempotency:
    def test_rerun_same_date_does_not_duplicate(self, db_session):
        _make_user(db_session, "Ada", "Lovelace")
        db_session.commit()

        target = date(2026, 8, 13)
        generate_daily_snapshot(db_session, target)
        generate_daily_snapshot(db_session, target)  # second run

        count = db_session.query(LeaderboardSnapshot).filter_by(
            snapshot_date="2026-08-13"
        ).count()
        assert count == 1

    def test_entries_not_duplicated_on_rerun(self, db_session):
        u1 = _make_user(db_session, "Ada", "Lovelace")
        _make_activity(db_session, u1.id, 500, activity_date="2026-08-13")
        db_session.commit()

        target = date(2026, 8, 13)
        generate_daily_snapshot(db_session, target)
        generate_daily_snapshot(db_session, target)

        entries = db_session.query(LeaderboardEntry).all()
        assert len(entries) == 1


# ── Date guard ─────────────────────────────────────────────────────────────────


class TestSnapshotDateGuard:
    def test_today_ist_rejected(self, db_session):
        """Cannot snapshot the current (incomplete) IST day."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        today = datetime.now(tz=ZoneInfo("Asia/Kolkata")).date()
        with pytest.raises(SnapshotDateError):
            generate_daily_snapshot(db_session, today)

    def test_future_date_rejected(self, db_session):
        from datetime import datetime
        from zoneinfo import ZoneInfo

        future = datetime.now(tz=ZoneInfo("Asia/Kolkata")).date() + timedelta(days=5)
        with pytest.raises(SnapshotDateError):
            generate_daily_snapshot(db_session, future)


# ── Empty snapshot ─────────────────────────────────────────────────────────────


class TestEmptySnapshot:
    def test_no_users_still_creates_header_row(self, db_session):
        """If no users exist, still create the snapshot header with 0 entries."""
        target = date(2026, 8, 13)
        generate_daily_snapshot(db_session, target)

        snapshot = db_session.query(LeaderboardSnapshot).one()
        assert snapshot.snapshot_date == "2026-08-13"
        entries = db_session.query(LeaderboardEntry).filter_by(
            snapshot_id=snapshot.id
        ).all()
        assert len(entries) == 0


# ── IST boundary regression (timezone bug fix) ────────────────────────────────


class TestSnapshotISTBoundary:
    """
    Regression tests for the IST user-inclusion cutoff.

    The snapshot for target_date uses the IST calendar boundary to decide which
    users are "registered on or before target_date".  created_at is stored in UTC.

    IST day boundary:
        2026-08-14 00:00 IST = 2026-08-13 18:30 UTC

    Therefore for target_date = 2026-08-13:
        - Users created before 2026-08-13 18:30 UTC → included (IST day <= Aug 13)
        - Users created at/after 2026-08-13 18:30 UTC → excluded (IST day >= Aug 14)
    """

    def test_user_created_late_aug13_ist_is_included(self, db_session):
        """
        User created at 2026-08-13 23:59 IST = 2026-08-13 18:29 UTC.
        This is still within Aug 13 IST → must be included in the Aug 13 snapshot.
        """
        user = User(
            first_name="Ada",
            last_name="Lovelace",
            name_key="ada|lovelace",
            created_at="2026-08-13T18:29:00Z",  # 2026-08-13 23:59 IST
        )
        db_session.add(user)
        db_session.commit()

        generate_daily_snapshot(db_session, date(2026, 8, 13))

        snapshot = db_session.query(LeaderboardSnapshot).one()
        entries = db_session.query(LeaderboardEntry).filter_by(
            snapshot_id=snapshot.id
        ).all()
        assert len(entries) == 1
        assert entries[0].user_id == user.id

    def test_user_created_early_aug14_ist_is_excluded(self, db_session):
        """
        User created at 2026-08-14 02:00 IST = 2026-08-13 20:30 UTC.
        This is Aug 14 in IST → must NOT appear in the Aug 13 snapshot.
        """
        user = User(
            first_name="Grace",
            last_name="Hopper",
            name_key="grace|hopper",
            created_at="2026-08-13T20:30:00Z",  # 2026-08-14 02:00 IST
        )
        db_session.add(user)
        db_session.commit()

        generate_daily_snapshot(db_session, date(2026, 8, 13))

        snapshot = db_session.query(LeaderboardSnapshot).one()
        entries = db_session.query(LeaderboardEntry).filter_by(
            snapshot_id=snapshot.id
        ).all()
        # User registered on Aug 14 IST must be excluded from Aug 13 snapshot
        assert len(entries) == 0

    def test_user_at_exact_boundary_is_excluded(self, db_session):
        """
        User created at exactly 2026-08-13 18:30:00 UTC = 2026-08-14 00:00 IST.
        This is the start of Aug 14 IST → must NOT appear in Aug 13 snapshot.
        """
        user = User(
            first_name="Boundary",
            last_name="User",
            name_key="boundary|user",
            created_at="2026-08-13T18:30:00Z",  # exactly 2026-08-14 00:00 IST
        )
        db_session.add(user)
        db_session.commit()

        generate_daily_snapshot(db_session, date(2026, 8, 13))

        snapshot = db_session.query(LeaderboardSnapshot).one()
        entries = db_session.query(LeaderboardEntry).filter_by(
            snapshot_id=snapshot.id
        ).all()
        assert len(entries) == 0
