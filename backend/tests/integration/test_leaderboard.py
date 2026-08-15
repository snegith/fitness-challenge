"""
Integration tests — live leaderboard (GET /api/leaderboard).

Coverage (SRS §11.5 leaderboard portion):
    - Multiple users with different points → correct descending order.
    - Tie-break: equal points → earlier created_at ranks higher.
    - Tie-break: equal points + equal created_at → lower userId ranks higher.
    - Users with zero activities appear with totalPoints=0.
    - rankTrend correctly reflects a seeded prior-day snapshot.
    - rankTrend is null for a user with no prior snapshot.
    - Empty leaderboard → 200 with empty array.
    - Endpoint requires no authentication (public).
"""

from app.db.models import Activity, LeaderboardEntry, LeaderboardSnapshot, User

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


# ── Ordering ───────────────────────────────────────────────────────────────────


class TestLeaderboardOrdering:
    def test_ordered_by_total_points_descending(self, client, db_session):
        u1 = _make_user(db_session, "Ada", "Lovelace")
        u2 = _make_user(db_session, "Grace", "Hopper")
        _make_activity(db_session, u1.id, 100)
        _make_activity(db_session, u2.id, 500)
        db_session.commit()

        resp = client.get("/api/leaderboard")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["userId"] == u2.id
        assert data[0]["totalPoints"] == 500
        assert data[0]["rank"] == 1
        assert data[1]["userId"] == u1.id
        assert data[1]["totalPoints"] == 100
        assert data[1]["rank"] == 2

    def test_tie_broken_by_created_at(self, client, db_session):
        u1 = _make_user(db_session, "Ada", "Lovelace", created_at="2026-08-10T00:00:00Z")
        u2 = _make_user(db_session, "Grace", "Hopper", created_at="2026-08-11T00:00:00Z")
        _make_activity(db_session, u1.id, 300)
        _make_activity(db_session, u2.id, 300)
        db_session.commit()

        resp = client.get("/api/leaderboard")
        data = resp.json()
        # Same points — Ada registered earlier → ranks first
        assert data[0]["userId"] == u1.id
        assert data[1]["userId"] == u2.id

    def test_tie_broken_by_user_id(self, client, db_session):
        # Force identical created_at by setting the same value
        u1 = _make_user(db_session, "Ada", "Lovelace", created_at="2026-08-10T00:00:00Z")
        u2 = _make_user(db_session, "Grace", "Hopper", created_at="2026-08-10T00:00:00Z")
        _make_activity(db_session, u1.id, 300)
        _make_activity(db_session, u2.id, 300)
        db_session.commit()

        resp = client.get("/api/leaderboard")
        data = resp.json()
        # Same points, same created_at — lower userId ranks first
        assert data[0]["userId"] == u1.id
        assert data[1]["userId"] == u2.id

    def test_zero_activity_user_appears(self, client, db_session):
        """A user with no activities should appear with totalPoints=0."""
        u1 = _make_user(db_session, "Ada", "Lovelace")
        u2 = _make_user(db_session, "Grace", "Hopper")
        _make_activity(db_session, u1.id, 500)
        # u2 has no activities
        db_session.commit()

        resp = client.get("/api/leaderboard")
        data = resp.json()
        assert len(data) == 2
        assert data[0]["userId"] == u1.id
        assert data[0]["totalPoints"] == 500
        assert data[1]["userId"] == u2.id
        assert data[1]["totalPoints"] == 0


# ── Rank trend ─────────────────────────────────────────────────────────────────


class TestRankTrend:
    def test_rank_trend_with_prior_snapshot(self, client, db_session):
        u1 = _make_user(db_session, "Ada", "Lovelace")
        u2 = _make_user(db_session, "Grace", "Hopper")
        _make_activity(db_session, u1.id, 500)
        _make_activity(db_session, u2.id, 300)

        # Seed a snapshot where u1 was rank 2, u2 was rank 1
        snapshot = LeaderboardSnapshot(snapshot_date="2026-08-12")
        db_session.add(snapshot)
        db_session.flush()
        db_session.add(LeaderboardEntry(
            snapshot_id=snapshot.id, user_id=u1.id, rank=2, total_points=100
        ))
        db_session.add(LeaderboardEntry(
            snapshot_id=snapshot.id, user_id=u2.id, rank=1, total_points=400
        ))
        db_session.commit()

        resp = client.get("/api/leaderboard")
        data = resp.json()
        # Live: u1 rank 1 (500pts), u2 rank 2 (300pts)
        # u1: previousRank=2, currentRank=1, trend=2-1=1
        # u2: previousRank=1, currentRank=2, trend=1-2=-1
        assert data[0]["userId"] == u1.id
        assert data[0]["rankTrend"] == 1
        assert data[1]["userId"] == u2.id
        assert data[1]["rankTrend"] == -1

    def test_rank_trend_null_without_prior_snapshot(self, client, db_session):
        _make_user(db_session, "Ada", "Lovelace")
        db_session.commit()

        resp = client.get("/api/leaderboard")
        data = resp.json()
        assert data[0]["rankTrend"] is None


# ── Edge cases ─────────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_leaderboard_returns_200_empty_array(self, client, db_session):
        resp = client.get("/api/leaderboard")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_no_auth_required(self, client, db_session):
        """Leaderboard endpoint must be public — no token needed."""
        resp = client.get("/api/leaderboard")
        assert resp.status_code != 401

    def test_name_format(self, client, db_session):
        """Name field should be 'firstName lastName'."""
        _make_user(db_session, "Ada", "Lovelace")
        db_session.commit()
        resp = client.get("/api/leaderboard")
        assert resp.json()[0]["name"] == "Ada Lovelace"
