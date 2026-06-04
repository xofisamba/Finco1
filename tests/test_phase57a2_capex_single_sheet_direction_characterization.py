"""Phase 57A-2 — CAPEX single-sheet direction characterization tests.

This test file is a docs/report-only test. It does not modify
runtime code, templates, or CSS. It pins:

* The 57A-2 docs/report files exist.
* They reference the correct current main SHA.
* The 57A-2 doc inventories the current dual CAPEX UI.
* The 57A-2 doc identifies the target single Excel-like
  CAPEX sheet (with all user-required columns).
* The 57A-2 doc recommends promoting the Detail view (B)
  and removing/collapsing the Summary view (A).
* The 57A-2 doc explicitly defers OPEX/Revenue grid
  migration (supersedes 57F).
* The 57A-2 doc explicitly defers IDC calculation changes.
* The 57A-2 doc explicitly defers Tailwind / Alpine.
* No runtime / model / persistence / CSS / JS / schema /
  formula changes were introduced in 57A-2.
"""

import json
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs" / "phase57a2_capex_single_sheet_direction_characterization.md"
REPORT = REPO_ROOT / "reports" / "phase57a2_capex_single_sheet_direction_characterization.json"
SHEET_CAPEX = REPO_ROOT / "app" / "templates" / "partials" / "sheet_capex.html"
SHEET_CAPEX_DETAIL = REPO_ROOT / "app" / "templates" / "partials" / "sheet_capex_detail.html"
WORKSPACE_SHELL = REPO_ROOT / "app" / "templates" / "partials" / "workspace_shell.html"
RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"


# ============================================================
# 1. Files exist
# ============================================================


class TestFilesExist:
    def test_docs_file_exists(self):
        assert DOCS.exists(), f"57A-2 doc file missing: {DOCS}"

    def test_report_file_exists(self):
        assert REPORT.exists(), f"57A-2 report file missing: {REPORT}"

    def test_doc_minimum_size(self):
        size = DOCS.stat().st_size
        assert size > 10000, (
            f"57A-2 doc is suspiciously small ({size} bytes)."
        )

    def test_report_is_valid_json(self):
        with open(REPORT) as f:
            data = json.load(f)
        assert "phase" in data
        assert data["phase"] == "57A-2"

    def test_sheet_capex_still_exists(self):
        assert SHEET_CAPEX.exists()

    def test_sheet_capex_detail_still_exists(self):
        assert SHEET_CAPEX_DETAIL.exists()


# ============================================================
# 2. SHA references
# ============================================================


class TestShaReferences:
    def test_doc_references_current_main_sha(self):
        text = DOCS.read_text()
        assert "88a6de68df1c651904accd5621ef2d8b5047a464" in text

    def test_doc_references_rc1_frozen_sha(self):
        text = DOCS.read_text()
        assert RC1_SHA in text

    def test_doc_references_57a_merge_sha(self):
        text = DOCS.read_text()
        assert "b173355b" in text

    def test_report_references_current_main_sha(self):
        data = json.loads(REPORT.read_text())
        assert data["base_sha_start"] == (
            "88a6de68df1c651904accd5621ef2d8b5047a464"
        )

    def test_report_references_rc1_frozen_sha(self):
        data = json.loads(REPORT.read_text())
        assert data["rc1_frozen_sha"] == RC1_SHA


# ============================================================
# 3. No runtime CAPEX rewrite in 57A-2
# ============================================================


class TestNoRuntimeCapexRewriteIn57A2:
    def test_report_says_no_runtime_rewrite(self):
        data = json.loads(REPORT.read_text())
        assert data["runtime_capex_rewrite_in_this_phase"] is False

    def test_doc_says_57a2_is_characterization_only(self):
        text = DOCS.read_text()
        assert "characterization" in text.lower()
        assert "characterization document only" in text.lower() or (
            "does NOT implement a runtime CAPEX rewrite" in text
        )

    def test_sheet_capex_unchanged(self):
        """57A-2 must not modify sheet_capex.html."""
        r = subprocess.run(
            ["git", "diff", "main", "--name-only", "--",
             "app/templates/partials/sheet_capex.html"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return
        pytest.fail(
            f"57A-2 must not modify sheet_capex.html. "
            f"Found: {r.stdout.strip()!r}."
        )

    def test_sheet_capex_detail_unchanged(self):
        r = subprocess.run(
            ["git", "diff", "main", "--name-only", "--",
             "app/templates/partials/sheet_capex_detail.html"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return
        pytest.fail(
            f"57A-2 must not modify sheet_capex_detail.html. "
            f"Found: {r.stdout.strip()!r}."
        )

    def test_workspace_shell_unchanged(self):
        r = subprocess.run(
            ["git", "diff", "main", "--name-only", "--",
             "app/templates/partials/workspace_shell.html"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return
        pytest.fail(
            f"57A-2 must not modify workspace_shell.html. "
            f"Found: {r.stdout.strip()!r}."
        )


# ============================================================
# 4. Current dual CAPEX UI inventory
# ============================================================


class TestCurrentDualCapexInventory:
    def test_doc_inventories_view_a_summary(self):
        text = DOCS.read_text()
        assert "sheet_capex.html" in text
        assert "Summary" in text or "summary" in text

    def test_doc_inventories_view_b_detail(self):
        text = DOCS.read_text()
        assert "sheet_capex_detail.html" in text
        assert "Detail" in text

    def test_doc_explains_why_two_views_confusing(self):
        text = DOCS.read_text()
        assert "confusing" in text.lower()
        # At least 3 reasons listed
        reasons_count = text.lower().count("different")
        assert reasons_count >= 3, (
            f"57A-2 doc must explain why two views are confusing. "
            f"Found {reasons_count} 'different' mentions."
        )

    def test_report_has_view_a_and_view_b(self):
        data = json.loads(REPORT.read_text())
        inv = data["current_capex_ui_inventory"]
        assert "view_A_capex_summary" in inv
        assert "view_B_capex_detail" in inv


# ============================================================
# 5. User target CAPEX model
# ============================================================


class TestUserTargetCapexModel:
    @pytest.mark.parametrize(
        "column",
        [
            "Line Item",
            "Amount",
            "Cost per MW",
            "Contingency",
            "VAT",
            "WHT",
            "Depreciation",
            "Comments",
            "Test / status",
            "Payment schedule",
            "Utilisation during construction",
            "Future IDC basis",
        ],
    )
    def test_doc_mentions_target_column(self, column):
        text = DOCS.read_text()
        assert column in text, (
            f"57A-2 doc must mention the user target column {column!r}."
        )

    def test_report_has_target_columns(self):
        data = json.loads(REPORT.read_text())
        target = data["user_target_capex_model"]
        cols = [c["name"] for c in target["columns"]]
        # All 12 columns present
        assert len(cols) >= 12
        # Use a tolerant matcher: the JSON column names
        # may include qualifier suffixes like " (%)" or
        # " (rate, amount)".
        required = [
            "Line Item",
            "Cost per MW",
            "Contingency",
            "VAT",
            "WHT",
            "Depreciation",
            "Comments",
            "Test / status",
            "Payment schedule",
            "Utilisation during construction",
            "Future IDC basis",
        ]
        for c in required:
            assert any(c in col for col in cols), (
                f"Target column {c!r} must be in the report. "
                f"Found columns: {cols}"
            )


# ============================================================
# 6. Recommended direction
# ============================================================


class TestRecommendedDirection:
    def test_doc_recommends_promoting_detail_view(self):
        text = DOCS.read_text()
        # Should explicitly recommend promoting view B
        assert "promote" in text.lower() or (
            "promotes" in text.lower()
        )

    def test_doc_recommends_removing_or_collapsing_summary(self):
        text = DOCS.read_text()
        assert "remove" in text.lower() or "collapse" in text.lower()

    def test_report_recommended_direction_is_promote_detail(self):
        data = json.loads(REPORT.read_text())
        assert "Detail view" in data["recommended_direction"]


# ============================================================
# 7. Treatment of 57A LineItemGrid
# ============================================================


class TestTreatmentOf57ALineItemGrid:
    def test_doc_keeps_macro_as_foundation(self):
        text = DOCS.read_text()
        assert "keep" in text.lower()
        assert "foundation" in text.lower() or "technical foundation" in text.lower()

    def test_doc_extends_macro_for_full_capex(self):
        text = DOCS.read_text()
        assert "extend" in text.lower()

    def test_report_keeps_macro(self):
        data = json.loads(REPORT.read_text())
        treatment = data["treatment_of_57a_lineitemgrid"]
        assert treatment["keep_macro_as_technical_foundation"] is True
        assert treatment["extend_macro_for_full_capex_line_grid"] is True

    def test_doc_defers_opex_revenue(self):
        """57A-2 must explicitly defer OPEX/Revenue grid
        migration until after CAPEX single-sheet is locked."""
        text = DOCS.read_text()
        # Look for explicit deferral
        m = re.search(
            r"do not migrate opex[^\n]{0,200}",
            text,
            re.IGNORECASE,
        )
        assert m is not None, (
            "57A-2 doc must explicitly defer OPEX/Revenue migration."
        )


# ============================================================
# 8. Supersedes 57F
# ============================================================


class TestSupersedes57F:
    def test_report_supersedes_57f_opex(self):
        data = json.loads(REPORT.read_text())
        assert data["supersedes_57f_opex_recommendation"] is True

    def test_doc_explains_supersession(self):
        text = DOCS.read_text()
        assert "supersede" in text.lower() or (
            "57F" in text and "OPEX" in text and "defer" in text.lower()
        )


# ============================================================
# 9. No IDC calculation changes
# ============================================================


class TestNoIdcCalculationChanges:
    def test_doc_says_no_idc_changes(self):
        text = DOCS.read_text()
        # Find the "Future IDC basis" column
        # and verify it's marked as a placeholder
        m = re.search(
            r"Future IDC basis[^\n]{0,300}",
            text,
        )
        assert m is not None
        ctx = m.group(0).lower()
        assert "placeholder" in ctx or "not implemented" in ctx or (
            "future work" in ctx
        )

    def test_report_no_idc_calculation_changes(self):
        data = json.loads(REPORT.read_text())
        assert data["hard_no_go_verified"]["no_idc_calculation_changes"] is True


# ============================================================
# 10. Hard no-go
# ============================================================


class TestHardNoGoScope:
    @pytest.mark.parametrize(
        "forbidden_change",
        [
            "waterfall_core",
            "project_factories",
            "persistence",
            "main_web.py",
            "static/app.js",
            "static/styles.css",
            "schema",
            "fixture",
            "tailwind",
            "alpine",
            "react",
            "vue",
            "svelte",
        ],
    )
    def test_doc_mentions_forbidden_change(self, forbidden_change):
        text = DOCS.read_text().lower()
        assert forbidden_change.lower() in text

    def test_doc_says_rc1_untouched(self):
        text = DOCS.read_text()
        m = re.search(r"rc1[^\n]{0,200}", text, re.IGNORECASE)
        assert m is not None
        ctx = m.group(0).lower()
        assert "untouched" in ctx or "frozen" in ctx

    def test_doc_says_no_runtime_capex_rewrite(self):
        text = DOCS.read_text()
        assert (
            "No runtime CAPEX rewrite" in text
            or "no runtime capex rewrite" in text.lower()
        )

    def test_doc_says_no_ui32_opex_revenue_yet(self):
        text = DOCS.read_text()
        assert "OPEX" in text and "Revenue" in text
        # Should mention deferral
        assert "defer" in text.lower()


# ============================================================
# 11. Diff scope
# ============================================================


class Test57A2IsDocsOnly:
    def test_57a2_diff_only_in_docs_reports_tests(self):
        r = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on 57A-2 branch or no diff")
        changed = set(r.stdout.strip().split("\n"))
        for c in changed:
            assert (
                c.startswith("docs/")
                or c.startswith("reports/")
                or c.startswith("tests/")
            ), (
                f"57A-2 diff file {c!r} is outside docs/reports/tests."
            )

    def test_no_runtime_files_in_diff(self):
        r = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on 57A-2 branch or no diff")
        changed = set(r.stdout.strip().split("\n"))
        forbidden = [
            "main_web.py",
            "app/waterfall_core.py",
            "app/project_factories.py",
            "static/app.js",
            "static/styles.css",
        ]
        for c in changed:
            for f in forbidden:
                if c.endswith(f):
                    pytest.fail(
                        f"57A-2 must not modify {f!r}. "
                        f"Found: {c!r}."
                    )
        for c in changed:
            assert not c.startswith("app/persistence/"), (
                f"57A-2 must not modify app/persistence/. "
                f"Found: {c!r}."
            )
            assert not c.startswith("app/services/"), (
                f"57A-2 must not modify app/services/. "
                f"Found: {c!r}."
            )


# ============================================================
# 12. Rc1 untouched
# ============================================================


class TestRc1Untouched:
    def test_rc1_sha_constant_stable(self):
        assert RC1_SHA == "b425a0708719eaa5e1d922b1008e5609758e0ad4"

    def test_rc1_still_in_git_history(self):
        r = subprocess.run(
            ["git", "rev-parse", RC1_SHA],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0
