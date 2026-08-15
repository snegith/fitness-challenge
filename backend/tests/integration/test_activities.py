"""
Integration tests — activity ingestion.

Coverage (SRS §11.4):
    - Valid payload for each of the 6 sports → correct points, 201 response.
    - recordedAt in response is server-generated UTC, not echoed from request body.
    - Client-supplied recordedAt in request body is rejected/ignored (not used).
    - Mismatched sport/metric field → 400 VALIDATION_ERROR.
    - Extra forbidden fields (userId, activityDate) in request → 400.
    - Second daily_steps submission for the same IST activity_date:
        - Existing row is updated, not duplicated.
        - SELECT COUNT(*) confirms exactly one row.
        - Points are recalculated from new step count.
    - daily_steps submission that falls on a new IST activity_date → new row inserted.
    - durationSec=55 (under 60) → 0 points, not an error.
"""

import pytest


class TestDistanceActivities:
    def test_running_correct_points(self, client):
        pytest.skip("not yet implemented")

    def test_walking_correct_points(self, client):
        pytest.skip("not yet implemented")

    def test_cycling_correct_points(self, client):
        pytest.skip("not yet implemented")


class TestDurationActivities:
    def test_swimming_correct_points(self, client):
        pytest.skip("not yet implemented")

    def test_gym_correct_points(self, client):
        pytest.skip("not yet implemented")

    def test_sub_60s_gym_returns_zero_points(self, client):
        pytest.skip("not yet implemented")


class TestDailySteps:
    def test_first_submission_inserts_row(self, client):
        pytest.skip("not yet implemented")

    def test_second_submission_same_ist_date_updates_row(self, client):
        pytest.skip("not yet implemented")

    def test_second_submission_different_ist_date_inserts_new_row(self, client):
        pytest.skip("not yet implemented")


class TestValidation:
    def test_mismatched_metric_field_returns_400(self, client):
        pytest.skip("not yet implemented")

    def test_client_supplied_recorded_at_is_rejected(self, client):
        pytest.skip("not yet implemented")

    def test_recorded_at_in_response_is_server_generated(self, client):
        pytest.skip("not yet implemented")
