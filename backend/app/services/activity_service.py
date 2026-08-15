"""
Activity service — ingestion, IST date derivation, daily_steps upsert.

Responsibilities:
    - Validate user existence (404 if not found).
    - Parse and normalise the client-supplied recordedAt timestamp.
    - Derive activity_date by converting recordedAt → IST calendar date via
      zoneinfo.  This is the ONLY place activity_date is computed.
      SQL timezone expressions must never be used (SRS §2.3, R12).
    - Call scoring.compute_points() to derive points.
    - For daily_steps:
        * Look up whether a row already exists for (user_id, activity_date).
        * If found → UPDATE step_count and recompute points (SRS FR-10).
        * If not found → INSERT a new row.
        * The UNIQUE partial index idx_daily_steps_unique is the database-level
          guard; IntegrityError on a concurrent race is handled as an upsert
          fallback.
    - Persist non-steps activities as new rows.
    - Return a typed result dict that the router converts to the HTTP response.

TEMPORARY DEVIATION:
    userId is currently supplied by the caller (from the request body) because
    session-token authentication is deferred.  When the auth unit is implemented
    this argument must be replaced by identity derived from the verified token.
    See schemas/activity.py for the full follow-up requirement.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Activity, User
from app.services.scoring import compute_points

_IST = ZoneInfo(settings.timezone)  # Asia/Kolkata


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_recorded_at(recorded_at_str: str) -> datetime:
    """
    Parse a client-supplied recordedAt string into an aware datetime.

    Accepts ISO 8601 strings, including:
        2026-08-13T07:00:00+05:30    (explicit offset)
        2026-08-13T07:00:00Z          (UTC shorthand)
        2026-08-13T07:00:00+00:00
        2026-08-13                    (date-only — interpreted as midnight IST)

    Returns a timezone-aware datetime.  Raises ValueError for malformed input.
    """
    s = recorded_at_str.strip()

    # Date-only format: 'YYYY-MM-DD'
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        # Interpret as midnight IST on that date
        naive = datetime.strptime(s, "%Y-%m-%d")
        return naive.replace(tzinfo=_IST)

    # Replace trailing Z with +00:00 for fromisoformat compatibility
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        raise ValueError(f"recordedAt '{recorded_at_str}' is not a valid ISO 8601 datetime.")

    if dt.tzinfo is None:
        raise ValueError(
            f"recordedAt '{recorded_at_str}' has no timezone offset. "
            "Provide an explicit offset (e.g. +05:30 or Z)."
        )

    return dt


def _derive_activity_date(recorded_at_dt: datetime) -> str:
    """
    Derive the IST calendar date string 'YYYY-MM-DD' from an aware datetime.

    This is the SINGLE place where the UTC→IST conversion happens for
    activity_date.  SQL expressions must never be used for this (SRS §2.3, R12).
    """
    ist_dt = recorded_at_dt.astimezone(_IST)
    return ist_dt.strftime("%Y-%m-%d")


def _to_utc_iso(dt: datetime) -> str:
    """Return an ISO 8601 UTC string for storage in recorded_at."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: UP017


# ── Public API ─────────────────────────────────────────────────────────────────

class UserNotFoundError(Exception):
    """Raised when the referenced userId does not exist."""


def log_activity(
    db: Session,
    user_id: int,
    sport_type: str,
    recorded_at_str: str | None,
    distance_km: float | None,
    duration_sec: int | None,
    step_count: int | None,
) -> dict:
    """
    Validate, score, and persist a fitness activity.

    Args:
        db:             SQLAlchemy session.
        user_id:        ID of the activity owner (TEMPORARY: from request body).
        sport_type:     One of the six sports defined in the SRS.
        recorded_at_str: Client-supplied ISO 8601 timestamp (when activity occurred).
                         For daily_steps this may be None → current IST date used.
        distance_km:    Set for distance sports; None otherwise.
        duration_sec:   Set for duration sports; None otherwise.
        step_count:     Set for daily_steps; None otherwise.

    Returns:
        dict with keys: activity_id, sport_type, points, recorded_at,
        and optionally updated=True for daily_steps upsert.

    Raises:
        UserNotFoundError: if user_id does not reference an existing user.
    """
    # ── 1. User existence check ────────────────────────────────────────────────
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise UserNotFoundError(f"No user found with userId={user_id}.")

    # ── 2. Determine recorded_at datetime ─────────────────────────────────────
    if recorded_at_str is not None:
        recorded_at_dt = _parse_recorded_at(recorded_at_str)
    else:
        # daily_steps with no recordedAt → current IST date, midnight IST
        now_ist = datetime.now(tz=_IST)
        recorded_at_dt = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)

    recorded_at_utc_str = _to_utc_iso(recorded_at_dt)

    # ── 3. Derive activity_date in IST (Python only — never SQL) ───────────────
    activity_date = _derive_activity_date(recorded_at_dt)

    # ── 4. Determine metric type and raw metric value for scoring ─────────────
    if distance_km is not None:
        metric_type = "distance"
        metric_value: float | int = distance_km
    elif duration_sec is not None:
        metric_type = "duration"
        metric_value = duration_sec
    else:
        metric_type = "count"
        metric_value = step_count  # type: ignore[assignment]

    # ── 5. Compute points (pure function — no DB/HTTP) ────────────────────────
    points = compute_points(sport_type, metric_value)

    # ── 6. Persist ────────────────────────────────────────────────────────────
    if sport_type == "daily_steps":
        return _upsert_daily_steps(
            db=db,
            user_id=user_id,
            activity_date=activity_date,
            step_count=step_count,  # type: ignore[arg-type]
            points=points,
            recorded_at_utc_str=recorded_at_utc_str,
        )
    else:
        return _insert_activity(
            db=db,
            user_id=user_id,
            sport_type=sport_type,
            metric_type=metric_type,
            distance_km=distance_km,
            duration_sec=duration_sec,
            step_count=None,
            points=points,
            recorded_at_utc_str=recorded_at_utc_str,
            activity_date=activity_date,
        )


def _insert_activity(
    db: Session,
    user_id: int,
    sport_type: str,
    metric_type: str,
    distance_km: float | None,
    duration_sec: int | None,
    step_count: int | None,
    points: int,
    recorded_at_utc_str: str,
    activity_date: str,
) -> dict:
    """Insert a new activity row and return the response dict."""
    activity = Activity(
        user_id=user_id,
        sport_type=sport_type,
        metric_type=metric_type,
        distance_km=distance_km,
        duration_sec=duration_sec,
        step_count=step_count,
        points=points,
        recorded_at=recorded_at_utc_str,
        activity_date=activity_date,
    )
    db.add(activity)
    db.flush()   # populates activity.id before commit
    activity_id = activity.id
    db.commit()

    return {
        "activity_id": activity_id,
        "sport_type": sport_type,
        "points": points,
        "recorded_at": recorded_at_utc_str,
    }


def _upsert_daily_steps(
    db: Session,
    user_id: int,
    activity_date: str,
    step_count: int,
    points: int,
    recorded_at_utc_str: str,
) -> dict:
    """
    Upsert the daily_steps row for (user_id, activity_date).

    Implementation strategy (SRS FR-10, project rules §3):
        1. Attempt to find an existing row.
        2. If found → UPDATE step_count and recompute points in place.
        3. If not found → INSERT a new row.
        4. If a concurrent INSERT races past the lookup and hits the UNIQUE
           constraint → catch IntegrityError, rollback, then UPDATE instead.

    The database UNIQUE partial index idx_daily_steps_unique is the final
    safety guarantee.  The application-level lookup is the normal path.

    Daily Steps replace (not accumulate):
        The client submits the cumulative daily total.
        We replace the stored value — we do NOT add old + new (SRS FR-10, R6).
    """
    existing = (
        db.query(Activity)
        .filter(
            Activity.user_id == user_id,
            Activity.activity_date == activity_date,
            Activity.sport_type == "daily_steps",
        )
        .first()
    )

    if existing is not None:
        # UPDATE in place — replace cumulative total and recompute points
        existing.step_count = step_count
        existing.points = points
        existing.recorded_at = recorded_at_utc_str
        existing_id = existing.id
        db.flush()
        db.commit()
        return {
            "activity_id": existing_id,
            "sport_type": "daily_steps",
            "points": points,
            "recorded_at": recorded_at_utc_str,
            "updated": True,
        }

    # No existing row — attempt INSERT
    activity = Activity(
        user_id=user_id,
        sport_type="daily_steps",
        metric_type="count",
        distance_km=None,
        duration_sec=None,
        step_count=step_count,
        points=points,
        recorded_at=recorded_at_utc_str,
        activity_date=activity_date,
    )
    db.add(activity)

    try:
        db.flush()   # populate activity.id
        activity_id = activity.id
        db.commit()
    except IntegrityError:
        # Concurrent race: another request inserted the row between our SELECT
        # and our INSERT.  Roll back and fall through to an UPDATE.
        db.rollback()
        existing = (
            db.query(Activity)
            .filter(
                Activity.user_id == user_id,
                Activity.activity_date == activity_date,
                Activity.sport_type == "daily_steps",
            )
            .one()
        )
        existing.step_count = step_count
        existing.points = points
        existing.recorded_at = recorded_at_utc_str
        existing_id = existing.id
        db.flush()
        db.commit()
        return {
            "activity_id": existing_id,
            "sport_type": "daily_steps",
            "points": points,
            "recorded_at": recorded_at_utc_str,
            "updated": True,
        }

    return {
        "activity_id": activity_id,
        "sport_type": "daily_steps",
        "points": points,
        "recorded_at": recorded_at_utc_str,
    }
