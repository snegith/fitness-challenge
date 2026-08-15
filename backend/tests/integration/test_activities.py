"""
Integration tests — activity ingestion (POST /api/activities).

Tests the full HTTP → service → database round-trip.

TEMPORARY DEVIATION NOTE:
    userId is supplied in the request body for this development unit because
    session-token authentication is deferred.  When auth is implemented these
    tests must be updated to use Bearer token identity instead.

Coverage (SRS §11.4 + task requirements §13):
    1.  Valid running activity → 201, correct points
    2.  Valid walking activity → 201, correct points
    3.  Valid cycling activity → 201, correct points
    4.  Valid swimming activity → 201, duration flooring
    5.  Valid gym activity → 201, duration flooring
    6.  Valid daily_steps activity → 201, correct points
    7.  Invalid sportType → 400 VALIDATION_ERROR
    8.  Missing required metric → 400 VALIDATION_ERROR
    9.  Wrong metric for sport (e.g. running + durationSec) → 400
    10. Extra/mismatched metric (e.g. running + stepCount) → 400
    11. Non-existent userId → 404 USER_NOT_FOUND
    12. Client-supplied points field is rejected → 400
    13. recordedAt is persisted as UTC in the DB
    14. activity_date is derived using IST
    15. IST boundary case: UTC 18:30 on date N → IST 00:00 date N+1 → activity_date = N+1
    16. Daily Steps first submission → inserts row
    17. Daily Steps second submission same IST date → updates same row (no duplicate)
    18. Daily Steps update replaces cumulative count (not adds)
    19. Daily Steps points are recomputed after update
    20. No duplicate daily_steps row for same user/date
    21. durationSec=55 (under 60s) → 0 points, not an error
    22. Daily Steps with no recordedAt → uses current IST date
    23. Invalid recordedAt string → 400 VALIDATION_ERROR (not 500)
    24. Negative durationSec → 400 VALIDATION_ERROR
    25. Negative stepCount → 400 VALIDATION_ERROR
    26. Client-supplied activityDate extra field → 400 VALIDATION_ERROR
"""

from app.db.models import Activity, User

# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_user(db, *, first="Ada", last="Lovelace"):
    """Insert a bare-minimum user row and return it."""
    user = User(
        first_name=first,
        last_name=last,
        name_key=f"{first.lower()}|{last.lower()}",
        created_at="2026-08-13T00:00:00Z",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _post_activity(client, payload):
    return client.post("/api/activities", json=payload)


# ── 1–3. Distance sports ───────────────────────────────────────────────────────

class TestDistanceActivities:
    def test_running_correct_points(self, client, db_session):
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "running",
            "distanceKm": 5.3,
            "recordedAt": "2026-08-13T07:00:00+05:30",
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["sportType"] == "running"
        assert body["points"] == 530  # floor(5.3 * 100)
        assert "activityId" in body
        assert "recordedAt" in body

    def test_walking_correct_points(self, client, db_session):
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "walking",
            "distanceKm": 1.55,
            "recordedAt": "2026-08-13T07:00:00+05:30",
        })
        assert resp.status_code == 201
        assert resp.json()["points"] == 77  # SRS §9.1 worked example

    def test_cycling_correct_points(self, client, db_session):
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "cycling",
            "distanceKm": 10.0,
            "recordedAt": "2026-08-13T07:00:00+05:30",
        })
        assert resp.status_code == 201
        assert resp.json()["points"] == 250  # floor(10.0 * 25)


# ── 4–5. Duration sports ───────────────────────────────────────────────────────

class TestDurationActivities:
    def test_swimming_correct_points(self, client, db_session):
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "swimming",
            "durationSec": 1855,
            "recordedAt": "2026-08-13T07:00:00+05:30",
        })
        assert resp.status_code == 201
        # floor(1855/60)*15 = 30*15 = 450
        assert resp.json()["points"] == 450

    def test_gym_correct_points(self, client, db_session):
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "gym",
            "durationSec": 3600,
            "recordedAt": "2026-08-13T07:00:00+05:30",
        })
        assert resp.status_code == 201
        assert resp.json()["points"] == 300  # floor(3600/60)*5

    def test_sub_60s_gym_returns_zero_points(self, client, db_session):
        """SRS US-4: durationSec < 60 → 0 points, still 201 (not an error)."""
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "gym",
            "durationSec": 55,
            "recordedAt": "2026-08-13T07:00:00+05:30",
        })
        assert resp.status_code == 201
        assert resp.json()["points"] == 0


# ── 6. Daily Steps ─────────────────────────────────────────────────────────────

class TestDailyStepsBasic:
    def test_daily_steps_correct_points(self, client, db_session):
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "daily_steps",
            "stepCount": 8342,
            "recordedAt": "2026-08-13",
        })
        assert resp.status_code == 201
        assert resp.json()["points"] == 83  # floor(8342/100)


# ── 7–12. Validation errors ────────────────────────────────────────────────────

class TestValidation:
    def test_invalid_sport_type_returns_400(self, client, db_session):
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "yoga",
            "distanceKm": 5.0,
            "recordedAt": "2026-08-13T07:00:00+05:30",
        })
        assert resp.status_code == 400
        assert resp.json()["error"] == "VALIDATION_ERROR"

    def test_missing_required_metric_returns_400(self, client, db_session):
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "running",
            # distanceKm missing
            "recordedAt": "2026-08-13T07:00:00+05:30",
        })
        assert resp.status_code == 400
        assert resp.json()["error"] == "VALIDATION_ERROR"

    def test_wrong_metric_running_plus_duration(self, client, db_session):
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "running",
            "durationSec": 1800,
            "recordedAt": "2026-08-13T07:00:00+05:30",
        })
        assert resp.status_code == 400
        assert resp.json()["error"] == "VALIDATION_ERROR"

    def test_extra_metric_running_plus_step_count(self, client, db_session):
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "running",
            "distanceKm": 5.0,
            "stepCount": 1000,
            "recordedAt": "2026-08-13T07:00:00+05:30",
        })
        assert resp.status_code == 400
        assert resp.json()["error"] == "VALIDATION_ERROR"

    def test_swimming_with_distance_km_returns_400(self, client, db_session):
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "swimming",
            "distanceKm": 1.5,
            "recordedAt": "2026-08-13T07:00:00+05:30",
        })
        assert resp.status_code == 400

    def test_daily_steps_with_distance_km_returns_400(self, client, db_session):
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "daily_steps",
            "distanceKm": 1.5,
            "stepCount": 5000,
            "recordedAt": "2026-08-13",
        })
        assert resp.status_code == 400

    def test_daily_steps_with_duration_sec_returns_400(self, client, db_session):
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "daily_steps",
            "durationSec": 3600,
            "stepCount": 5000,
            "recordedAt": "2026-08-13",
        })
        assert resp.status_code == 400

    def test_distance_zero_returns_400(self, client, db_session):
        """distanceKm must be > 0 (SRS §8)."""
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "running",
            "distanceKm": 0,
            "recordedAt": "2026-08-13T07:00:00+05:30",
        })
        assert resp.status_code == 400

    def test_nonexistent_user_returns_404(self, client, db_session):
        resp = _post_activity(client, {
            "userId": 99999,
            "sportType": "running",
            "distanceKm": 5.0,
            "recordedAt": "2026-08-13T07:00:00+05:30",
        })
        assert resp.status_code == 404
        assert resp.json()["error"] == "USER_NOT_FOUND"

    def test_client_supplied_points_rejected(self, client, db_session):
        """Points must never be accepted from the client (SRS §4, project rules §4)."""
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "running",
            "distanceKm": 5.0,
            "points": 9999,
            "recordedAt": "2026-08-13T07:00:00+05:30",
        })
        assert resp.status_code == 400

    def test_missing_sport_type_returns_400(self, client, db_session):
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "distanceKm": 5.0,
            "recordedAt": "2026-08-13T07:00:00+05:30",
        })
        assert resp.status_code == 400


# ── 13–15. Persistence and IST date derivation ─────────────────────────────────

class TestPersistenceAndIST:
    def test_recorded_at_persisted(self, client, db_session):
        """The submitted recordedAt is persisted (converted to UTC ISO string)."""
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "running",
            "distanceKm": 5.0,
            "recordedAt": "2026-08-13T07:00:00+05:30",
        })
        assert resp.status_code == 201
        activity_id = resp.json()["activityId"]
        activity = db_session.query(Activity).filter_by(id=activity_id).one()
        # Stored as UTC — 07:00 IST = 01:30 UTC
        assert activity.recorded_at == "2026-08-13T01:30:00Z"

    def test_activity_date_derived_in_ist(self, client, db_session):
        """activity_date is the IST calendar date of the activity."""
        user = _make_user(db_session)
        # 07:00 IST on 2026-08-13 → activity_date = 2026-08-13
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "running",
            "distanceKm": 5.0,
            "recordedAt": "2026-08-13T07:00:00+05:30",
        })
        assert resp.status_code == 201
        activity_id = resp.json()["activityId"]
        activity = db_session.query(Activity).filter_by(id=activity_id).one()
        assert activity.activity_date == "2026-08-13"

    def test_ist_boundary_utc_1830_is_next_ist_day(self, client, db_session):
        """
        UTC 18:30 on Aug 13 = IST 00:00 Aug 14.
        activity_date must be 2026-08-14, not 2026-08-13.
        """
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "running",
            "distanceKm": 3.0,
            "recordedAt": "2026-08-13T18:30:00+00:00",
        })
        assert resp.status_code == 201
        activity_id = resp.json()["activityId"]
        activity = db_session.query(Activity).filter_by(id=activity_id).one()
        assert activity.activity_date == "2026-08-14"

    def test_ist_boundary_utc_1829_is_same_ist_day(self, client, db_session):
        """
        UTC 18:29 on Aug 13 = IST 23:59 Aug 13.
        activity_date must be 2026-08-13.
        """
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "running",
            "distanceKm": 3.0,
            "recordedAt": "2026-08-13T18:29:00+00:00",
        })
        assert resp.status_code == 201
        activity_id = resp.json()["activityId"]
        activity = db_session.query(Activity).filter_by(id=activity_id).one()
        assert activity.activity_date == "2026-08-13"

    def test_points_are_server_computed_not_client_value(self, client, db_session):
        """Points in the response come from compute_points(), not the client."""
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "walking",
            "distanceKm": 1.55,
            "recordedAt": "2026-08-13T07:00:00+05:30",
        })
        assert resp.status_code == 201
        assert resp.json()["points"] == 77  # floor(1.55 * 50)


# ── 16–20. Daily Steps upsert semantics ───────────────────────────────────────

class TestDailyStepsUpsert:
    def test_first_submission_inserts_row(self, client, db_session):
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "daily_steps",
            "stepCount": 5000,
            "recordedAt": "2026-08-13",
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["points"] == 50
        assert "updated" not in body or body.get("updated") is not True

        count = (
            db_session.query(Activity)
            .filter_by(user_id=user.id, sport_type="daily_steps")
            .count()
        )
        assert count == 1

    def test_second_submission_same_ist_date_updates_row(self, client, db_session):
        """Second submission for the same IST date → 200 with updated=true."""
        user = _make_user(db_session)
        # First
        r1 = _post_activity(client, {
            "userId": user.id,
            "sportType": "daily_steps",
            "stepCount": 5000,
            "recordedAt": "2026-08-13",
        })
        assert r1.status_code == 201

        # Second — same IST date
        r2 = _post_activity(client, {
            "userId": user.id,
            "sportType": "daily_steps",
            "stepCount": 9000,
            "recordedAt": "2026-08-13",
        })
        assert r2.status_code == 200
        body = r2.json()
        assert body["updated"] is True
        assert body["points"] == 90  # floor(9000/100)

    def test_no_duplicate_row_after_second_submission(self, client, db_session):
        """Only one daily_steps row exists after two submissions on the same date."""
        user = _make_user(db_session)
        _post_activity(client, {
            "userId": user.id,
            "sportType": "daily_steps",
            "stepCount": 5000,
            "recordedAt": "2026-08-13",
        })
        _post_activity(client, {
            "userId": user.id,
            "sportType": "daily_steps",
            "stepCount": 9000,
            "recordedAt": "2026-08-13",
        })
        count = (
            db_session.query(Activity)
            .filter_by(
                user_id=user.id,
                sport_type="daily_steps",
                activity_date="2026-08-13",
            )
            .count()
        )
        assert count == 1

    def test_update_replaces_count_not_adds(self, client, db_session):
        """
        Daily Steps are cumulative totals — second submission replaces, not adds.
        Stored step_count after update must equal the second submission value.
        """
        user = _make_user(db_session)
        _post_activity(client, {
            "userId": user.id,
            "sportType": "daily_steps",
            "stepCount": 8342,
            "recordedAt": "2026-08-13",
        })
        _post_activity(client, {
            "userId": user.id,
            "sportType": "daily_steps",
            "stepCount": 9120,
            "recordedAt": "2026-08-13",
        })
        activity = (
            db_session.query(Activity)
            .filter_by(
                user_id=user.id,
                sport_type="daily_steps",
                activity_date="2026-08-13",
            )
            .one()
        )
        # Must be 9120 (replacement), not 8342+9120=17462 (accumulation)
        assert activity.step_count == 9120

    def test_points_recomputed_after_update(self, client, db_session):
        """Points are recomputed from the new step count after an update."""
        user = _make_user(db_session)
        _post_activity(client, {
            "userId": user.id,
            "sportType": "daily_steps",
            "stepCount": 8342,
            "recordedAt": "2026-08-13",
        })
        r2 = _post_activity(client, {
            "userId": user.id,
            "sportType": "daily_steps",
            "stepCount": 9120,
            "recordedAt": "2026-08-13",
        })
        assert r2.json()["points"] == 91  # floor(9120/100)

        activity = (
            db_session.query(Activity)
            .filter_by(
                user_id=user.id,
                sport_type="daily_steps",
                activity_date="2026-08-13",
            )
            .one()
        )
        assert activity.points == 91

    def test_second_submission_different_date_inserts_new_row(self, client, db_session):
        """A second daily_steps submission for a different IST date inserts a new row."""
        user = _make_user(db_session)
        _post_activity(client, {
            "userId": user.id,
            "sportType": "daily_steps",
            "stepCount": 5000,
            "recordedAt": "2026-08-13",
        })
        r2 = _post_activity(client, {
            "userId": user.id,
            "sportType": "daily_steps",
            "stepCount": 7000,
            "recordedAt": "2026-08-14",
        })
        assert r2.status_code == 201
        assert "updated" not in r2.json() or r2.json().get("updated") is not True

        count = (
            db_session.query(Activity)
            .filter_by(user_id=user.id, sport_type="daily_steps")
            .count()
        )
        assert count == 2

    def test_daily_steps_no_recorded_at_uses_current_ist_date(self, client, db_session):
        """
        When recordedAt is omitted for daily_steps, the current IST date is used.
        The row must exist and activity_date must be a valid date string.
        """
        from datetime import datetime
        from zoneinfo import ZoneInfo

        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "daily_steps",
            "stepCount": 3000,
            # recordedAt deliberately omitted
        })
        assert resp.status_code == 201
        activity_id = resp.json()["activityId"]
        activity = db_session.query(Activity).filter_by(id=activity_id).one()

        expected_date = datetime.now(tz=ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
        assert activity.activity_date == expected_date


# ── 21. durationSec=0 edge case ───────────────────────────────────────────────

class TestDurationEdgeCases:
    def test_duration_zero_is_accepted_with_zero_points(self, client, db_session):
        """durationSec=0 is valid at the API boundary (SRS §8 ≥ 0 rule)."""
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "gym",
            "durationSec": 0,
            "recordedAt": "2026-08-13T07:00:00+05:30",
        })
        assert resp.status_code == 201
        assert resp.json()["points"] == 0


# ── 22–25. Additional edge-case validation ─────────────────────────────────────

class TestAdditionalEdgeCases:
    def test_invalid_recorded_at_returns_400_not_500(self, client, db_session):
        """
        A malformed recordedAt string passes Pydantic (typed as Optional[str])
        but must be caught by the service and returned as 400 VALIDATION_ERROR,
        never as a 500 Internal Server Error.
        """
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "running",
            "distanceKm": 5.0,
            "recordedAt": "not-a-valid-timestamp",
        })
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"] == "VALIDATION_ERROR"

    def test_negative_duration_sec_returns_400(self, client, db_session):
        """durationSec must be ≥ 0; a negative value must return 400."""
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "gym",
            "durationSec": -1,
            "recordedAt": "2026-08-13T07:00:00+05:30",
        })
        assert resp.status_code == 400
        assert resp.json()["error"] == "VALIDATION_ERROR"

    def test_negative_step_count_returns_400(self, client, db_session):
        """stepCount must be ≥ 0; a negative value must return 400."""
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "daily_steps",
            "stepCount": -1,
            "recordedAt": "2026-08-13",
        })
        assert resp.status_code == 400
        assert resp.json()["error"] == "VALIDATION_ERROR"

    def test_client_supplied_activity_date_rejected(self, client, db_session):
        """
        activityDate is a server-derived field.  A client supplying it as an
        extra field must be rejected by extra='forbid' with 400 VALIDATION_ERROR.
        """
        user = _make_user(db_session)
        resp = _post_activity(client, {
            "userId": user.id,
            "sportType": "running",
            "distanceKm": 5.0,
            "recordedAt": "2026-08-13T07:00:00+05:30",
            "activityDate": "2026-08-13",
        })
        assert resp.status_code == 400
        assert resp.json()["error"] == "VALIDATION_ERROR"
