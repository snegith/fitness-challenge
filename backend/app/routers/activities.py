"""
Activities router.

Routes:
    POST /api/activities  — SRS FR-6 through FR-10

TEMPORARY DEVIATION (this development unit only):
    userId is accepted from the request body because session-token
    authentication is deferred to a later development unit.

    When the authentication unit is implemented:
        - Remove userId from ActivityRequest.
        - Add `Depends(get_current_user_id)` to this endpoint.
        - Derive user_id from the verified token only.
        - Update all relevant tests.

See schemas/activity.py for the full follow-up requirement.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.database import get_db
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
    db: Session = Depends(get_db),
):
    """
    Log a new fitness activity or upsert today's daily_steps record.

    Success (new activity) → 201 {activityId, sportType, points, recordedAt}
    Success (steps upsert) → 200 {activityId, sportType, points, recordedAt, updated: true}
    Unknown userId         → 404 USER_NOT_FOUND
    Bad payload            → 400 VALIDATION_ERROR  (handled by FastAPI/Pydantic)
    Bad recordedAt format  → 400 VALIDATION_ERROR  (caught from service ValueError)

    TEMPORARY: userId from request body (auth deferred — see module docstring).
    """
    try:
        result = log_activity(
            db=db,
            user_id=payload.user_id,
            sport_type=payload.sport_type,
            recorded_at_str=payload.recorded_at,
            distance_km=payload.distance_km,
            duration_sec=payload.duration_sec,
            step_count=payload.step_count,
        )
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "USER_NOT_FOUND", "message": "No user found with this userId."},
        )
    except ValueError as exc:
        # Covers malformed recordedAt that passes Pydantic (typed as Optional[str])
        # but is rejected by _parse_recorded_at() in the service layer.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "VALIDATION_ERROR", "message": str(exc)},
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
