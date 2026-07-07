import os
import re
import shutil
import tempfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ("tuho", "oborovo", "generic_solar", "generic_wind")
ROUTES = (
    "/",
    "/scenarios/exec-summary",
    "/scenarios/ic-pack",
    "/scenarios/credit-pack",
    "/scenarios/credit-summary",
    "/scenarios/lender-case",
    "/scenarios/compare",
    "/exports/runtime-summary.csv",
    "/exports/institutional-workbook.xlsx",
)

DEVELOPER_VISIBLE_WORDING = (
    "TODO",
    "placeholder",
    "demo",
    "temporary",
    "preview-only",
    "Coming Soon",
)


@pytest.fixture(scope="module")
def authenticated_client():
    tmpdir = tempfile.mkdtemp(prefix="finco1-sprint13-route-matrix-")
    db_path = Path(tmpdir) / "finco1_sprint13_route_matrix.db"

    os.environ["FINCO_SECRET_KEY"] = "sprint13-route-matrix-key"
    os.environ["FINCO_DB_URL"] = f"sqlite:///{db_path}"
    os.environ["FINCO_COOKIE_SECURE"] = "false"

    from fastapi.testclient import TestClient
    from main_web import app

    client = TestClient(app, raise_server_exceptions=False)
    login = client.get("/login")
    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', login.text)
    if csrf_match:
        client.post(
            "/login",
            data={
                "username": "admin",
                "password": "admin",
                "csrf_token": csrf_match.group(1),
            },
            follow_redirects=False,
        )

    yield client

    for key in ("FINCO_SECRET_KEY", "FINCO_DB_URL", "FINCO_COOKIE_SECURE"):
        os.environ.pop(key, None)
    shutil.rmtree(tmpdir, ignore_errors=True)


def _visible_text(html: str) -> str:
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.DOTALL)
    html = re.sub(r"<script\b.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style\b.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html)


@pytest.mark.parametrize("project", PROJECTS)
@pytest.mark.parametrize("route", ROUTES)
def test_sprint13_institutional_route_matrix(authenticated_client, project, route):
    response = authenticated_client.get(route, params={"project": project}, follow_redirects=True)

    assert response.status_code != 500, f"{route} for {project} returned HTTP 500"
    assert response.content, f"{route} for {project} returned a blank response"

    content_type = response.headers.get("content-type", "").lower()
    if "html" not in content_type:
        return

    visible = _visible_text(response.text)
    assert visible.strip(), f"{route} for {project} rendered blank visible text"

    for phrase in DEVELOPER_VISIBLE_WORDING:
        assert phrase.lower() not in visible.lower(), (
            f"{route} for {project} leaked developer wording {phrase!r}"
        )


def test_sprint13_playwright_dependency_status_documented():
    playwright = pytest.importorskip(
        "playwright.sync_api",
        reason=(
            "OPTIONAL_BROWSER_DEPENDENCY_MISSING: Sprint 13 browser screenshot "
            "capture requires Playwright and Chromium in the local environment."
        ),
    )
    assert playwright is not None
