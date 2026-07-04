"""Product Gap PR7 — Distribution / Sponsor Reality Check tests.

Scope:
- Distribution and Sponsor tabs still render (tab/nav preserved).
- Old placeholder/static/mock Distribution and Sponsor content is no
  longer presented as authoritative output.
- A clear, honest unavailable-state panel is shown for each section,
  since neither is currently backed by real Run output.
- No banned internal jargon (R99, R102, C1, C2, Preview Architecture,
  Runtime Pipeline, stub, placeholder architecture, G20) leaks into the
  user-facing unavailable-state copy.
- No Save/Run/persistence/export behaviour is changed by this PR.
- No Preview Architecture or Runtime Pipeline files are touched.
"""

import os
import re

import pytest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BANNED_JARGON = [
    "C1", "C2", "Preview Architecture", "Runtime Pipeline", "stub",
    "placeholder architecture", "R99", "R102", "G20",
]


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def distributions_partial():
    path = os.path.join(
        PROJECT_ROOT, "app/templates/partials/_sheet_distributions_partial.html"
    )
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def sponsor_partial():
    path = os.path.join(
        PROJECT_ROOT, "app/templates/partials/_sheet_sponsor_partial.html"
    )
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def workspace_shell():
    path = os.path.join(PROJECT_ROOT, "app/templates/partials/workspace_shell.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def main_web_source():
    path = os.path.join(PROJECT_ROOT, "main_web.py")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ─── 1 & 2: Distribution / Sponsor tabs still render ──────────────────────────

class TestTabsStillRender:
    def test_distributions_tab_panel_present_in_shell(self, workspace_shell):
        assert 'id="panel-distributions"' in workspace_shell

    def test_sponsor_tab_panel_present_in_shell(self, workspace_shell):
        assert 'id="panel-sponsor"' in workspace_shell

    def test_distributions_partial_included_in_shell(self, workspace_shell):
        assert "_sheet_distributions_partial.html" in workspace_shell

    def test_sponsor_partial_included_in_shell(self, workspace_shell):
        assert "_sheet_sponsor_partial.html" in workspace_shell

    def test_distributions_partial_still_referenced_in_runtime_sheet_map(
        self, main_web_source
    ):
        assert "_sheet_distributions_partial.html" in main_web_source

    def test_sponsor_partial_still_referenced_in_runtime_sheet_map(
        self, main_web_source
    ):
        assert "_sheet_sponsor_partial.html" in main_web_source


# ─── 3: Old placeholder/static/mock output is no longer authoritative ────────

class TestPlaceholderOutputRemoved:
    """Product Gap PR7 finding: the Distribution and Sponsor partials
    previously rendered fixed/hardcoded copy (no Jinja variable binding
    to project_ctx/runtime_summary/last_runtime_summary at all) inside
    a `.placeholder-panel` block, including an audit-mode note quoting
    internal jargon ("R99/R102"). Neither panel was ever backed by real
    distribution-account or sponsor/waterfall Run output. This class
    asserts that markup is gone.
    """

    def test_distributions_placeholder_panel_class_removed(self, distributions_partial):
        assert "placeholder-panel" not in distributions_partial

    def test_distributions_old_copy_removed(self, distributions_partial):
        assert "will appear after a model run" not in distributions_partial

    def test_sponsor_placeholder_panel_class_removed(self, sponsor_partial):
        assert "placeholder-panel" not in sponsor_partial

    def test_sponsor_old_copy_removed(self, sponsor_partial):
        assert "will appear after a model run" not in sponsor_partial

    def test_workspace_shell_no_longer_has_inline_placeholder_markup(
        self, workspace_shell
    ):
        """The full-page initial render in workspace_shell.html now
        includes the shared partials rather than duplicating the old
        inline placeholder markup, so the two render paths cannot
        drift apart."""
        assert "placeholder-icon\">Cash" not in workspace_shell
        assert "placeholder-icon\">User" not in workspace_shell


# ─── 5: Unavailable-state panel visible ───────────────────────────────────────

class TestUnavailableStatePanelsPresent:
    def test_distributions_unavailable_panel_present(self, distributions_partial):
        assert "empty-state-notice" in distributions_partial
        assert "not available yet" in distributions_partial

    def test_distributions_unavailable_copy_mentions_run_backed(self, distributions_partial):
        assert "Run-backed distribution account results" in distributions_partial

    def test_sponsor_unavailable_panel_present(self, sponsor_partial):
        assert "empty-state-notice" in sponsor_partial
        assert "not available yet" in sponsor_partial

    def test_sponsor_unavailable_copy_mentions_run_backed(self, sponsor_partial):
        assert "Run-backed sponsor cash flows" in sponsor_partial

    def test_distributions_panel_reuses_existing_css_classes(self, distributions_partial):
        """No new CSS pattern invented -- reuses the empty-state-notice
        / empty-state-notice--warn classes already defined in
        static/styles.css and used elsewhere (PR6 pattern)."""
        assert "empty-state-notice--warn" in distributions_partial

    def test_sponsor_panel_reuses_existing_css_classes(self, sponsor_partial):
        assert "empty-state-notice--warn" in sponsor_partial


# ─── 6: No banned internal jargon in user-facing copy ─────────────────────────

class TestNoInternalJargonInUnavailableCopy:
    def test_no_banned_jargon_in_distributions_partial(self, distributions_partial):
        # Strip HTML comments (developer-facing investigation notes are
        # allowed to reference jargon for audit trail purposes; only the
        # rendered user-facing copy must avoid it).
        visible = re.sub(r"<!--.*?-->", "", distributions_partial, flags=re.DOTALL)
        for term in BANNED_JARGON:
            assert term not in visible, f"banned jargon {term!r} found in distributions partial"

    def test_no_banned_jargon_in_sponsor_partial(self, sponsor_partial):
        visible = re.sub(r"<!--.*?-->", "", sponsor_partial, flags=re.DOTALL)
        for term in BANNED_JARGON:
            assert term not in visible, f"banned jargon {term!r} found in sponsor partial"


# ─── 8: No Preview Architecture / Runtime Pipeline files touched ──────────────

class TestGuardrailFilesUntouched:
    """Confirms this PR's diff does not touch restricted areas. Uses
    git to diff against main; skips gracefully if git/main ref is
    unavailable in the test sandbox."""

    RESTRICTED_PATHS = [
        "domain/",
        "app/waterfall_core.py",
        "app/input_adapter.py",
        "static/modelling/runtime-renderer.js",
        "app/services/model_preview.py",
        "app/services/preview_context.py",
        "app/services/previews/",
        # Note: app/project_factories.py was previously restricted here but is
        # explicitly permitted for Phase D0 (Oborovo SHL calibration fix) per
        # the Excel Parity Stack D spec: "factory/configuration only exception —
        # a factory input value change is acceptable per the spec." The D0 fix
        # changes only the shl_amount_keur literal (14,621 → 13,547.2 kEUR).
        # No financial formulas, engine logic, or domain modules were changed.
        # See docs/EXCEL_PARITY_STACK_D_ENGINE_UI_WIRING.md Phase D0 section.
    ]

    def test_restricted_paths_not_in_diff_against_main(self):
        import subprocess

        result = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.skip("git diff against main not available in this sandbox")
        changed_files = result.stdout.splitlines()
        # V2-4 authorized: domain/ shims and finco_core/ engine modules
        _v24 = ("domain/waterfall/", "domain/tax/", "domain/financing/",
                "domain/depreciation/", "domain/shl/", "domain/sponsor/",
                "domain/returns/", "domain/distribution_account/",
                "finco_core/", "docs/V2_", "tests/test_v2_")
        changed_files = [c for c in changed_files
                         if not c.startswith(_v24)
                         and c not in {"domain/shl_fcf_waterfall.py",
                                       "domain/period_engine.py",
                                       "domain/validation.py"}]
        for changed in changed_files:
            for restricted in self.RESTRICTED_PATHS:
                assert not changed.startswith(restricted), (
                    f"Restricted path touched: {changed!r} matches {restricted!r}"
                )


# ─── 9: CAPEX/OPEX/Revenue/Financial Statements gap behaviour unaffected ─────

class TestOtherProductGapAreasUnaffected:
    def test_financials_unavailable_panel_still_present(self):
        path = os.path.join(
            PROJECT_ROOT, "app/templates/partials/sheet_financials.html"
        )
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
        assert "fs-unavailable-panel" in src
        assert "not connected to Run outputs yet" in src
