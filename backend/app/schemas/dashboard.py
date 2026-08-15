"""
Pydantic response schemas for the dashboard endpoint.

Covers:
    GET /api/users/{id}/dashboard  (SRS §8, FR-14, US-7)

volumeOverTime is grouped by stored activity_date (IST calendar day).
sportBreakdown maps sport_type → total points for that sport.
Empty-activity case → 200 with totalPoints=0, empty arrays, empty dict.
"""

from pydantic import BaseModel, Field


class ActivityHistoryItem(BaseModel):
    """Single item in the activityHistory list."""

    activity_id: int = Field(..., alias="activityId")
    sport_type: str = Field(..., alias="sportType")
    points: int
    recorded_at: str = Field(..., alias="recordedAt")

    model_config = {"populate_by_name": True}


class VolumeOverTimeItem(BaseModel):
    """Single item in the volumeOverTime list."""

    date: str
    points: int


class DashboardResponse(BaseModel):
    """
    Full dashboard response.

    Shape:
    {
        totalPoints: int,
        activityHistory: [ActivityHistoryItem, ...],
        volumeOverTime:  [VolumeOverTimeItem, ...],
        sportBreakdown:  {sport_type: points, ...}
    }
    """

    total_points: int = Field(..., alias="totalPoints")
    activity_history: list[ActivityHistoryItem] = Field(..., alias="activityHistory")
    volume_over_time: list[VolumeOverTimeItem] = Field(..., alias="volumeOverTime")
    sport_breakdown: dict[str, int] = Field(..., alias="sportBreakdown")

    model_config = {"populate_by_name": True}
