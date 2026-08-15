"""
FastAPI dependency functions.

Current dependencies:
    get_current_user_id  – resolves the Bearer token in the Authorization header
                           to a verified userId.  Applied only to protected routes
                           (activity ingestion, dashboard).  Public routes
                           (register, login, leaderboard) do NOT use this dependency.

Authentication is optional scope (SRS §1.2, §2.3).  This module is a placeholder
until the optional auth feature is implemented.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Placeholder — implementation deferred to the optional auth feature
_bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> int:
    """
    Verify the Bearer token and return the authenticated userId (int).

    Raises HTTP 401 if the token is missing, malformed, expired, or references
    a userId that no longer exists.

    NOTE: userId is NEVER accepted from the request body — it is always derived
    from the verified token (SRS FR-5).
    """
    # TODO: implement JWT verification (HS256) and userId extraction
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": "UNAUTHORIZED", "message": "Missing or invalid session token."},
        headers={"WWW-Authenticate": "Bearer"},
    )
