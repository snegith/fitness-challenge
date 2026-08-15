"""
Leaderboard service — live leaderboard and rank-trend computation.

Responsibilities:
    - Aggregate SUM(points) GROUP BY user_id from the activities table (live,
      never cached — SRS NFR-1).
    - Include ALL registered users via LEFT JOIN, even those with zero activities
      (COALESCE to 0).
    - Apply deterministic tie-breaking: totalPoints DESC, created_at ASC, userId ASC
      (SRS §9.2).
    - For each user, look up their rank in the most recent prior snapshot entry
      to compute rankTrend = previousSnapshotRank − currentLiveRank (SRS §9.3).
    - Return None/null for rankTrend when no prior snapshot exists for that user.

This service does NOT generate snapshots — that is snapshot_service's job.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import Activity, LeaderboardEntry, LeaderboardSnapshot, User


def get_live_leaderboard(db: Session) -> list[dict]:
    """
    Compute and return the live global leaderboard.

    Returns a list of dicts, each with:
        rank, user_id, name, total_points, rank_trend

    Empty list if no users are registered.
    """
    # ── 1. Aggregate total points per user (LEFT JOIN — include zero-activity users)
    point_subq = (
        db.query(
            Activity.user_id,
            func.coalesce(func.sum(Activity.points), 0).label("total_points"),
        )
        .group_by(Activity.user_id)
        .subquery()
    )

    rows = (
        db.query(
            User.id,
            User.first_name,
            User.last_name,
            func.coalesce(point_subq.c.total_points, 0).label("total_points"),
            User.created_at,
        )
        .outerjoin(point_subq, User.id == point_subq.c.user_id)
        .order_by(
            func.coalesce(point_subq.c.total_points, 0).desc(),
            User.created_at.asc(),
            User.id.asc(),
        )
        .all()
    )

    if not rows:
        return []

    # ── 2. Assign sequential ranks
    ranked = []
    for idx, row in enumerate(rows, start=1):
        ranked.append({
            "rank": idx,
            "user_id": row.id,
            "name": f"{row.first_name} {row.last_name}",
            "total_points": row.total_points,
        })

    # ── 3. Look up most recent prior snapshot for rank-trend calculation
    latest_snapshot = (
        db.query(LeaderboardSnapshot)
        .order_by(LeaderboardSnapshot.snapshot_date.desc())
        .first()
    )

    # Build a map: user_id → previous rank from the most recent snapshot
    prev_rank_map: dict[int, int] = {}
    if latest_snapshot is not None:
        entries = (
            db.query(LeaderboardEntry)
            .filter(LeaderboardEntry.snapshot_id == latest_snapshot.id)
            .all()
        )
        for entry in entries:
            prev_rank_map[entry.user_id] = entry.rank

    # ── 4. Compute rankTrend for each user
    for item in ranked:
        prev_rank = prev_rank_map.get(item["user_id"])
        if prev_rank is not None:
            item["rank_trend"] = prev_rank - item["rank"]
        else:
            item["rank_trend"] = None

    return ranked
