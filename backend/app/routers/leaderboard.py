"""
Leaderboard router — public endpoint.

Routes:
    GET /api/leaderboard  – SRS FR-11, FR-13

No authentication dependency is applied to this route (SRS US-6).
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/leaderboard", status_code=200)
async def get_leaderboard():
    """
    Return the live global leaderboard with rank-trend values.

    Always returns 200.  Returns an empty list when no users exist.

    Response shape: [{rank, userId, name, totalPoints, rankTrend}, ...]
    rankTrend = previousSnapshotRank − currentLiveRank  (null if no prior snapshot)
    """
    # TODO: implement — delegate to leaderboard_service.get_live_leaderboard()
    return []
