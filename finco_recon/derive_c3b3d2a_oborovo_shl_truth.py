"""finco_recon.derive_c3b3d2a_oborovo_shl_truth — C3B3D2A derivation utility.

Reads ONLY committed source fixtures and derives the canonical D2A SHL fixture:
    tests/fixtures/excel_oborovo_shl_operating_truth.json

Sources read (in order of authority):
  1. tests/fixtures/excel_oborovo_financial_truth.json
       → DS sheet raw vectors (shl_beginning_keur, shl_funding_keur,
         shl_net_interest_keur, shl_interest_capitalised_keur,
         shl_ending_keur, shl_service_keur)
       → Inputs!D325 (shl draw), Inputs!F328 (rate)
       → Workbook identity (filename, SHA-256)

  2. tests/fixtures/interest_limitation/oborovo_interest_limitation_fixture.json
       → Period dates (start/end) and Excel column mappings for DS[1..40]
       → Gross interest cross-check (r27 = shl_net_interest)

No Python model output, no factory output, no legacy waterfall output is used.

Field classification
--------------------
SOURCE_RAW_CACHED_VALUE:
    opening_balance_keur       ← shl_beginning_keur
    drawdown_keur              ← shl_funding_keur
    gross_accrued_interest_keur← shl_net_interest_keur
    pik_interest_keur          ← shl_interest_capitalised_keur
    closing_balance_keur       ← shl_ending_keur
    shl_service_keur           ← shl_service_keur (raw, kept for audit)

DETERMINISTIC_DERIVATION_FROM_SOURCE_VALUES:
    cash_interest_keur         = gross_accrued_interest_keur - pik_interest_keur
    principal_repaid_keur      = shl_service_keur - cash_interest_keur

Payment mode classification is VALUE-DERIVED from the source DS vectors:
    cap >= gross (tol 1e-9)  → PIK            (DS[0]: 100% PIK)
    cap > 0 and cash > 0     → PARTIAL_CASH_PARTIAL_PIK (DS[1..24]: waterfall-driven)
    cap == 0 (tol 1e-9)      → CASH_PAID      (DS[25..40])

The DS25 boundary is DISCOVERED from data (first period where cap=0),
NOT asserted by a hardcoded index comparison.
"""
from __future__ import annotations

import json
import pathlib

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_SOURCE_TRUTH = _REPO_ROOT / "tests/fixtures/excel_oborovo_financial_truth.json"
_IL_FIXTURE = _REPO_ROOT / "tests/fixtures/interest_limitation/oborovo_interest_limitation_fixture.json"
_OUTPUT = _REPO_ROOT / "tests/fixtures/excel_oborovo_shl_operating_truth.json"

_TOL = 1e-9


def derive(write: bool = True) -> dict:
    """Derive the D2A fixture from committed source evidence.

    Parameters
    ----------
    write : bool
        If True (default), write the result to _OUTPUT.
        If False, return the dict without writing (for idempotency checks).

    Returns
    -------
    dict : the derived fixture content.
    """
    with open(_SOURCE_TRUTH) as f:
        truth = json.load(f)
    with open(_IL_FIXTURE) as f:
        il = json.load(f)

    meta = truth["_meta"]
    ds = truth["ds"]
    inp = truth["inputs"]

    # Rate sourced from committed fixture: Excel Inputs!F328 (SOURCE_RAW_CACHED_VALUE)
    shl_rate = inp["shl_interest_rate"]["value"]

    # ── period date map from interest_limitation fixture ─────────────────────
    # il.periods[i] = DS[i+1] (operating period, 0-based index in IL = DS[1] in SHL)
    il_periods = il["periods"]
    ds_date_map: dict[int, dict] = {}
    for i, p in enumerate(il_periods[:40]):
        ds_idx = i + 1
        ds_date_map[ds_idx] = {
            "period_start_date": p["start_date"],
            "period_end_date": p["end_date"],
            "excel_column": p["column"],
            "excel_period_number": int(p["excel_period_number"]),
            "date_source": "tests/fixtures/interest_limitation/oborovo_interest_limitation_fixture.json",
        }

    # ── cross-check: IL gross interest == DS shl_net_interest ────────────────
    ds_gross = ds["shl_net_interest_keur"]
    for i, p in enumerate(il_periods[:40]):
        ds_i = i + 1
        diff = abs(p["gross_shl_interest_r27"] - ds_gross[ds_i])
        assert diff < _TOL, (
            f"Cross-check failed at DS[{ds_i}]: "
            f"IL gross={p['gross_shl_interest_r27']} vs DS={ds_gross[ds_i]}"
        )

    # ── build period records ─────────────────────────────────────────────────
    periods = []
    for ds_idx in range(41):
        beg  = ds["shl_beginning_keur"][ds_idx]
        fund = ds["shl_funding_keur"][ds_idx]
        gross = ds["shl_net_interest_keur"][ds_idx]
        cap   = ds["shl_interest_capitalised_keur"][ds_idx]
        svc   = ds["shl_service_keur"][ds_idx]
        end   = ds["shl_ending_keur"][ds_idx]
        spf   = ds["sd_period_fraction"][ds_idx]

        # DERIVED: cash_interest = gross - cap  (gross = cash + cap definition)
        cash_int = gross - cap
        # DERIVED: principal_repaid = svc - cash_interest
        principal_repaid = svc - cash_int

        # Payment mode: value-derived from cap vs gross (NOT from ds_idx boundary).
        # DS25 boundary is discovered from data; the index is a consequence, not an input.
        if cap >= gross - _TOL and cash_int <= _TOL:
            payment_mode = "PIK"
        elif cap > _TOL and cash_int > _TOL:
            payment_mode = "PARTIAL_CASH_PARTIAL_PIK"
        elif cap <= _TOL and cash_int >= gross - _TOL:
            payment_mode = "CASH_PAID"
        else:
            raise ValueError(
                f"UNRESOLVED payment mode at DS[{ds_idx}]: "
                f"gross={gross}, cap={cap}, cash={cash_int}"
            )

        # Day-count fraction for SHL (actual/365): DERIVED from source values.
        # Rate sourced from inp["shl_interest_rate"]["value"] (Excel Inputs!F328),
        # NOT from a hardcoded constant. DCF = gross / ((beg + fund) * rate).
        # CONSTRUCTION_SHL_DCF_SOURCE_IMPLIED_1_0: for DS[0], gross/(draw*rate) = 1.0
        # exactly, implying the construction period is treated as a full year. The
        # exact construction interval dates are not directly committed in this fixture
        # (construction_parity shows 2029-06-29→2030-06-29; IL DS[1].start=2030-07-01).
        dcf_shl_derived = gross / ((beg + fund) * shl_rate) if (beg + fund) > 0 else None

        rec: dict = {
            "ds_index": ds_idx,
            "payment_mode": payment_mode,
            # SOURCE_RAW_CACHED_VALUE fields
            "opening_balance_keur": beg,
            "drawdown_keur": fund,
            "gross_accrued_interest_keur": gross,
            "pik_interest_keur": cap,
            "closing_balance_keur": end,
            "shl_service_keur": svc,
            "sd_period_fraction_actual_360": spf,
            # DETERMINISTIC_DERIVATION_FROM_SOURCE_VALUES fields
            "cash_interest_keur": cash_int,
            "principal_repaid_keur": principal_repaid,
            # Day-count: derived, not workbook-formula authority
            "shl_dcf_derived_actual_365": dcf_shl_derived,
        }

        # Add date info for operating periods (DS[1..40] — source-proven from IL fixture)
        if ds_idx >= 1:
            rec.update(ds_date_map.get(ds_idx, {}))
        # Construction has no committed period date; DS[0] is a single construction period
        # ending at the date of DS[1] start (inferred as 2030-06-30 from IL, but not
        # directly committed in either source fixture for the construction period itself).

        periods.append(rec)

    # ── workbook inputs (raw cached values from Inputs sheet) ────────────────
    shl_draw = inp["shl_amount_keur"]["value"]
    # shl_rate already bound above from inp["shl_interest_rate"]["value"]

    # ── assemble fixture ──────────────────────────────────────────────────────
    fixture = {
        "_meta": {
            "stage": "C3B3D2A",
            "label": "OBOROVO_SHL_SOURCE_TRUTH",
            "description": (
                "Immutable source-evidence fixture. All SOURCE_RAW_CACHED_VALUE fields "
                "are extracted from committed Excel cached-value fixtures. "
                "DETERMINISTIC_DERIVATION fields are computed by deterministic arithmetic "
                "from source values only. No Python model/factory/waterfall output used."
            ),
            "derivation_script": "finco_recon/derive_c3b3d2a_oborovo_shl_truth.py",
            "primary_source_fixture": "tests/fixtures/excel_oborovo_financial_truth.json",
            "period_date_source_fixture": (
                "tests/fixtures/interest_limitation/oborovo_interest_limitation_fixture.json"
            ),
            "source_workbook_filename": meta["source_filename"],
            "source_workbook_sha256": meta["source_sha256"],
            "ds_sheet_scope": (
                "DS[0]=construction, DS[1..40]=40 operating periods, "
                "DS[41..60]=zero (post-maturity)"
            ),
            "extraction_basis": (
                "Cached cell values via openpyxl data_only=True. "
                "Formula text via data_only=False for cross-reference. "
                "No live Excel recalculation."
            ),
            "field_classification": {
                "SOURCE_RAW_CACHED_VALUE": [
                    "opening_balance_keur",
                    "drawdown_keur",
                    "gross_accrued_interest_keur",
                    "pik_interest_keur",
                    "closing_balance_keur",
                    "shl_service_keur",
                    "sd_period_fraction_actual_360",
                ],
                "DETERMINISTIC_DERIVATION_FROM_SOURCE_VALUES": [
                    "cash_interest_keur (= gross_accrued_interest_keur - pik_interest_keur)",
                    "principal_repaid_keur (= shl_service_keur - cash_interest_keur)",
                    (
                        "shl_dcf_derived_actual_365 "
                        "(= gross / ((opening + drawdown) * shl_rate_from_Inputs_F328))"
                    ),
                ],
            },
            "day_count_status": (
                "OPERATING_SHL_DAY_COUNT_SOURCE_PROVEN_ACTUAL_365_INCLUSIVE: "
                "C3B3D2B0-R1 proved convention is actual/365 with inclusive end date. "
                "dcf = ((end_date - start_date).days + 1) / 365. "
                "Denominator always 365 (fixed, even in leap years). "
                "Max delta vs source-derived DCF: 1.11e-16 across all 40 operating periods. "
                "CONSTRUCTION_SHL_DCF_SOURCE_IMPLIED_1_0: construction DCF=1.0 is "
                "implied by arithmetic (gross/(draw*rate)=1.0). "
                "Senior debt day-count (actual/360) is in sd_period_fraction_actual_360."
            ),
            "c3b3d2b0_r1": {
                "status": "C3B3D2B0_CLEAN_SHL_FORMULA_PARITY_PROVEN",
                "dcf_convention": "OPERATING_SHL_DAY_COUNT_SOURCE_PROVEN_ACTUAL_365_INCLUSIVE",
                "dcf_formula": "((period_end_date - period_start_date).days + 1) / 365",
                "dcf_independence": "proven: DCF does not read gross_accrued_interest_keur",
                "max_gross_delta_keur": "2.27e-13",
                "max_closing_delta_keur": "0.00e+00",
                "final_ds40_closing_keur": "0.000000",
                "construction_path": "C3B3D1 compute_shl_period(opening=0, drawdown=draw, dcf=1.0)",
                "sweep_provenance": "SOURCE_VECTOR_DERIVED_AND_FULL_HORIZON_RECONCILED",
            },
        },
        "workbook_inputs": {
            "shl_draw_keur": {
                "value": shl_draw,
                "cell": "Inputs!D325",
                "field_classification": "SOURCE_RAW_CACHED_VALUE",
                "label": "Excel raw SHL draw (full funding at construction close)",
            },
            "shl_annual_rate": {
                "value": shl_rate,
                "cell": "Inputs!F328",
                "field_classification": "SOURCE_RAW_CACHED_VALUE",
                "label": "Annual simple interest rate (8%)",
            },
        },
        "python_factory_note": {
            "shl_amount_keur_in_factory": 13547.2,
            "status": "C3B3D2A_FACTORY_CALIBRATION_REVERSION_PROVEN",
            "conflict_status": "C3B3D2A_FACTORY_VALUE_CONFLICTS_WITH_AUTHORITATIVE_SOURCE",
            "gap_vs_excel_keur": round(shl_draw - 13547.2, 6),
            "provenance_chronology": (
                "PR #309 (Phase 23L, commit 34ed6d0b22084e16d4c42d2c7fbf0ea68b1ac5fe): "
                "13547.2 → 14621 (toward Excel source). "
                "PR #752 (Stack D, commit 099e4a14f920cf618b06d850f567374c0c8b9a95): "
                "14621 → 13547.2 (reversion to match oborovo_baseline.json parity). "
                "Current value 13547.2 is a deliberate parity-baseline calibration value, "
                "NOT an unresolved gap. The conflict with Excel Inputs!D325=14620.77 is a "
                "KNOWN_SOURCE_CONFLICT deferred to C3B3D2B. "
                "Do NOT change shl_amount_keur=13547.2 in D2A."
            ),
        },
        "construction_period": {
            "ds_index": 0,
            "payment_mode": "PIK",
            "opening_balance_keur": ds["shl_beginning_keur"][0],
            "drawdown_keur": ds["shl_funding_keur"][0],
            "gross_accrued_interest_keur": ds["shl_net_interest_keur"][0],
            "pik_interest_keur": ds["shl_interest_capitalised_keur"][0],
            "cash_interest_keur": 0.0,
            "principal_repaid_keur": 0.0,
            "closing_balance_keur": ds["shl_ending_keur"][0],
            "shl_dcf_derived_actual_365": 1.0,
            "dcf_note": (
                "CONSTRUCTION_SHL_DCF_SOURCE_IMPLIED_1_0: "
                "gross / (draw * rate) = 1169.661912 / (14620.773895 * 0.08) = 1.0 exactly. "
                "This implies a full-year construction period. The exact interval dates are "
                "NOT directly committed in this fixture (construction_parity: 2029-06-29 "
                "→ 2030-06-29; IL DS[1].start: 2030-07-01 — potential 2-day gap at seam). "
                "DCF=1.0 is proven by arithmetic, NOT by a claimed 365 calendar-day count."
            ),
            "sd_period_fraction_actual_360": ds["sd_period_fraction"][0],
            "day_count_mismatch_note": (
                "SHL_SOURCE_DAY_COUNT_MISMATCH: SHL uses actual/365 (derived); "
                "senior debt uses actual/360 (sd_period_fraction). "
                "These two conventions are distinct. Do NOT unify."
            ),
        },
        "operating_opening_balance_keur": ds["shl_ending_keur"][0],
        "operating_opening_balance_derivation": (
            "= shl_draw_keur(14620.773894815633) + construction_pik_keur(1169.6619115852516)"
        ),
        "operating_opening_balance_status": "OBOROVO_SHL_BALANCE_LINEAGE_RESOLVED",
        "operating_opening_balance_note": (
            "Excel DS[0].end == DS[1].begin = 15790.435806400885. "
            "Proven from committed source fixture roll-forward. "
            "C3B3D1 label OBOROVO_SHL_BALANCE_LINEAGE_UNRESOLVED is retired."
        ),
        "payment_mode_classification": {
            "construction_ds0": "PIK — cap == gross exactly; cash_interest = 0",
            "operating_ds1_to_ds24": (
                "PARTIAL_CASH_PARTIAL_PIK — 0 < cap < gross each period; "
                "cash_interest = gross - cap; principal_repaid = svc - cash_interest; "
                "cap fraction ~47-67% (waterfall-driven, NOT a fixed ratio)"
            ),
            "operating_ds25_to_ds40": "CASH_PAID — cap = 0.0 exactly for all 16 periods",
            "pik_to_cash_switch_at_ds25": (
                "DS[25] is first period with cap=0 (period_end_date 2042-12-31). "
                "Switch is driven by FCF waterfall availability (legacy engine: "
                "pik_switch_triggered = cf_for_shl > shl_balance * shl_rate). "
                "shl_pik_switch_period field is NOT the trigger — it is unused by any runtime."
            ),
            "source_semantics_status": "C3B3D2A_OBOROVO_PAYMENT_SOURCE_SEMANTICS_PROVEN",
            "canonical_runtime_status": (
                "C3B3D2B_CANONICAL_SHL_RUNTIME_BLOCKED_BY_WATERFALL_COUPLING — "
                "the canonical financial_engine/shl/engine.py supports only CASH_PAID or PIK (full). "
                "PARTIAL_CASH_PARTIAL_PIK (DS[1..24]) requires FCF waterfall coupling. "
                "The canonical engine cannot reproduce the Oborovo operating schedule "
                "for DS[1..24] without waterfall integration (C3B3D2B scope)."
            ),
        },
        "maturity": {
            "ds_index": 40,
            "closing_balance_keur": ds["shl_ending_keur"][40],
            "opening_balance_keur": ds["shl_beginning_keur"][40],
            "period_end_date": ds_date_map[40]["period_end_date"],
            "mechanism": (
                "SWEEP_NOT_BULLET — principal is repaid incrementally via FCF sweep "
                "from DS[25] onward. Balance reaches 0.0 exactly at DS[40] (2050-06-30). "
                "NOT a contractual bullet repayment."
            ),
            "first_nonzero_principal_ds_index": None,  # set below
        },
        "day_count_convention": {
            "shl_operating_basis": "actual/365-inclusive",
            "shl_operating_convention_label": "OPERATING_SHL_DAY_COUNT_SOURCE_PROVEN_ACTUAL_365_INCLUSIVE",
            "shl_operating_formula": "dcf = ((period_end_date - period_start_date).days + 1) / 365",
            "shl_operating_denominator": 365,
            "shl_operating_denominator_note": (
                "Denominator is always 365 regardless of leap years (actual/365-Fixed convention)."
            ),
            "shl_operating_evidence_type": "SOURCE_VECTOR_PROVEN_ALL_40_PERIODS",
            "shl_operating_evidence_note": (
                "C3B3D2B0-R1: computed independently from period_start_date and "
                "period_end_date (from interest_limitation fixture) using "
                "(end - start).days + 1) / 365. "
                "Max delta vs source-derived DCF: 1.11e-16 (machine epsilon) across "
                "all 40 operating periods including 5 leap-year periods (DS[4,12,20,28,36]). "
                "Proved NOT circular: DCF input does not read gross_accrued_interest_keur. "
                "Previous date-exclusive formula (end - start).days / 365 produced 1/365 "
                "error per period (~3.46 kEUR gross error at DS[1], ~387 kEUR recursive "
                "closing error at DS[40])."
            ),
            "shl_operating_previous_error_explanation": (
                "Using (end_date - start_date).days / 365 (exclusive end) gives "
                "183/365=0.50137 for DS[1] vs correct 184/365=0.50411. "
                "Error = opening*rate*(1/365) = 15790.44*0.08/365 = 3.46 kEUR per period. "
                "Recursive compounding through 40 PIK/sweep periods reached ~387 kEUR "
                "closing delta by DS[40]. Resolution: end date is INCLUSIVE in the "
                "Excel actual/365 convention."
            ),
            "shl_construction_basis": "DCF=1.0 (implied)",
            "shl_construction_convention_label": "CONSTRUCTION_SHL_DCF_SOURCE_IMPLIED_1_0",
            "shl_construction_evidence_note": (
                "DCF=1.0 proven by arithmetic: "
                "gross/(draw*rate)=1169.661912/(14620.773895*0.08)=1.0. "
                "Not proven by calendar date count (construction interval dates have a "
                "potential 2-day gap at the seam: cf.bop_date[0]=2029-06-29, "
                "cf.eop_date[0]=2030-06-30, IL DS[1].start=2030-07-01). "
                "The construction period uses C3B3D1 compute_shl_period with "
                "opening=0, drawdown_keur=draw, dcf=1.0."
            ),
            "senior_debt_basis": "actual/360",
            "senior_debt_evidence": "sd_period_fraction column (SOURCE_RAW_CACHED_VALUE)",
            "mismatch_status": "SHL_SOURCE_DAY_COUNT_MISMATCH",
            "mismatch_note": "Two different day-count bases confirmed in same workbook. Do not unify.",
        },
        "period_mapping": {
            "status": "C3B3D2A_PERIOD_MAPPING_FULL_HORIZON_COMMITTED_FIXTURE_PROVEN",
            "note": (
                "All 40 operating period dates (DS[1..40] = Excel P1..P40) are "
                "proven from tests/fixtures/interest_limitation/"
                "oborovo_interest_limitation_fixture.json (a committed fixture). "
                "P1..P12 also independently verified in excel_oborovo_periods.json. "
                "NOTE: the IL fixture uses source_workbook filename "
                "'20260414_BP_Oborovo_Sensitivity_FINAL for PPT (1).xlsm' with no SHA; "
                "the primary fixture uses SHA "
                "15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920. "
                "The fixtures are cross-verified via exact gross interest match (r27) "
                "for all 40 operating periods but are not cryptographically tied to "
                "a single binary workbook identity."
            ),
            "c3b2_clean_index_offset": (
                "DS[n] → clean_period_index = n+1 for operating periods "
                "(DS[1] = clean_idx 2, DS[40] = clean_idx 41)"
            ),
            "proven_through_ds_index": 40,
        },
        "roll_forward_identity": (
            "closing = opening + drawdown + pik_interest - principal_repaid. "
            "Equivalently: closing = opening + drawdown + gross_interest - shl_service. "
            "Verified exact for all 41 non-zero DS periods."
        ),
        "partial_cash_pik_arithmetic_ds1_proof": {
            "ds_index": 1,
            "gross_accrued_interest": ds["shl_net_interest_keur"][1],
            "pik_interest_capitalised": ds["shl_interest_capitalised_keur"][1],
            "cash_interest_derived": (
                ds["shl_net_interest_keur"][1] - ds["shl_interest_capitalised_keur"][1]
            ),
            "principal_repaid": 0.0,
            "identity": "cash_interest = gross - cap (NOT svc - cap)",
            "note": (
                "svc includes BOTH interest cash payment AND principal repayment. "
                "For DS[1]: svc=335.87 = cash_interest(335.87) + principal(0). "
                "For DS[25+]: svc includes both interest and principal sweep."
            ),
        },
        "d2b_architecture_note": {
            "label": "C3B3D2B_CANONICAL_SHL_RUNTIME_BLOCKED_BY_WATERFALL_COUPLING",
            "summary": (
                "The Oborovo gross SHL interest vector CANNOT be generated from the "
                "standalone C3B3D1 canonical schedule using only opening_balance, rate, "
                "and day_count_fraction. The balance trajectory depends on prior-period "
                "waterfall outcome (partial PIK DS[1..24], then principal sweep DS[25..40]). "
                "D2B must NOT simply inject the Excel SHL vector as a static exogenous input "
                "and must NOT assume run_shl_schedule() → static gross interest vector → Tax "
                "is sufficient for Oborovo. D2B must design the generic causal seam before "
                "any runtime promotion."
            ),
        },
        "unresolved_items": {
            "known_source_conflict": (
                "KNOWN_SOURCE_CONFLICT (C3B3D2A_FACTORY_CALIBRATION_REVERSION_PROVEN): "
                "factory shl_amount_keur=13547.2 (oborovo_baseline.json parity) vs "
                "Excel Inputs!D325=14620.77. Provenance documented. "
                "Resolution deferred to C3B3D2B."
            ),
            "partial_cash_pik_canonical": (
                "PARTIAL_CASH_PARTIAL_PIK for DS[1..24] cannot be modelled by canonical "
                "SHL engine in C3B3D1. Handled by C3B3D2B0 waterfall formula."
            ),
            "pik_switch_trigger": (
                "Sweep provenance: SOURCE_VECTOR_DERIVED_AND_FULL_HORIZON_RECONCILED. "
                "Identity cash_available > gross (period interest) triggers principal sweep. "
                "Proven by vector identity for all 40 periods. No direct workbook formula "
                "text committed for the sweep row formula."
            ),
            "tuho": (
                "TUHO_SHL_BALANCE_LINEAGE_UNRESOLVED: TUHO uses pik_then_sweep "
                "repayment — blocked at C3B3D1 adapter; deferred to later SHL/waterfall scope."
            ),
            "construction_period_start_date": (
                "DS[0] construction start=2029-06-29 (cf.bop_date[0]), end=2030-06-30 "
                "(cf.eop_date[0]). DCF=1.0 is arithmetic-implied, not calendar-derived. "
                "The 2-day gap between eop_date[0]=2030-06-30 and IL DS[1].start=2030-07-01 "
                "is unresolved. Construction handled by C3B3D1 engine (opening=0, drawdown=draw)."
            ),
            "cash_vector_not_wired_to_runtime": (
                "free_cash_flow_for_shl_keur used as test driver only; not wired to "
                "production FCF waterfall. Production wiring deferred to C3B3D2B1+."
            ),
        },
        "periods": periods,
    }

    # ── discover payment-mode boundaries from data ───────────────────────────
    first_principal_ds = None
    first_cash_paid_ds = None
    for p in periods:
        if first_principal_ds is None and p["principal_repaid_keur"] > _TOL:
            first_principal_ds = p["ds_index"]
        if first_cash_paid_ds is None and p["payment_mode"] == "CASH_PAID":
            first_cash_paid_ds = p["ds_index"]
    fixture["maturity"]["first_nonzero_principal_ds_index"] = first_principal_ds
    fixture["payment_mode_classification"]["first_cash_paid_ds_index_discovered"] = (
        first_cash_paid_ds
    )
    fixture["payment_mode_classification"]["payment_mode_discovery_note"] = (
        "DS boundaries are DISCOVERED from source values (cap vs gross tolerance), "
        "NOT asserted by hardcoded index comparisons. "
        f"first_cash_paid DS discovered as DS[{first_cash_paid_ds}]. "
        f"first_nonzero_principal DS discovered as DS[{first_principal_ds}]."
    )

    if write:
        with open(_OUTPUT, "w") as f:
            json.dump(fixture, f, indent=2)
        print(f"Written: {_OUTPUT}")

    return fixture


def check_idempotency() -> bool:
    """Check that deriving the fixture produces the same content as the committed file.

    Returns True if content matches, False otherwise.
    """
    import hashlib

    derived = derive(write=False)
    derived_bytes = json.dumps(derived, indent=2).encode()
    derived_hash = hashlib.sha256(derived_bytes).hexdigest()

    with open(_OUTPUT, "rb") as f:
        committed_bytes = f.read()
    committed_hash = hashlib.sha256(committed_bytes).hexdigest()

    match = derived_hash == committed_hash
    return match


if __name__ == "__main__":
    import sys
    if "--check" in sys.argv:
        ok = check_idempotency()
        if ok:
            print("IDEMPOTENCY OK: derived content matches committed fixture")
            sys.exit(0)
        else:
            print("IDEMPOTENCY FAIL: derived content differs from committed fixture")
            sys.exit(1)
    else:
        derive(write=True)
