"""
financial_engine.orchestrator — Clean Phase 2A operating-core orchestrator.

Exposes one primary API:

    result = run_operating_model(inputs)

Required sequence:
  1. Validate input — refuse if ERROR issues exist.
  2. Build period grid via PeriodEngine.
  3. Calculate production (reuses finco_core.revenue.generation leaf).
  4. Calculate revenue (reuses finco_core.revenue.generation leaf).
  5. Calculate OPEX (reuses finco_core.opex.projections leaf).
  6. Calculate EBITDA = revenue - OPEX (assembled here).
  7. Calculate book/tax depreciation (reuses finco_core.depreciation.engine leaf).
  8. Assemble immutable result.
  9. Attach immutable provenance.

The clean engine does NOT call:
  run_waterfall, run_waterfall_v3_core, WaterfallRunner, WaterfallRunConfig,
  run_service, run_project, or any legacy engine path.

The clean engine is unaware that the legacy engine exists.
"""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from financial_engine.inputs import OperatingModelInput, YieldScenario
from financial_engine.results import (
    OperatingPeriodResult,
    OperatingSchedules,
    ProjectModelResult,
)
from financial_engine.validation import validate_operating_model_input, has_errors
from financial_engine.provenance import (
    EngineProvenance,
    DerivationEvidence,
    compute_input_fingerprint,
)
from financial_engine.version import ENGINE_VERSION

RUN_PATH_ID = "financial_engine.orchestrator.run_operating_model"

# Sections not yet implemented in Phase 2A.
_PHASE_2A_UNAVAILABLE = ("tax_and_cfads", "financing", "financial_statements", "returns")


def _build_period_engine(inputs: OperatingModelInput):
    """Build a PeriodEngine from the clean input contract."""
    from finco_core.engine.period_engine import PeriodEngine, PeriodFrequency as _PF

    cal = inputs.calendar
    return PeriodEngine(
        financial_close=cal.financial_close,
        construction_months=cal.construction_months,
        horizon_years=cal.horizon_years,
        ppa_years=cal.ppa_years,
        frequency=_PF.SEMESTRIAL,
    )


def _build_project_inputs_proxy(inputs: OperatingModelInput):
    """Build a minimal ProjectInputs proxy for leaf-module reuse.

    The proxy holds only the fields the Phase 2A leaves read.
    It does NOT copy financing, tax, or other out-of-scope fields.
    """
    from finco_core.inputs import (
        ProjectInputs, ProjectInfo, TechnicalParams, RevenueParams,
        OpexItem, CapexStructure, CapexItem, FinancingParams, TaxParams,
        PeriodFrequency as _PF,
    )
    from finco_core.inputs._models import RevenueAdjustmentSchedule

    cal = inputs.calendar
    tech = inputs.technical
    rev = inputs.revenue
    opex_in = inputs.opex

    # Minimal ProjectInfo — only calendar fields used by period/schedule leaves.
    info = ProjectInfo(
        name="clean_engine",
        company="",
        code="clean_engine",
        country_iso="",
        financial_close=cal.financial_close,
        construction_months=cal.construction_months,
        cod_date=_cod_date(cal),
        horizon_years=int(cal.horizon_years),
        period_frequency=_PF.SEMESTRIAL,
    )

    # Map yield scenario.
    yield_scenario = "P_50"
    if tech.yield_scenario == YieldScenario.P90_10Y:
        yield_scenario = "P90-10y"

    technical = TechnicalParams(
        capacity_mw=tech.capacity_mw,
        yield_scenario=yield_scenario,
        operating_hours_p50=tech.operating_hours_p50,
        operating_hours_p90_10y=tech.operating_hours_p90_10y,
        pv_degradation=tech.pv_degradation,
        plant_availability=tech.plant_availability,
        grid_availability=tech.grid_availability,
    )

    # Reconstruct rich schedule objects from the clean contract's tuple fields.
    co2_schedule = None
    if rev.co2_price_semiannual_eur_mwh:
        co2_schedule = RevenueAdjustmentSchedule(
            semiannual_values=rev.co2_price_semiannual_eur_mwh,
        )
    balancing_schedule = None
    if rev.balancing_cost_eur_per_mwh != 0.0:
        balancing_schedule = RevenueAdjustmentSchedule(
            constant_value=rev.balancing_cost_eur_per_mwh,
        )

    revenue = RevenueParams(
        ppa_base_tariff=rev.ppa_base_tariff_eur_mwh,
        ppa_term_years=rev.ppa_term_years,
        ppa_index=rev.ppa_index,
        ppa_production_share=rev.ppa_production_share,
        market_prices_curve=rev.market_prices_curve_eur_mwh,
        market_inflation=rev.market_inflation,
        balancing_cost_pv=rev.balancing_cost_pv_fraction,
        balancing_cost_wind_eur_mwh=rev.balancing_cost_wind_eur_mwh,
        co2_enabled=rev.co2_enabled,
        co2_price_eur=rev.co2_price_eur_mwh,
        first_merchant_operating_period_index=rev.first_merchant_operating_period_index,
        co2_certificate_price_eur_per_mwh=rev.co2_price_eur_per_mwh_scalar,
        co2_sales_schedule=co2_schedule,
        balancing_cost_eur_per_mwh=rev.balancing_cost_eur_per_mwh,
        balancing_cost_schedule=balancing_schedule,
    )

    opex_items = tuple(
        OpexItem(
            name=item.name,
            y1_amount_keur=item.y1_amount_keur,
            annual_inflation=item.annual_inflation,
            step_changes=tuple(item.step_changes),
            percentage_of_opex=item.percentage_of_opex,
        )
        for item in opex_in.items
    )

    # Stub capex/financing/tax — not consumed by Phase 2A leaves.
    stub_capex_item = CapexItem(name="stub", amount_keur=0.0)
    stub_capex = CapexStructure(
        epc_contract=stub_capex_item,
        production_units=stub_capex_item,
        epc_other=stub_capex_item,
        grid_connection=stub_capex_item,
        ops_prep=stub_capex_item,
        insurances=stub_capex_item,
        lease_tax=stub_capex_item,
        construction_mgmt_a=stub_capex_item,
        commissioning=stub_capex_item,
        audit_legal=stub_capex_item,
        construction_mgmt_b=stub_capex_item,
        contingencies=stub_capex_item,
        taxes=stub_capex_item,
        project_acquisition=stub_capex_item,
        project_rights=stub_capex_item,
    )

    return ProjectInputs(
        info=info,
        technical=technical,
        capex=stub_capex,
        opex=opex_items,
        revenue=revenue,
        financing=FinancingParams(),
        tax=TaxParams(),
    )


def _cod_date(cal) -> date:
    """Compute COD date from financial close + construction months."""
    from dateutil.relativedelta import relativedelta
    return cal.financial_close + relativedelta(months=cal.construction_months)


def _compute_depreciation(inputs: OperatingModelInput, periods_meta: list) -> tuple[dict, dict]:
    """Compute per-period book and tax depreciation using build_depreciation_schedule.

    Uses the same straight-line, day-fraction-based formula as the legacy engine.
    Both book and tax schedules are identical in the Phase 2A operating core.
    Returns (book_dep_by_idx, tax_dep_by_idx) dicts keyed by period index.
    """
    from finco_core.inputs import AssetClass, CapexItem, ASSET_CLASS_USEFUL_LIFE
    from finco_core.debt.depreciation_schedule import (
        build_depreciation_schedule,
        depreciation_per_period,
    )

    dep = inputs.depreciation
    if not dep.capex_items_for_depreciation:
        return {}, {}

    # Reconstruct finco_core CapexItem objects from the clean contract.
    capex_items = tuple(
        CapexItem(
            name=item.name,
            amount_keur=item.amount_keur,
            asset_class=AssetClass(item.asset_class_code),
            useful_life_override=item.useful_life_override,
        )
        for item in dep.capex_items_for_depreciation
    )

    annual_schedule = build_depreciation_schedule(
        capex_items=capex_items,
        horizon_years=inputs.calendar.horizon_years,
        senior_tenor_years=dep.financial_cost_useful_life_years,
    )

    dep_by_idx = depreciation_per_period(annual_schedule, periods_meta)
    # Both book and tax use the same formula in the Phase 2A operating core.
    return dep_by_idx, dep_by_idx


def run_operating_model(inputs: OperatingModelInput) -> ProjectModelResult:
    """Run the Phase 2A clean operating model.

    Raises:
        ValueError: if input validation produces ERROR-level issues.
    """
    # Step 1: Validate input.
    validation_issues = validate_operating_model_input(inputs)
    if has_errors(validation_issues):
        errors = [i for i in validation_issues if i.severity.value == "ERROR"]
        msg = "; ".join(f"{i.code} {i.path}: {i.message}" for i in errors)
        raise ValueError(f"Input validation failed with {len(errors)} error(s): {msg}")

    # Step 2: Build period grid.
    from finco_core.engine.period_engine import PeriodMeta
    engine = _build_period_engine(inputs)
    periods_meta: list[PeriodMeta] = engine.periods()

    # Step 3–4: Production and revenue via finco_core leaves.
    from finco_core.revenue.generation import (
        full_generation_schedule,
        full_revenue_schedule,
    )
    proxy = _build_project_inputs_proxy(inputs)
    production_by_idx = full_generation_schedule(proxy, engine)
    revenue_by_idx = full_revenue_schedule(proxy, engine)

    # Step 5: OPEX via finco_core leaf.
    from finco_core.opex.projections import opex_schedule_period
    opex_by_idx = opex_schedule_period(proxy, engine)

    # Step 6: EBITDA = revenue - OPEX, assembled by orchestrator.
    ebitda_by_idx: dict[int, float] = {
        idx: revenue_by_idx.get(idx, 0.0) - opex_by_idx.get(idx, 0.0)
        for idx in production_by_idx
    }

    # Step 7: Book and tax depreciation via build_depreciation_schedule leaf.
    book_dep_by_idx, tax_dep_by_idx = _compute_depreciation(inputs, periods_meta)

    # Step 8: Assemble immutable period results.
    period_results: list[OperatingPeriodResult] = []
    for p in periods_meta:
        idx = p.index
        period_results.append(OperatingPeriodResult(
            period_index=idx,
            period_start=p.start_date,
            period_end=p.end_date,
            year_index=float(p.year_index),
            period_in_year=float(p.period_in_year),
            is_construction=p.is_construction,
            is_operation=p.is_operation,
            is_ppa_active=p.is_ppa_active,
            days_in_period=p.days_in_period,
            day_fraction=p.day_fraction,
            production_mwh=production_by_idx.get(idx, 0.0),
            revenue_keur=revenue_by_idx.get(idx, 0.0),
            opex_keur=opex_by_idx.get(idx, 0.0),
            ebitda_keur=ebitda_by_idx.get(idx, 0.0),
            book_depreciation_keur=book_dep_by_idx.get(idx, 0.0),
            tax_depreciation_keur=tax_dep_by_idx.get(idx, 0.0),
        ))

    periods_tuple = tuple(period_results)

    operating_schedules = OperatingSchedules(
        period_indices=tuple(p.period_index for p in periods_tuple),
        production_mwh=tuple(p.production_mwh for p in periods_tuple),
        revenue_keur=tuple(p.revenue_keur for p in periods_tuple),
        opex_keur=tuple(p.opex_keur for p in periods_tuple),
        ebitda_keur=tuple(p.ebitda_keur for p in periods_tuple),
        book_depreciation_keur=tuple(p.book_depreciation_keur for p in periods_tuple),
        tax_depreciation_keur=tuple(p.tax_depreciation_keur for p in periods_tuple),
    )

    # Step 9: Attach immutable provenance.
    fingerprint = compute_input_fingerprint(inputs)
    evidence = (
        DerivationEvidence(
            output_path="operating_schedules.production_mwh",
            source_module="finco_core.revenue.generation",
            source_function="full_generation_schedule",
            input_paths=("technical", "calendar"),
            notes=(),
        ),
        DerivationEvidence(
            output_path="operating_schedules.revenue_keur",
            source_module="finco_core.revenue.generation",
            source_function="full_revenue_schedule",
            input_paths=("revenue", "calendar", "technical"),
            notes=(),
        ),
        DerivationEvidence(
            output_path="operating_schedules.opex_keur",
            source_module="finco_core.opex.projections",
            source_function="opex_schedule_period",
            input_paths=("opex", "calendar"),
            notes=(),
        ),
        DerivationEvidence(
            output_path="operating_schedules.ebitda_keur",
            source_module="financial_engine.orchestrator",
            source_function="run_operating_model",
            input_paths=("operating_schedules.revenue_keur", "operating_schedules.opex_keur"),
            notes=("ebitda = revenue - opex, assembled by orchestrator",),
        ),
        DerivationEvidence(
            output_path="operating_schedules.book_depreciation_keur",
            source_module="finco_core.debt.depreciation_schedule",
            source_function="build_depreciation_schedule+depreciation_per_period",
            input_paths=("depreciation", "calendar.horizon_years"),
            notes=("straight-line, day-fraction-weighted; same formula as legacy engine",),
        ),
        DerivationEvidence(
            output_path="operating_schedules.tax_depreciation_keur",
            source_module="finco_core.debt.depreciation_schedule",
            source_function="build_depreciation_schedule+depreciation_per_period",
            input_paths=("depreciation", "calendar.horizon_years"),
            notes=("equal to book depreciation in Phase 2A operating core",),
        ),
    )

    provenance = EngineProvenance(
        engine_version=ENGINE_VERSION,
        run_path_id=RUN_PATH_ID,
        input_fingerprint=fingerprint,
        derivation_evidence=evidence,
    )

    return ProjectModelResult(
        provenance=provenance,
        periods=periods_tuple,
        operating_schedules=operating_schedules,
        unavailable_sections=_PHASE_2A_UNAVAILABLE,
        validation_issues=validation_issues,
        warnings=(),
    )
