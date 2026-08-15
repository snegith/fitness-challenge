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

from pydantic import BaseModel, Field


class LeaderboardEntry(BaseModel):
    """Single entry in the leaderboard response array."""

    rank: int
    user_id: int = Field(..., alias="userId")
    name: str
    total_points: int = Field(..., alias="totalPoints")
    rank_trend: int | None = Field(..., alias="rankTrend")

    model_config = {"populate_by_name": True}


# The endpoint returns list[LeaderboardEntry] directly — no wrapper object.
