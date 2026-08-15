"""
Activity service — ingestion, validation, daily_steps upsert.

Responsibilities:
    - Validate sport/metric pairing and value bounds (business layer, SRS R7).
    - Generate recorded_at as the current UTC instant (server-side only, SRS R11).
    - Compute activity_date by converting recorded_at UTC → IST calendar date
      using zoneinfo.ZoneInfo(settings.timezone).
      IMPORTANT: activity_date is ALWAYS computed here in Python.
                 SQL timezone expressions must never be used for this (SRS §2.3, R12).
    - Call scoring.compute_points() to derive points.
    - For daily_steps: if a row already exists for (user_id, activity_date),
      update step_count and recompute points (SRS FR-10, US-5).
      Handle concurrent inserts via the UNIQUE index + IntegrityError fallback.
    - Persist the activity row atomically (SRS §3 — transactions for atomic ops).
"""

from sqlalchemy.orm import Session

# TODO: implement log_activity()
