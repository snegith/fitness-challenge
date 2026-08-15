"""
Activity service — ingestion, IST date derivation, daily_steps upsert.

Responsibilities:
    - Validate user existence (404 if not found).
    - Generate recorded_at as the current UTC instant (server-side only, SRS R11).
    - Derive activity_date by converting recorded_at UTC → IST calendar date via
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

recordedAt is ALWAYS server-generated (SRS §2.3, §8, R11):
    The client never supplies this value.  It is the current UTC instant at the
    moment of write.  activity_date is derived from this timestamp via IST.
"""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Activity, User
from app.services.scoring import compute_points

_IST = ZoneInfo(settings.timezone)  # Asia/Kolkata


# ── Helpers ────────────────────────────────────────────────────────────────────


def _now_utc() -> datetime:
    """Return the current UTC instant (timezone-aware)."""
    return datetime.now(tz=timezone.utc)  # noqa: UP017


def _derive_activity_date(utc_dt: datetime) -> str:
    """
    Derive the IST calendar date string 'YYYY-MM-DD' from a UTC datetime.

    This is the SINGLE place where the UTC→IST conversion happens for
    activity_date.  SQL expressions must never be used for this (SRS §2.3, R12).
    """
    ist_dt = utc_dt.astimezone(_IST)
    return ist_dt.strftime("%Y-%m-%d")


def _to_utc_iso(dt: datetime) -> str:
    """Return an ISO 8601 UTC string for storage in recorded_at."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Public API ─────────────────────────────────────────────────────────────────


class UserNotFoundError(Exception):
    """Raised when the referenced userId does not exist."""


def log_activity(
    db: Session,
    user_id: int,
    sport_type: str,
    distance_km: float | None,
    duration_sec: int | None,
    step_count: int | None,
) -> dict:
    """
    Validate, score, and persist a fitness activity.

    recorded_at is ALWAYS server-generated (current UTC instant) — the client
    never supplies it (SRS §8, R11).

    Args:
        db:           SQLAlchemy session.
        user_id:      ID of the activity owner (from verified Bearer token).
        sport_type:   One of the six sports defined in the SRS.
        distance_km:  Set for distance sports; None otherwise.
        duration_sec: Set for duration sports; None otherwise.
        step_count:   Set for daily_steps; None otherwise.

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

    # ── 2. Generate server-side recorded_at (SRS R11 — never client-supplied) ──
    now = _now_utc()
    recorded_at_utc_str = _to_utc_iso(now)

    # ── 3. Derive activity_date in IST (Python only — never SQL) ───────────────
    activity_date = _derive_activity_date(now)

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
    db.flush()
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
        db.flush()
        activity_id = activity.id
        db.commit()
    except IntegrityError:
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
