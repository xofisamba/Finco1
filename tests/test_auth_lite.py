"""Tests for auth lite — lightweight session-based auth for FincoGPT."""

import os
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")

import pytest
from fastapi.testclient import TestClient
from itsdangerous import URLSafeTimedSerializer

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main_web import app
from app.auth import (
    verify_login, create_session_token, decode_session_token,
    make_session_cookie, clear_session_cookie,
    SessionData, ADMIN_USERNAME, COOKIE_NAME,
)


class TestPasswordHashing:
    def test_verify_login_correct_credentials(self):
        assert verify_login(ADMIN_USERNAME, "fincoGPT2026!") is True

    def test_verify_login_wrong_password(self):
        assert verify_login(ADMIN_USERNAME, "wrong") is False

    def test_verify_login_wrong_username(self):
        assert verify_login("wronguser", "fincoGPT2026!") is False


class TestSessionToken:
    def test_create_and_decode_session_token(self):
        token = create_session_token()
        session = decode_session_token(token)
        assert session is not None
        assert session.user_id == "1"
        assert session.username == ADMIN_USERNAME

    def test_invalid_token_returns_none(self):
        session = decode_session_token("not.a.valid.token")
        assert session is None

    def test_tampered_token_returns_none(self):
        token = create_session_token()
        tampered = token[:-5] + "XXXXX"
        session = decode_session_token(tampered)
        assert session is None

    def test_session_data_is_expired(self):
        from datetime import datetime, timezone, timedelta
        old = datetime.now(timezone.utc) - timedelta(hours=48)
        session = SessionData("1", ADMIN_USERNAME, old)
        assert session.is_expired() is True


class TestCookie:
    def test_make_session_cookie_has_correct_keys(self):
        token = "test-token"
        cookie = make_session_cookie(token)
        assert cookie["key"] == COOKIE_NAME
        assert cookie["value"] == token
        assert cookie["httponly"] is True
        assert cookie["secure"] is True
        assert cookie["samesite"] == "lax"
        assert cookie["path"] == "/"

    def test_clear_cookie_has_zero_max_age(self):
        cookie = clear_session_cookie()
        assert cookie["key"] == COOKIE_NAME
        assert cookie["value"] == ""
        assert cookie["max_age"] == 0


class TestAuthRoutes:
    @pytest.fixture
    def tc(self):
        return TestClient(app)

    @pytest.fixture
    def authenticated_tc(self, tc):
        """TC with valid session cookie."""
        token = create_session_token()
        tc.cookies.set(COOKIE_NAME, token)
        return tc

    # ── GET /public-health (public) ──────────────────────────────────────

    def test_public_health_no_auth_required(self, tc):
        r = tc.get("/public-health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["app"] == "fincogpt"

    # ── GET /login (shows login form) ───────────────────────────────────

    def test_login_page_shows_form(self, tc):
        r = tc.get("/login")
        assert r.status_code == 200
        assert "Sign in" in r.text
        assert 'name="username"' in r.text
        assert 'name="password"' in r.text

    def test_login_page_redirects_authenticated_user(self, authenticated_tc):
        r = authenticated_tc.get("/login", follow_redirects=True)
        assert r.status_code == 200
        assert "Sign in" not in r.text or "FincoGPT" in r.text

    # ── POST /login (valid credentials) ────────────────────────────────

    def test_login_success_sets_cookie(self, tc):
        r = tc.post("/login", data={"username": "admin", "password": "fincoGPT2026!"}, follow_redirects=False)
        assert r.status_code == 302
        assert r.headers.get("location") == "/"
        # Cookie should be set
        assert COOKIE_NAME in dict(tc.cookies)

    def test_login_success_redirects_to_dashboard(self, tc):
        r = tc.post("/login", data={"username": "admin", "password": "fincoGPT2026!"}, follow_redirects=False)
        assert r.status_code == 302
        assert r.headers.get("location") == "/"

    # ── POST /login (invalid credentials) ─────────────────────────────

    def test_login_failure_stays_on_login_page(self, tc):
        r = tc.post("/login", data={"username": "admin", "password": "wrongpassword"})
        assert r.status_code == 401
        assert "Invalid username or password" in r.text

    def test_login_wrong_username_shows_error(self, tc):
        r = tc.post("/login", data={"username": "wrong", "password": "fincoGPT2026!"})
        assert r.status_code == 401
        assert "Invalid username or password" in r.text

    # ── POST /logout ────────────────────────────────────────────────────

    def test_logout_clears_cookie_and_redirects(self, authenticated_tc):
        r = authenticated_tc.post("/logout", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers.get("location") == "/login"
        # Clear cookie should be set
        set_cookie = r.headers.get("set-cookie", "")
        assert COOKIE_NAME in set_cookie
        assert "Max-Age=0" in set_cookie or "max-age=0" in set_cookie.lower()

    # ── Protected routes redirect to /login without auth ──────────────────

    def test_index_without_auth_redirects_to_login(self, tc):
        r = tc.get("/", follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.headers.get("location", "")

    def test_run_without_auth_redirects_to_login(self, tc):
        """POST /run without auth redirects to /login."""
        r = tc.post("/run", data={"project_type": "Solar", "scenario": "Base"}, follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.headers.get("location", "")

    def test_protected_route_with_valid_session_works(self, authenticated_tc):
        r = authenticated_tc.get("/")
        assert r.status_code == 200
        assert "FincoGPT" in r.text

    def test_health_without_auth_returns_401(self, tc):
        r = tc.get("/health")
        assert r.status_code == 401

    def test_health_with_auth_returns_200(self, authenticated_tc):
        r = authenticated_tc.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"