"""
Pydantic request/response schemas for the activity endpoint.

Covers:
    POST /api/activities  (SRS FR-6, FR-7, FR-8, FR-9, FR-10)

userId is derived from the Bearer token via the authentication dependency.
It is NOT accepted from the request body (SRS FR-5).

recordedAt is ALWAYS server-generated (SRS §2.3, §8, R11).
It is NOT accepted from the client.  Any client-supplied recordedAt is rejected
with 400 via extra='forbid'.

Metric field validation (SRS §8):
    distance sports  → distanceKm required (> 0), durationSec/stepCount absent
    duration sports  → durationSec required (≥ 0), distanceKm/stepCount absent
    daily_steps      → stepCount required (≥ 0), distanceKm/durationSec absent

Extra fields (points, userId, recordedAt, activityDate, …) → rejected by
model_config extra='forbid'.
"""

from typing import Self

from pydantic import BaseModel, Field, model_validator

# ── Constants ──────────────────────────────────────────────────────────────────

DISTANCE_SPORTS = frozenset({"running", "walking", "cycling"})
DURATION_SPORTS = frozenset({"swimming", "gym"})
STEPS_SPORTS = frozenset({"daily_steps"})
ALL_SPORTS = DISTANCE_SPORTS | DURATION_SPORTS | STEPS_SPORTS


# ── Request ───────────────────────────────────────────────────────────────────

class ActivityRequest(BaseModel):
    """
    Request body for POST /api/activities.

    userId is NOT accepted — it comes from the verified Bearer token (SRS FR-5).
    recordedAt is NOT accepted — it is server-generated (SRS §8, R11).

    Valid sport/metric combinations (SRS §8):
        running/walking/cycling  → distanceKm (float > 0)
        swimming/gym             → durationSec (int ≥ 0)
        daily_steps              → stepCount (int ≥ 0)

    extra='forbid' rejects any field not declared here, including:
        points, userId, recordedAt, activityDate, etc.
    """

    sport_type: str = Field(..., alias="sportType")

    # Metric fields — exactly one must be present for the given sport
    distance_km: float | None = Field(None, alias="distanceKm")
    duration_sec: int | None = Field(None, alias="durationSec")
    step_count: int | None = Field(None, alias="stepCount")

    model_config = {
        "populate_by_name": True,
        # Reject ANY extra field (userId, points, recordedAt, activityDate…) → 400
        "extra": "forbid",
    }

    @model_validator(mode="after")
    def validate_sport_metric_combination(self) -> Self:
        sport = self.sport_type

        # 1. sport_type must be one of the six known sports
        if sport not in ALL_SPORTS:
            raise ValueError(
                f"Invalid sportType '{sport}'. "
                f"Must be one of: {sorted(ALL_SPORTS)}."
            )

        # 2. Enforce exactly the right metric field for the sport
        if sport in DISTANCE_SPORTS:
            if self.duration_sec is not None:
                raise ValueError(
                    f"sportType '{sport}' does not accept durationSec."
                )
            if self.step_count is not None:
                raise ValueError(
                    f"sportType '{sport}' does not accept stepCount."
                )
            if self.distance_km is None:
                raise ValueError(
                    f"sportType '{sport}' requires distanceKm (number > 0)."
                )
            if self.distance_km <= 0:
                raise ValueError(
                    f"distanceKm must be > 0 for sportType '{sport}'."
                )

        elif sport in DURATION_SPORTS:
            if self.distance_km is not None:
                raise ValueError(
                    f"sportType '{sport}' does not accept distanceKm."
                )
            if self.step_count is not None:
                raise ValueError(
                    f"sportType '{sport}' does not accept stepCount."
                )
            if self.duration_sec is None:
                raise ValueError(
                    f"sportType '{sport}' requires durationSec (integer ≥ 0)."
                )
            if self.duration_sec < 0:
                raise ValueError(
                    f"durationSec must be ≥ 0 for sportType '{sport}'."
                )

        elif sport in STEPS_SPORTS:
            if self.distance_km is not None:
                raise ValueError(
                    "sportType 'daily_steps' does not accept distanceKm."
                )
            if self.duration_sec is not None:
                raise ValueError(
                    "sportType 'daily_steps' does not accept durationSec."
                )
            if self.step_count is None:
                raise ValueError(
                    "sportType 'daily_steps' requires stepCount (integer ≥ 0)."
                )
            if self.step_count < 0:
                raise ValueError(
                    "stepCount must be ≥ 0 for sportType 'daily_steps'."
                )

        return self


# ── Responses ─────────────────────────────────────────────────────────────────

class ActivityResponse(BaseModel):
    """
    Success response for a newly created activity (201).

    Shape: {activityId, sportType, points, recordedAt}
    recordedAt is server-generated UTC — never echoed from the request.
    """

    activity_id: int = Field(..., alias="activityId")
    sport_type: str = Field(..., alias="sportType")
    points: int
    recorded_at: str = Field(..., alias="recordedAt")

    model_config = {"populate_by_name": True}


class ActivityUpsertResponse(BaseModel):
    """
    Success response for a daily_steps update (200).

    Shape: {activityId, sportType, points, recordedAt, updated: true}
    recordedAt is server-generated UTC.
    """

    activity_id: int = Field(..., alias="activityId")
    sport_type: str = Field(..., alias="sportType")
    points: int
    recorded_at: str = Field(..., alias="recordedAt")
    updated: bool = True

    model_config = {"populate_by_name": True}
