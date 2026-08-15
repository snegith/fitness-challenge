"""
Pydantic request/response schemas for the activity endpoint.

Covers:
    POST /api/activities  (SRS §8)

Important constraints captured here:
    - recordedAt is NEVER accepted from the client — it must not appear as an
      accepted request field.  Any client-supplied recordedAt, userId, or
      activity_date must be rejected with 400 (SRS §8, R11).
    - sportType drives which metric field is valid; the others must be absent.
    - userId is not a request field — it is derived from the Bearer token.
"""

from pydantic import BaseModel


# ── Request ───────────────────────────────────────────────────────────────────

class ActivityRequest(BaseModel):
    """
    Request body for POST /api/activities.

    Valid combinations (SRS §8):
        distance sports  → sportType + distanceKm (number > 0)
        duration sports  → sportType + durationSec (int ≥ 0)
        daily_steps      → sportType + stepCount   (int ≥ 0)

    Any extra field (recordedAt, userId, activityDate, …) → 400.
    """
    # TODO: add sportType, distanceKm, durationSec, stepCount with
    #       mutual-exclusion validation
    pass


# ── Responses ─────────────────────────────────────────────────────────────────

class ActivityResponse(BaseModel):
    """
    Success response for a new activity (201) or a daily_steps upsert (200).

    Shape: {activityId, sportType, points, recordedAt[, updated]}
    recordedAt is server-generated UTC — never echoed from the request.
    """
    # TODO: add fields
    pass
