"""
Integration tests — auth endpoints.

Coverage (SRS §11.3):
    - Register → receive token → token authorises a protected request.
    - Register duplicate name → 409 USER_ALREADY_EXISTS.
    - Register empty/missing name → 400 VALIDATION_ERROR.
    - Login matching name → 200 with correct userId and a fresh token.
    - Login non-matching name → 404 USER_NOT_FOUND.
    - Protected endpoint with missing token → 401.
    - Protected endpoint with expired/malformed token → 401.
    - Dashboard request where token's userId ≠ path {id} → 403.
"""

import pytest


class TestRegister:
    def test_successful_registration(self, client):
        pytest.skip("not yet implemented")

    def test_duplicate_name_returns_409(self, client):
        pytest.skip("not yet implemented")

    def test_missing_name_returns_400(self, client):
        pytest.skip("not yet implemented")


class TestLogin:
    def test_existing_user_returns_token(self, client):
        pytest.skip("not yet implemented")

    def test_unknown_user_returns_404(self, client):
        pytest.skip("not yet implemented")


class TestTokenEnforcement:
    def test_missing_token_returns_401(self, client):
        pytest.skip("not yet implemented")

    def test_malformed_token_returns_401(self, client):
        pytest.skip("not yet implemented")

    def test_wrong_user_dashboard_returns_403(self, client):
        pytest.skip("not yet implemented")
