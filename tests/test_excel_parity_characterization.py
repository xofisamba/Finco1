"""Excel Parity Characterization Tests

Branch: excel-parity-discovery
Purpose: Lock in the current engine state so that future implementation PRs have
         known-state anchors. These tests document what IS computed vs. what is NOT
         yet connected to the UI. They are discovery tests, not regression guards for
         financial values.

No financial logic was changed to produce these tests.
"""
from __future__ import annotations

import dataclasses

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
from domain.financial_statements import assemble_financial_statements
from domain.period_engine import PeriodEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_tuho():
    inputs = create_default_tuho_wind1()
    engine = PeriodEngine(
        inputs.info.financial_close,
        inputs.info.construction_months,
        inputs.info.horizon_years,
        inputs.revenue.ppa_term_years,
    )
    config = WaterfallRunConfig.from_inputs(inputs, engine)
    result = WaterfallRunner(inputs, engine).run(config)
    return inputs, engine, result


def _run_oborovo():
    inputs = create_default_oborovo()
    engine = PeriodEngine(
        inputs.info.financial_close,
        inputs.info.construction_months,
        inputs.info.horizon_years,
        inputs.revenue.ppa_term_years,
    )
    config = WaterfallRunConfig.from_inputs(inputs, engine)
    result = WaterfallRunner(inputs, engine).run(config)
    return inputs, engine, result


# ---------------------------------------------------------------------------
# C1: WaterfallResult does NOT contain a 'financial_statements' key
#     (financial statements are assembled separately, not part of the runtime result)
# ---------------------------------------------------------------------------

class TestFinancialStatementsNotInRuntimeResult:
    """Characterizes that financial_statements are NOT auto-attached to WaterfallResult.

    When a future PR connects FS to the UI, it will need to call
    assemble_financial_statements() separately and pass it to the template.
    These tests document the current separation.
    """

    def test_tuho_result_has_no_financial_statements_attribute(self):
        _, _, result = _run_tuho()
        assert not hasattr(result, "financial_statements"), (
            "WaterfallResult should not have a 'financial_statements' attribute. "
            "assemble_financial_statements() must be called separately."
        )

    def test_oborovo_result_has_no_financial_statements_attribute(self):
        _, _, result = _run_oborovo()
        assert not hasattr(result, "financial_statements")

    def test_assemble_financial_statements_produces_pnl(self):
        """assemble_financial_statements() does work and produces a non-empty P&L."""
        _, _, result = _run_tuho()
        fs = assemble_financial_statements(result)
        assert len(fs.pnl.periods) > 0, "P&L assembly produced no periods"
        assert len(fs.balance_sheet.periods) > 0, "Balance sheet assembly produced no periods"
        assert len(fs.pf_cash_waterfall.periods) > 0, "PF cash waterfall assembly produced no periods"

    def test_assemble_financial_statements_produces_pnl_oborovo(self):
        _, _, result = _run_oborovo()
        fs = assemble_financial_statements(result)
        assert len(fs.pnl.periods) > 0


# ---------------------------------------------------------------------------
# C2: Distribution amounts ARE computed by the waterfall engine
#     but are NOT wired to a UI tab (Distribution tab shows "not-yet-connected")
# ---------------------------------------------------------------------------

class TestDistributionComputedButNotWiredToUI:
    """Characterizes that distribution_keur is computed per-period."""

    def test_tuho_total_distribution_is_nonzero(self):
        _, _, result = _run_tuho()
        assert result.total_distribution_keur > 0, (
            "TUHO should produce non-zero total distributions."
        )

    def test_oborovo_total_distribution_is_nonzero(self):
        _, _, result = _run_oborovo()
        assert result.total_distribution_keur > 0

    def test_tuho_per_period_distribution_keur_present(self):
        """Each WaterfallPeriod has distribution_keur field."""
        _, _, result = _run_tuho()
        op_periods = [p for p in result.periods if getattr(p, "is_operation", False)]
        assert all(hasattr(p, "distribution_keur") for p in op_periods)
        # At least some periods should have non-zero distribution
        assert any(p.distribution_keur > 0 for p in op_periods), (
            "No operating periods have positive distribution_keur for TUHO."
        )

    def test_distribution_account_wiring_flag_not_active_by_default(self):
        """By default, use_distributionaccount_runtime_wiring is NOT active.

        The Distribution Account engine is governance-blocked (G20/R99/R102).
        This test documents the current gate: DA is dual-run audit only.
        """
        _, _, result = _run_tuho()
        # When DA wiring is not active, distribution_source is empty string
        # and da_paid_distribution_keur is 0 (no override applied)
        assert result.distribution_source in ("", "runtime"), (
            f"Unexpected distribution_source={result.distribution_source!r}; "
            "expected '' or 'runtime' when DA wiring is not active."
        )
        # da_paid_distribution_keur is only set when wiring was applied
        assert result.da_paid_distribution_keur == 0.0


# ---------------------------------------------------------------------------
# C3: Sponsor IRR IS computed but the Sponsor UI tab is not-yet-connected
# ---------------------------------------------------------------------------

class TestSponsorIrrComputedButSponsorTabNotConnected:

    def test_tuho_sponsor_irr_is_nonzero(self):
        _, _, result = _run_tuho()
        assert result.sponsor_irr > 0.0, (
            "TUHO sponsor_irr should be positive (computed from domain/returns/sponsor_cashflows.py)."
        )

    def test_oborovo_sponsor_irr_is_nonzero(self):
        _, _, result = _run_oborovo()
        assert result.sponsor_irr > 0.0

    def test_tuho_sponsor_irr_in_plausible_range(self):
        """Characterization: TUHO sponsor IRR is between 8% and 15%."""
        _, _, result = _run_tuho()
        assert 0.08 <= result.sponsor_irr <= 0.15, (
            f"TUHO sponsor_irr={result.sponsor_irr:.4f} outside expected 8–15% range."
        )


# ---------------------------------------------------------------------------
# C4: Senior debt schedule IS computed per-period but period-schedule
#     is NOT connected to the UI Senior Debt tab (only top-level KPIs surface)
# ---------------------------------------------------------------------------

class TestSeniorDebtScheduleComputedButNotInUI:

    def test_tuho_per_period_senior_ds_present(self):
        _, _, result = _run_tuho()
        op_periods = [p for p in result.periods if getattr(p, "is_operation", False)]
        assert all(hasattr(p, "senior_ds_keur") for p in op_periods)
        assert all(hasattr(p, "senior_interest_keur") for p in op_periods)
        assert all(hasattr(p, "senior_principal_keur") for p in op_periods)

    def test_tuho_senior_balance_is_computed(self):
        _, _, result = _run_tuho()
        op_periods = [p for p in result.periods if getattr(p, "is_operation", False)]
        # First operating period should have a positive senior balance
        assert op_periods[0].senior_balance_keur > 0

    def test_tuho_dscr_per_period_present(self):
        _, _, result = _run_tuho()
        op_periods = [p for p in result.periods if getattr(p, "is_operation", False)]
        dscrx = [p.dscr for p in op_periods if p.dscr > 0]
        assert len(dscrx) > 0, "No operating periods have positive DSCR for TUHO."


# ---------------------------------------------------------------------------
# C5: Tax per-period IS computed but Tax UI tab shows only rate/carryforward inputs
# ---------------------------------------------------------------------------

class TestTaxComputedButNotInUI:

    def test_tuho_per_period_tax_keur_present(self):
        _, _, result = _run_tuho()
        op_periods = [p for p in result.periods if getattr(p, "is_operation", False)]
        assert all(hasattr(p, "tax_keur") for p in op_periods)

    def test_tuho_total_tax_is_nonzero(self):
        _, _, result = _run_tuho()
        assert result.total_tax_keur > 0

    def test_tuho_tax_audit_fields_present(self):
        """Tax bridge fields are present on each period for TUHO."""
        _, _, result = _run_tuho()
        op_periods = [p for p in result.periods if getattr(p, "is_operation", False)]
        # These audit fields exist on the dataclass even if zero
        for field_name in [
            "cit_accrual_audit_keur",
            "tax_loss_opening_audit_keur",
            "tax_loss_closing_audit_keur",
            "taxable_profit_after_losses_audit_keur",
        ]:
            assert all(hasattr(p, field_name) for p in op_periods), (
                f"Field {field_name} missing from some WaterfallPeriod instances."
            )


# ---------------------------------------------------------------------------
# C6: Balance sheet can be assembled and should balance (Assets = Liabilities + Equity)
# ---------------------------------------------------------------------------

class TestBalanceSheetIdentity:

    def test_tuho_balance_sheet_closes(self):
        """Balance sheet should close (balance_check_keur near zero) for TUHO."""
        _, _, result = _run_tuho()
        fs = assemble_financial_statements(result)
        max_imbalance = fs.balance_sheet.max_abs_balance_check_keur
        # Allow 1 kEUR tolerance for floating-point accumulation across 60 periods
        assert max_imbalance < 1.0, (
            f"TUHO balance sheet imbalance {max_imbalance:.2f} kEUR exceeds 1 kEUR tolerance."
        )

    def test_oborovo_balance_sheet_closes(self):
        _, _, result = _run_oborovo()
        fs = assemble_financial_statements(result)
        max_imbalance = fs.balance_sheet.max_abs_balance_check_keur
        assert max_imbalance < 1.0, (
            f"Oborovo balance sheet imbalance {max_imbalance:.2f} kEUR exceeds 1 kEUR tolerance."
        )


# ---------------------------------------------------------------------------
# C7: WaterfallResult field inventory — documents every top-level KPI field
#     so future PRs can verify they didn't accidentally remove any.
# ---------------------------------------------------------------------------

class TestWaterfallResultFieldInventory:

    EXPECTED_SUMMARY_FIELDS = {
        "total_revenue_keur",
        "total_opex_keur",
        "total_ebitda_keur",
        "total_tax_keur",
        "total_senior_ds_keur",
        "total_shl_service_keur",
        "total_distribution_keur",
        "avg_dscr",
        "min_dscr",
        "max_dscr",
        "min_llcr",
        "min_plcr",
        "project_irr",
        "equity_irr",
        "sponsor_irr",
        "project_npv",
        "equity_npv",
    }

    def test_all_expected_summary_fields_present(self):
        _, _, result = _run_tuho()
        actual_fields = {f.name for f in dataclasses.fields(result)}
        missing = self.EXPECTED_SUMMARY_FIELDS - actual_fields
        assert not missing, f"WaterfallResult is missing expected fields: {missing}"


# ---------------------------------------------------------------------------
# C8: domain/financial_statements/ is NOT imported by waterfall_core.py
#     (confirms separation of concerns: FS is an offline assembly step)
# ---------------------------------------------------------------------------

class TestFinancialStatementsNotImportedByWaterfallCore:

    def test_waterfall_core_does_not_import_financial_statements(self):
        """Characterizes that waterfall_core.py does not import financial_statements.

        This separation means FS must be assembled after the waterfall run.
        If a future PR accidentally couples these, this test will catch it.
        """
        import ast
        from pathlib import Path

        core_path = Path(__file__).resolve().parents[1] / "app" / "waterfall_core.py"
        source = core_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = ""
                if isinstance(node, ast.ImportFrom) and node.module:
                    module = node.module
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name
                if "financial_statements" in module:
                    pytest.fail(
                        f"waterfall_core.py imports 'financial_statements' ({module}). "
                        "This couples the waterfall runtime to the FS assembly layer. "
                        "FS should be assembled separately after the run."
                    )
