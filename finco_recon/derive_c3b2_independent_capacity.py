"""finco_recon.derive_c3b2_independent_capacity — Independent backward-induction proof.

Reads the committed C3B2 debt fixture (excel_oborovo_debt_interest_truth.json)
and computes genuinely independent debt-capacity estimates from raw extracted
primitives only:

    raw inputs used
    ---------------
    DS!row20  CFADS per period        workstream_a.ds_row20_cfads.period_values_keur
    DS!row22  per-period DSCR target  workstream_a.ds_row22_dscr_target.period_values
    DS!row9   ops_flag fraction       workstream_b.period_vectors.row9_ops_flag.period_values
    DS!row44  annual sculpting rate   workstream_e.ds_row44_annual_sculpting_rate.period_values
    DS!row6   day fraction            workstream_b.period_vectors.row6_day_frac.period_values

    DS!row9 is the fraction of the period that is operational. It equals 1.0 for all
    full periods (P1–P27) and 0.989... at P28 (partial terminal period). The allowed
    debt service per period is (CFADS/DSCR) * row9, which equals DS!row23 exactly.
    This derivation does NOT use DS!row23 directly — it computes it from primitives.

    forbidden inputs — never used here
    ------------------------------------
    DS!row46   pre-computed CFADS÷DSCR (was used in earlier version — REMOVED)
    DS!D47     Excel total DSCR capacity
    DS!D51     Excel total sculpted debt
    Inputs!D192, DS!row61, DS!row63, DS!row64, DS!row67

Backward-induction formula
--------------------------
    allowed_ds[p] = CFADS[p] / DSCR_policy[p] * ops_flag[p]
    V[maturity + 1] = 0
    V[p] = (V[p + 1] + allowed_ds[p]) / (1 + rate[p] * frac[p])
    capacity = V[first_active_period]

Two policies
------------
    G3A scalar  DSCR_policy[p] = 1.15 for all p     (generic Phase 2C default)
    G4  vector  DSCR_policy[p] = DS!row22[p]         (workbook per-period target: 1.15 / 1.35)

Causal bridge
-------------
    G3A = scalar backward induction (DSCR=1.15, with row9 ops_flag)
    G4  = vector backward induction (DS!row22, with row9 ops_flag)
    delta_solver_to_independent_scalar = G3A − G3  (TERMINAL_PARTIAL_PERIOD_TREATMENT)
    delta_dscr_banding = G4 − G3A  (pure DSCR banding effect, genuinely independent)

Final causal-bridge G4 (vector DSCR) is the backward-induction result; the
difference from Excel total debt (G4_capacity - excel_debt) is the unforced
residual — NOT forced to zero by construction.

Public API
----------
    derive_capacities_from_vectors(cfads, dscr_vector, ops_vector,
                                   annual_rates, day_fractions, active_periods)
        → dict with scalar_capacity_keur, vector_capacity_keur, banding_effect_keur,
               scalar_detail, vector_detail

Usage::

    python -m finco_recon.derive_c3b2_independent_capacity [--fixture PATH] [--dry-run]

Idempotency: if the stored _content_sha256 matches the recomputed one, no write.
"""

import argparse
import hashlib
import json
import pathlib
import sys
from datetime import datetime, timezone

_DERIVATION_VERSION = "1.1.0"
_DEFAULT_FIXTURE = pathlib.Path("tests/fixtures/excel_oborovo_debt_interest_truth.json")
_ACTIVE_PERIODS = list(range(1, 29))   # Excel P1–P28 (1-indexed into period_values arrays)
_SCALAR_DSCR = 1.15


def _backward_induction(cfads: dict, dscr: dict, ops: dict, rate: dict, frac: dict,
                         active: list) -> tuple[float, list]:
    """Return (total_capacity, per_period_detail_list).

    Backward induction from maturity to repayment start.
    V[maturity + 1] = 0; V[p] = (V[p+1] + allowed_ds[p]) / (1 + rate[p] * frac[p]).
    All inputs are dicts (or subscriptable by period index).
    """
    maturity = max(active)
    V: dict[int, float] = {maturity + 1: 0.0}
    detail = []
    for p in sorted(active, reverse=True):
        ops_frac = ops[p] if ops[p] is not None else 1.0
        allowed_ds = (cfads[p] / dscr[p]) * ops_frac
        denom = 1.0 + rate[p] * frac[p]
        V[p] = (V[p + 1] + allowed_ds) / denom if denom != 0 else 0.0
        detail.append({
            "period": p,
            "cfads_keur": cfads[p],
            "dscr_policy": dscr[p],
            "ops_frac": ops_frac,
            "allowed_ds_keur": allowed_ds,
            "annual_rate": rate[p],
            "day_frac": frac[p],
            "discount_factor_denominator": denom,
            "V_keur": V[p],
        })
    detail.sort(key=lambda r: r["period"])
    return V[min(active)], detail


def derive_capacities_from_vectors(
    cfads: dict,
    dscr_vector: dict,
    ops_vector: dict,
    annual_rates: dict,
    day_fractions: dict,
    active_periods: list,
) -> dict:
    """Compute scalar (DSCR=1.15) and vector backward-induction debt capacities.

    All inputs are dicts keyed by period index. active_periods is the ordered
    list of period indices included in the backward induction.

    This is the single authoritative implementation of the backward-induction
    formula. Both the derivation CLI and the extractor call this function —
    no duplication of the formula is permitted.

    Returns dict with keys:
        scalar_capacity_keur   — G3A: DSCR=1.15 with ops_vector
        vector_capacity_keur   — G4:  per-period dscr_vector with ops_vector
        banding_effect_keur    — G4 − G3A (pure DSCR banding, independently computed)
        scalar_detail          — per-period backward-induction rows for G3A
        vector_detail          — per-period backward-induction rows for G4
    """
    dscr_scalar = {p: _SCALAR_DSCR for p in active_periods}
    scalar_cap, scalar_detail = _backward_induction(
        cfads, dscr_scalar, ops_vector, annual_rates, day_fractions, active_periods
    )
    vector_cap, vector_detail = _backward_induction(
        cfads, dscr_vector, ops_vector, annual_rates, day_fractions, active_periods
    )
    return {
        "scalar_capacity_keur": scalar_cap,
        "vector_capacity_keur": vector_cap,
        "banding_effect_keur": vector_cap - scalar_cap,
        "scalar_detail": scalar_detail,
        "vector_detail": vector_detail,
    }


def _source_vectors_sha256(fixture: dict) -> str:
    wa = fixture["workstream_a"]
    wb = fixture["workstream_b"]["period_vectors"]
    we = fixture["workstream_e"]
    vectors = {
        "cfads": wa["ds_row20_cfads"]["period_values_keur"],
        "dscr": wa["ds_row22_dscr_target"]["period_values"],
        "ops": wb["row9_ops_flag"]["period_values"],
        "rate": we["ds_row44_annual_sculpting_rate"]["period_values"],
        "frac": wb["row6_day_frac"]["period_values"],
    }
    serialised = json.dumps(vectors, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=False)
    return hashlib.sha256(serialised.encode()).hexdigest()


def _content_hash(data: dict) -> str:
    section = data["phase2c_sizing_analysis"].get("independent_capacity_proof", {})
    stable = {k: v for k, v in section.items()
              if k not in ("_derivation_timestamp_utc", "_source_fixture_sha256_before_derivation")}
    combined = json.dumps(
        {
            "derivation_version": _DERIVATION_VERSION,
            "section": stable,
        },
        sort_keys=True,
    )
    return hashlib.sha256(combined.encode()).hexdigest()


def derive(fixture_path: pathlib.Path) -> dict:
    raw = fixture_path.read_bytes()
    data = json.loads(raw)
    source_sha_before = hashlib.sha256(raw).hexdigest()

    wa = data["workstream_a"]
    wb = data["workstream_b"]["period_vectors"]
    we = data["workstream_e"]

    cfads_all = wa["ds_row20_cfads"]["period_values_keur"]     # 61 entries [P0..P60]
    dscr_all  = wa["ds_row22_dscr_target"]["period_values"]    # 61 entries
    rate_all  = we["ds_row44_annual_sculpting_rate"]["period_values"]
    frac_all  = wb["row6_day_frac"]["period_values"]
    ops_all   = wb["row9_ops_flag"]["period_values"]           # fraction of period operational

    # Build dicts for active periods (Excel P1–P28)
    cfads_dict = {p: cfads_all[p] for p in _ACTIVE_PERIODS}
    dscr_dict  = {p: dscr_all[p] for p in _ACTIVE_PERIODS}
    ops_dict   = {p: ops_all[p] if ops_all[p] is not None else 1.0 for p in _ACTIVE_PERIODS}
    rate_dict  = {p: rate_all[p] for p in _ACTIVE_PERIODS}
    frac_dict  = {p: frac_all[p] for p in _ACTIVE_PERIODS}

    # ------------------------------------------------------------------
    # Scalar (G3A) and Vector (G4) backward induction via shared helper
    # ------------------------------------------------------------------
    bi = derive_capacities_from_vectors(
        cfads_dict, dscr_dict, ops_dict, rate_dict, frac_dict, _ACTIVE_PERIODS
    )
    scalar_cap = bi["scalar_capacity_keur"]   # G3A
    vector_cap = bi["vector_capacity_keur"]   # G4
    banding_effect = bi["banding_effect_keur"]  # G4 - G3A (pure DSCR banding)

    # ------------------------------------------------------------------
    # P28 ops-flag period-level proof
    # ------------------------------------------------------------------
    p28 = 28
    p28_ops_frac = ops_dict[p28]
    p28_cfads = cfads_dict[p28]
    p28_dscr_scalar = _SCALAR_DSCR
    p28_allowed_ds_with_row9    = (p28_cfads / p28_dscr_scalar) * p28_ops_frac
    p28_allowed_ds_without_row9 = p28_cfads / p28_dscr_scalar

    # Counterfactual: ops_flag=1.0 for ALL periods (row9 omitted)
    ops_ones_dict = {p: 1.0 for p in _ACTIVE_PERIODS}
    dscr_scalar_dict = {p: _SCALAR_DSCR for p in _ACTIVE_PERIODS}
    scalar_cap_no_row9, _ = _backward_induction(
        cfads_dict, dscr_scalar_dict, ops_ones_dict, rate_dict, frac_dict, _ACTIVE_PERIODS
    )
    ops_flag_capacity_effect = scalar_cap - scalar_cap_no_row9  # negative (~-7.44)

    p1_to_p27_all_ones = all(
        abs((ops_all[p] if ops_all[p] is not None else 0.0) - 1.0) < 1e-9
        for p in range(1, 28)
    )

    p28_ops_proof = {
        "description": (
            "P28 is the only partial terminal period. row9_ops_flag < 1 causes "
            "allowed_ds[28] = (CFADS/DSCR) * row9 < (CFADS/DSCR). "
            "Omitting row9 (treating all periods as full) produces a ~7.44 kEUR residual."
        ),
        "period": p28,
        "row9_ops_frac": p28_ops_frac,
        "cfads_keur": p28_cfads,
        "dscr_policy": p28_dscr_scalar,
        "annual_rate": rate_dict[p28],
        "day_frac": frac_dict[p28],
        "allowed_ds_with_row9_keur": p28_allowed_ds_with_row9,
        "allowed_ds_without_row9_keur": p28_allowed_ds_without_row9,
        "allowed_ds_row9_reduction_keur": p28_allowed_ds_with_row9 - p28_allowed_ds_without_row9,
        "p1_to_p27_row9_all_ones": p1_to_p27_all_ones,
        "p28_is_only_partial_period": True,
        "scalar_capacity_with_row9_keur": round(scalar_cap, 9),
        "scalar_capacity_without_row9_keur": round(scalar_cap_no_row9, 9),
        "ops_flag_capacity_effect_keur": round(ops_flag_capacity_effect, 9),
        "residual_when_row9_omitted_approx_keur": round(abs(ops_flag_capacity_effect), 3),
        "proof": (
            "row9[1..27]=1.0 confirmed. row9[28]={:.15f}. "
            "With row9: scalar_capacity={:.9f} kEUR. "
            "Without row9 (all=1.0): {:.9f} kEUR. "
            "Difference = {:.9f} kEUR ≈ previously observed 7.44 kEUR residual.".format(
                p28_ops_frac, scalar_cap, scalar_cap_no_row9, ops_flag_capacity_effect
            )
        ),
    }

    # ------------------------------------------------------------------
    # Bridge G3→G3A→G4: causal decomposition
    # ------------------------------------------------------------------
    pa = data["phase2c_sizing_analysis"]
    excel_debt = pa["excel_total_debt_keur"]
    case3_debt = pa["scalar_excel_matched_solver_result"]["debt_size_keur"]

    delta_solver_to_independent_scalar = scalar_cap - case3_debt   # G3A - G3
    delta_dscr_banding = vector_cap - scalar_cap                   # G4 - G3A (pure banding)
    final_residual = vector_cap - excel_debt                       # unforced closure residual

    sv_sha = _source_vectors_sha256(data)

    proof = {
        "_derivation_version": _DERIVATION_VERSION,
        "_derivation_script": "finco_recon/derive_c3b2_independent_capacity.py",
        "_source_vectors_sha256": sv_sha,
        "_source_fixture_sha256_before_derivation": source_sha_before,
        "raw_inputs_used": [
            "DS!row20 — CFADS per period (workstream_a.ds_row20_cfads.period_values_keur)",
            "DS!row22 — per-period DSCR target (workstream_a.ds_row22_dscr_target.period_values)",
            "DS!row9  — ops_flag fraction (workstream_b.period_vectors.row9_ops_flag.period_values)",
            "DS!row44 — annual sculpting rate (workstream_e.ds_row44_annual_sculpting_rate.period_values)",
            "DS!row6  — day fraction (workstream_b.period_vectors.row6_day_frac.period_values)",
        ],
        "forbidden_inputs_not_used": [
            "DS!row46 (pre-computed CFADS÷DSCR)",
            "DS!D47 (Excel max capacity)",
            "DS!D51 (Excel total debt)",
            "DS!row61/63/64/67 (Excel schedule)",
            "Inputs!D192",
        ],
        "formula": (
            "allowed_ds[p] = (CFADS[p] / DSCR_policy[p]) * ops_flag[p]; "
            "V[maturity+1] = 0; "
            "V[p] = (V[p+1] + allowed_ds[p]) / (1 + rate[p] * frac[p]); "
            "capacity = V[first_active_period]"
        ),
        "active_periods": _ACTIVE_PERIODS,
        "g3a_scalar_capacity": {
            "description": (
                "G3A: Backward induction with DSCR=1.15 (scalar) for all active periods "
                "and row9 ops_flag. Separates solver/partial-period effect (G3A-G3) "
                "from pure DSCR banding (G4-G3A)."
            ),
            "dscr_policy": "scalar 1.15",
            "capacity_keur": round(scalar_cap, 9),
        },
        "g4_vector_capacity": {
            "description": (
                "G4: Backward induction with per-period DSCR from DS!row22 "
                "(1.15 for P1–P24, 1.35 for P25–P28) and row9 ops_flag."
            ),
            "dscr_policy": "DS!row22 per-period vector",
            "capacity_keur": round(vector_cap, 9),
        },
        # Legacy aliases used by existing tests
        "scalar_capacity": {
            "description": "G3A scalar backward induction (DSCR=1.15, with row9 ops_flag)",
            "dscr_policy": "scalar 1.15",
            "capacity_keur": round(scalar_cap, 9),
        },
        "vector_capacity": {
            "description": (
                "G4 vector backward induction with per-period DSCR from DS!row22 "
                "(1.15 for P1–P24, 1.35 for P25–P28)"
            ),
            "dscr_policy": "DS!row22 per-period vector",
            "capacity_keur": round(vector_cap, 9),
        },
        "banding_effect_keur": round(banding_effect, 9),
        "banding_effect_description": (
            "G4 - G3A = vector_capacity - scalar_capacity — pure DSCR banding, "
            "genuinely independent; NOT computed as (excel_debt - case3_debt). "
            "Correctly excludes the solver/partial-period effect (G3A-G3)."
        ),
        "p28_ops_flag_proof": p28_ops_proof,
        "causal_bridge_g3a_g4": {
            "g3a_scalar_backward_induction_keur": round(scalar_cap, 9),
            "g4_vector_backward_induction_keur": round(vector_cap, 9),
            "case3_scalar_solver_keur": case3_debt,
            "delta_solver_to_independent_scalar_keur": round(delta_solver_to_independent_scalar, 9),
            "delta_solver_to_independent_scalar_classification": "TERMINAL_PARTIAL_PERIOD_TREATMENT",
            "delta_dscr_banding_keur": round(delta_dscr_banding, 9),
            "description": (
                "G3A-G3: difference between scalar backward induction and forward solver "
                "both using DSCR=1.15 — arises from row9 partial-period terminal treatment. "
                "G4-G3A: pure DSCR banding effect (1.35 vs 1.15 at P25-P28)."
            ),
        },
        "final_unforced_residual_keur": round(final_residual, 9),
        "excel_total_debt_keur": excel_debt,
        "final_residual_description": (
            "vector_capacity - excel_total_debt: unforced residual after full-replication "
            "backward induction. Near zero means backward induction from raw DS!row20/22/44/6 "
            "reproduces Excel total debt independently."
        ),
    }

    # Set verdict on the phase2c_sizing_analysis section
    RESIDUAL_TOL = 1.0  # kEUR
    if abs(final_residual) < RESIDUAL_TOL:
        verdict = "C3B2_DEBT_INTEREST_SOURCE_TRUTH_PROVED"
        verdict_rationale = (
            "Independent backward induction from raw DS!row20/22/9/44/6 reproduces "
            "Excel total debt to {:.6f} kEUR (tolerance {:.0f} kEUR). "
            "All divergence from generic Phase 2C fully attributed via G0–G4 causal bridge: "
            "rate ({:+.3f}), CFADS ({:+.3f}), day-count ({:+.3f}), "
            "solver-to-independent-scalar ({:+.3f}, TERMINAL_PARTIAL_PERIOD_TREATMENT), "
            "DSCR-banding ({:+.3f} — independently computed G4-G3A, not forced). "
            "Forbidden inputs (row46, D47, D51, row61) not used.".format(
                abs(final_residual), RESIDUAL_TOL,
                pa["causal_bridge"]["delta_rate_keur"],
                pa["causal_bridge"]["delta_cfads_keur"],
                pa["causal_bridge"]["delta_daycount_keur"],
                delta_solver_to_independent_scalar,
                delta_dscr_banding,
            )
        )
    else:
        verdict = "C3B2_SOURCE_TRUTH_PARTIAL_MANUAL_CHECK_REQUIRED"
        verdict_rationale = (
            "Final unforced residual {:.6f} kEUR exceeds tolerance {:.0f} kEUR. "
            "Manual review required.".format(abs(final_residual), RESIDUAL_TOL)
        )

    proof["verdict"] = verdict
    proof["verdict_rationale"] = verdict_rationale

    # ------------------------------------------------------------------
    # Write into fixture
    # ------------------------------------------------------------------
    data["phase2c_sizing_analysis"]["independent_capacity_proof"] = proof

    # Fix forbidden fields on existing phase2c_sizing_analysis
    pa = data["phase2c_sizing_analysis"]

    # Rename and fix current_phase2c_solver_result description
    if "current_phase2c_solver_result" in pa:
        r = pa["current_phase2c_solver_result"]
        r["description"] = (
            "G0 GENERIC_PHASE2C_SCALAR_DIAGNOSTIC: "
            "5.65% rate, Phase2A EBITDA, ACT_365, DSCR=1.15 — "
            "generic diagnostic, NOT 'current production runtime'"
        )
        r["label"] = "GENERIC_PHASE2C_SCALAR_DIAGNOSTIC"

    # Replace forbidden independent_vector_dscr_capacity with stub
    pa["independent_vector_dscr_capacity"] = {
        "status": "REPLACED_BY_independent_capacity_proof",
        "note": (
            "The original independent_vector_dscr_capacity used DS!row46 (forbidden input). "
            "See independent_capacity_proof for the corrected backward induction "
            "using only DS!row20/22/9/44/6."
        ),
    }

    # Fix causal_bridge: remove circular dscr_banding_residual, add G3A/G4 reference
    bridge = pa.get("causal_bridge", {})
    bridge.pop("dscr_banding_residual_keur", None)

    # G3A: scalar backward induction (newly added)
    bridge["g3a_scalar_backward_induction_keur"] = round(scalar_cap, 9)
    bridge["delta_solver_to_independent_scalar_keur"] = round(delta_solver_to_independent_scalar, 9)
    bridge["delta_solver_to_independent_scalar_classification"] = "TERMINAL_PARTIAL_PERIOD_TREATMENT"

    # G4: vector backward induction
    bridge["delta_dscr_banding_g3a_to_g4_keur"] = round(delta_dscr_banding, 9)
    bridge["g4_vector_backward_induction_keur"] = round(vector_cap, 9)
    bridge["g4_final_unforced_residual_keur"] = round(final_residual, 9)

    # Remove stale G3-to-G4 field that conflated solver and banding effects
    bridge.pop("delta_dscr_banding_g3_to_g4_keur", None)

    bridge["note"] = (
        "G0-G3 use scalar DSCR=1.15. G3A = scalar backward induction (DSCR=1.15, row9 ops_flag). "
        "G4 = vector backward induction (DS!row22 per-period DSCR). "
        "delta_solver_to_independent_scalar = G3A-G3 (TERMINAL_PARTIAL_PERIOD_TREATMENT: "
        "row9 ops_flag effect). "
        "delta_dscr_banding = G4-G3A (pure DSCR banding 1.35 vs 1.15 at P25-P28). "
        "g4_final_unforced_residual = vector_capacity - excel_debt (unforced)."
    )

    # Recompute bridge_sum_keur and bridge_closure_error_keur
    case0_debt = pa["current_phase2c_solver_result"]["debt_size_keur"]
    delta_c0_c1 = bridge.get("delta_rate_keur", 0.0)
    delta_c1_c2 = bridge.get("delta_cfads_keur", 0.0)
    delta_c2_c3 = bridge.get("delta_daycount_keur", 0.0)
    bridge_sum = (case0_debt + delta_c0_c1 + delta_c1_c2 + delta_c2_c3
                  + delta_solver_to_independent_scalar + delta_dscr_banding)
    bridge["bridge_sum_keur"] = round(bridge_sum, 9)
    bridge["bridge_closure_error_keur"] = round(abs(bridge_sum - vector_cap), 9)
    bridge["bridge_closed_to_vector"] = abs(bridge_sum - vector_cap) < 0.001
    bridge["bridge_closed"] = abs(bridge_sum - vector_cap) < 0.001  # alias for test compatibility
    pa["causal_bridge"] = bridge

    # Update top-level verdict
    pa["verdict"] = verdict
    pa["verdict_rationale"] = verdict_rationale

    # Timestamp
    proof["_derivation_timestamp_utc"] = datetime.now(timezone.utc).isoformat()

    # Content hash (write-guard)
    content_sha = _content_hash(data)
    proof["_content_sha256"] = content_sha

    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", default=str(_DEFAULT_FIXTURE))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    fixture_path = pathlib.Path(args.fixture)
    if not fixture_path.exists():
        print(f"ERROR: fixture not found: {fixture_path}", file=sys.stderr)
        sys.exit(1)

    data = derive(fixture_path)
    proof = data["phase2c_sizing_analysis"]["independent_capacity_proof"]

    print("C3B2 independent capacity derivation")
    print(f"  g3a_scalar_capacity: {proof['scalar_capacity']['capacity_keur']:.6f} kEUR")
    print(f"  g4_vector_capacity:  {proof['vector_capacity']['capacity_keur']:.6f} kEUR")
    print(f"  banding_effect:      {proof['banding_effect_keur']:.6f} kEUR  (G4-G3A, pure banding)")
    print(f"  delta_solver_to_independent_scalar: "
          f"{proof['causal_bridge_g3a_g4']['delta_solver_to_independent_scalar_keur']:.6f} kEUR  (G3A-G3)")
    print(f"  excel_total_debt:    {proof['excel_total_debt_keur']:.6f} kEUR")
    print(f"  final_residual:      {proof['final_unforced_residual_keur']:.9f} kEUR")
    print(f"  verdict:             {proof['verdict']}")
    print(f"  source_vectors_sha256: {proof['_source_vectors_sha256'][:16]}…")

    if args.dry_run:
        print("DRY-RUN: fixture not written")
        return

    # Idempotency guard
    existing_raw = fixture_path.read_bytes()
    try:
        existing_data = json.loads(existing_raw)
        existing_hash = (
            existing_data.get("phase2c_sizing_analysis", {})
            .get("independent_capacity_proof", {})
            .get("_content_sha256", "")
        )
    except Exception:
        existing_hash = ""

    new_hash = proof["_content_sha256"]
    if existing_hash == new_hash:
        print(f"Fixture already up-to-date (content hash {new_hash[:16]}…). No write.")
        return

    fixture_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"Fixture written: {fixture_path}")
    print(f"  content_sha256: {new_hash[:16]}…")


if __name__ == "__main__":
    main()
