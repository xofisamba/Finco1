"""Phase 57A-3: CAPEX hide backend keys tests.

These tests pin the rule that backend keys (snake_case)
are NEVER visible to the user. They are preserved in
``data-capex-code`` attributes for stable identification.

Visible codes follow the Excel CAPEX model
(C.01..C.18 with sub-lines). The full dotted code is
preserved in ``data-capex-code-full``.

Type: runtime UI change (DRAFT, no auto-merge).
Visual review required.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_TEMPLATES = REPO_ROOT / "app" / "templates"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sheet_html_text() -> str:
    return (APP_TEMPLATES / "partials" / "sheet_capex.html").read_text(
        encoding="utf-8"
    )


@pytest.fixture(scope="module")
def env():
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    return Environment(
        loader=FileSystemLoader(str(APP_TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )


# A flat 6-section summary project context, with backend
# keys as `item.code`. This is the data the fallback path
# consumes in the post-57A-3 sheet.
FALLBACK_PROJECT_CTX = {
    "name": "Test Project",
    "data_source": "User Project",
    "capacity_mw": 50.0,
    "total_capex_keur": 25075.0,
    "capex_items": [
        {"code": "production_units", "name": "Production Unit",
         "amount_keur": 5000.0},
        {"code": "epc_contract", "name": "EPC Contract",
         "amount_keur": 12000.0},
        {"code": "epc_other", "name": "EPC Other",
         "amount_keur": 800.0},
        {"code": "project_rights", "name": "Project Rights",
         "amount_keur": 3024.5},
        {"code": "project_acquisition", "name": "Project Acquisition",
         "amount_keur": 1500.0},
        {"code": "ops_prep", "name": "Operations Prep",
         "amount_keur": 250.0},
        {"code": "construction_mgmt_a", "name": "Construction Mgmt A",
         "amount_keur": 600.0},
        {"code": "construction_mgmt_b", "name": "Construction Mgmt B",
         "amount_keur": 400.0},
        {"code": "commissioning", "name": "Commissioning",
         "amount_keur": 250.0},
        {"code": "audit_legal", "name": "Audit & Legal",
         "amount_keur": 350.0},
        {"code": "lease_tax", "name": "Lease & Tax",
         "amount_keur": 200.0},
        {"code": "insurances", "name": "Insurances",
         "amount_keur": 500.5},
        {"code": "contingencies", "name": "Contingencies",
         "amount_keur": 200.0},
        {"code": "taxes", "name": "Import Taxes",
         "amount_keur": 0.0},  # 0 — should be filtered
    ],
    "capex_detail_items": None,
    "construction_months": 18,
    "hard_capex_total_keur": 25075.0,
    "financing_total_keur": 0.0,
    "grand_total_keur": 25075.0,
}


@pytest.fixture(scope="module")
def rendered_fallback_html(env):
    tmpl = env.get_template("partials/sheet_capex.html")
    return tmpl.render(
        project_ctx=FALLBACK_PROJECT_CTX,
        is_user_project=True,
    )


# ---------------------------------------------------------------------------
# 1. Backend keys must NOT appear as visible text
# ---------------------------------------------------------------------------


class TestBackendKeysNotVisible:
    @pytest.mark.parametrize(
        "backend_key",
        [
            "lease_tax",
            "epc_contract",
            "project_rights",
            "production_units",
            "epc_other",
            "project_acquisition",
            "ops_prep",
            "construction_mgmt_a",
            "construction_mgmt_b",
            "commissioning",
            "audit_legal",
            "insurances",
            "contingencies",
            "taxes",
        ],
    )
    def test_backend_key_not_in_visible_code_cell(
        self, rendered_fallback_html, backend_key,
    ):
        """The backend key must NOT appear as the visible
        value in a code cell. It may appear in
        ``data-capex-code="..."`` attributes (which are
        hidden)."""
        # Find all visible code cell content (i.e. text
        # between <td class="lig-cell fc-cell--code" ...>
        # and </td>). The backend key must NOT be the
        # text content of any such cell.
        # The LIG macro renders code cells as:
        #   <td class="lig-cell fc-cell fc-cell--code"
        #       ...>VALUE</td>
        # We extract the VALUE between > and </td>.
        pattern = re.compile(
            r'<td[^>]*fc-cell--code[^>]*>(.*?)</td>',
            re.DOTALL,
        )
        for m in pattern.finditer(rendered_fallback_html):
            cell_text = m.group(1).strip()
            assert backend_key not in cell_text, (
                f"Backend key {backend_key!r} must not "
                f"appear as visible code-cell text. "
                f"Found in cell: {cell_text!r}."
            )

    @pytest.mark.parametrize(
        "backend_key",
        [
            "lease_tax",
            "epc_contract",
            "project_rights",
        ],
    )
    def test_canonical_backend_keys_not_in_visible_text(
        self, rendered_fallback_html, backend_key,
    ):
        # The canonical backend keys must not appear as
        # visible text anywhere in the rendered HTML.
        # (They may appear in attributes.)
        # Strip all HTML tags and check the remaining
        # text. If the backend key appears, the regex
        # finds it as a non-tag word.
        # First, strip attributes by removing
        # anything between < and >.
        # Actually, attributes are inside <>. We want to
        # check the visible text, which is between > and
        # <. Use a simple approach: find all `>text<`
        # sequences.
        visible = re.findall(
            r'>([^<]*)<',
            rendered_fallback_html,
        )
        visible_text = " ".join(visible)
        assert backend_key not in visible_text, (
            f"Backend key {backend_key!r} must not "
            f"appear as visible text in the rendered "
            f"CAPEX sheet."
        )


# ---------------------------------------------------------------------------
# 2. Excel-style codes must appear in the visible Code column
# ---------------------------------------------------------------------------


class TestExcelStyleCodesVisible:
    @pytest.mark.parametrize(
        "excel_code",
        [
            "C.02.01",  # epc_contract
            "C.01.01",  # production_units
            "C.16.01",  # project_rights
            "C.07.01",  # lease_tax
            "C.06.01",  # insurances
            "C.13.01",  # contingencies
        ],
    )
    def test_excel_code_in_visible_code_cell(
        self, rendered_fallback_html, excel_code,
    ):
        """Each mapped backend key should produce a
        visible Excel-style code like C.02.01.

        Note: C.14.01 (taxes) is intentionally not in
        this list because the sample project sets
        taxes to amount 0.0, which is filtered out
        by the fallback path's
        ``amount_keur|float > 0`` guard.
        """
        pattern = re.compile(
            r'<td[^>]*fc-cell--code[^>]*>\s*'
            + re.escape(excel_code)
            + r'\s*</td>',
            re.DOTALL,
        )
        assert pattern.search(rendered_fallback_html), (
            f"Excel-style code {excel_code!r} must "
            f"appear in a visible code cell. "
            f"(Rendered length: "
            f"{len(rendered_fallback_html)})"
        )


# ---------------------------------------------------------------------------
# 3. Backend keys preserved in data-capex-code attributes
# ---------------------------------------------------------------------------


class TestBackendKeyDataAttribute:
    @pytest.mark.parametrize(
        "backend_key",
        [
            "lease_tax",
            "epc_contract",
            "project_rights",
            "production_units",
            "epc_other",
            "project_acquisition",
            "ops_prep",
            "construction_mgmt_a",
            "construction_mgmt_b",
            "commissioning",
            "audit_legal",
            "insurances",
            "contingencies",
            "taxes",
        ],
    )
    def test_backend_key_in_data_capex_code_attr(
        self, rendered_fallback_html, backend_key,
    ):
        """The backend key must be preserved in
        ``data-capex-code="..."`` attribute for stable
        identification."""
        # Note: 'taxes' has amount 0 and is filtered out
        # by the fallback path, so it will not be in the
        # rendered HTML. We skip that one.
        if backend_key == "taxes":
            pytest.skip(
                "taxes has amount 0 and is filtered out "
                "by the fallback path."
            )
        pattern = re.compile(
            r'data-capex-code="'
            + re.escape(backend_key)
            + r'"'
        )
        assert pattern.search(rendered_fallback_html), (
            f"Backend key {backend_key!r} must be "
            f"preserved in data-capex-code attribute."
        )

    @pytest.mark.parametrize(
        "excel_code,backend_key",
        [
            ("C.02.01", "epc_contract"),
            ("C.01.01", "production_units"),
            ("C.16.01", "project_rights"),
            ("C.07.01", "lease_tax"),
        ],
    )
    def test_data_capex_code_full_has_excel_code(
        self, rendered_fallback_html, excel_code, backend_key,
    ):
        """The Excel-style code must be preserved in
        ``data-capex-code-full="..."`` attribute."""
        pattern = re.compile(
            r'data-capex-code-full="'
            + re.escape(excel_code)
            + r'"'
        )
        assert pattern.search(rendered_fallback_html), (
            f"Excel-style code {excel_code!r} (for "
            f"backend key {backend_key!r}) must be "
            f"preserved in data-capex-code-full "
            f"attribute."
        )


# ---------------------------------------------------------------------------
# 4. Template-level: backend_to_display_code mapping
# ---------------------------------------------------------------------------


class TestTemplateMapping:
    def test_template_has_backend_to_display_code_map(
        self, sheet_html_text,
    ):
        assert "backend_to_display_code" in sheet_html_text

    def test_template_maps_lease_tax(self, sheet_html_text):
        # Lease & Tax must map to C.07.01.
        assert re.search(
            r'"lease_tax":\s*"C\.07\.01"',
            sheet_html_text,
        )

    def test_template_maps_epc_contract(self, sheet_html_text):
        # EPC Contract must map to C.02.01.
        assert re.search(
            r'"epc_contract":\s*"C\.02\.01"',
            sheet_html_text,
        )

    def test_template_maps_project_rights(self, sheet_html_text):
        # Project Rights must map to C.16.01.
        assert re.search(
            r'"project_rights":\s*"C\.16\.01"',
            sheet_html_text,
        )

    def test_template_falls_back_to_dash_for_unknown_keys(
        self, sheet_html_text,
    ):
        # If a backend key has no display-code mapping,
        # the visible code cell must show a dash (em-dash
        # U+2014), not the snake_case key.
        # The literal em-dash is used in the template.
        assert (
            "backend_to_display_code.get"
            in sheet_html_text
        )
        # The em-dash character (U+2014) must appear in
        # the template, used as the fallback default.
        assert "\u2014" in sheet_html_text
        # Pattern: backend_to_display_code.get(item.code, "—")
        # The fallback is a quoted em-dash.
        assert re.search(
            r'backend_to_display_code\.get\(item\.code,\s*"\u2014"\)',
            sheet_html_text,
        ), (
            "Template must call "
            "backend_to_display_code.get(item.code, \"\u2014\")"
        )


# ---------------------------------------------------------------------------
# 5. No backend keys in the line-name label
# ---------------------------------------------------------------------------


class TestLineLabelsVisible:
    def test_label_shows_human_readable_name(
        self, rendered_fallback_html,
    ):
        # The display name "Production Unit" should be in
        # a label cell, not the backend key.
        pattern = re.compile(
            r'<td[^>]*fc-grid-col-label[^>]*>\s*Production Unit\s*</td>',
            re.DOTALL,
        )
        assert pattern.search(rendered_fallback_html), (
            "Human-readable label 'Production Unit' must "
            "appear in a label cell."
        )

    def test_label_does_not_show_backend_key(
        self, rendered_fallback_html,
    ):
        # The backend key "production_units" must NOT
        # appear inside a label cell.
        pattern = re.compile(
            r'<td[^>]*fc-grid-col-label[^>]*>(.*?)</td>',
            re.DOTALL,
        )
        for m in pattern.finditer(rendered_fallback_html):
            cell_text = m.group(1).strip()
            assert "production_units" not in cell_text, (
                f"Backend key must not appear in label "
                f"cell. Found: {cell_text!r}."
            )


# ---------------------------------------------------------------------------
# 6. CAPEX totals unchanged
# ---------------------------------------------------------------------------


class TestTotalsUnchanged:
    def test_hard_capex_total_appears(self, rendered_fallback_html):
        assert "Hard CAPEX Total" in rendered_fallback_html

    def test_total_capex_appears(self, rendered_fallback_html):
        assert "Total CAPEX" in rendered_fallback_html

    def test_subtotal_formatting(self, rendered_fallback_html):
        # The hard CAPEX total should be 25,075.00
        # (sum of 14 backend-key items, taxes filtered out).
        # Verify the amount appears with comma format.
        assert "25,075" in rendered_fallback_html


# ---------------------------------------------------------------------------
# 7. No backend model changes
# ---------------------------------------------------------------------------


class TestNoBackendModelChanges:
    def test_no_changes_to_capex_source_model(self):
        # The backend data model must not be touched.
        # This is a smoke check on the diff.
        import subprocess
        r = subprocess.run(
            ["git", "diff", "main", "--name-only", "--",
             "app/domain/capex/source_model.py"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0
        assert not r.stdout.strip(), (
            "57A-3 must NOT modify "
            "app/domain/capex/source_model.py."
        )

    def test_no_changes_to_main_web(self):
        import subprocess
        r = subprocess.run(
            ["git", "diff", "main", "--name-only", "--",
             "main_web.py"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0
        assert not r.stdout.strip(), (
            "57A-3 must NOT modify main_web.py."
        )

    def test_no_changes_to_app_js_or_styles(self):
        import subprocess
        # Skip if not on a 57A-3 branch.
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
                    "57a3" not in branch.lower()
                    and "57a-3" not in branch.lower()
                )
            ):
                pytest.skip(
                    f"Not on a 57A-3 branch (current: "
                    f"{branch!r})."
                )
        for path in ["static/app.js", "static/styles.css"]:
            r = subprocess.run(
                ["git", "diff", "main", "--name-only", "--",
                 path],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
            )
            assert not r.stdout.strip(), (
                f"57A-3 must NOT modify {path}."
            )


# ---------------------------------------------------------------------------
# 8. File-scope: only sheet_capex.html is modified
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
                    "57a3" not in branch.lower()
                    and "57a-3" not in branch.lower()
                )
            ):
                pytest.skip(
                    f"Not on a 57A-3 branch (current: "
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
        # 57A-3 runtime UI change. No new docs or report
        # files in this PR. The docs and report for the
        # CAPEX 2.0 arc come from 57A-2.
        # We compare against origin/main so that
        # already-merged main commits (e.g. 57A-2) do
        # not show up in the diff.
        # Skip if we are not on a 57A-3 branch.
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
                    "57a3" not in branch.lower()
                    and "57a-3" not in branch.lower()
                )
            ):
                pytest.skip(
                    f"Not on a 57A-3 branch (current: "
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
            f"57A-3 must not modify docs/ or reports/. "
            f"Found: {r.stdout.strip()!r}."
        )

    def test_only_sheet_capex_and_test_changed(self):
        import subprocess
        r_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r_branch.returncode == 0:
            branch = r_branch.stdout.strip()
            if branch == "main":
                pytest.skip(
                    "On main branch; 57A-3 has been merged. "
                    "This test is only meaningful on the "
                    "57A-3 unmerged branch."
                )
            if (
                "57a3" not in branch.lower()
                and "57a-3" not in branch.lower()
            ):
                pytest.skip(
                    f"Not on a 57A-3 branch (current: "
                    f"{branch!r})."
                )
        r = subprocess.run(
            ["git", "diff", "origin/main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        changed = set(
            line.strip() for line in r.stdout.splitlines()
            if line.strip()
        )
        allowed = {
            "app/templates/partials/sheet_capex.html",
            "tests/test_phase57a3_capex_hide_backend_keys.py",
        }
        unexpected = changed - allowed
        assert not unexpected, (
            f"57A-3 must only modify the allowed files. "
            f"Unexpected: {sorted(unexpected)}"
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
            "trust me",
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
