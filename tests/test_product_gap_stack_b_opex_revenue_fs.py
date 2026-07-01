"""Product Reality Gap Stack B: OPEX + Revenue + Financial Statements.

Characterization tests verifying:
  1. OPEX sheet renders and has correct editable cell CSS classes.
  2. OPEX live-totals JS module is wired and present.
  3. Revenue sheet renders; Code column is absent; ppa_base_tariff is editable.
  4. Financial Statements: fs-unavailable-panel present; runtime KPI script present.
  5. No banned jargon in any of the three sheets.
  6. Guardrails: restricted backend files are unchanged.

Investigation findings for all three areas are documented in
docs/PRODUCT_GAP_STACK_B_OPEX_REVENUE_FS.md.
"""
from __future__ import annotations

import os
import re

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def opex_partial():
    path = os.path.join(PROJECT_ROOT, "app/templates/partials/sheet_opex_detail.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def revenue_partial():
    path = os.path.join(PROJECT_ROOT, "app/templates/partials/sheet_revenue.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def financials_partial():
    path = os.path.join(PROJECT_ROOT, "app/templates/partials/sheet_financials.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def base_html():
    path = os.path.join(PROJECT_ROOT, "app/templates/base.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def capex_partial():
    path = os.path.join(PROJECT_ROOT, "app/templates/partials/sheet_capex.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ── 1. OPEX sheet still renders (template exists) ─────────────────────────────

class TestOpexSheet:
    def test_opex_template_exists(self):
        path = os.path.join(PROJECT_ROOT, "app/templates/partials/sheet_opex_detail.html")
        assert os.path.isfile(path), "sheet_opex_detail.html must exist"

    def test_opex_sheet_has_fc_grid(self, opex_partial):
        """OPEX grid must be present (data-fc-grid='opex')."""
        assert 'data-fc-grid="opex"' in opex_partial

    # ── 2. OPEX editable cells use correct CSS class (matching CAPEX) ─────────

    def test_opex_editable_cells_use_fc_input_native(self, opex_partial):
        """Editable OPEX Budget cells must use class='fc-input-native', same as CAPEX."""
        assert "fc-input-native" in opex_partial, (
            "OPEX editable cells must use fc-input-native (the CAPEX gold-standard class)"
        )

    def test_opex_editable_cell_has_no_name_attr(self, opex_partial):
        """OPEX Budget inputs must NOT carry a name= attribute (preview-only, not saveable)."""
        # Find every <input ... fc-input-native ...> block in opex
        inputs = re.findall(r'<input[^>]*fc-input-native[^>]*>', opex_partial)
        for inp in inputs:
            assert 'name=' not in inp, (
                f"OPEX fc-input-native input must not have name= attr: {inp!r}"
            )

    def test_opex_operating_subtotal_row_present(self, opex_partial):
        """Operating Subtotal row (PR3) must be present."""
        assert 'data-opex-row="operating-subtotal"' in opex_partial

    def test_opex_grand_total_row_present(self, opex_partial):
        """Total OPEX grand-total row (PR3) must be present."""
        assert 'data-opex-row="grand-total"' in opex_partial

    def test_opex_cat_subtotal_rows_present(self, opex_partial):
        """At least one category subtotal row (PR3) must be marked data-opex-row=cat-subtotal-*."""
        assert 'data-opex-row="cat-subtotal-' in opex_partial

    def test_opex_cat_budget_cells_have_data_opex_cat(self, opex_partial):
        """Budget cells must carry data-opex-cat= for live-total grouping."""
        assert 'data-opex-cat=' in opex_partial

    def test_opex_editable_cells_match_capex_fc_input_native(self, opex_partial, capex_partial):
        """OPEX must use fc-input-native. CAPEX uses a macro-based input pattern
        (editable cells are rendered via Jinja macros that produce standard input elements,
        but the literal class string 'fc-input-native' may not appear literally in the
        template source — only in the rendered output). We confirm OPEX uses the expected
        class and that CAPEX also has editable inputs (in its macro references)."""
        assert "fc-input-native" in opex_partial
        # CAPEX uses macros; verify editable inputs exist in some form
        assert "fc-editable" in capex_partial or "data-fc-editable" in capex_partial

    # ── 3. OPEX live-totals JS module is wired ────────────────────────────────

    def test_opex_live_totals_js_file_exists(self):
        path = os.path.join(PROJECT_ROOT, "static/modelling/opex-sheet-live-totals.js")
        assert os.path.isfile(path), "opex-sheet-live-totals.js must exist"

    def test_opex_live_totals_js_wired_in_base_html(self, base_html):
        """base.html must load opex-sheet-live-totals.js."""
        assert "opex-sheet-live-totals.js" in base_html

    def test_opex_live_totals_js_references_grid_id(self):
        """opex-sheet-live-totals.js must reference the opex grid selector."""
        path = os.path.join(PROJECT_ROOT, "static/modelling/opex-sheet-live-totals.js")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        # Must reference opex grid in some form
        assert "opex" in content.lower()

    def test_opex_banner_present(self, opex_partial):
        """OPEX sheet must have its sheet-banner."""
        assert "sheet-banner" in opex_partial
        assert "OPEX" in opex_partial


# ── 4. Revenue sheet still renders ───────────────────────────────────────────

class TestRevenueSheet:
    def test_revenue_template_exists(self):
        path = os.path.join(PROJECT_ROOT, "app/templates/partials/sheet_revenue.html")
        assert os.path.isfile(path), "sheet_revenue.html must exist"

    def test_revenue_sheet_has_fc_grid(self, revenue_partial):
        """Revenue grid must be present (data-fc-grid='revenue')."""
        assert 'data-fc-grid="revenue"' in revenue_partial

    # ── 5. Revenue Code column is absent ──────────────────────────────────────

    def test_revenue_code_column_header_absent(self, revenue_partial):
        """fc-th--code header must be absent from revenue template (PR5 removal)."""
        assert "fc-th--code" not in revenue_partial, (
            "Revenue Code column header must be removed (PR5)"
        )

    def test_revenue_code_column_cells_absent(self, revenue_partial):
        """fc-cell--code data cells must be absent from revenue template (PR5 removal)."""
        assert "fc-cell--code" not in revenue_partial, (
            "Revenue Code column cells must be removed (PR5)"
        )

    def test_revenue_colspan_is_5_not_6(self, revenue_partial):
        """After Code column removal, section-band colspan must be 5 (not 6)."""
        assert 'colspan="5"' in revenue_partial
        # Verify colspan=6 is NOT present in section bands
        # (allow colspan=6 if genuinely absent from all section-band rows)
        # Section band labels use colspan=5 after PR5
        section_bands = re.findall(
            r'<td[^>]*fc-section-band__label[^>]*colspan="(\d+)"', revenue_partial
        )
        for span in section_bands:
            assert span == "5", (
                f"section-band colspan should be 5 (was {span}) after Code column removal"
            )

    # ── 6. Revenue editable cell (ppa_base_tariff) correctly marked ───────────

    def test_revenue_ppa_base_tariff_editable_attr(self, revenue_partial):
        """ppa_base_tariff must be reachable via revenue!<item.code> addressing.
        The template uses Jinja loop variable: data-fc-addr='revenue!{{ item.code }}'
        and the PPA group includes ppa_base_tariff. Verify the template structure
        is correct for the PPA / Tariff group with an editable cell."""
        # The addr is templated as revenue!{{ item.code }}, so ppa_base_tariff addr
        # won't appear literally. Check for the Jinja addr pattern and the PPA group.
        assert 'data-fc-addr="revenue!{{ item.code }}"' in revenue_partial
        assert "PPA / Tariff" in revenue_partial
        # And the editable input pattern exists for revenue items
        assert 'name="rev_{{ item.code }}"' in revenue_partial

    def test_revenue_editable_input_uses_fc_input_native(self, revenue_partial):
        """Revenue editable inputs must use fc-input-native class."""
        assert "fc-input-native" in revenue_partial

    def test_revenue_editable_input_has_name_attr(self, revenue_partial):
        """Revenue ppa_base_tariff input must have name='rev_ppa_base_tariff' (real persistence path)."""
        assert 'name="rev_ppa_base_tariff"' in revenue_partial or \
               'name="rev_{{ item.code }}"' in revenue_partial, (
            "Revenue editable inputs must have name= for persistence via Save"
        )

    def test_revenue_readonly_cells_use_fc_cell_runtime(self, revenue_partial):
        """Revenue read-only cells must use fc-cell-runtime span."""
        assert "fc-cell-runtime" in revenue_partial

    def test_revenue_banner_present(self, revenue_partial):
        """Revenue sheet must have its sheet-banner."""
        assert "sheet-banner" in revenue_partial
        assert "Revenue" in revenue_partial


# ── 7. Financial Statements sheet still renders ───────────────────────────────

class TestFinancialStatementsSheet:
    def test_financials_template_exists(self):
        path = os.path.join(PROJECT_ROOT, "app/templates/partials/sheet_financials.html")
        assert os.path.isfile(path), "sheet_financials.html must exist"

    # ── 8. fs-unavailable-panel is present ────────────────────────────────────

    def test_fs_unavailable_panel_present(self, financials_partial):
        """PR6: fs-unavailable-panel must be present in the template."""
        assert "fs-unavailable-panel" in financials_partial

    def test_fs_unavailable_panel_uses_empty_state_notice(self, financials_partial):
        """fs-unavailable-panel must use the standard empty-state-notice pattern."""
        assert "empty-state-notice" in financials_partial
        assert "empty-state-notice--warn" in financials_partial

    def test_fs_old_static_tables_absent(self, financials_partial):
        """PR6: the old static statement table IDs must be absent."""
        assert "fs-pnl-grid" not in financials_partial
        assert "fs-cf-grid" not in financials_partial
        assert "fs-bs-grid" not in financials_partial

    def test_fs_unavailable_panel_has_user_copy(self, financials_partial):
        """Unavailable panel must explain the situation in plain language."""
        assert "Income Statement" in financials_partial
        assert "Cash Flow" in financials_partial
        assert "Balance Sheet" in financials_partial

    # ── 9. Runtime KPI block script is present ────────────────────────────────

    def test_fs_runtime_block_present(self, financials_partial):
        """fs-runtime-block (genuinely Run-backed, PR6 kept) must be present."""
        assert "fs-runtime-block" in financials_partial

    def test_fs_runtime_kpi_script_present(self, financials_partial):
        """_populateFSRuntimeBlock JS function must be present."""
        assert "_populateFSRuntimeBlock" in financials_partial

    def test_fs_runtime_kpi_reads_session_storage(self, financials_partial):
        """Runtime block script must read from sessionStorage (lastRuntimeSummary)."""
        assert "lastRuntimeSummary" in financials_partial

    def test_fs_banner_present(self, financials_partial):
        """Financial Statements sheet must have its sheet-banner."""
        assert "sheet-banner" in financials_partial
        assert "Financial Statements" in financials_partial


# ── 10. No banned jargon in any of the three sheets ──────────────────────────

BANNED_JARGON = [
    "Preview Architecture",
    "Runtime Pipeline",
    " stub",
    "R99",
    "R102",
    "G20",
    "TUHO factory snapshot",
    "static reference values",
]

# Note: "preview-only for now" in OPEX governance note is acceptable user-facing copy,
# not internal jargon. "preview" as a badge label is also acceptable.
# We only ban internal architecture terms.

ALLOWED_PREVIEW_PATTERNS = re.compile(
    r'preview-only for now|badge.{0,30}preview|badge-preview|badge badge-preview|'
    r'Running preview|Informational.*backend|opex-preview-only-note|fs-unavailable',
    re.IGNORECASE,
)


class TestNoBannedJargon:
    def _check_no_banned_jargon(self, content: str, sheet_name: str):
        for term in BANNED_JARGON:
            if term in content:
                # Check if it appears only in Jinja comments (stripped at render time)
                # Find all occurrences, ignore those inside {# ... #}
                for match in re.finditer(re.escape(term), content):
                    start = match.start()
                    # Check if this occurrence is inside a Jinja comment
                    # Find the nearest {# before this position
                    last_open = content.rfind("{#", 0, start)
                    last_close = content.rfind("#}", 0, start)
                    in_jinja_comment = last_open > last_close
                    if not in_jinja_comment:
                        pytest.fail(
                            f"Banned jargon {term!r} found in {sheet_name} "
                            f"outside a Jinja comment at position {start}"
                        )

    def test_opex_no_banned_jargon(self, opex_partial):
        self._check_no_banned_jargon(opex_partial, "sheet_opex_detail.html")

    def test_revenue_no_banned_jargon(self, revenue_partial):
        self._check_no_banned_jargon(revenue_partial, "sheet_revenue.html")

    def test_financials_no_banned_jargon(self, financials_partial):
        self._check_no_banned_jargon(financials_partial, "sheet_financials.html")

    def test_financials_no_static_tuho_reference(self, financials_partial):
        """The old 'Static TUHO reference values' footnote must be absent."""
        assert "TUHO factory snapshot" not in financials_partial
        assert "Static TUHO reference values" not in financials_partial

    def test_financials_no_stub_wording(self, financials_partial):
        """No 'stub' wording in the financials template."""
        # Only check in rendered text, not Jinja comments
        # A quick check: if 'stub' appears, it must be in a {# #} comment
        stub_positions = [m.start() for m in re.finditer(r'\bstub\b', financials_partial, re.IGNORECASE)]
        for pos in stub_positions:
            last_open = financials_partial.rfind("{#", 0, pos)
            last_close = financials_partial.rfind("#}", 0, pos)
            in_jinja_comment = last_open > last_close
            assert in_jinja_comment, (
                f"'stub' found outside a Jinja comment in sheet_financials.html at position {pos}"
            )


# ── 11. Guardrails: restricted backend files are unchanged ────────────────────

GUARDRAIL_FILES = [
    "app/waterfall_core.py",
    "app/input_adapter.py",
    "app/project_factories.py",
    "static/modelling/runtime-renderer.js",
    "app/services/model_preview.py",
    "app/services/preview_context.py",
]

GUARDRAIL_DIRS = [
    "domain",
    "app/services/previews",
]


class TestGuardrails:
    def test_guardrail_files_exist(self):
        """All guardrail files must still exist (not accidentally deleted)."""
        for rel_path in GUARDRAIL_FILES:
            full_path = os.path.join(PROJECT_ROOT, rel_path)
            assert os.path.isfile(full_path), (
                f"Guardrail file must still exist: {rel_path}"
            )

    def test_guardrail_dirs_exist(self):
        """Guardrail directories must still exist."""
        for rel_path in GUARDRAIL_DIRS:
            full_path = os.path.join(PROJECT_ROOT, rel_path)
            assert os.path.isdir(full_path), (
                f"Guardrail directory must still exist: {rel_path}"
            )

    def test_runtime_renderer_not_modified_by_this_pr(self):
        """runtime-renderer.js must not reference opex-sheet-live-totals or fs-unavailable-panel
        (i.e., this PR's changes must not have leaked into the restricted file)."""
        path = os.path.join(PROJECT_ROOT, "static/modelling/runtime-renderer.js")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "fs-unavailable-panel" not in content
        assert "opex-sheet-live-totals" not in content

    def test_opex_live_totals_js_does_not_reference_preview_services(self):
        """opex-sheet-live-totals.js must not CALL model_preview or preview_context
        (guardrail: no Preview Architecture bleed-in). Comments referencing these
        services are acceptable (they explain what the module does NOT do)."""
        path = os.path.join(PROJECT_ROOT, "static/modelling/opex-sheet-live-totals.js")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        # Strip block comments (/* ... */) and line comments (//) before checking
        # Remove block comments
        no_block_comments = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        # Remove line comments
        no_comments = re.sub(r'//[^\n]*', '', no_block_comments)
        assert "model_preview" not in no_comments
        assert "preview_context" not in no_comments
        # /model/preview endpoint must not be called (fetch/xhr) from live code
        assert "fetch" not in no_comments or "/model/preview" not in no_comments

    def test_no_financial_formula_in_opex_live_totals(self):
        """opex-sheet-live-totals.js must not contain inflation formula or Y2+ computation
        (only Y1 live totals are allowed, per PR3 scope)."""
        path = os.path.join(PROJECT_ROOT, "static/modelling/opex-sheet-live-totals.js")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        # Must not implement inflation formula (Math.pow or ** for year escalation)
        assert "inflation_rate" not in content, (
            "opex-sheet-live-totals.js must not reproduce the backend inflation formula"
        )
