"""
Integration tests — activity ingestion (POST /api/activities).

Tests the full HTTP → service → database round-trip.
Activities require a valid Bearer token (userId derived from the token).
recordedAt is server-generated — never client-supplied (SRS §8, R11).

Coverage:
    - Valid activities for all 6 sports → correct points
    - Validation errors (invalid sport, missing metric, extra fields)
    - recordedAt is server-generated UTC (not client-supplied)
    - activity_date is derived from server-generated timestamp using IST
    - Daily Steps upsert semantics (replace, not accumulate)
    - Client-supplied recordedAt rejected (extra='forbid')
    - Client-supplied userId rejected
    - Missing token → 401
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.db.models import Activity

# ── Helpers ────────────────────────────────────────────────────────────────────


def _register_user(client, *, first="Ada", last="Lovelace"):
    """Register a user via the API and return (user_id, token)."""
    resp = client.post("/api/auth/register", json={
        "firstName": first,
        "lastName": last,
    })
    assert resp.status_code == 201, f"Registration failed: {resp.json()}"
    body = resp.json()
    return body["userId"], body["token"]


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def _post_activity(client, payload, token):
    return client.post("/api/activities", json=payload, headers=_auth_header(token))


# ── Distance sports ────────────────────────────────────────────────────────────


class TestDistanceActivities:
    def test_running_correct_points(self, client, db_session):
        _, token = _register_user(client)
        resp = _post_activity(client, {
            "sportType": "running",
            "distanceKm": 5.3,
        }, token)
        assert resp.status_code == 201
        body = resp.json()
        assert body["sportType"] == "running"
        assert body["points"] == 530
        assert "activityId" in body
        assert "recordedAt" in body

    def test_walking_correct_points(self, client, db_session):
        _, token = _register_user(client)
        resp = _post_activity(client, {
            "sportType": "walking",
            "distanceKm": 1.55,
        }, token)
        assert resp.status_code == 201
        assert resp.json()["points"] == 77

    def test_cycling_correct_points(self, client, db_session):
        _, token = _register_user(client)
        resp = _post_activity(client, {
            "sportType": "cycling",
            "distanceKm": 10.0,
        }, token)
        assert resp.status_code == 201
        assert resp.json()["points"] == 250


# ── Duration sports ────────────────────────────────────────────────────────────


class TestDurationActivities:
    def test_swimming_correct_points(self, client, db_session):
        _, token = _register_user(client)
        resp = _post_activity(client, {
            "sportType": "swimming",
            "durationSec": 1855,
        }, token)
        assert resp.status_code == 201
        assert resp.json()["points"] == 450

    def test_gym_correct_points(self, client, db_session):
        _, token = _register_user(client)
        resp = _post_activity(client, {
            "sportType": "gym",
            "durationSec": 3600,
        }, token)
        assert resp.status_code == 201
        assert resp.json()["points"] == 300

    def test_sub_60s_gym_returns_zero_points(self, client, db_session):
        _, token = _register_user(client)
        resp = _post_activity(client, {
            "sportType": "gym",
            "durationSec": 55,
        }, token)
        assert resp.status_code == 201
        assert resp.json()["points"] == 0


# ── Daily Steps ────────────────────────────────────────────────────────────────


class TestDailyStepsBasic:
    def test_daily_steps_correct_points(self, client, db_session):
        _, token = _register_user(client)
        resp = _post_activity(client, {
            "sportType": "daily_steps",
            "stepCount": 8342,
        }, token)
        assert resp.status_code == 201
        assert resp.json()["points"] == 83


# ── Validation errors ──────────────────────────────────────────────────────────


class TestValidation:
    def test_invalid_sport_type_returns_400(self, client, db_session):
        _, token = _register_user(client)
        resp = _post_activity(client, {"sportType": "yoga", "distanceKm": 5.0}, token)
        assert resp.status_code == 400
        assert resp.json()["error"] == "VALIDATION_ERROR"

    def test_missing_required_metric_returns_400(self, client, db_session):
        _, token = _register_user(client)
        resp = _post_activity(client, {"sportType": "running"}, token)
        assert resp.status_code == 400
        assert resp.json()["error"] == "VALIDATION_ERROR"

    def test_wrong_metric_running_plus_duration(self, client, db_session):
        _, token = _register_user(client)
        resp = _post_activity(client, {"sportType": "running", "durationSec": 1800}, token)
        assert resp.status_code == 400

    def test_extra_metric_running_plus_step_count(self, client, db_session):
        _, token = _register_user(client)
        resp = _post_activity(client, {
            "sportType": "running", "distanceKm": 5.0, "stepCount": 1000,
        }, token)
        assert resp.status_code == 400

    def test_swimming_with_distance_km_returns_400(self, client, db_session):
        _, token = _register_user(client)
        resp = _post_activity(client, {"sportType": "swimming", "distanceKm": 1.5}, token)
        assert resp.status_code == 400

    def test_daily_steps_with_distance_km_returns_400(self, client, db_session):
        _, token = _register_user(client)
        resp = _post_activity(client, {
            "sportType": "daily_steps", "distanceKm": 1.5, "stepCount": 5000,
        }, token)
        assert resp.status_code == 400

    def test_daily_steps_with_duration_sec_returns_400(self, client, db_session):
        _, token = _register_user(client)
        resp = _post_activity(client, {
            "sportType": "daily_steps", "durationSec": 3600, "stepCount": 5000,
        }, token)
        assert resp.status_code == 400

    def test_distance_zero_returns_400(self, client, db_session):
        _, token = _register_user(client)
        resp = _post_activity(client, {"sportType": "running", "distanceKm": 0}, token)
        assert resp.status_code == 400

    def test_missing_token_returns_401(self, client, db_session):
        resp = client.post("/api/activities", json={"sportType": "running", "distanceKm": 5.0})
        assert resp.status_code == 401
        assert resp.json()["error"] == "UNAUTHORIZED"

    def test_client_supplied_points_rejected(self, client, db_session):
        _, token = _register_user(client)
        resp = _post_activity(client, {
            "sportType": "running", "distanceKm": 5.0, "points": 9999,
        }, token)
        assert resp.status_code == 400

    def test_missing_sport_type_returns_400(self, client, db_session):
        _, token = _register_user(client)
        resp = _post_activity(client, {"distanceKm": 5.0}, token)
        assert resp.status_code == 400

    def test_client_supplied_user_id_in_body_rejected(self, client, db_session):
        """userId in body must be rejected (extra='forbid')."""
        _, token = _register_user(client)
        resp = _post_activity(client, {
            "userId": 1, "sportType": "running", "distanceKm": 5.0,
        }, token)
        assert resp.status_code == 400

    def test_client_supplied_recorded_at_rejected(self, client, db_session):
        """recordedAt is server-generated; client-supplied value must be rejected (SRS R11)."""
        _, token = _register_user(client)
        resp = _post_activity(client, {
            "sportType": "running",
            "distanceKm": 5.0,
            "recordedAt": "2026-08-13T07:00:00+05:30",
        }, token)
        assert resp.status_code == 400
        assert resp.json()["error"] == "VALIDATION_ERROR"

    def test_client_supplied_activity_date_rejected(self, client, db_session):
        _, token = _register_user(client)
        resp = _post_activity(client, {
            "sportType": "running", "distanceKm": 5.0, "activityDate": "2026-08-13",
        }, token)
        assert resp.status_code == 400

    def test_negative_duration_sec_returns_400(self, client, db_session):
        _, token = _register_user(client)
        resp = _post_activity(client, {"sportType": "gym", "durationSec": -1}, token)
        assert resp.status_code == 400

    def test_negative_step_count_returns_400(self, client, db_session):
        _, token = _register_user(client)
        resp = _post_activity(client, {"sportType": "daily_steps", "stepCount": -1}, token)
        assert resp.status_code == 400


# ── Server-generated recordedAt and IST activity_date ──────────────────────────


class TestServerGeneratedTimestamp:
    def test_running_without_recorded_at_succeeds(self, client, db_session):
        """No recordedAt in request — server generates it."""
        _, token = _register_user(client)
        resp = _post_activity(client, {"sportType": "running", "distanceKm": 5.0}, token)
        assert resp.status_code == 201
        assert "recordedAt" in resp.json()

    def test_swimming_without_recorded_at_succeeds(self, client, db_session):
        _, token = _register_user(client)
        resp = _post_activity(client, {"sportType": "swimming", "durationSec": 120}, token)
        assert resp.status_code == 201
        assert "recordedAt" in resp.json()

    def test_daily_steps_without_recorded_at_succeeds(self, client, db_session):
        _, token = _register_user(client)
        resp = _post_activity(client, {"sportType": "daily_steps", "stepCount": 5000}, token)
        assert resp.status_code == 201
        assert "recordedAt" in resp.json()

    def test_recorded_at_is_server_generated_utc(self, client, db_session):
        """The returned recordedAt must be a valid UTC ISO 8601 string."""
        _, token = _register_user(client)
        resp = _post_activity(client, {"sportType": "running", "distanceKm": 3.0}, token)
        assert resp.status_code == 201
        recorded_at = resp.json()["recordedAt"]
        # Must end with Z (UTC)
        assert recorded_at.endswith("Z")
        # Must be parseable as ISO 8601
        dt = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
        assert dt.tzinfo is not None

    def test_activity_date_derived_from_server_timestamp_ist(self, client, db_session):
        """activity_date in DB is the IST calendar date of the server-generated timestamp."""
        user_id, token = _register_user(client)
        resp = _post_activity(client, {"sportType": "running", "distanceKm": 3.0}, token)
        assert resp.status_code == 201
        activity_id = resp.json()["activityId"]
        activity = db_session.query(Activity).filter_by(id=activity_id).one()

        # activity_date must equal today's IST date
        expected = datetime.now(tz=ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
        assert activity.activity_date == expected

    def test_activity_stored_against_token_user(self, client, db_session):
        """Activity is stored against the userId from the token."""
        user_id, token = _register_user(client)
        resp = _post_activity(client, {"sportType": "running", "distanceKm": 5.0}, token)
        assert resp.status_code == 201
        activity_id = resp.json()["activityId"]
        activity = db_session.query(Activity).filter_by(id=activity_id).one()
        assert activity.user_id == user_id


# ── Daily Steps upsert semantics ──────────────────────────────────────────────


class TestDailyStepsUpsert:
    def test_first_submission_inserts_row(self, client, db_session):
        user_id, token = _register_user(client)
        resp = _post_activity(client, {"sportType": "daily_steps", "stepCount": 5000}, token)
        assert resp.status_code == 201
        assert resp.json()["points"] == 50
        count = db_session.query(Activity).filter_by(
            user_id=user_id, sport_type="daily_steps"
        ).count()
        assert count == 1

    def test_second_submission_same_date_updates_row(self, client, db_session):
        _, token = _register_user(client)
        _post_activity(client, {"sportType": "daily_steps", "stepCount": 5000}, token)
        r2 = _post_activity(client, {"sportType": "daily_steps", "stepCount": 9000}, token)
        assert r2.status_code == 200
        assert r2.json()["updated"] is True
        assert r2.json()["points"] == 90

    def test_no_duplicate_row_after_second_submission(self, client, db_session):
        user_id, token = _register_user(client)
        _post_activity(client, {"sportType": "daily_steps", "stepCount": 5000}, token)
        _post_activity(client, {"sportType": "daily_steps", "stepCount": 9000}, token)
        today = datetime.now(tz=ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
        count = db_session.query(Activity).filter_by(
            user_id=user_id, sport_type="daily_steps", activity_date=today,
        ).count()
        assert count == 1

    def test_update_replaces_count_not_adds(self, client, db_session):
        user_id, token = _register_user(client)
        _post_activity(client, {"sportType": "daily_steps", "stepCount": 8342}, token)
        _post_activity(client, {"sportType": "daily_steps", "stepCount": 9120}, token)
        today = datetime.now(tz=ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
        activity = db_session.query(Activity).filter_by(
            user_id=user_id, sport_type="daily_steps", activity_date=today,
        ).one()
        assert activity.step_count == 9120

    def test_points_recomputed_after_update(self, client, db_session):
        user_id, token = _register_user(client)
        _post_activity(client, {"sportType": "daily_steps", "stepCount": 8342}, token)
        r2 = _post_activity(client, {"sportType": "daily_steps", "stepCount": 9120}, token)
        assert r2.json()["points"] == 91
        today = datetime.now(tz=ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
        activity = db_session.query(Activity).filter_by(
            user_id=user_id, sport_type="daily_steps", activity_date=today,
        ).one()
        assert activity.points == 91


# ── Edge cases ─────────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_duration_zero_accepted_with_zero_points(self, client, db_session):
        _, token = _register_user(client)
        resp = _post_activity(client, {"sportType": "gym", "durationSec": 0}, token)
        assert resp.status_code == 201
        assert resp.json()["points"] == 0
