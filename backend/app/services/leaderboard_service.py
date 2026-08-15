"""
Leaderboard service — live leaderboard and rank-trend computation.

Responsibilities:
    - Aggregate SUM(points) GROUP BY user_id from the activities table (live,
      never cached — SRS NFR-1).
    - Apply deterministic tie-breaking: totalPoints DESC, created_at ASC, userId ASC
      (SRS §9.2).
    - For each user, look up their rank in the most recent leaderboard_entries row
      to compute rankTrend = previousSnapshotRank − currentLiveRank (SRS §9.3).
    - Return None/null for rankTrend when no prior snapshot exists for that user.

This service does NOT generate snapshots — that is snapshot_service's job.
"""

# TODO: implement get_live_leaderboard()
