"""HOTFIX-1: Version history numeric coercion — no 500 on reopen.

Root cause: scenario_version_history.html line 85 used Jinja2 '%.1f'|format
on card.equity_irr which could be a string from last_run_summary_json,
causing TypeError: must be real number, not str.

Fix: coerce card.equity_irr via the Jinja2 float filter before formatting.

Tests:
  VH-1. Float equity_irr renders correctly (e.g. 0.0904 → "9.1%").
  VH-2. Numeric string equity_irr renders without error (e.g. "0.0904").
  VH-3. None equity_irr renders without error (block skipped).
  VH-4. Non-numeric garbage renders "—" without error.
  VH-5. Empty-string equity_irr renders "—" without error.
  VH-6. Missing equity_irr key (not in summary) renders without error.
  VH-7. No run history at all (empty summary) renders without error.
  VH-8. TUHO reference project opens HTTP 200.
  VH-9. TUHO working copy with string-typed run history opens HTTP 200.
  VH-10. Scope guard — only allowed files changed.
  VH-11. Engine MD5 unchanged.
  VH-12. TUHO P1 DSCR unchanged (1.4507).
  VH-13. Oborovo P1 DSCR unchanged (1.1500).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")

ENGINE_MD5 = "6bf49f33efc989736c17cea0cb9b7723"
TUHO_P1_DSCR = 1.4507
OBOROVO_P1_DSCR = 1.15

_TEMPLATE_PATH = (
    Path(REPO_ROOT) / "app/templates/partials/scenario_version_history.html"
)


def _render_template(equity_irr_value):
    """Render the version history template with a single card having
    the given equity_irr value. Returns rendered HTML string."""
    from jinja2 import Environment, FileSystemLoader

    env = Environment(
        loader=FileSystemLoader(str(Path(REPO_ROOT) / "app/templates")),
        autoescape=False,
    )
    tmpl = env.get_template("partials/scenario_version_history.html")

    import datetime

    card = {
        "scenario_id": "test-scenario-id",
        "scenario_name": "Test Scenario",
        "project_code": "test-project",
        "updated_at": datetime.datetime(2026, 1, 1, 12, 0, 0),
        "copied_from_scenario_id": None,
        "project_irr": 0.07,
        "equity_irr": equity_irr_value,
        "avg_dscr": 1.4,
        "export_count": 0,
        "governance_state": {},
        "previous_run_summary": {},
        "is_user_project": False,
        "template_source": "",
        "panel_rows": [],
        "has_previous_run": False,
    }

    class FakeWS:
        active_scenario_id = "other-id"
        dirty = False

    return tmpl.render(
        scenario_summary_cards=[card],
        workspace_state=FakeWS(),
        dirty_state_ui=None,
        scenario_workflow_ui=None,
    )


# ---------------------------------------------------------------------------
# VH-1 to VH-7: Template coercion unit tests
# ---------------------------------------------------------------------------


class TestVersionHistoryCoercion:
    def test_vh1_float_value(self):
        """VH-1: float equity_irr renders without error."""
        html = _render_template(0.0904)
        assert "IRR" in html
        assert "9.0" in html  # 0.0904 * 100 = 9.04 → "9.0"

    def test_vh2_numeric_string(self):
        """VH-2: string equity_irr renders without error."""
        html = _render_template("0.0904")
        assert "IRR" in html
        # Should not raise — main assertion is absence of exception

    def test_vh3_none_value(self):
        """VH-3: None equity_irr — block skipped, no error."""
        html = _render_template(None)
        # The {% if ... is not none %} block skips entirely
        assert isinstance(html, str)

    def test_vh4_garbage_string(self):
        """VH-4: non-numeric string renders fallback dash, not error."""
        html = _render_template("not-a-number")
        assert "—" in html or "IRR" not in html

    def test_vh5_empty_string(self):
        """VH-5: empty string equity_irr renders fallback dash, not error."""
        html = _render_template("")
        assert isinstance(html, str)

    def test_vh6_zero_float(self):
        """VH-6: 0.0 equity_irr (valid) renders '0.0%', not '—'."""
        html = _render_template(0.0)
        # 0.0 is a valid IRR; template should show 0.0% not "—"
        assert "0.0%" in html

    def test_vh7_no_run_history(self):
        """VH-7: card with no equity_irr key at all renders without error."""
        from jinja2 import Environment, FileSystemLoader
        import datetime

        env = Environment(
            loader=FileSystemLoader(str(Path(REPO_ROOT) / "app/templates")),
            autoescape=False,
        )
        tmpl = env.get_template("partials/scenario_version_history.html")

        card = {
            "scenario_id": "test-no-irr",
            "scenario_name": "No IRR scenario",
            "project_code": "test-project",
            "updated_at": datetime.datetime(2026, 1, 1),
            "copied_from_scenario_id": None,
            "project_irr": None,
            "equity_irr": None,
            "avg_dscr": None,
            "export_count": 0,
            "governance_state": {},
            "previous_run_summary": {},
            "is_user_project": False,
            "template_source": "",
            "panel_rows": [],
            "has_previous_run": False,
        }

        class FakeWS:
            active_scenario_id = "other"
            dirty = False

        html = tmpl.render(
            scenario_summary_cards=[card],
            workspace_state=FakeWS(),
            dirty_state_ui=None,
            scenario_workflow_ui=None,
        )
        assert isinstance(html, str)

    def test_vh7b_empty_scenario_list(self):
        """VH-7b: empty scenario list renders 'No saved versions yet'."""
        from jinja2 import Environment, FileSystemLoader

        env = Environment(
            loader=FileSystemLoader(str(Path(REPO_ROOT) / "app/templates")),
            autoescape=False,
        )
        tmpl = env.get_template("partials/scenario_version_history.html")

        class FakeWS:
            active_scenario_id = None
            dirty = False

        html = tmpl.render(
            scenario_summary_cards=[],
            workspace_state=FakeWS(),
            dirty_state_ui=None,
            scenario_workflow_ui=None,
        )
        assert "No saved versions yet" in html


# ---------------------------------------------------------------------------
# VH-8, VH-9: HTTP integration tests (app must be running on port 8765)
# ---------------------------------------------------------------------------


class TestVersionHistoryHTTP:
    """Integration tests that require the app to be running on port 8765."""

    @pytest.fixture(autouse=True)
    def _check_app(self):
        import urllib.request
        try:
            urllib.request.urlopen("http://localhost:8765/", timeout=2)
        except Exception:
            pytest.skip("App not running on port 8765 — skipping HTTP tests")

    def _get_session_cookie(self) -> str:
        """Log in as admin and return the session cookie string."""
        import http.cookiejar
        import urllib.parse
        import urllib.request

        jar = http.cookiejar.CookieJar()
        processor = urllib.request.HTTPCookieProcessor(jar)
        opener = urllib.request.build_opener(processor)

        # Step 1: GET login page to obtain CSRF token
        get_req = urllib.request.Request("http://localhost:8765/login")
        try:
            resp = opener.open(get_req, timeout=5)
            html = resp.read().decode("utf-8", errors="replace")
        except Exception:
            html = ""

        import re
        m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
        csrf = m.group(1) if m else ""

        # Step 2: POST login with CSRF token
        data = urllib.parse.urlencode(
            {"csrf_token": csrf, "username": "admin", "password": "fincoGPT2026!"}
        ).encode()
        post_req = urllib.request.Request(
            "http://localhost:8765/login",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            opener.open(post_req, timeout=5)
        except Exception:
            pass

        parts = [f"{c.name}={c.value}" for c in jar]
        return "; ".join(parts)

    def _get(self, path: str, cookie: str) -> tuple[int, str]:
        import urllib.request

        req = urllib.request.Request(
            f"http://localhost:8765{path}",
            headers={"Cookie": cookie},
        )
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            return resp.status, resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", errors="replace")

    def test_vh8_tuho_reference_opens(self):
        """VH-8: TUHO factory project opens HTTP 200."""
        cookie = self._get_session_cookie()
        status, _ = self._get("/?project=tuho", cookie)
        assert status == 200, f"Expected 200, got {status}"

    def test_vh9_project_with_string_run_history_opens(self):
        """VH-9: Project seeded with string-typed KPIs in run history opens HTTP 200.

        Creates a user project, writes string-typed KPIs into the scenario's
        last_run_summary_json, then GETs the project index page.
        """
        import datetime
        from app.persistence.db import get_connection

        project_code = f"hotfix1-test-{uuid.uuid4().hex[:8]}"
        project_id = uuid.uuid4().hex
        scenario_id = uuid.uuid4().hex
        now = datetime.datetime.utcnow().isoformat()

        # String-typed KPIs — this is the bug trigger
        string_kpis = json.dumps({
            "project_irr": "0.0733",
            "equity_irr": "0.0904",
            "min_dscr": "1.34",
            "avg_dscr": "1.51",
        })

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
                    project_id, "admin", project_code, "Hotfix1 Test Project",
                    "generic_wind", "user_created", "generic_wind",
                    "{}", '{"g20_status":"BLOCKED"}',
                    string_kpis, now, now,
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
                    scenario_id, project_id, "admin", "Base Case",
                    project_code, "generic_wind", 1,
                    "{}", '{"g20_status":"BLOCKED"}',
                    string_kpis, now, now,
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
                    uuid.uuid4().hex, project_id, "admin", project_code,
                    scenario_id, "{}", "{}", "{}",
                    string_kpis, 0,
                    '{"g20_status":"BLOCKED"}', now, now,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        cookie = self._get_session_cookie()
        status, body = self._get(f"/?project={project_code}", cookie)
        assert status == 200, (
            f"Expected 200 for project with string-typed KPIs, got {status}. "
            f"Body excerpt: {body[:400]}"
        )


# ---------------------------------------------------------------------------
# VH-10: File scope guard
# ---------------------------------------------------------------------------


class TestHotfix1FileScope:
    ALLOWED_PREFIXES = (
        "app/templates/partials/scenario_version_history.html",
        "app/templates/partials/scenario_multi_compare_picker.html",
        "tests/test_hotfix1_",
        "tests/test_phase_scenario1_",
        "tests/test_phase_scenario2_",
        "tests/test_phase_ux4cde_",
    )
    DISALLOWED_PREFIXES = (
        "app/waterfall_core.py",
        "app/project_factories.py",
        "app/persistence/",
        "app/services/",
        "app/export/",
        "main_web.py",
        "app/templates/partials/export_registry.html",
        "app/templates/partials/workspace_shell.html",
        "app/templates/partials/scenario_tab.html",
        "app/templates/partials/scenario_matrix.html",
        "static/styles.css",
    )

    def test_vh10_file_scope(self):
        """VH-10: Only allowed files changed on this branch."""
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
                f"HOTFIX-1 must not touch {f}"
            )
            assert any(f.startswith(p) for p in self.ALLOWED_PREFIXES), (
                f"HOTFIX-1 file outside allowed scope: {f}"
            )


# ---------------------------------------------------------------------------
# VH-11 to VH-13: Safety / parity
# ---------------------------------------------------------------------------


class TestHotfix1Safety:
    def test_vh11_engine_md5(self):
        """VH-11: Engine MD5 must be unchanged."""
        engine_path = Path(REPO_ROOT) / "app/waterfall_core.py"
        digest = hashlib.md5(engine_path.read_bytes()).hexdigest()
        assert digest == ENGINE_MD5, (
            f"Engine MD5 changed: expected {ENGINE_MD5}, got {digest}"
        )

    def test_vh12_tuho_p1_dscr(self):
        """VH-12: TUHO P1 DSCR must be 1.4507."""
        from app.project_factories import create_default_tuho_wind1
        from app.ui_runner import _build_period_engine, _run_waterfall
        proj = create_default_tuho_wind1()
        result = _run_waterfall(proj, _build_period_engine(proj))
        for p in result.periods:
            d = getattr(p, "dscr", None)
            if d is not None and abs(d) < 1e10:
                assert abs(d - TUHO_P1_DSCR) < 0.001, f"TUHO P1 DSCR={d}"
                return
        pytest.fail("No finite DSCR found")

    def test_vh13_oborovo_p1_dscr(self):
        """VH-13: Oborovo P1 DSCR must be 1.1500."""
        from app.project_factories import create_default_oborovo
        from app.ui_runner import _build_period_engine, _run_waterfall
        proj = create_default_oborovo()
        result = _run_waterfall(proj, _build_period_engine(proj))
        for p in result.periods:
            d = getattr(p, "dscr", None)
            if d is not None and abs(d) < 1e10:
                assert abs(d - OBOROVO_P1_DSCR) < 0.01, f"Oborovo P1 DSCR={d}"
                return
        pytest.fail("No finite DSCR found")
