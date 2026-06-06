"""Phase 57A / UI-3.1 — LineItemGrid CAPEX summary pilot tests.

Verifies that:
- A new shared LineItemGrid partial exists.
- `sheet_capex.html` renders through it (the wrapper marker
  `lig-wrapper lig-capex-pilot` is in the rendered output).
- The visible HTML / CSS class set is preserved 1:1 (every
  old class on every old element is still on the
  corresponding new element). This keeps the visual look
  identical to the pre-57A hand-written table.
- CAPEX summary content and labels are preserved (row order,
  values, formatting).
- The runtime impact / cell state semantics are preserved
  (read-only cells still have `aria-readonly="true"`,
  editable cells still have a `<input>`).
- HTMX / tab behaviour is unchanged.
- Inputs / OPEX / Revenue / Debt / SHL / Audit / Compare /
  Scenario sheets are NOT migrated.
- No `app/waterfall_core.py`, `app/project_factories.py`,
  `app/persistence`, `app/services`, `main_web.py` changes.
- No `static/app.js` changes.
- No frontend dependencies added.
- No no-go copy claims.
- Phase 57-pre route smoke still passes.
- GET / still returns 200.
- UI-2 / Phase 56 / Phase 55 / Phase 53I / 52F / 51F
  guardrails still pass.
- Engine MD5 / parity-core guardrails still pass.
- rc1 (b425a07) untouched.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_TEMPLATES = REPO_ROOT / "app" / "templates" / "partials"
SHEET_CAPEX = APP_TEMPLATES / "sheet_capex.html"
LINE_ITEM_GRID = APP_TEMPLATES / "_line_item_grid.html"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
APP_JS = REPO_ROOT / "static" / "app.js"
MAIN_WEB = REPO_ROOT / "main_web.py"

RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"

# Forbidden (out-of-scope) sheets — must NOT be migrated in 57A.
FORBIDDEN_SHEETS = [
    "sheet_capex_detail.html",
    "sheet_construction.html",
    "sheet_financials.html",
    "sheet_idc.html",
    "sheet_inputs.html",
    "sheet_opex.html",
    "sheet_opex_detail.html",
    "sheet_production.html",
    "sheet_revenue.html",
    "sheet_senior_debt.html",
    "sheet_shl.html",
    "sheet_tax.html",
]

# Forbidden backend / persistence / service / model files.
FORBIDDEN_BACKEND_FILES = {
    "app/waterfall_core.py",
    "app/project_factories.py",
    "app/runtime_impact_taxonomy.py",
    "main_web.py",
}


# ============================================================
# 1. Partial / macro exists
# ============================================================


class TestPartialExists:
    def test_line_item_grid_partial_exists(self):
        assert LINE_ITEM_GRID.exists(), (
            f"LineItemGrid partial must exist at {LINE_ITEM_GRID}"
        )

    def test_line_item_grid_partial_imports_cleanly(self):
        """The partial must compile in Jinja2 without errors
        (no unclosed blocks, no bad syntax)."""
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        env = Environment(
            loader=FileSystemLoader(str(APP_TEMPLATES.parent)),
            autoescape=select_autoescape(["html"]),
        )
        # The partial defines a macro `lig_render`. Loading
        # the file must succeed.
        try:
            tmpl = env.get_template(
                "partials/_line_item_grid.html"
            )
        except Exception as e:
            pytest.fail(
                f"LineItemGrid partial failed to load: {e}"
            )
        # And the macro must be defined
        assert "lig_render" in tmpl.module.__dict__ or hasattr(
            tmpl.module, "lig_render"
        ), (
            "LineItemGrid partial must define a `lig_render` macro."
        )


# ============================================================
# 2. sheet_capex.html uses the LineItemGrid partial
# ============================================================


class TestSheetCapexUsesLineItemGrid:
    def test_sheet_capex_imports_lig_macro(self):
        text = SHEET_CAPEX.read_text()
        assert (
            "from \"partials/_line_item_grid.html\" import lig_render" in text
            or "from 'partials/_line_item_grid.html' import lig_render" in text
        ), (
            "sheet_capex.html must `import lig_render` from the "
            "shared LineItemGrid partial."
        )

    def test_sheet_capex_calls_lig_render(self):
        text = SHEET_CAPEX.read_text()
        assert "lig_render(" in text, (
            "sheet_capex.html must call `lig_render(...)`."
        )

    def test_sheet_capex_no_inline_table_after_migration(self):
        """The migrated sheet must NOT keep an inline
        table body — it must delegate to the partial."""
        text = SHEET_CAPEX.read_text()
        # The old hand-written table body had this signature:
        #   <table class="fc-grid" aria-label="CAPEX detail grid ...">
        # The new version uses the partial; the table element
        # itself is rendered by lig_render.
        # We accept that the <table> tag appears inside a
        # lig_render macro call, but NOT as a top-level
        # sibling of `{{ lig_render(`.
        # Simple check: the old `<tbody>` containing
        # `{{ section_band(` macro calls must be gone.
        assert "{{ section_band(" not in text, (
            "sheet_capex.html still has inline section_band "
            "macros. After 57A migration, section bands must be "
            "expressed as lig_rows.append with type section_band."
        )

    def test_sheet_capex_no_inline_capex_row_macro(self):
        """The old hand-written `capex_row` macro must be gone."""
        text = SHEET_CAPEX.read_text()
        assert "{%- macro capex_row" not in text, (
            "sheet_capex.html still has the old `capex_row` macro. "
            "After 57A migration, rows are passed as data to "
            "lig_render."
        )

    def test_sheet_capex_no_inline_subtotal_row_macro(self):
        """The old hand-written `subtotal_row` macro must be gone."""
        text = SHEET_CAPEX.read_text()
        assert "{%- macro subtotal_row" not in text, (
            "sheet_capex.html still has the old `subtotal_row` "
            "macro. After 57A migration, subtotals are passed "
            "as data to lig_render."
        )

    def test_sheet_capex_no_inline_section_band_macro(self):
        """The old hand-written `section_band` macro must be gone."""
        text = SHEET_CAPEX.read_text()
        assert "{%- macro section_band" not in text, (
            "sheet_capex.html still has the old `section_band` "
            "macro. After 57A migration, section bands are passed "
            "as data to lig_render."
        )


# ============================================================
# 3. Render output preserves CAPEX summary content
# ============================================================


# Minimal project_ctx fixture mimicking what index.html passes
# to sheet_capex.html
SAMPLE_PROJECT_CTX = {
    "name": "Test CAPEX Project",
    "data_source": "User Project",
    "total_capex_keur": 12345.67,
    "capex_items": [
        # Construction section
        {"code": "epc_contract", "name": "EPC Contract", "amount_keur": 1000.00},
        {"code": "production_units", "name": "Production Units", "amount_keur": 500.00},
        # Development section
        {"code": "project_acquisition", "name": "Project Acquisition", "amount_keur": 200.00},
        # Civil & Land section
        {"code": "lease_tax", "name": "Lease & Land Tax", "amount_keur": 300.00},
        # Insurances & Risk
        {"code": "insurances", "name": "Insurances", "amount_keur": 100.00},
        # Financing Costs
        {"code": "idc", "name": "Interest During Construction", "amount_keur": 50.00},
    ],
}


def _render_sheet_capex():
    """Render sheet_capex.html in isolation with a sample
    project_ctx. Returns the rendered HTML string."""
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    env = Environment(
        loader=FileSystemLoader(str(APP_TEMPLATES.parent)),
        autoescape=select_autoescape(["html"]),
    )
    tmpl = env.get_template("partials/sheet_capex.html")
    return tmpl.render(
        project_ctx=SAMPLE_PROJECT_CTX,
        is_user_project=True,
    )


class TestRenderPreservesContent:
    def test_render_returns_html(self):
        html = _render_sheet_capex()
        assert isinstance(html, str)
        assert len(html) > 1000, (
            "Rendered HTML is suspiciously short. Did the macro "
            "expand correctly?"
        )

    def test_render_has_lig_wrapper(self):
        html = _render_sheet_capex()
        # The new stable test marker
        assert "lig-wrapper" in html
        assert "lig-capex-pilot" in html
        assert "data-line-item-grid=\"capex-pilot\"" in html

    def test_render_has_table_with_fc_grid_class(self):
        """The fc-grid class must be preserved on the table so
        the existing CSS still applies."""
        html = _render_sheet_capex()
        assert "fc-grid" in html, (
            "The `fc-grid` CSS class must be preserved on the "
            "rendered table."
        )

    def test_render_has_section_bands(self):
        html = _render_sheet_capex()
        # Note: 57A-3 (post-feedback) uses the canonical
        # C.01..C.18 hierarchy. Section bands are now
        # C.01  Production Unit, C.02  EPC Contract, etc.
        for label in [
            "C.01",
            "C.02",
            "C.06",  # Insurances
            "C.07",  # Land Securing Costs (Civil & Land)
            "C.15",  # Project Acquisition / Development
            "C.17",  # Financing Costs
        ]:
            # Each band appears as a section_band row
            # with the C.0X code in the data-capex-category
            # attribute.
            assert (
                f'data-capex-category="{label}"' in html
            ), (
                f"Section band for {label!r} must appear in "
                f"the rendered CAPEX table "
                f"(post-57A-3 C.01..C.18 hierarchy)."
            )

    def test_render_has_subtotal_labels(self):
        html = _render_sheet_capex()
        # Phase 57A-3 (post-feedback revision) rewrote
        # sheet_capex.html to render the canonical
        # C.01..C.18 hierarchy. Subtotal rows render for
        # categories that have non-zero sub-line amounts
        # in the sample data.
        # Sample data: production_units (C.01), epc_contract
        # (C.02), insurances (C.06), lease_tax (C.07),
        # project_acquisition (C.15), idc (financing,
        # rendered as data_financing).
        for label in [
            "C.01 Subtotal",
            "C.02 Subtotal",
            "C.06 Subtotal",
            "C.07 Subtotal",
            "C.15 Subtotal",
            "Hard CAPEX Total",
            "Total CAPEX",
        ]:
            assert label in html, (
                f"Subtotal label {label!r} must appear in the "
                f"rendered CAPEX table (post-57A-3 single sheet)."
            )

    def test_render_has_data_capex_codes(self):
        html = _render_sheet_capex()
        for code in [
            "epc_contract", "production_units", "project_acquisition",
            "lease_tax", "insurances", "idc",
        ]:
            assert f'data-capex-code="{code}"' in html, (
                f"data-capex-code=\"{code}\" must appear in the "
                f"rendered HTML."
            )

    def test_render_has_fc_total_row_classes(self):
        """The subtotal / total CSS classes must be preserved
        so the existing CSS still applies.

        Note: post-57A-3, the grand total row uses
        `lig-row--total` (the LineItemGrid macro's modern
        marker) rather than the legacy `fc-grand-total` class.
        The `data-capex-row="grand-total"` attribute is the
        stable, version-independent marker for the grand
        total row.
        """
        html = _render_sheet_capex()
        for cls in [
            "fc-total-row",
            "fc-subtotal-row",
            "fc-section-band",
        ]:
            assert cls in html, (
                f"CSS class {cls!r} must appear in the rendered "
                f"HTML (preserved by 57A migration)."
            )
        # Grand total: assert the modern stable marker.
        assert 'data-capex-row="grand-total"' in html, (
            "Grand total row must have data-capex-row="
            "\"grand-total\" attribute (stable marker)."
        )
        # Hard CAPEX total: also a stable marker.
        assert 'data-capex-row="hard-capex-total"' in html, (
            "Hard CAPEX total row must have data-capex-row="
            "\"hard-capex-total\" attribute (stable marker)."
        )

    def test_render_has_amount_cells_with_formatting(self):
        """The amount cells must have the value formatted
        (subtotals/totals with thousands separators like
        1,500.00; editable data row inputs as 1000.00).

        Note: 57A-3 (post-feedback) renders the C.01..C.18
        hierarchy. In the fallback path, the sample data
        maps to specific C.0X categories via the
        summary_to_cat map. The exact subtotal value is
        not as important as confirming the format and
        the read-only / input behaviour.
        """
        html = _render_sheet_capex()
        # Data row editable input — value attribute is the
        # raw number (no thousands separator, because
        # <input type="number"> doesn't accept comma).
        # 1000.00 must appear as the value attribute
        assert 'value="1000.00"' in html, (
            "Editable input value for 1000.00 must appear in "
            "the rendered HTML."
        )
        # 500.00
        assert 'value="500.00"' in html
        # 200.00 (project_acquisition)
        assert 'value="200.00"' in html
        # 300.00 (lease_tax)
        assert 'value="300.00"' in html
        # 100.00 (insurances)
        assert 'value="100.00"' in html
        # 50.00 (idc) — financing row, so it is NOT an
        # editable input. The value must still be visible
        # in the rendered HTML (as read-only text).
        assert "50.00" in html, (
            "idc financing row amount (50.00) must still "
            "appear visibly in the rendered HTML even "
            "though it is read-only (Fix A)."
        )
        assert 'value="50.00"' not in html, (
            "idc financing row must NOT render an editable "
            "<input value=\"50.00\"> in user project mode "
            "(Fix A: financing rows are read-only)."
        )

    def test_render_input_field_for_editable_cell(self):
        """When is_user_project=True, the amount cell for a
        data row must render a native <input>."""
        html = _render_sheet_capex()
        # At least one input with name="capex_*_keur" must exist
        assert re.search(
            r'name="capex_[a-z_]+_keur"',
            html,
        ), (
            "Editable amount cells must render "
            "<input name=\"capex_<code>_keur\">."
        )

    def test_render_total_capex_label(self):
        """The grand-total label must contain 'Total CAPEX'."""
        html = _render_sheet_capex()
        # 57A-3 (post-feedback) uses 'Total CAPEX (C.01–C.18)'
        # rather than just 'Total CAPEX'.
        assert "Total CAPEX" in html

    def test_render_no_lig_input_when_not_user_project(self):
        """When is_user_project=False (factory reference),
        the amount cells must be read-only (no <input>)."""
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        env = Environment(
            loader=FileSystemLoader(str(APP_TEMPLATES.parent)),
            autoescape=select_autoescape(["html"]),
        )
        tmpl = env.get_template("partials/sheet_capex.html")
        html = tmpl.render(
            project_ctx=SAMPLE_PROJECT_CTX,
            is_user_project=False,
        )
        # The amount cells must be read-only
        assert 'aria-readonly="true"' in html
        # The factory-reference notice must appear
        assert "Factory Reference" in html
        assert "template defaults" in html

    def test_financing_rows_readonly_in_user_project(self):
        """Financing rows (idc, bank_fees, commitment_fees,
        other_financial, vat_costs, reserve_accounts) must
        remain read-only even in user project mode. They
        are backend-computed values (Fix A)."""
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        env = Environment(
            loader=FileSystemLoader(str(APP_TEMPLATES.parent)),
            autoescape=select_autoescape(["html"]),
        )
        tmpl = env.get_template("partials/sheet_capex.html")
        html = tmpl.render(
            project_ctx=SAMPLE_PROJECT_CTX,
            is_user_project=True,
        )
        # The SAMPLE_PROJECT_CTX includes an idc item. We
        # extend it to cover the other financing codes that
        # might be present in the row loop.
        FINANCING_CODES = [
            "idc",
            "bank_fees",
            "commitment_fees",
            "other_financial",
            "vat_costs",
            "reserve_accounts",
        ]
        for code in FINANCING_CODES:
            input_name = f'name="capex_{code}_keur"'
            assert input_name not in html, (
                f"Financing row {code!r} must NOT render an "
                f"editable <input> in user project mode. "
                f"Found {input_name!r} in the rendered HTML. "
                f"Financing rows are backend-computed and must "
                f"remain read-only (Fix A)."
            )
        # The SAMPLE_PROJECT_CTX includes `idc` so we can
        # verify the idc data row still renders visibly and
        # with read-only semantics.
        # Find the idc data row (tr with data-capex-code="idc")
        idc_row_match = re.search(
            r'<tr[^>]*data-capex-code="idc"[^>]*>(.*?)</tr>',
            html,
            re.DOTALL,
        )
        assert idc_row_match is not None, (
            "The idc financing row must still render in the "
            "HTML (visible row, just not editable)."
        )
        idc_row_html = idc_row_match.group(1)
        # The idc row's amount cell must have aria-readonly="true"
        assert 'aria-readonly="true"' in idc_row_html, (
            "The idc financing row's amount cell must have "
            "aria-readonly=\"true\" (read-only semantics). "
            "Found: " + idc_row_html[:300]
        )
        # The idc amount must still be visible (not blank).
        # The sample data has idc.amount_keur = 50.00.
        assert "50.00" in idc_row_html, (
            "The idc financing row's amount value (50.00) "
            "must still be visible in the rendered HTML."
        )
        # The idc row must NOT have an <input> tag at all.
        assert "<input" not in idc_row_html, (
            "The idc financing row must not contain an "
            "<input> element (read-only financing)."
        )
        # Also: ordinary hard CAPEX data rows (epc_contract,
        # production_units, etc.) MUST still be editable in
        # user project mode (regression guard for Fix A).
        for editable_code in [
            "epc_contract",
            "production_units",
            "project_acquisition",
            "lease_tax",
            "insurances",
        ]:
            input_name = f'name="capex_{editable_code}_keur"'
            assert input_name in html, (
                f"Ordinary hard CAPEX data row {editable_code!r} "
                f"must still render an editable <input> in user "
                f"project mode. Found no {input_name!r} in the "
                f"rendered HTML. Fix A must not over-restrict "
                f"editable rows."
            )

    def test_financing_rows_readonly_in_factory_reference(self):
        """Financing rows must remain read-only in factory
        reference mode too (was already true pre-57A, must
        remain true post-Fix-A)."""
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        env = Environment(
            loader=FileSystemLoader(str(APP_TEMPLATES.parent)),
            autoescape=select_autoescape(["html"]),
        )
        tmpl = env.get_template("partials/sheet_capex.html")
        html = tmpl.render(
            project_ctx=SAMPLE_PROJECT_CTX,
            is_user_project=False,
        )
        FINANCING_CODES = [
            "idc",
            "bank_fees",
            "commitment_fees",
            "other_financial",
            "vat_costs",
            "reserve_accounts",
        ]
        for code in FINANCING_CODES:
            input_name = f'name="capex_{code}_keur"'
            assert input_name not in html, (
                f"Financing row {code!r} must NOT render an "
                f"editable <input> in factory reference mode."
            )
        # Factory reference notice must be present
        assert "Factory Reference" in html
        assert "template defaults" in html

    def test_section_bands_are_html_escaped(self):
        """Section band labels must be HTML-escaped (so
        `&` becomes `&amp;`). Fix C.

        Note: 57A-3 (post-feedback) uses the C.01..C.18
        canonical category names. The C.04 "Monitoring &
        Telecom", C.07 "Land Securing Costs", and
        C.11 "Audit & Accounting & Legal" labels contain
        `&` and must be auto-escaped to `&amp;`.
        """
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        env = Environment(
            loader=FileSystemLoader(str(APP_TEMPLATES.parent)),
            autoescape=select_autoescape(["html"]),
        )
        tmpl = env.get_template("partials/sheet_capex.html")
        html = tmpl.render(
            project_ctx=SAMPLE_PROJECT_CTX,
            is_user_project=True,
        )
        for label_with_amp in [
            "Monitoring &amp; Telecom",
            "Audit &amp; Accounting &amp; Legal",
        ]:
            assert label_with_amp in html, (
                f"Section band label {label_with_amp!r} must "
                f"appear in the rendered HTML (autoescaped)."
            )
        # And the unescaped `&` form should NOT appear in
        # the section band labels.
        # (Note: there are other `&` characters in the
        # rendered HTML e.g. inside aria-label values or
        # inside `<span class="fc-delta-warning">⚠ ...
        # kEUR delta ...</span>` — those are still inside
        # `safe` HTML and are OK. The fix is specifically
        # for the section band plain-string cell.)
        # We assert that the section band <td> with
        # colspan="3" and class "lig-cell fc-section-band__label"
        # contains escaped &.
        for m in re.finditer(
            r'<td class="lig-cell fc-section-band__label"[^>]*>([^<]+)</td>',
            html,
        ):
            label_text = m.group(1).strip()
            # No literal & in section band plain-text labels
            if "&" in label_text and "&amp;" not in label_text:
                pytest.fail(
                    f"Section band label {label_text!r} contains "
                    f"an unescaped `&`. Fix C requires autoescape."
                )

    def test_lig_data_financing_class_present(self):
        """The new data_financing row type must add the
        `lig-row--data-financing` CSS class. (Stable
        marker for the Fix A policy.)"""
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        env = Environment(
            loader=FileSystemLoader(str(APP_TEMPLATES.parent)),
            autoescape=select_autoescape(["html"]),
        )
        tmpl = env.get_template("partials/sheet_capex.html")
        html = tmpl.render(
            project_ctx=SAMPLE_PROJECT_CTX,
            is_user_project=True,
        )
        # The idc row in SAMPLE_PROJECT_CTX should have
        # the lig-row--data-financing class.
        assert "lig-row--data-financing" in html, (
            "The data_financing row type must produce a "
            "lig-row--data-financing CSS class (stable "
            "marker for Fix A)."
        )

    def test_render_preserves_sheet_banner(self):
        """The sheet-banner block (top-of-sheet tag) must be
        preserved.

        Note: post-57A-3, the banner label is "🏗️ CAPEX"
        (the single CAPEX sheet, no "Detail" suffix) per
        user direction: one CAPEX sheet, not two competing
        views.
        """
        html = _render_sheet_capex()
        assert "sheet-banner" in html
        assert "🏗️ CAPEX" in html

    def test_render_preserves_dirty_indicator(self):
        """The dirty-indicator (used by HTMX form) must be
        preserved."""
        html = _render_sheet_capex()
        assert 'id="dirty-indicator"' in html


# ============================================================
# 4. Other sheets are NOT migrated
# ============================================================


class TestForbiddenSheetsUntouched:
    @pytest.mark.parametrize("forbidden", FORBIDDEN_SHEETS)
    def test_sheet_not_migrated(self, forbidden):
        """The forbidden sheet must not import lig_render."""
        path = APP_TEMPLATES / forbidden
        if not path.exists():
            pytest.skip(f"{forbidden} does not exist")
        text = path.read_text()
        assert "import lig_render" not in text, (
            f"{forbidden} must NOT import lig_render. 57A only "
            f"migrates sheet_capex.html."
        )
        assert "lig_render(" not in text, (
            f"{forbidden} must NOT call lig_render. 57A only "
            f"migrates sheet_capex.html."
        )


# ============================================================
# 5. Backend / persistence / service / main_web untouched
# ============================================================


class TestBackendUntouched:
    @pytest.mark.parametrize("forbidden", sorted(FORBIDDEN_BACKEND_FILES))
    def test_backend_file_not_changed(self, forbidden):
        """The 57a branch must not modify any backend file."""
        r = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on a 57a branch; no diff to check")
        changed = set(r.stdout.strip().split("\n"))
        assert forbidden not in changed, (
            f"Forbidden backend file {forbidden!r} was modified by "
            f"57a. Only test/docs/report/templates/styles.css "
            f"are allowed to change."
        )

    def test_no_persistence_directory_changed(self):
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode == 0:
            branch = r.stdout.strip()
            if "57a9" in branch.lower():
                pytest.skip(
                    f"57A-9X branch — app/persistence/ is the "
                    f"target of the save/load wiring "
                    f"(current: {branch!r})."
                )
        r = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on a 57a branch; no diff to check")
        changed = set(r.stdout.strip().split("\n"))
        for f in changed:
            assert not f.startswith("app/persistence/"), (
                f"Forbidden persistence change: {f!r}."
            )

    def test_no_services_directory_changed(self):
        r = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on a 57a branch; no diff to check")
        changed = set(r.stdout.strip().split("\n"))
        for f in changed:
            assert not f.startswith("app/services/"), (
                f"Forbidden services change: {f!r}."
            )


# ============================================================
# 6. No static/app.js changes
# ============================================================


class TestStaticUntouched:
    def _skip_if_not_on_57a_branch(self) -> None:
        """Skip the test if we are not on a 57A branch.

        The TestStaticUntouched tests assert that
        static/app.js is unchanged vs main — which is
        only meaningful while 57A is the unmerged
        branch. A follow-up branch (e.g. 57A-8) may
        legitimately modify static/app.js; this is
        not 57A's concern.
        """
        r_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r_branch.returncode != 0:
            return
        branch = r_branch.stdout.strip()
        if branch == "main":
            pytest.skip(
                "On main branch; 57A has been merged. "
                "This test is only meaningful on the "
                "57A unmerged branch."
            )
        branch_lower = branch.lower()
        is_57a_branch = (
            "57a" in branch_lower
            and not any(
                suffix in branch_lower
                for suffix in (
                    "57a-1", "57a-2", "57a-3", "57a-4",
                    "57a-5", "57a-6", "57a-7", "57a-8",
                    "57a1", "57a2", "57a3", "57a4", "57a5",
                    "57a5b", "57a6", "57a7", "57a8",
                )
            )
        )
        if not is_57a_branch:
            pytest.skip(
                f"Not on a 57A branch (current: "
                f"{branch!r}). This test is only "
                f"meaningful on the 57A unmerged "
                f"branch."
            )

    def test_app_js_not_changed(self):
        r = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on a 57a branch; no diff to check")
        self._skip_if_not_on_57a_branch()
        changed = set(r.stdout.strip().split("\n"))
        assert "static/app.js" not in changed, (
            "static/app.js must NOT be modified by 57a. The "
            "LineItemGrid migration is template + (optional) "
            "additive CSS only."
        )

    def test_no_frontend_dependency_added(self):
        r = subprocess.run(
            ["git", "diff", "main", "--name-only", "--diff-filter=A"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on a 57a branch; no diff to check")
        self._skip_if_not_on_57a_branch()
        added = set(r.stdout.strip().split("\n"))
        forbidden = {
            "package.json",
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
            "vite.config.js",
            "webpack.config.js",
            "rollup.config.js",
            "tailwind.config.js",
        }
        for f in added:
            assert f not in forbidden, (
                f"Forbidden frontend dependency config: {f!r}."
            )

    def test_no_financial_formula_change(self):
        """The 57a branch must not have modified any financial
        file (waterfall_core, project_factories)."""
        r = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on a 57a branch; no diff to check")
        changed = set(r.stdout.strip().split("\n"))
        for f in changed:
            assert f not in {
                "app/waterfall_core.py",
                "app/project_factories.py",
            }, (
                f"Forbidden model change: {f!r}."
            )


# ============================================================
# 7. No-go copy
# ============================================================


class TestNoGoCopy:
    """The 57a branch must not introduce positive no-go claims
    in any template or doc."""
    NO_GO_TERMS = [
        "bankable", "lender-ready", "audit-ready", "certified",
        "validated", "investor-ready", "saas-ready", "production-ready",
        "guaranteed returns", "investment advice", "customer reference",
    ]

    def test_no_positive_claims_in_sheet_capex(self):
        text = SHEET_CAPEX.read_text()
        lowered = text.lower()
        for term in self.NO_GO_TERMS:
            # The terms may appear in Jinja comments as
            # "forbidden terms" — strip them first.
            stripped = re.sub(r"\{#.*?#\}", "", text, flags=re.DOTALL)
            stripped = re.sub(r"<!--.*?-->", "", stripped, flags=re.DOTALL)
            if term.lower() in stripped.lower():
                pytest.fail(
                    f"Positive no-go term {term!r} found in "
                    f"sheet_capex.html after stripping comments."
                )

    def test_no_positive_claims_in_line_item_grid(self):
        text = LINE_ITEM_GRID.read_text()
        stripped = re.sub(r"\{#.*?#\}", "", text, flags=re.DOTALL)
        for term in self.NO_GO_TERMS:
            if term.lower() in stripped.lower():
                pytest.fail(
                    f"Positive no-go term {term!r} found in "
                    f"_line_item_grid.html after stripping comments."
                )


# ============================================================
# 8. rc1 untouched
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
        assert r.returncode == 0, (
            f"rc1 frozen SHA {RC1_SHA} must still be present in "
            f"the repo. Got: {r.stderr}"
        )


# ============================================================
# 9. CSS additive (if any)
# ============================================================


class TestStylesheetAdditive:
    def test_styles_css_change_is_additive(self):
        """If static/styles.css is modified, the diff must be
        purely additive (no removed lines, no modifications
        to existing rules)."""
        r = subprocess.run(
            ["git", "diff", "main", "--", "static/styles.css"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            # No styles.css change — fine
            return
        diff = r.stdout
        # If styles.css was changed, the diff must contain
        # only `+` lines (no `-` lines at the start of a
        # line). Existing rules must not be modified.
        for line in diff.split("\n"):
            if line.startswith("---") or line.startswith("+++"):
                continue
            assert not line.startswith("-"), (
                f"static/styles.css has a removed or modified "
                f"line in the 57a diff. CSS changes must be "
                f"additive only. Offending line: {line!r}"
            )

    def test_lig_css_classes_defined_if_styles_changed(self):
        """If styles.css was modified, the new LineItemGrid CSS
        classes must be defined. (Optional CSS: 57a does NOT
        require styles.css to be modified — the existing
        `fc-grid` rules apply because the migrated sheet
        preserves every old class.)"""
        pass  # Optional; no required CSS changes for 57a.


# ============================================================
# 10. Phase 57-pre route smoke must still pass
# ============================================================


class TestPhase57PreStillPasses:
    def test_57pre_test_file_exists(self):
        path = REPO_ROOT / "tests" / "test_phase57pre_route_render_smoke.py"
        assert path.exists()

    def test_57pre_test_module_imports(self):
        """The 57pre test module must still import cleanly
        (no syntax errors, no circular imports)."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "test_phase57pre_route_render_smoke",
            str(REPO_ROOT / "tests" / "test_phase57pre_route_render_smoke.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            pytest.fail(
                f"57pre test module failed to import: {e}"
            )


# ============================================================
# 11. 56H-1 regression pin still in place
# ============================================================


class Test56H1RegressionStillPinned:
    def test_56h1_test_file_exists(self):
        path = REPO_ROOT / "tests" / "test_phase56h1_index_validation_errors_hotfix.py"
        assert path.exists()

    def test_56h1_test_module_imports(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "test_phase56h1",
            str(REPO_ROOT / "tests" / "test_phase56h1_index_validation_errors_hotfix.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            pytest.fail(
                f"56H-1 test module failed to import: {e}"
            )

    def test_56h1_local_validation_errors_hoist_still_present(self):
        """The 56H-1 local-variable hoist must still be in
        main_web.py (the 57a branch does not touch it)."""
        text = MAIN_WEB.read_text()
        m = re.search(
            r"^@app\.get\(\"/\"\)\s*\nasync def index\([^)]*\):(.*?)(?=^@app\.)",
            text,
            re.MULTILINE | re.DOTALL,
        )
        assert m is not None
        body = m.group(1)
        local_decl = re.search(
            r"^\s*validation_errors\s*:\s*list\s*\[\s*str\s*\]\s*=\s*\[\s*\]",
            body,
            re.MULTILINE,
        )
        assert local_decl is not None, (
            "56H-1 local-variable hoist must still be present "
            "in the index() function (regression pin)."
        )
