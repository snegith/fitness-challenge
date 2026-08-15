"""
Pydantic request/response schemas for the activity endpoint.

Covers:
    POST /api/activities  (SRS FR-6, FR-7, FR-8, FR-9, FR-10)

TEMPORARY DEVIATION — userId in request body:
    The finalized SRS (FR-5, §8) requires userId to be derived from the
    session/Bearer token, never accepted from the request body.

    For this development unit only, userId is accepted in the request body
    because session-token authentication is deferred to a later unit.

    The authentication unit MUST:
        1. Remove userId from this schema.
        2. Require Bearer token on POST /api/activities.
        3. Derive userId exclusively from the verified token.
        4. Update all relevant tests.

Metric field validation (SRS §8):
    distance sports  → distanceKm required (> 0), durationSec/stepCount absent
    duration sports  → durationSec required (≥ 0), distanceKm/stepCount absent
    daily_steps      → stepCount required (≥ 0), distanceKm/durationSec absent

Extra fields (points, activityDate, …) → rejected by model_config extra='forbid'.

Alias style note:
    Fields use the standard Pydantic v2 `field: type = Field(..., alias="...")` form.
    Using `Annotated[type, Field(alias=...)]` triggers an UnsupportedFieldAttributeWarning
    in Pydantic v2.12 because the alias metadata inside Annotated is treated as
    annotation-level (not field-level) in certain schema-build code paths.
    The plain assignment form is idiomatic, warning-free, and behaviorally identical.
    NOTE: The warning still fires at runtime via FastAPI's internal schema resolution
    (fastapi/_compat.py wraps fields as Annotated[type, FieldInfo] when building
    the request body TypeAdapter). This is a FastAPI 0.115.5 + Pydantic 2.12
    incompatibility and cannot be eliminated without changing either library version.
    See completion report for full analysis.
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

    TEMPORARY: userId accepted from body until auth unit is implemented.

    Valid sport/metric combinations (SRS §8):
        running/walking/cycling  → distanceKm (float > 0)
        swimming/gym             → durationSec (int ≥ 0)
        daily_steps              → stepCount (int ≥ 0), recordedAt optional

    recordedAt is accepted from the client for this unit and represents when
    the activity occurred.  For daily_steps it is optional; if omitted the
    service layer uses the current IST date.

    Points must NOT be supplied by the client — extra='forbid' ensures any
    attempt to pass 'points' returns 400 (SRS §7, project rule §4).
    """

    # TEMPORARY — remove when auth unit is implemented (see module docstring)
    user_id: int = Field(..., alias="userId")

    sport_type: str = Field(..., alias="sportType")

    # Metric fields — exactly one must be present for the given sport
    distance_km: float | None = Field(None, alias="distanceKm")
    duration_sec: int | None = Field(None, alias="durationSec")
    step_count: int | None = Field(None, alias="stepCount")

    # recordedAt — client-supplied timestamp (when the activity occurred).
    # For daily_steps this is optional; for all other sports it is required
    # (validated in the cross-field validator below).
    recorded_at: str | None = Field(None, alias="recordedAt")

    model_config = {
        "populate_by_name": True,
        # Reject any extra fields (including client-supplied 'points') → 400
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

        # 2. Enforce exactly the right metric field for the sport; reject the wrong ones
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
            if self.recorded_at is None:
                raise ValueError(
                    f"recordedAt is required for sportType '{sport}'."
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
            if self.recorded_at is None:
                raise ValueError(
                    f"recordedAt is required for sportType '{sport}'."
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
            # recordedAt is optional for daily_steps

        return self


# ── Responses ─────────────────────────────────────────────────────────────────

class ActivityResponse(BaseModel):
    """
    Success response for a newly created activity (201).

    Shape: {activityId, sportType, points, recordedAt}
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
    """

    activity_id: int = Field(..., alias="activityId")
    sport_type: str = Field(..., alias="sportType")
    points: int
    recorded_at: str = Field(..., alias="recordedAt")
    updated: bool = True

    model_config = {"populate_by_name": True}
