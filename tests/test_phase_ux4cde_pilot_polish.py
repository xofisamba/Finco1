"""UX-4C / UX-4D / UX-4E: Pilot polish tests.

UX-4C: Downloads tab — dead anchors disabled, "Coming Soon" shown.
UX-4D: Scenario edit popup — friendly field labels instead of raw names.
UX-4E: Developer-facing labels removed (M1 PROTOTYPE, M2 LIVE, Use→Activate).

Tests:
  C1. Dead download anchors removed (no href="#download-*" in export_registry.html).
  C2. Disabled cards have aria-disabled="true".
  C3. Disabled cards show "Coming Soon".
  C4. Disabled cards have tooltip (title attribute).
  C5. Working download links preserved (institutional-workbook, runtime-summary).
  C6. Export registry title does not say "Phase 10".
  D1. startScenarioEdit uses .sc-td--label text, not raw fieldName.
  D2. Friendly label lookup is in scenario_tab.html JS.
  E1. "Use" button replaced by "Activate" in scenario_tab.html.
  E2. "M1 PROTOTYPE" badge removed from scenario_matrix.html.
  E3. "M2 LIVE" badge removed from scenario_matrix.html.
  E4. "Inheritance prototype." text replaced.
  F1. Engine MD5 unchanged.
  F2. TUHO P1 DSCR unchanged.
  F3. Oborovo P1 DSCR unchanged.
  G1. File scope guard.
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

_EXPORT_PATH   = Path(REPO_ROOT) / "app/templates/partials/export_registry.html"
_SHELL_PATH    = Path(REPO_ROOT) / "app/templates/partials/workspace_shell.html"
_SCENARIO_PATH = Path(REPO_ROOT) / "app/templates/partials/scenario_tab.html"
_MATRIX_PATH   = Path(REPO_ROOT) / "app/templates/partials/scenario_matrix.html"
_CSS_PATH      = Path(REPO_ROOT) / "static/styles.css"


# ---------------------------------------------------------------------------
# C. UX-4C: Downloads cleanup
# ---------------------------------------------------------------------------

class TestDownloadsCleanup:
    def _src(self):
        return _EXPORT_PATH.read_text()

    def test_no_dead_download_anchors(self):
        for path in (_EXPORT_PATH, _SHELL_PATH):
            src = path.read_text()
            dead = ["href=\"#download-parity\"", "href=\"#download-gap\"",
                    "href=\"#download-source\"", "href=\"#download-governance\"",
                    "href=\"#download-calibration-pack\""]
            for anchor in dead:
                assert anchor not in src, f"Dead anchor still present in {path.name}: {anchor}"

    def test_disabled_cards_have_aria_disabled(self):
        for path in (_EXPORT_PATH, _SHELL_PATH):
            assert 'aria-disabled="true"' in path.read_text(), \
                f"aria-disabled missing from {path.name}"

    def test_disabled_cards_show_coming_soon(self):
        for path in (_EXPORT_PATH, _SHELL_PATH):
            assert "Coming Soon" in path.read_text(), \
                f"Coming Soon missing from {path.name}"

    def test_disabled_cards_have_tooltip(self):
        for path in (_EXPORT_PATH, _SHELL_PATH):
            assert 'title="Not yet available' in path.read_text(), \
                f"tooltip missing from {path.name}"

    def test_working_links_preserved(self):
        for path in (_EXPORT_PATH, _SHELL_PATH):
            src = path.read_text()
            assert "/exports/institutional-workbook.xlsx" in src
            assert "/exports/runtime-summary.csv" in src

    def test_registry_title_no_phase_number(self):
        src = self._src()
        assert "Phase 10 Export Registry" not in src
        assert "Export Registry" in src

    def test_disabled_css_in_stylesheet(self):
        css = _CSS_PATH.read_text()
        assert ".export-card--disabled" in css
        assert "pointer-events: none" in css


# ---------------------------------------------------------------------------
# D. UX-4D: Friendly scenario labels
# ---------------------------------------------------------------------------

class TestScenarioFriendlyLabels:
    def _src(self):
        return _SCENARIO_PATH.read_text()

    def test_popup_uses_label_cell_not_raw_field(self):
        src = self._src()
        assert "sc-td--label" in src, "JS must read the label from .sc-td--label"
        assert "fieldLabel" in src, "JS must use a fieldLabel variable"

    def test_raw_field_name_not_sole_title_source(self):
        src = self._src()
        # Old code used fieldName directly as title — must be replaced
        assert "title.textContent = (fieldName || 'Edit')" not in src, (
            "Old title.textContent using raw fieldName must be replaced"
        )

    def test_activate_button_in_scenario_tab(self):
        """Use → Activate also covered here for cross-check."""
        src = self._src()
        assert ">Activate</button>" in src


# ---------------------------------------------------------------------------
# E. UX-4E: Developer label removal
# ---------------------------------------------------------------------------

class TestDeveloperLabelRemoval:
    def test_use_replaced_by_activate(self):
        src = _SCENARIO_PATH.read_text()
        # Must not have bare >Use< button text
        assert ">Use</button>" not in src, "'Use' button must be replaced by 'Activate'"
        assert ">Activate</button>" in src

    def test_m1_prototype_badge_removed(self):
        src = _MATRIX_PATH.read_text()
        assert "M1 PROTOTYPE" not in src, "M1 PROTOTYPE badge must be removed"

    def test_m2_live_badge_removed(self):
        src = _MATRIX_PATH.read_text()
        assert "M2 LIVE" not in src, "M2 LIVE badge must be removed"

    def test_inheritance_prototype_text_replaced(self):
        src = _MATRIX_PATH.read_text()
        assert "Inheritance prototype." not in src, (
            "'Inheritance prototype.' developer text must be replaced"
        )


# ---------------------------------------------------------------------------
# F. Parity
# ---------------------------------------------------------------------------

class TestUX4CDEParity:
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
# G. File scope guard
# ---------------------------------------------------------------------------

class TestUX4CDEFileScope:
    ALLOWED_PREFIXES = (
        "app/templates/partials/export_registry.html",
        "app/templates/partials/workspace_shell.html",
        "app/templates/partials/scenario_tab.html",
        "app/templates/partials/scenario_matrix.html",
        "app/templates/partials/_matrix_run_result.html",
        "static/styles.css",
        "tests/test_phase_ux4cde_",
        "tests/test_phase_ux4b_",
        "tests/test_phase_ux4a_",
        "tests/test_phase_scenario1_",
        "tests/test_phase_scenario2_",
        "tests/test_phase_stab",
        "tests/test_phase_pr1_",
        "tests/test_phase_pr2_",
        "tests/test_phase_pr3_",
        "tests/test_phase_m1_",
        "tests/test_phase_m4_",
        "tests/test_p1_compare_validation.py",
        # IRR-ANOMALY-1-FIX display mapping followup
        "tests/test_phase_irr_",
        "tests/test_phase_pilot_blocker_1",
        "docs/phase_irr_",
        "docs/phase_pilot_blocker_1",
        "reports/phase_irr_",
        "reports/phase_pilot_blocker_1",
            "app/templates/partials/runtime_summary.html",  # UX-2C-1 cross-arc
            "app/ui/dashboard.py",  # UX-2C-1 cross-arc
            "tests/",  # UX-2C-1 cross-arc (branch-wide test footprint)
            "app/templates/partials/inputs_section.html",  # UX-2C-2 cross-arc
            "app/templates/partials/sheet_opex_detail.html",  # UX-2D cross-arc
            "tests/test_ux2d_",  # UX-2D cross-arc
    )
    DISALLOWED_PREFIXES = (
        "app/waterfall_core.py",
        "app/project_factories.py",
        "app/persistence/",
        "app/services/",
        "app/export/",
        "main_web.py",
    )
    # P1-COMPARE-VALIDATION landed after UX-4CDE; its main_web.py + test file
    # are acceptable on branches that build on this one.
    # IRR-ANOMALY-1-FIX display mapping followup: main_web.py + template
    # + test prefix are acceptable on branches that build on this one.
    # HOTFIX-PILOT-BLOCKER-1: presentation/routing fix touches
    # main_web.py (F4), app/services/project_save_as_service.py
    # (F1), app/templates/partials/_factory_lock_indicator.html
    # (F2), and app/ui/dashboard.py (F3). All are
    # presentation/routing only; allowlist them.
    DISALLOWED_EXCEPTIONS = (
        "main_web.py",
        "tests/test_p1_compare_validation",
        "app/templates/partials/_matrix_run_result.html",
        "tests/test_phase_irr_",
        "tests/test_phase_pilot_blocker_1",
        "app/services/project_save_as_service.py",
        "app/templates/partials/_factory_lock_indicator.html",
        "app/ui/dashboard.py",
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
            if any(f.startswith(e) for e in self.DISALLOWED_EXCEPTIONS):
                continue
            assert not any(f.startswith(p) for p in self.DISALLOWED_PREFIXES), (
                f"UX-4CDE must not touch {f}"
            )
            assert any(f.startswith(p) for p in self.ALLOWED_PREFIXES), (
                f"UX-4CDE file outside allowed scope: {f}"
            )
