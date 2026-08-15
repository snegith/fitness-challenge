"""
Activities router.

Routes:
    POST /api/activities  – SRS FR-6 through FR-10

Protected: requires a valid Bearer token.
userId is derived from the token — never from the request body (SRS FR-5).
"""

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user_id

router = APIRouter()


@router.post("/activities", status_code=201)
async def log_activity(user_id: int = Depends(get_current_user_id)):
    """
    Log a new activity or upsert today's daily_steps record.

    Success (new)    → 201 {activityId, sportType, points, recordedAt}
    Success (upsert) → 200 {activityId, sportType, points, recordedAt, updated: true}
    Bad payload      → 400 VALIDATION_ERROR
    Bad token        → 401 UNAUTHORIZED
    """
    # TODO: implement — delegate to activity_service.log_activity()
    raise NotImplementedError
