"""
Pydantic request/response schemas for auth endpoints.

Covers:
    POST /api/auth/register  (SRS §8)
    POST /api/auth/login     (SRS §8)
"""

from pydantic import BaseModel

# ── Requests ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """Request body for POST /api/auth/register."""
    # TODO: add firstName, lastName fields with validation
    pass


class LoginRequest(BaseModel):
    """Request body for POST /api/auth/login."""
    # TODO: add firstName, lastName fields with validation
    pass


# ── Responses ─────────────────────────────────────────────────────────────────

class AuthResponse(BaseModel):
    """
    Shared success response for both register (201) and login (200).

    Shape: {userId, firstName, lastName, token}
    """
    # TODO: add fields
    pass


class ErrorResponse(BaseModel):
    """Standard error envelope used across all error responses."""
    error: str
    message: str
