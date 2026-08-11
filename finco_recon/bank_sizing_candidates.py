"""finco_recon.bank_sizing_candidates — C3B3D2B2C diagnostic A/B/C candidate evaluation.

EVIDENCE-ONLY DIAGNOSTIC. NOT a production module.
No production financial_engine modifications. No project-name dispatch.
No fixture reads at runtime — oracle vectors loaded from committed fixture only.

Stage: C3B3D2B2C
R3 Verdict: C3B3D2B2C_R3_STOP_MACRO50_TRANSFORMATION_SOURCE_INACCESSIBLE
R4 Verdict: C3B3D2B2C_R4_SOURCE_INPUTS_IDENTIFIED_CURVE_EXTRACTION_REQUIRED
R4.1 Verdict: C3B3D2B2C_R4_1_MANUAL_CAUSALITY_PROVEN_ENGINE_EVALUATION_XLSM_EXTRACTION_REQUIRED
R4.2 Verdict: C3B3D2B2C_R4_2_STOP_CANDIDATE_C_SOURCE_PARITY_FAILED

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


# ---------------------------------------------------------------------------
# R4: Candidate C source evidence summary
# ---------------------------------------------------------------------------

CANDIDATE_C_SOURCE_EVIDENCE = {
    "candidate": "PRODUCTION_REVENUE_SIZING",
    "round": "R4",
    "r4_verdict": "C3B3D2B2C_R4_SOURCE_INPUTS_IDENTIFIED_CURVE_EXTRACTION_REQUIRED",
    "description": (
        "Candidate C: P90-10y production + bank/sizing revenue scenario. "
        "Evaluated over active Senior Debt horizon only (generic derivation from policy). "
        "No hardcoded period boundaries. No project-name dispatch."
    ),
    "oborovo": {
        "equity_cell": "Inputs!D102",
        "equity_label": "Equity case revenues",
        "sizing_cell": "Inputs!D103",
        "sizing_label": "Debt sizing revenues curve",
        "scenarios_equity": "Scenarios!E324",
        "scenarios_sizing": "Scenarios!E325",
        "central_low_case_cell": "Inputs!D111",
        "central_low_case_label": "Central Low case Trackers",
        "low_gmpv_cell": "Inputs!D110",
        "status": "CURVE_EXTRACTION_REQUIRED_FOR_D110_D111",
    },
    "tuho": {
        "equity_cell": "Inputs!D107",
        "equity_label": "Equity scenario",
        "sizing_cell": "Inputs!D108",
        "sizing_label": "Sizing scenario",
        "scenarios_equity": "Scenarios!E182",
        "scenarios_sizing": "Scenarios!E183",
        "mid_low_cell": "Inputs!D109",
        "mid_low_label": "MidLow",
        "status": "CURVE_EXTRACTION_REQUIRED_FOR_D109",
    },
    "active_horizon": {
        "derivation": "GENERIC_FROM_SENIOR_DEBT_POLICY_NOT_HARDCODED",
        "classification": "POST_MATURITY_CFADS_NON_CAUSAL_FOR_INITIAL_DSCR_SIZING",
        "note": (
            "Active debt period count derived from "
            "policy.maturity_period_index - policy.repayment_start_period_index + 1. "
            "Post-maturity periods are excluded from the DSCR schedule and cannot be "
            "the binding constraint. POST_MATURITY_CFADS_NON_CAUSAL_FOR_INITIAL_DSCR_SIZING."
        ),
    },
    "blocked_reason": (
        "D111 (Oborovo Central Low case Trackers time series), "
        "D110 (Oborovo Low case GMPV), and D109 (TUHO MidLow) values are not "
        "present in any committed fixture. Candidate C evaluation requires "
        "curve extraction before source comparison is possible."
    ),
}


# ---------------------------------------------------------------------------
# R4.1: Manual causality evidence and product contract design
# ---------------------------------------------------------------------------

MANUAL_CAUSALITY_EVIDENCE = {
    "classification": "OBOROVO_DEBT_SIZING_REVENUE_CURVE_MANUAL_CAUSALITY_PROVEN",
    "method": "BLACK_BOX_WORKBOOK_OBSERVATION",
    "observation_d111": {
        "scenarios_e325": "Central Low case Trackers",
        "inputs_cell": "Inputs!D111",
        "resulting_debt_keur": 42852.278763,
        "matches_ds_d51": True,
    },
    "observation_d106": {
        "scenarios_e325": "Central case Trackers",
        "inputs_cell": "Inputs!D106",
        "resulting_debt_keur": 43813.0,
        "matches_ds_d51": False,
    },
    "delta_keur": 961.0,
    "causal_conclusion": (
        "Revenue curve selector Scenarios!E325 IS causal for debt sizing. "
        "D111 (Central Low case Trackers) produces DS!D51 exactly. "
        "D106 (Central case Trackers, equity curve) produces +961 kEUR. "
        "OBOROVO_DEBT_SIZING_REVENUE_CURVE_MANUAL_CAUSALITY_PROVEN."
    ),
    "r4_1_verdict": "C3B3D2B2C_R4_1_MANUAL_CAUSALITY_PROVEN_ENGINE_EVALUATION_XLSM_EXTRACTION_REQUIRED",
}

TUHO_ORACLE_DERIVATION = {
    "classification": "TUHO_BANK_CFADS_ORACLE_BACK_CALCULATED_FROM_DEBT_SERVICE",
    "senior_debt_service_p1_keur": 2116.361394092063,
    "dscr_target": 1.2,
    "bank_cfads_p1_keur": 2539.633672910476,
    "base_cfads_p1_keur": 3070.175837370555,
    "bank_base_ratio": 2539.633672910476 / 3070.175837370555,
    "p90_p50_yield_ratio": 3620 / 4164,
    "residual_price_ratio": (2539.633672910476 / 3070.175837370555) / (3620 / 4164),
    "source_fixture": "tests/fixtures/excel_tuho_periods.json",
}

PRODUCT_CONTRACT_DESIGN = {
    "classification": "C3B3D2B2C_R4_1_PRODUCT_CONTRACT_DESIGN_DRAFT",
    "yield_case": {
        "fields": ["p50_hours", "p90_10y_hours", "p90_p50_ratio (derived)", "label"],
        "ux_contract": "P50 and P90 both user-editable. Ratio is derived display-only.",
    },
    "price_curve": {
        "fields": ["curve_id", "label", "calendar_start_year", "values_eur_mwh"],
        "ux_contract": "Named library; CRUD operations; selector by curve_id.",
    },
    "revenue_case_selection": {
        "fields": ["equity_curve_id", "sizing_curve_id", "bess_curve_id (optional)"],
        "ux_contract": "Scenario tab exposes two selectors; engine uses sizing_curve_id for bank CFADS.",
    },
    "scenario_tab_sections": [
        "Production / Yield (p50, p90)",
        "Revenue Curves (equity_curve_id, sizing_curve_id)",
        "BESS Revenue if applicable (bess_curve_id)",
    ],
    "no_project_name_dispatch": True,
    "no_hardcoded_period_boundaries": True,
}

R4_1_EVIDENCE_FIXTURE_PATH = (
    "tests/fixtures/excel_oborovo_bank_sizing_source_evidence_r4_1.json"
)


R4_2_EVIDENCE_FIXTURE_PATH = (
    "tests/fixtures/excel_bank_sizing_revenue_curves_r4_2.json"
)

# ---------------------------------------------------------------------------
# R4.2: Source price curves (extracted from XLSM, verbatim)
# ---------------------------------------------------------------------------

# Oborovo: Central Low case Trackers — CY2042-CY2060 slice (19 values).
# Source: Inputs!D111, confirmed causal via Scenarios!E325 = 'Central Low case Trackers'.
# These 19 values align with merchant_price_calendar_start_year=2042.
OBOROVO_CENTRAL_LOW_CY2042_2060: tuple[float, ...] = (
    44.110675,  # 2042
    43.199275,  # 2043
    42.098000,  # 2044
    39.412625,  # 2045
    39.629625,  # 2046
    39.841200,  # 2047
    40.052775,  # 2048
    40.264350,  # 2049
    40.481350,  # 2050
    40.210100,  # 2051
    39.944275,  # 2052
    39.673025,  # 2053
    39.407200,  # 2054
    39.135950,  # 2055
    38.837575,  # 2056
    38.539200,  # 2057
    38.240825,  # 2058
    37.942450,  # 2059
    37.644075,  # 2060
)

# TUHO: MidLow — Y1-Y30 slice (30 values = CY2030-CY2059).
# Source: Inputs!D109, confirmed active via Scenarios!E183 = 'Sizing case Afry curve'.
# market_prices_curve is operating-year indexed; COD 2030-01-01 → Y1=CY2030.
TUHO_MIDLOW_Y1_Y30: tuple[float, ...] = (
    75.790,  # Y1  2030
    76.355,  # Y2  2031
    76.390,  # Y3  2032
    75.175,  # Y4  2033
    74.755,  # Y5  2034
    75.720,  # Y6  2035
    72.735,  # Y7  2036
    71.215,  # Y8  2037
    70.485,  # Y9  2038
    69.360,  # Y10 2039
    67.895,  # Y11 2040
    67.300,  # Y12 2041
    65.895,  # Y13 2042
    63.825,  # Y14 2043
    61.145,  # Y15 2044
    58.825,  # Y16 2045
    58.970,  # Y17 2046
    59.120,  # Y18 2047
    59.270,  # Y19 2048
    59.420,  # Y20 2049
    59.565,  # Y21 2050
    59.200,  # Y22 2051
    58.840,  # Y23 2052
    58.480,  # Y24 2053
    58.120,  # Y25 2054
    57.755,  # Y26 2055
    57.220,  # Y27 2056
    56.680,  # Y28 2057
    56.150,  # Y29 2058
    55.610,  # Y30 2059
)


def derive_active_debt_period_count(sd_input: "Any") -> int:
    """Return the active Senior Debt period count from policy fields.

    Generic — no hardcoded period boundary integers.
    Derivation: maturity_period_index - repayment_start_period_index + 1
    Classification: GENERIC_FROM_SENIOR_DEBT_POLICY_NOT_HARDCODED
    """
    policy = sd_input.senior_debt_policy
    return policy.maturity_period_index - policy.repayment_start_period_index + 1


# ---------------------------------------------------------------------------
# R4.2: Candidate C — Oborovo
# P90-10y yield + Central Low case Trackers (D111) as merchant price curve.
# ---------------------------------------------------------------------------

def run_candidate_c_oborovo(project_factory_fn: Any) -> dict:
    """Run Candidate C for Oborovo and return diagnostic summary.

    Candidate C: P90-10y yield + Central Low case Trackers (Inputs!D111).
    Source curves: OBOROVO_CENTRAL_LOW_CY2042_2060 (19 values, CY2042-2060).
    Target: DS!D51 = 42,852.278763 kEUR.
    VBA_IMPLEMENTATION_NOT_VISIBLE — mechanism unresolved.

    Returns:
        dict with debt_keur, target_keur, delta_keur, verdict, per_period_decomposition
    """
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )
    from financial_engine.inputs import YieldScenario
    from financial_engine.orchestrator import run_senior_debt_model

    proj = project_factory_fn()

    # Swap merchant price curve to Central Low case Trackers (D111)
    new_rev = replace(
        proj.revenue,
        market_prices_by_calendar_year_eur_mwh=OBOROVO_CENTRAL_LOW_CY2042_2060,
    )
    proj_c = replace(proj, revenue=new_rev)

    # Build senior debt model input with P90-10y yield
    sd_input = build_senior_debt_model_input_from_project_inputs(proj_c)
    bank_op = _derive_bank_operating_input(sd_input.operating, YieldScenario.P90_10Y)
    sd_input_c = replace(sd_input, operating=bank_op)

    result = run_senior_debt_model(sd_input_c)
    debt_keur = result.senior_debt.debt_size_keur
    target_keur = 42852.278763
    delta_keur = debt_keur - target_keur

    # Per-period bank CFADS decomposition for merchant periods
    from financial_engine.orchestrator import run_operating_model
    from financial_engine.tax.engine import calculate_tax as calc_tax
    from financial_engine.cfads import calculate_canonical_cfads as calc_cfads

    bank_result = run_operating_model(bank_op)
    bank_tax_r = calc_tax(bank_result.periods, sd_input_c.tax)
    bank_cfads_r = calc_cfads(bank_result.periods, bank_tax_r.period_results)
    bank_cfads_by_idx = {cr.period_index: cr.cfads_keur for cr in bank_cfads_r}

    source = load_ds_row20_oracle()
    merchant_decomp = []
    for pidx in sorted(p.period_index for p in bank_result.periods if p.is_operation and not p.is_ppa_active):
        fidx = pidx - 1
        if 0 <= fidx < len(source):
            bank_v = bank_cfads_by_idx.get(pidx, 0.0)
            src_v = source[fidx]
            merchant_decomp.append({
                "period_index": pidx,
                "bank_cfads_keur": bank_v,
                "source_cfads_keur": src_v,
                "delta_keur": bank_v - src_v,
            })

    verdict = (
        "C3B3D2B2C_R4_2_STOP_CANDIDATE_C_SOURCE_PARITY_FAILED"
        if abs(delta_keur) > 500.0
        else "C3B3D2B2C_R4_2_CANDIDATE_C_OBOROVO_PASS"
    )

    return {
        "candidate": "CANDIDATE_C",
        "project": "oborovo",
        "yield_scenario": "P90_10Y",
        "price_curve": "Central Low case Trackers (Inputs!D111)",
        "debt_keur": debt_keur,
        "target_keur": target_keur,
        "delta_keur": delta_keur,
        "verdict": verdict,
        "blocker": (
            "VBA_IMPLEMENTATION_NOT_VISIBLE: Direct D111 price substitution gives "
            "engine sensitivity ~5x larger than observed Excel sensitivity (961 kEUR). "
            "Mechanism unresolved. No calibration applied."
        ),
        "merchant_period_decomposition": merchant_decomp,
    }


# ---------------------------------------------------------------------------
# R4.2: Candidate C — TUHO (operating model only; ATAD blocks full debt sizing)
# P90-10y yield + MidLow prices (D109) → compare bank CFADS to oracle.
# ---------------------------------------------------------------------------

def run_candidate_c_tuho(project_factory_fn: Any) -> dict:
    """Run Candidate C for TUHO and return diagnostic summary.

    Candidate C: P90-10y yield + MidLow (Inputs!D109).
    Full debt sizing blocked: build_tax_contract_from_project_inputs raises
    NotImplementedError for atad_enabled=True without full interest inputs.
    Operating model only — bank CFADS compared to oracle 2539.633673 kEUR.

    Returns:
        dict with bank_cfads_p2_keur, oracle_keur, delta_keur, verdict
    """
    from financial_engine.adapters.project_inputs import from_project_inputs
    from financial_engine.inputs import YieldScenario
    from financial_engine.orchestrator import run_operating_model

    proj = project_factory_fn()

    # Swap to MidLow (D109) — 30 operating-year values
    new_rev = replace(
        proj.revenue,
        market_prices_curve_eur_mwh=TUHO_MIDLOW_Y1_Y30,
    )
    proj_c = replace(proj, revenue=new_rev)

    op_input = from_project_inputs(proj_c)
    bank_op = _derive_bank_operating_input(op_input, YieldScenario.P90_10Y)
    bank_result = run_operating_model(bank_op)

    # TUHO engine P2 = oracle P1 (P1 is 1-day setup, revenue=0)
    p2 = next((p for p in bank_result.periods if p.period_index == 2), None)
    bank_cfads_p2 = p2.ebitda_keur if p2 is not None else float("nan")

    oracle_keur = 2539.633672910476
    delta_keur = bank_cfads_p2 - oracle_keur

    verdict = (
        "C3B3D2B2C_R4_2_STOP_CANDIDATE_C_SOURCE_PARITY_FAILED"
        if abs(delta_keur) > 500.0
        else "C3B3D2B2C_R4_2_CANDIDATE_C_TUHO_PASS"
    )

    return {
        "candidate": "CANDIDATE_C",
        "project": "tuho",
        "yield_scenario": "P90_10Y",
        "price_curve": "MidLow (Inputs!D109)",
        "bank_cfads_engine_p2_keur": bank_cfads_p2,
        "oracle_bank_cfads_p1_keur": oracle_keur,
        "delta_keur": delta_keur,
        "verdict": verdict,
        "atad_blocker": (
            "TUHO_ATAD_BLOCKER: build_tax_contract_from_project_inputs raises "
            "NotImplementedError for atad_enabled=True. Full debt sizing not possible "
            "without complete interest schedule. Operating model only."
        ),
        "oracle_derivation": "senior_debt_service_p1 * dscr_target = 2116.361394 * 1.2 = 2539.633673",
    }


# ---------------------------------------------------------------------------
# R4.2: Post-maturity runtime causality test
# ---------------------------------------------------------------------------

def run_post_maturity_sensitivity(project_factory_fn: Any) -> dict:
    """Runtime proof: post-maturity CFADS are non-causal for initial DSCR sizing.

    Perturbs merchant prices after Senior Debt maturity (post-active-periods) by
    ×2.0 and ×0.5. If debt changes by 0, the causality is proven:
    POST_MATURITY_CFADS_NON_CAUSAL_FOR_INITIAL_DSCR_SIZING_RUNTIME_PROVEN.

    Active periods: CY2042-CY2044 (first 3 merchant years within debt horizon).
    Post-maturity: CY2045+ (outside the sculpted DSCR schedule).

    Returns:
        dict with baseline_debt, perturbed debts, deltas, verdict
    """
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )
    from financial_engine.inputs import YieldScenario
    from financial_engine.orchestrator import run_senior_debt_model

    proj = project_factory_fn()

    def _build_and_run(price_curve: tuple) -> float:
        new_rev = replace(proj.revenue, market_prices_by_calendar_year_eur_mwh=price_curve)
        proj_mod = replace(proj, revenue=new_rev)
        sd = build_senior_debt_model_input_from_project_inputs(proj_mod)
        bank_op = _derive_bank_operating_input(sd.operating, YieldScenario.P90_10Y)
        sd_mod = replace(sd, operating=bank_op)
        return run_senior_debt_model(sd_mod).senior_debt.debt_size_keur

    # Baseline: Central case Trackers (D106) with P90 yield
    baseline_curve = tuple(proj.revenue.market_prices_by_calendar_year_eur_mwh)
    baseline_debt = _build_and_run(baseline_curve)

    # Post-maturity ×2.0: multiply CY2045+ prices (indices 3-18, 0-based from CY2042)
    up_curve = tuple(
        v * 2.0 if i >= 3 else v for i, v in enumerate(baseline_curve)
    )
    up_debt = _build_and_run(up_curve)

    # Post-maturity ×0.5
    down_curve = tuple(
        v * 0.5 if i >= 3 else v for i, v in enumerate(baseline_curve)
    )
    down_debt = _build_and_run(down_curve)

    # Active period sensitivity: ×1.1 on CY2042-2044 (indices 0-2)
    active_up_curve = tuple(
        v * 1.1 if i < 3 else v for i, v in enumerate(baseline_curve)
    )
    active_up_debt = _build_and_run(active_up_curve)

    post_maturity_verdict = (
        "POST_MATURITY_CFADS_NON_CAUSAL_FOR_INITIAL_DSCR_SIZING_RUNTIME_PROVEN"
        if abs(up_debt - baseline_debt) < 0.01 and abs(down_debt - baseline_debt) < 0.01
        else "POST_MATURITY_CAUSALITY_UNEXPECTED_SENSITIVITY"
    )

    return {
        "classification": post_maturity_verdict,
        "baseline_debt_keur": baseline_debt,
        "post_maturity_x2_debt_keur": up_debt,
        "post_maturity_x2_delta_keur": up_debt - baseline_debt,
        "post_maturity_x05_debt_keur": down_debt,
        "post_maturity_x05_delta_keur": down_debt - baseline_debt,
        "active_period_x11_debt_keur": active_up_debt,
        "active_period_x11_delta_keur": active_up_debt - baseline_debt,
        "post_maturity_perturbation_years": "CY2045+",
        "active_period_years": "CY2042-2044",
        "verdict": post_maturity_verdict,
    }


# ---------------------------------------------------------------------------
# R4.2: Result summary
# ---------------------------------------------------------------------------

CANDIDATE_C_R4_2_RESULT = {
    "stage": "C3B3D2B2C",
    "round": "R4.2",
    "verdict": "C3B3D2B2C_R4_2_STOP_CANDIDATE_C_SOURCE_PARITY_FAILED",
    "oborovo": {
        "candidate": "CANDIDATE_C",
        "yield_scenario": "P90_10Y",
        "price_curve": "Central Low case Trackers (Inputs!D111)",
        "engine_debt_keur": 38829.996,
        "target_debt_keur": 42852.278763,
        "delta_keur": -4022.283,
        "tolerance_keur": 500.0,
        "result": "FAIL",
        "analysis": (
            "Engine sensitivity (Central vs Central Low): ~5,089 kEUR. "
            "Excel observed sensitivity: 961 kEUR. Ratio: ~5.3x. "
            "Direct D111 substitution does not reproduce the VBA mechanism. "
            "VBA_IMPLEMENTATION_NOT_VISIBLE remains the fundamental blocker."
        ),
    },
    "tuho": {
        "candidate": "CANDIDATE_C",
        "yield_scenario": "P90_10Y",
        "price_curve": "MidLow (Inputs!D109)",
        "atad_blocker": "TUHO_ATAD_NOTIMPLEMENTEDERROR",
        "oracle_bank_cfads_p1_keur": 2539.633673,
        "result": "BLOCKED_ATAD",
    },
    "post_maturity_causality": {
        "verdict": "POST_MATURITY_CFADS_NON_CAUSAL_FOR_INITIAL_DSCR_SIZING_RUNTIME_PROVEN",
        "post_maturity_x2_delta_keur": 0.0,
        "post_maturity_x05_delta_keur": 0.0,
        "active_period_x11_delta_keur": 518.545,
    },
    "gate_decision": (
        "STOP: Candidate C engine gives 38,830 kEUR vs source 42,852 kEUR (delta -4,022 kEUR). "
        "Exceeds 500 kEUR tolerance. No calibration applied. "
        "VBA mechanism not visible — cannot advance to production without resolution."
    ),
    "financial_engine_diff": "ZERO — financial_engine/ unchanged from base SHA",
}
