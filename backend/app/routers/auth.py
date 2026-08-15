"""
Auth router — public endpoints.

Routes:
    POST /api/auth/register   – SRS FR-1, FR-2, FR-3
    POST /api/auth/login      – SRS FR-4

No authentication dependency is applied to these routes.
"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/register", status_code=201)
async def register():
    """
    Register a new user by first + last name.

    Success  → 201 {userId, firstName, lastName, token}
    Conflict → 409 USER_ALREADY_EXISTS
    Bad input→ 400 VALIDATION_ERROR
    """
    # TODO: implement — delegate to auth_service.register_user()
    raise NotImplementedError


@router.post("/login", status_code=200)
async def login():
    """
    Issue a fresh token for an existing user.

    Success      → 200 {userId, firstName, lastName, token}
    Not found    → 404 USER_NOT_FOUND
    Bad input    → 400 VALIDATION_ERROR
    """
    # TODO: implement — delegate to auth_service.login_user()
    raise NotImplementedError
