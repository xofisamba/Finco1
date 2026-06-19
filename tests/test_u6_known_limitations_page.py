"""U6-KNOWN-LIMITATIONS-PAGE: user-facing Known Limitations page.

Covers:
1. /known-limitations renders the required sections and disclaimer.
2. The page is reachable from the Help-area header link and the
   shared app footer.
3. Login is required (consistent with other authenticated pages).
"""
from __future__ import annotations

import os

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-u6")

import pytest
from fastapi.testclient import TestClient

from app.auth import create_session_token
from main_web import app


@pytest.fixture()
def client():
    return TestClient(app, follow_redirects=False)


def _login(client, user_id):
    token = create_session_token(user_id=user_id, username=user_id)
    client.cookies.set("finco_session", token)
    return client


REQUIRED_SECTIONS = (
    "Validated Models",
    "Methodology Caveats",
    "Not Yet Validated",
    "Not Yet Supported",
)

DISCLAIMER = (
    "Outputs are financial modelling estimates and not legal, "
    "tax, accounting or investment advice."
)


def test_known_limitations_requires_login(client):
    resp = client.get("/known-limitations")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/login"


def test_known_limitations_renders_for_logged_in_user(client):
    _login(client, "u6_page")
    resp = client.get("/known-limitations")
    assert resp.status_code == 200


def test_known_limitations_has_required_sections(client):
    _login(client, "u6_sections")
    resp = client.get("/known-limitations")
    for section in REQUIRED_SECTIONS:
        assert section in resp.text, f"missing section: {section!r}"


def test_known_limitations_has_disclaimer(client):
    _login(client, "u6_disclaimer")
    resp = client.get("/known-limitations")
    assert DISCLAIMER in resp.text


def test_known_limitations_mentions_validated_generic_projects(client):
    _login(client, "u6_generic")
    resp = client.get("/known-limitations")
    assert "Generic Solar" in resp.text
    assert "Generic Wind" in resp.text


def test_known_limitations_mentions_not_yet_validated_configs(client):
    _login(client, "u6_not_validated")
    resp = client.get("/known-limitations")
    assert "BESS" in resp.text
    assert "Portfolio" in resp.text


def test_known_limitations_mentions_not_yet_supported_items(client):
    _login(client, "u6_not_supported")
    resp = client.get("/known-limitations")
    assert "Multi-lender debt" in resp.text
    assert "Advanced tax structures" in resp.text
    assert "R99/R102" in resp.text


def test_known_limitations_reachable_from_footer(client):
    _login(client, "u6_footer")
    resp = client.get("/projects/browse", follow_redirects=True)
    assert resp.status_code == 200
    assert 'href="/known-limitations"' in resp.text


def test_known_limitations_reachable_from_header_help_area(client):
    _login(client, "u6_header")
    resp = client.get("/projects/browse", follow_redirects=True)
    assert resp.status_code == 200
    assert 'class="header-known-limitations-link"' in resp.text


def test_help_link_no_longer_dead_end(client):
    _login(client, "u6_help_redirect")
    resp = client.get("/help")
    assert resp.status_code == 302
