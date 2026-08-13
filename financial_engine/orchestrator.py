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

from financial_engine.inputs import (
    DebtSizingCaseInput,
    OperatingModelInput,
    TaxCfadsModelInput,
    SeniorDebtModelInput,
    YieldScenario,
)
from financial_engine.results import (
    DebtSizingSchedules,
    OperatingPeriodResult,
    OperatingSchedules,
    PostSeniorCashSchedules,
    ProjectModelResult,
    SeniorDebtSchedules as _SeniorDebtSchedulesResult,
    ShareholderLoanDiagnostics,
    ShareholderLoanSchedules,
    TaxAndCfadsSchedules,
)
from financial_engine.validation import validate_operating_model_input, has_errors
from financial_engine.provenance import (
    EngineProvenance,
    DerivationEvidence,
    compute_input_fingerprint,
    compute_tax_cfads_fingerprint,
    compute_senior_debt_fingerprint,
)
from financial_engine.version import ENGINE_VERSION

RUN_PATH_ID = "financial_engine.orchestrator.run_operating_model"

# Sections not yet implemented in Phase 2A.
_PHASE_2A_UNAVAILABLE = ("tax_and_cfads", "financing", "financial_statements", "returns")

# Sections still out of scope in Phase 2B.
_PHASE_2B_UNAVAILABLE = ("financing", "financial_statements", "returns")


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


def _build_project_inputs_proxy(inputs: OperatingModelInput, tariff_schedule: tuple[float, ...] = ()):
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
        ppa_indexation_start_policy=(
            rev.ppa_indexation_start_policy.value
            if rev.ppa_indexation_start_policy is not None
            else None  # preserve unmigrated state; finco_core uses tariff_at_year
        ),
        ppa_indexation_start_date=rev.ppa_indexation_start_date,
        ppa_tariff_by_operating_period=tariff_schedule,
        market_price_calendar_start_year=rev.merchant_price_calendar_start_year,
        market_prices_by_calendar_year_eur_mwh=rev.merchant_prices_by_calendar_year_eur_mwh,
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

    # Rebuild HierarchicalOpexCapability for opex_schedule_period dispatch.
    # Presence of hierarchical_model in clean OpexInput is the sole signal.
    _hier_cap = None
    if opex_in.hierarchical_model is not None:
        from finco_core.opex._capability import HierarchicalOpexCapability
        _hier_cap = HierarchicalOpexCapability(
            opex_model=opex_in.hierarchical_model,
            external_annual_series=opex_in.hierarchical_external_annual_series,
        )

    # Stub capex/financing/tax — not consumed by Phase 2A leaves.
    # senior_tenor_years is sourced from depreciation (same origin as financing.senior_tenor_years
    # in the adapter) so that OpexCalculationContext receives the correct value for
    # SENIOR_DEBT_TENOR_ACTIVE subitems when the hierarchical path is active.
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

    # senior_tenor_years for the proxy is sourced from opex_in.senior_debt_tenor_years —
    # an explicit field mapped from financing.senior_tenor_years in the adapter.
    # This decouples OPEX tenor from the depreciation contract.
    # When senior_debt_tenor_years is None (flat projects), FinancingParams default (0) is fine
    # because opex_schedule_period() takes the flat path and never reads financing.
    _proxy_senior_tenor = opex_in.senior_debt_tenor_years or 0

    return ProjectInputs(
        info=info,
        technical=technical,
        capex=stub_capex,
        opex=opex_items,
        revenue=revenue,
        financing=FinancingParams(
            senior_tenor_years=_proxy_senior_tenor,
        ),
        tax=TaxParams(),
        hierarchical_opex_capability=_hier_cap,
    )


def _cod_date(cal) -> date:
    """Compute contractual COD from financial close + construction months (EDATE-equivalent)."""
    from dateutil.relativedelta import relativedelta
    return cal.financial_close + relativedelta(months=cal.construction_months)


def _build_ppa_tariff_schedule(
    inputs: OperatingModelInput,
    periods_meta: list,
) -> tuple[float, ...]:
    """Compute per-operating-period PPA tariff using the explicit indexation policy.

    Returns a tuple indexed by operating_period_index (0-based) covering all
    operating periods in the horizon.  Construction periods are excluded.

    When policy is AFTER_FIRST_FULL_OPERATING_YEAR and no ppa_tariff_by_operating_period
    is pre-loaded, this function implements the same effective result as the legacy
    tariff_at_year formula for a project where COD aligns with semiannual boundaries —
    but correctly handles non-aligned CODs and all three policies generically.
    """
    from financial_engine.ppa_indexation import (
        compute_ppa_tariff,
        validate_no_intraperiod_escalation,
        PpaIndexationStartPolicy,
    )

    rev = inputs.revenue
    policy = rev.ppa_indexation_start_policy

    # None = not yet explicitly migrated. Return empty tuple so finco_core falls back
    # to the legacy tariff_at_year(year_index) path — exact pre-PR behaviour preserved.
    if policy is None:
        return ()

    cod = _cod_date(inputs.calendar)
    base_tariff = rev.ppa_base_tariff_eur_mwh
    ppa_index = rev.ppa_index
    ppa_indexation_start_date = rev.ppa_indexation_start_date

    op_periods = [p for p in periods_meta if p.is_operation]
    schedule: list[float] = []
    for p in op_periods:
        validate_no_intraperiod_escalation(
            policy=policy,
            cod=cod,
            period_start=p.start_date,
            period_end=p.end_date,
            ppa_indexation_start_date=ppa_indexation_start_date,
        )
        t = compute_ppa_tariff(
            base_tariff=base_tariff,
            ppa_index=ppa_index,
            policy=policy,
            cod=cod,
            period_end=p.end_date,
            ppa_indexation_start_date=ppa_indexation_start_date,
        )
        schedule.append(t)
    return tuple(schedule)


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
    if not dep.book_capex_items_for_depreciation and not dep.tax_capex_items_for_depreciation:
        return {}, {}

    def _build_schedule(capex_item_defs: tuple) -> dict[int, float]:
        if not capex_item_defs:
            return {}
        items = tuple(
            CapexItem(
                name=item.name,
                amount_keur=item.amount_keur,
                asset_class=AssetClass(item.asset_class_code),
                useful_life_override=item.useful_life_override,
            )
            for item in capex_item_defs
        )
        annual = build_depreciation_schedule(
            capex_items=items,
            horizon_years=inputs.calendar.horizon_years,
            senior_tenor_years=dep.financial_cost_useful_life_years,
        )
        return depreciation_per_period(annual, periods_meta)

    book_dep_by_idx = _build_schedule(dep.book_capex_items_for_depreciation)
    tax_dep_by_idx = _build_schedule(dep.tax_capex_items_for_depreciation)
    return book_dep_by_idx, tax_dep_by_idx


def derive_debt_sizing_operating_input(
    base_op: OperatingModelInput,
    debt_sizing_case: DebtSizingCaseInput,
) -> OperatingModelInput:
    """Derive the bank/debt-sizing operating input from the Base operating input.

    Pure immutable transformer: inherits all Base project fundamentals (calendar,
    opex, capex, PPA, tax structure, etc.) and overrides only the fields present
    in DebtSizingCaseInput:
    - technical.yield_scenario → debt_sizing_case.production_yield_scenario
    - revenue merchant price schedule → bank-case override (when provided)

    When no merchant price override is provided, Base revenue assumptions are
    inherited completely unchanged.

    GENERIC_DEBT_SIZING_CASE_IS_EXPLICIT_AND_PROJECT_IDENTITY_FREE:
    No project-name dispatch, no project-code dispatch, no hardcoded schedules,
    no Excel-compatibility quirks.

    Merchant price override precedence (mutually exclusive):
    1. calendar-year form (merchant_price_calendar_start_year is not None
       OR merchant_prices_by_calendar_year_eur_mwh is non-empty)
    2. relative curve form (market_prices_curve_eur_mwh non-empty)
    3. Base revenue inherited unchanged (neither provided)
    """
    from dataclasses import replace as _replace

    new_technical = _replace(
        base_op.technical,
        yield_scenario=debt_sizing_case.production_yield_scenario,
    )

    if (
        debt_sizing_case.merchant_price_calendar_start_year is not None
        or debt_sizing_case.merchant_prices_by_calendar_year_eur_mwh
    ):
        # Apply calendar-year override; clear curve form to prevent dual representation.
        new_revenue = _replace(
            base_op.revenue,
            merchant_price_calendar_start_year=debt_sizing_case.merchant_price_calendar_start_year,
            merchant_prices_by_calendar_year_eur_mwh=debt_sizing_case.merchant_prices_by_calendar_year_eur_mwh,
            market_prices_curve_eur_mwh=(),
        )
    elif debt_sizing_case.market_prices_curve_eur_mwh:
        new_revenue = _replace(
            base_op.revenue,
            market_prices_curve_eur_mwh=debt_sizing_case.market_prices_curve_eur_mwh,
            merchant_price_calendar_start_year=None,
            merchant_prices_by_calendar_year_eur_mwh=(),
        )
    else:
        new_revenue = base_op.revenue

    return _replace(base_op, technical=new_technical, revenue=new_revenue)


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
    tariff_schedule = _build_ppa_tariff_schedule(inputs, periods_meta)
    proxy = _build_project_inputs_proxy(inputs, tariff_schedule)
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
            ebit_keur=ebitda_by_idx.get(idx, 0.0) - book_dep_by_idx.get(idx, 0.0),
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
        ebit_keur=tuple(p.ebit_keur for p in periods_tuple),
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


TAX_CFADS_RUN_PATH_ID = "financial_engine.orchestrator.run_tax_cfads_model"


def _assemble_tax_cfads_schedules(
    base_result: "ProjectModelResult",
    tax_result,
    period_results,
    cfads_results,
) -> "TaxAndCfadsSchedules":
    """Assemble a TaxAndCfadsSchedules from authoritative tax and CFADS results.

    Extracted so that run_tax_cfads_model and run_senior_debt_model share identical
    assembly logic regardless of which solver iteration produced the final values.
    """
    annual_map = {ar.tax_year: ar for ar in tax_result.annual_results}
    # Use primary_tax_year (display-only) for audit lookups that need a single year per period.
    period_to_annual_tax_year: dict[int, int] = {
        pr.period_index: pr.primary_tax_year for pr in period_results
    }

    def _per_period_annual_share(attr: str) -> tuple[float, ...]:
        """Allocate an annual attribute to periods using normalised allocation fractions."""
        out: list[float] = []
        for pr in period_results:
            if pr.tax_year_allocations:
                total = sum(
                    getattr(annual_map[a.tax_year], attr) * a.allocation_fraction
                    for a in pr.tax_year_allocations
                    if a.tax_year in annual_map
                )
            else:
                total = 0.0
            out.append(total)
        return tuple(out)

    period_indices = tuple(pr.period_index for pr in period_results)
    cit_accrual_per_period = tuple(pr.cit_accrual_share_keur for pr in period_results)
    corporate_tax_cash = tuple(pr.cash_tax_keur for pr in period_results)
    cfads = tuple(cr.cfads_keur for cr in cfads_results)

    tax_loss_opening: list[float] = []
    tax_loss_closing: list[float] = []
    tax_loss_used: list[float] = []
    for pr in period_results:
        tax_year = period_to_annual_tax_year.get(pr.period_index, -999999)
        ar = annual_map.get(tax_year)
        if ar is None:
            tax_loss_opening.append(0.0)
            tax_loss_closing.append(0.0)
            tax_loss_used.append(0.0)
        else:
            first_idx = ar.period_indices[0] if ar.period_indices else -1
            if pr.period_index == first_idx:
                tax_loss_opening.append(ar.loss_opening_keur)
                tax_loss_closing.append(ar.loss_closing_keur)
                tax_loss_used.append(ar.loss_used_keur)
            else:
                tax_loss_opening.append(0.0)
                tax_loss_closing.append(0.0)
                tax_loss_used.append(0.0)

    taxable_profit = tuple(pr.taxable_income_before_lcf_share_keur for pr in period_results)
    taxable_after_lcf = _per_period_annual_share("taxable_income_after_lcf_keur")
    ebitda_per_period = tuple(cr.ebitda_keur for cr in cfads_results)
    tax_dep_per_period = tuple(
        p.tax_depreciation_keur for p in base_result.periods  # type: ignore[attr-defined]
    )

    return TaxAndCfadsSchedules(
        period_indices=period_indices,
        taxable_profit_keur=taxable_profit,
        taxable_income_before_losses_audit_keur=taxable_profit,
        taxable_profit_after_losses_audit_keur=taxable_after_lcf,
        tax_keur=cit_accrual_per_period,
        corporate_tax_cash_keur=corporate_tax_cash,
        cit_accrual_audit_keur=cit_accrual_per_period,
        cash_tax_bridge_reconciliation_keur=tuple(
            e - c for e, c in zip(ebitda_per_period, corporate_tax_cash)
        ),
        cash_tax_current_period_audit_keur=corporate_tax_cash,
        tax_loss_opening_audit_keur=tuple(tax_loss_opening),
        tax_loss_closing_audit_keur=tuple(tax_loss_closing),
        tax_loss_used_audit_keur=tuple(tax_loss_used),
        fiscal_reintegration_audit_keur=tuple(
            pr.disallowed_interest_keur
            + pr.other_fiscal_reintegration_keur
            + pr.shl_non_deductible_interest_keur
            for pr in period_results
        ),
        tax_depreciation_audit_keur=tax_dep_per_period,
        cf_after_tax_keur=cfads,
        cfads_keur=cfads,
        terminal_unpaid_tax_keur=tax_result.terminal_unpaid_tax_keur,
    )


def run_tax_cfads_model(inputs: TaxCfadsModelInput) -> ProjectModelResult:
    """Phase 2B orchestrator: operating core + annual tax + canonical CFADS.

    The operating model is invoked exactly once.  Canonical CFADS is computed
    by ``calculate_canonical_cfads``; no inline CFADS formula exists here.

    Calculation order:
      1.  Validate operating + tax inputs; refuse on ERROR-level issues.
      2.  Run Phase 2A operating model (exactly once).
      3.  Calendar-year fragment splitting → TaxYearCalculationBasis per year.
      4.  Per tax year: ATAD → taxable income → FIFO LCF → CIT.
      5.  Allocate cash tax to periods (TAX_YEAR_LAST_PERIOD or SAME_PERIOD).
      6.  Canonical CFADS = EBITDA − cash_tax via calculate_canonical_cfads().
      7.  Assemble TaxAndCfadsSchedules.
      8.  Attach Phase 2B provenance.

    Taxable income formula::

        taxable_income_before_lcf = EBITDA − tax_dep − deductible_interest
                                   + other_fiscal_reintegration
        (disallowed_interest is NOT added back separately)
    """
    from financial_engine.validation import validate_tax_calculation_input, has_errors
    from financial_engine.cfads import calculate_canonical_cfads

    # Step 1: Validate
    base_result = run_operating_model(inputs.operating)  # single invocation
    known_period_indices = frozenset(p.period_index for p in base_result.periods)
    tax_issues = validate_tax_calculation_input(inputs.tax, known_period_indices)
    combined_issues = base_result.validation_issues + tax_issues
    if has_errors(combined_issues):
        raise ValueError(
            f"Phase 2B validation failed with "
            f"{sum(1 for i in combined_issues if i.severity.value == 'ERROR')} error(s)"
        )

    # Steps 2-5: Annual tax engine
    from financial_engine.tax.engine import calculate_tax
    tax_result = calculate_tax(base_result.periods, inputs.tax)

    # Step 6: Canonical CFADS via the single authoritative function
    period_results = tax_result.period_results
    cfads_results = calculate_canonical_cfads(base_result.periods, period_results)

    # Step 7: Assemble TaxAndCfadsSchedules
    tax_and_cfads = _assemble_tax_cfads_schedules(base_result, tax_result, period_results, cfads_results)

    # Step 8: Phase 2B provenance
    fingerprint = compute_tax_cfads_fingerprint(inputs)
    evidence = base_result.provenance.derivation_evidence + (
        DerivationEvidence(
            output_path="tax_and_cfads.taxable_income_before_losses_audit_keur",
            source_module="financial_engine.tax.engine",
            source_function="calculate_tax",
            input_paths=("tax.policy", "tax.period_interest", "operating_schedules.ebitda_keur",
                         "operating_schedules.tax_depreciation_keur"),
            notes=("EBITDA - tax_dep - deductible_interest + other_reintegration",
                   "disallowed_interest is NOT added back separately"),
        ),
        DerivationEvidence(
            output_path="tax_and_cfads.taxable_profit_after_losses_audit_keur",
            source_module="financial_engine.tax.loss_ledger",
            source_function="run_annual_fifo_ledger",
            input_paths=("tax.opening_loss_vintages", "annual taxable_income_before_lcf"),
            notes=("annual FIFO vintage ledger; origin_tax_year + lcf_years = last_usable_tax_year",),
        ),
        DerivationEvidence(
            output_path="tax_and_cfads.corporate_tax_cash_keur",
            source_module="financial_engine.tax.engine",
            source_function="calculate_tax",
            input_paths=("tax.policy.cash_tax_timing", "tax.policy.cash_tax_payment_lag_periods"),
            notes=("full annual liability paid in last period of year + lag",),
        ),
        DerivationEvidence(
            output_path="tax_and_cfads.cfads_keur",
            source_module="financial_engine.orchestrator",
            source_function="run_tax_cfads_model",
            input_paths=("operating_schedules.ebitda_keur", "tax_and_cfads.corporate_tax_cash_keur"),
            notes=("canonical CFADS = EBITDA - cash_tax_paid; pre-debt-service, pre-DSRA",),
        ),
    )
    provenance = EngineProvenance(
        engine_version=ENGINE_VERSION,
        run_path_id=TAX_CFADS_RUN_PATH_ID,
        input_fingerprint=fingerprint,
        derivation_evidence=evidence,
    )

    all_issues = combined_issues
    warnings = base_result.warnings + tuple(
        f"{i.code} {i.path}: {i.message}" for i in tax_issues
        if i.severity.value == "WARNING"
    )

    return ProjectModelResult(
        provenance=provenance,
        periods=base_result.periods,
        operating_schedules=base_result.operating_schedules,
        tax_and_cfads=tax_and_cfads,
        unavailable_sections=_PHASE_2B_UNAVAILABLE,
        validation_issues=all_issues,
        warnings=warnings,
    )


SENIOR_DEBT_RUN_PATH_ID = "financial_engine.orchestrator.run_senior_debt_model"

# Sections still out of scope in Phase 2C.
_PHASE_2C_UNAVAILABLE = ("financial_statements", "returns")


def _merge_financing_tax_input(
    base_tax_input: object,
    senior_interest_by_period: dict[int, float] | None = None,
    shl_interest_by_period: dict[int, float] | None = None,
) -> object:
    """Merge Senior + SHL interest into tax input without mutating the source.

    Components are overridden only when explicitly supplied by the caller.
    SHL tax treatment is owned by TaxPolicy; this function does not create
    fiscal reintegration addbacks.
    """
    from financial_engine.inputs import (
        PeriodInterestInput,
        TaxCalculationInput,
    )

    senior_interest_by_period = senior_interest_by_period or {}
    shl_interest_by_period = shl_interest_by_period or {}
    merged_interest: dict[int, PeriodInterestInput] = {
        pi.period_index: pi for pi in base_tax_input.period_interest
    }
    for idx in set(senior_interest_by_period) | set(shl_interest_by_period):
        existing = merged_interest.get(idx)
        merged_interest[idx] = PeriodInterestInput(
            period_index=idx,
            senior_interest_keur=(
                senior_interest_by_period[idx]
                if idx in senior_interest_by_period
                else (existing.senior_interest_keur if existing else 0.0)
            ),
            shl_interest_keur=(
                shl_interest_by_period[idx]
                if idx in shl_interest_by_period
                else (existing.shl_interest_keur if existing else 0.0)
            ),
            other_interest_keur=existing.other_interest_keur if existing else 0.0,
        )

    return TaxCalculationInput(
        policy=base_tax_input.policy,
        opening_loss_vintages=base_tax_input.opening_loss_vintages,
        period_interest=tuple(merged_interest[idx] for idx in sorted(merged_interest)),
        period_adjustments=base_tax_input.period_adjustments,
    )


def _assemble_post_senior_cash_schedules(
    periods: tuple[OperatingPeriodResult, ...],
    tax_and_cfads: TaxAndCfadsSchedules,
    senior_debt_result: object,
) -> PostSeniorCashSchedules:
    """Build Base post-senior cash schedules from authoritative Base CFADS."""
    sd_service_by_idx: dict[int, float] = dict(
        zip(
            senior_debt_result.period_indices,
            senior_debt_result.senior_debt_service_keur,
        )
    )
    base_cfads_by_idx: dict[int, float] = dict(
        zip(tax_and_cfads.period_indices, tax_and_cfads.cfads_keur)
    )
    period_is_constr: dict[int, bool] = {p.period_index: p.is_construction for p in periods}
    all_period_indices = tuple(p.period_index for p in periods)
    cash_after: list[float] = []
    cash_avail: list[float] = []
    for idx in all_period_indices:
        base_cfads = base_cfads_by_idx.get(idx, 0.0)
        senior_service = sd_service_by_idx.get(idx, 0.0)
        after = base_cfads - senior_service
        cash_after.append(after)
        cash_avail.append(0.0 if period_is_constr.get(idx, False) else max(0.0, after))

    return PostSeniorCashSchedules(
        period_indices=all_period_indices,
        base_cfads_keur=tuple(base_cfads_by_idx.get(i, 0.0) for i in all_period_indices),
        senior_debt_service_keur=tuple(sd_service_by_idx.get(i, 0.0) for i in all_period_indices),
        cash_after_senior_before_reserves_keur=tuple(cash_after),
        cash_available_for_shl_before_reserves_keur=tuple(cash_avail),
    )


def _field_converged_local(a: float, b: float, abs_tol: float, rel_tol: float) -> bool:
    diff = abs(a - b)
    if diff <= abs_tol:
        return True
    if rel_tol > 0.0:
        return diff / max(abs(a), abs(b), 1.0) <= rel_tol
    return False


def _max_vector_delta(
    a: tuple[float, ...],
    b: tuple[float, ...],
) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return float("inf")
    return max(abs(a[i] - b[i]) for i in range(n))


def _build_debt_sizing_schedules_from_bank(
    *,
    bank_phase2a_result: ProjectModelResult,
    final_bank_tax_result: object,
    final_bank_cfads_results: tuple,
    senior_debt_result: object,
) -> DebtSizingSchedules:
    import math as _math

    sd_service_by_idx: dict[int, float] = dict(
        zip(
            senior_debt_result.period_indices,
            senior_debt_result.senior_debt_service_keur,
        )
    )
    final_bank_cash_tax_by_idx = {
        pr.period_index: pr.cash_tax_keur for pr in final_bank_tax_result.period_results
    }
    final_bank_cfads_by_idx = {
        cr.period_index: cr.cfads_keur for cr in final_bank_cfads_results
    }
    ops_indices = bank_phase2a_result.operating_schedules.period_indices
    bank_sizing_dscr: tuple[float | None, ...] = tuple(
        (
            final_bank_cfads_by_idx.get(i, 0.0) / sd_service_by_idx[i]
            if i in sd_service_by_idx
            and sd_service_by_idx[i] > 0.0
            and _math.isfinite(final_bank_cfads_by_idx.get(i, 0.0))
            else None
        )
        for i in ops_indices
    )
    solver_dscr_by_idx: dict[int, float | None] = dict(
        zip(senior_debt_result.period_indices, senior_debt_result.senior_dscr)
    )
    solver_bank_dscr: tuple[float | None, ...] = tuple(
        solver_dscr_by_idx.get(i, None) for i in ops_indices
    )
    return DebtSizingSchedules(
        period_indices=ops_indices,
        bank_production_mwh=bank_phase2a_result.operating_schedules.production_mwh,
        bank_revenue_keur=bank_phase2a_result.operating_schedules.revenue_keur,
        bank_opex_keur=bank_phase2a_result.operating_schedules.opex_keur,
        bank_ebitda_keur=bank_phase2a_result.operating_schedules.ebitda_keur,
        bank_cash_tax_keur=tuple(final_bank_cash_tax_by_idx.get(i, 0.0) for i in ops_indices),
        bank_cfads_keur=tuple(cr.cfads_keur for cr in final_bank_cfads_results),
        bank_sizing_dscr=bank_sizing_dscr,
        solver_bank_dscr=solver_bank_dscr,
    )


def _build_result_senior_debt_schedules(
    *,
    senior_debt_result: object,
    final_tax_cfads: TaxAndCfadsSchedules,
) -> _SeniorDebtSchedulesResult:
    import math as _math

    sd_service_by_idx: dict[int, float] = dict(
        zip(
            senior_debt_result.period_indices,
            senior_debt_result.senior_debt_service_keur,
        )
    )
    base_cfads_by_idx: dict[int, float] = dict(
        zip(final_tax_cfads.period_indices, final_tax_cfads.cfads_keur)
    )
    base_dscr: tuple[float | None, ...] = tuple(
        (
            base_cfads_by_idx.get(idx, 0.0) / ds
            if (ds := sd_service_by_idx.get(idx, 0.0)) > 0.0
            and _math.isfinite(base_cfads_by_idx.get(idx, 0.0))
            else None
        )
        for idx in senior_debt_result.period_indices
    )
    diag_dict = {
        "converged": senior_debt_result.diagnostics.converged,
        "is_authoritative": senior_debt_result.diagnostics.is_authoritative,
        "iteration_count": senior_debt_result.diagnostics.iteration_count,
        "initial_debt_guess_keur": senior_debt_result.diagnostics.initial_debt_guess_keur,
        "final_debt_size_keur": senior_debt_result.diagnostics.final_debt_size_keur,
        "maximum_absolute_difference_keur": senior_debt_result.diagnostics.maximum_absolute_difference_keur,
        "maximum_relative_difference": senior_debt_result.diagnostics.maximum_relative_difference,
        "binding_constraint": senior_debt_result.diagnostics.binding_constraint,
        "termination_reason": senior_debt_result.diagnostics.termination_reason,
    }
    return _SeniorDebtSchedulesResult(
        period_indices=senior_debt_result.period_indices,
        senior_debt_opening_keur=senior_debt_result.senior_debt_opening_keur,
        senior_interest_keur=senior_debt_result.senior_interest_keur,
        senior_principal_keur=senior_debt_result.senior_principal_keur,
        senior_debt_service_keur=senior_debt_result.senior_debt_service_keur,
        senior_debt_closing_keur=senior_debt_result.senior_debt_closing_keur,
        base_dscr=base_dscr,
        debt_size_keur=senior_debt_result.debt_size_keur,
        binding_constraint=senior_debt_result.binding_constraint,
        diagnostics=diag_dict,
    )


def _run_senior_debt_model_with_shl(inputs: SeniorDebtModelInput) -> ProjectModelResult:
    """Phase B5: Senior debt + SHL + tax fixed-point integration."""
    from financial_engine.cfads import calculate_canonical_cfads
    from financial_engine.inputs import TaxCfadsModelInput
    from financial_engine.senior_debt.inputs import SeniorDebtInputs
    from financial_engine.senior_debt.models import SeniorDebtNonConvergenceError
    from financial_engine.senior_debt.policy import SeniorDebtPolicy
    from financial_engine.senior_debt.solver import solve_senior_debt
    from financial_engine.shl.production import compute_shareholder_loan_schedules
    from financial_engine.tax.engine import calculate_tax

    policy: SeniorDebtPolicy = inputs.senior_debt_policy  # type: ignore[assignment]
    sd_inputs: SeniorDebtInputs = inputs.senior_debt_inputs  # type: ignore[assignment]
    shl_input = inputs.shareholder_loan
    assert shl_input is not None

    bank_op = derive_debt_sizing_operating_input(inputs.operating, inputs.debt_sizing_case)
    phase2b_result = run_tax_cfads_model(TaxCfadsModelInput(operating=inputs.operating, tax=inputs.tax))
    bank_phase2a_result = run_operating_model(bank_op)
    base_tax_input = inputs.tax

    debt_start = policy.repayment_start_period_index
    debt_end = policy.maturity_period_index
    debt_periods = tuple(
        p for p in bank_phase2a_result.periods
        if p.is_operation and debt_start <= p.period_index <= debt_end
    )

    shl_interest_guess: dict[int, float] = {}
    previous_shl: ShareholderLoanSchedules | None = None
    last_max_closing_delta = float("inf")
    last_max_interest_delta = float("inf")

    for iteration in range(1, shl_input.maximum_iterations + 1):
        def tax_cfads_fn(
            senior_interest_by_period: dict[int, float],
        ) -> tuple[dict[int, float], dict[int, float]]:
            tax_input = _merge_financing_tax_input(
                base_tax_input,
                senior_interest_by_period,
                shl_interest_guess,
            )
            tax_result = calculate_tax(bank_phase2a_result.periods, tax_input)
            cfads_results = calculate_canonical_cfads(
                bank_phase2a_result.periods,
                tax_result.period_results,
            )
            return (
                {cr.period_index: cr.cfads_keur for cr in cfads_results},
                {pr.period_index: pr.cash_tax_keur for pr in tax_result.period_results},
            )

        senior_result = solve_senior_debt(
            policy=policy,
            inputs=sd_inputs,
            periods=debt_periods,
            tax_cfads_fn=tax_cfads_fn,
        )
        if not senior_result.diagnostics.is_authoritative:
            raise SeniorDebtNonConvergenceError(
                "Senior debt failed inside SHL fixed point: "
                f"termination_reason={senior_result.diagnostics.termination_reason!r}"
            )

        senior_interest = dict(
            zip(senior_result.period_indices, senior_result.senior_interest_keur)
        )
        base_tax = calculate_tax(
            phase2b_result.periods,
            _merge_financing_tax_input(
                base_tax_input,
                senior_interest,
                shl_interest_guess,
            ),
        )
        base_cfads = calculate_canonical_cfads(phase2b_result.periods, base_tax.period_results)
        tax_cfads = _assemble_tax_cfads_schedules(
            phase2b_result,
            base_tax,
            base_tax.period_results,
            base_cfads,
        )
        post_senior_cash = _assemble_post_senior_cash_schedules(
            phase2b_result.periods,
            tax_cfads,
            senior_result,
        )
        provisional_diag = ShareholderLoanDiagnostics(
            converged=False,
            is_authoritative=False,
            iteration_count=iteration,
            max_iterations=shl_input.maximum_iterations,
            convergence_tolerance_keur=shl_input.convergence_tolerance_keur,
            convergence_relative_tolerance=shl_input.convergence_relative_tolerance,
            max_closing_delta_keur=last_max_closing_delta,
            max_interest_delta_keur=last_max_interest_delta,
            termination_reason="ITERATING",
        )
        shl_schedule = compute_shareholder_loan_schedules(
            phase2b_result.periods,
            shl_input,
            post_senior_cash.cash_available_for_shl_before_reserves_keur,
            diagnostics=provisional_diag,
        )
        new_interest = dict(
            zip(shl_schedule.period_indices, shl_schedule.shl_gross_interest_keur)
        )

        if previous_shl is not None:
            last_max_closing_delta = _max_vector_delta(
                previous_shl.shl_closing_keur,
                shl_schedule.shl_closing_keur,
            )
            last_max_interest_delta = _max_vector_delta(
                tuple(shl_interest_guess.get(i, 0.0) for i in shl_schedule.period_indices),
                shl_schedule.shl_gross_interest_keur,
            )
            if _field_converged_local(
                last_max_closing_delta,
                0.0,
                shl_input.convergence_tolerance_keur,
                shl_input.convergence_relative_tolerance,
            ) and _field_converged_local(
                last_max_interest_delta,
                0.0,
                shl_input.convergence_tolerance_keur,
                shl_input.convergence_relative_tolerance,
            ):
                previous_shl = shl_schedule
                shl_interest_guess = new_interest
                break

        previous_shl = shl_schedule
        shl_interest_guess = new_interest
    else:
        raise SeniorDebtNonConvergenceError(
            "SHL fixed point terminated without an authoritative result: "
            f"iteration_count={shl_input.maximum_iterations}; "
            "termination_reason='MAX_ITERATIONS_REACHED'"
        )

    # FINAL_FINANCING_STATE_RECOMPUTED_FROM_CONVERGED_SHL_AND_SENIOR_SCHEDULES
    final_shl_interest = dict(
        zip(previous_shl.period_indices, previous_shl.shl_gross_interest_keur)
    )

    def final_tax_cfads_fn(
        senior_interest_by_period: dict[int, float],
    ) -> tuple[dict[int, float], dict[int, float]]:
        tax_input = _merge_financing_tax_input(
            base_tax_input,
            senior_interest_by_period,
            final_shl_interest,
        )
        tax_result = calculate_tax(bank_phase2a_result.periods, tax_input)
        cfads_results = calculate_canonical_cfads(
            bank_phase2a_result.periods,
            tax_result.period_results,
        )
        return (
            {cr.period_index: cr.cfads_keur for cr in cfads_results},
            {pr.period_index: pr.cash_tax_keur for pr in tax_result.period_results},
        )

    final_senior_result = solve_senior_debt(
        policy=policy,
        inputs=sd_inputs,
        periods=debt_periods,
        tax_cfads_fn=final_tax_cfads_fn,
    )
    if not final_senior_result.diagnostics.is_authoritative:
        raise SeniorDebtNonConvergenceError(
            "Final senior debt recomputation failed inside SHL fixed point: "
            f"termination_reason={final_senior_result.diagnostics.termination_reason!r}"
        )

    final_senior_interest = dict(
        zip(final_senior_result.period_indices, final_senior_result.senior_interest_keur)
    )
    final_base_tax_input = _merge_financing_tax_input(
        base_tax_input,
        final_senior_interest,
        final_shl_interest,
    )
    final_base_tax = calculate_tax(phase2b_result.periods, final_base_tax_input)
    final_base_cfads = calculate_canonical_cfads(
        phase2b_result.periods,
        final_base_tax.period_results,
    )
    final_tax_cfads = _assemble_tax_cfads_schedules(
        phase2b_result,
        final_base_tax,
        final_base_tax.period_results,
        final_base_cfads,
    )
    final_post_senior_cash = _assemble_post_senior_cash_schedules(
        phase2b_result.periods,
        final_tax_cfads,
        final_senior_result,
    )
    handshake_probe_diag = ShareholderLoanDiagnostics(
        converged=False,
        is_authoritative=False,
        iteration_count=iteration,
        max_iterations=shl_input.maximum_iterations,
        convergence_tolerance_keur=shl_input.convergence_tolerance_keur,
        convergence_relative_tolerance=shl_input.convergence_relative_tolerance,
        max_closing_delta_keur=last_max_closing_delta,
        max_interest_delta_keur=last_max_interest_delta,
        termination_reason="FINAL_HANDSHAKE_PROBE",
    )
    handshake_shl_schedule = compute_shareholder_loan_schedules(
        phase2b_result.periods,
        shl_input,
        final_post_senior_cash.cash_available_for_shl_before_reserves_keur,
        diagnostics=handshake_probe_diag,
    )

    final_bank_tax_input = _merge_financing_tax_input(
        base_tax_input,
        final_senior_interest,
        final_shl_interest,
    )
    final_bank_tax = calculate_tax(bank_phase2a_result.periods, final_bank_tax_input)
    final_bank_cfads = calculate_canonical_cfads(
        bank_phase2a_result.periods,
        final_bank_tax.period_results,
    )
    final_base_tax_shl = {
        pi.period_index: pi.shl_interest_keur
        for pi in final_base_tax_input.period_interest
    }
    final_bank_tax_shl = {
        pi.period_index: pi.shl_interest_keur
        for pi in final_bank_tax_input.period_interest
    }
    authoritative_interest_vector = tuple(
        final_shl_interest.get(idx, 0.0) for idx in handshake_shl_schedule.period_indices
    )
    base_tax_interest_vector = tuple(
        final_base_tax_shl.get(idx, 0.0) for idx in handshake_shl_schedule.period_indices
    )
    bank_tax_interest_vector = tuple(
        final_bank_tax_shl.get(idx, 0.0) for idx in handshake_shl_schedule.period_indices
    )
    max_final_shl_interest_handshake_delta = max(
        _max_vector_delta(authoritative_interest_vector, handshake_shl_schedule.shl_gross_interest_keur),
        _max_vector_delta(authoritative_interest_vector, base_tax_interest_vector),
        _max_vector_delta(authoritative_interest_vector, bank_tax_interest_vector),
    )
    max_final_shl_closing_handshake_delta = _max_vector_delta(
        previous_shl.shl_closing_keur,
        handshake_shl_schedule.shl_closing_keur,
    )
    if not _field_converged_local(
        max_final_shl_interest_handshake_delta,
        0.0,
        shl_input.convergence_tolerance_keur,
        shl_input.convergence_relative_tolerance,
    ) or not _field_converged_local(
        max_final_shl_closing_handshake_delta,
        0.0,
        shl_input.convergence_tolerance_keur,
        shl_input.convergence_relative_tolerance,
    ):
        raise SeniorDebtNonConvergenceError(
            "FINAL_FINANCING_STATE_IS_SELF_CONSISTENT failed: "
            f"MAX_FINAL_SHL_INTEREST_HANDSHAKE_DELTA_KEUR="
            f"{max_final_shl_interest_handshake_delta:.12f}; "
            f"MAX_FINAL_SHL_CLOSING_HANDSHAKE_DELTA_KEUR="
            f"{max_final_shl_closing_handshake_delta:.12f}"
        )
    authoritative_diag = ShareholderLoanDiagnostics(
        converged=True,
        is_authoritative=True,
        iteration_count=iteration,
        max_iterations=shl_input.maximum_iterations,
        convergence_tolerance_keur=shl_input.convergence_tolerance_keur,
        convergence_relative_tolerance=shl_input.convergence_relative_tolerance,
        max_closing_delta_keur=last_max_closing_delta,
        max_interest_delta_keur=last_max_interest_delta,
        termination_reason="CONVERGED_FINAL_RECOMPUTE",
        max_final_shl_interest_handshake_delta_keur=max_final_shl_interest_handshake_delta,
        max_final_shl_closing_handshake_delta_keur=max_final_shl_closing_handshake_delta,
    )
    final_shl_schedule = compute_shareholder_loan_schedules(
        phase2b_result.periods,
        shl_input,
        final_post_senior_cash.cash_available_for_shl_before_reserves_keur,
        diagnostics=authoritative_diag,
    )
    debt_sizing_schedules = _build_debt_sizing_schedules_from_bank(
        bank_phase2a_result=bank_phase2a_result,
        final_bank_tax_result=final_bank_tax,
        final_bank_cfads_results=final_bank_cfads,
        senior_debt_result=final_senior_result,
    )
    result_schedules = _build_result_senior_debt_schedules(
        senior_debt_result=final_senior_result,
        final_tax_cfads=final_tax_cfads,
    )

    fingerprint = compute_senior_debt_fingerprint(inputs)
    evidence = phase2b_result.provenance.derivation_evidence + (
        DerivationEvidence(
            output_path="shareholder_loan.shl_gross_interest_keur",
            source_module="financial_engine.shl.production",
            source_function="compute_shareholder_loan_schedules",
            input_paths=("shareholder_loan", "post_senior_cash"),
            notes=(
                "SHL gross interest is included in TaxCalculationInput.period_interest.shl_interest_keur; "
                "TaxPolicy controls the tax-eligible SHL portion; "
                "CLEAN_ENGINE_NON_DEDUCTIBLE_SHL_TREATMENT; "
                "POST_SHL_CASH_IS_PRE_RESERVE",
            ),
        ),
        DerivationEvidence(
            output_path="senior_debt.debt_size_keur",
            source_module="financial_engine.orchestrator",
            source_function="_run_senior_debt_model_with_shl",
            input_paths=("senior_debt_inputs", "senior_debt_policy", "shareholder_loan"),
            notes=(
                "Senior debt is solved inside the SHL/tax fixed point; "
                "FINAL_FINANCING_STATE_RECOMPUTED_FROM_CONVERGED_SHL_AND_SENIOR_SCHEDULES",
            ),
        ),
    )
    provenance = EngineProvenance(
        engine_version=ENGINE_VERSION,
        run_path_id=SENIOR_DEBT_RUN_PATH_ID,
        input_fingerprint=fingerprint,
        derivation_evidence=evidence,
    )
    validation_issues = phase2b_result.validation_issues
    warnings = phase2b_result.warnings + tuple(
        f"{i.code} {i.path}: {i.message}" for i in validation_issues
        if i.severity.value == "WARNING"
    )
    return ProjectModelResult(
        provenance=provenance,
        periods=phase2b_result.periods,
        operating_schedules=phase2b_result.operating_schedules,
        tax_and_cfads=final_tax_cfads,
        senior_debt=result_schedules,
        debt_sizing=debt_sizing_schedules,
        post_senior_cash=final_post_senior_cash,
        shareholder_loan=final_shl_schedule,
        unavailable_sections=_PHASE_2C_UNAVAILABLE,
        validation_issues=validation_issues,
        warnings=warnings,
    )


def run_senior_debt_model(inputs: SeniorDebtModelInput) -> ProjectModelResult:
    """Phase 2C orchestrator: operating core + tax + canonical CFADS + senior debt.

    Two distinct economic cases flow through this orchestrator:
    - Base/equity case:  inputs.operating (e.g. P50 yield scenario)
    - Bank/debt-sizing case: derived from inputs.operating + inputs.debt_sizing_case
      (typically P90-10y yield scenario, per GENERIC_BANK_SIZING_DEFAULT_POLICY_IS_P90_10Y)

    The DSCR sizing constraint is applied to BANK CFADS (bank EBITDA − bank cash tax),
    not to Base CFADS. After the solver converges, the Base CFADS is recomputed using
    the final senior interest so that tax_and_cfads in the result reflects the correct
    Base-case post-interest CFADS.

    Calculation order:
      1.  Derive bank operating input from Base + DebtSizingCaseInput.
      2.  Run Phase 2B tax+CFADS model on Base (for base periods/provenance).
      3.  Run Phase 2A operating model on bank case (bank EBITDA for CFADS sizing).
      4.  Define tax_cfads_fn using bank periods (sizing CFADS from bank EBITDA).
      5.  Call solve_senior_debt() with bank-CFADS callback.
      6.  Recompute Base CFADS with final senior interest (authoritative base result).
      7.  Assemble DebtSizingSchedules from bank schedules.
      8.  Assemble SeniorDebtSchedules result.
      9.  Attach Phase 2C provenance.

    Non-converged results raise SeniorDebtNonConvergenceError.
    """
    if inputs.shareholder_loan is not None:
        return _run_senior_debt_model_with_shl(inputs)

    from financial_engine.inputs import TaxCalculationInput, PeriodInterestInput
    from financial_engine.tax.engine import calculate_tax
    from financial_engine.cfads import calculate_canonical_cfads
    from financial_engine.senior_debt.solver import solve_senior_debt
    from financial_engine.senior_debt.policy import SeniorDebtPolicy
    from financial_engine.senior_debt.inputs import SeniorDebtInputs

    policy: SeniorDebtPolicy = inputs.senior_debt_policy  # type: ignore[assignment]
    sd_inputs: SeniorDebtInputs = inputs.senior_debt_inputs  # type: ignore[assignment]

    # Step 1: Derive bank operating input.
    bank_op = derive_debt_sizing_operating_input(inputs.operating, inputs.debt_sizing_case)

    # Step 2: Phase 2B base run (base operating + base tax, any pre-existing interest).
    phase2b_inputs = TaxCfadsModelInput(operating=inputs.operating, tax=inputs.tax)
    phase2b_result = run_tax_cfads_model(phase2b_inputs)

    # Step 3: Bank Phase 2A result — bank EBITDA is the CFADS sizing input.
    bank_phase2a_result = run_operating_model(bank_op)

    base_tax_input = inputs.tax

    def tax_cfads_fn(
        senior_interest_by_period: dict[int, float],
    ) -> tuple[dict[int, float], dict[int, float]]:
        """Rebuild bank-case tax + CFADS with updated senior interest on each iteration.

        Uses bank operating periods (bank_phase2a_result.periods) so that EBITDA
        entering the tax base reflects the bank-case yield scenario, not Base.
        """
        # Merge solver-provided senior interest into PeriodInterestInput.
        merged_interest: dict[int, "PeriodInterestInput"] = {}
        for pi in base_tax_input.period_interest:
            merged_interest[pi.period_index] = pi
        for idx, senior_keur in senior_interest_by_period.items():
            existing = merged_interest.get(idx)
            if existing is not None:
                merged_interest[idx] = PeriodInterestInput(
                    period_index=idx,
                    senior_interest_keur=senior_keur,
                    shl_interest_keur=existing.shl_interest_keur,
                    other_interest_keur=existing.other_interest_keur,
                )
            else:
                merged_interest[idx] = PeriodInterestInput(
                    period_index=idx,
                    senior_interest_keur=senior_keur,
                )

        updated_tax_input = TaxCalculationInput(
            policy=base_tax_input.policy,
            opening_loss_vintages=base_tax_input.opening_loss_vintages,
            period_interest=tuple(merged_interest.values()),
            period_adjustments=base_tax_input.period_adjustments,
        )
        # Tax and CFADS computed against bank periods (bank EBITDA drives taxable income).
        tax_result = calculate_tax(bank_phase2a_result.periods, updated_tax_input)
        cfads_results = calculate_canonical_cfads(bank_phase2a_result.periods, tax_result.period_results)
        cfads_by_period = {cr.period_index: cr.cfads_keur for cr in cfads_results}
        cash_tax_by_period = {
            pr.period_index: pr.cash_tax_keur for pr in tax_result.period_results
        }
        return cfads_by_period, cash_tax_by_period

    # Step 5: Fixed-point solver against bank periods.
    debt_start = policy.repayment_start_period_index
    debt_end = policy.maturity_period_index
    debt_periods = tuple(
        p for p in bank_phase2a_result.periods
        if p.is_operation and debt_start <= p.period_index <= debt_end
    )
    sd_result = solve_senior_debt(
        policy=policy,
        inputs=sd_inputs,
        periods=debt_periods,
        tax_cfads_fn=tax_cfads_fn,
    )

    # Block non-authoritative results from reaching downstream modules.
    if not sd_result.diagnostics.is_authoritative:
        from financial_engine.senior_debt.models import SeniorDebtNonConvergenceError
        raise SeniorDebtNonConvergenceError(
            f"Senior debt solver terminated with non-authoritative result: "
            f"termination_reason={sd_result.diagnostics.termination_reason!r}, "
            f"iteration_count={sd_result.diagnostics.iteration_count}, "
            f"max_abs_diff={sd_result.diagnostics.maximum_absolute_difference_keur:.6f} kEUR. "
            f"Downstream waterfall/FS/returns code must not receive non-authoritative debt results."
        )

    # Step 6: Recompute Base CFADS with final senior interest (authoritative base result).
    # The solver converged on bank CFADS; now update the Base tax/CFADS using the same
    # final senior interest so that result.tax_and_cfads is the correct Base CFADS.
    final_senior_interest = dict(zip(sd_result.period_indices, sd_result.senior_interest_keur))
    merged_base: dict[int, "PeriodInterestInput"] = {}
    for pi in base_tax_input.period_interest:
        merged_base[pi.period_index] = pi
    for idx, senior_keur in final_senior_interest.items():
        existing = merged_base.get(idx)
        if existing is not None:
            merged_base[idx] = PeriodInterestInput(
                period_index=idx,
                senior_interest_keur=senior_keur,
                shl_interest_keur=existing.shl_interest_keur,
                other_interest_keur=existing.other_interest_keur,
            )
        else:
            merged_base[idx] = PeriodInterestInput(
                period_index=idx,
                senior_interest_keur=senior_keur,
            )
    base_updated_tax = TaxCalculationInput(
        policy=base_tax_input.policy,
        opening_loss_vintages=base_tax_input.opening_loss_vintages,
        period_interest=tuple(merged_base.values()),
        period_adjustments=base_tax_input.period_adjustments,
    )
    base_tax_result = calculate_tax(phase2b_result.periods, base_updated_tax)
    base_cfads_results = calculate_canonical_cfads(
        phase2b_result.periods, base_tax_result.period_results
    )
    final_tax_cfads = _assemble_tax_cfads_schedules(
        phase2b_result, base_tax_result, base_tax_result.period_results, base_cfads_results
    )

    # Step 7: Assemble DebtSizingSchedules from explicit final bank recomputation.
    # FINAL_BANK_CFADS_RECOMPUTED_FROM_FINAL_SENIOR_INTEREST:
    # Post-solver explicit recompute uses final senior interest from sd_result;
    # this is the authoritative bank CFADS source.
    import math as _math
    _sd_service_by_idx: dict[int, float] = dict(
        zip(sd_result.period_indices, sd_result.senior_debt_service_keur)
    )
    _merged_bank_final: dict[int, "PeriodInterestInput"] = {}
    for pi in base_tax_input.period_interest:
        _merged_bank_final[pi.period_index] = pi
    for _bidx, _bseni in final_senior_interest.items():
        _bexist = _merged_bank_final.get(_bidx)
        if _bexist is not None:
            _merged_bank_final[_bidx] = PeriodInterestInput(
                period_index=_bidx,
                senior_interest_keur=_bseni,
                shl_interest_keur=_bexist.shl_interest_keur,
                other_interest_keur=_bexist.other_interest_keur,
            )
        else:
            _merged_bank_final[_bidx] = PeriodInterestInput(
                period_index=_bidx,
                senior_interest_keur=_bseni,
            )
    _bank_final_tax_input = TaxCalculationInput(
        policy=base_tax_input.policy,
        opening_loss_vintages=base_tax_input.opening_loss_vintages,
        period_interest=tuple(_merged_bank_final.values()),
        period_adjustments=base_tax_input.period_adjustments,
    )
    final_bank_tax_result = calculate_tax(bank_phase2a_result.periods, _bank_final_tax_input)
    final_bank_cfads_results = calculate_canonical_cfads(
        bank_phase2a_result.periods, final_bank_tax_result.period_results
    )
    _final_bank_cash_tax_by_idx = {
        pr.period_index: pr.cash_tax_keur for pr in final_bank_tax_result.period_results
    }
    _final_bank_cfads_by_idx = {
        cr.period_index: cr.cfads_keur for cr in final_bank_cfads_results
    }
    _ops_indices = bank_phase2a_result.operating_schedules.period_indices
    _bank_sizing_dscr: tuple[float | None, ...] = tuple(
        (
            _final_bank_cfads_by_idx.get(i, 0.0) / _sd_service_by_idx[i]
            if i in _sd_service_by_idx
            and _sd_service_by_idx[i] > 0.0
            and _math.isfinite(_final_bank_cfads_by_idx.get(i, 0.0))
            else None
        )
        for i in _ops_indices
    )
    # SOLVER_BANK_DSCR_HANDSHAKE_PROOF (C3B3D2B4.2):
    # Capture solver-internal Bank DSCR at convergence (sd_result.senior_dscr = bank_cfads/senior_ds
    # from the solver's fixed-point iterations).  Mapped to _ops_indices; None for periods outside
    # the solver's period_indices (e.g. construction periods not in the debt schedule).
    _solver_dscr_by_idx: dict[int, float | None] = dict(
        zip(sd_result.period_indices, sd_result.senior_dscr)
    )
    _solver_bank_dscr: tuple[float | None, ...] = tuple(
        _solver_dscr_by_idx.get(i, None) for i in _ops_indices
    )
    debt_sizing_schedules: DebtSizingSchedules | None = DebtSizingSchedules(
        period_indices=_ops_indices,
        bank_production_mwh=bank_phase2a_result.operating_schedules.production_mwh,
        bank_revenue_keur=bank_phase2a_result.operating_schedules.revenue_keur,
        bank_opex_keur=bank_phase2a_result.operating_schedules.opex_keur,
        bank_ebitda_keur=bank_phase2a_result.operating_schedules.ebitda_keur,
        bank_cash_tax_keur=tuple(_final_bank_cash_tax_by_idx.get(i, 0.0) for i in _ops_indices),
        bank_cfads_keur=tuple(cr.cfads_keur for cr in final_bank_cfads_results),
        bank_sizing_dscr=_bank_sizing_dscr,
        solver_bank_dscr=_solver_bank_dscr,
    )

    # Step 8: Assemble result-layer SeniorDebtSchedules.
    # base_dscr = Base CFADS / senior DS per period (Base actual DSCR, NOT Bank sizing DSCR).
    # final_tax_cfads.cfads_keur is the authoritative Base CFADS (recomputed with final interest).
    import math as _math
    _base_cfads_by_idx: dict[int, float] = dict(
        zip(final_tax_cfads.period_indices, final_tax_cfads.cfads_keur)
    )
    _base_dscr: tuple[float | None, ...] = tuple(
        (
            _base_cfads_by_idx.get(idx, 0.0) / ds
            if (ds := _sd_service_by_idx.get(idx, 0.0)) > 0.0
            and _math.isfinite(_base_cfads_by_idx.get(idx, 0.0))
            else None
        )
        for idx in sd_result.period_indices
    )
    diag_dict = {
        "converged": sd_result.diagnostics.converged,
        "is_authoritative": sd_result.diagnostics.is_authoritative,
        "iteration_count": sd_result.diagnostics.iteration_count,
        "initial_debt_guess_keur": sd_result.diagnostics.initial_debt_guess_keur,
        "final_debt_size_keur": sd_result.diagnostics.final_debt_size_keur,
        "maximum_absolute_difference_keur": sd_result.diagnostics.maximum_absolute_difference_keur,
        "maximum_relative_difference": sd_result.diagnostics.maximum_relative_difference,
        "binding_constraint": sd_result.diagnostics.binding_constraint,
        "termination_reason": sd_result.diagnostics.termination_reason,
    }
    result_schedules = _SeniorDebtSchedulesResult(
        period_indices=sd_result.period_indices,
        senior_debt_opening_keur=sd_result.senior_debt_opening_keur,
        senior_interest_keur=sd_result.senior_interest_keur,
        senior_principal_keur=sd_result.senior_principal_keur,
        senior_debt_service_keur=sd_result.senior_debt_service_keur,
        senior_debt_closing_keur=sd_result.senior_debt_closing_keur,
        base_dscr=_base_dscr,
        debt_size_keur=sd_result.debt_size_keur,
        binding_constraint=sd_result.binding_constraint,
        diagnostics=diag_dict,
    )

    # Build PostSeniorCashSchedules: Base CFADS authority for pre-reserve downstream cash.
    # All model periods (construction + operating). Bank CFADS is NOT read here.
    # CONSTRUCTION_SHL_AVAILABLE_CASH_IS_ZERO_BY_CONTRACT: construction is PIK.
    _period_is_constr: dict[int, bool] = {
        p.period_index: p.is_construction for p in phase2b_result.periods
    }
    _all_period_indices = tuple(p.period_index for p in phase2b_result.periods)
    _cash_after: list[float] = []
    _cash_avail: list[float] = []
    for _idx in _all_period_indices:
        _bcfads = _base_cfads_by_idx.get(_idx, 0.0)
        _sds = _sd_service_by_idx.get(_idx, 0.0)
        _after = _bcfads - _sds
        _cash_after.append(_after)
        _cash_avail.append(
            0.0 if _period_is_constr.get(_idx, False) else max(0.0, _after)
        )
    _base_cfads_all = tuple(_base_cfads_by_idx.get(i, 0.0) for i in _all_period_indices)
    _sd_service_all = tuple(_sd_service_by_idx.get(i, 0.0) for i in _all_period_indices)
    post_senior_cash = PostSeniorCashSchedules(
        period_indices=_all_period_indices,
        base_cfads_keur=_base_cfads_all,
        senior_debt_service_keur=_sd_service_all,
        cash_after_senior_before_reserves_keur=tuple(_cash_after),
        cash_available_for_shl_before_reserves_keur=tuple(_cash_avail),
    )

    # Step 9: Phase 2C provenance.
    fingerprint = compute_senior_debt_fingerprint(inputs)
    evidence = phase2b_result.provenance.derivation_evidence + (
        DerivationEvidence(
            output_path="senior_debt.senior_interest_keur",
            source_module="financial_engine.senior_debt.interest",
            source_function="period_interest",
            input_paths=("senior_debt_inputs.period_rates", "senior_debt_policy"),
            notes=("interest = opening_balance × annual_rate × day_count_fraction",),
        ),
        DerivationEvidence(
            output_path="senior_debt.senior_principal_keur",
            source_module="financial_engine.senior_debt.sculpting",
            source_function="build_schedule",
            input_paths=(
                "debt_sizing.bank_cfads_keur",
                "senior_debt_inputs.period_rates",
                "senior_debt_inputs.period_dscr_targets",
                "senior_debt_inputs.period_debt_service_availability",
                "senior_debt_policy.target_dscr",
                "senior_debt_policy.day_count_convention",
            ),
            notes=(
                "C3B3A algorithm: "
                "resolved_target_dscr[p] = period_dscr_targets[p].target_dscr "
                "if p in period_dscr_targets else policy.target_dscr; "
                "resolved_availability[p] = period_debt_service_availability[p].availability_fraction "
                "if p in period_debt_service_availability else 1.0; "
                "allowed_debt_service[p] = max(0, bank_cfads[p] / resolved_target_dscr[p]) "
                "* resolved_availability[p]; "
                "principal[p] = min(opening_balance[p], max(0, allowed_debt_service[p] - interest[p]))",
            ),
        ),
        DerivationEvidence(
            output_path="post_senior_cash",
            source_module="financial_engine.orchestrator",
            source_function="run_senior_debt_model",
            input_paths=(
                "tax_and_cfads.cfads_keur",
                "senior_debt.senior_debt_service_keur",
            ),
            notes=(
                "post_senior_cash uses Base CFADS (tax_and_cfads.cfads_keur), NOT bank CFADS; "
                "cash_after_senior = base_cfads - senior_ds (signed); "
                "cash_available_for_shl = max(0, cash_after_senior); "
                "DSRA_NOT_IMPLEMENTED: pre-reserve figures; DSRA ordering unresolved",
            ),
        ),
        DerivationEvidence(
            output_path="senior_debt.debt_size_keur",
            source_module="financial_engine.senior_debt.solver",
            source_function="solve_senior_debt",
            input_paths=("senior_debt_inputs", "senior_debt_policy"),
            notes=(
                f"fixed-point sizing; termination={sd_result.diagnostics.termination_reason}; "
                f"iterations={sd_result.diagnostics.iteration_count}",
            ),
        ),
    )
    provenance = EngineProvenance(
        engine_version=ENGINE_VERSION,
        run_path_id=SENIOR_DEBT_RUN_PATH_ID,
        input_fingerprint=fingerprint,
        derivation_evidence=evidence,
    )

    validation_issues = phase2b_result.validation_issues
    warnings = phase2b_result.warnings + tuple(
        f"{i.code} {i.path}: {i.message}" for i in validation_issues
        if i.severity.value == "WARNING"
    )

    return ProjectModelResult(
        provenance=provenance,
        periods=phase2b_result.periods,
        operating_schedules=phase2b_result.operating_schedules,
        tax_and_cfads=final_tax_cfads,
        senior_debt=result_schedules,
        debt_sizing=debt_sizing_schedules,
        post_senior_cash=post_senior_cash,
        unavailable_sections=_PHASE_2C_UNAVAILABLE,
        validation_issues=validation_issues,
        warnings=warnings,
    )
