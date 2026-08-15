"""
Scoring engine — pure, independently testable.

This module has ZERO imports from app.db, app.routers, or any HTTP/ORM layer.
It must remain that way (SRS NFR-4).

Public API:
    compute_points(sport_type: str, metric_value: float | int) -> int

Conversion table (SRS §9.1):
    running      km   → floor(km  * 100)
    walking      km   → floor(km  *  50)
    cycling      km   → floor(km  *  25)
    swimming     sec  → floor(sec / 60) * 15
    gym          sec  → floor(sec / 60) *  5
    daily_steps  count→ floor(count / 100)

Flooring rule (SRS §9.1):
    All results are integer-floored, never rounded.
    Zero-value inputs return 0, not an error.

Unit tests live in tests/unit/test_scoring.py.
"""

# TODO: implement compute_points()
