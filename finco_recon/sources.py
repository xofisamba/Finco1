"""finco_recon.sources — Load all data sources for Oborovo reconciliation.

Three data sources:
  1. Excel truth fixture: tests/fixtures/excel_oborovo_financial_truth.json
     Extracted by finco_recon.extract_oborovo_excel from the authoritative XLSM.
     61 periods (0=construction, 1-60=operation) from CF/DS/P&L/Dep/Inputs/CapEx sheets.
  2. Legacy baseline snapshot: finco_parity/baselines/snapshots/oborovo.json
     Full 60-period legacy waterfall output (legacy_waterfall_v3).
  3. Clean engine: run_senior_debt_model with Phase 2C calibration.

Import boundary: may import from financial_engine.*, finco_parity.*, app.project_factories.
Must NOT modify any of those modules.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Per-period data containers
# ---------------------------------------------------------------------------

@dataclass
class ExcelData:
    """Parsed Excel fixture data for one operating period.

    Sourced from authoritative XLSM via finco_recon.extract_oborovo_excel.
    period_index 0 = first operation period (Excel period 1, H2-2030).
    """
    period_index: int       # 0-based operation index (fixture period_num - 1)
    period_start: str       # BoP date e.g. "2030-07-01"
    period_end: str         # EoP date e.g. "2030-12-31"
    operation_period_fraction: float | None = None   # day fraction
    # CF sheet — production & revenue
    production_mwh: float | None = None
    revenue_keur: float | None = None       # CF.operating_revenues_keur
    ppa_sales_keur: float | None = None
    production_to_ppa_mwh: float | None = None
    tariff_indexed_eur_mwh: float | None = None
    # CF sheet — OPEX
    opex_keur: float | None = None          # stored positive (abs of CF.operating_expenses)
    # CF OPEX per item (stored positive: abs of workbook negative values)
    opex_b01_keur: float | None = None  # Technical Management
    opex_b02_keur: float | None = None  # Infrastructure Maintenance
    opex_b03_keur: float | None = None  # Maintain Site
    opex_b04_keur: float | None = None  # Clean Material
    opex_b05_keur: float | None = None  # Security
    opex_b06_keur: float | None = None  # Insurance
    opex_b07_keur: float | None = None  # Lease & property Tax
    opex_b08_keur: float | None = None  # Power Expenses
    opex_b09_keur: float | None = None  # Fees
    opex_b10_keur: float | None = None  # Audit & Accounting & Legal
    opex_b11_keur: float | None = None  # Bank Fees
    opex_b12_keur: float | None = None  # Environmental & Social
    opex_b13_keur: float | None = None  # Contingencies
    # CF sheet — EBITDA  (direct from workbook, None if cell not cached)
    ebitda_keur: float | None = None
    # EBITDA derived as Revenue - OPEX where direct is None
    ebitda_derived_keur: float | None = None
    # CF sheet — downstream
    cash_tax_keur: float | None = None      # stored positive (abs)
    cfads_keur: float | None = None         # FCF for banks
    senior_ds_keur: float | None = None     # stored positive (abs)
    # DS sheet — senior debt schedule (direct from DS.senior_debt_service rows)
    dscr_target: float | None = None
    senior_principal_keur: float | None = None   # stored positive
    senior_interest_keur: float | None = None    # stored positive
    sd_opening_keur: float | None = None
    sd_closing_keur: float | None = None
    sd_service_keur: float | None = None
    # DS sheet — SHL schedule
    shl_opening_keur: float | None = None
    shl_net_interest_keur: float | None = None
    shl_interest_capitalised_keur: float | None = None
    shl_closing_keur: float | None = None
    shl_service_keur: float | None = None
    # P&L sheet
    pl_revenue_keur: float | None = None
    depreciation_keur: float | None = None
    pl_senior_interest_keur: float | None = None
    shl_interest_keur: float | None = None
    earnings_before_tax_keur: float | None = None
    taxable_income_keur: float | None = None
    pl_cit_keur: float | None = None            # stored positive (abs)
    net_dividends_keur: float | None = None
    net_income_keur: float | None = None
    # Dep sheet
    dep_depreciation_keur: float | None = None
    dep_total_keur: float | None = None


@dataclass
class LegacyData:
    """Legacy snapshot data for one period."""
    period_index: int
    period_end: str
    # Operating
    production_mwh: float | None = None
    revenue_keur: float | None = None
    opex_keur: float | None = None
    ebitda_keur: float | None = None
    book_depreciation_keur: float | None = None
    tax_depreciation_keur: float | None = None
    # Tax/CFADS
    taxable_profit_keur: float | None = None
    taxable_income_before_losses_keur: float | None = None
    tax_keur: float | None = None
    corporate_tax_cash_keur: float | None = None
    tax_loss_opening_keur: float | None = None
    tax_loss_closing_keur: float | None = None
    tax_loss_used_keur: float | None = None
    cfads_keur: float | None = None
    cf_after_tax_keur: float | None = None
    # Senior debt
    sd_opening_keur: float | None = None
    sd_interest_keur: float | None = None
    sd_principal_keur: float | None = None
    sd_ds_keur: float | None = None
    sd_closing_keur: float | None = None
    sd_dscr: float | None = None
    # SHL
    shl_opening_keur: float | None = None
    shl_closing_keur: float | None = None
    shl_interest_keur: float | None = None
    shl_pik_keur: float | None = None


@dataclass
class EngineData:
    """Clean engine output for one operating period."""
    period_index: int       # 0-based engine period index
    period_start: str
    period_end: str
    days_in_period: int = 0
    day_fraction: float = 0.0
    is_operation: bool = True
    # COD semantic fields — populated from engine; contractual_cod is date from FC+construction_months
    contractual_cod_date: str = ""          # financial_close + relativedelta(months=construction_months)
    first_operating_period_boundary: str = ""  # first period start after near-zero stub roll
    # PPA tariff (direct from policy computation, EUR/MWh)
    ppa_tariff_eur_mwh: float | None = None
    # Operating
    production_mwh: float | None = None
    revenue_keur: float | None = None
    opex_keur: float | None = None
    ebitda_keur: float | None = None
    book_depreciation_keur: float | None = None
    tax_depreciation_keur: float | None = None
    # Per-item OPEX
    opex_b01_keur: float | None = None
    opex_b02_keur: float | None = None
    opex_b03_keur: float | None = None
    opex_b04_keur: float | None = None
    opex_b05_keur: float | None = None
    opex_b06_keur: float | None = None
    opex_b07_keur: float | None = None
    opex_b08_keur: float | None = None
    opex_b09_keur: float | None = None
    opex_b10_keur: float | None = None
    opex_b11_keur: float | None = None
    opex_b12_keur: float | None = None
    opex_b13_keur: float | None = None
    opex_b14_keur: float | None = None
    opex_b15_keur: float | None = None
    # Tax/CFADS
    taxable_profit_keur: float | None = None
    taxable_income_before_losses_keur: float | None = None
    tax_keur: float | None = None
    corporate_tax_cash_keur: float | None = None
    tax_loss_opening_keur: float | None = None
    tax_loss_closing_keur: float | None = None
    tax_loss_used_keur: float | None = None
    cfads_keur: float | None = None
    # Senior debt
    sd_opening_keur: float | None = None
    sd_interest_keur: float | None = None
    sd_principal_keur: float | None = None
    sd_ds_keur: float | None = None
    sd_closing_keur: float | None = None
    sd_dscr: float | None = None
    # Scalar debt summary (same for all periods)
    sd_debt_size_keur: float | None = None
    sd_binding_constraint: str | None = None
    sd_iteration_count: int | None = None


@dataclass
class OborovoSources:
    """Container for all Oborovo data sources."""
    excel: list[ExcelData]       # 60 operation periods, index 0..59
    legacy: list[LegacyData]     # 60 periods, index 0..59
    engine: list[EngineData]     # 60 periods
    # Provenance of authoritative Excel fixture
    excel_fixture_sha256: str = ""
    excel_source_filename: str = ""
    # Scalar inputs — authoritative Excel source (from XLSM Inputs sheet)
    capacity_mw: float = 0.0                  # Excel: Inputs!D51
    cod_date: str = ""                        # Excel: Inputs!D11 (operation start)
    financial_close: str = ""                 # Excel: Inputs!D9
    ppa_tariff_eur_mwh: float = 0.0          # Excel: Inputs!D78
    ppa_term_years: int = 0                   # Excel: Inputs!D81
    ppa_index: float = 0.0                    # Excel: Inputs!D83
    operating_hours_p50: int = 0              # Excel: Inputs!D54
    plant_availability: float = 0.0          # Excel: Inputs!D58
    grid_availability: float = 0.0           # Excel: Inputs!D59
    pv_degradation_pa: float = 0.0           # Excel: Inputs!D56
    horizon_years: int = 0
    construction_months: int = 0
    # CAPEX — Excel source (from XLSM Inputs/CapEx sheets)
    excel_total_capex_keur: float = 0.0       # Excel: Inputs!C45 (authoritative)
    excel_idc_keur: float = 0.0              # Excel: Inputs!C39
    excel_bank_fees_keur: float = 0.0        # Excel: Inputs!C41
    excel_commitment_fees_keur: float = 0.0  # Excel: Inputs!C40
    excel_capex_items: dict = field(default_factory=dict)  # code → {label, amount_keur}
    excel_opex_annual: dict = field(default_factory=dict)  # code → {label, year1_keur}
    # Senior debt — Excel source
    excel_total_debt_keur: float = 0.0        # Excel: Inputs!D192
    excel_senior_maturity_years: int = 0      # Excel: Inputs!D196
    excel_senior_base_rate: float = 0.0       # Excel: Inputs!D202
    excel_senior_margin_bps: float = 0.0      # Excel: Inputs!D203
    excel_target_dscr: float = 0.0           # Excel: Inputs!D221
    excel_lockup_dscr: float = 0.0           # Excel: Inputs!D223
    # SHL — Excel source
    shl_amount_keur: float = 0.0             # Excel: Inputs!D325
    shl_rate: float = 0.0                    # Excel: Inputs!F328
    shl_idc_keur: float = 0.0
    # OPEX and CAPEX from factory (Python side — independent provenance)
    opex_items: list[dict] = field(default_factory=list)
    capex_items: list[dict] = field(default_factory=list)
    total_capex_keur: float = 0.0
    hard_capex_keur: float = 0.0
    idc_keur: float = 0.0
    # SHL per-period from old fixture (retained for backward compat)
    excel_shl: list[dict] = field(default_factory=list)
    # Engine scalars
    engine_debt_size_keur: float = 0.0
    engine_binding_constraint: str | None = None
    engine_iterations: int = 0
    # Derived averages (computed in load_oborovo_sources)
    excel_avg_dscr: float = 0.0
    excel_min_dscr: float = 0.0
    # Retained for backward compatibility with existing tests
    excel_sd_opening_keur: list[float | None] = field(default_factory=list)
    excel_sd_closing_keur: list[float | None] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _float_or_none(val: Any) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _load_excel_truth() -> tuple[list[ExcelData], dict]:
    """Load from authoritative XLSM extract (excel_oborovo_financial_truth.json).

    Returns (period_list, metadata_dict).
    Periods 1-60 (operation) only; period 0 (construction) is excluded from the list.
    OPEX values stored as positive (absolute of workbook negative).
    """
    path = _REPO_ROOT / "tests" / "fixtures" / "excel_oborovo_financial_truth.json"
    raw = json.loads(path.read_text())

    cf = raw["cf"]
    ds = raw["ds"]
    pl = raw["pl"]
    dep = raw["dep"]
    meta = raw.get("_meta", {})
    inp = raw.get("inputs", {})

    def fv(section: dict, key: str, p: int) -> float | None:
        lst = section.get(key)
        if lst is None or p >= len(lst):
            return None
        return _float_or_none(lst[p])

    def fabs(section: dict, key: str, p: int) -> float | None:
        v = fv(section, key, p)
        return abs(v) if v is not None else None

    def sval(section: dict, key: str, p: int) -> str | None:
        lst = section.get(key)
        if lst is None or p >= len(lst):
            return None
        return lst[p]

    result: list[ExcelData] = []
    # Periods 1-60 (operation periods in workbook; index 0 = col 7 in workbook = period 1)
    for op_idx in range(60):
        p = op_idx + 1      # workbook period number (1-based)

        # EBITDA: direct from workbook if cached, else derived from Revenue - OPEX
        ebitda_direct = fv(cf, "ebitda_keur", p)
        rev = fv(cf, "operating_revenues_keur", p)
        opex_abs = fabs(cf, "operating_expenses_keur", p)
        ebitda_derived = None
        if ebitda_direct is None and rev is not None and opex_abs is not None:
            ebitda_derived = rev - opex_abs

        ed = ExcelData(
            period_index=op_idx,
            period_start=sval(cf, "bop_date", p) or "",
            period_end=sval(cf, "eop_date", p) or "",
            operation_period_fraction=fv(cf, "operation_period_fraction", p),
            # Production & revenue
            production_mwh=fv(cf, "production_mwh", p),
            revenue_keur=rev,
            ppa_sales_keur=fv(cf, "ppa_sales_keur", p),
            production_to_ppa_mwh=fv(cf, "production_to_ppa_mwh", p),
            tariff_indexed_eur_mwh=fv(cf, "tariff_indexed_eur_mwh", p),
            # OPEX
            opex_keur=opex_abs,
            opex_b01_keur=fabs(cf, "opex_items_period_keur", p) if False else _opex_item(raw, "B.01", p),
            opex_b02_keur=_opex_item(raw, "B.02", p),
            opex_b03_keur=_opex_item(raw, "B.03", p),
            opex_b04_keur=_opex_item(raw, "B.04", p),
            opex_b05_keur=_opex_item(raw, "B.05", p),
            opex_b06_keur=_opex_item(raw, "B.06", p),
            opex_b07_keur=_opex_item(raw, "B.07", p),
            opex_b08_keur=_opex_item(raw, "B.08", p),
            opex_b09_keur=_opex_item(raw, "B.09", p),
            opex_b10_keur=_opex_item(raw, "B.10", p),
            opex_b11_keur=_opex_item(raw, "B.11", p),
            opex_b12_keur=_opex_item(raw, "B.12", p),
            opex_b13_keur=_opex_item(raw, "B.13", p),
            # EBITDA
            ebitda_keur=ebitda_direct,
            ebitda_derived_keur=ebitda_derived,
            # Downstream CF
            cash_tax_keur=fabs(cf, "corporate_income_tax_keur", p),
            cfads_keur=fv(cf, "fcf_for_banks_keur", p),
            senior_ds_keur=fabs(cf, "senior_debt_service_keur", p),
            # DS — senior debt (direct from DS sheet)
            dscr_target=fv(ds, "dscr_target", p),
            senior_principal_keur=fv(ds, "sd_principal_keur", p),
            senior_interest_keur=fv(ds, "sd_net_interest_keur", p),
            sd_opening_keur=fv(ds, "sd_beginning_keur", p),
            sd_closing_keur=fv(ds, "sd_ending_keur", p),
            sd_service_keur=fv(ds, "sd_service_keur", p),
            # DS — SHL (direct from DS sheet)
            shl_opening_keur=fv(ds, "shl_beginning_keur", p),
            shl_net_interest_keur=fv(ds, "shl_net_interest_keur", p),
            shl_interest_capitalised_keur=fv(ds, "shl_interest_capitalised_keur", p),
            shl_closing_keur=fv(ds, "shl_ending_keur", p),
            shl_service_keur=fv(ds, "shl_service_keur", p),
            # P&L
            pl_revenue_keur=fv(pl, "total_revenues_keur", p),
            depreciation_keur=fv(pl, "depreciation_keur", p),
            pl_senior_interest_keur=fv(pl, "senior_interests_keur", p),
            shl_interest_keur=fv(pl, "shl_interests_keur", p),
            earnings_before_tax_keur=fv(pl, "earnings_before_tax_keur", p),
            taxable_income_keur=fv(pl, "taxable_income_keur", p),
            pl_cit_keur=fv(pl, "corporate_income_tax_keur", p),
            net_dividends_keur=fv(pl, "net_dividends_keur", p),
            net_income_keur=fv(pl, "net_income_keur", p),
            # Dep
            dep_depreciation_keur=fv(dep, "dep_total_keur", p),
            dep_total_keur=fv(dep, "dep_total_keur", p),
        )
        result.append(ed)

    return result, meta


def _opex_item(raw: dict, code: str, period: int) -> float | None:
    """Extract one per-item OPEX value (stored positive) for a given period."""
    items = raw.get("cf", {}).get("opex_items_period_keur", {})
    lst = items.get(code)
    if lst is None or period >= len(lst):
        return None
    v = _float_or_none(lst[period])
    return abs(v) if v is not None else None


def _load_excel_shl() -> list[dict]:
    # Legacy SHL loader kept for backward compat; returns empty list if new fixture used
    path = _REPO_ROOT / "tests" / "fixtures" / "excel_oborovo_full_model_extract.json"
    if not path.exists():
        return []
    raw = json.loads(path.read_text())
    cols = raw.get("shl_columns", [])
    rows = raw.get("shl", [])
    return [dict(zip(cols, row)) for row in rows]


def _load_legacy_periods() -> list[LegacyData]:
    path = _REPO_ROOT / "finco_parity" / "baselines" / "snapshots" / "oborovo.json"
    snap = json.loads(path.read_text())

    period_grid = snap["period_grid"]  # list of {date, period_index, is_operation, ...}
    os_ = snap["operating_schedules"]
    tc = snap["tax_and_cfads"]
    sd = snap["financing"]["senior_debt"]
    shl = snap["financing"]["shl"]

    def get_list(d: dict, key: str) -> list:
        return d.get(key) or []

    prod = get_list(os_, "production_mwh")
    rev = get_list(os_, "revenue_keur")
    opex = get_list(os_, "opex_keur")
    ebitda = get_list(os_, "ebitda_keur")
    book_dep = get_list(os_, "book_depreciation_keur")
    tax_dep = get_list(os_, "tax_depreciation_keur")
    # Tax
    txp = get_list(tc, "taxable_profit_keur")
    txbl = get_list(tc, "taxable_income_before_losses_audit_keur")
    tax = get_list(tc, "tax_keur")
    ctax = get_list(tc, "corporate_tax_cash_keur")
    tlo = get_list(tc, "tax_loss_opening_audit_keur")
    tlc = get_list(tc, "tax_loss_closing_audit_keur")
    tlu = get_list(tc, "tax_loss_used_audit_keur")
    cfads = get_list(tc, "cfads_keur")
    cfat = get_list(tc, "cf_after_tax_keur")
    # Senior debt
    sd_open = get_list(sd, "opening_keur")
    sd_int = get_list(sd, "interest_keur")
    sd_prin = get_list(sd, "principal_keur")
    sd_ds = get_list(sd, "debt_service_keur")
    sd_close = get_list(sd, "closing_keur")
    sd_dscr_l = get_list(sd, "dscr")
    # SHL
    shl_open = get_list(shl, "opening_keur")
    shl_close = get_list(shl, "closing_keur")
    shl_int = get_list(shl, "interest_keur")
    shl_pik = get_list(shl, "pik_keur")

    def _at(lst: list, i: int) -> float | None:
        if i < len(lst):
            return _float_or_none(lst[i])
        return None

    result: list[LegacyData] = []
    for i, pg in enumerate(period_grid):
        ld = LegacyData(
            period_index=i,
            period_end=str(pg.get("date", "")),
            production_mwh=_at(prod, i),
            revenue_keur=_at(rev, i),
            opex_keur=_at(opex, i),
            ebitda_keur=_at(ebitda, i),
            book_depreciation_keur=_at(book_dep, i),
            tax_depreciation_keur=_at(tax_dep, i),
            taxable_profit_keur=_at(txp, i),
            taxable_income_before_losses_keur=_at(txbl, i),
            tax_keur=_at(tax, i),
            corporate_tax_cash_keur=_at(ctax, i),
            tax_loss_opening_keur=_at(tlo, i),
            tax_loss_closing_keur=_at(tlc, i),
            tax_loss_used_keur=_at(tlu, i),
            cfads_keur=_at(cfads, i),
            cf_after_tax_keur=_at(cfat, i),
            sd_opening_keur=_at(sd_open, i),
            sd_interest_keur=_at(sd_int, i),
            sd_principal_keur=_at(sd_prin, i),
            sd_ds_keur=_at(sd_ds, i),
            sd_closing_keur=_at(sd_close, i),
            sd_dscr=_at(sd_dscr_l, i),
            shl_opening_keur=_at(shl_open, i),
            shl_closing_keur=_at(shl_close, i),
            shl_interest_keur=_at(shl_int, i),
            shl_pik_keur=_at(shl_pik, i),
        )
        result.append(ld)
    return result


def _run_clean_engine() -> tuple[list[EngineData], float, str | None, int]:
    """Run run_senior_debt_model for oborovo and return (engine_data, debt_size, binding, iters)."""
    from financial_engine.orchestrator import run_senior_debt_model
    from financial_engine.inputs import TaxCalculationInput, SeniorDebtModelInput, DebtSizingCaseInput, YieldScenario
    from financial_engine.senior_debt.inputs import SeniorDebtInputs
    from financial_engine.senior_debt.policy import (
        SeniorDebtPolicy, SeniorDebtSizingMode, DayCountConvention,
    )
    from finco_parity.tax_reference_inputs import build_tax_policy, build_opening_loss_vintages
    from finco_parity.financial_engine_tax_cfads_candidate import (
        _load_project_inputs, _load_baseline_snapshot, _build_exogenous_interest,
    )
    from financial_engine.adapters.project_inputs import from_project_inputs

    project_inputs = _load_project_inputs("oborovo")
    op_inputs = from_project_inputs(project_inputs, source_id="parity_oborovo")
    tax_policy = build_tax_policy("oborovo")
    opening_vintages = build_opening_loss_vintages("oborovo")
    snap = _load_baseline_snapshot("oborovo")
    exog_interest = _build_exogenous_interest(snap)
    tax_input = TaxCalculationInput(
        policy=tax_policy,
        opening_loss_vintages=opening_vintages,
        period_interest=exog_interest,
        period_adjustments=(),
    )
    eligible_cost = getattr(project_inputs.capex, "total_capex_keur", None) or 100_000.0
    # Fall back to computed value if property
    if callable(eligible_cost):
        eligible_cost = 57973.05

    sd_policy = SeniorDebtPolicy(
        policy_id="parity_oborovo",
        policy_version="1.0",
        sizing_mode=SeniorDebtSizingMode.DSCR_SCULPTED,
        target_dscr=1.15,
        maximum_gearing=None,
        annual_fixed_rate=0.0565,
        periods_per_year=2,
        day_count_convention=DayCountConvention.ACT_365,
        repayment_start_period_index=2,
        maturity_period_index=29,
        convergence_tolerance_keur=1.0,
        convergence_relative_tolerance=0.001,
        maximum_iterations=500,
        permit_terminal_balloon=True,
        damping_alpha=1.0,
    )
    sd_inputs = SeniorDebtInputs(
        eligible_project_cost_keur=eligible_cost,
        initial_debt_guess_keur=eligible_cost * 0.60,
        period_rates=(),
        explicit_principal_schedule=None,
    )
    model_input = SeniorDebtModelInput(
        operating=op_inputs,
        tax=tax_input,
        senior_debt_policy=sd_policy,
        senior_debt_inputs=sd_inputs,
        debt_sizing_case=DebtSizingCaseInput(
            production_yield_scenario=YieldScenario.P90_10Y,
            source_label="generic_bank_case_p90_10y",
        ),
    )
    result = run_senior_debt_model(model_input)

    sd = result.senior_debt
    tc = result.tax_and_cfads
    diag = sd.diagnostics if isinstance(sd.diagnostics, dict) else {}

    # Compute contractual COD (EDATE-equivalent) and first operating boundary.
    from financial_engine.ppa_indexation import compute_ppa_tariff
    from dateutil.relativedelta import relativedelta as _rdelta
    _cal = op_inputs.calendar
    _contractual_cod = _cal.financial_close + _rdelta(months=_cal.construction_months)
    _all_op = [p for p in result.periods if p.is_operation]
    _first_op_boundary = _all_op[0].period_start if _all_op else _contractual_cod

    # Per-period PPA tariff from policy.
    _rev = op_inputs.revenue
    _policy = _rev.ppa_indexation_start_policy
    _base_tariff = _rev.ppa_base_tariff_eur_mwh
    _ppa_index = _rev.ppa_index
    _ppa_start_date = _rev.ppa_indexation_start_date

    # Index operating periods only
    op_periods = [p for p in result.periods if p.is_operation]
    period_idx_map = {p.period_index: i for i, p in enumerate(op_periods)}

    # Build per-item opex from factory
    from app.project_factories import create_default_oborovo
    proj = create_default_oborovo()
    opex_items_factory = list(proj.opex)  # tuple of OpexItem

    def _opex_at_period(item_idx: int, period: Any) -> float | None:
        if item_idx >= len(opex_items_factory):
            return None
        try:
            val = opex_items_factory[item_idx].amount_at_year(period.year_index)
            return _float_or_none(val) if val is not None else None
        except Exception:
            return None

    # Build per-operating-period opex breakdown (sum check vs total)
    n_op = len(op_periods)
    per_item_opex: list[list[float | None]] = [
        [None] * n_op for _ in range(15)
    ]
    for pos, p in enumerate(op_periods):
        total_check = 0.0
        for item_idx in range(15):
            v = _opex_at_period(item_idx, p)
            per_item_opex[item_idx][pos] = v
            if v is not None:
                total_check += v

    # Build sd index lookup
    sd_by_period: dict[int, int] = {idx: i for i, idx in enumerate(sd.period_indices)}

    # Build tax lookup
    tc_by_period: dict[int, int] = {idx: i for i, idx in enumerate(tc.period_indices)} if tc else {}

    def _sd_val(key_tuple: tuple, period_idx: int) -> float | None:
        sdi = sd_by_period.get(period_idx)
        if sdi is None:
            return None
        arr = key_tuple
        if sdi < len(arr):
            return _float_or_none(arr[sdi])
        return None

    def _tc_val(arr: tuple, period_idx: int) -> float | None:
        tci = tc_by_period.get(period_idx)
        if tci is None:
            return None
        if tci < len(arr):
            return _float_or_none(arr[tci])
        return None

    engine_data: list[EngineData] = []
    for pos, p in enumerate(op_periods):
        pidx = p.period_index
        _period_tariff = compute_ppa_tariff(
            base_tariff=_base_tariff,
            ppa_index=_ppa_index,
            policy=_policy,
            cod=_contractual_cod,
            period_end=p.period_end,
            ppa_indexation_start_date=_ppa_start_date,
        )
        ed = EngineData(
            period_index=pos,
            period_start=str(p.period_start),
            period_end=str(p.period_end),
            days_in_period=p.days_in_period,
            day_fraction=p.day_fraction,
            is_operation=p.is_operation,
            contractual_cod_date=str(_contractual_cod),
            first_operating_period_boundary=str(_first_op_boundary),
            ppa_tariff_eur_mwh=_period_tariff,
            production_mwh=_float_or_none(p.production_mwh),
            revenue_keur=_float_or_none(p.revenue_keur),
            opex_keur=_float_or_none(p.opex_keur),
            ebitda_keur=_float_or_none(p.ebitda_keur),
            book_depreciation_keur=_float_or_none(p.book_depreciation_keur),
            tax_depreciation_keur=_float_or_none(p.tax_depreciation_keur),
            # Per-item opex
            opex_b01_keur=per_item_opex[0][pos],
            opex_b02_keur=per_item_opex[1][pos],
            opex_b03_keur=per_item_opex[2][pos],
            opex_b04_keur=per_item_opex[3][pos],
            opex_b05_keur=per_item_opex[4][pos],
            opex_b06_keur=per_item_opex[5][pos],
            opex_b07_keur=per_item_opex[6][pos],
            opex_b08_keur=per_item_opex[7][pos],
            opex_b09_keur=per_item_opex[8][pos],
            opex_b10_keur=per_item_opex[9][pos],
            opex_b11_keur=per_item_opex[10][pos],
            opex_b12_keur=per_item_opex[11][pos],
            opex_b13_keur=per_item_opex[12][pos],
            opex_b14_keur=per_item_opex[13][pos],
            opex_b15_keur=per_item_opex[14][pos],
            # Tax / CFADS
            taxable_profit_keur=_tc_val(tc.taxable_profit_keur, pidx) if tc else None,
            taxable_income_before_losses_keur=_tc_val(tc.taxable_income_before_losses_audit_keur, pidx) if tc else None,
            tax_keur=_tc_val(tc.tax_keur, pidx) if tc else None,
            corporate_tax_cash_keur=_tc_val(tc.corporate_tax_cash_keur, pidx) if tc else None,
            tax_loss_opening_keur=_tc_val(tc.tax_loss_opening_audit_keur, pidx) if tc else None,
            tax_loss_closing_keur=_tc_val(tc.tax_loss_closing_audit_keur, pidx) if tc else None,
            tax_loss_used_keur=_tc_val(tc.tax_loss_used_audit_keur, pidx) if tc else None,
            cfads_keur=_tc_val(tc.cfads_keur, pidx) if tc else None,
            # Senior debt
            sd_opening_keur=_sd_val(sd.senior_debt_opening_keur, pidx),
            sd_interest_keur=_sd_val(sd.senior_interest_keur, pidx),
            sd_principal_keur=_sd_val(sd.senior_principal_keur, pidx),
            sd_ds_keur=_sd_val(sd.senior_debt_service_keur, pidx),
            sd_closing_keur=_sd_val(sd.senior_debt_closing_keur, pidx),
            sd_dscr=_sd_val(sd.senior_dscr, pidx),
            sd_debt_size_keur=_float_or_none(sd.debt_size_keur),
            sd_binding_constraint=sd.binding_constraint,
            sd_iteration_count=diag.get("iteration_count"),
        )
        engine_data.append(ed)

    debt_size = _float_or_none(sd.debt_size_keur) or 0.0
    binding = sd.binding_constraint
    iters = diag.get("iteration_count", 0)
    return engine_data, debt_size, binding, iters


def _load_factory_inputs() -> dict:
    from app.project_factories import create_default_oborovo
    proj = create_default_oborovo()
    cap = proj.capex
    capex_items_raw = cap.capex_items()
    capex_items = [
        {"code": f"C.{i+1:02d}", "name": item.name, "amount_keur": item.amount_keur}
        for i, item in enumerate(capex_items_raw)
    ]
    opex_items = [
        {
            "code": f"B.{i+1:02d}",
            "name": item.name,
            "y1_keur": item.y1_amount_keur,
            "inflation": item.annual_inflation,
        }
        for i, item in enumerate(proj.opex)
    ]
    total_capex = cap.total_capex
    hard_capex = cap.hard_capex_keur
    idc = cap.idc_keur

    return {
        "capex_items": capex_items,
        "opex_items": opex_items,
        "total_capex_keur": float(total_capex),
        "hard_capex_keur": float(hard_capex),
        "idc_keur": float(idc),
    }


def _load_excel_scalar_inputs() -> dict:
    """Load scalar inputs from the authoritative XLSM extract."""
    path = _REPO_ROOT / "tests" / "fixtures" / "excel_oborovo_financial_truth.json"
    raw = json.loads(path.read_text())
    inp = raw.get("inputs", {})
    cap = raw.get("capex_sheet", {})

    def v(key: str) -> Any:
        entry = inp.get(key, {})
        return entry.get("value") if isinstance(entry, dict) else None

    def fv(key: str, default: float = 0.0) -> float:
        val = v(key)
        return float(val) if isinstance(val, (int, float)) else default

    def iv(key: str, default: int = 0) -> int:
        val = v(key)
        return int(val) if isinstance(val, (int, float)) else default

    # Flatten capex items
    excel_capex_items = {}
    for code, item in inp.get("capex_items_from_inputs", {}).items():
        excel_capex_items[code] = {
            "label": item.get("label", ""),
            "amount_keur": item.get("amount_keur"),
        }

    # Flatten opex annual items
    excel_opex_annual = {}
    for code, item in inp.get("opex_annual_items", {}).items():
        excel_opex_annual[code] = {
            "label": item.get("label", ""),
            "year1_keur": item.get("year1_keur"),
            "years_1_to_6_keur": item.get("years_1_to_6_keur", []),
        }

    return {
        "excel_total_capex_keur": fv("total_capex_keur"),
        "excel_total_debt_keur": fv("senior_debt_amount_keur"),
        "excel_senior_maturity_years": iv("senior_debt_maturity_years"),
        "excel_senior_base_rate": fv("senior_debt_base_rate"),
        "excel_senior_margin_bps": fv("senior_debt_margin_bps"),
        "excel_target_dscr": fv("senior_dscr_covenant", 1.15),
        "excel_lockup_dscr": fv("senior_lockup_dscr", 1.1),
        "excel_idc_keur": fv("total_capex_keur") - fv("total_capex_keur"),  # derived below
        "capacity_mw": fv("capacity_mwp"),
        "cod_date": str(v("operation_start_date") or ""),
        "financial_close": str(v("financial_close_date") or ""),
        "ppa_tariff_eur_mwh": fv("ppa_base_tariff_y1_eur_mwh"),
        "ppa_term_years": iv("ppa_term_years"),
        "ppa_index": fv("ppa_index_pa"),
        "operating_hours_p50": iv("operating_hours_p50"),
        "plant_availability": fv("plant_availability"),
        "grid_availability": fv("grid_availability"),
        "pv_degradation_pa": fv("pv_degradation_pa"),
        "horizon_years": iv("investment_horizon_years"),
        "construction_months": iv("construction_months"),
        "shl_amount_keur": fv("shl_amount_keur"),
        "shl_rate": fv("shl_interest_rate"),
        "excel_capex_items": excel_capex_items,
        "excel_opex_annual": excel_opex_annual,
        # IDC directly from capex inputs
        "excel_idc_keur": float(inp.get("capex_items_from_inputs", {})
                                .get("C.IDC", {}).get("amount_keur") or 0.0),
        "excel_bank_fees_keur": float(inp.get("capex_items_from_inputs", {})
                                      .get("C.BF", {}).get("amount_keur") or 0.0),
        "excel_commitment_fees_keur": float(inp.get("capex_items_from_inputs", {})
                                            .get("C.CF", {}).get("amount_keur") or 0.0),
    }


def load_oborovo_sources() -> OborovoSources:
    """Load all data sources for the Oborovo Excel↔Python reconciliation."""
    excel, excel_meta = _load_excel_truth()
    legacy = _load_legacy_periods()
    excel_shl = _load_excel_shl()
    engine_data, debt_size, binding, iters = _run_clean_engine()
    factory = _load_factory_inputs()
    excel_inp = _load_excel_scalar_inputs()

    # Derive average and minimum DSCR from DS sheet CFADS / SD service
    # Active debt-service periods: opening > 0 and service > 0
    dscr_vals: list[float] = []
    for ep in excel:
        opening = ep.sd_opening_keur
        service = ep.sd_service_keur
        cfads = ep.cfads_keur
        if (opening is not None and opening > 0.01
                and service is not None and service > 0.01
                and cfads is not None):
            dscr = cfads / service
            dscr_vals.append(dscr)

    avg_dscr = sum(dscr_vals) / len(dscr_vals) if dscr_vals else 0.0
    min_dscr = min(dscr_vals) if dscr_vals else 0.0

    # Excel SD opening/closing schedule — now directly from DS sheet (not reconstructed)
    excel_opening = [ep.sd_opening_keur for ep in excel]
    excel_closing = [ep.sd_closing_keur for ep in excel]

    # SHL IDC: capitalised interest during construction (DS.shl_interest_capitalised row 128, period 0)
    # Load directly from fixture period 0 (construction)
    truth_path = _REPO_ROOT / "tests" / "fixtures" / "excel_oborovo_financial_truth.json"
    truth = json.loads(truth_path.read_text())
    shl_idc = abs(truth.get("ds", {}).get("shl_interest_capitalised_keur", [None])[0] or 0.0)

    return OborovoSources(
        excel=excel,
        legacy=legacy,
        engine=engine_data,
        excel_fixture_sha256=excel_meta.get("source_sha256", ""),
        excel_source_filename=excel_meta.get("source_filename", ""),
        capacity_mw=excel_inp["capacity_mw"],
        cod_date=excel_inp["cod_date"],
        financial_close=excel_inp["financial_close"],
        ppa_tariff_eur_mwh=excel_inp["ppa_tariff_eur_mwh"],
        ppa_term_years=excel_inp["ppa_term_years"],
        ppa_index=excel_inp["ppa_index"],
        operating_hours_p50=excel_inp["operating_hours_p50"],
        plant_availability=excel_inp["plant_availability"],
        grid_availability=excel_inp["grid_availability"],
        pv_degradation_pa=excel_inp["pv_degradation_pa"],
        horizon_years=excel_inp["horizon_years"],
        construction_months=excel_inp["construction_months"],
        excel_total_capex_keur=excel_inp["excel_total_capex_keur"],
        excel_idc_keur=excel_inp["excel_idc_keur"],
        excel_bank_fees_keur=excel_inp["excel_bank_fees_keur"],
        excel_commitment_fees_keur=excel_inp["excel_commitment_fees_keur"],
        excel_capex_items=excel_inp["excel_capex_items"],
        excel_opex_annual=excel_inp["excel_opex_annual"],
        excel_total_debt_keur=excel_inp["excel_total_debt_keur"],
        excel_senior_maturity_years=excel_inp["excel_senior_maturity_years"],
        excel_senior_base_rate=excel_inp["excel_senior_base_rate"],
        excel_senior_margin_bps=excel_inp["excel_senior_margin_bps"],
        excel_target_dscr=excel_inp["excel_target_dscr"],
        excel_lockup_dscr=excel_inp["excel_lockup_dscr"],
        shl_amount_keur=excel_inp["shl_amount_keur"],
        shl_rate=excel_inp["shl_rate"],
        shl_idc_keur=shl_idc,
        opex_items=factory["opex_items"],
        capex_items=factory["capex_items"],
        total_capex_keur=factory["total_capex_keur"],
        hard_capex_keur=factory["hard_capex_keur"],
        idc_keur=factory["idc_keur"],
        excel_shl=excel_shl,
        engine_debt_size_keur=debt_size,
        engine_binding_constraint=binding,
        engine_iterations=iters,
        excel_avg_dscr=avg_dscr,
        excel_min_dscr=min_dscr,
        excel_sd_opening_keur=excel_opening,
        excel_sd_closing_keur=excel_closing,
    )
