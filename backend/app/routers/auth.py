"""
Auth router — public endpoints.

Routes:
    POST /api/auth/register   – SRS FR-1, FR-2, FR-3
    POST /api/auth/login      – SRS FR-4

No authentication dependency is applied to these routes.

Security posture (SRS §2.3, NFR-6):
    This is basic session-token identification, NOT credential-based authentication.
    Anyone who submits a matching first/last name can obtain a valid token.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.auth import AuthRequest, AuthResponse
from app.services.auth_service import (
    UserAlreadyExistsError,
    UserNotFoundError,
    login_user,
    register_user,
)

router = APIRouter()


@router.post("/register", status_code=201)
async def register(payload: AuthRequest, db: Session = Depends(get_db)):
    """
    Register a new user by first + last name.

    Success  → 201 {userId, firstName, lastName, token}
    Conflict → 409 USER_ALREADY_EXISTS
    Bad input→ 400 VALIDATION_ERROR (handled by FastAPI/Pydantic)
    """
    try:
        result = register_user(db, payload.first_name, payload.last_name)
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "USER_ALREADY_EXISTS",
                "message": "A user with this name is already registered.",
            },
        )

    return AuthResponse(
        userId=result["user_id"],
        firstName=result["first_name"],
        lastName=result["last_name"],
        token=result["token"],
    )


@router.post("/login", status_code=200)
async def login(payload: AuthRequest, db: Session = Depends(get_db)):
    """
    Issue a fresh token for an existing user.

    Success      → 200 {userId, firstName, lastName, token}
    Not found    → 404 USER_NOT_FOUND
    Bad input    → 400 VALIDATION_ERROR (handled by FastAPI/Pydantic)
    """
    try:
        result = login_user(db, payload.first_name, payload.last_name)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "USER_NOT_FOUND",
                "message": "No user matches this name.",
            },
        )

    return AuthResponse(
        userId=result["user_id"],
        firstName=result["first_name"],
        lastName=result["last_name"],
        token=result["token"],
    )
