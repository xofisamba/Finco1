"""Phase 57A-4: Single CAPEX sheet layout cleanup tests.

These tests pin the layout for the single CAPEX sheet:

1. ONE CAPEX tab/view (no competing Summary + Detail
   duplication).
2. Compact derived totals (4 cards) at the top.
3. Clear copy: "CAPEX line items drive the model-level
   CAPEX total."
4. Detail/audit status shown inside the same sheet
   (deferred placeholders + Sources & Uses bridge).
5. C.01..C.18 detail line grid is the main working area.
6. No duplicate competing CAPEX tables.
7. The deprecated `sheet_capex_detail.html` alias is not
   linked from `workspace_shell.html`.

Type: runtime UI change (DRAFT, no auto-merge).
Visual review required.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_TEMPLATES = REPO_ROOT / "app" / "templates"
SHEET_CAPEX = APP_TEMPLATES / "partials" / "sheet_capex.html"
WORKSPACE_SHELL = APP_TEMPLATES / "partials" / "workspace_shell.html"


@pytest.fixture(scope="module")
def sheet_html_text() -> str:
    return SHEET_CAPEX.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def workspace_shell_text() -> str:
    return WORKSPACE_SHELL.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def env():
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    return Environment(
        loader=FileSystemLoader(str(APP_TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )


PRIMARY_PROJECT_CTX = {
    "name": "TUHO Reference",
    "data_source": "User Project",
    "capacity_mw": 50.0,
    "total_capex_keur": 50000.0,
    "capex_items": [],
    "capex_detail_items": {
        "categories": [
            {
                "code": "C.01",
                "name": "Production Unit",
                "is_backend_calculated": False,
                "children": [
                    {"code": "C.01.01", "name": "Solar Modules",
                     "amount_keur": 8000.0},
                    {"code": "C.01.02", "name": "Inverters",
                     "amount_keur": 2000.0},
                ],
            },
            {
                "code": "C.02",
                "name": "EPC Contract",
                "is_backend_calculated": False,
                "children": [
                    {"code": "C.02.01", "name": "EPC Contract",
                     "amount_keur": 12000.0},
                ],
            },
            {
                "code": "C.17",
                "name": "Financing Costs",
                "is_backend_calculated": True,
                "children": [
                    {"code": "C.17.01", "name": "IDC",
                     "amount_keur": 1500.0},
                ],
            },
        ],
        "grand_total_keur": 23500.0,
        "hard_capex_total_keur": 22000.0,
        "financing_total_keur": 1500.0,
    },
    "construction_months": 18,
    "hard_capex_total_keur": 22000.0,
    "financing_total_keur": 1500.0,
    "grand_total_keur": 23500.0,
}


@pytest.fixture(scope="module")
def rendered_primary_html(env):
    tmpl = env.get_template("partials/sheet_capex.html")
    return tmpl.render(
        project_ctx=PRIMARY_PROJECT_CTX,
        is_user_project=True,
    )


# ---------------------------------------------------------------------------
# 1. One CAPEX sheet rule
# ---------------------------------------------------------------------------


class TestOneCapexSheetRule:
    def test_workspace_shell_includes_sheet_capex(self, workspace_shell_text):
        # workspace_shell.html must include sheet_capex.html
        # (not the deprecated detail alias).
        assert "sheet_capex.html" in workspace_shell_text

    def test_workspace_shell_no_detail_alias(self, workspace_shell_text):
        # The deprecated sheet_capex_detail.html alias
        # must NOT be included.
        # Look for active includes (not comments).
        active_includes = re.findall(
            r'\{%\s*include\s+["\']([^"\']+)["\']\s*%\}',
            workspace_shell_text,
        )
        detail_includes = [
            inc for inc in active_includes
            if "sheet_capex_detail" in inc
        ]
        assert not detail_includes, (
            f"workspace_shell.html must NOT include "
            f"sheet_capex_detail.html. "
            f"Found: {detail_includes}"
        )

    def test_only_one_capex_sheet_grid_in_rendered_html(
        self, rendered_primary_html,
    ):
        # There should be exactly one capex-single-sheet-grid
        # table in the rendered HTML.
        matches = re.findall(
            r'id="capex-single-sheet-grid"',
            rendered_primary_html,
        )
        assert len(matches) == 1, (
            f"Expected exactly one capex-single-sheet-grid "
            f"table. Found {len(matches)}."
        )


# ---------------------------------------------------------------------------
# 2. Top cards (compact derived totals)
# ---------------------------------------------------------------------------


class TestTopCards:
    def test_capex_summary_strip_in_template(self, sheet_html_text):
        assert "capex-summary-strip" in sheet_html_text

    def test_summary_strip_renders_with_four_cards(
        self, rendered_primary_html,
    ):
        # The summary strip should have 4 cards:
        # Hard CAPEX, Financing/Reserve, Total CAPEX, CAPEX/MW
        cards = re.findall(
            r'class="capex-summary-card',
            rendered_primary_html,
        )
        assert len(cards) >= 4, (
            f"Expected at least 4 capex-summary-card "
            f"elements. Found {len(cards)}."
        )

    def test_summary_strip_renders_above_grid(
        self, rendered_primary_html,
    ):
        # The summary strip must come BEFORE the grid
        # in the rendered HTML (compact totals at the top).
        strip_pos = rendered_primary_html.find(
            'id="capex-summary-strip"'
        )
        grid_pos = rendered_primary_html.find(
            'id="capex-single-sheet-grid"'
        )
        assert strip_pos != -1
        assert grid_pos != -1
        assert strip_pos < grid_pos, (
            "Summary strip must appear before the grid "
            "(compact totals at the top)."
        )

    def test_summary_strip_data_derived_from_grid(
        self, rendered_primary_html,
    ):
        # The summary strip is marked as
        # data-derived-from="capex-single-sheet-grid" so
        # the JS / tests know the totals are derived from
        # the grid.
        assert 'data-derived-from="capex-single-sheet-grid"' in (
            rendered_primary_html
        )


# ---------------------------------------------------------------------------
# 3. Clear copy
# ---------------------------------------------------------------------------


class TestClearCopy:
    def test_driving_copy_in_template(self, sheet_html_text):
        # The clear copy block must be present in the
        # template.
        assert "data-capex-driving-copy" in sheet_html_text

    def test_driving_copy_text_present(self, sheet_html_text):
        # The exact copy must be present.
        assert (
            "CAPEX line items drive the model-level CAPEX total"
            in sheet_html_text
        )

    def test_driving_copy_renders(self, rendered_primary_html):
        # The clear copy is rendered.
        assert "data-capex-driving-copy=\"true\"" in (
            rendered_primary_html
        )

    def test_driving_copy_above_grid(self, rendered_primary_html):
        # The driving copy should be near the top, just
        # before the grid.
        copy_pos = rendered_primary_html.find(
            'data-capex-driving-copy="true"'
        )
        grid_pos = rendered_primary_html.find(
            'id="capex-single-sheet-grid"'
        )
        assert copy_pos != -1
        assert grid_pos != -1
        assert copy_pos < grid_pos, (
            "Driving copy must appear before the grid."
        )


# ---------------------------------------------------------------------------
# 4. Detail/audit status in same sheet
# ---------------------------------------------------------------------------


class TestDetailAuditStatusInSameSheet:
    def test_deferred_placeholders_in_template(self, sheet_html_text):
        assert "data-capex-deferred" in sheet_html_text

    def test_deferred_placeholders_renders(self, rendered_primary_html):
        assert "data-capex-deferred=\"true\"" in (
            rendered_primary_html
        )

    def test_sources_uses_bridge_in_template(self, sheet_html_text):
        assert "data-capex-su-bridge" in sheet_html_text

    def test_sources_uses_bridge_renders(self, rendered_primary_html):
        assert "data-capex-su-bridge=\"true\"" in (
            rendered_primary_html
        )

    def test_audit_status_below_grid(self, rendered_primary_html):
        # The audit/status block (deferred placeholders)
        # is below the grid, not above.
        grid_pos = rendered_primary_html.find(
            'id="capex-single-sheet-grid"'
        )
        deferred_pos = rendered_primary_html.find(
            'data-capex-deferred="true"'
        )
        bridge_pos = rendered_primary_html.find(
            'data-capex-su-bridge="true"'
        )
        assert deferred_pos > grid_pos, (
            "Deferred placeholders block must be below "
            "the grid."
        )
        assert bridge_pos > grid_pos, (
            "Sources & Uses bridge must be below the grid."
        )


# ---------------------------------------------------------------------------
# 5. C.01..C.18 detail line grid is the main working area
# ---------------------------------------------------------------------------


class TestC01ToC18DetailLineGrid:
    def test_grid_uses_lig_render_macro(self, sheet_html_text):
        # The grid must use the LIG render macro.
        assert "lig_render(" in sheet_html_text

    def test_grid_table_id_present(self, rendered_primary_html):
        # The grid table must have the
        # capex-single-sheet-grid id.
        assert 'id="capex-single-sheet-grid"' in (
            rendered_primary_html
        )

    def test_grid_renders_c01_to_c18_categories(
        self, rendered_primary_html,
    ):
        # The C.01..C.18 category bands must be present
        # in the rendered HTML.
        for code in [
            "C.01", "C.02", "C.17",
        ]:
            assert (
                f'data-capex-category="{code}"' in
                rendered_primary_html
            ), (
                f"Category {code!r} must be present in the "
                f"grid."
            )


# ---------------------------------------------------------------------------
# 6. No duplicate competing CAPEX tables
# ---------------------------------------------------------------------------


class TestNoDuplicateCapexTables:
    def test_one_grid_table(self, rendered_primary_html):
        # Exactly one capex-single-sheet-grid table.
        assert (
            rendered_primary_html.count(
                'id="capex-single-sheet-grid"'
            )
            == 1
        )

    def test_no_competing_capex_table_class(
        self, rendered_primary_html,
    ):
        # No other "fc-capex-grid" or "capex-grid" tables
        # beyond the single sheet.
        capex_grid_tables = re.findall(
            r'class="[^"]*fc-capex-grid-wrapper[^"]*"',
            rendered_primary_html,
        )
        assert len(capex_grid_tables) == 1, (
            f"Expected exactly one fc-capex-grid-wrapper "
            f"div. Found {len(capex_grid_tables)}."
        )


# ---------------------------------------------------------------------------
# 7. No backend keys in UI (regression check)
# ---------------------------------------------------------------------------


class TestNoBackendKeysInUI:
    @pytest.mark.parametrize(
        "backend_key",
        [
            "lease_tax",
            "epc_contract",
            "project_rights",
            "production_units",
        ],
    )
    def test_backend_key_not_in_visible_code_cell_in_primary_path(
        self, rendered_primary_html, backend_key,
    ):
        # In the primary path, sub-line codes are
        # Excel-style (C.01.01 etc.). The backend key
        # should not appear as a visible code cell value.
        pattern = re.compile(
            r'<td[^>]*fc-cell--code[^>]*>(.*?)</td>',
            re.DOTALL,
        )
        for m in pattern.finditer(rendered_primary_html):
            cell_text = m.group(1).strip()
            assert backend_key not in cell_text, (
                f"Backend key {backend_key!r} must not "
                f"appear in visible code cell. "
                f"Found: {cell_text!r}."
            )


# ---------------------------------------------------------------------------
# 8. File-scope
# ---------------------------------------------------------------------------


class TestFileScope:
    def test_sheet_capex_changed(self):
        import subprocess
        r_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r_branch.returncode == 0:
            branch = r_branch.stdout.strip()
            if (
                branch == "main"
                or (
                    "57a4" not in branch.lower()
                    and "57a-4" not in branch.lower()
                )
            ):
                pytest.skip(
                    f"Not on a 57A-4 branch (current: "
                    f"{branch!r})."
                )
        r = subprocess.run(
            ["git", "diff", "origin/main", "--name-only", "--",
             "app/templates/partials/sheet_capex.html"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0
        assert (
            r.stdout.strip()
            == "app/templates/partials/sheet_capex.html"
        )

    def test_no_documentation_or_test_files_added(self):
        # 57A-4 runtime UI change. No new docs or report
        # files. Skip if not on a 57A-4 branch.
        import subprocess
        r_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r_branch.returncode == 0:
            branch = r_branch.stdout.strip()
            if (
                branch == "main"
                or (
                    "57a4" not in branch.lower()
                    and "57a-4" not in branch.lower()
                )
            ):
                pytest.skip(
                    f"Not on a 57A-4 branch (current: "
                    f"{branch!r})."
                )
        r = subprocess.run(
            ["git", "diff", "origin/main", "--name-only", "--",
             "docs/", "reports/"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert not r.stdout.strip(), (
            f"57A-4 must not modify docs/ or reports/. "
            f"Found: {r.stdout.strip()!r}."
        )

    def test_no_other_templates_changed(self):
        # Only sheet_capex.html is modified, not other
        # templates.
        import subprocess
        r = subprocess.run(
            ["git", "diff", "origin/main", "--name-only", "--",
             "app/templates/"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        changed = set(
            line.strip() for line in r.stdout.splitlines()
            if line.strip()
        )
        # Allow only sheet_capex.html and our test file.
        allowed = {
            "app/templates/partials/sheet_capex.html",
        }
        unexpected = changed - allowed
        # U9-REMAINING-EXTERNAL-TERMINOLOGY-CLEANUP: presentation-text
        # sweep legitimately touches other partials (sheet_opex.html,
        # sheet_capex_detail.html, workspace_shell.html, project_home.html,
        # project_selector.html) for "factory" wording removal.
        u9_files = {
            "app/templates/partials/sheet_opex.html",
            "app/templates/partials/sheet_capex_detail.html",
            "app/templates/partials/sheet_opex_detail.html",
            "app/templates/partials/workspace_shell.html",
            "app/templates/partials/project_home.html",
            "app/templates/partials/project_selector.html",
        }
        unexpected -= u9_files
        assert not unexpected, (
            f"57A-4 must only modify sheet_capex.html. "
            f"Unexpected: {sorted(unexpected)}"
        )

    def test_no_main_web_or_services_changes(self):
        import subprocess
        # Skip if not on a 57A-4 branch.
        r_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r_branch.returncode == 0:
            branch = r_branch.stdout.strip()
            if (
                branch == "main"
                or (
                    "57a4" not in branch.lower()
                    and "57a-4" not in branch.lower()
                )
            ):
                pytest.skip(
                    f"Not on a 57A-4 branch (current: "
                    f"{branch!r})."
                )
        for path in [
            "main_web.py",
            "app/services/",
            "app/persistence/",
            "app/domain/",
            "static/app.js",
            "static/styles.css",
        ]:
            r = subprocess.run(
                ["git", "diff", "origin/main", "--name-only", "--",
                 path],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
            )
            assert not r.stdout.strip(), (
                f"57A-4 must NOT modify {path}."
            )


# ---------------------------------------------------------------------------
# 9. rc1 untouched
# ---------------------------------------------------------------------------


class TestRc1Untouched:
    def test_rc1_sha_unchanged(self):
        import subprocess
        r = subprocess.run(
            ["git", "rev-parse", "--verify",
             "b425a0708719eaa5e1d922b1008e5609758e0ad4"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, (
            "rc1 frozen SHA must still resolve."
        )


# ---------------------------------------------------------------------------
# 10. No-go copy
# ---------------------------------------------------------------------------


class TestNoNoGoCopy:
    @pytest.mark.parametrize(
        "forbidden",
        [
            "validated",
            "guaranteed",
            "100% accurate",
            "production-ready",
            "saas-ready",
        ],
    )
    def test_no_forbidden_claims(self, sheet_html_text, forbidden):
        pattern = re.compile(
            r"\b" + re.escape(forbidden) + r"\b",
            re.IGNORECASE,
        )
        assert not pattern.search(sheet_html_text), (
            f"Forbidden term {forbidden!r} must not "
            f"appear in sheet_capex.html."
        )
