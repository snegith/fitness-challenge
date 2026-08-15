"""
Activities router.

Routes:
    POST /api/activities  — SRS FR-6 through FR-10

Protected: requires a valid Bearer token.
userId is derived from the verified token — never from the request body (SRS FR-5).
recordedAt is server-generated — never from the client (SRS §8, R11).
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies import get_current_user_id
from app.schemas.activity import (
    ActivityRequest,
    ActivityResponse,
    ActivityUpsertResponse,
)
from app.services.activity_service import UserNotFoundError, log_activity

router = APIRouter()


@router.post("/activities")
async def post_activity(
    payload: ActivityRequest,
    response: Response,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Log a new fitness activity or upsert today's daily_steps record.

    Success (new activity) → 201 {activityId, sportType, points, recordedAt}
    Success (steps upsert) → 200 {activityId, sportType, points, recordedAt, updated: true}
    Bad payload            → 400 VALIDATION_ERROR
    Missing/bad token      → 401 UNAUTHORIZED

    recordedAt in the response is always server-generated (current UTC instant).
    """
    try:
        result = log_activity(
            db=db,
            user_id=user_id,
            sport_type=payload.sport_type,
            distance_km=payload.distance_km,
            duration_sec=payload.duration_sec,
            step_count=payload.step_count,
        )
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "USER_NOT_FOUND", "message": "No user found with this userId."},
        )

    if result.get("updated"):
        response.status_code = status.HTTP_200_OK
        return ActivityUpsertResponse(
            activityId=result["activity_id"],
            sportType=result["sport_type"],
            points=result["points"],
            recordedAt=result["recorded_at"],
            updated=True,
        )

    response.status_code = status.HTTP_201_CREATED
    return ActivityResponse(
        activityId=result["activity_id"],
        sportType=result["sport_type"],
        points=result["points"],
        recordedAt=result["recorded_at"],
    )
