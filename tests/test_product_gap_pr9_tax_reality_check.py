"""Product Gap PR9 -- Tax Reality Check tests.

Scope:
- Tax tab/screen still renders.
- Real editable Tax inputs, if any, remain editable. Investigation
  found no safe, already-wired persistence path exposes CIT Rate or
  Loss Carryforward as editable anywhere in the app (the Inputs tab's
  Tax Summary card also renders them read-only -- see
  app/templates/partials/inputs_section.html lines ~185-186, no
  editable=True passed to field_row). They remain read-only on this
  sheet too, for the same reason -- no new persisted field was
  invented.
- Read-only/frozen tax values (CIT Rate, Loss Carryforward) remain
  clearly non-editable (`data-fc-editable="false"`, no `<input>`).
- The old "Output Preview" placeholder card (no Jinja binding, just
  fixed copy claiming a "Preview schedule") is removed and replaced
  with a single honest unavailable-state panel, since there is no
  Run-backed CIT/depreciation/loss-carryforward/WHT output anywhere
  in last_runtime_summary.
- The static "Convention: AUDIT-ONLY" badge and the G20/R99/R102
  internal governance jargon cells are removed from user-facing Tax
  copy (banned jargon per the PR9 spec).
- No banned internal jargon leaks into the user-facing Tax copy.
- No Save/Run/persistence/export behaviour is changed.
- No Preview Architecture or Runtime Pipeline files are touched.
- CAPEX/OPEX/Revenue/Financial Statements/Distribution/Sponsor/Senior
  Debt Product Gap behaviour is unaffected.
"""
from __future__ import annotations

import os
import re
import subprocess

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BANNED_JARGON = [
    "C1", "C2", "Preview Architecture", "Runtime Pipeline", "stub",
    "placeholder architecture", "R99", "R102", "G20",
]


@pytest.fixture
def tax_partial():
    path = os.path.join(PROJECT_ROOT, "app/templates/partials/sheet_tax.html")
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


# ─── 1: Tax tab/screen still renders ───────────────────────────────────────

class TestTabStillRenders:
    def test_tax_tab_panel_present_in_shell(self, workspace_shell):
        assert 'id="panel-tax"' in workspace_shell

    def test_tax_partial_included_in_shell(self, workspace_shell):
        assert "sheet_tax.html" in workspace_shell

    def test_tax_still_referenced_in_runtime_sheet_map(self, main_web_source):
        assert "partials/sheet_tax.html" in main_web_source

    def test_sheet_banner_present(self, tax_partial):
        assert "Tax" in tax_partial


# ─── 2 & 3: No real editable inputs; read-only values stay read-only ──────

class TestReadOnlyAssumptionsPreserved:
    """Investigation found no safe, already-wired persistence path
    exposes any Tax assumption as editable anywhere in the app (the
    Inputs tab's own Tax Summary card is read-only too). This PR does
    not invent one -- it only confirms the existing read-only wiring
    is preserved and clearly labeled."""

    READ_ONLY_ADDRS = ["tax!cit_rate", "tax!loss_carryforward"]

    def test_assumptions_present_and_read_only(self, tax_partial):
        for addr in self.READ_ONLY_ADDRS:
            idx = tax_partial.find(addr)
            assert idx >= 0, f"{addr} missing from sheet"
            cell_chunk = tax_partial[idx - 200 : idx + 400]
            assert 'data-fc-editable="false"' in cell_chunk

    def test_grid_root_preserved(self, tax_partial):
        assert 'data-fc-grid="tax"' in tax_partial

    def test_no_input_elements_anywhere(self, tax_partial):
        assert "<input" not in tax_partial

    def test_read_only_explanation_present(self, tax_partial):
        assert "Read-only" in tax_partial


# ─── 4: Placeholder output removed / unavailable-state shown ──────────────

class TestPlaceholderOutputRemoved:
    """Product Gap PR9 finding: the 'Output Preview' card previously
    showed fixed copy ("Preview schedule -- static reference values,
    not live calculated output") with no Jinja variable binding to
    project_ctx/runtime_summary -- there is no real CIT/taxable-income/
    depreciation/loss-carryforward/WHT engine output anywhere in
    last_runtime_summary. This class asserts that markup is gone."""

    def test_old_preview_notice_class_removed(self, tax_partial):
        assert "preview-notice" not in tax_partial

    def test_old_static_preview_copy_removed(self, tax_partial):
        assert "static reference values, not live calculated output" not in tax_partial

    def test_old_fake_convention_badge_removed(self, tax_partial):
        """The 'Convention: AUDIT-ONLY' badge was a static literal with
        zero Jinja binding -- not real data, removed."""
        assert "AUDIT-ONLY" not in tax_partial


class TestUnavailableStatePanelPresent:
    def test_unavailable_panel_present(self, tax_partial):
        assert "empty-state-notice" in tax_partial
        assert "not available yet" in tax_partial

    def test_unavailable_copy_mentions_run_backed(self, tax_partial):
        assert "Run-backed taxable income, depreciation, loss carryforward, CIT" in tax_partial

    def test_panel_reuses_existing_css_classes(self, tax_partial):
        """No new CSS pattern invented -- reuses the empty-state-notice
        / empty-state-notice--warn classes already defined in
        static/styles.css (PR6/PR7/PR8 pattern)."""
        assert "empty-state-notice--warn" in tax_partial


# ─── 5: Real Run-backed KPI block preserved (project-level only) ──────────

class TestRunBackedKPIBlockPreserved:
    """The shared-runtime-block / runtime-block-kpis block is the only
    genuinely Run-backed content available near this sheet --
    populated client-side from sessionStorage.lastRuntimeSummary,
    which is written by the existing post-/run flow. There are no
    tax-specific keys in last_runtime_summary (confirmed by searching
    main_web.py), so no tax-specific KPI is fabricated here."""

    def test_runtime_block_present(self, tax_partial):
        assert 'id="shared-runtime-block"' in tax_partial

    def test_runtime_block_population_script_present(self, tax_partial):
        assert "_populateTaxRuntimeBlock" in tax_partial
        assert "lastRuntimeSummary" in tax_partial

    def test_no_fake_tax_status_fabricated(self, tax_partial):
        """The old script hardcoded the rendered 'tax-status' element
        to the literal string 'AUDIT-ONLY' regardless of any real
        runtime data -- that fabricated client-side assignment is
        removed along with the element it targeted."""
        assert "tax-status" not in tax_partial
        assert 'textContent = "AUDIT-ONLY"' not in tax_partial


# ─── 6: No banned internal jargon in user-facing copy ──────────────────────

class TestNoInternalJargonInCopy:
    def test_no_banned_jargon_in_visible_copy(self, tax_partial):
        # Strip HTML comments (developer-facing investigation notes are
        # allowed to reference jargon for audit trail purposes; only
        # rendered user-facing copy must avoid it).
        visible = re.sub(r"<!--.*?-->", "", tax_partial, flags=re.DOTALL)
        for term in BANNED_JARGON:
            assert term not in visible, f"banned jargon {term!r} found in tax partial"


# ─── 7: No Save/Run/persistence/export behaviour changed ──────────────────

class TestNoBehaviourRegressed:
    def test_no_run_route_changes(self):
        result = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=PROJECT_ROOT, capture_output=True, text=True,
        )
        if result.returncode != 0:
            pytest.skip("git diff against main not available in this sandbox")
        changed = result.stdout.splitlines()
        assert "main_web.py" not in changed, (
            "main_web.py should not need changes for a template-only UX cleanup"
        )


# ─── 8: No Preview Architecture / Runtime Pipeline files touched ──────────

class TestGuardrailFilesUntouched:
    RESTRICTED_PATHS = [
        "domain/",
        "app/waterfall_core.py",
        "app/input_adapter.py",
        "app/project_factories.py",
        "static/modelling/runtime-renderer.js",
        "app/services/model_preview.py",
        "app/services/preview_context.py",
        "app/services/previews/",
    ]

    def test_restricted_paths_not_in_diff_against_main(self):
        result = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=PROJECT_ROOT, capture_output=True, text=True,
        )
        if result.returncode != 0:
            pytest.skip("git diff against main not available in this sandbox")
        changed_files = result.stdout.splitlines()
        for changed in changed_files:
            for restricted in self.RESTRICTED_PATHS:
                assert not changed.startswith(restricted), (
                    f"Restricted path touched: {changed!r} matches {restricted!r}"
                )


# ─── 9: Other Product Gap areas unaffected ─────────────────────────────────

class TestOtherProductGapAreasUnaffected:
    def test_financials_unavailable_panel_still_present(self):
        path = os.path.join(PROJECT_ROOT, "app/templates/partials/sheet_financials.html")
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
        assert "fs-unavailable-panel" in src

    def test_distributions_unavailable_panel_still_present(self):
        path = os.path.join(
            PROJECT_ROOT, "app/templates/partials/_sheet_distributions_partial.html"
        )
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
        assert "dist-unavailable-panel" in src

    def test_sponsor_unavailable_panel_still_present(self):
        path = os.path.join(
            PROJECT_ROOT, "app/templates/partials/_sheet_sponsor_partial.html"
        )
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
        assert "sponsor-unavailable-panel" in src

    def test_senior_debt_unavailable_panel_still_present(self):
        path = os.path.join(
            PROJECT_ROOT, "app/templates/partials/sheet_senior_debt.html"
        )
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
        assert "sd-unavailable-panel" in src
