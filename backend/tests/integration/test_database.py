"""
Database-layer tests — verifies actual schema behaviour.

Tests actual SQLAlchemy/SQLite behaviour: inserts, constraints, relationships,
and indexes.  No HTTP client, no service logic.

Coverage:
    1.  User persistence (insert and read back all fields).
    2.  name_key uniqueness (duplicate name_key raises IntegrityError).
    3.  Foreign-key enforcement (activity with non-existent user_id is rejected).
    4.  Daily Steps uniqueness per (user_id, activity_date) — second insert raises
        IntegrityError; other sport types on the same date are not affected.
    5.  Snapshot date uniqueness (duplicate snapshot_date raises IntegrityError).
    6.  Snapshot → entry relationship (entries are accessible via snapshot.entries).
    7.  Activity → user relationship (activity.user resolves to the correct User).
    8.  Required NOT NULL constraints (missing nullable=False fields raise errors).
    9.  Activity CHECK constraint rejects a structurally invalid metric combination
        (e.g. distance_km set on a duration-type row).
    10. Duplicate leaderboard_entries for the same (snapshot_id, user_id) is rejected.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.models import Activity, LeaderboardEntry, LeaderboardSnapshot, User

# ── helpers ───────────────────────────────────────────────────────────────────

def _make_user(db, *, first="Ada", last="Lovelace", name_key=None):
    """Insert and return a User row."""
    user = User(
        first_name=first,
        last_name=last,
        name_key=name_key or f"{first.lower()}|{last.lower()}",
        created_at="2026-08-13T00:00:00Z",
    )
    db.add(user)
    db.flush()
    return user


def _make_running_activity(db, user_id, *, activity_date="2026-08-13"):
    """Insert and return a valid running (distance) activity."""
    activity = Activity(
        user_id=user_id,
        sport_type="running",
        metric_type="distance",
        distance_km=5.0,
        duration_sec=None,
        step_count=None,
        points=500,
        recorded_at="2026-08-12T18:30:00Z",
        activity_date=activity_date,
        created_at="2026-08-12T18:30:00Z",
    )
    db.add(activity)
    db.flush()
    return activity


def _make_steps_activity(db, user_id, *, activity_date="2026-08-13", step_count=8000):
    """Insert and return a valid daily_steps activity."""
    activity = Activity(
        user_id=user_id,
        sport_type="daily_steps",
        metric_type="count",
        distance_km=None,
        duration_sec=None,
        step_count=step_count,
        points=step_count // 100,
        recorded_at="2026-08-12T18:30:00Z",
        activity_date=activity_date,
        created_at="2026-08-12T18:30:00Z",
    )
    db.add(activity)
    db.flush()
    return activity


def _make_snapshot(db, *, snapshot_date="2026-08-12"):
    snapshot = LeaderboardSnapshot(
        snapshot_date=snapshot_date,
        created_at="2026-08-13T00:00:00Z",
    )
    db.add(snapshot)
    db.flush()
    return snapshot


# ── 1. User persistence ───────────────────────────────────────────────────────

class TestUserPersistence:
    def test_insert_and_read_back(self, db_session):
        user = _make_user(db_session, first="Ada", last="Lovelace")
        db_session.commit()

        fetched = db_session.query(User).filter_by(id=user.id).one()
        assert fetched.first_name == "Ada"
        assert fetched.last_name == "Lovelace"
        assert fetched.name_key == "ada|lovelace"
        assert fetched.created_at is not None

    def test_id_is_autoincremented(self, db_session):
        u1 = _make_user(db_session, first="Ada", last="Lovelace", name_key="ada|lovelace")
        u2 = _make_user(db_session, first="Grace", last="Hopper", name_key="grace|hopper")
        db_session.commit()
        assert u1.id != u2.id
        assert u2.id > u1.id


# ── 2. name_key uniqueness ────────────────────────────────────────────────────

class TestNameKeyUniqueness:
    def test_duplicate_name_key_raises_integrity_error(self, db_session):
        _make_user(db_session, name_key="ada|lovelace")
        db_session.commit()

        db_session.add(
            User(
                first_name="Ada",
                last_name="Lovelace",
                name_key="ada|lovelace",  # same key — must be rejected
                created_at="2026-08-13T00:00:01Z",
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_different_name_keys_are_allowed(self, db_session):
        _make_user(db_session, name_key="ada|lovelace")
        _make_user(db_session, first="Grace", last="Hopper", name_key="grace|hopper")
        db_session.commit()
        assert db_session.query(User).count() == 2


# ── 3. Foreign-key enforcement ────────────────────────────────────────────────

class TestForeignKeyEnforcement:
    def test_activity_with_nonexistent_user_id_is_rejected(self, db_session):
        """FK constraint must prevent orphan activities."""
        db_session.add(
            Activity(
                user_id=99999,  # no such user
                sport_type="running",
                metric_type="distance",
                distance_km=5.0,
                duration_sec=None,
                step_count=None,
                points=500,
                recorded_at="2026-08-12T18:30:00Z",
                activity_date="2026-08-13",
                created_at="2026-08-12T18:30:00Z",
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_leaderboard_entry_with_nonexistent_snapshot_is_rejected(self, db_session):
        user = _make_user(db_session)
        db_session.commit()

        db_session.add(
            LeaderboardEntry(
                snapshot_id=99999,  # no such snapshot
                user_id=user.id,
                rank=1,
                total_points=100,
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_leaderboard_entry_with_nonexistent_user_is_rejected(self, db_session):
        snapshot = _make_snapshot(db_session)
        db_session.commit()

        db_session.add(
            LeaderboardEntry(
                snapshot_id=snapshot.id,
                user_id=99999,  # no such user
                rank=1,
                total_points=100,
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()


# ── 4. Daily steps uniqueness ─────────────────────────────────────────────────

class TestDailyStepsUniqueness:
    def test_second_daily_steps_same_user_same_date_raises(self, db_session):
        """Only one daily_steps row allowed per (user_id, activity_date)."""
        user = _make_user(db_session)
        db_session.commit()

        _make_steps_activity(db_session, user.id, activity_date="2026-08-13")
        db_session.commit()

        with pytest.raises(IntegrityError):
            _make_steps_activity(db_session, user.id, activity_date="2026-08-13")
            db_session.flush()

    def test_daily_steps_different_dates_allowed(self, db_session):
        """Same user, different dates — two rows must be accepted."""
        user = _make_user(db_session)
        db_session.commit()

        _make_steps_activity(db_session, user.id, activity_date="2026-08-13")
        _make_steps_activity(db_session, user.id, activity_date="2026-08-14")
        db_session.commit()

        count = (
            db_session.query(Activity)
            .filter_by(user_id=user.id, sport_type="daily_steps")
            .count()
        )
        assert count == 2

    def test_daily_steps_different_users_same_date_allowed(self, db_session):
        """Two different users can each have a daily_steps row on the same date."""
        u1 = _make_user(db_session, first="Ada", last="Lovelace", name_key="ada|lovelace")
        u2 = _make_user(db_session, first="Grace", last="Hopper", name_key="grace|hopper")
        db_session.commit()

        _make_steps_activity(db_session, u1.id, activity_date="2026-08-13")
        _make_steps_activity(db_session, u2.id, activity_date="2026-08-13")
        db_session.commit()

        assert db_session.query(Activity).filter_by(sport_type="daily_steps").count() == 2

    def test_non_steps_sport_not_affected_by_partial_index(self, db_session):
        """
        The partial index only covers daily_steps.
        Two running rows for the same user on the same date must be allowed.
        """
        user = _make_user(db_session)
        db_session.commit()

        _make_running_activity(db_session, user.id, activity_date="2026-08-13")
        _make_running_activity(db_session, user.id, activity_date="2026-08-13")
        db_session.commit()

        assert (
            db_session.query(Activity)
            .filter_by(user_id=user.id, sport_type="running")
            .count()
            == 2
        )


# ── 5. Snapshot date uniqueness ───────────────────────────────────────────────

class TestSnapshotDateUniqueness:
    def test_duplicate_snapshot_date_raises(self, db_session):
        _make_snapshot(db_session, snapshot_date="2026-08-12")
        db_session.commit()

        db_session.add(
            LeaderboardSnapshot(
                snapshot_date="2026-08-12",  # duplicate — must be rejected
                created_at="2026-08-13T01:00:00Z",
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_different_snapshot_dates_allowed(self, db_session):
        _make_snapshot(db_session, snapshot_date="2026-08-12")
        _make_snapshot(db_session, snapshot_date="2026-08-13")
        db_session.commit()

        assert db_session.query(LeaderboardSnapshot).count() == 2


# ── 6. Snapshot → entry relationship ─────────────────────────────────────────

class TestSnapshotEntryRelationship:
    def test_entries_accessible_via_snapshot(self, db_session):
        user = _make_user(db_session)
        snapshot = _make_snapshot(db_session)
        db_session.commit()

        entry = LeaderboardEntry(
            snapshot_id=snapshot.id,
            user_id=user.id,
            rank=1,
            total_points=500,
        )
        db_session.add(entry)
        db_session.commit()

        db_session.refresh(snapshot)
        assert len(snapshot.entries) == 1
        assert snapshot.entries[0].rank == 1
        assert snapshot.entries[0].total_points == 500

    def test_multiple_entries_per_snapshot(self, db_session):
        u1 = _make_user(db_session, first="Ada", last="Lovelace", name_key="ada|lovelace")
        u2 = _make_user(db_session, first="Grace", last="Hopper", name_key="grace|hopper")
        snapshot = _make_snapshot(db_session)
        db_session.commit()

        db_session.add_all([
            LeaderboardEntry(snapshot_id=snapshot.id, user_id=u1.id, rank=1, total_points=500),
            LeaderboardEntry(snapshot_id=snapshot.id, user_id=u2.id, rank=2, total_points=300),
        ])
        db_session.commit()

        db_session.refresh(snapshot)
        assert len(snapshot.entries) == 2


# ── 7. Activity → user relationship ──────────────────────────────────────────

class TestActivityUserRelationship:
    def test_activity_user_resolves_correctly(self, db_session):
        user = _make_user(db_session, first="Ada", last="Lovelace")
        db_session.commit()

        activity = _make_running_activity(db_session, user.id)
        db_session.commit()

        db_session.refresh(activity)
        assert activity.user.id == user.id
        assert activity.user.first_name == "Ada"

    def test_user_activities_relationship(self, db_session):
        user = _make_user(db_session)
        db_session.commit()

        _make_running_activity(db_session, user.id, activity_date="2026-08-13")
        _make_steps_activity(db_session, user.id, activity_date="2026-08-13")
        db_session.commit()

        db_session.refresh(user)
        assert len(user.activities) == 2


# ── 8. NOT NULL constraints ───────────────────────────────────────────────────

class TestNotNullConstraints:
    def test_user_missing_first_name_raises(self, db_session):
        db_session.add(
            User(first_name=None, last_name="Lovelace", name_key="none|lovelace",
                 created_at="2026-08-13T00:00:00Z")
        )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_user_missing_name_key_raises(self, db_session):
        db_session.add(
            User(first_name="Ada", last_name="Lovelace", name_key=None,
                 created_at="2026-08-13T00:00:00Z")
        )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_activity_missing_points_raises(self, db_session):
        user = _make_user(db_session)
        db_session.commit()

        db_session.add(
            Activity(
                user_id=user.id,
                sport_type="running",
                metric_type="distance",
                distance_km=5.0,
                duration_sec=None,
                step_count=None,
                points=None,  # NOT NULL violated
                recorded_at="2026-08-12T18:30:00Z",
                activity_date="2026-08-13",
                created_at="2026-08-12T18:30:00Z",
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_activity_missing_activity_date_raises(self, db_session):
        user = _make_user(db_session)
        db_session.commit()

        db_session.add(
            Activity(
                user_id=user.id,
                sport_type="running",
                metric_type="distance",
                distance_km=5.0,
                duration_sec=None,
                step_count=None,
                points=500,
                recorded_at="2026-08-12T18:30:00Z",
                activity_date=None,  # NOT NULL violated
                created_at="2026-08-12T18:30:00Z",
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_snapshot_missing_snapshot_date_raises(self, db_session):
        db_session.add(
            LeaderboardSnapshot(snapshot_date=None, created_at="2026-08-13T00:00:00Z")
        )
        with pytest.raises(IntegrityError):
            db_session.flush()


# ── 9. Activity CHECK constraint — structural metric validation ───────────────

class TestActivityCheckConstraint:
    def test_distance_km_on_duration_row_is_rejected(self, db_session):
        """
        metric_type='duration' requires duration_sec only.
        Setting distance_km violates the CHECK constraint (SRS §7).
        """
        user = _make_user(db_session)
        db_session.commit()

        db_session.add(
            Activity(
                user_id=user.id,
                sport_type="swimming",
                metric_type="duration",
                distance_km=5.0,        # must be NULL for duration type
                duration_sec=1800,
                step_count=None,
                points=450,
                recorded_at="2026-08-12T18:30:00Z",
                activity_date="2026-08-13",
                created_at="2026-08-12T18:30:00Z",
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_duration_sec_on_distance_row_is_rejected(self, db_session):
        """
        metric_type='distance' requires distance_km only.
        Setting duration_sec violates the CHECK constraint.
        """
        user = _make_user(db_session)
        db_session.commit()

        db_session.add(
            Activity(
                user_id=user.id,
                sport_type="running",
                metric_type="distance",
                distance_km=5.0,
                duration_sec=1800,      # must be NULL for distance type
                step_count=None,
                points=500,
                recorded_at="2026-08-12T18:30:00Z",
                activity_date="2026-08-13",
                created_at="2026-08-12T18:30:00Z",
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_step_count_on_distance_row_is_rejected(self, db_session):
        """Setting step_count on a distance-type row is structurally invalid."""
        user = _make_user(db_session)
        db_session.commit()

        db_session.add(
            Activity(
                user_id=user.id,
                sport_type="running",
                metric_type="distance",
                distance_km=5.0,
                duration_sec=None,
                step_count=8000,        # must be NULL for distance type
                points=500,
                recorded_at="2026-08-12T18:30:00Z",
                activity_date="2026-08-13",
                created_at="2026-08-12T18:30:00Z",
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_all_metric_fields_null_is_rejected(self, db_session):
        """A row with no metric value set at all must be rejected."""
        user = _make_user(db_session)
        db_session.commit()

        db_session.add(
            Activity(
                user_id=user.id,
                sport_type="running",
                metric_type="distance",
                distance_km=None,       # all NULL — violates CHECK
                duration_sec=None,
                step_count=None,
                points=0,
                recorded_at="2026-08-12T18:30:00Z",
                activity_date="2026-08-13",
                created_at="2026-08-12T18:30:00Z",
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_valid_distance_activity_is_accepted(self, db_session):
        user = _make_user(db_session)
        db_session.commit()
        activity = _make_running_activity(db_session, user.id)
        db_session.commit()
        assert activity.id is not None

    def test_valid_duration_activity_is_accepted(self, db_session):
        user = _make_user(db_session)
        db_session.commit()

        activity = Activity(
            user_id=user.id,
            sport_type="gym",
            metric_type="duration",
            distance_km=None,
            duration_sec=3600,
            step_count=None,
            points=300,
            recorded_at="2026-08-12T18:30:00Z",
            activity_date="2026-08-13",
            created_at="2026-08-12T18:30:00Z",
        )
        db_session.add(activity)
        db_session.commit()
        assert activity.id is not None

    def test_valid_steps_activity_is_accepted(self, db_session):
        user = _make_user(db_session)
        db_session.commit()
        activity = _make_steps_activity(db_session, user.id)
        db_session.commit()
        assert activity.id is not None


# ── 10. Duplicate leaderboard_entries rejected ────────────────────────────────

class TestLeaderboardEntryUniqueness:
    def test_duplicate_snapshot_user_pair_raises(self, db_session):
        """(snapshot_id, user_id) must be unique within a snapshot."""
        user = _make_user(db_session)
        snapshot = _make_snapshot(db_session)
        db_session.commit()

        db_session.add(
            LeaderboardEntry(snapshot_id=snapshot.id, user_id=user.id, rank=1, total_points=500)
        )
        db_session.flush()

        db_session.add(
            LeaderboardEntry(snapshot_id=snapshot.id, user_id=user.id, rank=1, total_points=500)
        )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_same_user_in_different_snapshots_allowed(self, db_session):
        """A user can appear in multiple distinct snapshots."""
        user = _make_user(db_session)
        s1 = _make_snapshot(db_session, snapshot_date="2026-08-11")
        s2 = _make_snapshot(db_session, snapshot_date="2026-08-12")
        db_session.commit()

        db_session.add_all([
            LeaderboardEntry(snapshot_id=s1.id, user_id=user.id, rank=1, total_points=300),
            LeaderboardEntry(snapshot_id=s2.id, user_id=user.id, rank=1, total_points=500),
        ])
        db_session.commit()

        assert db_session.query(LeaderboardEntry).filter_by(user_id=user.id).count() == 2
