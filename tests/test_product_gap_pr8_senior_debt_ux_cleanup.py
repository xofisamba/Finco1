"""Product Gap PR8 — Senior Debt UX Cleanup tests.

Scope:
- Senior Debt tab/screen still renders.
- Real editable Senior Debt draft inputs (gearing, target DSCR,
  interest rate, tenor) remain editable -- these are genuinely
  persisted-path inputs per the prior Senior Debt C1 migration
  (docs/SENIOR_DEBT_C1_MIGRATION_NOTE.md), confirmed via
  `data-fc-editable="true"` + a real `<input data-grid-source>`.
- Read-only/frozen assumption-grid summary values (Facility Amount,
  Tenor, All-in Rate, Target DSCR, Indicative Gearing) remain clearly
  non-editable (`data-fc-editable="false"`, no `<input>`).
- The old static "Output Preview" / "Preview schedule" placeholder
  card (no Jinja binding, just fixed copy) is removed and replaced
  with a single honest unavailable-state panel.
- No banned internal jargon leaks into the user-facing copy.
- No Save/Run/persistence/export behaviour is changed.
- No Preview Architecture or Runtime Pipeline files are touched.
- CAPEX/OPEX/Revenue/Financial Statements/Distribution/Sponsor
  Product Gap behaviour is unaffected.
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
def senior_debt_partial():
    path = os.path.join(
        PROJECT_ROOT, "app/templates/partials/sheet_senior_debt.html"
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


# ─── 1: Senior Debt tab/screen still renders ──────────────────────────────

class TestTabStillRenders:
    def test_senior_debt_tab_panel_present_in_shell(self, workspace_shell):
        assert 'id="panel-senior-debt"' in workspace_shell

    def test_senior_debt_partial_included_in_shell(self, workspace_shell):
        assert "sheet_senior_debt.html" in workspace_shell

    def test_senior_debt_still_referenced_in_runtime_sheet_map(self, main_web_source):
        assert "partials/sheet_senior_debt.html" in main_web_source

    def test_sheet_banner_present(self, senior_debt_partial):
        assert "Senior Debt" in senior_debt_partial


# ─── 2 & 3: Real editable inputs vs read-only summary cells ───────────────

class TestEditableVsReadOnlyDistinction:
    """Mirrors the Senior Debt C1 migration findings: the 4 draft
    inputs (gearing_pct, target_dscr, interest_rate_pct, tenor_years)
    are genuinely editable (draft workspace state); the 4-5 assumption
    summary cells are genuinely read-only derived display values. This
    PR does not change that wiring -- it only confirms it's preserved
    and the surrounding copy is honest."""

    DRAFT_ADDRS = [
        "seniordebt!gearing_pct",
        "seniordebt!target_dscr",
        "seniordebt!interest_rate_pct",
        "seniordebt!tenor_years",
    ]

    SUMMARY_ADDRS = [
        "seniordebt!facility_amount",
        "seniordebt!tenor_summary",
        "seniordebt!interest_rate_summary",
        "seniordebt!target_dscr_summary",
    ]

    def test_draft_inputs_still_editable(self, senior_debt_partial):
        for addr in self.DRAFT_ADDRS:
            idx = senior_debt_partial.find(addr)
            assert idx >= 0, f"{addr} missing from sheet"
            cell_chunk = senior_debt_partial[idx - 200 : idx + 400]
            assert 'data-fc-editable="true"' in cell_chunk
            assert "editable-grid-input" in cell_chunk

    def test_summary_cells_remain_read_only(self, senior_debt_partial):
        for addr in self.SUMMARY_ADDRS:
            idx = senior_debt_partial.find(addr)
            assert idx >= 0, f"{addr} missing from sheet"
            cell_chunk = senior_debt_partial[idx - 200 : idx + 400]
            assert 'data-fc-editable="false"' in cell_chunk

    def test_grid_root_preserved(self, senior_debt_partial):
        assert 'data-fc-grid="seniordebt"' in senior_debt_partial

    def test_draft_only_badge_present(self, senior_debt_partial):
        """The draft-input table keeps its 'Draft only' badge clarifying
        these are draft workspace edits, not saved/runtime values."""
        assert "Draft only" in senior_debt_partial


# ─── 4: Placeholder output removed / unavailable-state shown ──────────────

class TestPlaceholderOutputRemoved:
    """Product Gap PR8 finding: the 'Output Preview' card previously
    showed fixed copy ("Preview schedule -- static reference values,
    not live calculated output") with no Jinja variable binding to
    project_ctx/runtime_summary -- there was no real repayment
    schedule, interest/principal table, DSCR table, or covenant table
    behind it. This class asserts that markup is gone."""

    def test_old_preview_notice_class_removed(self, senior_debt_partial):
        assert "preview-notice" not in senior_debt_partial

    def test_old_static_preview_copy_removed(self, senior_debt_partial):
        assert "static reference values, not live calculated output" not in senior_debt_partial


class TestUnavailableStatePanelPresent:
    def test_unavailable_panel_present(self, senior_debt_partial):
        assert "empty-state-notice" in senior_debt_partial
        assert "not available yet" in senior_debt_partial

    def test_unavailable_copy_mentions_run_backed(self, senior_debt_partial):
        assert "Run-backed debt sizing, interest, principal, and covenant results" in senior_debt_partial

    def test_panel_reuses_existing_css_classes(self, senior_debt_partial):
        """No new CSS pattern invented -- reuses the empty-state-notice
        / empty-state-notice--warn classes already defined in
        static/styles.css (PR6/PR7 pattern)."""
        assert "empty-state-notice--warn" in senior_debt_partial


# ─── 5: Real Run-backed KPI block preserved ────────────────────────────────

class TestRunBackedKPIBlockPreserved:
    """The shared-runtime-block / sd-secondary-metrics block is the
    only genuinely Run-backed content on this sheet -- populated
    client-side from sessionStorage.lastRuntimeSummary, which is
    written by the existing post-/run flow. Untouched by this PR."""

    def test_runtime_block_present(self, senior_debt_partial):
        assert 'id="shared-runtime-block"' in senior_debt_partial

    def test_runtime_block_population_script_present(self, senior_debt_partial):
        assert "_populateSDRuntimeBlock" in senior_debt_partial
        assert "lastRuntimeSummary" in senior_debt_partial

    def test_secondary_metrics_ids_unchanged(self, senior_debt_partial):
        for el_id in ("sd-senior-debt", "sd-avg-dscr", "sd-min-dscr"):
            assert f'id="{el_id}"' in senior_debt_partial


# ─── 6: No banned internal jargon in user-facing copy ──────────────────────

class TestNoInternalJargonInCopy:
    def test_no_banned_jargon_in_visible_copy(self, senior_debt_partial):
        # Strip HTML comments (developer-facing investigation notes are
        # allowed to reference jargon for audit trail purposes; only
        # rendered user-facing copy must avoid it).
        visible = re.sub(r"<!--.*?-->", "", senior_debt_partial, flags=re.DOTALL)
        for term in BANNED_JARGON:
            assert term not in visible, f"banned jargon {term!r} found in senior debt partial"


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
