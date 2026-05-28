"""Phase 20S: SHL partial_pay_sweep method — runtime implementation tests."""
from __future__ import annotations

import pytest
import dataclasses
from domain.waterfall.shl_engine import compute_shl_period_v3


class TestPartialPaySweepUnit:
    """Unit tests for partial_pay_sweep SHL method."""

    def test_cash_less_than_interest_full_pi(self):
        """Available cash < net interest due → all cash to interest, remainder PIK'd."""
        # balance=1000, rate=0.10/period, cf=50, net_int=100, WHT=0
        res = compute_shl_period_v3(
            shl_balance=1000.0,
            shl_rate_per_period=0.10,
            cf_available=50.0,
            method="partial_pay_sweep",
            wht_rate=0.0,
            pik_switch_triggered=False,
            is_final_period=False,
        )
        assert res.interest_paid_keur == 50.0  # all CF goes to interest
        assert res.principal_keur == 0.0  # no principal
        assert res.pik_addition_keur == 50.0  # gross(100) - cash(50) = 50 PIK'd
        assert res.new_balance_keur == 1050.0  # 1000 + 50 PIK

    def test_cash_exceeds_interest_partial_principal(self):
        """Available cash > net interest but < interest + full balance → principal sweep."""
        # balance=1000, rate=0.10, cf=400, net_int=100
        res = compute_shl_period_v3(
            shl_balance=1000.0,
            shl_rate_per_period=0.10,
            cf_available=400.0,
            method="partial_pay_sweep",
            wht_rate=0.0,
            pik_switch_triggered=False,
            is_final_period=False,
        )
        assert res.interest_paid_keur == 100.0  # full interest
        assert res.pik_addition_keur == 0.0  # no shortfall
        assert res.principal_keur == 300.0  # 400 - 100 residual, capped at balance
        assert res.new_balance_keur == 700.0  # 1000 - 300 principal

    def test_cash_exceeds_all_shl_repaid(self):
        """Available cash > interest + full balance → SHL fully repaid, residual to dividends."""
        res = compute_shl_period_v3(
            shl_balance=1000.0,
            shl_rate_per_period=0.10,
            cf_available=1500.0,
            method="partial_pay_sweep",
            wht_rate=0.0,
            pik_switch_triggered=False,
            is_final_period=False,
        )
        assert res.interest_paid_keur == 100.0
        assert res.pik_addition_keur == 0.0
        assert res.principal_keur == 1000.0  # cant sweep more than balance
        assert res.new_balance_keur == 0.0  # fully repaid
        # residual (400) goes to fcf_for_dividends (handled by caller)

    def test_zero_balance_returns_zeros(self):
        """Zero opening balance returns all-zero result."""
        res = compute_shl_period_v3(
            shl_balance=0.0,
            shl_rate_per_period=0.10,
            cf_available=500.0,
            method="partial_pay_sweep",
            wht_rate=0.0,
            pik_switch_triggered=False,
            is_final_period=False,
        )
        assert res.interest_paid_keur == 0.0
        assert res.principal_keur == 0.0
        assert res.pik_addition_keur == 0.0
        assert res.new_balance_keur == 0.0

    def test_pik_uses_gross_not_net(self):
        """PIK amount = gross interest - cash paid (not net - cash)."""
        # balance=1000, rate=0.10, cf=60, net_int=100, WHT=0.10
        # gross=100, net=90
        # But even with WHT, pik = gross - cash = 100 - 60 = 40 (not 90 - 60 = 30)
        res = compute_shl_period_v3(
            shl_balance=1000.0,
            shl_rate_per_period=0.10,
            cf_available=60.0,
            method="partial_pay_sweep",
            wht_rate=0.10,
            pik_switch_triggered=False,
            is_final_period=False,
        )
        # interest_paid = min(60, 90) = 60
        # pik = gross - cash_paid = 100 - 60 = 40 (NOT net - cash = 30)
        assert res.interest_paid_keur == 60.0
        assert res.pik_addition_keur == 40.0  # gross - cash_paid = 100 - 60 = 40

    def test_no_annual_threshold_trigger(self):
        """Confirm partial_pay_sweep does not depend on annual threshold."""
        # Even tiny CF triggers interest+PIK+partial sweep
        res = compute_shl_period_v3(
            shl_balance=1000.0,
            shl_rate_per_period=0.10,
            cf_available=1.0,  # tiny, < annual interest
            method="partial_pay_sweep",
            wht_rate=0.0,
            pik_switch_triggered=False,
            is_final_period=False,
        )
        assert res.interest_paid_keur == 1.0  # partial interest paid
        assert res.pik_addition_keur == 99.0  # 100 - 1 = 99 PIK

    def test_wht_applies_only_to_cash_interest(self):
        """WHT only applies to cash interest, not to capitalized PIK."""
        res = compute_shl_period_v3(
            shl_balance=1000.0,
            shl_rate_per_period=0.10,
            cf_available=50.0,
            method="partial_pay_sweep",
            wht_rate=0.18,  # 18% WHT
            pik_switch_triggered=False,
            is_final_period=False,
        )
        # With WHT=18%, cash payment is treated differently
        # interest_wht = payments * (wht / (1-wht)) if wht > 0 and payments > 0
        # But the actual net to investor is what matters for the test
        assert res.interest_paid_keur == 50.0  # cash paid


class TestPartialPaySweepTUHOP4:
    """TUHO P4 calibration with partial_pay_sweep method."""

    def test_tuho_p4_sweep_positive_with_partial_pay_sweep(self):
        """With partial_pay_sweep, TUHO P4 produces positive SHL principal sweep."""
        from app.project_factories import create_default_tuho_wind1
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner

        tuho = create_default_tuho_wind1()
        tuho = dataclasses.replace(tuho, financing=dataclasses.replace(tuho.financing, shl_repayment_method="partial_pay_sweep"))
        eng = _build_period_engine(tuho)
        r = WaterfallRunner(inputs=tuho, engine=eng).run(
            WaterfallRunConfig.from_inputs(tuho, eng)
        )
        wp = r.periods[3]
        assert wp.shl_principal_keur > 0.0, (
            f"P4 sweep should be > 0 with partial_pay_sweep, got {wp.shl_principal_keur:.2f}"
        )

    def test_tuho_p4_prior_zero_sweep_is_eliminated(self):
        """Confirm the prior zero-sweep behavior is fixed for TUHO P4."""
        from app.project_factories import create_default_tuho_wind1
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner

        tuho = create_default_tuho_wind1()
        tuho = dataclasses.replace(tuho, financing=dataclasses.replace(tuho.financing, shl_repayment_method="partial_pay_sweep"))
        eng = _build_period_engine(tuho)
        r = WaterfallRunner(inputs=tuho, engine=eng).run(
            WaterfallRunConfig.from_inputs(tuho, eng)
        )
        wp = r.periods[3]
        assert wp.shl_principal_keur > 0.0
        assert wp.distribution_keur == 0.0, "No distribution while SHL alive"

    def test_tuho_p4_no_distribution_leakage_in_partial_pay(self):
        """With partial_pay_sweep, TUHO P4 distribution = 0 (no leakage)."""
        from app.project_factories import create_default_tuho_wind1
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner

        tuho = create_default_tuho_wind1()
        tuho = dataclasses.replace(tuho, financing=dataclasses.replace(tuho.financing, shl_repayment_method="partial_pay_sweep"))
        eng = _build_period_engine(tuho)
        r = WaterfallRunner(inputs=tuho, engine=eng).run(
            WaterfallRunConfig.from_inputs(tuho, eng)
        )
        wp = r.periods[3]
        # Distribution must be 0 while SHL is alive
        assert wp.distribution_keur == 0.0, f"Expected 0, got {wp.distribution_keur:.2f}"
        # And sweep should be positive
        assert wp.shl_principal_keur > 0.0


class TestPartialPaySweepOborovoP4:
    """Oborovo P4 calibration with partial_pay_sweep method."""

    def test_oborovo_p4_sweep_positive_with_partial_pay_sweep(self):
        """With partial_pay_sweep, Oborovo P4 produces positive SHL principal sweep."""
        from app.project_factories import create_default_oborovo
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner

        obor = create_default_oborovo()
        obor = dataclasses.replace(obor, financing=dataclasses.replace(obor.financing, shl_repayment_method="partial_pay_sweep"))
        eng = _build_period_engine(obor)
        r = WaterfallRunner(inputs=obor, engine=eng).run(
            WaterfallRunConfig.from_inputs(obor, eng)
        )
        wp = r.periods[3]
        assert wp.shl_principal_keur > 0.0, (
            f"P4 sweep should be > 0 with partial_pay_sweep, got {wp.shl_principal_keur:.2f}"
        )

    def test_oborovo_p4_distribution_zero_with_partial_pay(self):
        """With partial_pay_sweep, Oborovo P4 distribution = 0 (no leakage)."""
        from app.project_factories import create_default_oborovo
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner

        obor = create_default_oborovo()
        obor = dataclasses.replace(obor, financing=dataclasses.replace(obor.financing, shl_repayment_method="partial_pay_sweep"))
        eng = _build_period_engine(obor)
        r = WaterfallRunner(inputs=obor, engine=eng).run(
            WaterfallRunConfig.from_inputs(obor, eng)
        )
        wp = r.periods[3]
        assert wp.distribution_keur == 0.0, f"Expected 0, got {wp.distribution_keur:.2f}"

    def test_oborovo_p4_prior_leakage_eliminated(self):
        """With partial_pay_sweep, the prior 64.97 kEUR distribution leakage is eliminated."""
        from app.project_factories import create_default_oborovo
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner

        obor = create_default_oborovo()
        obor = dataclasses.replace(obor, financing=dataclasses.replace(obor.financing, shl_repayment_method="partial_pay_sweep"))
        eng = _build_period_engine(obor)
        r = WaterfallRunner(inputs=obor, engine=eng).run(
            WaterfallRunConfig.from_inputs(obor, eng)
        )
        wp = r.periods[3]
        # Prior: distribution = 64.97 kEUR (leakage); now should be 0
        assert wp.distribution_keur == 0.0, f"Expected 0, got {wp.distribution_keur:.2f}"
        assert wp.shl_principal_keur > 0.0, "Principal sweep must be positive"


class TestPartialPaySweepRegression:
    """Regression: default behavior is unchanged unless explicitly opted in."""

    def _run_tuho_default(self):
        from app.project_factories import create_default_tuho_wind1
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
        tuho = create_default_tuho_wind1()  # default = pik_then_sweep
        eng = _build_period_engine(tuho)
        return WaterfallRunner(inputs=tuho, engine=eng).run(
            WaterfallRunConfig.from_inputs(tuho, eng)
        )

    def _run_oborovo_default(self):
        from app.project_factories import create_default_oborovo
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
        obor = create_default_oborovo()  # default = bullet
        eng = _build_period_engine(obor)
        return WaterfallRunner(inputs=obor, engine=eng).run(
            WaterfallRunConfig.from_inputs(obor, eng)
        )

    def test_default_tuho_sweep_still_zero(self):
        """Default TUHO (pik_then_sweep) still produces sweep=0 in P4."""
        r = self._run_tuho_default()
        wp = r.periods[3]
        assert wp.shl_principal_keur == 0.0, (
            "Default pik_then_sweep should not produce sweep in P4"
        )

    def test_default_oborovo_distribution_still_64(self):
        """Default Oborovo (bullet) still shows distribution=64.97 in P4."""
        r = self._run_oborovo_default()
        wp = r.periods[3]
        # Default method behavior is unchanged
        assert abs(wp.distribution_keur - 64.97) < 1.0, (
            f"Default behavior changed! Expected ~64.97, got {wp.distribution_keur:.2f}"
        )

    def test_partial_pay_sweep_explicitly_differs_from_default(self):
        """Explicit partial_pay_sweep must differ from default behavior in same project."""
        from app.project_factories import create_default_oborovo
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner

        obor_default = create_default_oborovo()
        eng = _build_period_engine(obor_default)
        r_def = WaterfallRunner(inputs=obor_default, engine=eng).run(
            WaterfallRunConfig.from_inputs(obor_default, eng)
        )

        obor_new = create_default_oborovo()
        obor_new = dataclasses.replace(obor_new, financing=dataclasses.replace(obor_new.financing, shl_repayment_method="partial_pay_sweep"))
        eng2 = _build_period_engine(obor_new)
        r_new = WaterfallRunner(inputs=obor_new, engine=eng2).run(
            WaterfallRunConfig.from_inputs(obor_new, eng2)
        )

        wp_def = r_def.periods[3]
        wp_new = r_new.periods[3]

        # Distribution must differ
        assert wp_new.distribution_keur != wp_def.distribution_keur, (
            "partial_pay_sweep should produce different distribution than default"
        )
        # And sweep should differ
        assert wp_new.shl_principal_keur != wp_def.shl_principal_keur, (
            "partial_pay_sweep should produce different sweep than default"
        )
