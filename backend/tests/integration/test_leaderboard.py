"""
Integration tests — live leaderboard.

Coverage (SRS §11.5 leaderboard portion):
    - Multiple users with different points → correct descending order.
    - Tie-break: equal points → earlier created_at ranks higher.
    - Tie-break: equal points + equal created_at → lower userId ranks higher.
    - rankTrend correctly reflects a seeded prior-day snapshot.
    - rankTrend is null for a user with no prior snapshot.
    - Empty leaderboard → 200 with empty array.
    - Endpoint requires no authentication (public).
"""

import pytest


class TestLeaderboardOrdering:
    def test_ordered_by_total_points_descending(self, client):
        pytest.skip("not yet implemented")

    def test_tie_broken_by_created_at(self, client):
        pytest.skip("not yet implemented")

    def test_tie_broken_by_user_id(self, client):
        pytest.skip("not yet implemented")


class TestRankTrend:
    def test_rank_trend_with_prior_snapshot(self, client):
        pytest.skip("not yet implemented")

    def test_rank_trend_null_without_prior_snapshot(self, client):
        pytest.skip("not yet implemented")


class TestEdgeCases:
    def test_empty_leaderboard_returns_200_empty_array(self, client):
        pytest.skip("not yet implemented")

    def test_no_auth_required(self, client):
        pytest.skip("not yet implemented")
