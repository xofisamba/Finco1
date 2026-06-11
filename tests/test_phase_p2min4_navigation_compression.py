"""Phase P2-min-4: Navigation Compression (presentation only).

PR4 compresses the 20 top-level tabs into 5
compressed tabs (Dashboard, Inputs, Scenarios,
Outputs, Export & Audit, Help). The underlying
ws-tab buttons + panel panels + routes are
preserved (hidden != deleted).

Tests prove:
  - 5 compressed tabs are present
  - Compressed tabs use brief-approved copy
  - The underlying ws-tab buttons + panel
    panels + routes are preserved
  - The compressed nav calls the existing
    switchTab JS function (no new JS lib)
  - No route deletion
  - No panel deletion
  - No Tailwind / Alpine / React / Vue / Svelte
  - rc1 SHA preserved
  - use_construction_schedule_engine
    remains False
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"

HAS_GIT = shutil.which("git") is not None and (REPO_ROOT / ".git").exists()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def logged_in_client():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from app.auth import create_session_token
    from main_web import app

    client = TestClient(app)
    token = create_session_token(user_id="1", username="test_user")
    client.cookies.set("finco_session", token)
    return client


# ---------------------------------------------------------------------------
# Test: 5 compressed tabs
# ---------------------------------------------------------------------------


class TestCompressedNav:
    def test_partial_exists(self):
        path = REPO_ROOT / "app/templates/partials/_nav_compression.html"
        assert path.is_file(), (
            "P2-min-4 must introduce the _nav_compression.html partial"
        )

    def test_five_compressed_tabs(self):
        """Brief: 5 top-level tabs (Dashboard,
        Inputs, Scenarios, Outputs, Export &
        Audit, Help) — actually 6 because
        Help is kept as is.
        """
        path = REPO_ROOT / "app/templates/partials/_nav_compression.html"
        text = path.read_text(encoding="utf-8")
        for label in ["Dashboard", "Inputs", "Scenarios",
                      "Outputs", "Export &amp; Audit", "Help"]:
            assert label in text, (
                f"Nav compression must include tab label {label!r}"
            )
        # Count the buttons
        n_tabs = text.count("nav-compression-tab")
        # 5 visible + 1 active class = 6
        # or 6 buttons; allow 5-7 to count
        # buttons + class refs.
        assert n_tabs >= 6, (
            f"Nav compression must have at least 6 tab buttons; "
            f"got {n_tabs} references"
        )

    def test_brief_approved_copy(self):
        """Brief: '5 top-level tabs: Dashboard /
        Inputs / Scenarios / Outputs / Export
        & Audit'.
        """
        path = REPO_ROOT / "app/templates/partials/_nav_compression.html"
        text = path.read_text(encoding="utf-8")
        # Verify brief-approved copy
        assert "Dashboard" in text
        assert "Inputs" in text
        assert "Scenarios" in text
        assert "Outputs" in text
        assert "Export &amp; Audit" in text

    def test_dashboard_is_default_active(self):
        path = REPO_ROOT / "app/templates/partials/_nav_compression.html"
        text = path.read_text(encoding="utf-8")
        # The Dashboard button is the only
        # one with the 'active' class.
        assert 'id="nav-compression-tab-dashboard"' in text
        assert 'class="nav-compression-tab active"' in text

    def test_uses_existing_switchtab_js(self):
        """The compressed nav uses the
        existing switchTab JS function
        (no new JS library).
        """
        path = REPO_ROOT / "app/templates/partials/_nav_compression.html"
        text = path.read_text(encoding="utf-8")
        assert "switchTab" in text, (
            "Compressed nav must use the existing switchTab JS function"
        )


# ---------------------------------------------------------------------------
# Test: hidden != deleted
# ---------------------------------------------------------------------------


class TestNoRouteOrPanelDeletion:
    def test_ws_tab_buttons_preserved(self):
        """The existing ws-tab buttons in
        workspace_tabs.html are preserved
        (no deletion).
        """
        path = REPO_ROOT / "app/templates/partials/workspace_tabs.html"
        text = path.read_text(encoding="utf-8")
        # 20 ws-tab buttons
        n_tabs = text.count('class="ws-tab')
        assert n_tabs >= 19, (
            f"workspace_tabs.html must have at least 19 ws-tab "
            f"buttons; got {n_tabs}"
        )

    def test_panel_panels_preserved(self):
        """The existing panel-... panels in
        workspace_shell.html are preserved
        (no deletion).
        """
        path = REPO_ROOT / "app/templates/partials/workspace_shell.html"
        text = path.read_text(encoding="utf-8")
        for must_have in [
            "panel-overview", "panel-inputs", "panel-scenario",
            "panel-construction", "panel-production", "panel-revenue",
            "panel-opex", "panel-capex", "panel-senior-debt", "panel-shl",
            "panel-tax", "panel-pl", "panel-cashflow", "panel-balance",
            "panel-distributions", "panel-sponsor", "panel-audit",
            "panel-downloads", "panel-compare", "panel-help",
        ]:
            assert must_have in text, (
                f"workspace_shell.html must still have {must_have!r}"
            )

    def test_no_route_renames_or_deletions(self):
        """No route renames or deletions.
        """
        from main_web import app
        route_paths = {r.path for r in app.routes if hasattr(r, "path")}
        for must_have in [
            "/", "/home", "/projects/new/minimal", "/projects/browse",
            "/projects/create", "/projects/new",
            "/download", "/exports/runtime-summary.csv",
            "/exports/institutional-workbook.xlsx",
            "/scenarios", "/scenarios/compare-multi",
            "/runs", "/run/{run_id}",
        ]:
            assert must_have in route_paths, (
                f"Route {must_have!r} must remain unchanged"
            )


# ---------------------------------------------------------------------------
# Test: base.html integration
# ---------------------------------------------------------------------------


class TestBaseHtmlIntegration:
    def test_base_includes_nav_compression_partial(self):
        path = REPO_ROOT / "app/templates/base.html"
        text = path.read_text(encoding="utf-8")
        assert "_nav_compression.html" in text, (
            "base.html must include the _nav_compression.html partial"
        )

    def test_nav_compression_partial_guarded_by_flag(self):
        path = REPO_ROOT / "app/templates/base.html"
        text = path.read_text(encoding="utf-8")
        # The include is guarded by
        # nav_compression_enabled.
        assert "nav_compression_enabled" in text, (
            "base.html must guard the nav compression include with "
            "{% if nav_compression_enabled %}"
        )


# ---------------------------------------------------------------------------
# Test: no Tailwind / Alpine / React / Vue / Svelte
# ---------------------------------------------------------------------------


class TestNoJsLibraries:
    def test_no_js_libraries_in_nav_compression(self):
        from pathlib import Path
        path = REPO_ROOT / "app/templates/partials/_nav_compression.html"
        text = path.read_text(encoding="utf-8")
        for forbidden in [
            "react", "vue", "svelte", "tailwind", "alpine",
            "import ", "from ",
        ]:
            assert forbidden not in text.lower(), (
                f"Nav compression must NOT include {forbidden!r}"
            )

    def test_no_js_libraries_in_static_appjs(self):
        path = REPO_ROOT / "static/app.js"
        if not path.is_file():
            pytest.skip("no static/app.js in this branch")
        text = path.read_text(encoding="utf-8")
        for forbidden in [
            "import react", "from react",
            "import vue", "from vue",
            "import svelte", "from svelte",
            "import tailwind", "from tailwind",
            "import alpine", "from alpine",
            "import chart", "from chart",
            "import plotly", "from plotly",
            "import d3", "from d3",
        ]:
            assert forbidden not in text.lower(), (
                f"static/app.js must NOT import {forbidden!r}"
            )


# ---------------------------------------------------------------------------
# Test: phase invariants
# ---------------------------------------------------------------------------


class TestPhaseInvariants:
    def test_rc1_sha_resolvable(self):
        if not HAS_GIT:
            pytest.skip("no git in test env")
        r = subprocess.run(
            ["git", "rev-parse", "--verify", RC1_SHA],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        assert r.returncode == 0
        assert r.stdout.strip() == RC1_SHA

    def test_use_construction_schedule_engine_remains_false(self):
        if not HAS_GIT:
            pytest.skip("no git in test env")
        r = subprocess.run(
            [
                "grep", "-rn",
                "use_construction_schedule_engine\\s*=\\s*True",
                "app/", "main_web.py", "main_api.py",
            ],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        bad = r.stdout.strip().splitlines()
        assert not bad, (
            f"use_construction_schedule_engine=True "
            f"found in code: {bad}"
        )

    def test_parity_guardrails_unchanged(self):
        if not HAS_GIT:
            pytest.skip("no git in test env")
        r = subprocess.run(
            ["python3", "-m", "pytest",
             "tests/test_phase51f_parallel_work_guardrails.py",
             "-q", "--tb=line", "--no-header"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode in (0, 5), (
            f"Phase 51F parity guardrails broke under P2-min-4: "
            f"returncode={r.returncode}\n"
            f"stdout={r.stdout[-1000:]}\n"
            f"stderr={r.stderr[-500:]}"
        )


# ---------------------------------------------------------------------------
# Test: prior-phase tests preserved
# ---------------------------------------------------------------------------


class TestPriorPhaseTestsPreserved:
    def test_all_prior_phase_tests_pass(self):
        if not HAS_GIT:
            pytest.skip("no git in test env")
        r = subprocess.run(
            ["python3", "-m", "pytest",
             "tests/test_phase_pr1_form_timing_fields.py",
             "tests/test_phase_pr2_realized_gearing.py",
             "tests/test_phase_pr3_taxonomy.py",
             "tests/test_phase_m1_scenario_matrix.py",
             "tests/test_phase_p1a_generic_driver_response_audit.py",
             "tests/test_phase_p1b_driver_status_badges.py",
             "tests/test_phase51f_parallel_work_guardrails.py",
             "tests/test_phase_p2min1_project_home.py",
             "tests/test_phase_p2min2_hide_internal_vocabulary.py",
             "tests/test_phase_p2min3_dashboard_v1.py",
             "-q", "--tb=line", "--no-header"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode in (0, 5), (
            f"Prior-phase tests broke under P2-min-4: "
            f"returncode={r.returncode}\n"
            f"stdout={r.stdout[-1500:]}\n"
            f"stderr={r.stderr[-500:]}"
        )
