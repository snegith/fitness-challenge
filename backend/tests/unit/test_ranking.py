"""
Unit tests for leaderboard ranking and rank-trend logic.

Coverage required by SRS §11.2:
    - Tie-break: two users with identical totalPoints → ordered by created_at ASC,
      then userId ASC.
    - rankTrend = previousSnapshotRank − currentLiveRank (positive = improved).
    - rankTrend = None when no prior snapshot exists for the user.
"""

import pytest


class TestTieBreaking:
    def test_tie_broken_by_created_at(self):
        """Earlier-registered user ranks higher when points are equal."""
        pytest.skip("not yet implemented")

    def test_tie_broken_by_user_id_when_created_at_equal(self):
        pytest.skip("not yet implemented")


class TestRankTrend:
    def test_positive_trend_when_rank_improved(self):
        """previousRank=3, currentRank=1 → rankTrend=2"""
        pytest.skip("not yet implemented")

    def test_negative_trend_when_rank_dropped(self):
        """previousRank=1, currentRank=3 → rankTrend=-2"""
        pytest.skip("not yet implemented")

    def test_null_when_no_prior_snapshot(self):
        pytest.skip("not yet implemented")
