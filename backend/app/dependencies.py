"""
FastAPI dependency functions.

Current dependencies:
    get_current_user_id  – resolves the Bearer token in the Authorization header
                           to a verified userId.  Applied only to protected routes
                           (activity ingestion, dashboard).  Public routes
                           (register, login, leaderboard) do NOT use this dependency.

Security posture (SRS §2.3, NFR-6):
    This is basic session-token identification, NOT credential-based authentication.
    The dependency verifies the JWT signature and expiry, then derives the userId.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.services.auth_service import verify_token

# auto_error=False so we can control the 401 message format ourselves.
# If auto_error=True, FastAPI returns {"detail": "Not authenticated"} which
# doesn't match the project error envelope.
_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> int:
    """
    Verify the Bearer token and return the authenticated userId (int).

    Raises HTTP 401 if the token is missing, malformed, expired, or references
    a userId that no longer exists.

    NOTE: userId is NEVER accepted from the request body — it is always derived
    from the verified token (SRS FR-5).
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORIZED", "message": "Missing or invalid session token."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = verify_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORIZED", "message": "Missing or invalid session token."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify the user still exists in the database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORIZED", "message": "Missing or invalid session token."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id
