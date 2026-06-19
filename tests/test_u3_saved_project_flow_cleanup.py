"""U3-SAVED-PROJECT-FLOW-CLEANUP: project browser / save-state / reopen UX.

Covers the External Friendly Pilot blocker that follows U2 (New Project
simplification): once a project can be created in 30 seconds, the user
needs to be able to find it again, know it was saved, and reopen it
without confusion -- without TUHO/Oborovo reference projects mixed in or
internal terminology ("factory", "baseline", "calibration") leaking
through.

This module covers:

1. "My Projects" section rendering in /projects/browse.
2. "Example Projects" section rendering in /projects/browse.
3. TUHO visibility through the Example Projects path.
4. User project visibility through the My Projects path.
5. Save-state indicator rendering (sidebar Saved/Unsaved badge).
6. Reopen workflow (create -> save -> close -> reopen -> run -> export ->
   scenario).
7. No regression in project switching between My Projects and Example
   Projects.

Does not touch domain/waterfall/*, app/waterfall_core.py,
app/input_adapter.py, app/project_factories.py, or any engine/validation/
export calculation -- only the project browser/selector presentation
layer in main_web.py and app/templates/partials/{project_browser,
project_selector}.html.
"""
from __future__ import annotations

import os
import re

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-u3")

import pytest
from fastapi.testclient import TestClient

from app.auth import create_session_token
from main_web import app


@pytest.fixture()
def client():
    return TestClient(app, follow_redirects=True)


def _login(client, user_id):
    token = create_session_token(user_id=user_id, username=user_id)
    client.cookies.set("finco_session", token)
    return client


def _create_minimal(client, *, user_id, name, technology, country, capacity_mw):
    _login(client, user_id)
    resp = client.post(
        "/projects/create",
        data={
            "project_name": name,
            "project_type": technology,
            "template_source": "",
            "country_market": country,
            "capacity_mw": str(capacity_mw),
        },
    )
    return resp


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")


# ---------------------------------------------------------------------------
# 1. "My Projects" section rendering
# ---------------------------------------------------------------------------

def test_my_projects_section_renders_with_user_project(client):
    name = "U3 My Project Test"
    resp = _create_minimal(
        client, user_id="u3_myproj", name=name, technology="Solar",
        country="Spain", capacity_mw=20,
    )
    assert resp.status_code == 200

    browse = client.get("/projects/browse")
    assert browse.status_code == 200
    assert "My Projects" in browse.text
    assert name in browse.text


# ---------------------------------------------------------------------------
# 2. "Example Projects" section rendering
# ---------------------------------------------------------------------------

def test_example_projects_section_renders(client):
    _login(client, "u3_example_section")
    browse = client.get("/projects/browse")
    assert browse.status_code == 200
    assert "Example Projects" in browse.text


# ---------------------------------------------------------------------------
# 3. TUHO visibility through the Example Projects path
# ---------------------------------------------------------------------------

def test_tuho_and_oborovo_visible_under_example_projects(client):
    _login(client, "u3_tuho_visibility")
    browse = client.get("/projects/browse")
    assert browse.status_code == 200
    example_start = browse.text.find("Example Projects")
    assert example_start != -1
    example_section = browse.text[example_start:]
    assert "TUHO Wind" in example_section
    assert "Oborovo Solar PV" in example_section


# ---------------------------------------------------------------------------
# 4. User project visibility through My Projects path
# ---------------------------------------------------------------------------

def test_user_project_appears_under_my_projects_not_example_projects(client):
    name = "U3 Section Placement Test"
    resp = _create_minimal(
        client, user_id="u3_placement", name=name, technology="Wind",
        country="Croatia", capacity_mw=25,
    )
    assert resp.status_code == 200

    browse = client.get("/projects/browse")
    body = browse.text[browse.text.find('<div class="project-browser"'):]
    my_start = body.find("My Projects")
    example_start = body.find("Example Projects")
    assert my_start != -1 and example_start != -1
    assert my_start < example_start, "My Projects must appear before Example Projects"

    my_projects_section = body[my_start:example_start]
    assert name in my_projects_section
    assert "TUHO" not in my_projects_section
    assert "Oborovo" not in my_projects_section


# ---------------------------------------------------------------------------
# 5. Save-state indicator rendering
# ---------------------------------------------------------------------------

def test_saved_state_badge_visible_after_creation(client):
    name = "U3 Save State Test"
    resp = _create_minimal(
        client, user_id="u3_savestate", name=name, technology="Solar",
        country="Spain", capacity_mw=15,
    )
    assert resp.status_code == 200
    code = _slug(name)

    opened = client.get(f"/?project={code}")
    assert opened.status_code == 200
    assert "Saved" in opened.text or "Unsaved" in opened.text


def test_no_internal_template_identifiers_in_project_browser(client):
    """Project cards must not leak template_source / factory identifiers."""
    name = "U3 No Internal IDs Test"
    resp = _create_minimal(
        client, user_id="u3_noids", name=name, technology="Wind",
        country="Croatia", capacity_mw=30,
    )
    assert resp.status_code == 200

    browse = client.get("/projects/browse")
    assert "generic_wind" not in browse.text
    assert "generic_solar" not in browse.text


# ---------------------------------------------------------------------------
# 6. Reopen workflow: create -> save -> close -> reopen -> run -> export ->
#    scenario
# ---------------------------------------------------------------------------

def test_full_reopen_workflow(client):
    name = "U3 Full Reopen Workflow"
    create_resp = _create_minimal(
        client, user_id="u3_workflow", name=name, technology="Wind",
        country="Croatia", capacity_mw=35,
    )
    assert create_resp.status_code == 200
    code = _slug(name)

    # "Close" (navigate away to the project browser) then reopen.
    browse = client.get("/projects/browse")
    assert browse.status_code == 200
    assert name in browse.text

    reopened = client.get(f"/?project={code}")
    assert reopened.status_code == 200
    assert name in reopened.text

    run_resp = client.post("/run", data={"active_project": code})
    assert run_resp.status_code == 200

    export_resp = client.get(f"/exports/runtime-summary.csv?project={code}")
    assert export_resp.status_code == 200
    assert export_resp.headers.get("content-type", "").startswith("text/csv")

    scenario_resp = client.post(
        "/scenarios/add",
        data={"project_code": code, "scenario_name": "Downside"},
    )
    assert scenario_resp.status_code == 200


# ---------------------------------------------------------------------------
# 7. No regression in project switching
# ---------------------------------------------------------------------------

def test_switching_between_user_project_and_example_project(client):
    name = "U3 Switch Test"
    create_resp = _create_minimal(
        client, user_id="u3_switch", name=name, technology="Solar",
        country="Spain", capacity_mw=10,
    )
    assert create_resp.status_code == 200
    code = _slug(name)

    my_project = client.get(f"/?project={code}")
    assert my_project.status_code == 200
    assert name in my_project.text

    example_project = client.get("/?project=tuho")
    assert example_project.status_code == 200
    assert "TUHO" in example_project.text

    back_to_mine = client.get(f"/?project={code}")
    assert back_to_mine.status_code == 200
    assert name in back_to_mine.text
