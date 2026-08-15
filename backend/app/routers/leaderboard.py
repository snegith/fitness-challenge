"""
Leaderboard router — public endpoint.

Routes:
    GET /api/leaderboard  – SRS FR-11, FR-13

No authentication dependency is applied to this route (SRS US-6).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.leaderboard import LeaderboardEntry
from app.services.leaderboard_service import get_live_leaderboard

router = APIRouter()


@router.get("/leaderboard", status_code=200, response_model=list[LeaderboardEntry])
async def get_leaderboard(db: Session = Depends(get_db)):
    """
    Return the live global leaderboard with rank-trend values.

    Always returns 200.  Returns an empty list when no users exist.

    Response shape: [{rank, userId, name, totalPoints, rankTrend}, ...]
    rankTrend = previousSnapshotRank − currentLiveRank  (null if no prior snapshot)
    """
    results = get_live_leaderboard(db)
    return [
        LeaderboardEntry(
            rank=r["rank"],
            userId=r["user_id"],
            name=r["name"],
            totalPoints=r["total_points"],
            rankTrend=r["rank_trend"],
        )
        for r in results
    ]
