"""UI-6 — Institutional Financial Statements & Reporting Experience.

Verifies the additive introduction of the institutional reporting
chrome (statement selector + toolbar + notes panel + reporting
dashboard wrapper + compare layout + print stylesheet) across the
P&L, Cash Flow, Balance Sheet, Executive Summary, IC Pack, Credit
Pack, Lender Workspace, and FS Compare panels.

Same governance contract as UI-4 / UI-5 (no engine / route /
calculation / persistence / financial-statement / export / factory
change).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
TOKENS_CSS = REPO_ROOT / "static" / "tokens.css"
STMTS_CSS = REPO_ROOT / "static" / "statements-reporting.css"
BASE_HTML = REPO_ROOT / "app" / "templates" / "base.html"
WORKSPACE_SHELL_HTML = (
    REPO_ROOT / "app" / "templates" / "partials" / "workspace_shell.html"
)
SCENARIO_WORKSPACE_HTML = (
    REPO_ROOT / "app" / "templates" / "partials" / "scenario_workspace.html"
)
SELECTOR_PARTIAL = (
    REPO_ROOT / "app" / "templates" / "partials" / "_statements_workspace_selector.html"
)
NOTES_PARTIAL = (
    REPO_ROOT / "app" / "templates" / "partials" / "_statements_workspace_notes.html"
)
REPORT_DASHBOARD = (
    REPO_ROOT / "app" / "templates" / "partials" / "_reporting_dashboard.html"
)
COMPARE_PARTIAL = (
    REPO_ROOT / "app" / "templates" / "partials" / "_statements_compare.html"
)
REPORT_WRAPPER_PARTIALS = {
    "exec": REPO_ROOT / "app" / "templates" / "partials" / "_reporting_dashboard_exec.html",
    "ic": REPO_ROOT / "app" / "templates" / "partials" / "_reporting_dashboard_ic.html",
    "credit": REPO_ROOT / "app" / "templates" / "partials" / "_reporting_dashboard_credit.html",
    "lender": REPO_ROOT / "app" / "templates" / "partials" / "_reporting_dashboard_lender.html",
    "fs-compare": REPO_ROOT / "app" / "templates" / "partials" / "_reporting_dashboard_fs_compare.html",
}


REQUIRED_FO_CLASSES = [
    # Statements workspace
    "fo-statements-workspace",
    "fo-statements-selector",
    "fo-statements-selector__group",
    "fo-statements-selector__divider",
    "fo-statements-selector__btn",
    "fo-statements-toolbar",
    "fo-statements-toolbar__group",
    "fo-statements-toolbar__label",
    "fo-statements-toolbar__select",
    "fo-statements-toolbar__btn",
    "fo-statements-toolbar__btn--primary",
    "fo-statements-workspace__layout",
    "fo-statements-workspace__nav",
    "fo-statements-workspace__nav-title",
    "fo-statements-workspace__nav-list",
    "fo-statements-workspace__nav-link",
    "fo-statements-workspace__nav-dot",
    "fo-statements-workspace__content",
    "fo-statements-workspace__context",
    "fo-statements-workspace__context-title",
    "fo-statements-workspace__context-list",
    "fo-statements-workspace__context-row",
    "fo-statements-workspace__context-label",
    "fo-statements-workspace__context-value",
    "fo-statements-workspace__context-value--placeholder",
    "fo-statements-workspace__context-hint",
    # Notes panel
    "fo-statements-notes",
    "fo-statements-notes__title",
    "fo-statements-notes__list",
    "fo-statements-notes__item",
    "fo-statements-notes__item-title",
    "fo-statements-notes__item-icon",
    "fo-statements-notes__item-icon--warn",
    "fo-statements-notes__item-icon--info",
    "fo-statements-notes__item-body",
    "fo-statements-notes__disclosure",
    # Reporting dashboard
    "fo-reporting-dashboard",
    "fo-reporting-dashboard__header",
    "fo-reporting-dashboard__title",
    "fo-reporting-dashboard__subtitle",
    "fo-reporting-dashboard__card",
    "fo-reporting-dashboard__card-title",
    "fo-reporting-dashboard__card-content",
    "fo-reporting-dashboard__card-grid",
    # Compare
    "fo-statements-compare",
    "fo-statements-compare__header",
    "fo-statements-compare__row",
    "fo-statements-compare__row--subtotal",
    "fo-statements-compare__row--total",
    "fo-statements-compare__delta--up",
    "fo-statements-compare__delta--down",
    "fo-statements-compare__delta--flat",
    # Inline value spans
    "fo-stmts-neg",
    "fo-stmts-pos",
]


class TestFilesExist:
    @pytest.mark.parametrize("path", [
        STMTS_CSS,
        SELECTOR_PARTIAL,
        NOTES_PARTIAL,
        REPORT_DASHBOARD,
        COMPARE_PARTIAL,
        *REPORT_WRAPPER_PARTIALS.values(),
    ])
    def test_deliverable_present(self, path):
        assert path.is_file(), f"UI-6 deliverable missing: {path}"


class TestStatementsCssSanity:
    def test_css_has_header_comment(self):
        text = STMTS_CSS.read_text(encoding="utf-8")
        assert "STATEMENTS & REPORTING" in text.upper()

    def test_css_balanced_braces(self):
        text = STMTS_CSS.read_text(encoding="utf-8")
        assert text.count("{") == text.count("}")

    def test_css_substantive(self):
        assert STMTS_CSS.stat().st_size > 12000

    def test_print_block_present(self):
        # PART E requires browser-print optimisation.
        text = STMTS_CSS.read_text(encoding="utf-8")
        assert "@media print" in text
        assert "@page" in text


class TestFoClassNamespacing:
    @pytest.mark.parametrize("cls", REQUIRED_FO_CLASSES)
    def test_fo_class_declared_in_statements_css(self, cls):
        text = STMTS_CSS.read_text(encoding="utf-8")
        pattern = re.compile(rf"\.{re.escape(cls)}\b")
        assert pattern.search(text), (
            f"Required class .{cls} not declared in statements-reporting.css."
        )

    @pytest.mark.parametrize("cls", REQUIRED_FO_CLASSES)
    def test_fo_class_does_not_leak_into_legacy_stylesheets(self, cls):
        legacy_paths = [
            REPO_ROOT / "static" / "styles.css",
            REPO_ROOT / "static" / "chrome.css",
            REPO_ROOT / "static" / "sheet-tabs.css",
            REPO_ROOT / "static" / "workspace.css",
            REPO_ROOT / "static" / "modelling-workspace.css",
        ]
        for legacy in legacy_paths:
            if not legacy.is_file():
                continue
            text = legacy.read_text(encoding="utf-8")
            text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
            pattern = re.compile(rf"\.{re.escape(cls)}\b")
            assert not pattern.search(text), (
                f"Statements class .{cls} leaked into {legacy.name}."
            )


class TestStatementsCssOnlyConsumesFoTokens:
    def test_no_raw_hex_colours(self):
        text = STMTS_CSS.read_text(encoding="utf-8")
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        offenders = []
        for line_no, raw in enumerate(text.splitlines(), start=1):
            if re.search(r"#[0-9a-fA-F]{3,8}\b", raw):
                offenders.append((line_no, raw))
        assert not offenders, (
            "statements-reporting.css must not declare raw hex colours. "
            "Offends:\n  " +
            "\n  ".join(f"L{n}: {l}" for n, l in offenders)
        )

    def test_no_raw_rgb_colours(self):
        text = STMTS_CSS.read_text(encoding="utf-8")
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        offenders = []
        for line_no, raw in enumerate(text.splitlines(), start=1):
            if re.search(r"\brgba?\s*\(", raw):
                offenders.append((line_no, raw))
        assert not offenders, (
            "statements-reporting.css must not declare raw rgba() colours."
        )

    def test_uses_fo_tokens(self):
        text = STMTS_CSS.read_text(encoding="utf-8")
        for token in [
            "--fo-paper", "--fo-line", "--fo-ink", "--fo-ink-soft",
            "--fo-ink-faint", "--fo-brand-50", "--fo-brand-600",
            "--fo-brand-700", "--fo-brand-800",
            "--fo-rag-green", "--fo-rag-amber", "--fo-rag-red",
            "--fo-rag-green-bg", "--fo-rag-amber-bg",
            "--fo-rag-neutral", "--fo-rag-neutral-bg",
            "--fo-font-ui", "--fo-font-mono",
            "--fo-text-xs", "--fo-text-sm", "--fo-text-md",
            "--fo-text-lg", "--fo-text-xl",
            "--fo-s1", "--fo-s2", "--fo-s3", "--fo-s4", "--fo-s5",
            "--fo-r-sm", "--fo-r-md", "--fo-r-lg",
            "--fo-weight-regular", "--fo-weight-medium",
            "--fo-weight-semibold", "--fo-weight-bold",
            "--fo-t-fast", "--fo-ease",
            "--fo-chrome-brand-h", "--fo-chrome-cmd-h",
        ]:
            assert token in text, (
                f"statements-reporting.css must consume {token} from tokens.css."
            )

    def test_no_legacy_palette_alias(self):
        text = STMTS_CSS.read_text(encoding="utf-8")
        for legacy in ["--sidebar-bg", "--primary", "--surface",
                        "--border", "--text-secondary"]:
            pattern = re.compile(rf"var\(\s*{re.escape(legacy)}\b")
            assert not pattern.search(text), (
                f"statements-reporting.css must not reference legacy token {legacy}."
            )


class TestBaseHtmlWiring:
    def test_statements_css_linked(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert "/static/statements-reporting.css" in text, (
            "base.html must link static/statements-reporting.css."
        )

    def test_load_order_full_ui_stack(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        order = [
            "/static/tokens.css",
            "/static/styles.css",
            "/static/chrome.css",
            "/static/sheet-tabs.css",
            "/static/workspace.css",
            "/static/modelling-workspace.css",
            "/static/statements-reporting.css",
        ]
        positions = [text.find(p) for p in order]
        assert all(p > 0 for p in positions), (
            f"All UI stylesheets must be linked. Positions: {positions}"
        )
        assert positions == sorted(positions), (
            f"Stylesheets MUST load in order: {order}"
        )


class TestStatementsPartialContracts:
    def test_selector_partial_declares_statement_selector_and_toolbar(self):
        text = SELECTOR_PARTIAL.read_text(encoding="utf-8")
        for needle in (
            "fo-statements-selector",
            "fo-statements-toolbar",
            "fo-statements-selector__btn",
            "fo-statements-toolbar__select",
            "Print",
            "Export",
            "Period",
            "Scenario",
            "View",
        ):
            assert needle in text, (
                f"Selector partial must declare {needle!r}."
            )

    def test_selector_partial_uses_role_tablist(self):
        text = SELECTOR_PARTIAL.read_text(encoding="utf-8")
        assert 'role="tablist"' in text

    def test_notes_partial_surfaces_existing_disclosures(self):
        text = NOTES_PARTIAL.read_text(encoding="utf-8")
        # PART C — at least these disclosures must be visible:
        for needle in (
            "Tax policy",
            "Loss carry-forward",
            "SHL convention",
            "Balance Sheet closes",
            "Debt reconciliation",
        ):
            assert needle in text, (
                f"Notes partial must surface {needle!r} as a UI element."
            )
        # Never invent calculations.
        for forbidden in ("import math", "import numpy", "from math",
                           "from numpy", "import scipy",
                           "run_scenario", "compute_irr", "compute_dscr",
                           "compute_npv", "app/capex_engine",
                           "app/waterfall_core"):
            assert forbidden not in text, (
                f"Notes partial must not invent calculations; "
                f"found {forbidden!r}."
            )

    @pytest.mark.parametrize("kind,path", list(REPORT_WRAPPER_PARTIALS.items()))
    def test_reporting_wrapper_declares_dashboard(self, kind, path):
        text = path.read_text(encoding="utf-8")
        for needle in ("fo-reporting-dashboard",
                        "fo-reporting-dashboard__title",
                        "data-fo-reporting-pack="):
            assert needle in text, (
                f"{kind} wrapper must include {needle!r}."
            )

    def test_compare_partial_has_sticky_header(self):
        text = COMPARE_PARTIAL.read_text(encoding="utf-8")
        for needle in (
            "fo-statements-compare",
            "fo-statements-compare__header",
            "fo-statements-compare__row",
            "fo-statements-compare__delta--up",
            "fo-statements-compare__delta--down",
            "fo-statements-compare__delta--flat",
        ):
            assert needle in text, (
                f"Compare partial must declare {needle!r}."
            )


# ---------------------------------------------------------------------------
# Mount tests — workspace_shell.html + scenario_workspace.html
# ---------------------------------------------------------------------------

class TestWorkspaceShellMountsStatementsChrome:
    """P&L / Cash Flow / Balance Sheet panels must wrap content in the
    statements-workspace chrome (PART A)."""

    @pytest.mark.parametrize("panel_id,active,kind", [
        ("panel-pl", "pl", "pl"),
        ("panel-cashflow", "cf", "cf"),
        ("panel-balance", "bs", "bs"),
    ])
    def test_statement_panel_mounted(self, panel_id, active, kind):
        text = WORKSPACE_SHELL_HTML.read_text(encoding="utf-8")
        idx = text.find(f'id="{panel_id}"')
        assert idx > 0, f"{panel_id} not found in workspace_shell.html."
        # Within 6000 chars of the panel opener:
        window = text[idx:idx + 6000]
        assert "_statements_workspace_selector.html" in window, (
            f"{panel_id} must mount the statements selector partial."
        )
        assert "_statements_workspace_notes.html" in window, (
            f"{panel_id} must mount the financial notes panel."
        )
        assert f'_active_statement = "{active}"' in window, (
            f"{panel_id} must set _active_statement={active!r}."
        )


class TestScenarioWorkspaceMountsReportingDashboard:
    """scenario_workspace.html must mount the reporting-dashboard wrappers
    for exec / ic / credit / lender / fs-compare."""

    @pytest.mark.parametrize("wrapper", [
        "_reporting_dashboard_exec.html",
        "_reporting_dashboard_ic.html",
        "_reporting_dashboard_credit.html",
        "_reporting_dashboard_lender.html",
        "_reporting_dashboard_fs_compare.html",
    ])
    def test_wrapper_mounted(self, wrapper):
        text = SCENARIO_WORKSPACE_HTML.read_text(encoding="utf-8")
        assert wrapper in text, (
            f"scenario_workspace.html must mount {wrapper}."
        )


# ---------------------------------------------------------------------------
# Forbidden paths — UI-6 is presentation only
# ---------------------------------------------------------------------------

FORBIDDEN_PATHS = [
    "app/waterfall_core.py",
    "app/waterfall_runner.py",
    "app/input_adapter.py",
    "app/project_factories.py",
    "app/capex_engine.py",
    "app/opex_engine.py",
    "app/depreciation_engine.py",
    "app/excel_export.py",
    "app/services/save_run_service.py",
    "app/services/run_service.py",
    "app/services/compare_service.py",
    "app/services/download_service.py",
    "app/services/preview_context.py",
    "app/services/previews/",
    "app/persistence/",
    "domain/",
    "main_web.py",
    "main_api.py",
    "static/app.js",
    "static/styles.css",
    "static/chrome.css",
    "static/sheet-tabs.css",
    "static/workspace.css",
    "static/modelling-workspace.css",
    "static/modelling/",
    "static/interaction/",
    "app/templates/partials/sheet_financials.html",
    "app/templates/partials/sheet_revenue.html",
    "app/templates/partials/sheet_opex.html",
    "app/templates/partials/sheet_opex_detail.html",
    "app/templates/partials/sheet_capex.html",
    "app/templates/partials/sheet_capex_detail.html",
    "app/templates/partials/sheet_senior_debt.html",
    "app/templates/partials/sheet_shl.html",
    "app/templates/partials/sheet_tax.html",
    "app/templates/partials/sheet_inputs.html",
    "app/templates/partials/inputs_section.html",
    "app/templates/partials/_overview_workspace.html",
    "app/templates/partials/_inputs_workspace.html",
    "app/templates/partials/_modelling_workspace_chrome.html",
    "app/templates/partials/_modelling_workspace_header.html",
    "app/templates/partials/_modelling_workspace_nav.html",
    "app/templates/partials/_modelling_workspace_init.html",
    "app/templates/partials/_modelling_workspace_context_revenue.html",
    "app/templates/partials/_modelling_workspace_context_opex.html",
    "app/templates/partials/_modelling_workspace_context_capex.html",
    "app/templates/partials/_modelling_workspace_context_debt.html",
    "app/templates/partials/_modelling_workspace_context_tax.html",
    # Reporting content partials — UI-6 wraps them but never modifies them.
    "app/templates/partials/exec_summary.html",
    "app/templates/partials/ic_pack.html",
    "app/templates/partials/credit_pack.html",
    "app/templates/partials/lender_case.html",
    "app/templates/partials/scenario_fs_compare.html",
    "app/templates/partials/credit_summary.html",
    "app/templates/partials/covenant_dashboard.html",
    "app/templates/partials/covenant_timeline.html",
    "app/templates/partials/scenario_sensitivity.html",
    "app/templates/partials/scenario_compare_multi.html",
    "app/templates/partials/bess_revenue_breakdown.html",
    "app/templates/partials/bess_asset_dashboard.html",
]


class TestForbiddenPathsUntouched:
    @pytest.mark.parametrize("relpath", FORBIDDEN_PATHS)
    def test_path_unchanged(self, relpath, repo_diff):
        if not (REPO_ROOT / relpath).exists():
            pytest.skip(f"{relpath} does not exist in repo")
        assert relpath not in repo_diff.changed_paths, (
            f"UI-6 must not modify {relpath}; presentation only. "
            f"Changed: {sorted(repo_diff.changed_paths)}"
        )


class TestBaseHtmlAdditiveOnly:
    def test_base_html_diff_is_minimal(self, repo_diff):
        if "app/templates/base.html" not in repo_diff.changed_paths:
            return
        hunks = repo_diff.hunks_for("app/templates/base.html")
        added_lines = [h["content"] for h in hunks if h["op"] == "+"]
        removed_lines = [h["content"] for h in hunks if h["op"] == "-"]
        for needle in (
            "/static/styles.css", "/static/tokens.css",
            "/static/chrome.css", "/static/sheet-tabs.css",
            "/static/workspace.css", "/static/modelling-workspace.css",
            "/static/statements-reporting.css",
            "/static/power-user.css",
            '<header class="top-header">',
        ):
            assert not any(needle in line for line in removed_lines), (
                f"UI-6 must not remove existing line containing {needle!r}."
            )
        inside_jinja = False
        for line in added_lines:
            stripped = line.strip()
            if not stripped:
                continue
            if inside_jinja:
                if "#}" in stripped:
                    inside_jinja = False
                continue
            if stripped.startswith("{#"):
                if "#}" not in stripped:
                    inside_jinja = True
                continue
            assert stripped.startswith("<link"), (
                f"base.html diff contains an unexpected added line: {line!r}"
            )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class _RepoDiff:
    def __init__(self) -> None:
        import subprocess
        out = subprocess.run(
            ["git", "diff", "--name-only", "origin/main", "--"],
            cwd=str(REPO_ROOT), check=True, capture_output=True, text=True,
        )
        self.changed_paths = {
            line.strip() for line in out.stdout.splitlines() if line.strip()
        }
        self._hunks: dict[str, list[dict]] = {}
        for path in sorted(self.changed_paths):
            self._hunks[path] = self._parse_hunks(path)

    def _parse_hunks(self, path: str) -> list[dict]:
        import subprocess
        proc = subprocess.run(
            ["git", "diff", "origin/main", "--", path],
            cwd=str(REPO_ROOT), check=True, capture_output=True, text=True,
        )
        hunks: list[dict] = []
        for line in proc.stdout.splitlines():
            if not line or line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
                continue
            if line.startswith("+"):
                hunks.append({"op": "+", "content": line[1:]})
            elif line.startswith("-"):
                hunks.append({"op": "-", "content": line[1:]})
        return hunks

    def hunks_for(self, path: str) -> list[dict]:
        return list(self._hunks.get(path, []))


@pytest.fixture(scope="session")
def repo_diff():
    return _RepoDiff()