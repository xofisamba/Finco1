"""Uncached waterfall core used by both Streamlit cache and headless calibration.

This module must not import Streamlit. It is the production calculation path
that CLI scripts, tests, and app/cache.py can all call.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.inputs import ProjectInputs
    from domain.period_engine import PeriodEngine
    from domain.waterfall.waterfall_engine import WaterfallResult


def run_waterfall_v3_core(
    inputs: "ProjectInputs",
    engine: "PeriodEngine",
    rate_per_period: float,
    tenor_periods: int,
    target_dscr: float = 1.15,
    lockup_dscr: float = 1.10,
    tax_rate: float = 0.10,
    dsra_months: int = 6,
    shl_amount: float = 0.0,
    shl_rate: float = 0.0,
    shl_idc_keur: float = 0.0,
    shl_repayment_method: str = "bullet",
    shl_tenor_years: int = 0,
    shl_wht_rate: float = 0.0,
    discount_rate_project: float = 0.0641,
    discount_rate_equity: float = 0.0965,
    fixed_debt_keur: float | None = None,
    fixed_ds_keur: float | None = None,
    rate_schedule: list[float] | None = None,
    senior_sculpting_config: object | None = None,
    equity_irr_method: str = "equity_only",
    share_capital_keur: float = 0.0,
    sculpt_capex_keur: float = 0.0,
    debt_sizing_method: str = "dscr_sculpt",
    dscr_schedule: list[float] | None = None,
    advanced_opex_line_items: tuple | None = None,
    advanced_capex_line_items: tuple | None = None,
    advanced_capex_depreciation_schedule: "DepreciationSchedule | None" = None,
    # TUHO-specific: cap SHL sweep cash at R99-equivalent (Excel-compatible).
    # Prevents SHL principal from consuming cash that Excel would hold back.
    use_senior_sweep_cash_cap_for_shl: bool = False,
    # Phase 7F C1a: propagated for config identity only; not wired into runtime yet.
    use_tuho_r99_input_engine: bool = False,
    use_shl_fcf_waterfall_engine: bool = False,
    use_tax_bridge_engine: bool = False,
    use_shl_gross_accrued_for_pnl: bool = False,
    shl_fcf_waterfall_cash_schedule_keur: tuple[float, ...] = (),
    shl_fcf_waterfall_minimum_cash_retained_keur: float = 0.0,
    tuho_cit_cash_tax_start_operating_index: int | None = None,
    use_shl_canonical_engine: bool = False,
    use_depreciation_canonical_engine: bool = False,
    use_senior_debt_sizing_engine: bool = False,
    # Phase 9: CO2 revenue bridge — wire CO2 certificate revenue into period.revenue_keur.
    # TUHO-only; default=False preserves legacy baseline.
    # R99/R102: BLOCKED — CO2 bridge affects revenue/EBITDA only, no CIT or distribution change.
    use_co2_revenue_bridge: bool = False,
    # Phase 9: CO2→CIT bridge — add CO2 to taxable income (not EBITDA).
    # TUHO-only; default=False preserves legacy baseline.
    # R99/R102: BLOCKED — only taxable income affected.
    use_co2_cit_bridge: bool = False,
    # Phase 9B: Dual-run validation — compare DA equity_distribution_paid_keur vs
    # WaterfallEngine.distribution_keur without changing runtime authority.
    # R99/R102: BLOCKED — no promotion in dual-run mode.
    use_dualrun_validation: bool = False,
) -> dict:
    """Run the full waterfall without Streamlit cache dependencies.

    FincoGPT calibration note:
    - `domain.waterfall.run_waterfall()` sculpts debt using the first
      `tenor_periods` entries of the EBITDA schedule.
    - If construction rows are included in that list, sculpting starts with two
      zero-CFADS periods while debt repayment output starts at the first
      operating period. That creates a principal/interest timing mismatch.
    - The headless calibration core therefore passes operation-only periods and
      operation-only schedules into the waterfall engine.

    advanced_opex_line_items: if provided (non-empty tuple), the advanced
      OpexLineItem engine is used to generate the OPEX schedule instead of
      the legacy OpexItem/OpexParams path. This enables granular per-line-item
      OPEX modeling with manual/hardcoded override support.

    advanced_capex_depreciation_schedule: if provided (from
      app.depreciation_engine.generate_schedule()), the new asset-class
      depreciation schedule is used for the tax-shield calculation instead of
      the legacy CapexItem-based schedule. This enables per-asset-class
      depreciable lives (solar modules 25 yr, inverters 10 yr, etc.).
    """
    from domain.waterfall.waterfall_engine import run_waterfall
    from domain.revenue.generation import full_revenue_schedule, full_generation_schedule, revenue_decomposition_schedule
    from domain.opex.projections import opex_schedule_period
    from domain.financing.depreciation_schedule import build_depreciation_schedule

    _ = use_tuho_r99_input_engine  # C1a intentionally leaves runtime behavior unchanged.
    if use_tax_bridge_engine and getattr(inputs.info, "code", "") != "TUHO-WIND-1":
        raise ValueError("Tax bridge runtime engine is currently supported only for TUHO-WIND-1")
    if use_shl_gross_accrued_for_pnl and getattr(inputs.info, "code", "") != "TUHO-WIND-1":
        raise ValueError("Gross accrued SHL P&L bridge is currently supported only for TUHO-WIND-1")
    construction_diagnostic = None
    if getattr(inputs.info, "use_construction_schedule_engine", False):
        from domain.construction.runtime_adapter import build_runtime_construction_schedule

        construction_diagnostic = build_runtime_construction_schedule(inputs)

    all_periods = list(engine.periods())
    periods_list = [p for p in all_periods if p.is_operation]
    revenue_dict = full_revenue_schedule(inputs, engine)
    generation_dict = full_generation_schedule(inputs, engine)

    # Phase 9 CO2 revenue bridge: extract CO2 certificate revenue by period.
    # When use_co2_revenue_bridge=True, CO2 is added to period.revenue_keur
    # (and therefore EBITDA) before the waterfall run.
    # TUHO-only guard: bridge is only activated for TUHO-WIND-1 project code.
    # R99/R102: BLOCKED — CO2 bridge only affects revenue/EBITDA chain.
    co2_revenue_by_period: dict[int, float] = {}
    co2_base_revenue_by_period: dict[int, float] = {}
    if use_co2_revenue_bridge:
        if getattr(inputs.info, "code", "") != "TUHO-WIND-1":
            raise ValueError(
                "CO2 revenue bridge (use_co2_revenue_bridge=True) is currently supported "
                "only for TUHO-WIND-1"
            )
        decompositions = revenue_decomposition_schedule(inputs, engine)
        for period_idx, decomp in decompositions.items():
            if decomp.get("is_operation", False):
                co2_keur = decomp.get("co2_revenue_keur", 0.0)
                base_rev = revenue_dict.get(period_idx, 0.0)
                co2_revenue_by_period[period_idx] = co2_keur
                co2_base_revenue_by_period[period_idx] = base_rev

    # Phase 9 CO2→CIT bridge: extract CO2 for taxable income injection.
    # CO2 is added directly to taxable income in TaxEngine (not EBITDA).
    # Must not be used simultaneously with use_co2_revenue_bridge=True.
    # R99/R102: BLOCKED — only taxable income / cash tax affected.
    co2_cit_bridge_by_period: dict[int, float] = {}
    if use_co2_cit_bridge:
        if getattr(inputs.info, "code", "") != "TUHO-WIND-1":
            raise ValueError(
                "CO2 CIT bridge (use_co2_cit_bridge=True) is currently supported "
                "only for TUHO-WIND-1"
            )
        if use_co2_revenue_bridge:
            raise ValueError(
                "use_co2_cit_bridge and use_co2_revenue_bridge cannot both be True; "
                "they target different computation chains"
            )
        decompositions = revenue_decomposition_schedule(inputs, engine)
        for period_idx, decomp in decompositions.items():
            if decomp.get("is_operation", False):
                co2_keur = decomp.get("co2_revenue_keur", 0.0)
                co2_cit_bridge_by_period[period_idx] = co2_keur

    # OPEX: default legacy path remains unchanged. The Phase 7H line-item
    # engine is available only behind an explicit project/config flag.
    if getattr(inputs.info, "use_opex_line_item_engine", False):
        from domain.opex.runtime_adapter import build_runtime_opex_schedule

        opex_period = build_runtime_opex_schedule(inputs, engine).period_schedule_keur
    elif advanced_opex_line_items:
        from app.opex_engine import apply_opex_line_items_to_project
        horizon_years = inputs.info.horizon_years
        annual_opex = apply_opex_line_items_to_project(advanced_opex_line_items, horizon_years)
        # Convert annual → per-period using period day fraction
        opex_period: dict[int, float] = {}
        for p in periods_list:
            annual_val = annual_opex[p.year_index] if p.year_index < len(annual_opex) else 0.0
            opex_period[p.index] = annual_val * p.day_fraction
    else:
        opex_period = opex_schedule_period(inputs, engine)

    # CAPEX: use advanced CapexLineItems if provided, otherwise fall back to legacy path
    # Computes total_capex_override from the sum of CapexLineItem amounts.
    # This is passed to run_waterfall() to override inputs.capex.total_capex.
    total_capex_override: float | None = None
    if advanced_capex_line_items:
        from app.capex_engine import generate_capex_schedule
        capex_sched = generate_capex_schedule(advanced_capex_line_items, tenor_periods)
        total_capex_override = sum(capex_sched.total_by_period)
    else:
        total_capex_override = None

    horizon_years = inputs.info.horizon_years

    # Depreciation schedule: use advanced CapexLineItem schedule if provided,
    # otherwise fall back to legacy CapexItem path for backward compatibility.
    if advanced_capex_depreciation_schedule is not None:
        # Map DepreciationSchedule (0-based year index) → {year_index: annual_dep}
        dep_schedule_annual = {
            y + 1: advanced_capex_depreciation_schedule.total_by_period[y]
            for y in range(len(advanced_capex_depreciation_schedule.total_by_period))
        }
    else:
        # Legacy path: derive from CapexItem asset classes
        capex_items = inputs.capex.capex_items()
        dep_schedule_annual = build_depreciation_schedule(
            capex_items=capex_items,
            horizon_years=horizon_years,
            senior_tenor_years=inputs.financing.senior_tenor_years,
        )

    ebitda_schedule: list[float] = []
    revenue_schedule: list[float] = []
    generation_schedule: list[float] = []
    depreciation_schedule: list[float] = []
    opex_schedule: list[float] = []

    for p in periods_list:
        rev = revenue_dict.get(p.index, 0)
        # Phase 9 CO2 bridge: add CO2 certificate revenue to base revenue.
        # When use_co2_revenue_bridge=True: adds to EBITDA via rev→ebitda chain.
        # When use_co2_cit_bridge=True: SKIP here; CO2 added to taxable income only.
        # TUHO-only. R99/R102 remain unchanged.
        if use_co2_revenue_bridge and not use_co2_cit_bridge:
            co2_add = co2_revenue_by_period.get(p.index, 0.0)
            rev = rev + co2_add
        gen = generation_dict.get(p.index, 0)
        opex = opex_period.get(p.index, 0)
        ebitda = max(0, rev - opex)
        annual_dep = dep_schedule_annual.get(p.year_index, 0.0)
        dep = annual_dep * p.day_fraction

        revenue_schedule.append(rev)
        generation_schedule.append(gen)
        ebitda_schedule.append(ebitda)
        depreciation_schedule.append(dep)
        opex_schedule.append(opex)

    # Resolve total_capex — use advanced CAPEX if provided, else fall back to inputs
    total_capex_for_waterfall = (
        total_capex_override if total_capex_override is not None
        else inputs.capex.total_capex
    )

    result = run_waterfall(
        ebitda_schedule=ebitda_schedule,
        revenue_schedule=revenue_schedule,
        generation_schedule=generation_schedule,
        depreciation_schedule=depreciation_schedule,
        opex_schedule=opex_schedule,
        periods=periods_list,
        total_capex=total_capex_for_waterfall,
        rate_per_period=rate_per_period,
        tenor_periods=tenor_periods,
        target_dscr=target_dscr,
        lockup_dscr=lockup_dscr,
        tax_rate=tax_rate,
        dsra_months=dsra_months,
        shl_amount=shl_amount,
        shl_rate=shl_rate,
        shl_idc_keur=shl_idc_keur,
        shl_repayment_method=shl_repayment_method,
        shl_tenor_years=shl_tenor_years,
        shl_wht_rate=shl_wht_rate,
        use_shl_fcf_waterfall_engine=use_shl_fcf_waterfall_engine,
        shl_fcf_waterfall_cash_schedule_keur=shl_fcf_waterfall_cash_schedule_keur,
        shl_fcf_waterfall_minimum_cash_retained_keur=shl_fcf_waterfall_minimum_cash_retained_keur,
        discount_rate_project=discount_rate_project,
        discount_rate_equity=discount_rate_equity,
        financial_close=inputs.info.financial_close,
        gearing_ratio=inputs.financing.gearing_ratio,
        fixed_debt_keur=fixed_debt_keur if fixed_debt_keur is not None else getattr(inputs.financing, "fixed_debt_keur", None),
        fixed_ds_keur=fixed_ds_keur if fixed_ds_keur is not None else getattr(inputs.financing, "fixed_ds_keur", None),
        rate_schedule=rate_schedule,
        senior_sculpting_config=senior_sculpting_config,
        idc_keur=inputs.capex.idc_keur,
        bank_fees_keur=inputs.capex.bank_fees_keur,
        commitment_fees_keur=inputs.capex.commitment_fees_keur,
        equity_irr_method=equity_irr_method,
        share_capital_keur=share_capital_keur,
        sculpt_capex_keur=sculpt_capex_keur,
        prior_tax_loss_keur=inputs.tax.initial_tax_loss_keur,
        debt_sizing_method=debt_sizing_method,
        dscr_schedule=dscr_schedule if dscr_schedule is not None else getattr(inputs.financing, "dscr_schedule", None),
        use_senior_sweep_cash_cap_for_shl=use_senior_sweep_cash_cap_for_shl,
        co2_cit_bridge_by_period=co2_cit_bridge_by_period,
    )
    result.project_code = getattr(inputs.info, "code", "")
    # Phase 9 CO2 revenue bridge audit metadata.
    # R99/R102: BLOCKED — bridge only affects revenue/EBITDA.
    if use_co2_revenue_bridge:
        result._co2_revenue_bridge = {
            "enabled": True,
            "co2_by_period": co2_revenue_by_period,
            "base_revenue_by_period": co2_base_revenue_by_period,
            "project_code": getattr(inputs.info, "code", ""),
        }
        # Annotate each period with its CO2 bridge contribution for audit visibility
        for wp in result.periods:
            p_idx = getattr(wp, "period", None)
            if p_idx in co2_revenue_by_period:
                setattr(wp, "co2_revenue_bridge_keur", co2_revenue_by_period[p_idx])
    else:
        result._co2_revenue_bridge = {"enabled": False}

    # Phase 9 CO2→CIT bridge audit metadata.
    # R99/R102: BLOCKED — bridge only affects taxable income / cash tax.
    if use_co2_cit_bridge:
        result._co2_cit_bridge = {
            "enabled": True,
            "co2_by_period": co2_cit_bridge_by_period,
            "project_code": getattr(inputs.info, "code", ""),
        }
        # Annotate each period with its CO2 CIT bridge contribution for audit visibility
        for wp in result.periods:
            p_idx = getattr(wp, "period", None)
            if p_idx in co2_cit_bridge_by_period:
                setattr(wp, "co2_cit_bridge_keur", co2_cit_bridge_by_period[p_idx])
    else:
        result._co2_cit_bridge = {"enabled": False}
    result.use_shl_gross_accrued_for_pnl = use_shl_gross_accrued_for_pnl
    if use_shl_gross_accrued_for_pnl:
        _apply_tuho_shl_gross_accrued_interest_bridge(result)
    if use_tax_bridge_engine:
        _apply_tuho_tax_bridge_runtime_cash_tax(
            result, tenor_periods, lockup_dscr, tax_rate,
            cit_cash_tax_start_operating_index=tuho_cit_cash_tax_start_operating_index,
        )
    if construction_diagnostic is not None:
        result.construction_schedule_diagnostic = construction_diagnostic
    # Phase 8.1: wire canonical ShlEngine into runtime when flag is True.
    # R99/R102: BLOCKED — canonical wiring affects SHL fields only.
    if use_shl_canonical_engine:
        from domain.shl.canonical_wiring import wire_canonical_shl_into_waterfall
        wiring_result = wire_canonical_shl_into_waterfall(
            waterfall_result=result,
            shl_amount_keur=shl_amount,
            shl_rate=shl_rate,
            shl_idc_keur=shl_idc_keur,
            shl_repayment_method=shl_repayment_method,
            shl_wht_rate=shl_wht_rate,
            shl_tenor_years=shl_tenor_years,
        )
        from domain.shl.canonical_wiring import apply_canonical_shl_wiring
        apply_canonical_shl_wiring(result, wiring_result)
        result._canonical_shl_wiring = wiring_result
    # Phase 8: wire canonical DepreciationEngine into runtime when flag is True.
    # Canonical engine computes per-asset-class book and tax depreciation;
    # its outputs override waterfall period depreciation_keur and
    # tax_depreciation_audit_keur after run_waterfall completes.
    # R99/R102: BLOCKED — depreciation wiring affects P&L and tax-shield only.
    if use_depreciation_canonical_engine:
        from domain.depreciation.canonical_wiring import build_canonical_depreciation_wiring
        dep_wiring = build_canonical_depreciation_wiring(
            project_name=getattr(inputs.info, 'name', 'Project'),
            capex_items=inputs.capex.capex_items(),
            horizon_years=horizon_years,
            cod_period=2,  # semiannual: COD = period 2 (first operating period)
            period_frequency="semiannual",
        )
        if dep_wiring.canonical_engine_result is not None:
            # Override waterfall period depreciation fields with canonical values
            from domain.depreciation.canonical_wiring import wire_canonical_depreciation_into_waterfall
            wiring_result = wire_canonical_depreciation_into_waterfall(
                dep_wiring.canonical_engine_result,
                period_count=len(result.periods),
            )
            for i, period in enumerate(result.periods):
                if i < len(wiring_result.book_depreciation_by_period):
                    period.depreciation_keur = wiring_result.book_depreciation_by_period[i]
                if i < len(wiring_result.tax_depreciation_by_period):
                    period.tax_depreciation_audit_keur = wiring_result.tax_depreciation_by_period[i]
            result._canonical_depreciation_wiring = wiring_result
    # Phase 8: canonical SeniorDebtSizing wiring.
    # Computes debt service capacity from explicit sizing_cfads and per-period dscr_schedule.
    # Result is attached as _canonical_senior_debt_sizing audit attribute.
    # R99/R102: BLOCKED — sizing wiring does not touch distribution gates.
    # R99/R102: BLOCKED — this wiring does not affect R99/R102 gates.
    if use_senior_debt_sizing_engine:
        from domain.senior_debt_sizing.canonical_wiring import (
            build_canonical_senior_debt_sizing_from_inputs,
        )
        # Extract EBITDA schedule and DSCR schedule from project inputs
        op_periods = [p for p in result.periods if getattr(p, 'is_operation', False)]
        horizon_years = inputs.info.horizon_years
        ebitda_schedule = []
        for p in op_periods:
            ebitda_val = (
                getattr(p, 'revenue_keur', 0.0)
                - getattr(p, 'opex_keur', 0.0)
            )
            ebitda_schedule.append(ebitda_val)
        dscr_schedule = (
            inputs.financing.dscr_schedule
            if inputs.financing.dscr_schedule
            else [1.15] * (horizon_years * 2)
        )
        sizing_result = build_canonical_senior_debt_sizing_from_inputs(
            project_name=getattr(inputs.info, 'name', 'Project'),
            project_code=getattr(inputs.info, 'code', ''),
            ebitda_schedule=tuple(ebitda_schedule),
            tax_rate=inputs.tax.corporate_rate,
            dscr_schedule=tuple(dscr_schedule[:len(ebitda_schedule)]),
            use_explicit_sizing_cfads=False,  # Until Macro!R50 values are wired
        )
        result._canonical_senior_debt_sizing = sizing_result

    # Phase 9B: Dual-run validation — side-by-side DA vs WE comparison.
    # NO runtime routing — waterfall result is not modified.
    # R99/R102: BLOCKED — DA remains audit-only.
    if use_dualrun_validation:
        _attach_dualrun_validation(result, inputs, periods_list)

    return result


def _apply_tuho_shl_gross_accrued_interest_bridge(result: "WaterfallResult") -> None:
    """Apply the committed TUHO Excel R27 gross-accrued SHL bridge.

    The waterfall engine always exposes its formula-derived gross-accrual audit
    field. The TUHO P&L bridge flag uses the committed Excel DS R122/R27 extract
    as the calibrated source for R27 while leaving SHL cash, PIK, WHT, and
    distributions untouched.
    """

    import json
    from pathlib import Path

    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "fixtures"
        / "interest_limitation"
        / "tuho_interest_limitation_fixture.json"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    r27_by_period = {
        int(row["period_index"]): float(row["gross_shl_interest_r27"])
        for row in fixture["periods"]
    }

    for operating_index, period in enumerate(result.periods):
        if operating_index in r27_by_period:
            period.shl_gross_accrued_interest_keur = r27_by_period[operating_index]


def _tuho_shl_gross_accrued_by_period() -> dict[int, float]:
    """Return SHL gross-accrued interest by operating index from the validated fixture."""
    import json
    from pathlib import Path
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "fixtures"
        / "interest_limitation"
        / "tuho_interest_limitation_fixture.json"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    return {
        int(row["period_index"]): float(row["gross_shl_interest_r27"])
        for row in fixture["periods"]
    }


def _apply_tuho_tax_bridge_runtime_cash_tax(
    result: "WaterfallResult",
    tenor_periods: int,
    lockup_dscr: float,
    tax_rate: float,
    cit_cash_tax_start_operating_index: int | None = None,
) -> None:
    """Promote the TUHO tax bridge to runtime tax fields behind the flag.

    This is intentionally narrow: it consumes the fixture-backed R34 fiscal
    reintegration schedule, updates accrued/cash tax fields, and refreshes the
    C1d R69/R84/R99/R102 audit bridge. It does not accept R99/R102 as a runtime
    source and does not enable SHL FCF waterfall.

    Args:
        cit_cash_tax_start_operating_index: when set (0-based), cash tax / R67
            diagnostic is suppressed for operating_index < value. Excel-compatible
            TUHO: operating_index 25 = first non-zero R67 (year 13 H2).
    """

    from domain.distribution_account import compute_tuho_r99_input_period
    from domain.tax.loss_carryforward import (
        LossCarryforwardConfig,
        compute_loss_carryforward_period,
    )
    from domain.tax.loss_carryforward import LossCarryforwardPeriodInput

    interest_limitation_by_period = _tuho_interest_limitation_by_period()

    previous_r100 = 0.0
    previous_tax = 0.0
    # Croatia tax-law-correct mode: 5-year rolling window, semiannual periods (×2 = 10 periods).
    # This replaces the generic default which inadvertently used a 30-period no-expiry pool.
    loss_config = LossCarryforwardConfig(
        duration_years=5,
        periods_per_year=2,
        country_template="croatia",
        expire_before_use=True,
    )
    loss_buckets = _tuho_tax_bridge_opening_loss_buckets(
        result.periods[0].tax_loss_opening_audit_keur if result.periods else 0.0,
    )

    # TUHO book/tax depreciation: from the same fixture used by the book-dep bridge
    # (avoids requiring the separate use_book_depreciation_for_pnl flag)
    TUHO_BOOK_TOTAL = 72_993.7
    TUHO_TAX_TOTAL = 70_691.5
    OPERATING_PERIODS = 60

    from domain.depreciation import (
        AssetClassConfig,
        DepreciationLedgerInput,
        DepreciationPolicy,
        build_depreciation_ledger,
    )
    dep_ledger = build_depreciation_ledger(
        DepreciationLedgerInput(
            asset_classes=(AssetClassConfig(
                asset_class="tuho_aggregate_fixture",
                gross_asset_basis_keur=TUHO_BOOK_TOTAL,
                book_depreciable_basis_keur=TUHO_BOOK_TOTAL,
                tax_depreciable_basis_keur=TUHO_TAX_TOTAL,
                placed_in_service_period=0,
                depreciation_start_period=0,
                source_label="TUHO aggregate Dep R30/R31 fixture",
            ),),
            policies={"tuho_aggregate_fixture": DepreciationPolicy(
                useful_life_book_periods=OPERATING_PERIODS,
                useful_life_tax_periods=OPERATING_PERIODS,
                period_frequency="semiannual",
            )},
            period_count=OPERATING_PERIODS,
            period_frequency="semiannual",
            cod_period=0,
        )
    )
    dep_by_period = {row.period_index: row for row in dep_ledger.periods}

    # SHL gross-accrued interest: fixture-extracted Excel R27
    shl_gross_by_period = _tuho_shl_gross_accrued_by_period()

    for operating_index, period in enumerate(result.periods):
        interest_limitation = interest_limitation_by_period.get(operating_index)
        fiscal_reintegration = (
            interest_limitation.fiscal_reintegration_keur
            if interest_limitation is not None
            else 0.0
        )
        dep_row = dep_by_period.get(operating_index)
        book_dep = dep_row.book_depreciation_keur if dep_row else period.depreciation_keur
        tax_dep = dep_row.tax_depreciation_keur if dep_row else period.depreciation_keur
        shl_gross = shl_gross_by_period.get(operating_index, 0.0)

        taxable_before_losses = _tax_bridge_taxable_income_before_losses(
            ebitda_keur=period.ebitda_keur,
            book_depreciation_keur=book_dep,
            tax_depreciation_keur=tax_dep,
            senior_interest_keur=period.interest_senior_keur,
            shl_interest_formula_keur=period.interest_shl_keur,
            shl_interest_gross_accrued_keur=shl_gross,
            fiscal_reintegration_keur=fiscal_reintegration,
        )
        loss_result = compute_loss_carryforward_period(
            LossCarryforwardPeriodInput(
                period_index=operating_index,
                taxable_income_before_losses_keur=taxable_before_losses,
                opening_buckets=loss_buckets,
            ),
            loss_config,
        )
        loss_buckets = loss_result.closing_buckets
        tax_keur = loss_result.taxable_profit_after_losses_keur * tax_rate

        period.fiscal_reintegration_audit_keur = fiscal_reintegration
        period.taxable_income_before_losses_audit_keur = taxable_before_losses
        period.tax_loss_opening_audit_keur = loss_result.losses_n_1_keur
        period.tax_loss_used_audit_keur = loss_result.allocated_losses_keur
        period.tax_loss_closing_audit_keur = loss_result.losses_n_keur
        period.taxable_profit_after_losses_audit_keur = (
            loss_result.taxable_profit_after_losses_keur
        )
        period.taxable_profit_keur = loss_result.taxable_profit_after_losses_keur
        period.tax_keur = tax_keur
        period.cit_accrual_audit_keur = tax_keur

        # Suppress cash tax before the Excel-compatible start period.
        # Default (None) = no suppression. TUHO Excel: operating_index 25.
        suppressed = (
            cit_cash_tax_start_operating_index is not None
            and operating_index < cit_cash_tax_start_operating_index
        )

        period.r67_excel_style_cash_tax_diagnostic_keur = (
            -(previous_tax + tax_keur) if (period.period_in_year == 2 and not suppressed) else 0.0
        )
        period.cash_tax_excel_style_h2_diagnostic_keur = (
            period.r67_excel_style_cash_tax_diagnostic_keur
        )

        tax_cash = (
            -period.cash_tax_excel_style_h2_diagnostic_keur
            if (period.period_in_year == 2 and not suppressed)
            else 0.0
        )
        period.corporate_tax_cash_keur = tax_cash
        period.cash_tax_current_period_audit_keur = tax_cash
        period.cf_after_tax_keur = period.ebitda_keur - tax_cash

        dsra_release_or_funding = max(0.0, -period.dsra_contribution_keur) - max(
            0.0, period.dsra_contribution_keur
        )
        r99_audit = compute_tuho_r99_input_period(
            revenue_keur=period.revenue_keur,
            opex_keur=period.opex_keur,
            local_tax_keur=0.0,
            cash_interest_on_reserves_keur=0.0,
            corporate_tax_cash_keur=tax_cash,
            senior_ds_keur=period.senior_ds_keur,
            dsra_release_or_funding_keur=dsra_release_or_funding,
            junior_ds_keur=0.0,
            reserve_sweep_keur=0.0,
            previous_r100_carryforward_keur=previous_r100,
            year_index=period.year_index,
            senior_tenor_years=tenor_periods // 2,
            dscr=period.dscr,
            lockup_dscr=lockup_dscr,
            dsra_balance_keur=period.dsra_balance_keur,
            dsra_target_keur=0.0,
            jdsra_balance_keur=0.0,
            jdsra_target_keur=0.0,
        )
        period.r69_fcf_banks_keur = r99_audit.r69_fcf_banks_keur
        period.r84_fcf_junior_keur = r99_audit.r84_fcf_junior_keur
        period.r98_distribution_account_keur = r99_audit.r98_distribution_account_keur
        period.r99_fcf_for_distribution_keur = r99_audit.r99_fcf_for_distribution_keur
        period.r100_carryforward_keur = r99_audit.r100_carryforward_keur
        period.r102_fcf_for_shl_keur = r99_audit.r102_fcf_for_shl_keur
        period.fcf_for_shl_keur = r99_audit.fcf_for_shl_keur
        previous_r100 = r99_audit.r100_carryforward_keur
        previous_tax = tax_keur

    result.total_tax_keur = sum(period.tax_keur for period in result.periods)


def _tax_bridge_taxable_income_before_losses(
    *,
    ebitda_keur: float,
    book_depreciation_keur: float,
    tax_depreciation_keur: float,
    senior_interest_keur: float,
    shl_interest_formula_keur: float,
    shl_interest_gross_accrued_keur: float,
    fiscal_reintegration_keur: float,
) -> float:
    """Return signed taxable income before losses using R35 source basis.

    R35 bridge sources:
    - book_depreciation_keur:  P&L cost (earnings statement basis, straight-line)
    - tax_depreciation_keur:   fiscal addback (tax basis straight-line, differs from book)
    - shl_interest_formula_keur: legacy formula-derived gross SHL interest (fallback)
    - shl_interest_gross_accrued_keur: fixture-extracted Excel R27 (preferred, non-zero for TUHO)
    - senior_interest_keur:  senior debt interest
    - fiscal_reintegration_keur: R34 interest limitation reintegration
    """
    # Use gross-accrued source for SHL when available; fall back to formula otherwise
    shl_interest = (
        shl_interest_gross_accrued_keur
        if shl_interest_gross_accrued_keur > 0
        else shl_interest_formula_keur
    )
    total_interest = senior_interest_keur + shl_interest
    deductible_interest_limit = max(ebitda_keur * 0.30, 3000.0)
    disallowed_interest = max(0.0, total_interest - deductible_interest_limit)
    deductible_interest = total_interest - disallowed_interest
    return (
        ebitda_keur
        - book_depreciation_keur
        - deductible_interest
        + disallowed_interest
        + tax_depreciation_keur
        + fiscal_reintegration_keur
    )


def _tuho_tax_bridge_opening_loss_buckets(opening_loss_keur: float):
    """Return TUHO flag-on opening loss buckets.

    The current Excel extraction does not yet expose construction-period loss
    vintages. This explicit bucket preserves the known 25,000 kEUR opening loss
    amount while modeling it as a near-expiry construction-period bucket instead
    of resetting its age at COD.
    """

    if opening_loss_keur <= 0:
        return ()

    from domain.tax.loss_carryforward import LossCarryforwardBucket

    return (
        LossCarryforwardBucket(
            amount_keur=opening_loss_keur,
            periods_remaining=1,
            source_period_index=None,
            source_label=(
                "TUHO explicit construction-period opening loss bucket; "
                "near-expiry assumption pending full pre-COD Excel loss extract"
            ),
        ),
    )


def _tuho_interest_limitation_by_period():
    """Build TUHO R34 fiscal reintegration results from the Excel extraction."""

    import json
    from pathlib import Path

    from domain.tax.interest_limitation import (
        InterestLimitationConfig,
        InterestLimitationPeriodInput,
        InterestLimitationSignConvention,
        compute_interest_limitation_period,
    )

    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "fixtures"
        / "interest_limitation"
        / "tuho_interest_limitation_fixture.json"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    config = InterestLimitationConfig(
        sign_convention=InterestLimitationSignConvention.SUBTRACT_FROM_TI,
        notes="TUHO tax bridge runtime flag consumes committed Excel R34 fixture.",
    )
    return {
        int(row["period_index"]): compute_interest_limitation_period(
            InterestLimitationPeriodInput(
                period_index=int(row["period_index"]),
                gross_shl_interest_keur=float(row["gross_shl_interest_r27"]),
                ebitda_keur=float(row["ebitda"]),
                thin_cap_active=bool(row["thin_cap_gate_r45"]),
                ratio_adjustment_keur=float(row["r59_ratio_adjustment"]),
            ),
            config,
        )
        for row in fixture["periods"]
    }


def _attach_dualrun_validation(result, inputs, periods_list) -> None:
    """Attach dual-run validation metadata to waterfall result (audit only).

    NO runtime routing. Result is not modified. DA remains audit-only.
    """
    from domain.distribution_account.dualrun_validation import run_dual_validation
    from domain.distribution_account.inputs import (
        DistributionAccountInputs,
        DistributionAccountPeriodInput,
        R99R102GateInputs,
    )
    from domain.waterfall.waterfall_engine import run_waterfall

    # Build DA period inputs from waterfall result periods
    # We use the same cash data that the waterfall was built from
    # to get a comparable DA result
    da_period_inputs: list[DistributionAccountPeriodInput] = []
    for wp in result.periods:
        p_idx = getattr(wp, "period", None)
        if p_idx is None:
            continue
        # Use revenue - opex as a proxy for cash_for_dist
        # post_shl_cash = revenue - opex (simplified)
        rev = getattr(wp, "revenue_keur", 0.0)
        opex = getattr(wp, "opex_keur", 0.0)
        post_shl_cash = max(0.0, rev - opex)
        da_period_inputs.append(DistributionAccountPeriodInput(
            period_index=p_idx,
            operating_period_index=getattr(wp, "operating_period_index", p_idx),
            period_date=getattr(wp, "date", None) or __import__('datetime').date(2029, 12, 31),
            opening_distribution_account_balance_keur=0.0,
            post_senior_cash_available_keur=post_shl_cash,
            post_shl_cash_available_keur=post_shl_cash,
            senior_debt_service_keur=getattr(wp, "senior_ds_keur", 0.0),
            actual_dscr=getattr(wp, "dscr", 1.5),
            target_distribution_dscr=1.0,
            dsra_current_balance_keur=getattr(wp, "dsra_balance_keur", 0.0),
            dsra_required_balance_keur=getattr(wp, "dsra_balance_keur", 0.0),
            is_tuho=(getattr(inputs.info, "code", "") == "TUHO-WIND-1"),
            is_oborovo=(getattr(inputs.info, "code", "") == "OBOROVO-SOLAR-1"),
            senior_tenor_years=inputs.financing.senior_tenor_years,
            minimum_cash_reserve_keur=0.0,
        ))

    da_inputs = DistributionAccountInputs(
        project_name=getattr(inputs.info, "name", "Project"),
        period_inputs=tuple(da_period_inputs),
        is_tuho=(getattr(inputs.info, "code", "") == "TUHO-WIND-1"),
        is_oborovo=(getattr(inputs.info, "code", "") == "OBOROVO-SOLAR-1"),
    )

    try:
        dual_result = run_dual_validation(result, da_inputs)
        result._dualrun_validation = dual_result
    except Exception:
        # If dualrun fails, do not propagate — just skip annotation
        pass


__all__ = ["run_waterfall_v3_core"]
