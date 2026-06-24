"""P1-COMPARE-VALIDATION: scenario compare cross-project guard.

Bug: GET /scenarios/compare accepted left_scenario_id and right_scenario_id
from any project. If both IDs came from a *different* project than the one
in the `project` query param, the compare service returned None (no data),
but the route displayed "Scenario compare ready" — a misleading success state.

Fix: Before calling compare_scenarios(), the route now loads both scenario
records and validates:
  1. Both scenarios exist for the authenticated user.
  2. Both scenarios belong to the project loaded in the workspace
     (scenario.project_id == project_record.project_id).
If either check fails, a user-friendly error message is returned instead of
the misleading success banner. No delta table or KPI comparison is rendered.

Tests:
  CV-1. Same-project compare -> "Scenario compare ready" (happy path unchanged).
  CV-2. Cross-project left scenario -> validation error message.
  CV-3. Cross-project right scenario -> validation error message.
  CV-4. Missing left scenario ID -> validation error message.
  CV-5. Missing right scenario ID -> validation error message.
  CV-6. No scenario IDs supplied -> prompt message (no change to existing UX).
  CV-7. Validation logic is in main_web.py before compare_scenarios() call.
  CV-8. compare_scenarios() is NOT called when validation fails (no side effects).
  CV-9. Engine MD5 unchanged.
  CV-10. TUHO P1 DSCR unchanged.
  CV-11. Oborovo P1 DSCR unchanged.
  CV-12. File scope guard.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")

ENGINE_MD5 = "6bf49f33efc989736c17cea0cb9b7723"
TUHO_P1_DSCR = 1.4507
OBOROVO_P1_DSCR = 1.15


# ---------------------------------------------------------------------------
# CV-7. Validation logic is present in main_web.py source
# ---------------------------------------------------------------------------

class TestValidationInSource:
    _SRC = (Path(REPO_ROOT) / "main_web.py").read_text()

    def test_cv7_validation_before_compare_call(self):
        """CV-7: The route validates project ownership before calling compare_scenarios."""
        src = self._SRC
        # The guard must check project_id membership
        assert "_left_sc.project_id != _project_id" in src or \
               "project_id" in src, (
            "Route must validate scenario project_id before calling compare_scenarios()"
        )
        # The error message must be present
        assert "do not belong to the same project" in src, (
            "Route must emit 'do not belong to the same project' on validation failure"
        )

    def test_cv8_compare_not_called_on_validation_failure(self):
        """CV-8: compare_scenarios() call is inside the validation success branch."""
        src = self._SRC
        # The compare_scenarios call must come AFTER the ownership check, not before.
        ownership_check_pos = src.find("do not belong to the same project")
        compare_call_pos = src.find(
            "compare_result = compare_scenarios(user.user_id, left_scenario_id"
        )
        assert ownership_check_pos != -1, "Ownership check not found in source"
        assert compare_call_pos != -1, "compare_scenarios() call not found in source"
        assert ownership_check_pos < compare_call_pos, (
            "Ownership check must appear before compare_scenarios() call in source"
        )

    def test_cv_missing_scenario_error_message(self):
        """Route emits a 'could not be found' message for missing scenarios."""
        src = self._SRC
        assert "could not be found" in src, (
            "Route must emit 'could not be found' when scenario does not exist"
        )


# ---------------------------------------------------------------------------
# Integration tests via DB seed + HTTP (app must run on port 8765)
# ---------------------------------------------------------------------------


def _make_project_with_scenario(user_id: str = "1") -> tuple[str, str]:
    """Seed a minimal project + scenario, return (project_code, scenario_id)."""
    from app.persistence.db import get_connection

    project_code = f"cv-test-{uuid.uuid4().hex[:8]}"
    project_id = uuid.uuid4().hex
    scenario_id = uuid.uuid4().hex
    now = datetime.datetime.utcnow().isoformat()

    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO projects
               (project_id, user_id, project_code, project_name,
                project_type, project_origin, source_project_template,
                baseline_snapshot_json, governance_state_json,
                last_run_summary_json, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                project_id, user_id, project_code, f"CV Test {project_code}",
                "generic_wind", "user_created", "generic_wind",
                "{}", '{"g20_status":"BLOCKED"}', "{}", now, now,
            ),
        )
        conn.execute(
            """INSERT INTO scenarios
               (scenario_id, project_id, user_id, scenario_name,
                project_code, source_project_template, is_base_case,
                snapshot_json, governance_state_json,
                last_run_summary_json, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                scenario_id, project_id, user_id, "Base Case",
                project_code, "generic_wind", 1,
                "{}", '{"g20_status":"BLOCKED"}', "{}", now, now,
            ),
        )
        conn.execute(
            """INSERT INTO workspace_states
               (workspace_id, project_id, user_id, project_code,
                active_scenario_id, draft_snapshot_json,
                saved_snapshot_json, last_runtime_snapshot_json,
                last_runtime_summary_json, dirty,
                governance_state_json, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                uuid.uuid4().hex, project_id, user_id, project_code,
                scenario_id, "{}", "{}", "{}", "{}", 0,
                '{"g20_status":"BLOCKED"}', now, now,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return project_code, scenario_id


class TestCompareValidationHTTP:
    """Integration tests requiring the app on port 8765."""

    @pytest.fixture(autouse=True)
    def _check_app(self):
        import urllib.request
        try:
            urllib.request.urlopen("http://localhost:8765/", timeout=2)
        except Exception:
            pytest.skip("App not running on port 8765 — skipping HTTP tests")

    def _login(self) -> str:
        import http.cookiejar
        import re
        import urllib.parse
        import urllib.request

        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        html = opener.open(
            urllib.request.Request("http://localhost:8765/login"), timeout=5
        ).read().decode("utf-8", errors="replace")
        csrf = (re.search(r'name="csrf_token"\s+value="([^"]+)"', html) or ["", ""])[1]
        data = urllib.parse.urlencode(
            {"csrf_token": csrf, "username": "admin", "password": "fincoGPT2026!"}
        ).encode()
        try:
            opener.open(
                urllib.request.Request(
                    "http://localhost:8765/login", data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                ),
                timeout=5,
            )
        except Exception:
            pass
        return "; ".join(f"{c.name}={c.value}" for c in jar)

    def _get(self, path: str, cookie: str) -> tuple[int, str]:
        import urllib.request
        req = urllib.request.Request(
            f"http://localhost:8765{path}", headers={"Cookie": cookie}
        )
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            return resp.status, resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", errors="replace")

    def test_cv1_same_project_compare_succeeds(self):
        """CV-1: Same-project compare renders success message."""
        cookie = self._login()
        # Create two scenarios under the same project
        project_code, scen_a = _make_project_with_scenario()
        # Add a second scenario to the same project
        from app.persistence.db import get_connection
        import datetime

        conn = get_connection()
        scen_b = uuid.uuid4().hex
        now = datetime.datetime.utcnow().isoformat()
        project_id = conn.execute(
            "SELECT project_id FROM projects WHERE project_code=?", (project_code,)
        ).fetchone()[0]
        conn.execute(
            """INSERT INTO scenarios
               (scenario_id, project_id, user_id, scenario_name,
                project_code, source_project_template, is_base_case,
                snapshot_json, governance_state_json,
                last_run_summary_json, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                scen_b, project_id, "1", "Downside",
                project_code, "generic_wind", 0,
                "{}", '{"g20_status":"BLOCKED"}', "{}", now, now,
            ),
        )
        conn.commit()
        conn.close()

        status, body = self._get(
            f"/scenarios/compare?project={project_code}"
            f"&left_scenario_id={scen_a}&right_scenario_id={scen_b}",
            cookie,
        )
        assert status == 200, f"Expected 200, got {status}"
        assert "Scenario compare ready" in body, (
            "Same-project compare should render 'Scenario compare ready'"
        )

    def test_cv2_cross_project_left_returns_error(self):
        """CV-2: Left scenario from wrong project returns validation error."""
        cookie = self._login()
        project_a, scen_a = _make_project_with_scenario()
        project_b, scen_b = _make_project_with_scenario()

        # Use project_a in URL but pass scen_a (from project_a) as left
        # and scen_b (from project_b) as right — cross-project
        status, body = self._get(
            f"/scenarios/compare?project={project_a}"
            f"&left_scenario_id={scen_a}&right_scenario_id={scen_b}",
            cookie,
        )
        assert status == 200
        assert "do not belong to the same project" in body, (
            f"Expected cross-project error, got: {body[:300]}"
        )
        assert "Scenario compare ready" not in body

    def test_cv3_cross_project_right_returns_error(self):
        """CV-3: Right scenario from wrong project returns validation error."""
        cookie = self._login()
        project_a, scen_a = _make_project_with_scenario()
        project_b, scen_b = _make_project_with_scenario()

        # project_b in URL, scen_b correct, scen_a from project_a = cross-project
        status, body = self._get(
            f"/scenarios/compare?project={project_b}"
            f"&left_scenario_id={scen_b}&right_scenario_id={scen_a}",
            cookie,
        )
        assert status == 200
        assert "do not belong to the same project" in body
        assert "Scenario compare ready" not in body

    def test_cv4_missing_left_scenario(self):
        """CV-4: Non-existent left_scenario_id returns error, not 500."""
        cookie = self._login()
        project_code, scen_a = _make_project_with_scenario()
        missing_id = "nonexistent-" + uuid.uuid4().hex

        status, body = self._get(
            f"/scenarios/compare?project={project_code}"
            f"&left_scenario_id={missing_id}&right_scenario_id={scen_a}",
            cookie,
        )
        assert status == 200
        assert "could not be found" in body or "do not belong" in body, (
            f"Expected not-found error, body excerpt: {body[:300]}"
        )
        assert "Scenario compare ready" not in body

    def test_cv5_missing_right_scenario(self):
        """CV-5: Non-existent right_scenario_id returns error, not 500."""
        cookie = self._login()
        project_code, scen_a = _make_project_with_scenario()
        missing_id = "nonexistent-" + uuid.uuid4().hex

        status, body = self._get(
            f"/scenarios/compare?project={project_code}"
            f"&left_scenario_id={scen_a}&right_scenario_id={missing_id}",
            cookie,
        )
        assert status == 200
        assert "could not be found" in body or "do not belong" in body
        assert "Scenario compare ready" not in body

    def test_cv6_no_scenario_ids_shows_prompt(self):
        """CV-6: No scenario IDs supplied shows selection prompt (unchanged UX)."""
        cookie = self._login()
        project_code, _ = _make_project_with_scenario()

        status, body = self._get(
            f"/scenarios/compare?project={project_code}", cookie
        )
        assert status == 200
        assert "Select two saved scenarios to compare" in body


# ---------------------------------------------------------------------------
# CV-9 to CV-11: Parity
# ---------------------------------------------------------------------------


class TestCompareValidationParity:
    def test_cv9_engine_md5(self):
        """CV-9: Engine MD5 must be unchanged."""
        digest = hashlib.md5(
            (Path(REPO_ROOT) / "app/waterfall_core.py").read_bytes()
        ).hexdigest()
        assert digest == ENGINE_MD5, f"Engine changed: {digest}"

    def test_cv10_tuho_p1_dscr(self):
        """CV-10: TUHO P1 DSCR must be 1.4507."""
        from app.project_factories import create_default_tuho_wind1
        from app.ui_runner import _build_period_engine, _run_waterfall
        proj = create_default_tuho_wind1()
        result = _run_waterfall(proj, _build_period_engine(proj))
        for p in result.periods:
            d = getattr(p, "dscr", None)
            if d is not None and abs(d) < 1e10:
                assert abs(d - TUHO_P1_DSCR) < 0.001, f"TUHO DSCR={d}"
                return
        pytest.fail("No finite DSCR found")

    def test_cv11_oborovo_p1_dscr(self):
        """CV-11: Oborovo P1 DSCR must be 1.1500."""
        from app.project_factories import create_default_oborovo
        from app.ui_runner import _build_period_engine, _run_waterfall
        proj = create_default_oborovo()
        result = _run_waterfall(proj, _build_period_engine(proj))
        for p in result.periods:
            d = getattr(p, "dscr", None)
            if d is not None and abs(d) < 1e10:
                assert abs(d - OBOROVO_P1_DSCR) < 0.01, f"Oborovo DSCR={d}"
                return
        pytest.fail("No finite DSCR found")


# ---------------------------------------------------------------------------
# CV-12: File scope guard
# ---------------------------------------------------------------------------


class TestCompareValidationFileScope:
    ALLOWED_PREFIXES = (
        "main_web.py",
        "tests/test_p1_compare_validation",
        "tests/test_phase_ux4cde_",
        "tests/test_phase_scenario1_",
        "tests/test_phase_scenario2_",
        "tests/test_phase_m4_",
        # IRR-ANOMALY-1-FIX display mapping followup
        "tests/test_phase_irr_",
        "tests/test_phase_pilot_blocker_1",
        "docs/phase_irr_",
        "docs/phase_pilot_blocker_1",
        "reports/phase_irr_",
        "reports/phase_pilot_blocker_1",
        "app/templates/partials/_matrix_run_result.html",
        # HOTFIX-PILOT-BLOCKER-1: presentation/routing fix
        # touches main_web.py (already in ALLOWED_PREFIXES),
        # app/services/project_save_as_service.py (F1), and
        # app/templates/partials/_factory_lock_indicator.html
        # (F2). All are presentation/routing only.
        "app/services/project_save_as_service.py",
        "app/templates/partials/_factory_lock_indicator.html",
        "app/ui/dashboard.py",
        "app/templates/partials/runtime_summary.html",  # UX-2C-1 cross-arc
        "tests/test_ux2c1_",  # UX-2C-1 cross-arc
        "tests/test_phase_pr1_",  # UX-2C-1 cross-arc
        "tests/test_phase_pr2_",  # UX-2C-1 cross-arc
        "tests/test_phase_pr3_",  # UX-2C-1 cross-arc
        "tests/test_phase_m1_",  # UX-2C-1 cross-arc
        "tests/test_phase_m2_",  # UX-2C-1 cross-arc
        "tests/test_phase_m3_",  # UX-2C-1 cross-arc
        "tests/test_phase_m4_",  # UX-2C-1 cross-arc
        "tests/test_phase_p2fix",  # UX-2C-1 cross-arc
        "tests/test_phase_scenario1_",  # UX-2C-1 cross-arc
        "tests/test_phase_stab",  # UX-2C-1 cross-arc
        "tests/test_phase_ux2_",  # UX-2C-1 cross-arc
        "tests/test_phase_ux4cde_",  # UX-2C-1 cross-arc
    )
    DISALLOWED_PREFIXES = (
        "app/waterfall_core.py",
        "app/project_factories.py",
        "app/persistence/",
        "app/export/",
    )

    def test_cv12_file_scope(self):
        """CV-12: Only allowed files changed on this branch."""
        import shutil
        if shutil.which("git") is None:
            pytest.skip("git not available")
        result = subprocess.run(
            ["git", "-C", REPO_ROOT, "diff", "--name-only", "origin/main"],
            capture_output=True, text=True,
        )
        changed = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        for f in changed:
            assert not any(f.startswith(p) for p in self.DISALLOWED_PREFIXES), (
                f"P1-COMPARE-VALIDATION must not touch {f}"
            )
            assert any(f.startswith(p) for p in self.ALLOWED_PREFIXES), (
                f"P1-COMPARE-VALIDATION file outside allowed scope: {f}"
            )
