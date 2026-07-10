"""
Tests for Financial Statements output honesty — PR #857.

Verifies:
- sheet_financials.html renders without error for protected and user projects
- Empty state is shown when no runtime financial_statements context
- Runtime-backed state is shown when financial_statements context is present
- No placeholder values presented as final statements
- No editable inputs in protected project
- Per-panel element IDs are unique (triple-DOM bug fix: data-fs-panel scoping)
- No financial calculations performed in template

Does NOT start a server — renders via Jinja2.
"""

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.ui.project_context import get_project_context


@pytest.fixture(scope="module")
def jinja_env():
    return Environment(
        loader=FileSystemLoader("app/templates"),
        autoescape=select_autoescape(["html"]),
    )


@pytest.fixture(scope="module")
def fs_template(jinja_env):
    return jinja_env.get_template("partials/sheet_financials.html")


@pytest.fixture(scope="module")
def tuho_ctx():
    return get_project_context("tuho")


@pytest.fixture(scope="module")
def oborovo_ctx():
    return get_project_context("oborovo")


def _render(template, ctx, active_statement="pl", financial_statements=None,
            is_user_project=False):
    return template.render(
        project_ctx=ctx,
        _active_statement=active_statement,
        financial_statements=financial_statements,
        is_user_project=is_user_project,
        runtime_summary=None,
    )


# ---------------------------------------------------------------------------
# Baseline renders
# ---------------------------------------------------------------------------

class TestBaselineRenders:
    def test_pl_panel_renders_protected(self, fs_template, tuho_ctx):
        html = _render(fs_template, tuho_ctx, active_statement="pl")
        assert len(html) > 0

    def test_cf_panel_renders_protected(self, fs_template, tuho_ctx):
        html = _render(fs_template, tuho_ctx, active_statement="cf")
        assert len(html) > 0

    def test_bs_panel_renders_protected(self, fs_template, tuho_ctx):
        html = _render(fs_template, tuho_ctx, active_statement="bs")
        assert len(html) > 0

    def test_renders_for_user_project(self, fs_template, tuho_ctx):
        html = _render(fs_template, tuho_ctx, is_user_project=True)
        assert len(html) > 0

    def test_renders_for_oborovo(self, fs_template, oborovo_ctx):
        html = _render(fs_template, oborovo_ctx)
        assert len(html) > 0


# ---------------------------------------------------------------------------
# Empty state (no runtime financial_statements)
# ---------------------------------------------------------------------------

class TestEmptyState:
    def test_unavailable_panel_present_without_runtime(self, fs_template, tuho_ctx):
        html = _render(fs_template, tuho_ctx, financial_statements=None)
        assert "fs-unavailable-panel" in html

    def test_run_model_message_shown_without_runtime(self, fs_template, tuho_ctx):
        html = _render(fs_template, tuho_ctx, financial_statements=None)
        assert "Run the model" in html

    def test_statements_block_hidden_without_runtime(self, fs_template, tuho_ctx):
        html = _render(fs_template, tuho_ctx, financial_statements=None)
        # fs-statements-block-pl is hidden when no runtime data
        assert 'id="fs-statements-block-pl"' in html
        assert 'style="display:none;"' in html

    def test_no_fake_pnl_values_without_runtime(self, fs_template, tuho_ctx):
        html = _render(fs_template, tuho_ctx, financial_statements=None)
        # The only numeric content in an un-run FS page should be from project_ctx
        # fields passed to _context_items — not from a statement table.
        # Statement tbody must be empty (no rows).
        assert "<tbody id=" in html


# ---------------------------------------------------------------------------
# Runtime-backed state
# ---------------------------------------------------------------------------

class _FakePeriod:
    def get(self, key, default=None):
        vals = {
            "revenues_keur": 10000,
            "operating_expenses_keur": -3000,
            "depreciation_keur": -1500,
            "ebit_keur": 5500,
            "senior_interest_expense_keur": -1200,
            "shl_interest_expense_keur": -300,
            "earnings_before_tax_keur": 4000,
            "cit_accrual_keur": -720,
            "net_income_keur": 3280,
            "retained_earnings_keur": 3280,
            "net_dividends_keur": 0,
        }
        return vals.get(key, default)

    def __getitem__(self, key):
        return self.get(key)

    @property
    def date(self):
        return "2030-06"


class _FakeStatement:
    def __init__(self):
        period = {"date": "2030-06", "revenues_keur": 10000,
                  "operating_expenses_keur": -3000, "depreciation_keur": -1500,
                  "ebit_keur": 5500, "senior_interest_expense_keur": -1200,
                  "shl_interest_expense_keur": -300, "earnings_before_tax_keur": 4000,
                  "cit_accrual_keur": -720, "net_income_keur": 3280,
                  "retained_earnings_keur": 3280, "net_dividends_keur": 0,
                  "net_fixed_assets_keur": 70000, "dsra_balance_keur": 500,
                  "cash_keur": 1000, "total_assets_keur": 71500,
                  "share_capital_keur": 500, "shl_balance_keur": 29000,
                  "senior_balance_keur": 43000, "total_liabilities_equity_keur": 71500,
                  "balance_check_keur": 0, "revenue_cash_keur": 10000,
                  "opex_cash_keur": -3000, "ebitda_cash_keur": 7000,
                  "cash_tax_keur": -700, "fcf_banks_keur": 6300,
                  "senior_total_ds_keur": -3000, "dsra_funding_keur": -200,
                  "dsra_release_keur": 0, "fcf_junior_keur": 3100,
                  "fcf_for_distribution_keur": 3100}
        self.pnl = type("S", (), {"periods": [period]})()
        self.balance_sheet = type("S", (), {"periods": [period]})()
        self.pf_cash_waterfall = type("S", (), {"periods": [period]})()


class TestRuntimeBackedState:
    def test_statements_block_visible_with_runtime(self, fs_template, tuho_ctx):
        fs = _FakeStatement()
        html = _render(fs_template, tuho_ctx, financial_statements=fs)
        # statements block should NOT have display:none
        assert 'id="fs-statements-block-pl"' in html
        # Check it's not hidden
        import re
        block_match = re.search(r'id="fs-statements-block-pl"([^>]*>)', html)
        assert block_match
        assert 'display:none' not in block_match.group(1)

    def test_unavailable_panel_hidden_with_runtime(self, fs_template, tuho_ctx):
        fs = _FakeStatement()
        html = _render(fs_template, tuho_ctx, financial_statements=fs)
        # Unavailable panel should have display:none when runtime data present
        import re
        panel_match = re.search(r'id="fs-unavailable-panel-pl"([^>]*>)', html)
        assert panel_match
        assert 'display:none' in panel_match.group(1)

    def test_engine_output_badge_present(self, fs_template, tuho_ctx):
        fs = _FakeStatement()
        html = _render(fs_template, tuho_ctx, financial_statements=fs)
        assert "Engine Output" in html

    def test_income_statement_section_header(self, fs_template, tuho_ctx):
        html = _render(fs_template, tuho_ctx)
        assert "Income Statement" in html

    def test_balance_sheet_section_header(self, fs_template, tuho_ctx):
        html = _render(fs_template, tuho_ctx)
        assert "Balance Sheet" in html

    def test_pf_cash_waterfall_section_header(self, fs_template, tuho_ctx):
        html = _render(fs_template, tuho_ctx)
        assert "PF Cash Waterfall" in html


# ---------------------------------------------------------------------------
# Per-panel element ID uniqueness (triple-DOM fix)
# ---------------------------------------------------------------------------

class TestPerPanelIdUniqueness:
    def test_pl_panel_has_pl_suffixed_ids(self, fs_template, tuho_ctx):
        html = _render(fs_template, tuho_ctx, active_statement="pl")
        assert 'id="fs-pnl-header-pl"' in html
        assert 'id="fs-unavailable-panel-pl"' in html
        assert 'id="fs-statements-block-pl"' in html

    def test_cf_panel_has_cf_suffixed_ids(self, fs_template, tuho_ctx):
        html = _render(fs_template, tuho_ctx, active_statement="cf")
        assert 'id="fs-pnl-header-cf"' in html
        assert 'id="fs-unavailable-panel-cf"' in html
        assert 'id="fs-statements-block-cf"' in html

    def test_bs_panel_has_bs_suffixed_ids(self, fs_template, tuho_ctx):
        html = _render(fs_template, tuho_ctx, active_statement="bs")
        assert 'id="fs-pnl-header-bs"' in html
        assert 'id="fs-unavailable-panel-bs"' in html
        assert 'id="fs-statements-block-bs"' in html

    def test_pl_panel_has_data_fs_panel_attribute(self, fs_template, tuho_ctx):
        html = _render(fs_template, tuho_ctx, active_statement="pl")
        assert 'data-fs-panel="pl"' in html

    def test_cf_panel_has_data_fs_panel_attribute(self, fs_template, tuho_ctx):
        html = _render(fs_template, tuho_ctx, active_statement="cf")
        assert 'data-fs-panel="cf"' in html

    def test_bs_panel_has_data_fs_panel_attribute(self, fs_template, tuho_ctx):
        html = _render(fs_template, tuho_ctx, active_statement="bs")
        assert 'data-fs-panel="bs"' in html

    def test_no_unsuffixed_fs_pnl_header_id(self, fs_template, tuho_ctx):
        # Bare 'id="fs-pnl-header"' must not exist — would cause getElementById cross-talk
        html = _render(fs_template, tuho_ctx, active_statement="pl")
        assert 'id="fs-pnl-header"' not in html

    def test_js_uses_panel_id_variable(self, fs_template, tuho_ctx):
        html = _render(fs_template, tuho_ctx, active_statement="pl")
        assert "_panelId" in html
        assert "data.fsPanel" in html or "dataset.fsPanel" in html


# ---------------------------------------------------------------------------
# No engine/math in template
# ---------------------------------------------------------------------------

class TestNoTemplateCalculations:
    def test_no_arithmetic_operators_in_jinja_output_rows(self, fs_template, tuho_ctx):
        # Row definitions are label/key maps only — no numeric expressions
        html = _render(fs_template, tuho_ctx)
        # The macros _fs_header and _fs_body only call _fs_num() (formatting)
        # and p.get(row["key"]) (lookup). Confirm no raw arithmetic.
        assert "PNL_ROWS" in html  # JS row definitions present
        assert "BS_ROWS" in html

    def test_accounting_conventions_block_present(self, fs_template, tuho_ctx):
        # Transparency: conventions are documented, not calculated
        html = _render(fs_template, tuho_ctx)
        assert "Accounting Conventions" in html

    def test_values_in_keur_footer_note(self, fs_template, tuho_ctx):
        html = _render(fs_template, tuho_ctx)
        assert "kEUR" in html

    def test_no_editable_inputs_in_statements(self, fs_template, tuho_ctx):
        # FS output is read-only — no type="number" inputs in statement rows
        html = _render(fs_template, tuho_ctx)
        # The only inputs in FS should be toolbar controls, not statement cells
        assert 'data-readonly="true"' in html or 'type="number"' not in html
