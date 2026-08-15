"""
Integration tests — dashboard endpoint.

Coverage (SRS §11.3 auth portion for dashboard + US-7):
    - Authenticated user's own dashboard → 200 with correct aggregates.
    - totalPoints == sum of all activity points.
    - sportBreakdown values sum to totalPoints.
    - volumeOverTime groups by activity_date (IST calendar day).
    - Zero-activity user → 200 with totalPoints=0, empty arrays, empty sportBreakdown.
    - Token's userId ≠ path {id} → 403 FORBIDDEN.
    - Missing/invalid token → 401 UNAUTHORIZED.
    - Non-existent userId in path → 404 USER_NOT_FOUND.
"""

import pytest


class TestDashboardAccess:
    def test_own_dashboard_returns_200(self, client):
        pytest.skip("not yet implemented")

    def test_other_user_dashboard_returns_403(self, client):
        pytest.skip("not yet implemented")

    def test_missing_token_returns_401(self, client):
        pytest.skip("not yet implemented")

    def test_nonexistent_user_returns_404(self, client):
        pytest.skip("not yet implemented")


class TestDashboardAggregation:
    def test_total_points_equals_sum_of_activities(self, client):
        pytest.skip("not yet implemented")

    def test_sport_breakdown_sums_to_total(self, client):
        pytest.skip("not yet implemented")

    def test_volume_over_time_grouped_by_activity_date(self, client):
        pytest.skip("not yet implemented")

    def test_zero_activities_returns_empty_dashboard(self, client):
        pytest.skip("not yet implemented")
