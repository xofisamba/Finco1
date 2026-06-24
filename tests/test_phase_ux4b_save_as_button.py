"""UX-4B: Create Working Copy button visibility tests.

Problem: _state_banner.html gated the "Create editable copy" button
behind ``audit_mode``. In normal mode users saw text telling them to
"use Save As" but no actionable button existed.

Fix: remove ``audit_mode and`` from the banner button condition.
Button now shows for protected references (TUHO, Oborovo) in all modes.
Route: POST /projects/{code}/confirm-first-edit-copy (reuses existing
copy; returns 400 for non-protected projects — safe gate).

Tests:
  A1. Banner source: button condition no longer requires audit_mode.
  A2. Banner source: button POSTs to confirm-first-edit-copy route.
  A3. Banner source: button label is "Create Working Copy".
  A4. Banner source: button still gated on is_protected_reference.
  A5. Banner source: button still gated on not is_user_project.
  B1. Template renders button for protected reference (TUHO-like context).
  B2. Template does NOT render button for user project.
  B3. Template does NOT render button for generic (non-protected) template.
  C1. scenario_tab.html wording consistent: no "Save As" in read-only subtitle.
  D1. Engine MD5 unchanged.
  D2. TUHO P1 DSCR unchanged.
  D3. Oborovo P1 DSCR unchanged.
  E1. File scope guard.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
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

_BANNER_PATH = Path(REPO_ROOT) / "app/templates/partials/_state_banner.html"
_SCENARIO_TAB_PATH = Path(REPO_ROOT) / "app/templates/partials/scenario_tab.html"


# ---------------------------------------------------------------------------
# A. Source inspection
# ---------------------------------------------------------------------------

class TestBannerSource:
    def _src(self):
        return _BANNER_PATH.read_text()

    def test_button_not_gated_on_audit_mode(self):
        src = self._src()
        # The old gate was: audit_mode and _ctx == 'factory_template' ...
        assert "audit_mode and _ctx == 'factory_template'" not in src, (
            "Button must not be gated on audit_mode"
        )

    def test_button_posts_to_confirm_first_edit_copy(self):
        src = self._src()
        assert "confirm-first-edit-copy" in src, (
            "Button must POST to confirm-first-edit-copy route"
        )

    def test_button_label_is_create_working_copy(self):
        src = self._src()
        assert "Create Working Copy" in src, (
            "Button label must be 'Create Working Copy'"
        )

    def test_button_gated_on_is_protected_reference(self):
        src = self._src()
        assert "is_protected_reference" in src, (
            "Button must still be gated on is_protected_reference"
        )

    def test_button_gated_on_not_is_user_project(self):
        src = self._src()
        assert "not is_user_project" in src, (
            "Button must still be gated on not is_user_project"
        )


# ---------------------------------------------------------------------------
# B. Template rendering
# ---------------------------------------------------------------------------

def _render_banner(*, banner_context, is_protected_reference, is_user_project,
                   active_project_code="tuho", audit_mode=False):
    from jinja2 import Environment, FileSystemLoader
    env = Environment(
        loader=FileSystemLoader(str(Path(REPO_ROOT) / "app/templates")),
    )
    tpl = env.get_template("partials/_state_banner.html")
    ctx = {
        "banner_context": banner_context,
        "banner_tone": "info",
        "is_protected_reference": is_protected_reference,
        "is_user_project": is_user_project,
        "active_project_code": active_project_code,
        "audit_mode": audit_mode,
    }
    return tpl.render(**ctx)


class TestBannerRendering:
    def test_renders_button_for_protected_reference(self):
        """TUHO-like context: protected reference, not user project → button visible."""
        html = _render_banner(
            banner_context="factory_template",
            is_protected_reference=True,
            is_user_project=False,
            active_project_code="tuho",
            audit_mode=False,
        )
        assert "Create Working Copy" in html, (
            "Button must render for protected reference in normal mode"
        )
        assert "confirm-first-edit-copy" in html

    def test_no_button_for_user_project(self):
        """User-owned copy: button must not render."""
        html = _render_banner(
            banner_context="factory_template",
            is_protected_reference=True,
            is_user_project=True,
            active_project_code="tuho-copy",
            audit_mode=False,
        )
        assert "Create Working Copy" not in html

    def test_no_button_for_generic_template(self):
        """Generic Solar/Wind: not protected reference → button must not render."""
        html = _render_banner(
            banner_context="factory_template",
            is_protected_reference=False,
            is_user_project=False,
            active_project_code="generic-solar",
            audit_mode=False,
        )
        assert "Create Working Copy" not in html

    def test_renders_button_without_audit_mode(self):
        """Normal mode (audit_mode=False) must show button for protected reference."""
        html_normal = _render_banner(
            banner_context="factory_template",
            is_protected_reference=True,
            is_user_project=False,
            audit_mode=False,
        )
        html_audit = _render_banner(
            banner_context="factory_template",
            is_protected_reference=True,
            is_user_project=False,
            audit_mode=True,
        )
        assert "Create Working Copy" in html_normal, "Button must show in normal mode"
        assert "Create Working Copy" in html_audit, "Button must still show in audit mode"


# ---------------------------------------------------------------------------
# C. scenario_tab.html wording
# ---------------------------------------------------------------------------

class TestScenarioTabWording:
    def test_no_save_as_in_read_only_subtitle(self):
        src = _SCENARIO_TAB_PATH.read_text()
        # Find the read-only subtitle block
        idx = src.find("Protected projects cannot add scenarios")
        assert idx >= 0, "Read-only subtitle text not found"
        line = src[idx:src.find("\n", idx)]
        assert "Save As" not in line, (
            f"Read-only subtitle should not say 'Save As'; got: {line!r}"
        )
        assert "Create Working Copy" in line, (
            f"Read-only subtitle should say 'Create Working Copy'; got: {line!r}"
        )


# ---------------------------------------------------------------------------
# D. Parity
# ---------------------------------------------------------------------------

class TestUX4BParity:
    def test_engine_md5_unchanged(self):
        digest = hashlib.md5(
            (Path(REPO_ROOT) / "app/waterfall_core.py").read_bytes()
        ).hexdigest()
        assert digest == ENGINE_MD5, f"waterfall_core.py changed: {digest}"

    def test_tuho_p1_dscr_unchanged(self):
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

    def test_oborovo_p1_dscr_unchanged(self):
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


# ---------------------------------------------------------------------------
# E. File scope guard
# ---------------------------------------------------------------------------

class TestUX4BFileScope:
    ALLOWED_PREFIXES = (
        "app/templates/partials/new_project_minimal.html",  # UX-2E cross-arc
        "app/templates/partials/workspace_shell.html",  # UX-2E cross-arc
        "tests/",  # UX-2E cross-arc (branch-wide test footprint)
        "tests/test_phase56",  # UX-2E cross-arc
        "app/templates/partials/_state_banner.html",
        "app/templates/partials/scenario_tab.html",
        "tests/test_phase_ux4b_",
        # Allow prior phase test files that scope-guard may update
        "tests/test_phase_scenario1_",
        "tests/test_phase_scenario2_",
        "tests/test_phase_ux4a_",
        "tests/test_phase_stab",
        "tests/test_phase_pr1_",
        "tests/test_phase_pr2_",
        "tests/test_phase_pr3_",
        "tests/test_phase_m1_",
    )
    DISALLOWED_PREFIXES = (
        "app/waterfall_core.py",
        "app/project_factories.py",
        "app/persistence/",
        "app/export/",
        "static/",
    )

    def test_file_scope(self):
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
                f"UX-4B must not touch {f}"
            )
            assert any(f.startswith(p) for p in self.ALLOWED_PREFIXES), (
                f"UX-4B file outside allowed scope: {f}"
            )
