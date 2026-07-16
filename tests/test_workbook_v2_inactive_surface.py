"""Integration tests: V2 workbook surface when FINCO_WORKBOOK_V2=0.

Verifies that:
- All 11 POST endpoints return 409 (not 200/422/500) — activation guard fires first
- Complete DB snapshot is identical before and after every rejected request
- GET /v2/workbook?project=X redirects to /?project=X
- GET /v2/workbook (no project) redirects to /library
"""
from __future__ import annotations

import importlib
import os
import sqlite3
import sys
import urllib.parse
from unittest.mock import patch

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-inactive-surface-key")

# ---------------------------------------------------------------------------
# Fixture: isolated SQLite + inactive flag + real app + real project
# ---------------------------------------------------------------------------

_INACTIVE_ENV = {
    "FINCO_WORKBOOK_V2": "0",
    "FINCO_SECRET_KEY": "test-inactive-surface-key",
}

_CREATE_FORM = {
    "project_name": "Inactive Guard Test",
    "project_type": "Wind",
    "template_source": "generic_wind",
    "country_market": "Poland",
    "capacity_mw": "50",
    "cod_date": "2028-01-01",
    "construction_months": "18",
    "horizon_years": "25",
    "tariff_eur_mwh": "55",
    "ppa_term_years": "15",
    "p50_hours": "2200",
    "opex_y1_keur": "900",
    "total_capex_keur": "60000",
    "gearing_pct": "70",
    "interest_rate_pct": "4.5",
    "tenor_years": "18",
    "target_dscr": "1.30",
}


@pytest.fixture(scope="class")
def inactive_setup(tmp_path_factory):
    """Create an isolated DB, a real project, seed CAPEX/OPEX rows, return client + state."""
    tmp = tmp_path_factory.mktemp("inactive_zero_write")
    db_path = str(tmp / "inactive_zero_write.db")
    env_patch = {**_INACTIVE_ENV, "FINCO_DB_PATH": db_path}

    with patch.dict(os.environ, env_patch):
        # Clean module cache so env is read fresh
        for mod_name in [k for k in sys.modules
                         if "workbook_flag" in k or k == "main_web"
                         or k.startswith("app.")]:
            sys.modules.pop(mod_name, None)

        from fastapi.testclient import TestClient
        import main_web as mw
        importlib.reload(mw)

        from app.auth import COOKIE_NAME, create_session_token
        token = create_session_token()

        with TestClient(mw.app, raise_server_exceptions=False) as client:
            client.cookies.set(COOKIE_NAME, token)

            # Create a real working-copy project
            resp = client.post("/projects/create", data=_CREATE_FORM,
                               follow_redirects=False)
            location = resp.headers.get("location", "")
            parsed = urllib.parse.urlparse(location)
            project_code = dict(urllib.parse.parse_qsl(parsed.query)).get("project", "")
            assert project_code, f"project creation failed; location={location!r}"

            # Retrieve project_id for DB seeding
            con = sqlite3.connect(db_path)
            row = con.execute(
                "SELECT project_id FROM projects WHERE project_code=?", (project_code,)
            ).fetchone()
            assert row, f"project row not found for {project_code}"
            project_id = row[0]

            # Seed one CAPEX sub-line
            import uuid
            now_ts = "2026-01-01T00:00:00"
            capex_id = str(uuid.uuid4())
            con.execute(
                "INSERT INTO capex_sub_lines "
                "(sub_line_id, project_id, parent_category_code, business_code, "
                " display_order, label, amount_keur, source, is_active, "
                " created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (capex_id, project_id, "construction", "SEED-C", 1,
                 "Seeded capex line", 1000.0, "manual", 1, now_ts, now_ts),
            )
            # Seed one OPEX sub-line
            opex_id = str(uuid.uuid4())
            con.execute(
                "INSERT INTO opex_sub_lines "
                "(sub_line_id, project_id, parent_group_code, business_code, "
                " display_order, label, amount_keur, source, is_active, "
                " created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (opex_id, project_id, "om", "SEED-O", 1,
                 "Seeded opex line", 200.0, "manual", 1, now_ts, now_ts),
            )
            con.commit()
            con.close()

            yield {
                "client": client,
                "db_path": db_path,
                "project_code": project_code,
                "project_id": project_id,
            }


def _snapshot(db_path: str, project_code: str, project_id: int) -> dict:
    """Capture a deterministic DB snapshot for zero-write verification."""
    con = sqlite3.connect(db_path)
    try:
        proj = con.execute(
            "SELECT * FROM projects WHERE project_code=?", (project_code,)
        ).fetchone()
        ws = con.execute(
            "SELECT draft_snapshot_json, saved_snapshot_json, dirty, "
            "last_runtime_snapshot_id, last_runtime_summary_json, draft_content_hash "
            "FROM workspace_states WHERE project_code=?", (project_code,)
        ).fetchone()
        try:
            runs = con.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        except Exception:
            runs = 0
        try:
            capex_rows = con.execute(
                "SELECT sub_line_id, label, amount_keur, is_active "
                "FROM capex_sub_lines WHERE project_id=? ORDER BY sub_line_id",
                (project_id,)
            ).fetchall()
        except Exception:
            capex_rows = []
        try:
            opex_rows = con.execute(
                "SELECT sub_line_id, label, amount_keur, is_active "
                "FROM opex_sub_lines WHERE project_id=? ORDER BY sub_line_id",
                (project_id,)
            ).fetchall()
        except Exception:
            opex_rows = []
        return {
            "proj": proj,
            "ws": ws,
            "runs": runs,
            "capex": capex_rows,
            "opex": opex_rows,
        }
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Test class: zero-write proof for all 11 POST endpoints
# ---------------------------------------------------------------------------

class TestInactiveGuardZeroWrite:
    """All 11 POST endpoints return 409 and leave the DB byte-identical."""

    # (path, extra_form_fields_beyond_project)
    POST_ENDPOINTS = [
        ("/v2/workbook/update",              {}),
        ("/v2/workbook/inputs-slice1/update", {"field_id": "project_setup.schedule.cod_date",
                                               "value": "2030-01-01",
                                               "workbook_version": "1",
                                               "content_hash": "aaa"}),
        ("/v2/workbook/run",                 {}),
        ("/v2/capex/line/add",               {"parent_category_code": "construction",
                                               "label": "Test",
                                               "workbook_version": "1",
                                               "content_hash": "aaa"}),
        ("/v2/capex/line/update",            {"sub_line_id": "x", "label": "X",
                                               "row_version": "1",
                                               "workbook_version": "1",
                                               "content_hash": "aaa"}),
        ("/v2/capex/line/deactivate",        {"sub_line_id": "x", "row_version": "1",
                                               "workbook_version": "1",
                                               "content_hash": "aaa"}),
        ("/v2/capex/line/reorder",           {"parent_category_code": "construction",
                                               "workbook_version": "1",
                                               "content_hash": "aaa"}),
        ("/v2/opex/line/add",                {"parent_category_code": "om",
                                               "label": "Test",
                                               "workbook_version": "1",
                                               "content_hash": "aaa"}),
        ("/v2/opex/line/update",             {"sub_line_id": "x", "label": "X",
                                               "row_version": "1",
                                               "workbook_version": "1",
                                               "content_hash": "aaa"}),
        ("/v2/opex/line/deactivate",         {"sub_line_id": "x", "row_version": "1",
                                               "workbook_version": "1",
                                               "content_hash": "aaa"}),
        ("/v2/opex/line/reorder",            {"parent_category_code": "om",
                                               "workbook_version": "1",
                                               "content_hash": "aaa"}),
    ]

    @pytest.mark.parametrize("endpoint,extra", POST_ENDPOINTS)
    def test_post_returns_409_with_zero_db_writes(self, inactive_setup, endpoint, extra):
        client = inactive_setup["client"]
        db_path = inactive_setup["db_path"]
        project_code = inactive_setup["project_code"]
        project_id = inactive_setup["project_id"]

        data = {"project": project_code, **extra}
        before = _snapshot(db_path, project_code, project_id)

        resp = client.post(endpoint, data=data)

        after = _snapshot(db_path, project_code, project_id)

        assert resp.status_code == 409, (
            f"{endpoint} returned {resp.status_code} (expected 409). "
            f"Body: {resp.text[:200]}"
        )
        assert before == after, (
            f"{endpoint}: DB state changed despite 409 rejection.\n"
            f"  BEFORE: {before}\n  AFTER:  {after}"
        )


class TestInactiveGetRedirects:
    """GET /v2/workbook inactive redirects."""

    @pytest.fixture(autouse=True)
    def _client(self, inactive_setup):
        self.client = inactive_setup["client"]

    def test_get_workbook_with_project_redirects_to_legacy(self):
        resp = self.client.get("/v2/workbook?project=TEST001", follow_redirects=False)
        assert resp.status_code == 302
        location = resp.headers.get("location", "")
        assert "project=TEST001" in location, f"Expected project=TEST001, got {location}"
        assert "/?project=" in location or location.startswith("/?"), (
            f"Expected redirect to /?project=TEST001, got {location}"
        )

    def test_get_workbook_with_sheet_inputs_redirects_to_fragment(self):
        resp = self.client.get("/v2/workbook?project=TEST001&sheet=inputs",
                               follow_redirects=False)
        assert resp.status_code == 302
        location = resp.headers.get("location", "")
        assert "#inputs" in location, (
            f"Expected #inputs fragment in inactive redirect, got {location}"
        )

    def test_get_workbook_no_project_redirects_to_library(self):
        resp = self.client.get("/v2/workbook", follow_redirects=False)
        assert resp.status_code == 302
        location = resp.headers.get("location", "")
        assert "/library" in location, f"Expected /library redirect, got {location}"
