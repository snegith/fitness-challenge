"""
Pydantic response schemas for the leaderboard endpoint.

Covers:
    GET /api/leaderboard  (SRS §8)

rankTrend semantics (SRS §9.3):
    rankTrend = mostRecentSnapshotRank − currentLiveRank
    Positive  → user improved.
    Negative  → user dropped.
    None/null → no prior snapshot exists for this user.
"""

from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    """Single entry in the leaderboard response array."""
    # TODO: add rank, userId, name, totalPoints, rankTrend (Optional[int])
    pass


# The endpoint returns a list[LeaderboardEntry] directly — no wrapper object.
