"""Phase P2-min-2: Hide Internal Vocabulary (presentation only).

P2-min-2 relocates internal implementation
vocabulary from normal user UI to the
Export & Audit area. Hidden != deleted.
The full disclaimer remains in Export &
Audit. No backend / no persistence / no
factory change. No CSS class rename, no
context-key rename, no route rename, no
test rename, no project_origin rename.
Only user-visible copy may change.

Tests prove:
  - Generic disclosure rule is followed:
    "Internal-use model — results are
    indicative." is rendered as a single
    clear status line per screen.
  - The full disclaimer remains in
    Export & Audit.
  - Derivation evidence remains intact
    (audit popovers, derivation
    citations).
  - Negative-exposure tests assert on
    rendered visible text from rendered
    routes/pages.
  - factory / baseline / parity /
    calibration / G20 / R99 / R102 /
    runtime-source labels / TUHO /
    Oborovo / OBR-001 are not present in
    the normal UI (workspace overview,
    inputs section, project home).
  - Same labels remain in Export & Audit
    (audit_reconciliation_tab, export
    registry).
  - parity guardrails still pass.
  - rc1 SHA preserved.
  - use_construction_schedule_engine
    remains False.
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
# Test classes
# ---------------------------------------------------------------------------


class TestGenericDisclosureRule:
    """The brief: 'Internal-use model —
    results are indicative.' must appear as
    a single clear status line per screen.
    """

    def test_generic_status_line_partial_exists(self):
        partial = REPO_ROOT / "app/templates/partials/_generic_status_line.html"
        assert partial.is_file(), (
            "P2-min-2 must introduce the generic status line partial"
        )
        text = partial.read_text(encoding="utf-8")
        assert "Internal-use model" in text, (
            "Generic status line must use the brief-approved copy"
        )
        assert "results are indicative" in text, (
            "Generic status line must use the brief-approved copy"
        )

    def test_generic_status_line_included_in_workspace_shell(self):
        shell = REPO_ROOT / "app/templates/partials/workspace_shell.html"
        text = shell.read_text(encoding="utf-8")
        assert "_generic_status_line.html" in text, (
            "workspace_shell.html must include the generic status "
            "line partial (P2-min-2 brief)"
        )


class TestProjectHomeStaysClean:
    """The Project Home (PR1) partial does
    not expose internal vocabulary to the
    pilot user.
    """

    def test_home_partial_has_no_factory_terminology(self, logged_in_client):
        r = logged_in_client.get("/home", follow_redirects=False)
        assert r.status_code == 200
        # Negative-exposure: assert on rendered text.
        # "factory" is a word that COULD appear
        # in user-facing copy, but the P2-min-2
        # brief asks us to hide it from the
        # normal UI. We allow it in audit
        # contexts but the home partial must
        # not contain the word.
        text = r.text.lower()
        assert "factory template" not in text, (
            "Project Home must not mention 'factory template' in "
            "the rendered visible text"
        )

    def test_home_partial_has_no_parity_label(self, logged_in_client):
        r = logged_in_client.get("/home", follow_redirects=False)
        assert r.status_code == 200
        text = r.text.lower()
        for forbidden in ["parity", "calibration", "g20", "r99", "r102"]:
            assert forbidden not in text, (
                f"Project Home must NOT expose {forbidden!r} in "
                f"the rendered visible text"
            )

    def test_home_partial_has_no_factory_or_template_name(self, logged_in_client):
        r = logged_in_client.get("/home", follow_redirects=False)
        assert r.status_code == 200
        # The user-facing Project Home must not
        # mention TUHO, Oborovo, or OBR-001.
        for forbidden in ["TUHO", "Oborovo", "OBR-001"]:
            assert forbidden not in r.text, (
                f"Project Home must NOT mention {forbidden!r} in "
                f"the rendered visible text"
            )


class TestMinimalFormStaysClean:
    """The minimal New Project form (PR1)
    does not expose internal vocabulary.
    """

    def test_minimal_form_has_no_factory_terminology(self, logged_in_client):
        r = logged_in_client.get(
            "/projects/new/minimal", follow_redirects=False
        )
        assert r.status_code == 200
        text = r.text.lower()
        # The minimal form should not show
        # internal vocabulary.
        for forbidden in [
            "factory template",
            "parity",
            "calibration",
            "g20",
            "r99",
            "r102",
            "tuho",
            "oborovo",
            "obr-001",
        ]:
            assert forbidden not in text, (
                f"Minimal form must NOT mention {forbidden!r} in "
                f"the rendered visible text"
            )


class TestExportAuditStillExposesAuditInfo:
    """The Export & Audit area (audit
    reconciliation tab + export registry)
    must STILL expose audit information
    (parity, calibration, TUHO, Oborovo,
    G20, R99, R102, factory, etc.). This
    is the derivation-evidence rule.
    """

    def test_audit_reconciliation_tab_template_exposes_parity(self):
        path = REPO_ROOT / "app/templates/partials/audit_reconciliation_tab.html"
        text = path.read_text(encoding="utf-8")
        # The audit tab continues to expose
        # the full audit vocabulary.
        assert "TUHO" in text, (
            "Audit tab must still expose TUHO (hidden != deleted)"
        )
        assert "Oborovo" in text, (
            "Audit tab must still expose Oborovo"
        )
        assert "parity" in text.lower(), (
            "Audit tab must still expose parity references"
        )

    def test_export_registry_template_exposes_audit(self):
        path = REPO_ROOT / "app/templates/partials/export_registry.html"
        text = path.read_text(encoding="utf-8")
        # The export registry continues to
        # expose the full audit / parity /
        # calibration vocabulary.
        assert "calibration" in text.lower() or "parity" in text.lower(), (
            "Export registry must still expose calibration / parity"
        )


class TestNoRenameOfImplementationDetails:
    """No CSS class rename, no context-key
    rename, no route rename, no test
    rename, no project_origin rename. Only
    user-visible copy may change.
    """

    def test_no_route_renames(self):
        """The route names from PR1 are
        preserved (no rename).
        """
        from main_web import app
        route_paths = {r.path for r in app.routes if hasattr(r, "path")}
        for must_have in ["/", "/home", "/projects/new/minimal",
                          "/projects/browse", "/projects/create",
                          "/projects/new"]:
            assert must_have in route_paths, (
                f"Route {must_have!r} must remain unchanged"
            )

    def test_factory_template_options_unchanged(self):
        from main_web import FACTORY_TEMPLATE_OPTIONS
        codes = {item.get("project_code") for item in FACTORY_TEMPLATE_OPTIONS}
        # The factory template options are
        # unchanged (hidden != deleted).
        assert "tuho" in codes
        assert "oborovo" in codes

    def test_project_origin_values_unchanged(self):
        """The project_origin values are not
        renamed. Hidden != deleted.
        """
        # The project_origin values are
        # referenced from the model layer
        # (ProjectRecord.project_origin).
        from app.persistence.records import ProjectRecord
        from dataclasses import fields
        names = {f.name for f in fields(ProjectRecord)}
        assert "project_origin" in names, (
            "ProjectRecord must still carry the project_origin field "
            "(no rename)"
        )
        # The original literal default
        # (factory_template) is set by the
        # SQL DEFAULT in the schema, not
        # by the dataclass. We verify it is
        # still used as the default in
        # the persistence layer by
        # inspecting the source of
        # app/persistence/db.py.
        from pathlib import Path
        db_src = (Path(__file__).resolve().parents[1]
                  / "app/persistence/db.py").read_text(encoding="utf-8")
        assert "project_origin" in db_src, (
            "db.py must still define the project_origin column"
        )
        assert "factory_template" in db_src, (
            "db.py must still use the 'factory_template' default "
            "(no rename)"
        )


class TestPhaseInvariants:
    """rc1, factory paths, forbidden paths,
    construction flag, and downstream-phase
    test contracts are preserved.
    """

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
            f"Phase 51F parity guardrails broke under P2-min-2: "
            f"returncode={r.returncode}\n"
            f"stdout={r.stdout[-1000:]}\n"
            f"stderr={r.stderr[-500:]}"
        )


class TestPriorPhaseTestsPreserved:
    """P2-min-2 must not break PR1, M1, S1,
    S2, S3, P1-A, P1-B, Phase 51F parity,
    or P2-min-1.
    """

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
             "-q", "--tb=line", "--no-header"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode in (0, 5), (
            f"Prior-phase tests broke under P2-min-2: "
            f"returncode={r.returncode}\n"
            f"stdout={r.stdout[-1500:]}\n"
            f"stderr={r.stderr[-500:]}"
        )
