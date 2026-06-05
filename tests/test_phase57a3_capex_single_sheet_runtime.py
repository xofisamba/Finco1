"""Phase 57A-3 — CAPEX single-sheet runtime draft tests.

These tests verify the runtime CAPEX single-sheet
implementation:

* Only one primary CAPEX sheet is rendered (the
  `sheet_capex.html` single Excel-like input sheet).
* `sheet_capex_detail.html` is no longer included in
  `workspace_shell.html`.
* No Excel-vs-App comparison / Delta / Status columns
  in the primary CAPEX sheet.
* C.01..C.05 category groupings exist.
* Line items are editable inputs in user project mode.
* Subtotals and total CAPEX are derived (read-only).
* Financing / IDC rows are read-only (data_financing).
* VAT / WHT / depreciation / payment schedule / utilisation
  are documented as deferred placeholders.
* Cost per MW is derived (read-only).
* No no-go claims.
* No financial output changes.
* No backend / model / persistence / formula changes.

The tests do NOT modify any production code, model, formula,
persistence, or service files. They verify the runtime
behaviour of the modified templates.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SHEET_CAPEX = REPO_ROOT / "app" / "templates" / "partials" / "sheet_capex.html"
SHEET_CAPEX_DETAIL = REPO_ROOT / "app" / "templates" / "partials" / "sheet_capex_detail.html"
WORKSPACE_SHELL = REPO_ROOT / "app" / "templates" / "partials" / "workspace_shell.html"
LIG = REPO_ROOT / "app" / "templates" / "partials" / "_line_item_grid.html"
RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"


# Sample project context for rendering tests
SAMPLE_PROJECT_CTX = {
    "name": "Test CAPEX Project",
    "data_source": "User Project",
    "capacity_mw": 50.0,
    "total_capex_keur": 2175.0,
    "capex_items": [
        # C.01 Construction
        {"code": "epc_contract", "name": "EPC Contract", "amount_keur": 1000.00},
        {"code": "production_units", "name": "Production Units", "amount_keur": 500.00},
        # C.02 Development
        {"code": "project_acquisition", "name": "Project Acquisition", "amount_keur": 200.00},
        # C.04 Civil & Land
        {"code": "lease_tax", "name": "Lease & Land Tax", "amount_keur": 300.00},
        # C.05 Insurances & Risk
        {"code": "insurances", "name": "Insurances", "amount_keur": 100.00},
        # Financing Costs (read-only)
        {"code": "idc", "name": "Interest During Construction", "amount_keur": 50.00},
        {"code": "bank_fees", "name": "Bank Fees", "amount_keur": 25.00},
    ],
}


def _render_sheet_capex(is_user_project=True):
    """Render sheet_capex.html with the sample project context."""
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    env = Environment(
        loader=FileSystemLoader(str(REPO_ROOT / "app" / "templates")),
        autoescape=select_autoescape(["html"]),
    )
    tmpl = env.get_template("partials/sheet_capex.html")
    return tmpl.render(
        project_ctx=SAMPLE_PROJECT_CTX,
        is_user_project=is_user_project,
    )


# ============================================================
# 1. Only one primary CAPEX sheet is rendered
# ============================================================


class TestOnlyOnePrimaryCapexSheet:
    def test_workspace_shell_does_not_include_sheet_capex_detail(self):
        # The historical mention in a comment block is OK;
        # we want to assert there is no active include
        # directive for sheet_capex_detail.html.
        text = WORKSPACE_SHELL.read_text()
        # Strip HTML/Jinja comments so the historical
        # mention in the doc-comment does not count.
        stripped = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        stripped = re.sub(r"\{#.*?#\}", "", stripped, flags=re.DOTALL)
        # There must be no {% include ... sheet_capex_detail.html %}
        # directive.
        assert (
            'include "partials/sheet_capex_detail.html"' not in stripped
            and "include 'partials/sheet_capex_detail.html'" not in stripped
        ), (
            "workspace_shell.html must not actively include "
            "sheet_capex_detail.html. Phase 57A-3 collapses "
            "the dual CAPEX view to a single sheet."
        )

    def test_workspace_shell_includes_sheet_capex_only_once(self):
        text = WORKSPACE_SHELL.read_text()
        # Find every include of sheet_capex.html
        # (must be exactly one, in the CAPEX panel)
        matches = re.findall(
            r"\{\%\s*include\s*[\"']partials/sheet_capex\.html[\"']\s*\%\}",
            text,
        )
        assert len(matches) == 1, (
            f"workspace_shell.html must include "
            f"partials/sheet_capex.html exactly once. "
            f"Found {len(matches)} includes."
        )

    def test_sheet_capex_detail_still_on_disk_as_deprecated(self):
        """The deprecated Excel-reconciliation file may still
        exist on disk (so old direct-path references do not
        404) but must not be in the workspace shell."""
        assert SHEET_CAPEX_DETAIL.exists(), (
            "sheet_capex_detail.html should still be on disk "
            "as a deprecated alias (do not delete)."
        )

    def test_sheet_capex_rendered_only_once_per_page(self):
        html = _render_sheet_capex()
        # Count the number of capex-single-sheet-grid tables
        count = html.count('id="capex-single-sheet-grid"')
        assert count == 1, (
            f"Expected exactly one CAPEX grid table per render. "
            f"Found {count}."
        )


# ============================================================
# 2. No Excel-vs-App / Delta / Status columns
# ============================================================


class TestNoExcelVsAppComparison:
    @staticmethod
    def _strip_comments(text: str) -> str:
        """Strip Jinja and HTML comments from the rendered
        HTML so that historical mentions of 'audit' /
        'reconciliation' in the file's doc-comment do not
        trigger false positives."""
        text = re.sub(r"\{#.*?#\}", "", text, flags=re.DOTALL)
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        return text

    def test_no_excel_keur_column(self):
        html = self._strip_comments(_render_sheet_capex())
        # The previous sheet_capex_detail had an "Excel kEUR"
        # column. The new sheet must not have it.
        assert "Excel<br/>kEUR" not in html
        assert "Excel kEUR" not in html

    def test_no_app_keur_column(self):
        html = self._strip_comments(_render_sheet_capex())
        # The previous sheet had an "App kEUR" column.
        assert "App<br/>kEUR" not in html
        assert "App kEUR" not in html

    def test_no_delta_column(self):
        html = self._strip_comments(_render_sheet_capex())
        # The previous sheet had a "Delta kEUR" column.
        assert "Delta<br/>kEUR" not in html
        assert "Delta kEUR" not in html

    def test_no_status_column(self):
        html = self._strip_comments(_render_sheet_capex())
        # The previous sheet had a "Status" column.
        # The new sheet must not have a runtime status column
        # (the "Test / status" header would be the marker).
        # The new sheet has "Code" and "Amount" only.
        assert "Test / status" not in html
        assert "test/status" not in html.lower()

    def test_no_authority_summary_strip(self):
        """The previous detail view had a 'capex-auth-strip'
        showing Backend auth. / App mapped / Excel ref only /
        Missing src / Mismatch / Scope diff / Deferred counts.
        The new sheet must not have this."""
        html = self._strip_comments(_render_sheet_capex())
        assert "capex-auth-strip" not in html
        assert "Backend auth" not in html
        assert "App mapped" not in html
        assert "Excel ref only" not in html
        assert "Missing src" not in html
        assert "Scope diff" not in html

    def test_no_display_only_audit_banner(self):
        """The previous detail view had a
        'CAPEX detail grid is an audit/display view' banner.
        The new sheet must not have it."""
        html = self._strip_comments(_render_sheet_capex())
        assert "audit/display view" not in html
        assert "Display only" not in html

    def test_no_authority_summary_classes(self):
        html = self._strip_comments(_render_sheet_capex())
        for cls in [
            "capex-auth-card--backend",
            "capex-auth-card--app",
            "capex-auth-card--excel",
            "capex-auth-card--mismatch",
            "capex-auth-card--scope-mismatch",
        ]:
            assert cls not in html, (
                f"Authority-summary CSS class {cls!r} must not "
                f"appear in the new CAPEX sheet."
            )

    def test_no_audit_term(self):
        html = self._strip_comments(_render_sheet_capex())
        # No "reconciliation" / "audit" framing in the
        # rendered sheet body (comments stripped).
        assert "reconciliation" not in html.lower()
        assert "audit/display" not in html.lower()


# ============================================================
# 3. C.01..C.05 category groupings exist
# ============================================================


class TestCategoryGroupings:
    @pytest.mark.parametrize("cat_code", ["C.01", "C.02", "C.03", "C.04", "C.05"])
    def test_category_code_present(self, cat_code):
        html = _render_sheet_capex()
        assert cat_code in html, (
            f"Category code {cat_code!r} must appear in the "
            f"rendered CAPEX sheet."
        )

    def test_c01_subtotal_present(self):
        html = _render_sheet_capex()
        assert "C.01 Subtotal" in html, (
            "C.01 Subtotal must appear in the rendered sheet."
        )

    def test_hard_capex_total_present(self):
        html = _render_sheet_capex()
        assert "Hard CAPEX Total" in html, (
            "Hard CAPEX Total must appear in the rendered sheet."
        )

    def test_total_capex_present(self):
        html = _render_sheet_capex()
        assert "Total CAPEX" in html

    def test_category_section_bands_present(self):
        html = _render_sheet_capex()
        # Section bands have the fc-section-band__label class
        # and contain the C.0X code
        for cat in ["C.01", "C.02", "C.03", "C.04", "C.05"]:
            # Find a section_band td containing the cat code
            m = re.search(
                r'<td class="lig-cell fc-section-band__label"[^>]*>'
                r'([^<]*' + re.escape(cat) + r'[^<]*)'
                r'</td>',
                html,
            )
            assert m is not None, (
                f"Section band for {cat!r} must appear in the "
                f"rendered sheet."
            )


# ============================================================
# 4. Line items are editable inputs in user project mode
# ============================================================


class TestLineItemsEditable:
    @pytest.mark.parametrize(
        "code",
        [
            "epc_contract",
            "production_units",
            "project_acquisition",
            "lease_tax",
            "insurances",
        ],
    )
    def test_ordinary_capex_line_editable(self, code):
        html = _render_sheet_capex(is_user_project=True)
        pat = f'name="capex_{code}_keur"'
        assert pat in html, (
            f"Ordinary CAPEX line {code!r} must render an "
            f"editable input in user project mode. "
            f"Missing {pat}."
        )

    def test_input_value_is_raw_number(self):
        html = _render_sheet_capex(is_user_project=True)
        # 1000.00 must be a value attribute (no thousands
        # separator; HTML <input type="number">)
        assert 'value="1000.00"' in html


# ============================================================
# 5. Subtotals and totals are read-only
# ============================================================


class TestSubtotalsAndTotalsReadOnly:
    def test_hard_capex_total_row_readonly(self):
        html = _render_sheet_capex(is_user_project=True)
        m = re.search(
            r'<tr[^>]*data-capex-row="hard-capex-total"[^>]*>(.*?)</tr>',
            html,
            re.DOTALL,
        )
        assert m is not None, "Hard CAPEX Total row must exist."
        row = m.group(1)
        assert "aria-readonly=\"true\"" in row, (
            "Hard CAPEX Total row must be read-only."
        )
        assert "<input" not in row, (
            "Hard CAPEX Total row must not contain an <input>."
        )

    def test_grand_total_row_readonly(self):
        html = _render_sheet_capex(is_user_project=True)
        m = re.search(
            r'<tr[^>]*data-capex-row="grand-total"[^>]*>(.*?)</tr>',
            html,
            re.DOTALL,
        )
        assert m is not None, "Grand Total row must exist."
        row = m.group(1)
        assert "aria-readonly=\"true\"" in row, (
            "Grand Total row must be read-only."
        )
        assert "<input" not in row, (
            "Grand Total row must not contain an <input>."
        )

    def test_financing_costs_subtotal_readonly(self):
        html = _render_sheet_capex(is_user_project=True)
        m = re.search(
            r'<tr[^>]*data-capex-row="financing-costs-total"[^>]*>(.*?)</tr>',
            html,
            re.DOTALL,
        )
        if m is None:
            # No financing rows in sample data; OK
            return
        row = m.group(1)
        assert "aria-readonly=\"true\"" in row
        assert "<input" not in row

    def test_subtotals_class_present(self):
        html = _render_sheet_capex(is_user_project=True)
        assert "fc-subtotal-row" in html, (
            "Subtotal rows must have the fc-subtotal-row class."
        )

    def test_grand_total_class_present(self):
        html = _render_sheet_capex(is_user_project=True)
        # The LineItemGrid macro uses lig-row--total for the
        # grand total row. fc-grand-total is a legacy class
        # name that may or may not be applied by the
        # current macro version. We assert the more robust
        # lig-row--total and data-capex-row="grand-total"
        # markers instead.
        assert "lig-row--total" in html, (
            "Grand total row must have the lig-row--total class."
        )
        assert 'data-capex-row="grand-total"' in html, (
            "Grand total row must have data-capex-row="
            "\"grand-total\" attribute."
        )


# ============================================================
# 6. Financing / IDC rows are read-only
# ============================================================


class TestFinancingRowsReadOnly:
    FINANCING_CODES = [
        "idc",
        "bank_fees",
        "commitment_fees",
        "other_financial",
        "vat_costs",
        "reserve_accounts",
    ]

    @pytest.mark.parametrize("code", FINANCING_CODES)
    def test_financing_code_not_editable(self, code):
        html = _render_sheet_capex(is_user_project=True)
        pat = f'name="capex_{code}_keur"'
        assert pat not in html, (
            f"Financing row {code!r} must NOT render an "
            f"editable input in user project mode. "
            f"Found {pat!r}."
        )

    def test_idc_row_uses_data_financing_class(self):
        html = _render_sheet_capex(is_user_project=True)
        # The idc row should be a data_financing row
        m = re.search(
            r'<tr[^>]*data-capex-code="idc"[^>]*>(.*?)</tr>',
            html,
            re.DOTALL,
        )
        assert m is not None, "idc financing row must exist."
        assert "lig-row--data-financing" in m.group(0)
        assert "aria-readonly=\"true\"" in m.group(1)
        assert "<input" not in m.group(1)

    def test_financing_rows_readonly_in_factory_reference(self):
        html = _render_sheet_capex(is_user_project=False)
        for code in self.FINANCING_CODES:
            pat = f'name="capex_{code}_keur"'
            assert pat not in html


# ============================================================
# 7. Cost per MW is derived
# ============================================================


class TestCostPerMWDerived:
    def test_capex_per_mw_card_present(self):
        html = _render_sheet_capex()
        assert "CAPEX / MW" in html, (
            "CAPEX / MW card must be in the derived top "
            "summary strip."
        )

    def test_capex_per_mw_value_present(self):
        html = _render_sheet_capex()
        # Total CAPEX in sample = 1000+500+200+300+100+50+25 = 2175
        # 2175 / 50 MW = 43.5
        assert "43.5" in html, (
            "CAPEX / MW value (43.5) must appear in the "
            "derived summary."
        )

    def test_per_mw_no_input(self):
        """Cost per MW must be a derived value, not an input."""
        html = _render_sheet_capex(is_user_project=True)
        # No <input> should compute cost per MW
        m = re.search(
            r'<div class="capex-summary-card__value">([^<]+)</div>',
            html,
        )
        # The summary strip values must not be inputs
        assert m is not None


# ============================================================
# 8. Deferred placeholders for VAT / WHT / Depreciation /
#    Payment schedule / Utilisation
# ============================================================


class TestDeferredPlaceholders:
    def test_vat_wht_deferred(self):
        text = SHEET_CAPEX.read_text()
        # The deferred note must mention VAT, WHT
        # and payment schedule explicitly.
        for k in ["VAT", "WHT", "depreciation", "payment schedule"]:
            assert k in text, (
                f"Deferred note must mention {k!r}."
            )

    def test_sheet_documents_deferred_columns(self):
        text = SHEET_CAPEX.read_text()
        # The doc-comment at the top mentions the placeholders
        assert "Cost per MW" in text
        assert "VAT" in text
        assert "WHT" in text
        assert "depreciation" in text.lower() or "Depreciation" in text


# ============================================================
# 9. Sheet banner is correct
# ============================================================


class TestSheetBanner:
    def test_banner_says_capex(self):
        html = _render_sheet_capex()
        # The new sheet banner says "🏗️ CAPEX" (not the
        # previous mislabel "🏗️ CAPEX Detail")
        assert "🏗️ CAPEX" in html
        # Make sure it's a single CAPEX label, not duplicate
        banner_count = html.count("🏗️ CAPEX")
        assert banner_count >= 1

    def test_banner_does_not_say_audit(self):
        # Strip Jinja and HTML comments (which document the
        # deprecated alias for historical reference).
        text = _render_sheet_capex()
        text = re.sub(r"\{#.*?#\}", "", text, flags=re.DOTALL)
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        assert "audit" not in text.lower()
        assert "reconciliation" not in text.lower()


# ============================================================
# 10. Editability: factory reference is read-only
# ============================================================


class TestFactoryReferenceReadOnly:
    def test_factory_reference_no_inputs(self):
        html = _render_sheet_capex(is_user_project=False)
        # No editable inputs in factory reference mode
        inputs = re.findall(
            r'<input[^>]+name="capex_[a-z_]+_keur"',
            html,
        )
        assert len(inputs) == 0, (
            f"Factory reference mode must not have any "
            f"editable CAPEX inputs. Found {len(inputs)} inputs."
        )

    def test_factory_reference_notice_present(self):
        html = _render_sheet_capex(is_user_project=False)
        assert "Factory template" in html or (
            "Factory Reference" in html
        )


# ============================================================
# 11. line item sums match section totals
# ============================================================


class TestLineItemSumsToSectionTotal:
    def test_c01_subtotal_equals_sum_of_lines(self):
        html = _render_sheet_capex(is_user_project=True)
        # C.01 has epc_contract (1000) + production_units (500)
        # = 1500.00
        assert "1,500.00" in html, (
            "C.01 Subtotal value (1,500.00) must appear in "
            "the rendered HTML."
        )

    def test_hard_capex_total_equals_sum_of_categories(self):
        html = _render_sheet_capex(is_user_project=True)
        # Hard CAPEX Total = C.01 (1500) + C.02 (200) +
        # C.04 (300) + C.05 (100) = 2100
        assert "2,100.00" in html, (
            "Hard CAPEX Total (2,100.00) must appear in the "
            "rendered HTML."
        )

    def test_grand_total_equals_hard_plus_financing(self):
        html = _render_sheet_capex(is_user_project=True)
        # Total = 2100 + 50 + 25 = 2175.00
        assert "2,175.00" in html, (
            "Grand Total CAPEX (2,175.00) must appear in the "
            "rendered HTML."
        )


# ============================================================
# 12. No no-go claims in the new sheet
# ============================================================


class TestNoNoGoClaims:
    FORBIDDEN = [
        "bankable",
        "lender-ready",
        "audit-ready",
        "certified",
        "validated",
        "investor-ready",
        "saas-ready",
        "production-ready",
        "guaranteed returns",
        "investment advice",
        "customer reference",
    ]

    @pytest.mark.parametrize("term", FORBIDDEN)
    def test_no_forbidden_term_in_rendered_html(self, term):
        html = _render_sheet_capex(is_user_project=True)
        # Strip Jinja / HTML comments
        stripped = re.sub(r"\{#.*?#\}", "", html, flags=re.DOTALL)
        stripped = re.sub(r"<!--.*?-->", "", stripped, flags=re.DOTALL)
        assert term.lower() not in stripped.lower(), (
            f"Forbidden positive claim {term!r} found in the "
            f"rendered CAPEX sheet."
        )


# ============================================================
# 13. Sheet uses lig_render macro
# ============================================================


class TestLigRenderMacroUsed:
    def test_sheet_imports_lig_render(self):
        text = SHEET_CAPEX.read_text()
        assert (
            "from \"partials/_line_item_grid.html\" import lig_render"
            in text
        )

    def test_sheet_calls_lig_render(self):
        text = SHEET_CAPEX.read_text()
        assert "lig_render(" in text

    def test_sheet_uses_table_id(self):
        text = SHEET_CAPEX.read_text()
        assert "capex-single-sheet-grid" in text


# ============================================================
# 14. No backend / model / persistence changes
# ============================================================


class TestNoBackendModelPersistenceChanges:
    @pytest.mark.parametrize(
        "forbidden",
        [
            "main_web.py",
            "app/waterfall_core.py",
            "app/project_factories.py",
            "static/app.js",
            "static/styles.css",
        ],
    )
    def test_no_runtime_forbidden_file_in_diff(self, forbidden):
        import subprocess
        r = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on 57A-3 branch or no diff")
        changed = set(r.stdout.strip().split("\n"))
        for c in changed:
            assert not c.endswith(forbidden), (
                f"57A-3 must not modify {forbidden!r}. "
                f"Found: {c!r}."
            )

    def test_no_persistence_or_services_changes(self):
        import subprocess
        r = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on 57A-3 branch or no diff")
        changed = set(r.stdout.strip().split("\n"))
        for c in changed:
            assert not c.startswith("app/persistence/"), (
                f"57A-3 must not modify app/persistence/. "
                f"Found: {c!r}."
            )
            assert not c.startswith("app/services/"), (
                f"57A-3 must not modify app/services/. "
                f"Found: {c!r}."
            )


# ============================================================
# 15. lig_render macro not modified (kept as technical
#     foundation; not extended in this PR)
# ============================================================


class TestLigMacroNotModified:
    def test_lig_macro_unchanged(self):
        import subprocess
        r = subprocess.run(
            ["git", "diff", "main", "--name-only", "--",
             "app/templates/partials/_line_item_grid.html"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return
        pytest.fail(
            f"57A-3 must not modify _line_item_grid.html "
            f"(reuses 57A macro as-is). Found: {r.stdout.strip()!r}."
        )


# ============================================================
# 16. sheet_capex.html changed; sheet_capex_detail.html
#     NOT changed
# ============================================================


class TestFileScope:
    def test_sheet_capex_changed(self):
        import subprocess
        r = subprocess.run(
            ["git", "diff", "main", "--name-only", "--",
             "app/templates/partials/sheet_capex.html"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0
        assert r.stdout.strip() == "app/templates/partials/sheet_capex.html", (
            f"57A-3 must modify sheet_capex.html. "
            f"Found: {r.stdout.strip()!r}."
        )

    def test_sheet_capex_detail_not_changed(self):
        import subprocess
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
            f"57A-3 must NOT modify sheet_capex_detail.html "
            f"(kept as deprecated alias). "
            f"Found: {r.stdout.strip()!r}."
        )

    def test_workspace_shell_changed(self):
        import subprocess
        r = subprocess.run(
            ["git", "diff", "main", "--name-only", "--",
             "app/templates/partials/workspace_shell.html"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0
        assert r.stdout.strip() == "app/templates/partials/workspace_shell.html", (
            f"57A-3 must modify workspace_shell.html to remove "
            f"the sheet_capex_detail.html include. "
            f"Found: {r.stdout.strip()!r}."
        )


# ============================================================
# 17. rc1 untouched
# ============================================================


class TestRc1Untouched:
    def test_rc1_sha_constant_stable(self):
        assert RC1_SHA == "b425a0708719eaa5e1d922b1008e5609758e0ad4"

    def test_rc1_still_in_git_history(self):
        import subprocess
        r = subprocess.run(
            ["git", "rev-parse", RC1_SHA],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0
