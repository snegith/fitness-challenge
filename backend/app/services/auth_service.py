"""
Auth service — registration, login, token issuance and verification.

Responsibilities:
    - Normalize first + last name into a name_key for deduplication.
    - Register a new user (insert into users, issue JWT).
    - Log in an existing user by name_key lookup (issue fresh JWT).
    - Sign and verify HS256 JWTs using settings.jwt_secret.

Security posture (SRS §2.3, NFR-6):
    This is basic session-token identification, NOT credential-based authentication.
    No credential or password is verified at any point.
    Anyone who knows a matching first/last name can obtain a valid token.
    Tokens identify the user; they do not authenticate them.

Token shape: {userId: int, exp: UTC timestamp}
Algorithm: HS256
Expiry: settings.jwt_expire_hours (default 24 h, SRS R10)
"""

import re
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import User

_ALGORITHM = "HS256"


# ── Name normalization ─────────────────────────────────────────────────────────


def _normalize_name_key(first_name: str, last_name: str) -> str:
    """
    Produce the canonical name_key for deduplication.

    Normalization:
        - strip leading/trailing whitespace
        - collapse internal whitespace to single space
        - lowercase
        - join with '|'

    This matches the SRS §7 name_key definition:
        lower(trim(first)) || '|' || lower(trim(last)), whitespace-collapsed
    """
    first = re.sub(r"\s+", " ", first_name.strip()).lower()
    last = re.sub(r"\s+", " ", last_name.strip()).lower()
    return f"{first}|{last}"


# ── Token operations ───────────────────────────────────────────────────────────


def create_token(user_id: int) -> str:
    """
    Issue a signed JWT containing the user's identity.

    Payload: {userId: int, exp: UTC datetime}
    Algorithm: HS256
    Expiry: settings.jwt_expire_hours (default 24h)
    """
    expire = datetime.now(tz=UTC) + timedelta(hours=settings.jwt_expire_hours)
    payload = {"userId": user_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def verify_token(token: str) -> int:
    """
    Verify a JWT and extract the userId.

    Returns:
        The integer userId from the token payload.

    Raises:
        ValueError: if the token is invalid, expired, malformed, or missing userId.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except JWTError as exc:
        raise ValueError(f"Token verification failed: {exc}") from exc

    user_id = payload.get("userId")
    if user_id is None:
        raise ValueError("Token missing required 'userId' claim.")

    return int(user_id)


# ── Registration ───────────────────────────────────────────────────────────────


class UserAlreadyExistsError(Exception):
    """Raised when a user with the same normalized name already exists."""


def register_user(db: Session, first_name: str, last_name: str) -> dict:
    """
    Register a new user and issue a token.

    Args:
        db: SQLAlchemy session.
        first_name: Raw first name from the client.
        last_name: Raw last name from the client.

    Returns:
        dict with keys: user_id, first_name, last_name, token

    Raises:
        UserAlreadyExistsError: if a user with the same name_key already exists.
    """
    name_key = _normalize_name_key(first_name, last_name)

    # Use stripped (but case-preserving) names for storage
    stored_first = re.sub(r"\s+", " ", first_name.strip())
    stored_last = re.sub(r"\s+", " ", last_name.strip())

    user = User(
        first_name=stored_first,
        last_name=stored_last,
        name_key=name_key,
    )
    db.add(user)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise UserAlreadyExistsError("A user with this name is already registered.")

    user_id = user.id
    db.commit()

    token = create_token(user_id)

    return {
        "user_id": user_id,
        "first_name": stored_first,
        "last_name": stored_last,
        "token": token,
    }


# ── Login ──────────────────────────────────────────────────────────────────────


class UserNotFoundError(Exception):
    """Raised when no user matches the supplied name."""


def login_user(db: Session, first_name: str, last_name: str) -> dict:
    """
    Look up an existing user by name and issue a fresh token.

    Args:
        db: SQLAlchemy session.
        first_name: Raw first name from the client.
        last_name: Raw last name from the client.

    Returns:
        dict with keys: user_id, first_name, last_name, token

    Raises:
        UserNotFoundError: if no user matches the normalized name.
    """
    name_key = _normalize_name_key(first_name, last_name)
    user = db.query(User).filter(User.name_key == name_key).first()

    if user is None:
        raise UserNotFoundError("No user matches this name.")

    token = create_token(user.id)

    return {
        "user_id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "token": token,
    }
