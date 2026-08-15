"""
Dashboard router.

Routes:
    GET /api/users/{id}/dashboard  – SRS FR-14, FR-15

Protected: requires a valid Bearer token whose userId matches the path {id}.
Returning data for a different userId is forbidden (SRS FR-15, US-7).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies import get_current_user_id
from app.schemas.dashboard import (
    ActivityHistoryItem,
    DashboardResponse,
    VolumeOverTimeItem,
)
from app.services.dashboard_service import get_dashboard

router = APIRouter()


@router.get("/users/{user_id}/dashboard", status_code=200)
async def get_user_dashboard(
    user_id: int,
    authenticated_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Return the personal dashboard for the authenticated user.

    Success          → 200 {totalPoints, activityHistory, volumeOverTime, sportBreakdown}
    Token mismatch   → 403 FORBIDDEN
    Bad/missing token→ 401 UNAUTHORIZED

    Empty-activity case returns 200 with zeros/empty collections — never 404.
    """
    # Ownership check: token's userId must equal the path userId
    if authenticated_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "FORBIDDEN",
                "message": "Cannot access another user's dashboard.",
            },
        )

    result = get_dashboard(db, user_id)

    return DashboardResponse(
        totalPoints=result["total_points"],
        activityHistory=[
            ActivityHistoryItem(
                activityId=item["activity_id"],
                sportType=item["sport_type"],
                points=item["points"],
                recordedAt=item["recorded_at"],
            )
            for item in result["activity_history"]
        ],
        volumeOverTime=[
            VolumeOverTimeItem(date=item["date"], points=item["points"])
            for item in result["volume_over_time"]
        ],
        sportBreakdown=result["sport_breakdown"],
    )
