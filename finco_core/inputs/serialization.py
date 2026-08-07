"""Full-fidelity ProjectInputs serialization — to/from plain JSON-safe dict.

Rules:
- All nested frozen dataclasses are serialized recursively.
- date → ISO-8601 string; reconstructed via date.fromisoformat().
- Enum → .value (string); reconstructed via EnumClass(value).
- tuple[T, ...] → list; reconstructed via tuple(list).
- tuple[tuple[int, float], ...] → list of [int, float] pairs (OpexItem.step_changes).
- None-valued Optional fields → None in dict.
- No financial logic. Pure structural round-trip only.

Public API:
    project_inputs_to_dict(inputs)  -> dict
    project_inputs_from_dict(d)     -> ProjectInputs
"""
from __future__ import annotations

from datetime import date
from typing import Any

from finco_core.inputs._models import (
    AssetClass,
    CapexItem,
    CapexStructure,
    DebtSizingMethod,
    DebtSizingMode,
    EquityIRRMethod,
    FinancingParams,
    OpexItem,
    PeriodFrequency,
    ProjectInfo,
    ProjectInputs,
    RevenueAdjustmentSchedule,
    RevenueParams,
    SHLRepaymentMethod,
    TaxDepreciationMode,
    TaxParams,
    TechnicalParams,
    YieldScenario,
)
from finco_core.inputs.bess import BessParams
from finco_core.inputs.senior_rate_schedule import (
    SeniorDayCountConvention,
    SeniorDebtInterestConfig,
    SeniorHedgeConfig,
    SeniorRateMode,
    SeniorRateSchedule,
)
from finco_core.inputs.senior_sculpting import (
    SeniorFinalRepaymentPolicy,
    SeniorPrincipalCapPolicy,
    SeniorReserveTreatment,
    SeniorSculptingConfig,
    SeniorSculptingMode,
)
from finco_core.tax.construction_pl import ConstructionPLStatement

_SCHEMA_VERSION = "v3-6"


# ── Serialization helpers ──────────────────────────────────────────────────────

def _ser_date(d: date | None) -> str | None:
    return d.isoformat() if d is not None else None


def _ser_enum(e: Any | None) -> str | None:
    return e.value if e is not None else None


def _ser_tuple_float(t: tuple) -> list:
    return list(t)


def _ser_step_changes(t: tuple) -> list:
    return [[int(year), float(amt)] for year, amt in t]


def _ser_bess(b: BessParams | None) -> dict | None:
    if b is None:
        return None
    return {
        "power_mw": b.power_mw,
        "energy_mwh": b.energy_mwh,
        "cycles_per_year": b.cycles_per_year,
        "round_trip_efficiency": b.round_trip_efficiency,
        "availability": b.availability,
        "annual_degradation": b.annual_degradation,
        "arbitrage_spread_eur_mwh": b.arbitrage_spread_eur_mwh,
        "ancillary_revenue_eur_mw_year": b.ancillary_revenue_eur_mw_year,
        "capacity_revenue_eur_mw_year": b.capacity_revenue_eur_mw_year,
        "augmentation_capex_keur": b.augmentation_capex_keur,
    }


def _ser_construction_pl(c: ConstructionPLStatement | None) -> dict | None:
    if c is None:
        return None
    return {
        "idc_keur": c.idc_keur,
        "bank_fees_keur": c.bank_fees_keur,
        "commitment_fees_keur": c.commitment_fees_keur,
        "pre_operational_opex_keur": c.pre_operational_opex_keur,
        "construction_period_revenue_keur": c.construction_period_revenue_keur,
        "other_book_tax_difference_keur": c.other_book_tax_difference_keur,
    }


def _ser_revenue_adjustment(r: RevenueAdjustmentSchedule | None) -> dict | None:
    if r is None:
        return None
    return {
        "constant_value": r.constant_value,
        "annual_values": list(r.annual_values),
        "semiannual_values": list(r.semiannual_values),
    }


def _ser_capex_item(item: CapexItem) -> dict:
    return {
        "name": item.name,
        "amount_keur": item.amount_keur,
        "y0_share": item.y0_share,
        "spending_profile": list(item.spending_profile),
        "asset_class": item.asset_class.value,
        "useful_life_override": item.useful_life_override,
    }


def _ser_senior_hedge(h: SeniorHedgeConfig | None) -> dict | None:
    if h is None:
        return None
    return {
        "hedge_pct": h.hedge_pct,
        "fixed_base_rate": h.fixed_base_rate,
        "floating_base_rate_curve": list(h.floating_base_rate_curve),
        "floating_curve_buffer_pct": h.floating_curve_buffer_pct,
    }


def _ser_senior_rate_schedule(s: SeniorRateSchedule) -> dict:
    return {
        "mode": s.mode.value,
        "flat_all_in_rate": s.flat_all_in_rate,
        "fixed_base_rate": s.fixed_base_rate,
        "margin_rate": s.margin_rate,
        "hedge": _ser_senior_hedge(s.hedge),
        "explicit_all_in_rates": list(s.explicit_all_in_rates),
    }


def _ser_senior_interest_config(c: SeniorDebtInterestConfig) -> dict:
    return {
        "enabled": c.enabled,
        "rate_schedule": _ser_senior_rate_schedule(c.rate_schedule),
        "day_count": c.day_count.value,
        "explicit_period_fractions": list(c.explicit_period_fractions),
    }


def _ser_senior_sculpting_config(c: SeniorSculptingConfig) -> dict:
    return {
        "enabled": c.enabled,
        "mode": c.mode.value,
        "explicit_debt_service_schedule": list(c.explicit_debt_service_schedule),
        "explicit_principal_schedule": list(c.explicit_principal_schedule),
        "target_dscr_schedule": list(c.target_dscr_schedule),
        "available_senior_cfads_schedule": list(c.available_senior_cfads_schedule),
        "debt_service_availability_schedule": list(c.debt_service_availability_schedule),
        "final_repayment_policy": c.final_repayment_policy.value,
        "principal_cap_policy": c.principal_cap_policy.value,
        "reserve_treatment": c.reserve_treatment.value,
    }


# ── Public serializer ──────────────────────────────────────────────────────────

def project_inputs_to_dict(inputs: ProjectInputs) -> dict:
    """Serialize ProjectInputs to a full-fidelity JSON-safe dict."""
    info = inputs.info
    tech = inputs.technical
    cap = inputs.capex
    rev = inputs.revenue
    fin = inputs.financing
    tax = inputs.tax

    capex_item_fields = (
        "epc_contract", "production_units", "epc_other", "grid_connection",
        "ops_prep", "insurances", "lease_tax", "construction_mgmt_a",
        "commissioning", "audit_legal", "construction_mgmt_b", "contingencies",
        "taxes", "project_acquisition", "project_rights",
    )

    return {
        "_schema_version": _SCHEMA_VERSION,
        "info": {
            "name": info.name,
            "company": info.company,
            "code": info.code,
            "country_iso": info.country_iso,
            "financial_close": _ser_date(info.financial_close),
            "construction_months": info.construction_months,
            "cod_date": _ser_date(info.cod_date),
            "horizon_years": info.horizon_years,
            "period_frequency": info.period_frequency.value,
            "use_opex_line_item_engine": info.use_opex_line_item_engine,
            "use_construction_schedule_engine": info.use_construction_schedule_engine,
            "use_senior_rate_schedule_engine": info.use_senior_rate_schedule_engine,
            "use_senior_sculpting_basis_engine": info.use_senior_sculpting_basis_engine,
            "use_shl_fcf_waterfall_engine": info.use_shl_fcf_waterfall_engine,
            "use_shl_canonical_engine": info.use_shl_canonical_engine,
            "use_canonical_tax_depreciation_bridge": info.use_canonical_tax_depreciation_bridge,
            "use_depreciation_canonical_engine": info.use_depreciation_canonical_engine,
            "use_tax_bridge_engine": info.use_tax_bridge_engine,
            "use_senior_debt_sizing_engine": info.use_senior_debt_sizing_engine,
            "use_shl_gross_accrued_for_pnl": info.use_shl_gross_accrued_for_pnl,
            "use_book_depreciation_for_pnl": info.use_book_depreciation_for_pnl,
        },
        "technical": {
            "capacity_mw": tech.capacity_mw,
            "yield_scenario": tech.yield_scenario,
            "operating_hours_p50": tech.operating_hours_p50,
            "operating_hours_p90_1y": tech.operating_hours_p90_1y,
            "operating_hours_p90_10y": tech.operating_hours_p90_10y,
            "operating_hours_p99_1y": tech.operating_hours_p99_1y,
            "pv_degradation": tech.pv_degradation,
            "bess_degradation": tech.bess_degradation,
            "plant_availability": tech.plant_availability,
            "grid_availability": tech.grid_availability,
            "bess_enabled": tech.bess_enabled,
            "bess": _ser_bess(tech.bess),
        },
        "capex": {
            **{f: _ser_capex_item(getattr(cap, f)) for f in capex_item_fields},
            "idc_keur": cap.idc_keur,
            "commitment_fees_keur": cap.commitment_fees_keur,
            "bank_fees_keur": cap.bank_fees_keur,
            "other_financial_keur": cap.other_financial_keur,
            "vat_costs_keur": cap.vat_costs_keur,
            "reserve_accounts_keur": cap.reserve_accounts_keur,
        },
        "opex": [
            {
                "name": item.name,
                "y1_amount_keur": item.y1_amount_keur,
                "annual_inflation": item.annual_inflation,
                "step_changes": _ser_step_changes(item.step_changes),
                "percentage_of_opex": item.percentage_of_opex,
            }
            for item in inputs.opex
        ],
        "revenue": {
            "ppa_base_tariff": rev.ppa_base_tariff,
            "ppa_term_years": rev.ppa_term_years,
            "ppa_index": rev.ppa_index,
            "ppa_production_share": rev.ppa_production_share,
            "market_scenario": rev.market_scenario,
            "market_prices_curve": list(rev.market_prices_curve),
            "market_inflation": rev.market_inflation,
            "balancing_cost_pv": rev.balancing_cost_pv,
            "balancing_cost_bess": rev.balancing_cost_bess,
            "balancing_cost_wind_eur_mwh": rev.balancing_cost_wind_eur_mwh,
            "co2_enabled": rev.co2_enabled,
            "co2_price_eur": rev.co2_price_eur,
            "co2_certificate_price_eur_per_mwh": rev.co2_certificate_price_eur_per_mwh,
            "balancing_cost_eur_per_mwh": rev.balancing_cost_eur_per_mwh,
            "balancing_cost_schedule": _ser_revenue_adjustment(rev.balancing_cost_schedule),
            "co2_sales_schedule": _ser_revenue_adjustment(rev.co2_sales_schedule),
            "first_merchant_operating_period_index": rev.first_merchant_operating_period_index,
        },
        "financing": {
            "share_capital_keur": fin.share_capital_keur,
            "share_premium_keur": fin.share_premium_keur,
            "shl_amount_keur": fin.shl_amount_keur,
            "shl_rate": fin.shl_rate,
            "gearing_ratio": fin.gearing_ratio,
            "senior_debt_amount_keur": fin.senior_debt_amount_keur,
            "senior_tenor_years": fin.senior_tenor_years,
            "base_rate": fin.base_rate,
            "margin_bps": fin.margin_bps,
            "floating_share": fin.floating_share,
            "fixed_share": fin.fixed_share,
            "hedge_coverage": fin.hedge_coverage,
            "commitment_fee": fin.commitment_fee,
            "arrangement_fee": fin.arrangement_fee,
            "structuring_fee": fin.structuring_fee,
            "target_dscr": fin.target_dscr,
            "lockup_dscr": fin.lockup_dscr,
            "min_llcr": fin.min_llcr,
            "amortization_type": fin.amortization_type,
            "fixed_ds_keur": fin.fixed_ds_keur,
            "dsra_months": fin.dsra_months,
            "equity_irr_method": fin.equity_irr_method,
            "debt_sizing_method": fin.debt_sizing_method,
            "debt_sizing_mode": _ser_enum(fin.debt_sizing_mode),
            "target_min_dscr": fin.target_min_dscr,
            "flat_dscr_target": fin.flat_dscr_target,
            "frozen_schedule_note": fin.frozen_schedule_note,
            "use_frozen_excel_senior_debt_schedule": fin.use_frozen_excel_senior_debt_schedule,
            "frozen_senior_ds_fixture_path": fin.frozen_senior_ds_fixture_path,
            "fixed_debt_keur": fin.fixed_debt_keur,
            "dscr_schedule": fin.dscr_schedule,
            "senior_debt_interest_config": _ser_senior_interest_config(fin.senior_debt_interest_config),
            "senior_sculpting_config": _ser_senior_sculpting_config(fin.senior_sculpting_config),
            "shl_repayment_method": fin.shl_repayment_method,
            "shl_pik_switch_period": fin.shl_pik_switch_period,
            "shl_tenor_years": fin.shl_tenor_years,
            "shl_idc_keur": fin.shl_idc_keur,
            "shl_fcf_waterfall_cash_schedule_keur": list(fin.shl_fcf_waterfall_cash_schedule_keur),
            "shl_fcf_waterfall_minimum_cash_retained_keur": fin.shl_fcf_waterfall_minimum_cash_retained_keur,
            "use_senior_sweep_cash_cap_for_shl": fin.use_senior_sweep_cash_cap_for_shl,
            "use_tuho_r99_input_engine": fin.use_tuho_r99_input_engine,
            "use_tuho_shl_repayment_alignment": fin.use_tuho_shl_repayment_alignment,
            "tuho_shl_principal_eligibility_start_period": fin.tuho_shl_principal_eligibility_start_period,
        },
        "tax": {
            "corporate_rate": tax.corporate_rate,
            "loss_carryforward_years": tax.loss_carryforward_years,
            "loss_carryforward_cap": tax.loss_carryforward_cap,
            "prior_tax_loss_keur": tax.prior_tax_loss_keur,
            "legal_reserve_cap": tax.legal_reserve_cap,
            "construction_pl": _ser_construction_pl(tax.construction_pl),
            "thin_cap_enabled": tax.thin_cap_enabled,
            "thin_cap_de_ratio": tax.thin_cap_de_ratio,
            "atad_ebitda_limit": tax.atad_ebitda_limit,
            "atad_min_interest_keur": tax.atad_min_interest_keur,
            "wht_sponsor_dividends": tax.wht_sponsor_dividends,
            "wht_sponsor_shl_interest": tax.wht_sponsor_shl_interest,
            "shl_cap_applies": tax.shl_cap_applies,
            "cit_cash_tax_start_operating_index": tax.cit_cash_tax_start_operating_index,
            "tax_depreciation_mode": tax.tax_depreciation_mode.value,
            "tax_deductible_book_dep_pct": tax.tax_deductible_book_dep_pct,
            "tax_dep_basis_source_owned": tax.tax_dep_basis_source_owned,
            "cash_tax_timing_source_owned": tax.cash_tax_timing_source_owned,
        },
    }


# ── Deserialization helpers ────────────────────────────────────────────────────

def _deser_date(s: str | None) -> date | None:
    return date.fromisoformat(s) if s is not None else None


def _deser_bess(d: dict | None) -> BessParams | None:
    if d is None:
        return None
    return BessParams(**d)


def _deser_construction_pl(d: dict | None) -> ConstructionPLStatement | None:
    if d is None:
        return None
    return ConstructionPLStatement(**d)


def _deser_revenue_adjustment(d: dict | None) -> RevenueAdjustmentSchedule | None:
    if d is None:
        return None
    return RevenueAdjustmentSchedule(
        constant_value=d["constant_value"],
        annual_values=tuple(d["annual_values"]),
        semiannual_values=tuple(d["semiannual_values"]),
    )


def _deser_capex_item(d: dict) -> CapexItem:
    return CapexItem(
        name=d["name"],
        amount_keur=d["amount_keur"],
        y0_share=d["y0_share"],
        spending_profile=tuple(d["spending_profile"]),
        asset_class=AssetClass(d["asset_class"]),
        useful_life_override=d.get("useful_life_override"),
    )


def _deser_senior_hedge(d: dict | None) -> SeniorHedgeConfig | None:
    if d is None:
        return None
    return SeniorHedgeConfig(
        hedge_pct=d["hedge_pct"],
        fixed_base_rate=d["fixed_base_rate"],
        floating_base_rate_curve=tuple(d["floating_base_rate_curve"]),
        floating_curve_buffer_pct=d["floating_curve_buffer_pct"],
    )


def _deser_senior_rate_schedule(d: dict) -> SeniorRateSchedule:
    return SeniorRateSchedule(
        mode=SeniorRateMode(d["mode"]),
        flat_all_in_rate=d["flat_all_in_rate"],
        fixed_base_rate=d["fixed_base_rate"],
        margin_rate=d["margin_rate"],
        hedge=_deser_senior_hedge(d.get("hedge")),
        explicit_all_in_rates=tuple(d["explicit_all_in_rates"]),
    )


def _deser_senior_interest_config(d: dict) -> SeniorDebtInterestConfig:
    return SeniorDebtInterestConfig(
        enabled=d["enabled"],
        rate_schedule=_deser_senior_rate_schedule(d["rate_schedule"]),
        day_count=SeniorDayCountConvention(d["day_count"]),
        explicit_period_fractions=tuple(d["explicit_period_fractions"]),
    )


def _deser_senior_sculpting_config(d: dict) -> SeniorSculptingConfig:
    return SeniorSculptingConfig(
        enabled=d["enabled"],
        mode=SeniorSculptingMode(d["mode"]),
        explicit_debt_service_schedule=tuple(d["explicit_debt_service_schedule"]),
        explicit_principal_schedule=tuple(d["explicit_principal_schedule"]),
        target_dscr_schedule=tuple(d["target_dscr_schedule"]),
        available_senior_cfads_schedule=tuple(d["available_senior_cfads_schedule"]),
        debt_service_availability_schedule=tuple(d.get("debt_service_availability_schedule", ())),
        final_repayment_policy=SeniorFinalRepaymentPolicy(d["final_repayment_policy"]),
        principal_cap_policy=SeniorPrincipalCapPolicy(d["principal_cap_policy"]),
        reserve_treatment=SeniorReserveTreatment(d["reserve_treatment"]),
    )


# ── Public deserializer ────────────────────────────────────────────────────────

def project_inputs_from_dict(d: dict) -> ProjectInputs:
    """Reconstruct a ProjectInputs from a dict produced by project_inputs_to_dict."""
    info_d = d["info"]
    tech_d = d["technical"]
    cap_d = d["capex"]
    rev_d = d["revenue"]
    fin_d = d["financing"]
    tax_d = d["tax"]

    capex_item_fields = (
        "epc_contract", "production_units", "epc_other", "grid_connection",
        "ops_prep", "insurances", "lease_tax", "construction_mgmt_a",
        "commissioning", "audit_legal", "construction_mgmt_b", "contingencies",
        "taxes", "project_acquisition", "project_rights",
    )

    info = ProjectInfo(
        name=info_d["name"],
        company=info_d["company"],
        code=info_d["code"],
        country_iso=info_d["country_iso"],
        financial_close=date.fromisoformat(info_d["financial_close"]),
        construction_months=info_d["construction_months"],
        cod_date=date.fromisoformat(info_d["cod_date"]),
        horizon_years=info_d["horizon_years"],
        period_frequency=PeriodFrequency(info_d["period_frequency"]),
        use_opex_line_item_engine=info_d.get("use_opex_line_item_engine", False),
        use_construction_schedule_engine=info_d.get("use_construction_schedule_engine", False),
        use_senior_rate_schedule_engine=info_d.get("use_senior_rate_schedule_engine", False),
        use_senior_sculpting_basis_engine=info_d.get("use_senior_sculpting_basis_engine", False),
        use_shl_fcf_waterfall_engine=info_d.get("use_shl_fcf_waterfall_engine", False),
        use_shl_canonical_engine=info_d.get("use_shl_canonical_engine", False),
        use_canonical_tax_depreciation_bridge=info_d.get("use_canonical_tax_depreciation_bridge", False),
        use_depreciation_canonical_engine=info_d.get("use_depreciation_canonical_engine", False),
        use_tax_bridge_engine=info_d.get("use_tax_bridge_engine", False),
        use_senior_debt_sizing_engine=info_d.get("use_senior_debt_sizing_engine", False),
        use_shl_gross_accrued_for_pnl=info_d.get("use_shl_gross_accrued_for_pnl", False),
        use_book_depreciation_for_pnl=info_d.get("use_book_depreciation_for_pnl", False),
    )

    technical = TechnicalParams(
        capacity_mw=tech_d["capacity_mw"],
        yield_scenario=tech_d["yield_scenario"],
        operating_hours_p50=tech_d.get("operating_hours_p50", 0.0),
        operating_hours_p90_1y=tech_d.get("operating_hours_p90_1y"),
        operating_hours_p90_10y=tech_d.get("operating_hours_p90_10y", 0.0),
        operating_hours_p99_1y=tech_d.get("operating_hours_p99_1y"),
        pv_degradation=tech_d.get("pv_degradation", 0.004),
        bess_degradation=tech_d.get("bess_degradation", 0.003),
        plant_availability=tech_d.get("plant_availability", 0.99),
        grid_availability=tech_d.get("grid_availability", 0.99),
        bess_enabled=tech_d.get("bess_enabled", False),
        bess=_deser_bess(tech_d.get("bess")),
    )

    capex = CapexStructure(
        **{f: _deser_capex_item(cap_d[f]) for f in capex_item_fields},
        idc_keur=cap_d.get("idc_keur", 0.0),
        commitment_fees_keur=cap_d.get("commitment_fees_keur", 0.0),
        bank_fees_keur=cap_d.get("bank_fees_keur", 0.0),
        other_financial_keur=cap_d.get("other_financial_keur", 0.0),
        vat_costs_keur=cap_d.get("vat_costs_keur", 0.0),
        reserve_accounts_keur=cap_d.get("reserve_accounts_keur", 0.0),
    )

    opex = tuple(
        OpexItem(
            name=item["name"],
            y1_amount_keur=item["y1_amount_keur"],
            annual_inflation=item.get("annual_inflation", 0.02),
            step_changes=tuple(tuple(pair) for pair in item.get("step_changes", [])),
            percentage_of_opex=item.get("percentage_of_opex", 0.0),
        )
        for item in d["opex"]
    )

    revenue = RevenueParams(
        ppa_base_tariff=rev_d["ppa_base_tariff"],
        ppa_term_years=rev_d["ppa_term_years"],
        ppa_index=rev_d.get("ppa_index", 0.02),
        ppa_production_share=rev_d.get("ppa_production_share", 1.0),
        market_scenario=rev_d.get("market_scenario", "Central"),
        market_prices_curve=tuple(rev_d.get("market_prices_curve", [])),
        market_inflation=rev_d.get("market_inflation", 0.02),
        balancing_cost_pv=rev_d.get("balancing_cost_pv", 0.025),
        balancing_cost_bess=rev_d.get("balancing_cost_bess", 0.025),
        balancing_cost_wind_eur_mwh=rev_d.get("balancing_cost_wind_eur_mwh", 0.0),
        co2_enabled=rev_d.get("co2_enabled", False),
        co2_price_eur=rev_d.get("co2_price_eur", 1.5),
        co2_certificate_price_eur_per_mwh=rev_d.get("co2_certificate_price_eur_per_mwh", 0.0),
        balancing_cost_eur_per_mwh=rev_d.get("balancing_cost_eur_per_mwh", 0.0),
        balancing_cost_schedule=_deser_revenue_adjustment(rev_d.get("balancing_cost_schedule")),
        co2_sales_schedule=_deser_revenue_adjustment(rev_d.get("co2_sales_schedule")),
        first_merchant_operating_period_index=rev_d.get("first_merchant_operating_period_index"),
    )

    dsm_raw = fin_d.get("debt_sizing_mode")
    financing = FinancingParams(
        share_capital_keur=fin_d.get("share_capital_keur", 500.0),
        share_premium_keur=fin_d.get("share_premium_keur", 0.0),
        shl_amount_keur=fin_d.get("shl_amount_keur", 13547.2),
        shl_rate=fin_d.get("shl_rate", 0.08),
        gearing_ratio=fin_d.get("gearing_ratio", 0.7524),
        senior_debt_amount_keur=fin_d.get("senior_debt_amount_keur", 0.0),
        senior_tenor_years=fin_d.get("senior_tenor_years", 14),
        base_rate=fin_d.get("base_rate", 0.03),
        margin_bps=fin_d.get("margin_bps", 265),
        floating_share=fin_d.get("floating_share", 0.2),
        fixed_share=fin_d.get("fixed_share", 0.8),
        hedge_coverage=fin_d.get("hedge_coverage", 0.8),
        commitment_fee=fin_d.get("commitment_fee", 0.0105),
        arrangement_fee=fin_d.get("arrangement_fee", 0.0),
        structuring_fee=fin_d.get("structuring_fee", 0.01),
        target_dscr=fin_d.get("target_dscr", 1.15),
        lockup_dscr=fin_d.get("lockup_dscr", 1.10),
        min_llcr=fin_d.get("min_llcr", 1.15),
        amortization_type=fin_d.get("amortization_type", "sculpted"),
        fixed_ds_keur=fin_d.get("fixed_ds_keur", 0.0),
        dsra_months=fin_d.get("dsra_months", 6),
        equity_irr_method=fin_d.get("equity_irr_method", "equity_only"),
        debt_sizing_method=fin_d.get("debt_sizing_method", "dscr_sculpt"),
        debt_sizing_mode=DebtSizingMode(dsm_raw) if dsm_raw is not None else None,
        target_min_dscr=fin_d.get("target_min_dscr"),
        flat_dscr_target=fin_d.get("flat_dscr_target"),
        frozen_schedule_note=fin_d.get("frozen_schedule_note"),
        use_frozen_excel_senior_debt_schedule=fin_d.get("use_frozen_excel_senior_debt_schedule", False),
        frozen_senior_ds_fixture_path=fin_d.get("frozen_senior_ds_fixture_path"),
        fixed_debt_keur=fin_d.get("fixed_debt_keur"),
        dscr_schedule=fin_d.get("dscr_schedule"),
        senior_debt_interest_config=_deser_senior_interest_config(
            fin_d["senior_debt_interest_config"]
        ),
        senior_sculpting_config=_deser_senior_sculpting_config(
            fin_d["senior_sculpting_config"]
        ),
        shl_repayment_method=fin_d.get("shl_repayment_method", "bullet"),
        shl_pik_switch_period=fin_d.get("shl_pik_switch_period", 0),
        shl_tenor_years=fin_d.get("shl_tenor_years", 0),
        shl_idc_keur=fin_d.get("shl_idc_keur", 0.0),
        shl_fcf_waterfall_cash_schedule_keur=tuple(
            fin_d.get("shl_fcf_waterfall_cash_schedule_keur", [])
        ),
        shl_fcf_waterfall_minimum_cash_retained_keur=fin_d.get(
            "shl_fcf_waterfall_minimum_cash_retained_keur", 0.0
        ),
        use_senior_sweep_cash_cap_for_shl=fin_d.get("use_senior_sweep_cash_cap_for_shl", False),
        use_tuho_r99_input_engine=fin_d.get("use_tuho_r99_input_engine", False),
        use_tuho_shl_repayment_alignment=fin_d.get("use_tuho_shl_repayment_alignment", False),
        tuho_shl_principal_eligibility_start_period=fin_d.get(
            "tuho_shl_principal_eligibility_start_period"
        ),
    )

    tax = TaxParams(
        corporate_rate=tax_d.get("corporate_rate", 0.10),
        loss_carryforward_years=tax_d.get("loss_carryforward_years", 5),
        loss_carryforward_cap=tax_d.get("loss_carryforward_cap", 1.0),
        prior_tax_loss_keur=tax_d.get("prior_tax_loss_keur", 0.0),
        legal_reserve_cap=tax_d.get("legal_reserve_cap", 0.10),
        construction_pl=_deser_construction_pl(tax_d.get("construction_pl")),
        thin_cap_enabled=tax_d.get("thin_cap_enabled", False),
        thin_cap_de_ratio=tax_d.get("thin_cap_de_ratio", 0.8),
        atad_ebitda_limit=tax_d.get("atad_ebitda_limit", 0.30),
        atad_min_interest_keur=tax_d.get("atad_min_interest_keur", 3000.0),
        wht_sponsor_dividends=tax_d.get("wht_sponsor_dividends", 0.05),
        wht_sponsor_shl_interest=tax_d.get("wht_sponsor_shl_interest", 0.0),
        shl_cap_applies=tax_d.get("shl_cap_applies", True),
        cit_cash_tax_start_operating_index=tax_d.get("cit_cash_tax_start_operating_index"),
        tax_depreciation_mode=TaxDepreciationMode(
            tax_d.get("tax_depreciation_mode", TaxDepreciationMode.BOOK_BASED_PERCENTAGE.value)
        ),
        tax_deductible_book_dep_pct=tax_d.get("tax_deductible_book_dep_pct", 1.0),
        tax_dep_basis_source_owned=tax_d.get("tax_dep_basis_source_owned", False),
        cash_tax_timing_source_owned=tax_d.get("cash_tax_timing_source_owned", False),
    )

    return ProjectInputs(
        info=info,
        technical=technical,
        capex=capex,
        opex=opex,
        revenue=revenue,
        financing=financing,
        tax=tax,
    )
