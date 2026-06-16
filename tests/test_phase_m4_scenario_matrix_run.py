"""Phase M4 — Scenario Matrix Run Integration tests.

Hard constraints verified here:

- Engine MD5 unchanged (waterfall_core.py).
- POST /matrix/scenario/{id}/run exists and returns 200 with HTML fragment.
- Run result has data-m4-run-result attribute.
- Run result has HX-Trigger: matrixRunComplete header.
- After a successful run, last_run_summary is populated.
- Run on base-case scenario returns 422.
- Run on unknown scenario_id returns 422.
- Template has matrix-run-btn and data-m4-run-btn when m2_live.
- Template has matrix-run-badge-wrap.
- CSS has .matrix-run-btn, .matrix-run-badge, .matrix-run-badge--run, .matrix-run-badge--not-run.
- _matrix_run_result.html template exists.
- File scope: only allowed files changed.
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-m4")

ENGINE_MD5 = "6bf49f33efc989736c17cea0cb9b7723"


# ---------------------------------------------------------------------------
# 1. Engine parity
# ---------------------------------------------------------------------------

class TestEngineParity:
    def test_engine_md5_unchanged(self):
        md5 = hashlib.md5(
            (REPO_ROOT / "app" / "waterfall_core.py").read_bytes()
        ).hexdigest()
        assert md5 == ENGINE_MD5, f"waterfall_core.py MD5 changed: {md5!r}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(user_id="m4_user"):
    from fastapi.testclient import TestClient
    from app.auth import create_session_token
    from main_web import app
    c = TestClient(app, follow_redirects=False)
    token = create_session_token(user_id=user_id, username=user_id)
    c.cookies.set("finco_session", token)
    return c


_FULL_SNAPSHOT = {
    "project_name": "M4 Test Wind",
    "project_type": "Wind",
    "country_market": "Croatia",
    "capacity_mw": 35.0,
    "cod_date": "2025-01-01",
    "construction_months": 18,
    "horizon_years": 25,
    "tariff_eur_mwh": 75.0,
    "ppa_tariff_eur_mwh": 75.0,
    "ppa_term_years": 15,
    "p50_hours": 2800,
    "opex_y1_keur": 1200.0,
    "opex_y1_total_keur": 1200.0,
    "total_capex_keur": 42000.0,
    "gearing_pct": 70.0,
    "interest_rate_pct": 4.5,
    "tenor_years": 18,
    "senior_tenor_years": 18,
    "target_dscr": 1.30,
    "operating_hours_p50": 2800,
}


def _create_non_base_scenario(user_id="m4_user"):
    """Create a non-base scenario with a full valid snapshot."""
    import uuid
    from app.persistence.repository import save_project, save_scenario, add_scenario

    project_code = f"m4test_{uuid.uuid4().hex[:8]}"
    project_record = save_project(
        user_id=user_id,
        project_code=project_code,
        project_name="M4 Test Project",
        project_type="Wind",
        project_origin="user_created",
        source_project_template="tuho",
        template_source="tuho",
        baseline_snapshot=_FULL_SNAPSHOT,
        governance_state={},
        last_run_summary={},
        replay_metadata={},
    )
    base = save_scenario(
        user_id=user_id,
        project_id=project_record.project_id,
        project_code=project_record.project_code,
        scenario_name="Base Case",
        source_project_template="tuho",
        snapshot=_FULL_SNAPSHOT,
        governance_state={},
        last_run_summary={},
        replay_metadata={},
    )
    non_base = add_scenario(
        user_id=user_id,
        project_id=project_record.project_id,
        project_code=project_record.project_code,
        scenario_name="M4 Downside",
        parent_scenario_id=base.scenario_id,
        base_input_set=_FULL_SNAPSHOT,
        overrides={"capacity_mw": 30.0},
        governance_state={},
        replay_metadata={},
    )
    return non_base, project_record


# ---------------------------------------------------------------------------
# 2. Route: POST /matrix/scenario/{id}/run
# ---------------------------------------------------------------------------

class TestRunRouteExists:
    def test_run_route_returns_200(self):
        non_base, _ = _create_non_base_scenario()
        c = _make_client()
        r = c.post(f"/matrix/scenario/{non_base.scenario_id}/run")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"

    def test_run_route_returns_html(self):
        non_base, _ = _create_non_base_scenario()
        c = _make_client()
        r = c.post(f"/matrix/scenario/{non_base.scenario_id}/run")
        assert "text/html" in r.headers.get("content-type", "")

    def test_run_result_hx_trigger(self):
        non_base, _ = _create_non_base_scenario()
        c = _make_client()
        r = c.post(f"/matrix/scenario/{non_base.scenario_id}/run")
        assert r.headers.get("hx-trigger") == "matrixRunComplete"

    def test_run_result_data_attribute(self):
        non_base, _ = _create_non_base_scenario()
        c = _make_client()
        r = c.post(f"/matrix/scenario/{non_base.scenario_id}/run")
        assert 'data-m4-run-result="true"' in r.text

    def test_run_result_contains_run_badge(self):
        non_base, _ = _create_non_base_scenario()
        c = _make_client()
        r = c.post(f"/matrix/scenario/{non_base.scenario_id}/run")
        assert "matrix-run-badge--run" in r.text or "data-m4-run-badge" in r.text


# ---------------------------------------------------------------------------
# 3. Run updates last_run_summary
# ---------------------------------------------------------------------------

class TestRunUpdatesPersistence:
    def test_last_run_summary_populated_after_run(self):
        from app.persistence.repository import get_scenario
        non_base, _ = _create_non_base_scenario()
        assert not non_base.last_run_summary  # starts empty
        c = _make_client()
        r = c.post(f"/matrix/scenario/{non_base.scenario_id}/run")
        assert r.status_code == 200
        updated = get_scenario(non_base.scenario_id, "m4_user")
        assert updated is not None
        assert updated.last_run_summary, "last_run_summary should be populated after run"


# ---------------------------------------------------------------------------
# 4. Error cases
# ---------------------------------------------------------------------------

class TestRunErrorCases:
    def test_base_case_returns_422(self):
        import uuid
        from app.persistence.repository import save_project, save_scenario, promote_scenario_to_base_case
        uid = "m4_base_test"
        pc = f"m4base_{uuid.uuid4().hex[:6]}"
        proj = save_project(
            user_id=uid, project_code=pc, project_name="M4 Base Test", project_type="Wind",
            project_origin="user_created", source_project_template="tuho", template_source="tuho",
            baseline_snapshot=_FULL_SNAPSHOT, governance_state={}, last_run_summary={}, replay_metadata={},
        )
        base = save_scenario(
            user_id=uid, project_id=proj.project_id, project_code=proj.project_code,
            scenario_name="Base Case", source_project_template="tuho",
            snapshot=_FULL_SNAPSHOT, governance_state={}, last_run_summary={}, replay_metadata={},
        )
        promote_scenario_to_base_case(uid, base.scenario_id)
        c = _make_client(uid)
        r = c.post(f"/matrix/scenario/{base.scenario_id}/run")
        assert r.status_code == 422

    def test_unknown_scenario_returns_422(self):
        c = _make_client()
        r = c.post("/matrix/scenario/nonexistent-scenario-id-xyz/run")
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# 5. Template: run button present in matrix column headers when m2_live
# ---------------------------------------------------------------------------

class TestTemplateRunButton:
    def _get_template_text(self):
        return (REPO_ROOT / "app" / "templates" / "partials" / "scenario_matrix.html").read_text()

    def test_matrix_run_btn_class_present(self):
        tmpl = self._get_template_text()
        assert "matrix-run-btn" in tmpl

    def test_data_m4_run_btn_attr_present(self):
        tmpl = self._get_template_text()
        assert "data-m4-run-btn" in tmpl

    def test_hx_post_run_url_present(self):
        tmpl = self._get_template_text()
        assert "/run" in tmpl
        assert "hx-post" in tmpl

    def test_matrix_run_badge_wrap_present(self):
        tmpl = self._get_template_text()
        assert "matrix-run-badge-wrap" in tmpl

    def test_data_m4_run_wrap_present(self):
        tmpl = self._get_template_text()
        assert "data-m4-run-wrap" in tmpl

    def test_run_result_template_exists(self):
        p = REPO_ROOT / "app" / "templates" / "partials" / "_matrix_run_result.html"
        assert p.exists(), "_matrix_run_result.html must exist"

    def test_run_result_template_has_data_attribute(self):
        p = REPO_ROOT / "app" / "templates" / "partials" / "_matrix_run_result.html"
        assert "data-m4-run-result" in p.read_text()


# ---------------------------------------------------------------------------
# 6. CSS rules
# ---------------------------------------------------------------------------

class TestCSS:
    def test_matrix_run_btn_css(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert ".matrix-run-btn" in css

    def test_matrix_run_badge_css(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert ".matrix-run-badge" in css

    def test_matrix_run_badge_run_css(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert ".matrix-run-badge--run" in css

    def test_matrix_run_badge_not_run_css(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert ".matrix-run-badge--not-run" in css

    def test_matrix_run_badge_error_css(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert ".matrix-run-badge--error" in css

    def test_m4_css_section_present(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert "Phase M4" in css


# ---------------------------------------------------------------------------
# 7. File scope
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
            "app/templates/partials/_matrix_run_result.html",
            "main_web.py",
            "static/styles.css",
            "tests/test_phase_m4_",
            # Cross-arc allowlist patches accumulated since M4:
            "tests/test_phase_stab",
            "tests/test_p1_compare_validation.py",
            "tests/test_phase_irr_",
            "tests/test_phase_ux4cde_",
            "tests/test_phase_scenario1_",
            "tests/test_phase_scenario2_",
            "app/templates/partials/_scenario_matrix_oob.html",
            "app/ui/dashboard.py",
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
            "tests/test_phase_pr1_",
            "tests/test_phase_pr2_",
            "tests/test_phase_pr3_",
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
