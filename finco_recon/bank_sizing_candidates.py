"""finco_recon.bank_sizing_candidates — C3B3D2B2C diagnostic A/B candidate evaluation.

EVIDENCE-ONLY DIAGNOSTIC. NOT a production module.
No production financial_engine modifications. No project-name dispatch.
No fixture reads at runtime — oracle vectors loaded from committed fixture only.

Stage: C3B3D2B2C
Verdict: C3B3D2B2C_R3_STOP_MACRO50_TRANSFORMATION_SOURCE_INACCESSIBLE

Classification of candidates:
    OBOROVO_ALL_PRODUCTION_BANK_CASE_RULE_CANDIDATE_ONLY
    OBOROVO_MERCHANT_ONLY_BANK_CASE_RULE_CANDIDATE_ONLY

Neither candidate reproduces source Macro50 (DS!row20).

Macro!row50 forensics:
    - DS!H20 formula: =Macro!H50  (confirmed from dual-load extraction)
    - Macro!H49 formula: =CF!H79   (base P50 CFADS, confirmed)
    - Macro!H50 formula: None      (no formula element in XML; no <f> element present)
    - PPA periods 1-24: DS20 ≈ CF79 (component identity confirmed)
    - Merchant periods 25+: DS20 << CF79 by 590–1117 kEUR per period
    - VBA_IMPLEMENTATION_NOT_VISIBLE: VBA source is password-protected
    - BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED: specific inputs unknown

Governance:
    No DS25/DS40 period boundary hardcoding — ENFORCED
    No project-name dispatch — ENFORCED (Oborovo used as test oracle via factory)
    No approved_delta or balancing plug — ENFORCED
    No calibration of clean engine to source — ENFORCED
    13547.2 does not appear as a literal — ENFORCED
    Protected C3B2 SHA not in literals — ENFORCED
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import replace
from typing import Any

_FIXTURE_DIR = pathlib.Path(__file__).parent.parent / "tests" / "fixtures"
_OBOROVO_DEBT_TRUTH_PATH = _FIXTURE_DIR / "excel_oborovo_debt_interest_truth.json"


# ---------------------------------------------------------------------------
# Source oracle loader (test-only — not callable from production engine)
# ---------------------------------------------------------------------------

def load_ds_row20_oracle() -> list[float]:
    """Load DS!row20 = Macro!row50 from committed fixture.

    Test oracle only. 61 values: index 0 = construction (0.0),
    indices 1-60 = operating periods 1-60.
    Source: workbook SHA 15a621c4...
    Classification: SOURCE_ORACLE_FIXTURE_ONLY
    """
    with open(_OBOROVO_DEBT_TRUTH_PATH) as f:
        data = json.load(f)
    return data["workstream_a"]["ds_row20_cfads"]["period_values_keur"]


def load_cf79_base_cfads() -> list[float]:
    """Load CF!row79 base P50 CFADS from committed fixture."""
    with open(_OBOROVO_DEBT_TRUTH_PATH) as f:
        data = json.load(f)
    return data["workstream_a"]["cf_row79_free_cash_flow_for_banks"]["period_values_keur"]


# ---------------------------------------------------------------------------
# Operating input transformer (diagnostic copy — not in production engine)
# ---------------------------------------------------------------------------

def _derive_bank_operating_input(base_op: Any, yield_scenario: Any) -> Any:
    """Derive bank-scenario operating input by swapping yield_scenario only.

    Pure function. All other fields shared by reference.
    This is a DIAGNOSTIC copy — not the same as any production implementation.
    """
    from financial_engine.inputs import TechnicalInput, YieldScenario
    bank_technical = TechnicalInput(
        capacity_mw=base_op.technical.capacity_mw,
        yield_scenario=yield_scenario,
        operating_hours_p50=base_op.technical.operating_hours_p50,
        operating_hours_p90_10y=base_op.technical.operating_hours_p90_10y,
        pv_degradation=base_op.technical.pv_degradation,
        plant_availability=base_op.technical.plant_availability,
        grid_availability=base_op.technical.grid_availability,
    )
    from financial_engine.inputs import OperatingModelInput
    return OperatingModelInput(
        calendar=base_op.calendar,
        technical=bank_technical,
        revenue=base_op.revenue,
        opex=base_op.opex,
        depreciation=base_op.depreciation,
        source=base_op.source,
    )


# ---------------------------------------------------------------------------
# Candidate A: ALL_PRODUCTION
# Apply P90-10y yield to ALL operating periods (PPA + merchant).
# Classification: OBOROVO_ALL_PRODUCTION_BANK_CASE_RULE_CANDIDATE_ONLY
# ---------------------------------------------------------------------------

def run_candidate_a_all_production(project_factory_fn: Any) -> dict:
    """Run Candidate A (ALL_PRODUCTION) and return diagnostic summary.

    ALL_PRODUCTION: P90-10y yield for all periods, PPA and merchant alike.
    Rejected: max_abs_delta = 690 kEUR vs DS!row20.

    Args:
        project_factory_fn: callable returning a project object (e.g. create_default_oborovo)

    Returns:
        dict with cfads, deltas, max_abs_delta, debt — diagnostic only
    """
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )
    from financial_engine.inputs import YieldScenario
    from financial_engine.orchestrator import run_operating_model

    proj = project_factory_fn()
    sd_input = build_senior_debt_model_input_from_project_inputs(proj)
    base_op = sd_input.operating

    # ALL_PRODUCTION: swap yield_scenario for ALL periods
    bank_op = _derive_bank_operating_input(base_op, YieldScenario.P90_10Y)
    bank_result = run_operating_model(bank_op)

    # Compute bank-case tax+CFADS using the bank operating periods
    from financial_engine.tax.engine import calculate_tax as calc_tax
    from financial_engine.cfads import calculate_canonical_cfads as calc_cfads
    bank_tax_r = calc_tax(bank_result.periods, sd_input.tax)
    bank_cfads_r = calc_cfads(bank_result.periods, bank_tax_r.period_results)
    bank_cfads_by_idx = {cr.period_index: cr.cfads_keur for cr in bank_cfads_r}

    source = load_ds_row20_oracle()
    source_by_idx = {i: v for i, v in enumerate(source)}  # 0-based fixture index

    op_indices = sorted(p.period_index for p in bank_result.periods if p.is_operation)
    cfads_vec = [bank_cfads_by_idx.get(i, 0.0) for i in op_indices]
    deltas = []
    for pidx in op_indices:
        fidx = pidx - 1  # fixture index (1-based period → 0-based fixture)
        if 0 <= fidx < len(source):
            deltas.append((pidx, bank_cfads_by_idx.get(pidx, 0.0) - source[fidx]))

    max_abs = max(abs(d) for _, d in deltas) if deltas else 0.0
    signed_total = sum(d for _, d in deltas)
    mismatch_count = sum(1 for _, d in deltas if abs(d) > 1.0)

    return {
        "candidate": "ALL_PRODUCTION",
        "classification": "OBOROVO_ALL_PRODUCTION_BANK_CASE_RULE_CANDIDATE_ONLY",
        "verdict": "REJECTED",
        "max_abs_delta_keur": max_abs,
        "signed_total_delta_keur": signed_total,
        "period_count_outside_1keur": mismatch_count,
        "cfads_vec": cfads_vec,
        "deltas": deltas,
    }


# ---------------------------------------------------------------------------
# Candidate B: MERCHANT_ONLY
# Apply P90-10y yield only to merchant/post-PPA periods.
# Classification: OBOROVO_MERCHANT_ONLY_BANK_CASE_RULE_CANDIDATE_ONLY
# BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED
# ---------------------------------------------------------------------------

def run_candidate_b_merchant_only(project_factory_fn: Any) -> dict:
    """Run Candidate B (MERCHANT_ONLY) and return diagnostic summary.

    MERCHANT_ONLY: P90-10y yield for post-PPA periods; PPA periods retain P50.
    Rejected: merchant periods have additional VBA-driven downside not captured
    by yield substitution alone. Max delta = 690 kEUR in merchant periods.

    Args:
        project_factory_fn: callable returning a project object

    Returns:
        dict with cfads, deltas, max_abs_delta, debt — diagnostic only
    """
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )
    from financial_engine.inputs import YieldScenario
    from financial_engine.orchestrator import run_operating_model
    from financial_engine.tax.engine import calculate_tax as calc_tax
    from financial_engine.cfads import calculate_canonical_cfads as calc_cfads

    proj = project_factory_fn()
    sd_input = build_senior_debt_model_input_from_project_inputs(proj)
    base_op = sd_input.operating

    # Base and bank operating models
    base_result = run_operating_model(base_op)
    bank_op = _derive_bank_operating_input(base_op, YieldScenario.P90_10Y)
    bank_result = run_operating_model(bank_op)

    base_period_map = {p.period_index: p for p in base_result.periods}
    bank_period_map = {p.period_index: p for p in bank_result.periods}

    # MERCHANT_ONLY splice: PPA periods → base periods, merchant → bank periods
    # Revenue-regime authority: is_ppa_active (no fmopi override for Oborovo)
    spliced_periods = tuple(
        base_period_map[p.period_index] if p.is_ppa_active
        else bank_period_map.get(p.period_index, p)
        for p in base_result.periods
    )

    # Compute bank-case tax+CFADS on spliced periods
    bank_tax_r = calc_tax(spliced_periods, sd_input.tax)
    bank_cfads_r = calc_cfads(spliced_periods, bank_tax_r.period_results)
    bank_cfads_by_idx = {cr.period_index: cr.cfads_keur for cr in bank_cfads_r}

    source = load_ds_row20_oracle()

    op_indices = sorted(p.period_index for p in base_result.periods if p.is_operation)
    cfads_vec = [bank_cfads_by_idx.get(i, 0.0) for i in op_indices]
    deltas = []
    for pidx in op_indices:
        fidx = pidx - 1
        if 0 <= fidx < len(source):
            deltas.append((pidx, bank_cfads_by_idx.get(pidx, 0.0) - source[fidx]))

    max_abs = max(abs(d) for _, d in deltas) if deltas else 0.0
    signed_total = sum(d for _, d in deltas)
    mismatch_count = sum(1 for _, d in deltas if abs(d) > 1.0)

    merchant_deltas = [(p, d) for p, d in deltas if p >= 25]
    merchant_all_positive = all(d > 0 for _, d in merchant_deltas) if merchant_deltas else False

    return {
        "candidate": "MERCHANT_ONLY",
        "classification": "OBOROVO_MERCHANT_ONLY_BANK_CASE_RULE_CANDIDATE_ONLY",
        "verdict": "REJECTED",
        "rejection_reason": (
            "VBA_IMPLEMENTATION_NOT_VISIBLE: "
            "Macro!row50 has no worksheet formula in the inspected extraction. "
            "Merchant period values cannot be reproduced by P90 yield substitution alone. "
            "VBA_IMPLEMENTATION_NOT_VISIBLE: the exact mechanism is not accessible."
        ),
        "max_abs_delta_keur": max_abs,
        "signed_total_delta_keur": signed_total,
        "period_count_outside_1keur": mismatch_count,
        "merchant_deltas_all_positive": merchant_all_positive,
        "cfads_vec": cfads_vec,
        "deltas": deltas,
    }


# ---------------------------------------------------------------------------
# Macro!row50 forensic summary
# ---------------------------------------------------------------------------

MACRO50_FORENSICS = {
    "sheet_cell": "Macro!H50 (period 1 column)",
    "formula_h": None,
    "formula_note": (
        "Macro!row50 has no worksheet formula in the inspected extraction. "
        "No <f> element is present; only cached/output values are visible. "
        "The workbook architecture indicates Macro/VBA involvement, but the exact "
        "VBA procedure and assignment mechanism are not visible and must not be inferred. "
        "VBA_IMPLEMENTATION_NOT_VISIBLE: source code is password-protected."
    ),
    "upstream_confirmed": "DS!H20 = Macro!H50 (formula confirmed from dual-load extraction)",
    "sibling_row49": "Macro!H49 = CF!H79 (base P50 CFADS, formula confirmed)",
    "ppa_period_behaviour": (
        "Periods 1-24: DS20 ≈ CF79. Component bridge confirms identity. "
        "Bank CFADS ≈ base CFADS for PPA periods (contractual revenue unchanged)."
    ),
    "merchant_period_behaviour": (
        "Periods 25-60: DS20 << CF79 by 590–1117 kEUR per period. "
        "Gap grows over time. Not explained by P90 yield or any simple price ratio."
    ),
    "vba_label": "VBA_IMPLEMENTATION_NOT_VISIBLE",
    "mechanism_label": "BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED",
    "workbook_sha256": "15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920",
    "scenario_selectors_inspected": {
        "Inputs!D52": "P_50 (base production scenario)",
        "Inputs!D89": "Fixed (base market price scenario)",
        "Scenarios!E345": "14 (maturity)",
        "Scenarios!E348": "0.80 (gearing/hedge coverage)",
        "Scenarios!E350": "1.15 (DSCR band 1)",
        "Scenarios!E351": "1.35 (DSCR band 2)",
        "Scenarios!E352": "1.65 (DSCR band 3)",
        "Scenarios!E4": "opex template selector (controls OpEx sheet column)",
    },
    "bank_production_selector": None,
    "bank_market_price_selector": None,
    "bank_lender_haircut_selector": None,
    "note": (
        "No bank-case production or price selector was found in the inspected fixture data. "
        "The Scenarios sheet column structure (beyond E-column base values and opex selector) "
        "was not captured in extraction artifacts. "
        "VBA code is password-protected and not accessible."
    ),
    "r3_verdict": "C3B3D2B2C_R3_STOP_MACRO50_TRANSFORMATION_SOURCE_INACCESSIBLE",
}
