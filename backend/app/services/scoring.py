"""
Scoring engine — pure, independently testable.

This module has ZERO imports from app.db, app.routers, or any HTTP/ORM layer.
It must remain that way (SRS NFR-4).

Public API:
    compute_points(sport_type: str, metric_value: float | int) -> int

Conversion table (SRS §9.1):
    running      km    → floor(km * 100)
    walking      km    → floor(km * 50)
    cycling      km    → floor(km * 25)
    swimming     sec   → floor(sec / 60) * 15
    gym          sec   → floor(sec / 60) * 5
    daily_steps  count → floor(count / 100)

Flooring rule (SRS §9.1):
    All results are integer-floored, never rounded.
    Zero-value inputs return 0, not an error.

There is ONE source of truth for the conversion logic: _CONVERSION_TABLE below.
No other module should duplicate these rates.

Unit tests live in tests/unit/test_scoring.py.
"""

import math

# ── Single source of truth for conversion rates ────────────────────────────────
#
# sport_type → (rate, divisor, floor_first)
#
# floor_first=False  (distance/steps):  points = floor(metric * rate / divisor)
#     e.g. running:      floor(km * 100 / 1)    = floor(km * 100)
#     e.g. daily_steps:  floor(steps * 1 / 100) = floor(steps / 100)
#
# floor_first=True   (duration sports): points = floor(metric / divisor) * rate
#     This floors to whole minutes BEFORE multiplying, matching the SRS §9.1
#     wording "floor(sec / 60) * rate".
#     e.g. swimming: floor(sec / 60) * 15
#     e.g. gym:      floor(sec / 60) * 5
#
# Using floor_first=True for duration sports is intentional and different from
# floor(sec * rate / divisor), which would give the same answer only when
# rate is a multiple of divisor.

_RATES: dict[str, tuple[int, int, bool]] = {
    # sport          rate  divisor  floor_first
    "running":      (100,  1,       False),
    "walking":      (50,   1,       False),
    "cycling":      (25,   1,       False),
    "swimming":     (15,   60,      True),
    "gym":          (5,    60,      True),
    "daily_steps":  (1,    100,     False),
}


def compute_points(sport_type: str, metric_value: float | int) -> int:
    """
    Compute integer points for a given sport and raw metric value.

    Args:
        sport_type:   One of the six supported sport strings.
        metric_value: km for distance sports, seconds for duration sports,
                      step count for daily_steps.

    Returns:
        Non-negative integer points, always floored (never rounded).

    Raises:
        ValueError: if sport_type is not one of the six known sports.

    This function has no database or HTTP dependency and is directly
    unit-testable (SRS NFR-4).
    """
    if sport_type not in _RATES:
        raise ValueError(
            f"Unknown sport_type '{sport_type}'. "
            f"Valid values: {list(_RATES.keys())}"
        )

    rate, divisor, floor_first = _RATES[sport_type]

    if floor_first:
        # Duration sports: floor(sec / 60) * rate  — floor BEFORE multiplying
        return math.floor(metric_value / divisor) * rate
    else:
        # Distance/steps: floor(km * rate)  or  floor(steps / 100)
        return math.floor(metric_value * rate / divisor)
