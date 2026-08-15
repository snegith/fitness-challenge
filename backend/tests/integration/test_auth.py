"""
Integration tests — auth endpoints and token enforcement.

Coverage (SRS §11.3):
    Registration:
        - Valid registration → 201, userId, token
        - Token from registration authenticates the user
        - Duplicate normalized name → 409 USER_ALREADY_EXISTS
        - Empty/missing firstName → 400 VALIDATION_ERROR
        - Empty/missing lastName → 400 VALIDATION_ERROR

    Login:
        - Existing user → 200, correct userId, fresh token
        - Name normalization consistent with registration
        - Unknown user → 404 USER_NOT_FOUND

    Token verification:
        - Valid token allows access to protected endpoint
        - Missing Authorization header → 401
        - Malformed Authorization header → 401
        - Malformed token → 401
        - Invalid signature → 401
        - Expired token → 401
        - Token for nonexistent user → 401

    Dashboard ownership:
        - Own dashboard → success
        - Other user's dashboard → 403 FORBIDDEN
        - Missing token on dashboard → 401

    Public endpoints:
        - Registration is public
        - Login is public
        - Leaderboard is public
"""

from datetime import UTC, datetime, timedelta

from jose import jwt

from app.config import settings

# ── Helpers ────────────────────────────────────────────────────────────────────


def _register(client, first="Ada", last="Lovelace"):
    return client.post("/api/auth/register", json={
        "firstName": first,
        "lastName": last,
    })


def _login(client, first="Ada", last="Lovelace"):
    return client.post("/api/auth/login", json={
        "firstName": first,
        "lastName": last,
    })


def _make_token(user_id, *, secret=None, expire_hours=24, algorithm="HS256"):
    """Create a valid JWT for testing."""
    secret = secret or settings.jwt_secret
    payload = {
        "userId": user_id,
        "exp": datetime.now(tz=UTC) + timedelta(hours=expire_hours),
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def _expired_token(user_id):
    """Create an expired JWT."""
    payload = {
        "userId": user_id,
        "exp": datetime.now(tz=UTC) - timedelta(hours=1),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


# ── Registration ───────────────────────────────────────────────────────────────


class TestRegister:
    def test_successful_registration(self, client, db_session):
        resp = _register(client, "Ada", "Lovelace")
        assert resp.status_code == 201
        body = resp.json()
        assert "userId" in body
        assert body["firstName"] == "Ada"
        assert body["lastName"] == "Lovelace"
        assert "token" in body
        assert len(body["token"]) > 0

    def test_token_authenticates_user(self, client, db_session):
        """Token from registration can be used on a protected endpoint."""
        resp = _register(client, "Ada", "Lovelace")
        token = resp.json()["token"]
        # Use token on activity endpoint
        act_resp = client.post("/api/activities", json={
            "sportType": "running",
            "distanceKm": 5.0,
        }, headers={"Authorization": f"Bearer {token}"})
        assert act_resp.status_code == 201

    def test_duplicate_name_returns_409(self, client, db_session):
        _register(client, "Ada", "Lovelace")
        resp = _register(client, "Ada", "Lovelace")
        assert resp.status_code == 409
        assert resp.json()["error"] == "USER_ALREADY_EXISTS"

    def test_duplicate_case_insensitive_returns_409(self, client, db_session):
        """Name normalization: 'ada lovelace' == 'ADA LOVELACE'."""
        _register(client, "Ada", "Lovelace")
        resp = _register(client, "ADA", "LOVELACE")
        assert resp.status_code == 409
        assert resp.json()["error"] == "USER_ALREADY_EXISTS"

    def test_missing_first_name_returns_400(self, client, db_session):
        resp = client.post("/api/auth/register", json={
            "lastName": "Lovelace",
        })
        assert resp.status_code == 400
        assert resp.json()["error"] == "VALIDATION_ERROR"

    def test_missing_last_name_returns_400(self, client, db_session):
        resp = client.post("/api/auth/register", json={
            "firstName": "Ada",
        })
        assert resp.status_code == 400
        assert resp.json()["error"] == "VALIDATION_ERROR"

    def test_empty_first_name_returns_400(self, client, db_session):
        resp = client.post("/api/auth/register", json={
            "firstName": "   ",
            "lastName": "Lovelace",
        })
        assert resp.status_code == 400
        assert resp.json()["error"] == "VALIDATION_ERROR"

    def test_empty_last_name_returns_400(self, client, db_session):
        resp = client.post("/api/auth/register", json={
            "firstName": "Ada",
            "lastName": "",
        })
        assert resp.status_code == 400
        assert resp.json()["error"] == "VALIDATION_ERROR"


# ── Login ──────────────────────────────────────────────────────────────────────


class TestLogin:
    def test_existing_user_returns_token(self, client, db_session):
        reg = _register(client, "Ada", "Lovelace")
        user_id = reg.json()["userId"]

        resp = _login(client, "Ada", "Lovelace")
        assert resp.status_code == 200
        body = resp.json()
        assert body["userId"] == user_id
        assert "token" in body
        assert body["firstName"] == "Ada"
        assert body["lastName"] == "Lovelace"

    def test_login_token_identifies_correct_user(self, client, db_session):
        """Token from login can authenticate the correct user."""
        _register(client, "Ada", "Lovelace")
        resp = _login(client, "Ada", "Lovelace")
        token = resp.json()["token"]

        # Use it on activity endpoint
        act_resp = client.post("/api/activities", json={
            "sportType": "running",
            "distanceKm": 1.0,
        }, headers={"Authorization": f"Bearer {token}"})
        assert act_resp.status_code == 201

    def test_name_normalization_consistent(self, client, db_session):
        """Login with different casing finds the same user."""
        _register(client, "Ada", "Lovelace")
        resp = _login(client, "ada", "lovelace")
        assert resp.status_code == 200

    def test_unknown_user_returns_404(self, client, db_session):
        resp = _login(client, "Nobody", "Here")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"] == "USER_NOT_FOUND"
        assert body["message"] == "No user matches this name."


# ── Token verification ─────────────────────────────────────────────────────────


class TestTokenVerification:
    def test_valid_token_succeeds(self, client, db_session):
        resp = _register(client, "Ada", "Lovelace")
        token = resp.json()["token"]
        act_resp = client.post("/api/activities", json={
            "sportType": "running",
            "distanceKm": 5.0,
        }, headers={"Authorization": f"Bearer {token}"})
        assert act_resp.status_code == 201

    def test_missing_auth_header_returns_401(self, client, db_session):
        resp = client.post("/api/activities", json={
            "sportType": "running",
            "distanceKm": 5.0,
        })
        assert resp.status_code == 401
        assert resp.json()["error"] == "UNAUTHORIZED"

    def test_malformed_auth_header_returns_401(self, client, db_session):
        resp = client.post("/api/activities", json={
            "sportType": "running",
            "distanceKm": 5.0,
        }, headers={"Authorization": "NotBearer abc"})
        assert resp.status_code == 401

    def test_malformed_token_returns_401(self, client, db_session):
        resp = client.post("/api/activities", json={
            "sportType": "running",
            "distanceKm": 5.0,
        }, headers={"Authorization": "Bearer not.a.jwt"})
        assert resp.status_code == 401

    def test_invalid_signature_returns_401(self, client, db_session):
        _register(client, "Ada", "Lovelace")
        # Sign with a different secret
        bad_token = _make_token(1, secret="wrong-secret-key")
        resp = client.post("/api/activities", json={
            "sportType": "running",
            "distanceKm": 5.0,
        }, headers={"Authorization": f"Bearer {bad_token}"})
        assert resp.status_code == 401

    def test_expired_token_returns_401(self, client, db_session):
        reg = _register(client, "Ada", "Lovelace")
        user_id = reg.json()["userId"]
        token = _expired_token(user_id)
        resp = client.post("/api/activities", json={
            "sportType": "running",
            "distanceKm": 5.0,
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_token_for_nonexistent_user_returns_401(self, client, db_session):
        """Token referencing a userId that doesn't exist → 401."""
        token = _make_token(99999)
        resp = client.post("/api/activities", json={
            "sportType": "running",
            "distanceKm": 5.0,
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_token_missing_user_id_claim_returns_401(self, client, db_session):
        """Token without userId claim → 401."""
        payload = {"exp": datetime.now(tz=UTC) + timedelta(hours=24)}
        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        resp = client.post("/api/activities", json={
            "sportType": "running",
            "distanceKm": 5.0,
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


# ── Dashboard ownership ────────────────────────────────────────────────────────


class TestDashboardOwnership:
    def test_own_dashboard_auth_and_ownership_pass(self, client, db_session):
        """
        Valid token accessing own dashboard passes auth + ownership check.
        Dashboard returns 200 with empty data for a user with no activities.
        """
        resp = _register(client, "Ada", "Lovelace")
        user_id = resp.json()["userId"]
        token = resp.json()["token"]

        dash = client.get(
            f"/api/users/{user_id}/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert dash.status_code == 200
        assert dash.json()["totalPoints"] == 0

    def test_other_user_dashboard_returns_403(self, client, db_session):
        r1 = _register(client, "Ada", "Lovelace")
        r2 = _register(client, "Grace", "Hopper")
        token_ada = r1.json()["token"]
        user_id_grace = r2.json()["userId"]

        dash = client.get(
            f"/api/users/{user_id_grace}/dashboard",
            headers={"Authorization": f"Bearer {token_ada}"},
        )
        assert dash.status_code == 403
        assert dash.json()["error"] == "FORBIDDEN"

    def test_missing_token_on_dashboard_returns_401(self, client, db_session):
        resp = _register(client, "Ada", "Lovelace")
        user_id = resp.json()["userId"]
        dash = client.get(f"/api/users/{user_id}/dashboard")
        assert dash.status_code == 401


# ── Public endpoints ───────────────────────────────────────────────────────────


class TestPublicEndpoints:
    def test_register_is_public(self, client, db_session):
        """Registration does not require a token."""
        resp = _register(client, "Ada", "Lovelace")
        assert resp.status_code == 201

    def test_login_is_public(self, client, db_session):
        """Login does not require a token."""
        _register(client, "Ada", "Lovelace")
        resp = _login(client, "Ada", "Lovelace")
        assert resp.status_code == 200

    def test_leaderboard_is_public(self, client, db_session):
        """Leaderboard does not require a token."""
        resp = client.get("/api/leaderboard")
        # May return NotImplementedError or empty list depending on state,
        # but must NOT return 401
        assert resp.status_code != 401
