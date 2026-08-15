"""
Pydantic response schemas for the dashboard endpoint.

Covers:
    GET /api/users/{id}/dashboard  (SRS §8)

volumeOverTime is grouped by stored activity_date (IST calendar day).
sportBreakdown maps sport_type → total points for that sport.
Empty-activity case → 200 with totalPoints=0, empty arrays, empty dict.
"""

from pydantic import BaseModel


class ActivityHistoryItem(BaseModel):
    """Single item in the activityHistory list."""
    # TODO: add activityId, sportType, points, recordedAt
    pass


class VolumeOverTimeItem(BaseModel):
    """Single item in the volumeOverTime list."""
    # TODO: add date (str, YYYY-MM-DD), points (int)
    pass


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
    # TODO: add fields
    pass
