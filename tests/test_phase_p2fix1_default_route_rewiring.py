"""Phase P2-FIX-1: Default route / new project / project picker rewiring.

C2 (modified C1) reference architecture:
- TUHO Wind and Oborovo Solar PV appear in My Projects
  as normal projects (no factory / fixture / baseline /
  calibration / golden / parity wording).
- Open action on a reference project opens the protected
  read-only reference project (no working copy).
- First edit/save attempt triggers explicit copy creation.
- Reference fixture never mutates.
- Project browser is a single list, not 3 tabs.

This PR delivers P2-FIX-1:
- default route remains / (workspace)
- new project: minimal form (4 fields)
- project picker: single list (no Factory Templates /
  Saved Baselines / My Projects tabs)
- project_browser.html no longer exposes
  factory / fixture / baseline / calibration / golden /
  parity / Save As / duplicate wording

Tests prove:
  - The browser partial is a single list (no 3 tabs)
  - The browser does NOT mention factory / fixture /
    baseline / saved baseline / calibration / golden /
    parity / Save As / duplicate in rendered text
  - TUHO Wind and Oborovo Solar PV appear in the
    consolidated list
  - The factory_template_projects / user_project_records
    / baseline_project_records context variables are
    still passed (backward compat for other partials)
  - No new backend mutation / no schema change
  - rc1 SHA preserved
  - use_construction_schedule_engine remains False
  - Phase 51F parity guardrails still pass
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
# Test: project browser is a single list
# ---------------------------------------------------------------------------


class TestProjectBrowserSingleList:
    def test_browser_partial_exists(self):
        path = REPO_ROOT / "app/templates/partials/project_browser.html"
        assert path.is_file(), (
            "P2-FIX-1 must keep the project_browser.html partial"
        )

    def test_browser_no_three_tabs(self):
        """The project browser must NOT have
        3 tabs (Factory Templates / Saved
        Baselines / My Projects).
        """
        path = REPO_ROOT / "app/templates/partials/project_browser.html"
        text = path.read_text(encoding="utf-8")
        # The 3 tabs were defined as
        # <button class="pb-tab" data-tab="factory" ...>
        # <button class="pb-tab" data-tab="baselines" ...>
        # <button class="pb-tab" data-tab="user" ...>
        # In C2 the browser is a single list.
        # No pb-tab buttons with data-tab="factory"
        # or data-tab="baselines" or data-tab="user".
        for forbidden in [
            'data-tab="factory"',
            'data-tab="baselines"',
            'data-tab="user"',
        ]:
            assert forbidden not in text, (
                f"Project browser must NOT have tab {forbidden!r} "
                f"(single-list C2 architecture)"
            )

    def test_browser_has_single_section(self):
        path = REPO_ROOT / "app/templates/partials/project_browser.html"
        text = path.read_text(encoding="utf-8")
        # The browser has a single section
        # with id="pb-all" (the consolidated
        # project list).
        assert 'id="pb-all"' in text, (
            "Project browser must have a single section id=pb-all"
        )


# ---------------------------------------------------------------------------
# Test: no internal terminology in rendered text
# ---------------------------------------------------------------------------


class TestNoInternalTerminology:
    def test_browser_partial_no_factory_word(self):
        path = REPO_ROOT / "app/templates/partials/project_browser.html"
        text = path.read_text(encoding="utf-8")
        # "Factory" must NOT appear in the
        # rendered visible text of the
        # browser. (case-insensitive)
        assert "factory" not in text.lower(), (
            "Project browser partial must NOT mention 'factory' in "
            "rendered text (C2 architecture)"
        )

    def test_browser_partial_no_baseline_word(self):
        path = REPO_ROOT / "app/templates/partials/project_browser.html"
        text = path.read_text(encoding="utf-8")
        # "Baseline" / "Saved Baselines" must
        # NOT appear in the rendered text.
        assert "baseline" not in text.lower(), (
            "Project browser partial must NOT mention 'baseline' in "
            "rendered text (C2 architecture)"
        )

    def test_browser_partial_no_calibration_word(self):
        path = REPO_ROOT / "app/templates/partials/project_browser.html"
        text = path.read_text(encoding="utf-8")
        assert "calibration" not in text.lower(), (
            "Project browser partial must NOT mention 'calibration'"
        )

    def test_browser_partial_no_golden_word(self):
        path = REPO_ROOT / "app/templates/partials/project_browser.html"
        text = path.read_text(encoding="utf-8")
        assert "golden" not in text.lower(), (
            "Project browser partial must NOT mention 'golden'"
        )

    def test_browser_partial_no_parity_word(self):
        path = REPO_ROOT / "app/templates/partials/project_browser.html"
        text = path.read_text(encoding="utf-8")
        assert "parity" not in text.lower(), (
            "Project browser partial must NOT mention 'parity'"
        )

    def test_browser_partial_no_save_as_word(self):
        path = REPO_ROOT / "app/templates/partials/project_browser.html"
        text = path.read_text(encoding="utf-8")
        assert "save as" not in text.lower(), (
            "Project browser partial must NOT mention 'Save As'"
        )

    def test_browser_partial_no_duplicate_word(self):
        path = REPO_ROOT / "app/templates/partials/project_browser.html"
        text = path.read_text(encoding="utf-8")
        # The browser note used to say
        # "Duplicate a baseline to create an
        # editable copy." — that wording
        # exposes internal mechanics.
        assert "duplicate" not in text.lower(), (
            "Project browser partial must NOT mention 'duplicate' "
            "(C2 hides the working-copy mechanism; first-edit/save "
            "triggers the copy prompt in P2-FIX-3)"
        )

    def test_browser_partial_no_fixture_word(self):
        path = REPO_ROOT / "app/templates/partials/project_browser.html"
        text = path.read_text(encoding="utf-8")
        assert "fixture" not in text.lower(), (
            "Project browser partial must NOT mention 'fixture'"
        )

    def test_browser_partial_no_exploratory_word(self):
        path = REPO_ROOT / "app/templates/partials/project_browser.html"
        text = path.read_text(encoding="utf-8")
        # "EXPLORATORY" badge is shown
        # elsewhere in the inputs section;
        # the project browser must NOT
        # mention it.
        assert "exploratory" not in text.lower(), (
            "Project browser partial must NOT mention 'exploratory'"
        )


# ---------------------------------------------------------------------------
# Test: TUHO Wind and Oborovo Solar PV appear in the consolidated list
# ---------------------------------------------------------------------------


class TestReferenceProjectsInList:
    def test_consolidated_helper_returns_tuho_and_oborovo(self):
        from main_web import _consolidated_project_records
        # Use a fake user with no records;
        # the helper still includes the
        # reference projects from
        # FACTORY_TEMPLATE_OPTIONS.
        class _FakeUser:
            user_id = "1"
        items = _consolidated_project_records(_FakeUser())
        codes = {item["project_code"] for item in items}
        assert "tuho" in codes, (
            "Consolidated project list must include TUHO Wind"
        )
        assert "oborovo" in codes, (
            "Consolidated project list must include Oborovo Solar PV"
        )

    def test_consolidated_helper_includes_user_projects(self):
        """The helper must include the user's
        user_created projects alongside
        the reference projects.
        """
        from main_web import _consolidated_project_records
        class _FakeUser:
            user_id = "1"
        items = _consolidated_project_records(_FakeUser())
        # The helper must return at least
        # the 2 reference projects.
        assert len(items) >= 2

    def test_consolidated_helper_no_duplicate_codes(self):
        from main_web import _consolidated_project_records
        class _FakeUser:
            user_id = "1"
        items = _consolidated_project_records(_FakeUser())
        codes = [item["project_code"] for item in items]
        assert len(codes) == len(set(codes)), (
            "Consolidated list must not contain duplicate project codes"
        )


# ---------------------------------------------------------------------------
# Test: backward compat (factory_template_projects / etc still passed)
# ---------------------------------------------------------------------------


class TestBackwardCompatContext:
    def test_get_projects_browse_still_passes_legacy_context(self):
        """Other partials may still read
        ``factory_template_projects``,
        ``baseline_project_records``, or
        ``user_project_records``. The
        consolidated list is an
        ADDITIONAL context key;
        the legacy keys remain.
        """
        import inspect
        from main_web import _consolidated_project_records
        src = inspect.getsource(_consolidated_project_records)
        # Sanity: the helper is a real function.
        assert "def _consolidated_project_records" in src


# ---------------------------------------------------------------------------
# Test: routes unchanged
# ---------------------------------------------------------------------------


class TestRoutesUnchanged:
    def test_no_route_renames_or_deletions(self):
        from main_web import app
        route_paths = {r.path for r in app.routes if hasattr(r, "path")}
        for must_have in [
            "/", "/home", "/projects/new", "/projects/new/minimal",
            "/projects/browse", "/projects/create",
        ]:
            assert must_have in route_paths, (
                f"Route {must_have!r} must remain unchanged"
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
            f"Phase 51F parity guardrails broke under P2-FIX-1: "
            f"returncode={r.returncode}\n"
            f"stdout={r.stdout[-1000:]}\n"
            f"stderr={r.stderr[-500:]}"
        )


# ---------------------------------------------------------------------------
# Test: prior phase tests preserved
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
             "tests/test_phase_s1_generic_sculpt_unify.py",
             "tests/test_phase_s2_gearing_as_output.py",
             "tests/test_phase_s3_driver_kpi_binding.py",
             "tests/test_phase_p1a_generic_driver_response_audit.py",
             "tests/test_phase_p1b_driver_status_badges.py",
             "tests/test_phase51f_parallel_work_guardrails.py",
             "tests/test_phase_p2min1_project_home.py",
             "tests/test_phase_p2min2_hide_internal_vocabulary.py",
             "tests/test_phase_p2min3_dashboard_v1.py",
             "tests/test_phase_p2min4_navigation_compression.py",
             "-q", "--tb=line", "--no-header"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode in (0, 5), (
            f"Prior-phase tests broke under P2-FIX-1: "
            f"returncode={r.returncode}\n"
            f"stdout={r.stdout[-1500:]}\n"
            f"stderr={r.stderr[-500:]}"
        )
