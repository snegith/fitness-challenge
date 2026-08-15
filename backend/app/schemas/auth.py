"""
Pydantic request/response schemas for auth endpoints.

Covers:
    POST /api/auth/register  (SRS §8)
    POST /api/auth/login     (SRS §8)

Security posture (SRS §2.3, NFR-6):
    This is basic session-token identification, NOT credential-based authentication.
    Anyone who knows a matching first/last name can obtain a valid token.
"""

from pydantic import BaseModel, Field, field_validator

# ── Requests ──────────────────────────────────────────────────────────────────


class AuthRequest(BaseModel):
    """
    Shared request body for both register and login.

    Shape: {firstName, lastName}
    Both fields are required non-empty strings.
    """

    first_name: str = Field(..., alias="firstName")
    last_name: str = Field(..., alias="lastName")

    model_config = {"populate_by_name": True, "extra": "forbid"}

    @field_validator("first_name", "last_name")
    @classmethod
    def must_be_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field must be a non-empty string.")
        return v


# ── Responses ─────────────────────────────────────────────────────────────────


class AuthResponse(BaseModel):
    """
    Shared success response for both register (201) and login (200).

    Shape: {userId, firstName, lastName, token}
    """

    user_id: int = Field(..., alias="userId")
    first_name: str = Field(..., alias="firstName")
    last_name: str = Field(..., alias="lastName")
    token: str

    model_config = {"populate_by_name": True}
