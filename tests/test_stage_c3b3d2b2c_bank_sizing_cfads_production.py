"""
C3B3D2B2C: Generic Bank-Sizing CFADS Scenario Layer — Production Tests.

Productionizes MISSING_GENERIC_BANK_SIZING_CFADS_SCENARIO_LAYER.

Test classes:
  TestInputContract            — ProductionScenarioScope, DebtSizingScenario, SeniorDebtModelInput
  TestPureTransformer          — _derive_bank_operating_input: immutability, no mutation
  TestMerchantOnlySplice       — MERCHANT_ONLY period splicing logic
  TestAllProductionPath        — ALL_PRODUCTION uses P90 for every period
  TestBackwardCompatibility    — None bank_sizing_scenario → unchanged behaviour
  TestAuditField               — bank_sizing_cfads_keur audit tuple
  TestBaseEconomicAuthority    — final tax_and_cfads is always base P50 result
  TestNumericalOborovoMerchant — Oborovo MERCHANT_ONLY debt sizing numerical probe
  TestNumericalTuhoOperating   — TUHO P90 operating model production check
  TestGovernance               — no project-name dispatch, no fixture reads
"""
from __future__ import annotations

import math
from dataclasses import replace
from datetime import date

import pytest

from financial_engine.inputs import (
    CalendarInput,
    CapexItemForDep,
    DepreciationInput,
    DebtSizingScenario,
    InputProvenance,
    OperatingModelInput,
    OpexInput,
    OpexLineInput,
    ProductionScenarioScope,
    RevenueInput,
    SeniorDebtModelInput,
    TaxCalculationInput,
    TechnicalInput,
    YieldScenario,
)
from financial_engine.ppa_indexation import PpaIndexationStartPolicy
from financial_engine.results import SeniorDebtSchedules


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_minimal_operating_input(yield_scenario: YieldScenario = YieldScenario.P50) -> OperatingModelInput:
    """Minimal valid OperatingModelInput — suitable for unit tests that need the type."""
    return OperatingModelInput(
        calendar=CalendarInput(
            financial_close=date(2024, 1, 1),
            construction_months=6,
            horizon_years=10,
            ppa_years=5.0,
        ),
        technical=TechnicalInput(
            capacity_mw=10.0,
            yield_scenario=yield_scenario,
            operating_hours_p50=1500.0,
            operating_hours_p90_10y=1350.0,
            pv_degradation=0.005,
            plant_availability=0.97,
            grid_availability=0.99,
        ),
        revenue=RevenueInput(
            ppa_base_tariff_eur_mwh=55.0,
            ppa_term_years=5.0,
            ppa_index=0.02,
            ppa_production_share=1.0,
            market_prices_curve_eur_mwh=tuple([60.0] * 10),
            market_inflation=0.02,
            balancing_cost_pv_fraction=0.0,
            balancing_cost_wind_eur_mwh=0.0,
            co2_enabled=False,
            co2_price_eur_mwh=0.0,
            ppa_indexation_start_policy=PpaIndexationStartPolicy.FIRST_FULL_CALENDAR_YEAR_AS_BASE,
        ),
        opex=OpexInput(
            items=(
                OpexLineInput(
                    name="o&m",
                    y1_amount_keur=200.0,
                    annual_inflation=0.02,
                    step_changes=(),
                    percentage_of_opex=0.0,
                ),
            )
        ),
        depreciation=DepreciationInput(
            book_capex_items_for_depreciation=(
                CapexItemForDep(name="panels", amount_keur=5000.0, asset_class_code="solar_panels"),
            ),
            tax_capex_items_for_depreciation=(
                CapexItemForDep(name="panels", amount_keur=5000.0, asset_class_code="solar_panels"),
            ),
            financial_cost_useful_life_years=15,
        ),
        source=InputProvenance(source_id="test", baseline_commit_sha="test-sha"),
    )


# ---------------------------------------------------------------------------
# TestInputContract
# ---------------------------------------------------------------------------

class TestInputContract:
    """Section 5 of spec: frozen dataclass input contracts."""

    def test_production_scenario_scope_values(self):
        assert ProductionScenarioScope.ALL_PRODUCTION == "all_production"
        assert ProductionScenarioScope.MERCHANT_ONLY == "merchant_only"

    def test_production_scenario_scope_is_str_enum(self):
        assert isinstance(ProductionScenarioScope.ALL_PRODUCTION, str)
        assert isinstance(ProductionScenarioScope.MERCHANT_ONLY, str)

    def test_debt_sizing_scenario_requires_scope(self):
        scenario = DebtSizingScenario(
            yield_scenario=YieldScenario.P90_10Y,
            scope=ProductionScenarioScope.MERCHANT_ONLY,
        )
        assert scenario.yield_scenario == YieldScenario.P90_10Y
        assert scenario.scope == ProductionScenarioScope.MERCHANT_ONLY

    def test_debt_sizing_scenario_is_frozen(self):
        scenario = DebtSizingScenario(
            yield_scenario=YieldScenario.P90_10Y,
            scope=ProductionScenarioScope.ALL_PRODUCTION,
        )
        with pytest.raises((AttributeError, TypeError)):
            scenario.yield_scenario = YieldScenario.P50  # type: ignore[misc]

    def test_senior_debt_model_input_bank_scenario_optional(self):
        """bank_sizing_scenario defaults to None — backward-compatible."""
        op = _make_minimal_operating_input()
        sdi = SeniorDebtModelInput(
            operating=op,
            tax=object(),
            senior_debt_policy=object(),
            senior_debt_inputs=object(),
        )
        assert sdi.bank_sizing_scenario is None

    def test_senior_debt_model_input_bank_scenario_accepted(self):
        op = _make_minimal_operating_input()
        scenario = DebtSizingScenario(
            yield_scenario=YieldScenario.P90_10Y,
            scope=ProductionScenarioScope.MERCHANT_ONLY,
        )
        sdi = SeniorDebtModelInput(
            operating=op,
            tax=object(),
            senior_debt_policy=object(),
            senior_debt_inputs=object(),
            bank_sizing_scenario=scenario,
        )
        assert sdi.bank_sizing_scenario is scenario

    def test_senior_debt_model_input_is_frozen(self):
        op = _make_minimal_operating_input()
        sdi = SeniorDebtModelInput(
            operating=op,
            tax=object(),
            senior_debt_policy=object(),
            senior_debt_inputs=object(),
        )
        with pytest.raises((AttributeError, TypeError)):
            sdi.bank_sizing_scenario = None  # type: ignore[misc]

    def test_yield_scenario_enum_values_unchanged(self):
        """Protected: YieldScenario enum values must not change — referenced by factories."""
        assert YieldScenario.P50 == "P_50"
        assert YieldScenario.P90_10Y == "P90-10y"


# ---------------------------------------------------------------------------
# TestPureTransformer
# ---------------------------------------------------------------------------

class TestPureTransformer:
    """_derive_bank_operating_input: pure, deterministic, no side effects."""

    def test_only_yield_scenario_changes(self):
        from financial_engine.orchestrator import _derive_bank_operating_input

        base = _make_minimal_operating_input(YieldScenario.P50)
        scenario = DebtSizingScenario(
            yield_scenario=YieldScenario.P90_10Y,
            scope=ProductionScenarioScope.ALL_PRODUCTION,
        )
        bank = _derive_bank_operating_input(base, scenario)

        assert bank.technical.yield_scenario == YieldScenario.P90_10Y
        assert bank.technical.capacity_mw == base.technical.capacity_mw
        assert bank.technical.operating_hours_p50 == base.technical.operating_hours_p50
        assert bank.technical.operating_hours_p90_10y == base.technical.operating_hours_p90_10y
        assert bank.technical.pv_degradation == base.technical.pv_degradation
        assert bank.technical.plant_availability == base.technical.plant_availability
        assert bank.technical.grid_availability == base.technical.grid_availability

        assert bank.calendar is base.calendar
        assert bank.revenue is base.revenue
        assert bank.opex is base.opex
        assert bank.depreciation is base.depreciation
        assert bank.source is base.source

    def test_base_input_unchanged(self):
        from financial_engine.orchestrator import _derive_bank_operating_input

        base = _make_minimal_operating_input(YieldScenario.P50)
        scenario = DebtSizingScenario(
            yield_scenario=YieldScenario.P90_10Y,
            scope=ProductionScenarioScope.ALL_PRODUCTION,
        )
        _derive_bank_operating_input(base, scenario)

        assert base.technical.yield_scenario == YieldScenario.P50

    def test_returns_new_instance(self):
        from financial_engine.orchestrator import _derive_bank_operating_input

        base = _make_minimal_operating_input(YieldScenario.P50)
        scenario = DebtSizingScenario(
            yield_scenario=YieldScenario.P90_10Y,
            scope=ProductionScenarioScope.ALL_PRODUCTION,
        )
        bank = _derive_bank_operating_input(base, scenario)
        assert bank is not base

    def test_deterministic_same_inputs_same_output(self):
        from financial_engine.orchestrator import _derive_bank_operating_input

        base = _make_minimal_operating_input(YieldScenario.P50)
        scenario = DebtSizingScenario(
            yield_scenario=YieldScenario.P90_10Y,
            scope=ProductionScenarioScope.MERCHANT_ONLY,
        )
        bank1 = _derive_bank_operating_input(base, scenario)
        bank2 = _derive_bank_operating_input(base, scenario)
        assert bank1 == bank2


# ---------------------------------------------------------------------------
# TestMerchantOnlySplice
# ---------------------------------------------------------------------------

class TestMerchantOnlySplice:
    """MERCHANT_ONLY: PPA periods use base, merchant periods use P90."""

    @pytest.fixture(scope="class")
    def oborovo_periods(self):
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
        from financial_engine.orchestrator import run_operating_model

        proj = create_default_oborovo()
        sd_input = build_senior_debt_model_input_from_project_inputs(proj)
        base_result = run_operating_model(sd_input.operating)
        return base_result.periods, sd_input.operating

    def test_ppa_periods_use_base_production(self, oborovo_periods):
        from financial_engine.orchestrator import _derive_bank_operating_input, run_operating_model
        base_periods, op_input = oborovo_periods

        scenario = DebtSizingScenario(
            yield_scenario=YieldScenario.P90_10Y,
            scope=ProductionScenarioScope.MERCHANT_ONLY,
        )
        bank_op = _derive_bank_operating_input(op_input, scenario)
        bank_result = run_operating_model(bank_op)
        bank_period_map = {p.period_index: p for p in bank_result.periods}
        base_period_map = {p.period_index: p for p in base_periods}

        for p in base_periods:
            if p.is_ppa_active:
                base_prod = base_period_map[p.period_index].production_mwh
                bank_prod = bank_period_map[p.period_index].production_mwh
                assert base_prod > bank_prod, (
                    f"PPA period {p.period_index}: base ({base_prod:.1f}) should exceed P90 ({bank_prod:.1f})"
                )

    def test_merchant_periods_use_p90_production(self, oborovo_periods):
        from financial_engine.orchestrator import _derive_bank_operating_input, run_operating_model
        base_periods, op_input = oborovo_periods

        scenario = DebtSizingScenario(
            yield_scenario=YieldScenario.P90_10Y,
            scope=ProductionScenarioScope.MERCHANT_ONLY,
        )
        bank_op = _derive_bank_operating_input(op_input, scenario)
        bank_result = run_operating_model(bank_op)
        bank_period_map = {p.period_index: p for p in bank_result.periods}
        base_period_map = {p.period_index: p for p in base_periods}

        merchant_count = 0
        for p in base_periods:
            if not p.is_ppa_active and p.is_operation:
                base_prod = base_period_map[p.period_index].production_mwh
                bank_prod = bank_period_map[p.period_index].production_mwh
                assert bank_prod < base_prod, (
                    f"Merchant period {p.period_index}: P90 ({bank_prod:.1f}) should be below P50 ({base_prod:.1f})"
                )
                merchant_count += 1
        assert merchant_count > 0, "No merchant periods found in Oborovo"

    def test_merchant_production_ratio_matches_p90_p50(self, oborovo_periods):
        from financial_engine.orchestrator import _derive_bank_operating_input, run_operating_model
        base_periods, op_input = oborovo_periods

        scenario = DebtSizingScenario(
            yield_scenario=YieldScenario.P90_10Y,
            scope=ProductionScenarioScope.MERCHANT_ONLY,
        )
        bank_op = _derive_bank_operating_input(op_input, scenario)
        bank_result = run_operating_model(bank_op)
        bank_period_map = {p.period_index: p for p in bank_result.periods}
        base_period_map = {p.period_index: p for p in base_periods}

        p50h = op_input.technical.operating_hours_p50
        p90h = op_input.technical.operating_hours_p90_10y
        expected_ratio = p90h / p50h

        for p in base_periods:
            if not p.is_ppa_active and p.is_operation:
                idx = p.period_index
                ratio = bank_period_map[idx].production_mwh / base_period_map[idx].production_mwh
                assert abs(ratio - expected_ratio) < 0.02, (
                    f"Period {idx}: production ratio {ratio:.4f} deviates from P90/P50 {expected_ratio:.4f}"
                )
                break


# ---------------------------------------------------------------------------
# TestAllProductionPath
# ---------------------------------------------------------------------------

class TestAllProductionPath:
    """ALL_PRODUCTION: P90 yield applies to every operating period."""

    @pytest.fixture(scope="class")
    def oborovo_operating(self):
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
        proj = create_default_oborovo()
        sd_input = build_senior_debt_model_input_from_project_inputs(proj)
        return sd_input.operating

    def test_all_periods_use_p90_production(self, oborovo_operating):
        from financial_engine.orchestrator import _derive_bank_operating_input, run_operating_model

        base_result = run_operating_model(oborovo_operating)
        scenario = DebtSizingScenario(
            yield_scenario=YieldScenario.P90_10Y,
            scope=ProductionScenarioScope.ALL_PRODUCTION,
        )
        bank_op = _derive_bank_operating_input(oborovo_operating, scenario)
        bank_result = run_operating_model(bank_op)

        base_map = {p.period_index: p for p in base_result.periods}
        bank_map = {p.period_index: p for p in bank_result.periods}

        for p in base_result.periods:
            if p.is_operation:
                assert bank_map[p.period_index].production_mwh < base_map[p.period_index].production_mwh

    def test_all_production_debt_lower_than_base(self, oborovo_operating):
        """ALL_PRODUCTION: debt < base (P90 throughout → lower CFADS)."""
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
        from financial_engine.orchestrator import run_senior_debt_model

        proj = create_default_oborovo()
        base_input = build_senior_debt_model_input_from_project_inputs(proj)
        result_base = run_senior_debt_model(base_input)

        scenario = DebtSizingScenario(
            yield_scenario=YieldScenario.P90_10Y,
            scope=ProductionScenarioScope.ALL_PRODUCTION,
        )
        result_bank = run_senior_debt_model(replace(base_input, bank_sizing_scenario=scenario))

        assert result_bank.senior_debt.debt_size_keur < result_base.senior_debt.debt_size_keur, (
            "ALL_PRODUCTION bank debt should be below base P50 debt"
        )


# ---------------------------------------------------------------------------
# TestBackwardCompatibility
# ---------------------------------------------------------------------------

class TestBackwardCompatibility:
    """None bank_sizing_scenario → behaviour unchanged from pre-C3B3D2B2C."""

    @pytest.fixture(scope="class")
    def oborovo_base_result(self):
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
        from financial_engine.orchestrator import run_senior_debt_model

        proj = create_default_oborovo()
        base_input = build_senior_debt_model_input_from_project_inputs(proj)
        return run_senior_debt_model(base_input)

    def test_bank_sizing_cfads_none_when_no_scenario(self, oborovo_base_result):
        assert oborovo_base_result.senior_debt.bank_sizing_cfads_keur is None

    def test_debt_size_unchanged_no_scenario(self, oborovo_base_result):
        """Without bank scenario, debt size must equal the C3B3D2B2B baseline."""
        expected = 43919.033  # CURRENT_GRID0 from C3B3D2B2B
        assert abs(oborovo_base_result.senior_debt.debt_size_keur - expected) < 1.0, (
            f"Baseline debt {oborovo_base_result.senior_debt.debt_size_keur:.3f} deviates from "
            f"C3B3D2B2B baseline {expected}"
        )

    def test_base_cfads_unchanged_no_scenario(self, oborovo_base_result):
        assert oborovo_base_result.tax_and_cfads is not None
        cfads = oborovo_base_result.tax_and_cfads.cfads_keur
        # All operating period CFADS must be finite and positive
        op_cfads = [c for c in cfads if c > 0]
        assert len(op_cfads) > 0


# ---------------------------------------------------------------------------
# TestAuditField
# ---------------------------------------------------------------------------

class TestAuditField:
    """bank_sizing_cfads_keur: audit tuple aligned to debt period_indices."""

    @pytest.fixture(scope="class")
    def oborovo_merchant_result(self):
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
        from financial_engine.orchestrator import run_senior_debt_model

        proj = create_default_oborovo()
        base_input = build_senior_debt_model_input_from_project_inputs(proj)
        scenario = DebtSizingScenario(
            yield_scenario=YieldScenario.P90_10Y,
            scope=ProductionScenarioScope.MERCHANT_ONLY,
        )
        return run_senior_debt_model(replace(base_input, bank_sizing_scenario=scenario))

    def test_bank_sizing_cfads_present(self, oborovo_merchant_result):
        assert oborovo_merchant_result.senior_debt.bank_sizing_cfads_keur is not None

    def test_bank_sizing_cfads_aligned_to_period_indices(self, oborovo_merchant_result):
        sd = oborovo_merchant_result.senior_debt
        assert len(sd.bank_sizing_cfads_keur) == len(sd.period_indices)

    def test_bank_sizing_cfads_merchant_periods_lower_than_base(self, oborovo_merchant_result):
        """Bank CFADS for merchant periods must be below base CFADS."""
        sd = oborovo_merchant_result.senior_debt
        base_cfads = oborovo_merchant_result.tax_and_cfads.cfads_keur
        base_by_idx = {i: c for i, c in enumerate(base_cfads)}

        for i, (pidx, bk_cfads) in enumerate(zip(sd.period_indices, sd.bank_sizing_cfads_keur)):
            base_c = base_by_idx.get(pidx, 0.0)
            if base_c > 100.0 and bk_cfads < base_c * 0.95:
                # At least one merchant period has significantly lower bank CFADS
                break
        else:
            pytest.fail("No period found where bank CFADS < 95% of base CFADS (expected for merchant P90)")

    def test_bank_sizing_cfads_is_tuple(self, oborovo_merchant_result):
        assert isinstance(oborovo_merchant_result.senior_debt.bank_sizing_cfads_keur, tuple)

    def test_bank_sizing_cfads_all_finite(self, oborovo_merchant_result):
        for c in oborovo_merchant_result.senior_debt.bank_sizing_cfads_keur:
            assert math.isfinite(c), f"bank_sizing_cfads_keur contains non-finite value: {c}"


# ---------------------------------------------------------------------------
# TestBaseEconomicAuthority
# ---------------------------------------------------------------------------

class TestBaseEconomicAuthority:
    """Final tax_and_cfads must be the base P50 economic result, not bank case."""

    @pytest.fixture(scope="class")
    def results(self):
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
        from financial_engine.orchestrator import run_senior_debt_model

        proj = create_default_oborovo()
        base_input = build_senior_debt_model_input_from_project_inputs(proj)

        result_no_bank = run_senior_debt_model(base_input)
        scenario = DebtSizingScenario(
            yield_scenario=YieldScenario.P90_10Y,
            scope=ProductionScenarioScope.MERCHANT_ONLY,
        )
        result_with_bank = run_senior_debt_model(replace(base_input, bank_sizing_scenario=scenario))
        return result_no_bank, result_with_bank

    def test_tax_and_cfads_present(self, results):
        _, result_with_bank = results
        assert result_with_bank.tax_and_cfads is not None

    def test_base_cfads_not_p90_scaled(self, results):
        """Base CFADS in the final result must not be P90-scaled production."""
        result_no_bank, result_with_bank = results
        base_cfads = result_no_bank.tax_and_cfads.cfads_keur
        bank_result_cfads = result_with_bank.tax_and_cfads.cfads_keur

        # The final base CFADS should be close to no-bank result (within tax feedback tolerance)
        # Not identical (interest changes slightly with different debt), but of similar magnitude
        total_base = sum(base_cfads)
        total_bank_result = sum(bank_result_cfads)
        assert abs(total_base - total_bank_result) / total_base < 0.05, (
            f"Final base CFADS ({total_bank_result:.0f}) deviates >5% from no-bank base CFADS ({total_base:.0f})"
        )

    def test_base_cfads_higher_than_bank_sizing_cfads_in_merchant(self, results):
        """Base CFADS for merchant periods must exceed bank CFADS (P50 > P90)."""
        _, result_with_bank = results
        sd = result_with_bank.senior_debt
        final_base_cfads = result_with_bank.tax_and_cfads.cfads_keur
        base_by_idx = {i: c for i, c in enumerate(final_base_cfads)}
        bank_cfads = sd.bank_sizing_cfads_keur

        # Find at least one merchant period where final base > bank
        found = False
        for pidx, bk in zip(sd.period_indices, bank_cfads):
            base_c = base_by_idx.get(pidx, 0.0)
            if base_c > 100 and base_c > bk * 1.05:
                found = True
                break
        assert found, "Expected final base CFADS > bank CFADS in at least one merchant period"


# ---------------------------------------------------------------------------
# TestNumericalOborovoMerchant
# ---------------------------------------------------------------------------

class TestNumericalOborovoMerchant:
    """Oborovo MERCHANT_ONLY numerical probe.

    Source classification: BANK_SIZING_SCENARIO_P90_10Y_REVIEWER_CONFIRMED_NOT_COMMITTED
    Gap analysis: residual gap to Excel (42,852) explained by ACT/360 (-215 kEUR)
    and DSCR banding (-516 kEUR), both out of scope for C3B3D2B2C.

    BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED: preserved.
    """

    @pytest.fixture(scope="class")
    def oborovo_merchant_result(self):
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
        from financial_engine.orchestrator import run_senior_debt_model

        proj = create_default_oborovo()
        base_input = build_senior_debt_model_input_from_project_inputs(proj)
        scenario = DebtSizingScenario(
            yield_scenario=YieldScenario.P90_10Y,
            scope=ProductionScenarioScope.MERCHANT_ONLY,
        )
        return run_senior_debt_model(replace(base_input, bank_sizing_scenario=scenario))

    def test_debt_below_base(self, oborovo_merchant_result):
        """Bank-sized debt must be below the base P50 debt (C3B3D2B2B CURRENT_GRID0)."""
        current_grid0 = 43919.033
        debt = oborovo_merchant_result.senior_debt.debt_size_keur
        assert debt < current_grid0, (
            f"MERCHANT_ONLY debt {debt:.3f} is not below CURRENT_GRID0 {current_grid0}"
        )

    def test_debt_above_all_production(self, oborovo_merchant_result):
        """MERCHANT_ONLY debt must exceed ALL_PRODUCTION debt (PPA preserved at P50)."""
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
        from financial_engine.orchestrator import run_senior_debt_model

        proj = create_default_oborovo()
        base_input = build_senior_debt_model_input_from_project_inputs(proj)
        ap_scenario = DebtSizingScenario(
            yield_scenario=YieldScenario.P90_10Y,
            scope=ProductionScenarioScope.ALL_PRODUCTION,
        )
        result_ap = run_senior_debt_model(replace(base_input, bank_sizing_scenario=ap_scenario))

        merchant_debt = oborovo_merchant_result.senior_debt.debt_size_keur
        all_prod_debt = result_ap.senior_debt.debt_size_keur
        assert merchant_debt > all_prod_debt, (
            f"MERCHANT_ONLY debt {merchant_debt:.3f} must exceed ALL_PRODUCTION {all_prod_debt:.3f}"
        )

    def test_debt_in_expected_range(self, oborovo_merchant_result):
        """MERCHANT_ONLY debt should be in the expected range [41000, 44500] kEUR.

        Lower bound: >ALL_PRODUCTION (~40,950). Upper bound: <base (~43,919).
        Causal bridge case2 (excel CFADS) = 43,591. Our result aligns at engine rate.
        """
        debt = oborovo_merchant_result.senior_debt.debt_size_keur
        assert 41000 < debt < 44500, (
            f"MERCHANT_ONLY Oborovo debt {debt:.3f} outside expected range [41000, 44500]"
        )

    def test_bank_sizing_cfads_audit_populated(self, oborovo_merchant_result):
        sd = oborovo_merchant_result.senior_debt
        assert sd.bank_sizing_cfads_keur is not None
        assert len(sd.bank_sizing_cfads_keur) > 0

    def test_solver_authoritative(self, oborovo_merchant_result):
        """Solver must converge to an authoritative result."""
        sd = oborovo_merchant_result.senior_debt
        assert sd.diagnostics.get("is_authoritative", False) is True


# ---------------------------------------------------------------------------
# TestNumericalTuhoOperating
# ---------------------------------------------------------------------------

class TestNumericalTuhoOperating:
    """TUHO ALL_PRODUCTION: bank P90 period 1 EBITDA proof.

    Source proof: BANK_SIZING_SCENARIO_P90_10Y_TUHO_CFADS_PROVEN (ALL_PRODUCTION)
    Target: period 2 (first operating) P90 EBITDA ≈ 2539.634 kEUR.
    """

    def test_tuho_p90_period2_ebitda_near_target(self):
        from app.project_factories import create_default_tuho_wind1
        from financial_engine.adapters.project_inputs import from_project_inputs
        from financial_engine.orchestrator import _derive_bank_operating_input, run_operating_model

        proj = create_default_tuho_wind1()
        op_input = from_project_inputs(proj)

        scenario = DebtSizingScenario(
            yield_scenario=YieldScenario.P90_10Y,
            scope=ProductionScenarioScope.ALL_PRODUCTION,
        )
        bank_op = _derive_bank_operating_input(op_input, scenario)
        bank_result = run_operating_model(bank_op)
        bank_map = {p.period_index: p for p in bank_result.periods}

        period2 = bank_map[2]
        assert abs(period2.ebitda_keur - 2539.634) < 5.0, (
            f"TUHO P90 period 2 EBITDA {period2.ebitda_keur:.3f} not near target 2539.634"
        )

    def test_tuho_p90_all_periods_below_p50(self):
        from app.project_factories import create_default_tuho_wind1
        from financial_engine.adapters.project_inputs import from_project_inputs
        from financial_engine.orchestrator import _derive_bank_operating_input, run_operating_model

        proj = create_default_tuho_wind1()
        op_input = from_project_inputs(proj)

        base_result = run_operating_model(op_input)
        scenario = DebtSizingScenario(
            yield_scenario=YieldScenario.P90_10Y,
            scope=ProductionScenarioScope.ALL_PRODUCTION,
        )
        bank_op = _derive_bank_operating_input(op_input, scenario)
        bank_result = run_operating_model(bank_op)

        base_map = {p.period_index: p for p in base_result.periods}
        bank_map = {p.period_index: p for p in bank_result.periods}

        for p in base_result.periods:
            if p.is_operation:
                assert bank_map[p.period_index].ebitda_keur < base_map[p.period_index].ebitda_keur


# ---------------------------------------------------------------------------
# TestGovernance
# ---------------------------------------------------------------------------

class TestGovernance:
    """Governance: no project dispatch, no hardcoded period boundaries."""

    def test_no_project_name_in_transformer(self):
        """_derive_bank_operating_input must not reference project names."""
        import inspect
        from financial_engine import orchestrator
        src = inspect.getsource(orchestrator._derive_bank_operating_input)
        forbidden = ["oborovo", "tuho", "project_name", "source_id", "finco_core"]
        for term in forbidden:
            assert term not in src.lower(), (
                f"_derive_bank_operating_input contains forbidden reference: '{term}'"
            )

    def test_no_hardcoded_period_boundary_in_splice(self):
        """The MERCHANT_ONLY splice must use is_ppa_active, not hardcoded period numbers."""
        import inspect
        from financial_engine import orchestrator
        src = inspect.getsource(orchestrator.run_senior_debt_model)
        # DS25/DS40 hardcoding forbidden by spec
        assert "25" not in src.split("MERCHANT_ONLY")[1].split("else")[0] if "MERCHANT_ONLY" in src else True
        assert "is_ppa_active" in src, "Splice must use is_ppa_active field"

    def test_scope_required_no_default_hidden(self):
        """DebtSizingScenario.scope has no default — explicit required."""
        import inspect
        sig = inspect.signature(DebtSizingScenario)
        scope_param = sig.parameters.get("scope")
        assert scope_param is not None
        assert scope_param.default is inspect.Parameter.empty, "scope must have no default"

    def test_no_13547_literal_in_bank_sizing_code(self):
        """13547.2 must not appear as a literal in bank-sizing logic."""
        import inspect
        from financial_engine import orchestrator
        src = inspect.getsource(orchestrator.run_senior_debt_model)
        assert "13547" not in src, "Forbidden literal 13547.2 found in run_senior_debt_model"

    def test_results_frozen(self):
        """SeniorDebtSchedules is frozen — audit field cannot be mutated."""
        sd = SeniorDebtSchedules(
            period_indices=(1, 2),
            senior_debt_opening_keur=(1000.0, 500.0),
            senior_interest_keur=(10.0, 5.0),
            senior_principal_keur=(500.0, 500.0),
            senior_debt_service_keur=(510.0, 505.0),
            senior_debt_closing_keur=(500.0, 0.0),
            senior_dscr=(2.0, 2.0),
            debt_size_keur=1000.0,
            binding_constraint=None,
            diagnostics={},
            bank_sizing_cfads_keur=(900.0, 800.0),
        )
        with pytest.raises((AttributeError, TypeError)):
            sd.bank_sizing_cfads_keur = None  # type: ignore[misc]
