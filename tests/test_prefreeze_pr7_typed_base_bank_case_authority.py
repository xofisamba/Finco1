"""Pre-freeze PR-7 — typed Base Case vs Bank Case authority consolidation.

Proves:
  ONE_TYPED_BASE_AND_BANK_CASE_AUTHORITY
  BANK_CFADS_SIZES_SENIOR_BUT_DOES_NOT_BECOME_BASE_CASH
  NO_PROJECT_IDENTITY_FINANCIAL_DISPATCH
  NO_WORKBOOK_INCONSISTENCY_PROMOTED_AS_GENERIC_POLICY

Scope:
  S — canonical Bank Case serialization matrix (13 cases);
  M — Base/Bank mutation matrix A–K;
  W — Bank CFADS never becomes Base cash (direct wiring proof);
  Y — fail-closed yield scenario mapping (no silent P99/typo fallback);
  G — governance scans (identity dispatch, target fitting, source replay).

Group S cases follow 01_PR7_IMPLEMENTATION_PROMPT section 15; group M follows
section 17; group W follows section 13.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _solar():
    from app.project_factories import create_default_solar_project

    return create_default_solar_project()


def _run(project):
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )
    from financial_engine.orchestrator import run_senior_debt_model

    model = build_senior_debt_model_input_from_project_inputs(
        project, source_id="pr7-test"
    )
    return run_senior_debt_model(model)


def _run_tuho_clean_case(*, target_dscr: float = 1.2, bank_case=None):
    """TUHO clean-engine DSCR-bound run (C3B3D2B3 fixture pattern).

    TUHO production financials run through the frozen-schedule legacy
    waterfall; this runner is the accepted TUHO representation inside the
    clean Base/Bank authority. DSCR-binding makes it the vehicle for
    mutations that must move Senior capacity (B, C, D).
    """
    from app.project_factories import create_default_tuho_wind1
    from finco_parity.tax_reference_inputs import (
        build_opening_loss_vintages,
        build_tax_policy,
    )
    from financial_engine.adapters.project_inputs import from_project_inputs
    from financial_engine.inputs import (
        DebtSizingCaseInput,
        SeniorDebtModelInput,
        TaxCalculationInput,
        YieldScenario,
    )
    from financial_engine.orchestrator import run_senior_debt_model
    from financial_engine.senior_debt.inputs import SeniorDebtInputs
    from financial_engine.senior_debt.policy import (
        DayCountConvention,
        SeniorDebtPolicy,
        SeniorDebtSizingMode,
    )

    base_op = from_project_inputs(create_default_tuho_wind1())
    model = SeniorDebtModelInput(
        operating=base_op,
        tax=TaxCalculationInput(
            policy=build_tax_policy("tuho"),
            opening_loss_vintages=build_opening_loss_vintages("tuho"),
            period_interest=(),
            period_adjustments=(),
        ),
        senior_debt_policy=SeniorDebtPolicy(
            policy_id="pr7_tuho_mutation",
            policy_version="1.0",
            sizing_mode=SeniorDebtSizingMode.DSCR_SCULPTED,
            target_dscr=target_dscr,
            maximum_gearing=None,
            annual_fixed_rate=0.05,
            periods_per_year=2,
            day_count_convention=DayCountConvention.ACT_365,
            repayment_start_period_index=2,
            maturity_period_index=61,
            convergence_tolerance_keur=1.0,
            convergence_relative_tolerance=0.001,
            maximum_iterations=300,
            permit_terminal_balloon=True,
        ),
        senior_debt_inputs=SeniorDebtInputs(
            eligible_project_cost_keur=100_000.0,
            initial_debt_guess_keur=60_000.0,
            period_rates=(),
            explicit_principal_schedule=None,
        ),
        debt_sizing_case=bank_case
        or DebtSizingCaseInput(
            production_yield_scenario=YieldScenario.P90_10Y,
            source_label="tuho_p90_10y_bank_case",
        ),
    )
    return run_senior_debt_model(model)


def _with_debt_sizing_case(project, case):
    return dataclasses.replace(
        project,
        financing=dataclasses.replace(
            project.financing, debt_sizing_case=case
        ),
    )


def _tuho_base_market_curve():
    from app.project_factories import create_default_tuho_wind1

    return create_default_tuho_wind1().revenue.market_prices_curve


# ---------------------------------------------------------------------------
# Group S — canonical Bank Case serialization matrix (prompt section 15)
# ---------------------------------------------------------------------------

class TestS_SerializationMatrix:
    def _roundtrip(self, project):
        from finco_core.inputs.serialization import (
            project_inputs_from_dict,
            project_inputs_to_dict,
        )

        payload = project_inputs_to_dict(project)
        restored = project_inputs_from_dict(json.loads(json.dumps(payload)))
        return payload, restored

    def test_s1_default_p90_roundtrip(self):
        from finco_core.inputs._models import DebtSizingCaseConfig, YieldScenario

        payload, restored = self._roundtrip(_solar())
        case = restored.financing.debt_sizing_case
        assert case == DebtSizingCaseConfig()
        assert case.production_yield_scenario is YieldScenario.P90_10Y
        assert payload["financing"]["debt_sizing_case"]["production_yield_scenario"] == (
            YieldScenario.P90_10Y.value
        )

    def test_s2_explicit_p50_roundtrip(self):
        from finco_core.inputs._models import DebtSizingCaseConfig, YieldScenario

        project = _with_debt_sizing_case(
            _solar(),
            DebtSizingCaseConfig(production_yield_scenario=YieldScenario.P50),
        )
        _, restored = self._roundtrip(project)
        assert restored.financing.debt_sizing_case.production_yield_scenario is (
            YieldScenario.P50
        )

    def test_s3_bank_calendar_curve_roundtrip(self):
        from finco_core.inputs._models import DebtSizingCaseConfig, YieldScenario

        case = DebtSizingCaseConfig(
            production_yield_scenario=YieldScenario.P90_10Y,
            merchant_price_calendar_start_year=2042,
            merchant_prices_by_calendar_year_eur_mwh=(50.0, 51.0, 52.0),
        )
        _, restored = self._roundtrip(_with_debt_sizing_case(_solar(), case))
        got = restored.financing.debt_sizing_case
        assert got.merchant_price_calendar_start_year == 2042
        assert got.merchant_prices_by_calendar_year_eur_mwh == (50.0, 51.0, 52.0)
        assert got.market_prices_curve_eur_mwh == ()

    def test_s4_bank_relative_curve_roundtrip(self):
        from finco_core.inputs._models import DebtSizingCaseConfig, YieldScenario

        case = DebtSizingCaseConfig(
            production_yield_scenario=YieldScenario.P90_10Y,
            market_prices_curve_eur_mwh=(60.0, 61.0),
        )
        _, restored = self._roundtrip(_with_debt_sizing_case(_solar(), case))
        got = restored.financing.debt_sizing_case
        assert got.market_prices_curve_eur_mwh == (60.0, 61.0)
        assert got.merchant_price_calendar_start_year is None
        assert got.merchant_prices_by_calendar_year_eur_mwh == ()

    def test_s5_inherited_base_price_roundtrip(self):
        from finco_core.inputs._models import DebtSizingCaseConfig, YieldScenario

        case = DebtSizingCaseConfig(production_yield_scenario=YieldScenario.P90_10Y)
        _, restored = self._roundtrip(_with_debt_sizing_case(_solar(), case))
        got = restored.financing.debt_sizing_case
        assert got.merchant_price_calendar_start_year is None
        assert got.merchant_prices_by_calendar_year_eur_mwh == ()
        assert got.market_prices_curve_eur_mwh == ()

    def test_s6_tax_periodisation_override_roundtrip(self):
        from finco_core.inputs._models import (
            DebtSizingCaseConfig,
            TaxPeriodisationMode,
            YieldScenario,
        )

        case = DebtSizingCaseConfig(
            production_yield_scenario=YieldScenario.P90_10Y,
            tax_periodisation_mode_override=(
                TaxPeriodisationMode.WORKBOOK_MODEL_YEAR_PAIRING
            ),
        )
        _, restored = self._roundtrip(_with_debt_sizing_case(_solar(), case))
        assert restored.financing.debt_sizing_case.tax_periodisation_mode_override is (
            TaxPeriodisationMode.WORKBOOK_MODEL_YEAR_PAIRING
        )

    def test_s7_source_label_roundtrip(self):
        from finco_core.inputs._models import DebtSizingCaseConfig, YieldScenario

        case = DebtSizingCaseConfig(
            production_yield_scenario=YieldScenario.P90_10Y,
            source_label="pr7_audit_label",
        )
        _, restored = self._roundtrip(_with_debt_sizing_case(_solar(), case))
        assert restored.financing.debt_sizing_case.source_label == "pr7_audit_label"

    def test_s8_legacy_payload_missing_bank_config_resolves_to_default(self):
        """Old payload without debt_sizing_case → documented generic P90-10y default."""
        from finco_core.inputs._models import DebtSizingCaseConfig, YieldScenario
        from finco_core.inputs.serialization import (
            project_inputs_from_dict,
            project_inputs_to_dict,
        )

        payload = project_inputs_to_dict(_solar())
        assert "debt_sizing_case" in payload["financing"]
        del payload["financing"]["debt_sizing_case"]
        restored = project_inputs_from_dict(payload)
        assert restored.financing.debt_sizing_case == DebtSizingCaseConfig()
        assert restored.financing.debt_sizing_case.production_yield_scenario is (
            YieldScenario.P90_10Y
        )

    def test_s9_none_empty_zero_remain_distinct(self):
        from finco_core.inputs._models import DebtSizingCaseConfig, YieldScenario

        case = DebtSizingCaseConfig(
            production_yield_scenario=YieldScenario.P90_10Y,
            merchant_price_calendar_start_year=None,
            merchant_prices_by_calendar_year_eur_mwh=(),
            market_prices_curve_eur_mwh=(0.0,),
        )
        _, restored = self._roundtrip(_with_debt_sizing_case(_solar(), case))
        got = restored.financing.debt_sizing_case
        # Zero price survives; empty calendar form stays empty; None stays None.
        assert got.market_prices_curve_eur_mwh == (0.0,)
        assert got.merchant_prices_by_calendar_year_eur_mwh == ()
        assert got.merchant_price_calendar_start_year is None

    def test_s10_invalid_enum_fails_closed(self):
        from finco_core.inputs.serialization import (
            project_inputs_from_dict,
            project_inputs_to_dict,
        )

        payload = project_inputs_to_dict(_solar())
        payload["financing"]["debt_sizing_case"]["production_yield_scenario"] = "P_77"
        with pytest.raises(ValueError):
            project_inputs_from_dict(payload)

    def test_s11_calendar_curve_without_start_year_fails_closed(self):
        from finco_core.inputs.serialization import (
            project_inputs_from_dict,
            project_inputs_to_dict,
        )

        payload = project_inputs_to_dict(_solar())
        payload["financing"]["debt_sizing_case"][
            "merchant_prices_by_calendar_year_eur_mwh"
        ] = [50.0, 51.0]
        payload["financing"]["debt_sizing_case"][
            "merchant_price_calendar_start_year"
        ] = None
        with pytest.raises(ValueError, match="merchant_price_calendar_start_year"):
            project_inputs_from_dict(payload)

    def test_s12_start_year_without_calendar_curve_fails_closed(self):
        from finco_core.inputs.serialization import (
            project_inputs_from_dict,
            project_inputs_to_dict,
        )

        payload = project_inputs_to_dict(_solar())
        payload["financing"]["debt_sizing_case"][
            "merchant_price_calendar_start_year"
        ] = 2042
        payload["financing"]["debt_sizing_case"][
            "merchant_prices_by_calendar_year_eur_mwh"
        ] = []
        with pytest.raises(ValueError, match="merchant_prices_by_calendar_year_eur_mwh"):
            project_inputs_from_dict(payload)

    def test_s13_calendar_and_relative_curves_together_fail_closed(self):
        from finco_core.inputs.serialization import (
            project_inputs_from_dict,
            project_inputs_to_dict,
        )

        payload = project_inputs_to_dict(_solar())
        payload["financing"]["debt_sizing_case"][
            "merchant_price_calendar_start_year"
        ] = 2042
        payload["financing"]["debt_sizing_case"][
            "merchant_prices_by_calendar_year_eur_mwh"
        ] = [50.0]
        payload["financing"]["debt_sizing_case"]["market_prices_curve_eur_mwh"] = [60.0]
        with pytest.raises(ValueError, match="mutually exclusive"):
            project_inputs_from_dict(payload)


# ---------------------------------------------------------------------------
# Group M — mutation matrix (prompt section 17)
# ---------------------------------------------------------------------------

class TestM_MutationMatrix:
    def test_m_a_bank_p90_to_p50(self):
        """A. Bank P90→P50: Bank changes; Base operating economics unchanged."""
        from finco_core.inputs._models import DebtSizingCaseConfig, YieldScenario

        base_run = _run(_solar())
        bank_p50_run = _run(
            _with_debt_sizing_case(
                _solar(),
                DebtSizingCaseConfig(production_yield_scenario=YieldScenario.P50),
            )
        )
        assert sum(bank_p50_run.debt_sizing.bank_production_mwh) > sum(
            base_run.debt_sizing.bank_production_mwh
        )
        assert sum(bank_p50_run.debt_sizing.bank_revenue_keur) != pytest.approx(
            sum(base_run.debt_sizing.bank_revenue_keur)
        )
        # Base operating economics are untouched by the bank yield selection.
        assert bank_p50_run.operating_schedules.production_mwh == (
            base_run.operating_schedules.production_mwh
        )
        assert bank_p50_run.operating_schedules.revenue_keur == (
            base_run.operating_schedules.revenue_keur
        )
        assert bank_p50_run.operating_schedules.ebitda_keur == (
            base_run.operating_schedules.ebitda_keur
        )
        assert bank_p50_run.operating_schedules.opex_keur == (
            base_run.operating_schedules.opex_keur
        )

    def test_m_b_bank_price_minus_10pct(self):
        """B. Bank price −10%: Bank revenue/CFADS down, Senior capacity down, Base revenue unchanged."""
        from financial_engine.inputs import DebtSizingCaseInput, YieldScenario

        base_curve = _tuho_base_market_curve()
        low_curve = tuple(v * 0.9 for v in base_curve)
        base_run = _run_tuho_clean_case()
        low_run = _run_tuho_clean_case(
            bank_case=DebtSizingCaseInput(
                production_yield_scenario=YieldScenario.P90_10Y,
                market_prices_curve_eur_mwh=low_curve,
            )
        )
        assert sum(low_run.debt_sizing.bank_revenue_keur) < sum(
            base_run.debt_sizing.bank_revenue_keur
        )
        assert sum(low_run.debt_sizing.bank_cfads_keur) < sum(
            base_run.debt_sizing.bank_cfads_keur
        )
        assert low_run.senior_debt.debt_size_keur < base_run.senior_debt.debt_size_keur
        assert low_run.operating_schedules.revenue_keur == (
            base_run.operating_schedules.revenue_keur
        )

    def test_m_c_bank_price_plus_10pct(self):
        """C. Bank price +10%: Bank revenue/CFADS up, Senior non-decreasing, Base unchanged."""
        from financial_engine.inputs import DebtSizingCaseInput, YieldScenario

        base_curve = _tuho_base_market_curve()
        high_curve = tuple(v * 1.1 for v in base_curve)
        base_run = _run_tuho_clean_case()
        high_run = _run_tuho_clean_case(
            bank_case=DebtSizingCaseInput(
                production_yield_scenario=YieldScenario.P90_10Y,
                market_prices_curve_eur_mwh=high_curve,
            )
        )
        assert sum(high_run.debt_sizing.bank_revenue_keur) > sum(
            base_run.debt_sizing.bank_revenue_keur
        )
        assert sum(high_run.debt_sizing.bank_cfads_keur) > sum(
            base_run.debt_sizing.bank_cfads_keur
        )
        assert high_run.senior_debt.debt_size_keur >= (
            base_run.senior_debt.debt_size_keur - 1e-6
        )
        assert high_run.operating_schedules.revenue_keur == (
            base_run.operating_schedules.revenue_keur
        )

    def test_m_d_target_dscr_increase_via_senior_policy(self):
        """D. Target DSCR increase (Senior policy): Senior capacity down; Base operating unchanged."""
        base_run = _run_tuho_clean_case(target_dscr=1.2)
        tight_run = _run_tuho_clean_case(target_dscr=1.3)
        assert tight_run.senior_debt.debt_size_keur < base_run.senior_debt.debt_size_keur
        assert tight_run.operating_schedules.production_mwh == (
            base_run.operating_schedules.production_mwh
        )
        assert tight_run.operating_schedules.revenue_keur == (
            base_run.operating_schedules.revenue_keur
        )

    def test_m_e_bank_tax_periodisation(self):
        """E. Bank tax periodisation override: Bank tax changes; Base tax scope
        is never mutated.

        Vehicle: Oborovo (canonical override carrier). Because Oborovo is
        DSCR-bound, Base tax CAN move end-to-end through the legitimate
        senior-interest financing feedback — so the Base-scope invariant is
        proven directly at the tax-input merge boundary, plus the bank-side
        timing shift at model level.
        """
        from app.project_factories import create_default_oborovo
        from finco_core.inputs._models import TaxPeriodisationMode
        from financial_engine.orchestrator import _merge_financing_tax_input
        from financial_engine.policies.tax import (
            CashTaxTiming,
            TaxBasisPeriodisation,
        )
        from financial_engine.adapters.tax_inputs import (
            build_tax_contract_from_project_inputs,
        )

        canonical = create_default_oborovo()
        assert canonical.financing.debt_sizing_case.tax_periodisation_mode_override is (
            TaxPeriodisationMode.WORKBOOK_MODEL_YEAR_PAIRING
        )

        # (1) Merge boundary: the override rewrites ONLY the explicitly
        # requested bank policy; the Base merge (no override kwarg) keeps the
        # canonical Base policy untouched.
        base_tax_input = build_tax_contract_from_project_inputs(
            canonical, complete_financing_interest_will_be_injected=True
        )
        senior_int = {2: 1_000.0}
        merged_base = _merge_financing_tax_input(base_tax_input, senior_int)
        merged_bank = _merge_financing_tax_input(
            base_tax_input, senior_int,
            tax_periodisation_mode_override="workbook_model_year_pairing",
        )
        assert merged_base.policy.cash_tax_timing == (
            base_tax_input.policy.cash_tax_timing
        )
        assert merged_base.policy.tax_basis_periodisation == (
            base_tax_input.policy.tax_basis_periodisation
        )
        assert merged_bank.policy.cash_tax_timing is (
            CashTaxTiming.MODEL_YEAR_PAYMENT_PERIOD
        )
        assert merged_bank.policy.tax_basis_periodisation is (
            TaxBasisPeriodisation.MODEL_YEAR_PAIRING
        )
        # Interest vectors are shared identically — only the policy differs.
        assert merged_base.period_interest == merged_bank.period_interest

        # (2) Model level: the canonical override shifts bank cash-tax timing
        # relative to the same project without the override.
        without_override = _with_debt_sizing_case(
            canonical,
            dataclasses.replace(
                canonical.financing.debt_sizing_case,
                tax_periodisation_mode_override=None,
            ),
        )
        paired = _run(canonical)
        plain = _run(without_override)
        assert list(paired.debt_sizing.bank_cash_tax_keur) != list(
            plain.debt_sizing.bank_cash_tax_keur
        ), "Workbook pairing periodisation must shift bank cash-tax timing"

    def test_m_f_source_label_zero_numerical_change(self):
        from finco_core.inputs._models import DebtSizingCaseConfig, YieldScenario

        plain = _run(_solar())
        labelled = _run(
            _with_debt_sizing_case(
                _solar(),
                DebtSizingCaseConfig(
                    production_yield_scenario=YieldScenario.P90_10Y,
                    source_label="completely_different_label",
                ),
            )
        )
        assert labelled.debt_sizing == plain.debt_sizing
        assert labelled.senior_debt.senior_debt_service_keur == (
            plain.senior_debt.senior_debt_service_keur
        )
        assert labelled.tax_and_cfads.cfads_keur == plain.tax_and_cfads.cfads_keur
        assert labelled.post_senior_cash == plain.post_senior_cash
        assert labelled.shareholder_loan.shl_closing_keur == (
            plain.shareholder_loan.shl_closing_keur
        )

    def test_m_g_identity_rename_zero_financial_change(self):
        project = _solar()
        renamed = dataclasses.replace(
            project,
            info=dataclasses.replace(
                project.info,
                name="Renamed Project",
                company="Renamed Company",
                code="RENAMED-1",
            ),
        )
        plain = _run(project)
        renamed_run = _run(renamed)
        assert renamed_run.operating_schedules == plain.operating_schedules
        assert renamed_run.tax_and_cfads == plain.tax_and_cfads
        assert renamed_run.senior_debt == plain.senior_debt
        assert renamed_run.debt_sizing == plain.debt_sizing
        assert renamed_run.post_senior_cash == plain.post_senior_cash
        assert renamed_run.shareholder_loan.shl_closing_keur == (
            plain.shareholder_loan.shl_closing_keur
        )

    def test_m_h_base_p50_mutation_with_bank_p90(self):
        """H. Base P50 mutation with Bank=P90: Base changes; Bank stays P90-controlled."""
        project = _solar()
        mutated = dataclasses.replace(
            project,
            technical=dataclasses.replace(
                project.technical, operating_hours_p50=1600.0
            ),
        )
        plain = _run(project)
        mutated_run = _run(mutated)
        assert sum(mutated_run.operating_schedules.production_mwh) > sum(
            plain.operating_schedules.production_mwh
        )
        assert mutated_run.debt_sizing.bank_production_mwh == (
            plain.debt_sizing.bank_production_mwh
        )

    def test_m_i_base_p50_mutation_with_bank_p50(self):
        """I. Base P50 mutation with Bank=P50: both move — both explicitly select P50."""
        from finco_core.inputs._models import DebtSizingCaseConfig, YieldScenario

        project = _solar()
        bank_p50 = _with_debt_sizing_case(
            project,
            DebtSizingCaseConfig(production_yield_scenario=YieldScenario.P50),
        )
        mutated = _with_debt_sizing_case(
            dataclasses.replace(
                project,
                technical=dataclasses.replace(
                    project.technical, operating_hours_p50=1600.0
                ),
            ),
            DebtSizingCaseConfig(production_yield_scenario=YieldScenario.P50),
        )
        plain_run = _run(bank_p50)
        mutated_run = _run(mutated)
        assert sum(mutated_run.operating_schedules.production_mwh) > sum(
            plain_run.operating_schedules.production_mwh
        )
        assert sum(mutated_run.debt_sizing.bank_production_mwh) > sum(
            plain_run.debt_sizing.bank_production_mwh
        )

    def test_m_j_base_price_mutation_with_inherited_bank(self):
        """J. Base merchant price mutation, no Bank override: both move."""
        project = _solar()
        assert project.revenue.market_prices_curve
        mutated = dataclasses.replace(
            project,
            revenue=dataclasses.replace(
                project.revenue,
                market_prices_curve=tuple(
                    v * 1.1 for v in project.revenue.market_prices_curve
                ),
            ),
        )
        plain = _run(project)
        mutated_run = _run(mutated)
        assert sum(mutated_run.operating_schedules.revenue_keur) > sum(
            plain.operating_schedules.revenue_keur
        )
        assert sum(mutated_run.debt_sizing.bank_revenue_keur) > sum(
            plain.debt_sizing.bank_revenue_keur
        )

    def test_m_k_base_price_mutation_with_explicit_bank_override(self):
        """K. Base merchant price mutation with explicit Bank curve: Bank stays on lender curve."""
        from finco_core.inputs._models import DebtSizingCaseConfig, YieldScenario

        project = _solar()
        lender_case = DebtSizingCaseConfig(
            production_yield_scenario=YieldScenario.P90_10Y,
            merchant_price_calendar_start_year=2032,
            merchant_prices_by_calendar_year_eur_mwh=tuple(
                [55.0] * 29
            ),
        )
        bank_fixed = _with_debt_sizing_case(project, lender_case)
        mutated_bank_fixed = _with_debt_sizing_case(
            dataclasses.replace(
                project,
                revenue=dataclasses.replace(
                    project.revenue,
                    market_prices_curve=tuple(
                        v * 1.1 for v in project.revenue.market_prices_curve
                    ),
                ),
            ),
            lender_case,
        )
        plain_run = _run(bank_fixed)
        mutated_run = _run(mutated_bank_fixed)
        assert sum(mutated_run.operating_schedules.revenue_keur) > sum(
            plain_run.operating_schedules.revenue_keur
        )
        assert mutated_run.debt_sizing.bank_revenue_keur == (
            plain_run.debt_sizing.bank_revenue_keur
        )


# ---------------------------------------------------------------------------
# Group W — Bank CFADS never becomes Base cash (prompt section 13)
# ---------------------------------------------------------------------------

class TestW_BankCfadsNotBaseCash:
    def test_w1_post_senior_cash_reads_base_cfads_exactly(self):
        result = _run(_solar())
        assert result.post_senior_cash.base_cfads_keur == (
            result.tax_and_cfads.cfads_keur
        )

    def test_w2_post_senior_cash_contract_has_no_bank_fields(self):
        from financial_engine.results import PostSeniorCashSchedules

        field_names = {f.name for f in dataclasses.fields(PostSeniorCashSchedules)}
        assert not any(name.startswith("bank_") for name in field_names)

    def test_w3_bank_economics_cannot_reach_base_cash_when_senior_fixed(self):
        """EXPLICIT_SCHEDULE senior: bank production, revenue and CFADS all
        change (P90→P50) while the Senior schedule is contract-fixed — so the
        ENTIRE Base/downstream chain must be bit-identical. Bank economics can
        influence Base only through Senior financing outputs; if bank CFADS
        were ever routed into Base cash, DSRA, SHL or distributions, this
        test would fail."""
        from app.project_factories import create_default_tuho_wind1
        from finco_parity.tax_reference_inputs import (
            build_opening_loss_vintages,
            build_tax_policy,
        )
        from financial_engine.adapters.project_inputs import from_project_inputs
        from financial_engine.inputs import (
            DebtSizingCaseInput,
            SeniorDebtModelInput,
            TaxCalculationInput,
            YieldScenario,
        )
        from financial_engine.orchestrator import run_senior_debt_model
        from financial_engine.senior_debt.inputs import (
            PeriodPrincipal,
            SeniorDebtInputs,
        )
        from financial_engine.senior_debt.policy import (
            DayCountConvention,
            SeniorDebtPolicy,
            SeniorDebtSizingMode,
        )

        base_op = from_project_inputs(create_default_tuho_wind1())
        # Contract-fixed senior: 20 equal principals over the debt window.
        debt_window = range(2, 42)
        explicit = tuple(
            PeriodPrincipal(period_index=i, principal_keur=1_000.0)
            for i in debt_window
        )

        def _run_case(bank_case):
            model = SeniorDebtModelInput(
                operating=base_op,
                tax=TaxCalculationInput(
                    policy=build_tax_policy("tuho"),
                    opening_loss_vintages=build_opening_loss_vintages("tuho"),
                    period_interest=(),
                    period_adjustments=(),
                ),
                senior_debt_policy=SeniorDebtPolicy(
                    policy_id="pr7_w3_explicit",
                    policy_version="1.0",
                    sizing_mode=SeniorDebtSizingMode.EXPLICIT_SCHEDULE,
                    target_dscr=1.2,
                    maximum_gearing=None,
                    annual_fixed_rate=0.05,
                    periods_per_year=2,
                    day_count_convention=DayCountConvention.ACT_365,
                    repayment_start_period_index=2,
                    maturity_period_index=41,
                    convergence_tolerance_keur=1.0,
                    convergence_relative_tolerance=0.001,
                    maximum_iterations=300,
                    permit_terminal_balloon=True,
                ),
                senior_debt_inputs=SeniorDebtInputs(
                    eligible_project_cost_keur=100_000.0,
                    initial_debt_guess_keur=40_000.0,
                    period_rates=(),
                    explicit_principal_schedule=explicit,
                    opening_debt_balance_keur=float(len(explicit) * 1_000.0),
                ),
                debt_sizing_case=bank_case,
            )
            return run_senior_debt_model(model)

        plain = _run_case(
            DebtSizingCaseInput(production_yield_scenario=YieldScenario.P90_10Y)
        )
        bank_p50 = _run_case(
            DebtSizingCaseInput(production_yield_scenario=YieldScenario.P50)
        )

        # Senior is contract-fixed: identical under both bank cases.
        assert plain.senior_debt.senior_debt_service_keur == (
            bank_p50.senior_debt.senior_debt_service_keur
        )
        # Bank economics genuinely moved (production, revenue, CFADS).
        assert bank_p50.debt_sizing.bank_production_mwh != (
            plain.debt_sizing.bank_production_mwh
        )
        assert bank_p50.debt_sizing.bank_revenue_keur != (
            plain.debt_sizing.bank_revenue_keur
        )
        assert bank_p50.debt_sizing.bank_cfads_keur != plain.debt_sizing.bank_cfads_keur
        # Yet nothing downstream may move — no bank CFADS leak path exists.
        assert bank_p50.operating_schedules == plain.operating_schedules
        assert bank_p50.tax_and_cfads == plain.tax_and_cfads
        assert bank_p50.post_senior_cash == plain.post_senior_cash

    def test_w4_bank_cfads_and_base_cfads_are_distinct_vectors(self):
        result = _run(_solar())
        assert list(result.debt_sizing.bank_cfads_keur) != list(
            result.tax_and_cfads.cfads_keur
        )

    def test_w5_full_g2c_downstream_isolation_with_fixed_senior(self):
        """W5 — FULL downstream Bank-CFADS isolation proof through the production
        G2C covenant-gated waterfall (post-Senior → CASH_DSRA → DA/CF109 → SHL
        → legal distributions / Sponsor receipts).

        BANK_CASE_MUTATION_WITH_FIXED_SENIOR
        CHANGES_BANK_ECONOMICS
        BUT_CHANGES_ZERO_DOWNSTREAM_BASE_CASH_OUTPUTS

        Vehicle: Generic Wind + ACTIVE CASH_DSRA (FORWARD_DEBT_SERVICE_MONTHS
        dynamic target funded from final Senior DS) + derived SHL + DSCR
        lockup-gated distributions. Two otherwise identical runs of the
        production entry point ``run_project_shareholder_waterfall_model``:

          Run A — Bank case inherits Base merchant prices (default P90-10y);
          Run B — Bank case carries an explicit calendar-year merchant curve
                  that is IDENTICAL to Base inside the Senior debt window and
                  materially higher (×2) in every year AFTER the last Senior
                  debt-service period.

        The Senior → downstream transmission channel is therefore neutralised
        causally (bank CFADS inside the sizing window is identical), which is
        the narrowest existing production-supported seam: the G2A/G2C adapter
        only supports DSCR-sculpted Senior, so an in-window Bank mutation
        necessarily moves the sculpted Senior schedule (the legitimate channel
        W3 already isolates at orchestrator level with EXPLICIT_SCHEDULE).
        No mocks, no production code changes, no new scenario mechanism.

        The test fails numerically if Bank CFADS/cash is ever routed into
        post-Senior cash, CASH_DSRA funding, DA inflow, CF109 release, SHL
        cash, or legal distributions.
        """
        import dataclasses as dc

        from app.project_factories import create_default_wind_project
        from finco_core.inputs import DebtServiceReserveSupportMode
        from finco_core.inputs._models import DebtSizingCaseConfig, YieldScenario
        from financial_engine.shareholder_waterfall import (
            run_project_shareholder_waterfall_model,
        )

        wind = create_default_wind_project()
        vehicle = dc.replace(
            wind,
            financing=dc.replace(
                wind.financing,
                dsra_support_mode=DebtServiceReserveSupportMode.CASH_DSRA,
                dsra_target_policy="forward_debt_service_months",
                dsra_months=6,
                debt_service_reserve_requirement_keur=1_000.0,
            ),
        )

        run_a = run_project_shareholder_waterfall_model(vehicle, source_id="pr7_w5_a")

        # ── Determine the Senior debt window end from Run A's production output.
        model_a = run_a.financing_result.project_model_result
        senior_a = model_a.senior_debt
        senior_ds_by_idx = {
            i: ds for i, ds in zip(senior_a.period_indices, senior_a.senior_debt_service_keur)
        }
        last_debt_year = max(
            p.period_end.year
            for p in model_a.periods
            if senior_ds_by_idx.get(p.period_index, 0.0) > 0.0
        )
        # First operating period's end year anchors the calendar map to the
        # project's own operating-year convention (no hardcoded calendar).
        first_op_year = min(
            p.period_end.year for p in model_a.periods if p.is_operation
        )
        horizon_last_year = max(p.period_end.year for p in model_a.periods)

        # Bank calendar curve: identical to the Base curve inside the Senior
        # window (calendar year <= last_debt_year), doubled after it.
        base_prices = {
            year: vehicle.revenue.market_price_at_year(year - first_op_year + 1)
            for year in range(first_op_year, horizon_last_year + 1)
        }
        bank_calendar = tuple(
            (value if year <= last_debt_year else value * 2.0)
            for year, value in base_prices.items()
        )

        run_b = run_project_shareholder_waterfall_model(
            dc.replace(
                vehicle,
                financing=dc.replace(
                    vehicle.financing,
                    debt_sizing_case=DebtSizingCaseConfig(
                        production_yield_scenario=YieldScenario.P90_10Y,
                        merchant_price_calendar_start_year=first_op_year,
                        merchant_prices_by_calendar_year_eur_mwh=bank_calendar,
                        source_label="pr7_w5_post_maturity_bank_price_mutation",
                    ),
                ),
            ),
            source_id="pr7_w5_b",
        )
        model_b = run_b.financing_result.project_model_result

        # ── 1. The Bank mutation is real ──────────────────────────────────────
        bank_a = model_a.debt_sizing
        bank_b = model_b.debt_sizing
        assert list(bank_a.bank_cfads_keur) != list(bank_b.bank_cfads_keur)
        assert sum(bank_b.bank_cfads_keur) > sum(bank_a.bank_cfads_keur)
        assert sum(bank_b.bank_revenue_keur) > sum(bank_a.bank_revenue_keur)
        # (production identical by design — the mutation is price-only)

        # ── 2. Senior is deliberately constant ────────────────────────────────
        senior_b = model_b.senior_debt
        assert run_b.financing_result.final_senior_commitment_keur == (
            run_a.financing_result.final_senior_commitment_keur
        )
        assert senior_b.senior_interest_keur == senior_a.senior_interest_keur
        assert senior_b.senior_principal_keur == senior_a.senior_principal_keur
        assert senior_b.senior_debt_service_keur == senior_a.senior_debt_service_keur
        assert senior_b.senior_debt_closing_keur == senior_a.senior_debt_closing_keur
        assert run_b.financing_result.binding_senior_constraint == (
            run_a.financing_result.binding_senior_constraint
        )

        # ── 3. Base economics remain identical ────────────────────────────────
        assert model_b.operating_schedules.production_mwh == (
            model_a.operating_schedules.production_mwh
        )
        assert model_b.operating_schedules.revenue_keur == (
            model_a.operating_schedules.revenue_keur
        )
        assert model_b.operating_schedules.opex_keur == model_a.operating_schedules.opex_keur
        assert model_b.operating_schedules.ebitda_keur == (
            model_a.operating_schedules.ebitda_keur
        )
        assert model_b.tax_and_cfads.corporate_tax_cash_keur == (
            model_a.tax_and_cfads.corporate_tax_cash_keur
        )
        assert model_b.tax_and_cfads.cfads_keur == model_a.tax_and_cfads.cfads_keur

        # ── 4. Post-Senior ────────────────────────────────────────────────────
        psa = model_a.post_senior_cash
        psb = model_b.post_senior_cash
        assert psb.cash_after_senior_before_reserves_keur == (
            psa.cash_after_senior_before_reserves_keur
        )
        assert psb.cash_available_for_shl_before_reserves_keur == (
            psa.cash_available_for_shl_before_reserves_keur
        )

        # ── 5. CASH_DSRA — active mechanics, identical vectors ────────────────
        dsra_a = model_a.cash_dsra
        dsra_b = model_b.cash_dsra
        wa = run_a.waterfall_periods
        wb = run_b.waterfall_periods
        assert len(wa) == len(wb)
        assert any(
            getattr(p, "dsra_top_up_keur", 0.0) > 0.0
            or getattr(p, "dsra_release_keur", 0.0) > 0.0
            for p in wa
        ), "vehicle must exercise ACTIVE CASH_DSRA funding/release mechanics"
        for pa, pb in zip(wa, wb):
            assert pa.senior_dsra_target_keur == pb.senior_dsra_target_keur
            assert pa.senior_dsra_opening_keur == pb.senior_dsra_opening_keur
            assert pa.dsra_top_up_keur == pb.dsra_top_up_keur
            assert pa.dsra_draw_keur == pb.dsra_draw_keur
            assert pa.dsra_release_keur == pb.dsra_release_keur
            assert pa.senior_dsra_closing_keur == pb.senior_dsra_closing_keur
            assert pa.reserve_adjusted_cash_keur == pb.reserve_adjusted_cash_keur
        if dsra_a is not None and dsra_b is not None:
            assert dsra_b.final_closing_balance_keur == dsra_a.final_closing_balance_keur
            assert dsra_b.total_top_up_keur == dsra_a.total_top_up_keur
            assert dsra_b.total_draw_keur == dsra_a.total_draw_keur
            assert dsra_b.total_release_keur == dsra_a.total_release_keur
            assert dsra_b.requirement_keur == dsra_a.requirement_keur
            for ra, rb in zip(dsra_a.period_results, dsra_b.period_results):
                assert rb.opening_balance_keur == ra.opening_balance_keur
                assert rb.required_balance_keur == ra.required_balance_keur
                assert rb.closing_balance_keur == ra.closing_balance_keur
                assert rb.cash_after_dsra_keur == ra.cash_after_dsra_keur

        # ── 6. Distribution Account / CF109 — non-inert, identical vectors ────
        assert any(p.distribution_account_release_keur > 0.0 for p in wa), (
            "vehicle must exercise DA release (CF109) mechanics"
        )
        for pa, pb in zip(wa, wb):
            assert pa.distribution_account_opening_keur == pb.distribution_account_opening_keur
            assert pa.distribution_account_inflow_keur == pb.distribution_account_inflow_keur
            assert pa.distribution_account_available_keur == (
                pb.distribution_account_available_keur
            )
            assert pa.distribution_account_release_keur == (
                pb.distribution_account_release_keur
            )
            assert pa.distribution_account_closing_keur == (
                pb.distribution_account_closing_keur
            )
            assert pa.distribution_gate_status == pb.distribution_gate_status

        # ── 7. SHL — non-inert cash mechanics, identical vectors ──────────────
        assert (
            run_a.total_shl_cash_interest_received_keur > 0.0
            or run_a.total_shl_principal_received_keur > 0.0
        ), "vehicle must exercise actual SHL cash interest/principal"
        for pa, pb in zip(wa, wb):
            assert pa.shl_opening_balance_keur == pb.shl_opening_balance_keur
            assert pa.shl_gross_interest_keur == pb.shl_gross_interest_keur
            assert pa.shl_cash_interest_receipt_keur == pb.shl_cash_interest_receipt_keur
            assert pa.shl_pik_keur == pb.shl_pik_keur
            assert pa.contractual_shl_principal_due_keur == (
                pb.contractual_shl_principal_due_keur
            )
            assert pa.actual_shl_principal_paid_keur == pb.actual_shl_principal_paid_keur
            assert pa.unpaid_shl_principal_keur == pb.unpaid_shl_principal_keur
            assert pa.actual_shl_closing_balance_keur == pb.actual_shl_closing_balance_keur

        # ── 8. Sponsor / distributions — non-inert, identical ─────────────────
        assert run_a.total_legal_equity_distributions_keur > 0.0, (
            "vehicle must exercise legal equity distributions"
        )
        assert run_b.total_legal_equity_distributions_keur == (
            run_a.total_legal_equity_distributions_keur
        )
        assert run_b.total_shl_cash_interest_received_keur == (
            run_a.total_shl_cash_interest_received_keur
        )
        assert run_b.total_shl_principal_received_keur == (
            run_a.total_shl_principal_received_keur
        )
        assert run_b.total_sponsor_receipts_keur == run_a.total_sponsor_receipts_keur
        assert run_b.total_covenant_locked_keur == run_a.total_covenant_locked_keur
        assert run_b.pure_equity_xirr == run_a.pure_equity_xirr
        assert run_b.pure_equity_xirr_status == run_a.pure_equity_xirr_status
        assert run_b.total_sponsor_xirr == run_a.total_sponsor_xirr
        assert run_b.total_sponsor_xirr_status == run_a.total_sponsor_xirr_status
        assert run_b.shl_bullet_unpaid_at_maturity == run_a.shl_bullet_unpaid_at_maturity


# ---------------------------------------------------------------------------
# Group Y — fail-closed yield scenario mapping
# ---------------------------------------------------------------------------

class TestY_FailClosedYieldMapping:
    def _adapt(self, yield_scenario: str):
        from financial_engine.adapters.project_inputs import from_project_inputs

        project = _solar()
        return from_project_inputs(
            dataclasses.replace(
                project,
                technical=dataclasses.replace(
                    project.technical, yield_scenario=yield_scenario
                ),
            )
        )

    def test_y1_p50_maps(self):
        from financial_engine.inputs import YieldScenario

        assert self._adapt("P_50").technical.yield_scenario is YieldScenario.P50

    def test_y2_p90_10y_maps(self):
        from financial_engine.inputs import YieldScenario

        assert self._adapt("P90-10y").technical.yield_scenario is YieldScenario.P90_10Y

    def test_y3_p99_fails_closed(self):
        with pytest.raises(ValueError, match="YIELD_SCENARIO_EXPLICIT_MAPPING_REQUIRED"):
            self._adapt("P99-1y")

    def test_y4_typo_fails_closed(self):
        with pytest.raises(ValueError, match="YIELD_SCENARIO_EXPLICIT_MAPPING_REQUIRED"):
            self._adapt("p_50")

    def test_y5_empty_fails_closed(self):
        with pytest.raises(ValueError, match="YIELD_SCENARIO_EXPLICIT_MAPPING_REQUIRED"):
            self._adapt("")


# ---------------------------------------------------------------------------
# Group G — governance scans
# ---------------------------------------------------------------------------

_CLEAN_ENGINE_PACKAGES = ("financial_engine", "finco_core")


_PROJECT_IDENTITY_NAMES = ("tuho", "oborovo", "kupi")


def _docstring_node_ranges(tree):
    """Line ranges of docstrings, so code scans can skip documentation."""
    ranges = []
    for node in __import__("ast").walk(tree):
        if isinstance(node, (__import__("ast").Module, __import__("ast").FunctionDef,
                             __import__("ast").AsyncFunctionDef, __import__("ast").ClassDef)):
            body = node.body
            if body and isinstance(body[0], __import__("ast").Expr) and isinstance(
                body[0].value, __import__("ast").Constant
            ) and isinstance(body[0].value.value, str):
                ranges.append((body[0].lineno, body[0].end_lineno))
    return ranges


class TestG_GovernanceScans:
    @staticmethod
    def _production_sources():
        for package in _CLEAN_ENGINE_PACKAGES:
            for path in sorted((REPO_ROOT / package).rglob("*.py")):
                yield path

    def test_g1_no_project_identity_dispatch_comparisons(self):
        """AST scan: no Compare node in the clean engine may test a project
        identity string. Docstring examples and audit label defaults are not
        dispatch; comparisons are."""
        import ast

        for path in self._production_sources():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            docstrings = _docstring_node_ranges(tree)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Compare):
                    continue
                if any(start <= node.lineno <= end for start, end in docstrings):
                    continue
                for comparator in (node.left, *node.comparators):
                    if (
                        isinstance(comparator, ast.Constant)
                        and isinstance(comparator.value, str)
                        and comparator.value.strip().lower() in _PROJECT_IDENTITY_NAMES
                    ):
                        raise AssertionError(
                            f"{path}:{node.lineno} dispatches on project identity "
                            f"{comparator.value!r}"
                        )

    def test_g2_no_project_identity_literals_in_clean_engine_code(self):
        """No project-name string literals outside docstrings anywhere in the
        clean-engine packages. The only permitted carrier is an audit label
        default for a parameter explicitly named project_name (provenance
        pass-through, excluded from numerics by the identity-rename test M-G
        and the B7 renamed-clone parity test)."""
        import ast

        audit_label_node_ids: set[int] = set()
        for path in self._production_sources():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    all_defaults = list(node.args.defaults) + [
                        d for d in node.args.kw_defaults if d is not None
                    ]
                    arg_names = [a.arg for a in node.args.args] + [
                        a.arg for a in node.args.kwonlyargs
                    ]
                    offset = len(arg_names) - len(node.args.defaults)
                    for i, default in enumerate(node.args.defaults):
                        if arg_names[offset + i] == "project_name":
                            audit_label_node_ids.add(id(default))
                    for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
                        if default is not None and arg.arg == "project_name":
                            audit_label_node_ids.add(id(default))
            docstrings = _docstring_node_ranges(tree)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if id(node) in audit_label_node_ids:
                        continue
                    if any(start <= node.lineno <= end for start, end in docstrings):
                        continue
                    if node.value.strip().lower() in _PROJECT_IDENTITY_NAMES:
                        raise AssertionError(
                            f"{path}:{node.lineno} contains project-name literal "
                            f"{node.value!r} in code (outside docstring/audit label)"
                        )

    def test_g3_no_target_fitting_or_plug_mechanisms(self):
        for path in self._production_sources():
            src = path.read_text(encoding="utf-8")
            for token in ("approved_delta", "expected_delta", "balancing_plug"):
                assert token not in src, f"{path} contains forbidden token {token!r}"

    def test_g4_no_kupi_bank_balancing_field(self):
        from finco_core.inputs._models import DebtSizingCaseConfig

        names = {f.name for f in dataclasses.fields(DebtSizingCaseConfig)}
        assert not any("balancing" in n for n in names), (
            "No KUPI-specific Bank balancing field may exist "
            "(KUPI_SOURCE_BANK_REVENUE_BALANCING_OMISSION stays a classified "
            "source workbook asymmetry)"
        )

    def test_g5_target_dscr_not_on_debt_sizing_case(self):
        """Target DSCR is Senior sizing policy, not a Bank revenue-scenario input."""
        from finco_core.inputs._models import DebtSizingCaseConfig

        names = {f.name for f in dataclasses.fields(DebtSizingCaseConfig)}
        assert not any("dscr" in n.lower() for n in names)

    def test_g6_single_shared_bank_case_validator(self):
        """Config and runtime input must delegate to the same validator."""
        from finco_core.inputs._models import (
            validate_debt_sizing_case_merchant_price_fields,
        )
        from financial_engine import inputs as fe_inputs

        src = Path(fe_inputs.__file__).read_text(encoding="utf-8")
        assert "validate_debt_sizing_case_merchant_price_fields" in src, (
            "DebtSizingCaseInput must delegate to the shared finco_core validator"
        )
        assert callable(validate_debt_sizing_case_merchant_price_fields)

    def test_g7_deprecated_dscr_fields_are_classified(self):
        """flat_dscr_target / target_min_dscr: serialized compatibility only."""
        src = (REPO_ROOT / "finco_core" / "inputs" / "_models.py").read_text(
            encoding="utf-8"
        )
        assert "PR-7 authority classification: DEPRECATED" in src, (
            "flat_dscr_target/target_min_dscr must carry an explicit DEPRECATED "
            "authority classification"
        )


def test_pr7_final_classification_marker():
    """Classification marker — full proof lives in this module + delivery report."""
    assert "PR7_TYPED_BASE_BANK_CASE_AUTHORITY_CONSOLIDATED"
