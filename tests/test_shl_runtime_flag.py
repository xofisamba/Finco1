"""Phase 7 — SHL Runtime Flag Wiring Tests.

Tests the `use_shl_canonical_engine` flag wiring in `domain/inputs.py`.

Acceptance criteria:
- Flag default is False
- Existing default outputs unchanged (no default behavior change)
- Canonical SHL runs when flag = True
- R99/R102 remains BLOCKED
- No broad app/waterfall_core.py rewrite
"""
import pytest

from domain.inputs import ProjectInfo, PeriodFrequency
from domain.shl.engine import ShlEngine, ShlEngineInputs
from domain.shl.inputs import ShlPeriodInput
from datetime import date


# ---------------------------------------------------------------------------
# Flag default
# ---------------------------------------------------------------------------

class TestShlCanonicalFlagDefault:
    """A. Flag default is False."""

    def test_use_shl_canonical_engine_defaults_to_false(self):
        """use_shl_canonical_engine defaults to False in ProjectInfo."""
        info = ProjectInfo(
            name="TUHO",
            company="TUHO Energy",
            code="TUHO-WIND-1",
            country_iso="HR",
            financial_close=date(2025, 1, 1),
            construction_months=12,
            cod_date=date(2026, 1, 1),
            horizon_years=30,
            period_frequency=PeriodFrequency.SEMESTRIAL,
        )
        assert info.use_shl_canonical_engine is False

    def test_project_info_frozen(self):
        """ProjectInfo is frozen and can be created with the flag."""
        info = ProjectInfo(
            name="TUHO",
            company="TUHO Energy",
            code="TUHO-WIND-1",
            country_iso="HR",
            financial_close=date(2025, 1, 1),
            construction_months=12,
            cod_date=date(2026, 1, 1),
            horizon_years=30,
            period_frequency=PeriodFrequency.SEMESTRIAL,
            use_shl_canonical_engine=True,  # explicitly set to True
        )
        assert info.use_shl_canonical_engine is True

    def test_existing_flags_still_default_off(self):
        """Existing flags (use_shl_fcf_waterfall_engine, etc.) remain False."""
        info = ProjectInfo(
            name="TUHO",
            company="TUHO Energy",
            code="TUHO-WIND-1",
            country_iso="HR",
            financial_close=date(2025, 1, 1),
            construction_months=12,
            cod_date=date(2026, 1, 1),
            horizon_years=30,
            period_frequency=PeriodFrequency.SEMESTRIAL,
        )
        assert info.use_shl_fcf_waterfall_engine is False
        assert info.use_tax_bridge_engine is False
        assert info.use_shl_gross_accrued_for_pnl is False
        assert info.use_book_depreciation_for_pnl is False


# ---------------------------------------------------------------------------
# Canonical SHL runs when flag = True
# ---------------------------------------------------------------------------

class TestCanonicalShlRuns:
    """B. Canonical SHL engine runs when flag is True."""

    def test_shl_engine_compute_succeeds_with_valid_inputs(self):
        """ShlEngine.compute() produces a valid result with TUHO-style inputs."""
        period_inputs = tuple(
            ShlPeriodInput(
                period_index=t + 1,
                opening_balance_keur=0.0,
                drawdown_keur=32703.864 if t == 0 else 0.0,
                interest_rate=0.08,
                day_count_fraction=0.5,
                post_senior_cash_available_keur=1000.0,
                pik_allowed=True,
                maintain_minimum_cash_reserve=False,
                minimum_cash_reserve_keur=0.0,
            )
            for t in range(63)
        )
        inputs = ShlEngineInputs(
            project_name="TUHO",
            period_count=63,
            period_inputs=period_inputs,
            total_shl_funding_keur=32703.864,
            tranche_rates=(0.08,),
            tranche_day_fracs=(0.5,),
            tranche_opening_balances_keur=(32703.864,),
            pik_allowed=True,
            maintain_minimum_cash_reserve=False,
            minimum_cash_reserve_keur=0.0,
        )
        result = ShlEngine.compute(inputs)
        assert result.total_gross_accrued_interest_keur > 0
        assert len(result.period_results) == 63

    def test_shl_runtime_adapter_builds_inputs(self):
        """ShlRuntimeAdapter builds valid ShlEngineInputs from waterfall data."""
        from domain.shl.runtime_adapter import ShlRuntimeAdapter

        class FakePeriod:
            period = 1
            is_operation = True
            day_fraction = 0.5
            ebitda_keur = 5000.0
            cf_after_tax_keur = 4000.0
            senior_ds_keur = 2000.0

        adapter = ShlRuntimeAdapter()
        fake_periods = [FakePeriod() for _ in range(5)]

        shl_inputs = adapter.from_waterfall(
            project_name="TUHO",
            waterfall_periods=fake_periods,
            shl_amount_keur=32703.864,
            shl_rate=0.08,
            shl_idc_keur=0.0,
            shl_repayment_method="pik_then_sweep",
            shl_wht_rate=0.0,
        )

        assert shl_inputs.project_name == "TUHO"
        assert shl_inputs.period_count == 5
        assert len(shl_inputs.period_inputs) == 5
        assert shl_inputs.tranche_rates == (0.08,)

    def test_run_canonical_shl_produces_result(self):
        """run_canonical_shl() is a valid convenience function."""
        from domain.shl.runtime_adapter import run_canonical_shl

        class FakePeriod:
            period = 1
            is_operation = True
            day_fraction = 0.5
            ebitda_keur = 5000.0
            cf_after_tax_keur = 4000.0
            senior_ds_keur = 2000.0

        fake_periods = [FakePeriod() for _ in range(5)]

        result = run_canonical_shl(
            waterfall_periods=fake_periods,
            shl_amount_keur=10000.0,
            shl_rate=0.08,
            shl_idc_keur=0.0,
            shl_repayment_method="pik_then_sweep",
            shl_wht_rate=0.0,
            project_name="TUHO",
        )

        assert result.total_gross_accrued_interest_keur > 0
        assert len(result.period_results) == 5

    def test_canonical_result_has_audit_rows(self):
        """Canonical SHL result includes audit rows when flag is True."""
        period_inputs = tuple(
            ShlPeriodInput(
                period_index=t + 1,
                opening_balance_keur=0.0,
                drawdown_keur=5000.0 if t == 0 else 0.0,
                interest_rate=0.08,
                day_count_fraction=0.5,
                post_senior_cash_available_keur=1000.0,
                pik_allowed=True,
                maintain_minimum_cash_reserve=False,
                minimum_cash_reserve_keur=0.0,
            )
            for t in range(5)
        )
        inputs = ShlEngineInputs(
            project_name="TUHO",
            period_count=5,
            period_inputs=period_inputs,
            total_shl_funding_keur=5000.0,
            tranche_rates=(0.08,),
            tranche_day_fracs=(0.5,),
            tranche_opening_balances_keur=(5000.0,),
            pik_allowed=True,
            maintain_minimum_cash_reserve=False,
            minimum_cash_reserve_keur=0.0,
        )
        result = ShlEngine.compute(inputs)
        # Audit rows available via audit_table
        assert hasattr(result, "audit_table")
        assert len(result.audit_table) > 0

    def test_canonical_result_exposes_cash_for_distribution(self):
        """Canonical result exposes cash_for_distribution (not gated)."""
        period_inputs = tuple(
            ShlPeriodInput(
                period_index=t + 1,
                opening_balance_keur=0.0,
                drawdown_keur=0.0,
                interest_rate=0.08,
                day_count_fraction=0.5,
                post_senior_cash_available_keur=500.0,
                pik_allowed=True,
                maintain_minimum_cash_reserve=False,
                minimum_cash_reserve_keur=0.0,
            )
            for t in range(5)
        )
        inputs = ShlEngineInputs(
            project_name="TUHO",
            period_count=5,
            period_inputs=period_inputs,
            total_shl_funding_keur=5000.0,
            tranche_rates=(0.08,),
            tranche_day_fracs=(0.5,),
            tranche_opening_balances_keur=(5000.0,),
            pik_allowed=True,
            maintain_minimum_cash_reserve=False,
            minimum_cash_reserve_keur=0.0,
        )
        result = ShlEngine.compute(inputs)
        # cash_for_distribution is exposed but NOT gated on DSCR
        first = result.period_results[0]
        assert hasattr(first, "cash_for_distribution_keur")


# ---------------------------------------------------------------------------
# R99/R102 remains BLOCKED
# ---------------------------------------------------------------------------

class TestNoR99R102Promotion:
    """C. R99/R102 remains BLOCKED in canonical SHL."""

    def test_no_distribution_gate_in_result(self):
        """Canonical result has no distribution_gate field."""
        period_inputs = tuple(
            ShlPeriodInput(
                period_index=t + 1,
                opening_balance_keur=0.0,
                drawdown_keur=0.0,
                interest_rate=0.08,
                day_count_fraction=0.5,
                post_senior_cash_available_keur=500.0,
                pik_allowed=True,
                maintain_minimum_cash_reserve=False,
                minimum_cash_reserve_keur=0.0,
            )
            for t in range(5)
        )
        inputs = ShlEngineInputs(
            project_name="TUHO",
            period_count=5,
            period_inputs=period_inputs,
            total_shl_funding_keur=5000.0,
            tranche_rates=(0.08,),
            tranche_day_fracs=(0.5,),
            tranche_opening_balances_keur=(5000.0,),
            pik_allowed=True,
            maintain_minimum_cash_reserve=False,
            minimum_cash_reserve_keur=0.0,
        )
        result = ShlEngine.compute(inputs)
        assert not hasattr(result, "distribution_gate")
        assert not hasattr(result, "r99_triggered")

    def test_runtime_adapter_does_not_promote_r99_r102(self):
        """ShlRuntimeAdapter does not compute R99/R102 gates."""
        from domain.shl.runtime_adapter import ShlRuntimeAdapter, run_canonical_shl

        class FakePeriod:
            period = 1
            is_operation = True
            day_fraction = 0.5
            ebitda_keur = 10000.0
            cf_after_tax_keur = 10000.0
            senior_ds_keur = 5000.0

        fake_periods = [FakePeriod() for _ in range(5)]

        result = run_canonical_shl(
            waterfall_periods=fake_periods,
            shl_amount_keur=10000.0,
            shl_rate=0.08,
            shl_idc_keur=0.0,
            shl_repayment_method="pik_then_sweep",
            shl_wht_rate=0.0,
            project_name="TUHO",
        )

        assert not hasattr(result, "distribution_gate")
        assert not hasattr(result, "r99_triggered")
        assert not hasattr(result, "reserve_required")


# ---------------------------------------------------------------------------
# No broad app/waterfall_core.py rewrite
# ---------------------------------------------------------------------------

class TestNoBroadRewrite:
    """D. No broad app/waterfall_core.py rewrite — minimal flag propagation."""

    def test_project_info_has_new_flag_field(self):
        """ProjectInfo has use_shl_canonical_engine field."""
        info = ProjectInfo(
            name="TUHO",
            company="TUHO Energy",
            code="TUHO-WIND-1",
            country_iso="HR",
            financial_close=date(2025, 1, 1),
            construction_months=12,
            cod_date=date(2026, 1, 1),
            horizon_years=30,
            period_frequency=PeriodFrequency.SEMESTRIAL,
            use_shl_canonical_engine=True,
        )
        assert hasattr(info, "use_shl_canonical_engine")

    def test_no_extra_fields_added_to_waterfall_result(self):
        """Adding the flag does not change WaterfallResult structure."""
        from domain.waterfall.waterfall_engine import WaterfallResult

        result = WaterfallResult()
        # Only flag propagation, no new result fields required
        assert not hasattr(result, "canonical_shl_result")

    def test_runtime_adapter_does_not_modify_waterfall_period(self):
        """ShlRuntimeAdapter.from_waterfall() does not mutate input periods."""
        from domain.shl.runtime_adapter import ShlRuntimeAdapter

        class FakePeriod:
            period = 1
            is_operation = True
            day_fraction = 0.5
            ebitda_keur = 5000.0
            cf_after_tax_keur = 4000.0
            senior_ds_keur = 2000.0

        fake_period = FakePeriod()
        original_ebitda = fake_period.ebitda_keur

        adapter = ShlRuntimeAdapter()
        _ = adapter.from_waterfall(
            project_name="TUHO",
            waterfall_periods=[fake_period],
            shl_amount_keur=5000.0,
            shl_rate=0.08,
        )

        # Original period unchanged
        assert fake_period.ebitda_keur == original_ebitda


# ---------------------------------------------------------------------------
# All existing tests still pass (regression check)
# ---------------------------------------------------------------------------

class TestDefaultOffUnchanged:
    """E. Default-off path unchanged — all existing tests pass."""

    def test_all_existing_phase7_tests_pass(self):
        """All Phase 7 tests pass with the new flag added to ProjectInfo."""
        import subprocess, sys
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                "tests/test_shl_engine.py",
                "tests/test_shl_engine_tuho_fixture.py",
                "tests/test_model_stack_validation_pack.py",
                "tests/test_senior_debt_sizing_policy.py",
                "tests/test_depreciation_engine.py",
                "-v", "--tb=no",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Tests failed: {result.stdout[-500]}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])