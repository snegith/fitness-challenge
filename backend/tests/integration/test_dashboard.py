"""
Integration tests — dashboard endpoint (GET /api/users/{id}/dashboard).

Coverage (SRS §11, FR-14, FR-15, US-7):
    - Own dashboard returns 200 with correct aggregates.
    - totalPoints == sum of all activity points.
    - activityHistory contains all activities with correct fields.
    - activityHistory ordered by recorded_at DESC (most recent first).
    - volumeOverTime grouped by activity_date, ordered date ASC.
    - volumeOverTime is sparse (no zero-filled missing dates).
    - sportBreakdown sums to totalPoints.
    - Zero-activity user → 200 with empty data.
    - Wrong-user dashboard → 403 FORBIDDEN.
    - Missing token → 401 UNAUTHORIZED.
    - Invalid token → 401 UNAUTHORIZED.
    - Daily steps participate in dashboard totals.
    - User isolation (other user's activities not included).
    - IST activity_date semantics (uses stored column directly).
"""

from app.db.models import Activity

# ── Helpers ────────────────────────────────────────────────────────────────────


def _register(client, first="Ada", last="Lovelace"):
    resp = client.post("/api/auth/register", json={
        "firstName": first, "lastName": last,
    })
    assert resp.status_code == 201
    body = resp.json()
    return body["userId"], body["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _add_activity(db, user_id, sport_type, points, *,
                  activity_date="2026-08-13", recorded_at="2026-08-13T07:00:00Z"):
    """Directly insert an activity row for testing."""
    metric_map = {
        "running": ("distance", {"distance_km": points / 100.0}),
        "walking": ("distance", {"distance_km": points / 50.0}),
        "cycling": ("distance", {"distance_km": points / 25.0}),
        "swimming": ("duration", {"duration_sec": (points // 15) * 60}),
        "gym": ("duration", {"duration_sec": (points // 5) * 60}),
        "daily_steps": ("count", {"step_count": points * 100}),
    }
    metric_type, fields = metric_map[sport_type]
    a = Activity(
        user_id=user_id,
        sport_type=sport_type,
        metric_type=metric_type,
        distance_km=fields.get("distance_km"),
        duration_sec=fields.get("duration_sec"),
        step_count=fields.get("step_count"),
        points=points,
        recorded_at=recorded_at,
        activity_date=activity_date,
    )
    db.add(a)
    db.flush()
    return a


# ── Access control ─────────────────────────────────────────────────────────────


class TestDashboardAccess:
    def test_own_dashboard_returns_200(self, client, db_session):
        user_id, token = _register(client)
        resp = client.get(f"/api/users/{user_id}/dashboard", headers=_auth(token))
        assert resp.status_code == 200

    def test_other_user_dashboard_returns_403(self, client, db_session):
        _, token_a = _register(client, "Ada", "Lovelace")
        user_b, _ = _register(client, "Grace", "Hopper")
        resp = client.get(f"/api/users/{user_b}/dashboard", headers=_auth(token_a))
        assert resp.status_code == 403
        assert resp.json()["error"] == "FORBIDDEN"

    def test_missing_token_returns_401(self, client, db_session):
        user_id, _ = _register(client)
        resp = client.get(f"/api/users/{user_id}/dashboard")
        assert resp.status_code == 401
        assert resp.json()["error"] == "UNAUTHORIZED"

    def test_invalid_token_returns_401(self, client, db_session):
        user_id, _ = _register(client)
        resp = client.get(
            f"/api/users/{user_id}/dashboard",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401


# ── Empty dashboard ────────────────────────────────────────────────────────────


class TestEmptyDashboard:
    def test_zero_activities_returns_empty_dashboard(self, client, db_session):
        user_id, token = _register(client)
        resp = client.get(f"/api/users/{user_id}/dashboard", headers=_auth(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["totalPoints"] == 0
        assert body["activityHistory"] == []
        assert body["volumeOverTime"] == []
        assert body["sportBreakdown"] == {}


# ── totalPoints ────────────────────────────────────────────────────────────────


class TestTotalPoints:
    def test_total_points_equals_sum_of_activities(self, client, db_session):
        user_id, token = _register(client)
        _add_activity(db_session, user_id, "running", 500)
        _add_activity(db_session, user_id, "gym", 300)
        db_session.commit()

        resp = client.get(f"/api/users/{user_id}/dashboard", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["totalPoints"] == 800


# ── activityHistory ────────────────────────────────────────────────────────────


class TestActivityHistory:
    def test_contains_all_activities(self, client, db_session):
        user_id, token = _register(client)
        _add_activity(db_session, user_id, "running", 500)
        _add_activity(db_session, user_id, "swimming", 450)
        db_session.commit()

        resp = client.get(f"/api/users/{user_id}/dashboard", headers=_auth(token))
        history = resp.json()["activityHistory"]
        assert len(history) == 2

    def test_fields_present(self, client, db_session):
        user_id, token = _register(client)
        _add_activity(db_session, user_id, "running", 500,
                      recorded_at="2026-08-13T01:30:00Z")
        db_session.commit()

        resp = client.get(f"/api/users/{user_id}/dashboard", headers=_auth(token))
        item = resp.json()["activityHistory"][0]
        assert "activityId" in item
        assert item["sportType"] == "running"
        assert item["points"] == 500
        assert item["recordedAt"] == "2026-08-13T01:30:00Z"

    def test_ordered_by_recorded_at_desc(self, client, db_session):
        user_id, token = _register(client)
        _add_activity(db_session, user_id, "running", 100,
                      recorded_at="2026-08-10T10:00:00Z")
        _add_activity(db_session, user_id, "gym", 200,
                      recorded_at="2026-08-12T10:00:00Z")
        _add_activity(db_session, user_id, "walking", 50,
                      recorded_at="2026-08-11T10:00:00Z")
        db_session.commit()

        resp = client.get(f"/api/users/{user_id}/dashboard", headers=_auth(token))
        history = resp.json()["activityHistory"]
        recorded_ats = [h["recordedAt"] for h in history]
        assert recorded_ats == sorted(recorded_ats, reverse=True)


# ── volumeOverTime ─────────────────────────────────────────────────────────────


class TestVolumeOverTime:
    def test_grouped_by_activity_date(self, client, db_session):
        user_id, token = _register(client)
        _add_activity(db_session, user_id, "running", 300, activity_date="2026-08-13")
        _add_activity(db_session, user_id, "gym", 200, activity_date="2026-08-13")
        _add_activity(db_session, user_id, "walking", 100, activity_date="2026-08-14")
        db_session.commit()

        resp = client.get(f"/api/users/{user_id}/dashboard", headers=_auth(token))
        volume = resp.json()["volumeOverTime"]
        assert len(volume) == 2
        aug13 = next(v for v in volume if v["date"] == "2026-08-13")
        aug14 = next(v for v in volume if v["date"] == "2026-08-14")
        assert aug13["points"] == 500
        assert aug14["points"] == 100

    def test_ordered_date_ascending(self, client, db_session):
        user_id, token = _register(client)
        _add_activity(db_session, user_id, "running", 100, activity_date="2026-08-15")
        _add_activity(db_session, user_id, "gym", 200, activity_date="2026-08-10")
        db_session.commit()

        resp = client.get(f"/api/users/{user_id}/dashboard", headers=_auth(token))
        volume = resp.json()["volumeOverTime"]
        dates = [v["date"] for v in volume]
        assert dates == sorted(dates)

    def test_sparse_no_zero_fill(self, client, db_session):
        """Only dates with activities appear — no zero-filled gaps."""
        user_id, token = _register(client)
        _add_activity(db_session, user_id, "running", 100, activity_date="2026-08-10")
        _add_activity(db_session, user_id, "gym", 200, activity_date="2026-08-15")
        db_session.commit()

        resp = client.get(f"/api/users/{user_id}/dashboard", headers=_auth(token))
        volume = resp.json()["volumeOverTime"]
        dates = [v["date"] for v in volume]
        # Only the two actual dates — nothing in between
        assert dates == ["2026-08-10", "2026-08-15"]
        assert len(volume) == 2


# ── sportBreakdown ─────────────────────────────────────────────────────────────


class TestSportBreakdown:
    def test_grouped_by_sport(self, client, db_session):
        user_id, token = _register(client)
        _add_activity(db_session, user_id, "running", 300)
        _add_activity(db_session, user_id, "running", 200)
        _add_activity(db_session, user_id, "gym", 100)
        db_session.commit()

        resp = client.get(f"/api/users/{user_id}/dashboard", headers=_auth(token))
        breakdown = resp.json()["sportBreakdown"]
        assert breakdown["running"] == 500
        assert breakdown["gym"] == 100

    def test_breakdown_sums_to_total(self, client, db_session):
        user_id, token = _register(client)
        _add_activity(db_session, user_id, "running", 300)
        _add_activity(db_session, user_id, "swimming", 450)
        _add_activity(db_session, user_id, "daily_steps", 83)
        db_session.commit()

        resp = client.get(f"/api/users/{user_id}/dashboard", headers=_auth(token))
        body = resp.json()
        assert sum(body["sportBreakdown"].values()) == body["totalPoints"]


# ── Daily steps ────────────────────────────────────────────────────────────────


class TestDailySteps:
    def test_daily_steps_in_dashboard(self, client, db_session):
        user_id, token = _register(client)
        _add_activity(db_session, user_id, "daily_steps", 83,
                      activity_date="2026-08-13")
        db_session.commit()

        resp = client.get(f"/api/users/{user_id}/dashboard", headers=_auth(token))
        body = resp.json()
        assert body["totalPoints"] == 83
        assert body["sportBreakdown"]["daily_steps"] == 83
        assert any(v["date"] == "2026-08-13" and v["points"] == 83
                   for v in body["volumeOverTime"])


# ── User isolation ─────────────────────────────────────────────────────────────


class TestUserIsolation:
    def test_other_users_activities_not_included(self, client, db_session):
        user_a, token_a = _register(client, "Ada", "Lovelace")
        user_b, _ = _register(client, "Grace", "Hopper")
        _add_activity(db_session, user_a, "running", 500)
        _add_activity(db_session, user_b, "gym", 9999)
        db_session.commit()

        resp = client.get(f"/api/users/{user_a}/dashboard", headers=_auth(token_a))
        body = resp.json()
        assert body["totalPoints"] == 500
        assert len(body["activityHistory"]) == 1


# ── IST activity_date semantics ────────────────────────────────────────────────


class TestISTSemantics:
    def test_volume_uses_stored_activity_date(self, client, db_session):
        """
        activity_date is pre-computed as IST calendar day at write time.
        Dashboard must use it directly — no re-derivation from recorded_at.
        """
        user_id, token = _register(client)
        # recorded_at is UTC 18:30 Aug 13 = IST 00:00 Aug 14 → activity_date = Aug 14
        _add_activity(db_session, user_id, "running", 100,
                      activity_date="2026-08-14",
                      recorded_at="2026-08-13T18:30:00Z")
        db_session.commit()

        resp = client.get(f"/api/users/{user_id}/dashboard", headers=_auth(token))
        volume = resp.json()["volumeOverTime"]
        assert len(volume) == 1
        assert volume[0]["date"] == "2026-08-14"
