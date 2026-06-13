"""Phase M3 — Scenario Matrix Inline Override Editing tests.

Hard constraints verified here:

- Engine MD5 unchanged (waterfall_core.py).
- New routes exist and return correct HTML/status.
- set-field saves override, returns HTML fragment.
- set-field with unknown field returns 422.
- set-field with non-numeric value returns 422.
- cell-edit returns form HTML with input element.
- cell-view returns cell HTML.
- Template has data-m3-editable on editable input cells when live.
- Template has hx-get on editable input cells.
- Template does NOT add data-m3-editable to KPI cells.
- CSS has .matrix-cell-editable and .matrix-cell-editing.
- Workspace integration: matrix card present with M3 attributes.
- File scope: only allowed files changed.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-m3")

ENGINE_MD5 = "6bf49f33efc989736c17cea0cb9b7723"


# ---------------------------------------------------------------------------
# 1. Engine parity
# ---------------------------------------------------------------------------

class TestEngineParity:
    def test_engine_md5_unchanged(self):
        md5 = hashlib.md5(
            (REPO_ROOT / "app" / "waterfall_core.py").read_bytes()
        ).hexdigest()
        assert md5 == ENGINE_MD5, (
            f"waterfall_core.py MD5 changed: {md5!r} != {ENGINE_MD5!r}"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client_with_session(user_id="m3_user"):
    from fastapi.testclient import TestClient
    from app.auth import create_session_token
    from main_web import app
    c = TestClient(app, follow_redirects=False)
    token = create_session_token(user_id=user_id, username=user_id)
    c.cookies.set("finco_session", token)
    return c


def _create_test_scenario(user_id="m3_user"):
    """Create a non-base scenario for testing via the add_scenario persistence call."""
    import uuid
    from app.persistence.repository import save_project, save_scenario, add_scenario
    project_code = f"m3test_{uuid.uuid4().hex[:8]}"
    project_record = save_project(
        user_id=user_id,
        project_code=project_code,
        project_name="M3 Test Project",
        project_type="Wind",
        project_origin="user_created",
        source_project_template="tuho",
        template_source="tuho",
        baseline_snapshot={"capacity_mw": 35.0, "ppa_tariff_eur_mwh": 75.0},
        governance_state={},
        last_run_summary={},
        replay_metadata={},
    )
    # Create base case scenario first
    base = save_scenario(
        user_id=user_id,
        project_id=project_record.project_id,
        project_code=project_record.project_code,
        scenario_name="Base Case",
        source_project_template="tuho",
        snapshot={"capacity_mw": 35.0, "ppa_tariff_eur_mwh": 75.0},
        governance_state={},
        last_run_summary={},
        replay_metadata={},
    )
    # Create non-base scenario using add_scenario
    non_base = add_scenario(
        user_id=user_id,
        project_id=project_record.project_id,
        project_code=project_record.project_code,
        scenario_name="M3 Downside",
        parent_scenario_id=base.scenario_id,
        base_input_set={"capacity_mw": 35.0, "ppa_tariff_eur_mwh": 75.0},
        overrides={},
        governance_state={},
        replay_metadata={},
    )
    return non_base


# ---------------------------------------------------------------------------
# 2. New routes exist
# ---------------------------------------------------------------------------

class TestRoutesExist:
    @pytest.fixture(scope="class")
    def scenario(self):
        return _create_test_scenario()

    def test_set_field_route_exists(self, scenario):
        c = _make_client_with_session()
        r = c.post(
            f"/matrix/scenario/{scenario.scenario_id}/set-field",
            data={"field": "capacity_mw", "value": "40.0"},
        )
        assert r.status_code in (200, 303, 422), f"Unexpected: {r.status_code}"

    def test_cell_edit_route_exists(self, scenario):
        c = _make_client_with_session()
        r = c.get(
            f"/matrix/scenario/{scenario.scenario_id}/cell-edit",
            params={"field": "capacity_mw", "col": "downside"},
        )
        assert r.status_code in (200, 303, 422), f"Unexpected: {r.status_code}"

    def test_cell_view_route_exists(self, scenario):
        c = _make_client_with_session()
        r = c.get(
            f"/matrix/scenario/{scenario.scenario_id}/cell-view",
            params={"field": "capacity_mw", "col": "downside"},
        )
        assert r.status_code in (200, 303, 422), f"Unexpected: {r.status_code}"


# ---------------------------------------------------------------------------
# 3. set-field route — valid field+value returns 200 with HTML fragment
# ---------------------------------------------------------------------------

class TestSetFieldValid:
    @pytest.fixture(scope="class")
    def response(self):
        scenario = _create_test_scenario()
        c = _make_client_with_session()
        r = c.post(
            f"/matrix/scenario/{scenario.scenario_id}/set-field",
            data={"field": "capacity_mw", "value": "42.5"},
        )
        return r

    def test_status_200(self, response):
        assert response.status_code == 200

    def test_returns_html_fragment(self, response):
        ct = response.headers.get("content-type", "")
        assert "text/html" in ct

    def test_hx_trigger_header(self, response):
        assert response.headers.get("hx-trigger") == "matrixCellSaved"

    def test_contains_td(self, response):
        assert "<td" in response.text

    def test_contains_data_m3_editable(self, response):
        assert "data-m3-editable" in response.text

    def test_contains_value(self, response):
        # Should show formatted value (42.5 in some form)
        assert "42" in response.text


# ---------------------------------------------------------------------------
# 4. set-field — unknown field returns 422
# ---------------------------------------------------------------------------

class TestSetFieldUnknownField:
    def test_unknown_field_returns_422(self):
        scenario = _create_test_scenario()
        c = _make_client_with_session()
        r = c.post(
            f"/matrix/scenario/{scenario.scenario_id}/set-field",
            data={"field": "nonexistent_field_xyz", "value": "1.0"},
        )
        assert r.status_code == 422

    def test_unknown_field_error_message(self):
        scenario = _create_test_scenario()
        c = _make_client_with_session()
        r = c.post(
            f"/matrix/scenario/{scenario.scenario_id}/set-field",
            data={"field": "nonexistent_field_xyz", "value": "1.0"},
        )
        body = r.json()
        assert "error" in body


# ---------------------------------------------------------------------------
# 5. set-field — non-numeric value for numeric field returns 422
# ---------------------------------------------------------------------------

class TestSetFieldNonNumeric:
    def test_non_numeric_returns_422(self):
        scenario = _create_test_scenario()
        c = _make_client_with_session()
        r = c.post(
            f"/matrix/scenario/{scenario.scenario_id}/set-field",
            data={"field": "capacity_mw", "value": "not_a_number"},
        )
        assert r.status_code == 422

    def test_non_numeric_error_message(self):
        scenario = _create_test_scenario()
        c = _make_client_with_session()
        r = c.post(
            f"/matrix/scenario/{scenario.scenario_id}/set-field",
            data={"field": "capacity_mw", "value": "abc"},
        )
        body = r.json()
        assert "error" in body


# ---------------------------------------------------------------------------
# 6. cell-edit — returns form HTML with input element
# ---------------------------------------------------------------------------

class TestCellEdit:
    @pytest.fixture(scope="class")
    def response(self):
        scenario = _create_test_scenario()
        c = _make_client_with_session()
        r = c.get(
            f"/matrix/scenario/{scenario.scenario_id}/cell-edit",
            params={"field": "capacity_mw", "col": "downside"},
        )
        return r

    def test_status_200(self, response):
        assert response.status_code == 200

    def test_contains_form(self, response):
        assert "<form" in response.text

    def test_contains_input_element(self, response):
        assert '<input' in response.text

    def test_contains_data_m3_input(self, response):
        assert 'data-m3-input="true"' in response.text

    def test_contains_set_field_url(self, response):
        assert "set-field" in response.text


# ---------------------------------------------------------------------------
# 7. cell-view — returns cell HTML
# ---------------------------------------------------------------------------

class TestCellView:
    @pytest.fixture(scope="class")
    def response(self):
        scenario = _create_test_scenario()
        c = _make_client_with_session()
        r = c.get(
            f"/matrix/scenario/{scenario.scenario_id}/cell-view",
            params={"field": "capacity_mw", "col": "downside"},
        )
        return r

    def test_status_200(self, response):
        assert response.status_code == 200

    def test_contains_td(self, response):
        assert "<td" in response.text

    def test_contains_data_m3_editable(self, response):
        assert "data-m3-editable" in response.text

    def test_no_form_element(self, response):
        assert "<form" not in response.text


# ---------------------------------------------------------------------------
# 8. Template: data-m3-editable on input cells when live
# ---------------------------------------------------------------------------

class TestTemplateM3Editable:
    def _get_template_text(self):
        path = REPO_ROOT / "app" / "templates" / "partials" / "scenario_matrix.html"
        return path.read_text()

    def test_data_m3_editable_present(self):
        tmpl = self._get_template_text()
        assert "data-m3-editable" in tmpl

    def test_hx_get_present_for_cell_edit(self):
        tmpl = self._get_template_text()
        assert "cell-edit" in tmpl

    def test_matrix_cell_editable_class_present(self):
        tmpl = self._get_template_text()
        assert "matrix-cell-editable" in tmpl


# ---------------------------------------------------------------------------
# 9. Template: hx-get on editable input cells
# ---------------------------------------------------------------------------

class TestTemplateHxGet:
    def test_hx_get_cell_edit_url(self):
        tmpl = (REPO_ROOT / "app" / "templates" / "partials" / "scenario_matrix.html").read_text()
        assert "hx-get=" in tmpl
        assert "/cell-edit" in tmpl


# ---------------------------------------------------------------------------
# 10. Template: KPI cells do NOT get data-m3-editable
# ---------------------------------------------------------------------------

class TestTemplateKpiNotEditable:
    def test_kpi_cells_read_only(self):
        tmpl = (REPO_ROOT / "app" / "templates" / "partials" / "scenario_matrix.html").read_text()
        # The editable td should only appear when not entry.is_kpi
        # We verify that `not entry.is_kpi` guard appears in the template
        assert "not entry.is_kpi" in tmpl

    def test_kpi_check_is_present(self):
        tmpl = (REPO_ROOT / "app" / "templates" / "partials" / "scenario_matrix.html").read_text()
        assert "is_kpi" in tmpl


# ---------------------------------------------------------------------------
# 11. CSS: .matrix-cell-editable
# ---------------------------------------------------------------------------

class TestCSSEditable:
    def test_css_has_matrix_cell_editable(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert ".matrix-cell-editable" in css

    def test_css_has_cursor_pointer(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert "cursor: pointer" in css


# ---------------------------------------------------------------------------
# 12. CSS: .matrix-cell-editing
# ---------------------------------------------------------------------------

class TestCSSEditing:
    def test_css_has_matrix_cell_editing(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert ".matrix-cell-editing" in css

    def test_css_m3_section_present(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert "Phase M3" in css


# ---------------------------------------------------------------------------
# 13. Workspace integration: matrix card present with M3 attributes
# ---------------------------------------------------------------------------

class TestWorkspaceM3Integration:
    @pytest.fixture(scope="class")
    def workspace_html(self):
        from fastapi.testclient import TestClient
        from app.auth import create_session_token
        from main_web import app
        c = TestClient(app, follow_redirects=True)
        token = create_session_token(user_id="m3_ws_user", username="m3_ws_user")
        c.cookies.set("finco_session", token)
        r = c.get("/?project=tuho")
        assert r.status_code == 200
        return r.text

    def test_matrix_card_present(self, workspace_html):
        assert 'data-m2-matrix="true"' in workspace_html

    def test_m3_template_files_exist(self):
        assert (REPO_ROOT / "app" / "templates" / "partials" / "_matrix_cell_updated.html").exists()
        assert (REPO_ROOT / "app" / "templates" / "partials" / "_matrix_cell_edit.html").exists()


# ---------------------------------------------------------------------------
# 14. File scope: only allowed files changed
# ---------------------------------------------------------------------------

class TestFileScope:
    def test_only_allowed_files_changed(self):
        import shutil
        import subprocess
        if shutil.which("git") is None or not (REPO_ROOT / ".git").exists():
            pytest.skip("git not available")
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "diff", "--name-only", "origin/main"],
            capture_output=True, text=True,
        )
        changed = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        allowed_prefixes = (
            "app/ui/scenario_matrix.py",
            "app/templates/partials/scenario_matrix.html",
            "app/templates/partials/_matrix_cell_updated.html",
            "app/templates/partials/_matrix_cell_edit.html",
            "main_web.py",
            "static/styles.css",
            "tests/test_phase_m3_",
            "tests/test_phase_m2_",
            "tests/test_phase_m1_",
            "tests/test_phase_wf1_",
            "tests/test_phase_wf2_",
            "tests/test_phase_wf3_",
            "tests/test_phase_wf4_",
            "tests/test_phase_wf5_",
            "tests/test_phase_wf6_",
            "tests/test_phase_p2fix",
            "app/templates/partials/_results_subnav.html",
            "app/templates/partials/project_selector.html",
            "app/templates/partials/project_home.html",
            "app/templates/partials/new_project_minimal.html",
            "app/templates/partials/new_project_result.html",
            "app/ui/dashboard.py",
            "app/templates/partials/_dashboard_oob.html",
        )
        disallowed_prefixes = (
            "app/persistence/",
            "app/services/",
            "app/waterfall_core.py",
            "app/project_factories.py",
            "app/excel_export.py",
            "main_api.py",
            "static/app.js",
        )
        for f in changed:
            assert not any(f.startswith(p) for p in disallowed_prefixes), (
                f"Disallowed file changed: {f}"
            )
            assert any(f.startswith(p) for p in allowed_prefixes), (
                f"File outside allowed scope: {f}"
            )
