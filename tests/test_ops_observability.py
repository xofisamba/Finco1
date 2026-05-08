"""Tests for ops observability — request logging, security headers, exception handling."""
import os
import re
import sys

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
os.environ.setdefault("FINCO_COOKIE_SECURE", "false")
os.environ.setdefault("FINCO_LOG_LEVEL", "DEBUG")

import pytest
from fastapi.testclient import TestClient

# Import main_web after env is set
import main_web


@pytest.fixture
def client():
    """Fresh TestClient for each test."""
    return TestClient(main_web.app, raise_server_exceptions=False)


@pytest.fixture
def auth_client(client):
    """TestClient with valid authenticated session."""
    token = main_web.create_session_token()
    client.cookies.set(main_web.COOKIE_NAME, token)
    return client


class TestSecurityHeaders:
    def test_x_frame_options_deny(self, client):
        r = client.get("/public-health")
        assert "X-Frame-Options" in r.headers
        assert r.headers["X-Frame-Options"] == "DENY"

    def test_x_content_type_options_nosniff(self, client):
        r = client.get("/public-health")
        assert "X-Content-Type-Options" in r.headers
        assert r.headers["X-Content-Type-Options"] == "nosniff"

    def test_referrer_policy_same_origin(self, client):
        r = client.get("/public-health")
        assert "Referrer-Policy" in r.headers
        assert r.headers["Referrer-Policy"] == "same-origin"

    def test_csp_header_present(self, client):
        r = client.get("/public-health")
        assert "Content-Security-Policy" in r.headers

    def test_csp_allows_self_and_inline(self, client):
        r = client.get("/public-health")
        csp = r.headers.get("Content-Security-Policy", "")
        assert "default-src 'self'" in csp
        assert "'unsafe-inline'" in csp  # needed for Jinja2

    def test_csp_blocks_frame_ancestors(self, client):
        r = client.get("/public-health")
        csp = r.headers.get("Content-Security-Policy", "")
        assert "frame-ancestors 'none'" in csp


class TestPublicHealth:
    def test_public_health_returns_ok(self, client):
        r = client.get("/public-health")
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "ok"
        assert "app" in data

    def test_public_health_no_auth_required(self, client):
        r = client.get("/public-health")
        assert r.status_code == 200


class TestAuthRoutesWithMiddleware:
    def test_login_page_works(self, client):
        r = client.get("/login")
        assert r.status_code == 200
        assert "Sign in" in r.text

    def test_login_includes_csrf_token(self, client):
        r = client.get("/login")
        assert 'name="csrf_token"' in r.text

    def test_protected_route_redirects_unauthenticated(self, client):
        r = client.get("/", follow_redirects=False)
        assert r.status_code in (302, 401)

    def test_authenticated_index_works(self, auth_client):
        r = auth_client.get("/")
        assert r.status_code == 200
        assert "FincoGPT" in r.text

    def test_logout_works(self, auth_client):
        r = auth_client.post("/logout", follow_redirects=False)
        assert r.status_code == 302, f"logout should return 302, got {r.status_code}"
        assert r.headers.get("location") == "/login"


class TestExceptionHandling:
    def test_404_does_not_expose_traceback(self, client):
        r = client.get("/nonexistent-path-xyz123")
        assert r.status_code == 404
        assert "Traceback" not in r.text
        assert "File \"/" not in r.text

    def test_404_does_not_expose_stack_trace(self, client):
        r = client.get("/nonexistent")
        # No Python file paths or module names in response
        for bad in ["app/", "main_web", "starlette", "uvicorn"]:
            assert bad not in r.text, f"Expected '{bad}' not in 404 page"


class TestPasswordNotLogged:
    def test_password_not_in_request_logs(self, client, caplog):
        import logging
        caplog.set_level(logging.INFO)

        r = client.get("/login")
        m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text)
        csrf = m.group(1) if m else None

        r = client.post("/login", data={
            "csrf_token": csrf,
            "username": "admin",
            "password": "fincoGPT2026!",
        })

        for record in caplog.records:
            msg = str(record.message)
            assert "fincoGPT2026" not in msg, f"Password found in log: {msg}"

    def test_wrong_password_not_logged(self, caplog):
        import logging
        caplog.set_level(logging.INFO)

        tc = TestClient(main_web.app, raise_server_exceptions=False)
        r = tc.get("/login")
        m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text)
        csrf = m.group(1) if m else None

        r = tc.post("/login", data={
            "csrf_token": csrf,
            "username": "admin",
            "password": "SUPER_SECRET_WRONG_PASSWORD",
        })

        for record in caplog.records:
            msg = str(record.message)
            assert "SUPER_SECRET_WRONG_PASSWORD" not in msg


class TestNoPostgreSQL:
    def test_no_postgresql_references_in_ops_files(self):
        """Verify no PostgreSQL/psycopg2 in app/, deploy/, docs/ (except hold note)."""
        import subprocess

        result = subprocess.run(
            [
                "grep", "-r", "-i",
                "psycopg2|DATABASE_URL|postgresql|pg_dump|pg_restore|psql",
                "--include=*.py", "--include=*.sh", "--include=*.md",
                "app/", "deploy/", "docs/",
            ],
            cwd="/root/.openclaw/workspace/finco1",
            capture_output=True,
            text=True,
        )

        # Filter out the hold note which documents the old contamination
        lines = [
            line for line in result.stdout.split("\n")
            if line and "ops_observability_hold_note" not in line
        ]

        assert result.returncode != 0 or not lines, (
            f"PostgreSQL/psycopg2 found:\n{result.stdout}"
        )