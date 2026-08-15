"""
Dashboard service — per-user aggregation.

Responsibilities:
    - totalPoints: SUM(points) for all of the user's activities.
    - activityHistory: all activity rows for the user, ordered by recorded_at DESC.
    - volumeOverTime: points grouped by activity_date (IST calendar day), sparse,
      ordered by date ASC.  Uses the stored activity_date column directly —
      no per-query UTC→IST conversion.
    - sportBreakdown: SUM(points) GROUP BY sport_type.

Empty-activity case returns zeros and empty collections — never raises 404
(SRS US-7).
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import Activity


def get_dashboard(db: Session, user_id: int) -> dict:
    """
    Aggregate and return dashboard data for a single user.

    Returns a dict with keys:
        total_points: int
        activity_history: list[dict]
        volume_over_time: list[dict]
        sport_breakdown: dict[str, int]

    Returns zero/empty values if the user has no activities.
    """
    # ── totalPoints ────────────────────────────────────────────────────────────
    total_points = (
        db.query(func.coalesce(func.sum(Activity.points), 0))
        .filter(Activity.user_id == user_id)
        .scalar()
    )

    # ── activityHistory — all activities, most recent first ────────────────────
    activities = (
        db.query(Activity)
        .filter(Activity.user_id == user_id)
        .order_by(Activity.recorded_at.desc())
        .all()
    )

    activity_history = [
        {
            "activity_id": a.id,
            "sport_type": a.sport_type,
            "points": a.points,
            "recorded_at": a.recorded_at,
        }
        for a in activities
    ]

    # ── volumeOverTime — sparse, grouped by activity_date, date ASC ────────────
    volume_rows = (
        db.query(
            Activity.activity_date,
            func.sum(Activity.points).label("points"),
        )
        .filter(Activity.user_id == user_id)
        .group_by(Activity.activity_date)
        .order_by(Activity.activity_date.asc())
        .all()
    )

    volume_over_time = [
        {"date": row.activity_date, "points": row.points}
        for row in volume_rows
    ]

    # ── sportBreakdown — points by sport ───────────────────────────────────────
    breakdown_rows = (
        db.query(
            Activity.sport_type,
            func.sum(Activity.points).label("points"),
        )
        .filter(Activity.user_id == user_id)
        .group_by(Activity.sport_type)
        .all()
    )

    sport_breakdown = {row.sport_type: row.points for row in breakdown_rows}

    return {
        "total_points": total_points,
        "activity_history": activity_history,
        "volume_over_time": volume_over_time,
        "sport_breakdown": sport_breakdown,
    }
