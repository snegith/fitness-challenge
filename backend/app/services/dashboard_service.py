"""
Dashboard service — per-user aggregation.

Responsibilities:
    - totalPoints: SUM(points) for all of the user's activities.
    - activityHistory: all activity rows for the user, ordered by recorded_at DESC.
    - volumeOverTime: points grouped by activity_date (IST calendar day).
      Uses the stored activity_date column directly — no per-query UTC→IST conversion.
    - sportBreakdown: SUM(points) GROUP BY sport_type.

Empty-activity case returns zeros and empty collections — never raises 404
(SRS US-7).
"""

from sqlalchemy.orm import Session

# TODO: implement get_dashboard()
