"""
Auth service — registration, login, token issuance and verification.

Responsibilities:
    - Normalize first + last name into a name_key for deduplication.
    - Register a new user (insert into users, issue JWT).
    - Log in an existing user by name_key lookup (issue fresh JWT).
    - Sign and verify HS256 JWTs using settings.jwt_secret.

Security note (SRS §2.3, NFR-6):
    This is session-token identification, NOT authentication.
    No credential or password is verified at any point.
    Tokens identify the user; they do not authenticate them.

Token shape: {userId: int, exp: UTC timestamp}
Algorithm: HS256
Expiry: settings.jwt_expire_hours (default 24 h, SRS R10)
"""

# TODO: implement register_user(), login_user(), create_token(), verify_token()
