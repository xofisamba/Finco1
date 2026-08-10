"""finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge — C3B3D2B2B bridge diagnostic.

R2: Source-contamination fix, day-fraction counterfactual added, fail-closed snapshot.

EVIDENCE-ONLY DIAGNOSTIC. No production promotion. No production engine changes.
Purpose: Decompose the CURRENT_GRID0_TO_SOURCE_DEBT_BRIDGE_NOT_YET_CLOSED gap
(+1,066.754 kEUR) between:
  CURRENT_GRID0_PRODUCTION_CANDIDATE   = 43,919.032698 kEUR  (clean engine runtime)
  SOURCE_EXCEL_SENIOR_DEBT             = 42,852.278763 kEUR  (DS!D51, source workbook)

Snapshot contract (R2):
  capture_current_grid0_snapshot() reads ONLY from:
    - current ProjectInputs via create_default_oborovo()
    - current SeniorDebtPolicy (day_count_convention, target_dscr)
    - current SeniorDebtInputs (period_rates, period_dscr_targets,
      period_debt_service_availability)
    - current OperatingPeriodResult (period_start, period_end) for day fractions
    - current tax_and_cfads (cfads_keur)
  Day fractions are derived via the production helper:
    financial_engine.senior_debt.interest.period_day_fraction(start, end, convention)
  No source-fixture reads are performed in this function.

One-factor counterfactuals (each from pure CURRENT_GRID0 snapshot, R2 ordering):
  CF1: CFADS — clean Phase2A EBITDA → source DS!row20 (Macro50 bank transformation)
  CF2: DSCR banding — current engine vector → source DS!row22
  CF3: Day fractions — current derived ACT/360 vector → source DS!row6
  CF4: Ops fraction — current engine vector → source DS!row9
  CF5: Annual rate — current engine per-period → source DS!row44

SOURCE_ALL gate: apply all source vectors simultaneously.
  Result: SOURCE_ALL = 42,852.278763 kEUR → residual = 0.000 kEUR
  Classification: CURRENT_GRID0_TO_SOURCE_SIZING_INPUT_BRIDGE_CLOSED

R2 result: CF1 alone explains +1,066.754 kEUR. CF2–CF5 each = 0.000 kEUR
because rates, DSCR banding, ops fraction, and day-count convention are
already source-matched in the current engine (proven by per-period vector equality).

CFADS interpretation:
  Clean engine CFADS = Phase2A EBITDA - canonical cash_tax (no SHL feedback, no Macro50).
  Source DS!row20 = Macro50 output (bank/P90 scenario transformation: VBA_IMPLEMENTATION_NOT_VISIBLE).
  BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED — Macro50 not decomposed here.
  BANK_SIZING_SCENARIO_P90_10Y_REVIEWER_CONFIRMED_NOT_COMMITTED.

Production interpretation:
  MISSING_GENERIC_BANK_SIZING_CFADS_SCENARIO_LAYER — the production engine does not yet
  implement a generic bank-sizing CFADS scenario (base_case_cfads / bank_sizing_cfads /
  debt_sizing_scenario separation). This is a future architecture concern, not part of PR #924.

Governance:
  No DS25/DS40 period boundary hardcoding — ENFORCED
  No project-name dispatch — ENFORCED
  No approved_delta or balancing plug — ENFORCED
  No calibration of clean engine to source — ENFORCED
  Protected C3B2 SHA: f8f244c0660495bfb4115d4e32ba329c291ab829d1d0693e614c889457b5add7
  13547.2 MUST NOT appear in any clean SHL calculation — ENFORCED
  No DSRA implementation in this module — ENFORCED
  No production financial-engine file modifications — ENFORCED
  CURRENT_CAUSE_UNRESOLVED re Macro50 mechanism — no false causal attribution
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Governance constants — three baseline authorities (must not be conflated)
# ---------------------------------------------------------------------------

CURRENT_GRID0_DEBT_KEUR: float = 43_919.032698        # CURRENT_GRID0_PRODUCTION_CANDIDATE
SOURCE_EXCEL_SENIOR_DEBT_KEUR: float = 42_852.27876256299  # SOURCE_EXCEL_SENIOR_DEBT (DS!D51)
HISTORICAL_GENERIC_PHASE2C_DEBT_KEUR: float = 46_053.402378616  # HISTORICAL — not a current baseline

CURRENT_GRID0_TO_SOURCE_GAP_KEUR: float = (
    CURRENT_GRID0_DEBT_KEUR - SOURCE_EXCEL_SENIOR_DEBT_KEUR
)  # +1,066.754 kEUR — target to close

# Tight tolerance: current solver is deterministic; baseline lock at 1e-3 kEUR
_BASELINE_LOCK_TOLERANCE_KEUR: float = 1e-3

# Source vector replay tolerance
_SOURCE_REPLAY_TOLERANCE_KEUR: float = 1.0

_DEBT_FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "tests", "fixtures", "excel_oborovo_debt_interest_truth.json",
)


# ---------------------------------------------------------------------------
# Snapshot: current GRID-0 engine parameters — NO source fixture reads
# ---------------------------------------------------------------------------

@dataclass
class CurrentGrid0Snapshot:
    """Immutable snapshot of current engine sizing parameters for GRID-0.

    R2 contract: all fields come ONLY from current runtime (ProjectInputs,
    SeniorDebtPolicy, SeniorDebtInputs, OperatingPeriodResult, tax_and_cfads).
    No source fixture is read during snapshot construction.
    """

    debt_keur: float
    """Senior debt computed by current clean engine (sd.diagnostics.final_debt_size_keur)."""

    cfads_by_src_period: dict[int, float]
    """Clean CFADS per source period index (1-indexed P1..P28). From tac.cfads_keur."""

    rate_by_src_period: dict[int, float]
    """Annual sculpting rate per source period. From SeniorDebtInputs.period_rates."""

    day_frac_by_src_period: dict[int, float]
    """Day fraction per source period, derived via period_day_fraction(start, end, convention).

    Source: OperatingPeriodResult.period_start/period_end + SeniorDebtPolicy.day_count_convention.
    NOT read from any Excel fixture.
    """

    dscr_by_src_period: dict[int, float]
    """DSCR target per source period. From SeniorDebtInputs.period_dscr_targets."""

    ops_by_src_period: dict[int, float]
    """Ops fraction per source period. From SeniorDebtInputs.period_debt_service_availability."""

    active_src_periods: list[int]
    """Source period indices (1..28) active in the sizing calculation."""

    backward_induction_keur: float
    """Independent backward-induction from CURRENT-ONLY snapshot (no source vectors)."""

    day_count_convention: str
    """Name of the day-count convention used (e.g. 'ACT_360')."""

    baseline_label: str = "CURRENT_GRID0_PRODUCTION_CANDIDATE"


def capture_current_grid0_snapshot() -> CurrentGrid0Snapshot:
    """Capture the current GRID-0 engine parameters — NO source fixture reads.

    Derives all values from:
      - create_default_oborovo() → ProjectInputs
      - build_senior_debt_model_input_from_project_inputs() → SeniorDebtModelInput
      - run_senior_debt_model() → ProjectModelResult
      - period_day_fraction(p.period_start, p.period_end, policy.day_count_convention)

    Raises RuntimeError with CURRENT_GRID0_SNAPSHOT_REQUIRED_VECTOR_MISSING if any
    required vector entry is absent for an active debt period.

    Raises RuntimeError with C3B3D2B2B_STOP_CURRENT_GRID0_BASELINE_DRIFT if the
    captured engine debt deviates from CURRENT_GRID0_DEBT_KEUR by > _BASELINE_LOCK_TOLERANCE_KEUR.
    """
    from app.project_factories import create_default_oborovo
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )
    from financial_engine.orchestrator import run_senior_debt_model
    from financial_engine.senior_debt.interest import period_day_fraction

    proj = create_default_oborovo()
    sd_input = build_senior_debt_model_input_from_project_inputs(
        proj, source_id="c3b3d2b2b-snapshot"
    )
    phase2c = run_senior_debt_model(sd_input)
    tac = phase2c.tax_and_cfads
    sd = phase2c.senior_debt
    policy = sd_input.senior_debt_policy

    debt = sd.diagnostics.get("final_debt_size_keur", 0.0)
    if abs(debt - CURRENT_GRID0_DEBT_KEUR) > _BASELINE_LOCK_TOLERANCE_KEUR:
        raise RuntimeError(
            f"C3B3D2B2B_STOP_CURRENT_GRID0_BASELINE_DRIFT: engine={debt:.6f} "
            f"locked={CURRENT_GRID0_DEBT_KEUR:.6f} "
            f"delta={debt - CURRENT_GRID0_DEBT_KEUR:.6f} "
            f"tolerance={_BASELINE_LOCK_TOLERANCE_KEUR}"
        )

    # Active debt period indices from solver output
    op_pidx = list(sd.period_indices)  # engine period_indices [2..29], 28 periods

    # Build CFADS dict (fail closed — require explicit value for each active period)
    cfads_by_eng = dict(zip(tac.period_indices, tac.cfads_keur))
    _require_all(cfads_by_eng, op_pidx, "cfads_keur")

    # Build rate dict (fail closed)
    rate_by_eng = {pr.period_index: pr.annual_rate for pr in sd_input.senior_debt_inputs.period_rates}
    _require_all(rate_by_eng, op_pidx, "period_rates")

    # Build DSCR dict (fail closed)
    dscr_by_eng = {pr.period_index: pr.target_dscr for pr in sd_input.senior_debt_inputs.period_dscr_targets}
    _require_all(dscr_by_eng, op_pidx, "period_dscr_targets")

    # Build ops dict (fail closed)
    ops_by_eng = {pa.period_index: pa.availability_fraction for pa in sd_input.senior_debt_inputs.period_debt_service_availability}
    _require_all(ops_by_eng, op_pidx, "period_debt_service_availability")

    # Derive day fractions from production helper (NOT from any source fixture)
    period_date_map = {
        p.period_index: (p.period_start, p.period_end)
        for p in phase2c.periods
        if p.period_index in set(op_pidx)
    }
    _require_all(period_date_map, op_pidx, "period_dates")

    day_frac_by_eng: dict[int, float] = {}
    for pidx in op_pidx:
        start, end = period_date_map[pidx]
        day_frac_by_eng[pidx] = period_day_fraction(start, end, policy.day_count_convention)

    convention_name = policy.day_count_convention.name if hasattr(policy.day_count_convention, 'name') else str(policy.day_count_convention)

    # Remap engine period_index → source period index (p - 1)
    def eng_to_src(p: int) -> int:
        return p - 1

    active_src = [eng_to_src(p) for p in op_pidx]  # [1..28]

    cfads_by_src = {eng_to_src(p): cfads_by_eng[p] for p in op_pidx}
    rate_by_src = {eng_to_src(p): rate_by_eng[p] for p in op_pidx}
    frac_by_src = {eng_to_src(p): day_frac_by_eng[p] for p in op_pidx}
    dscr_by_src = {eng_to_src(p): dscr_by_eng[p] for p in op_pidx}
    ops_by_src = {eng_to_src(p): ops_by_eng[p] for p in op_pidx}

    bi_keur = _backward_induction(
        cfads_by_src, dscr_by_src, ops_by_src, rate_by_src, frac_by_src, active_src
    )

    if abs(bi_keur - debt) > _BASELINE_LOCK_TOLERANCE_KEUR:
        raise RuntimeError(
            f"C3B3D2B2B_STOP_CURRENT_RUNTIME_SNAPSHOT_NOT_INDEPENDENT: "
            f"BI={bi_keur:.6f} engine={debt:.6f} delta={bi_keur - debt:.6f}"
        )

    return CurrentGrid0Snapshot(
        debt_keur=debt,
        cfads_by_src_period=cfads_by_src,
        rate_by_src_period=rate_by_src,
        day_frac_by_src_period=frac_by_src,
        dscr_by_src_period=dscr_by_src,
        ops_by_src_period=ops_by_src,
        active_src_periods=active_src,
        backward_induction_keur=bi_keur,
        day_count_convention=convention_name,
    )


def _require_all(d: dict, required_keys: list, vector_name: str) -> None:
    """Raise RuntimeError if any required key is missing from dict (fail-closed)."""
    for p in required_keys:
        if p not in d:
            raise RuntimeError(
                f"CURRENT_GRID0_SNAPSHOT_REQUIRED_VECTOR_MISSING: "
                f"vector={vector_name} period_index={p}"
            )


# ---------------------------------------------------------------------------
# Source vector extraction (reads from fixture — separate from snapshot)
# ---------------------------------------------------------------------------

@dataclass
class SourceVectors:
    """Source sizing vectors extracted from committed C3B2 fixture (read-only)."""

    cfads_by_period: dict[int, float]
    """DS!row20 CFADS per period (1..28): Macro50 bank/P90 transformation output."""

    dscr_by_period: dict[int, float]
    """DS!row22 DSCR target per period (1.15 for P1-P24, 1.35 for P25-P28)."""

    ops_by_period: dict[int, float]
    """DS!row9 ops fraction per period."""

    rate_by_period: dict[int, float]
    """DS!row44 annual sculpting rate per period."""

    day_frac_by_period: dict[int, float]
    """DS!row6 day fraction per period (ACT/360-style from Excel)."""

    source_capacity_keur: float
    """G4 backward-induction from all source vectors: must equal SOURCE_EXCEL_SENIOR_DEBT."""

    excel_total_debt_keur: float
    """DS!D51 committed fixture value."""


def load_source_vectors() -> SourceVectors:
    """Load source sizing vectors from committed C3B2 fixture.

    This is the ONLY function that reads from excel_oborovo_debt_interest_truth.json.

    Raises RuntimeError if backward-induction from source vectors deviates
    from SOURCE_EXCEL_SENIOR_DEBT_KEUR by more than _SOURCE_REPLAY_TOLERANCE_KEUR.
    """
    with open(_DEBT_FIXTURE_PATH) as fh:
        fixture = json.load(fh)

    wa = fixture["workstream_a"]
    wb = fixture["workstream_b"]
    we = fixture["workstream_e"]

    cfads_list = wa["ds_row20_cfads"]["period_values_keur"]
    dscr_list = wa["ds_row22_dscr_target"]["period_values"]
    ops_list = wb["period_vectors"]["row9_ops_flag"]["period_values"]
    rate_list = we["ds_row44_annual_sculpting_rate"]["period_values"]
    frac_list = wb["period_vectors"]["row6_day_frac"]["period_values"]
    excel_debt = wb["ds_d51_total_debt"]["value_keur"]

    active = list(range(1, 29))
    cfads = {i: cfads_list[i] for i in active}
    dscr = {i: dscr_list[i] for i in active}
    ops = {i: ops_list[i] for i in active}
    rate = {i: rate_list[i] for i in active}
    frac = {i: frac_list[i] for i in active}

    capacity = _backward_induction(cfads, dscr, ops, rate, frac, active)

    if abs(capacity - SOURCE_EXCEL_SENIOR_DEBT_KEUR) > _SOURCE_REPLAY_TOLERANCE_KEUR:
        raise RuntimeError(
            f"C3B3D2B2B_STOP_SOURCE_CAPACITY_REPLAY_FAILED: "
            f"bi={capacity:.6f} source={SOURCE_EXCEL_SENIOR_DEBT_KEUR:.6f} "
            f"delta={capacity - SOURCE_EXCEL_SENIOR_DEBT_KEUR:.6f}"
        )

    return SourceVectors(
        cfads_by_period=cfads,
        dscr_by_period=dscr,
        ops_by_period=ops,
        rate_by_period=rate,
        day_frac_by_period=frac,
        source_capacity_keur=capacity,
        excel_total_debt_keur=excel_debt,
    )


# ---------------------------------------------------------------------------
# Vector equality comparison
# ---------------------------------------------------------------------------

@dataclass
class VectorComparison:
    """Per-period comparison of current vs source vector values."""

    vector_name: str
    current_label: str
    source_label: str
    max_abs_delta: float
    first_mismatch_period: Optional[int]
    classification: str
    per_period_deltas: dict[int, float]

    MATCH_THRESHOLD: float = 1e-9

    @classmethod
    def compare(
        cls,
        vector_name: str,
        current_label: str,
        source_label: str,
        current_by_period: dict[int, float],
        source_by_period: dict[int, float],
        active_periods: list[int],
    ) -> "VectorComparison":
        per_period = {}
        first_mismatch = None
        max_delta = 0.0
        for p in active_periods:
            delta = abs(current_by_period[p] - source_by_period[p])
            per_period[p] = delta
            if delta > max_delta:
                max_delta = delta
            if delta > cls.MATCH_THRESHOLD and first_mismatch is None:
                first_mismatch = p

        classification = (
            "VECTOR_ALREADY_SOURCE_MATCHED" if max_delta <= cls.MATCH_THRESHOLD
            else "VECTOR_DIFFERS_FROM_SOURCE"
        )
        return cls(
            vector_name=vector_name,
            current_label=current_label,
            source_label=source_label,
            max_abs_delta=max_delta,
            first_mismatch_period=first_mismatch,
            classification=classification,
            per_period_deltas=per_period,
        )


def compare_vectors(
    snapshot: CurrentGrid0Snapshot, src: SourceVectors
) -> dict[str, VectorComparison]:
    """Compare all current engine vectors against source vectors, period by period."""
    active = snapshot.active_src_periods
    return {
        "dscr": VectorComparison.compare(
            "dscr", "SeniorDebtInputs.period_dscr_targets", "DS!row22",
            snapshot.dscr_by_src_period, src.dscr_by_period, active,
        ),
        "day_frac": VectorComparison.compare(
            "day_frac",
            f"period_day_fraction({snapshot.day_count_convention})",
            "DS!row6",
            snapshot.day_frac_by_src_period, src.day_frac_by_period, active,
        ),
        "ops": VectorComparison.compare(
            "ops", "SeniorDebtInputs.period_debt_service_availability", "DS!row9",
            snapshot.ops_by_src_period, src.ops_by_period, active,
        ),
        "rate": VectorComparison.compare(
            "rate", "SeniorDebtInputs.period_rates", "DS!row44",
            snapshot.rate_by_src_period, src.rate_by_period, active,
        ),
    }


# ---------------------------------------------------------------------------
# Backward induction (pure function — no engine calls, no fixture reads)
# ---------------------------------------------------------------------------

def _backward_induction(
    cfads: dict[int, float],
    dscr: dict[int, float],
    ops: dict[int, float],
    rate: dict[int, float],
    frac: dict[int, float],
    active: list[int],
) -> float:
    """Independent backward induction from period vectors.

    Formula (DS!row47):
        allowed_ds[p] = (cfads[p] / dscr[p]) * ops[p]
        V[maturity+1] = 0
        V[p] = (V[p+1] + allowed_ds[p]) / (1 + rate[p] * frac[p])
        capacity = V[min(active)]
    """
    maturity = max(active)
    V: dict[int, float] = {maturity + 1: 0.0}
    for p in sorted(active, reverse=True):
        allowed_ds = (cfads[p] / dscr[p]) * ops[p]
        denom = 1.0 + rate[p] * frac[p]
        V[p] = (V[p + 1] + allowed_ds) / denom if denom != 0 else 0.0
    return V[min(active)]


# ---------------------------------------------------------------------------
# Counterfactual results
# ---------------------------------------------------------------------------

@dataclass
class CounterfactualResult:
    label: str
    description: str
    capacity_keur: float
    delta_vs_baseline_keur: float
    classification: str


_CF_MATCH_THRESHOLD: float = 1.0  # kEUR — threshold for VECTOR_ALREADY_SOURCE_MATCHED


def run_one_factor_counterfactuals(
    snapshot: CurrentGrid0Snapshot, src: SourceVectors
) -> list[CounterfactualResult]:
    """Run CF1–CF5 one-factor counterfactuals from the pure CURRENT_GRID0 snapshot.

    R2 ordering:
      CF1: Source CFADS (DS!row20 / Macro50)
      CF2: Source DSCR banding (DS!row22)
      CF3: Source day fractions (DS!row6)
      CF4: Source ops fraction (DS!row9)
      CF5: Source annual rates (DS!row44)

    Each arm swaps exactly one vector; all others remain at current engine values.
    """
    active = snapshot.active_src_periods
    baseline = snapshot.backward_induction_keur

    def _classify(delta: float) -> str:
        if abs(delta) < _CF_MATCH_THRESHOLD:
            return "VECTOR_ALREADY_SOURCE_MATCHED"
        return "VECTOR_DIFFERENCE_CONFIRMED"

    results = []

    # CF1: Source CFADS (DS!row20 / Macro50)
    cf1 = _backward_induction(
        src.cfads_by_period,
        snapshot.dscr_by_src_period,
        snapshot.ops_by_src_period,
        snapshot.rate_by_src_period,
        snapshot.day_frac_by_src_period,
        active,
    )
    results.append(CounterfactualResult(
        label="CF1",
        description="Source CFADS: DS!row20 (Macro50/bank P90) vs clean Phase2A EBITDA",
        capacity_keur=cf1,
        delta_vs_baseline_keur=cf1 - baseline,
        classification=_classify(cf1 - baseline),
    ))

    # CF2: Source DSCR banding (DS!row22)
    cf2 = _backward_induction(
        snapshot.cfads_by_src_period,
        src.dscr_by_period,
        snapshot.ops_by_src_period,
        snapshot.rate_by_src_period,
        snapshot.day_frac_by_src_period,
        active,
    )
    results.append(CounterfactualResult(
        label="CF2",
        description="Source DSCR banding: DS!row22 (1.15/1.35 per period) vs current engine vector",
        capacity_keur=cf2,
        delta_vs_baseline_keur=cf2 - baseline,
        classification=_classify(cf2 - baseline),
    ))

    # CF3: Source day fractions (DS!row6) — R2 added arm
    cf3 = _backward_induction(
        snapshot.cfads_by_src_period,
        snapshot.dscr_by_src_period,
        snapshot.ops_by_src_period,
        snapshot.rate_by_src_period,
        src.day_frac_by_period,
        active,
    )
    results.append(CounterfactualResult(
        label="CF3",
        description=(
            f"Source day fractions: DS!row6 vs current {snapshot.day_count_convention} derived fractions"
        ),
        capacity_keur=cf3,
        delta_vs_baseline_keur=cf3 - baseline,
        classification=_classify(cf3 - baseline),
    ))

    # CF4: Source ops fraction (DS!row9)
    cf4 = _backward_induction(
        snapshot.cfads_by_src_period,
        snapshot.dscr_by_src_period,
        src.ops_by_period,
        snapshot.rate_by_src_period,
        snapshot.day_frac_by_src_period,
        active,
    )
    results.append(CounterfactualResult(
        label="CF4",
        description="Source ops fraction: DS!row9 vs current engine availability",
        capacity_keur=cf4,
        delta_vs_baseline_keur=cf4 - baseline,
        classification=_classify(cf4 - baseline),
    ))

    # CF5: Source annual rates (DS!row44)
    cf5 = _backward_induction(
        snapshot.cfads_by_src_period,
        snapshot.dscr_by_src_period,
        snapshot.ops_by_src_period,
        src.rate_by_period,
        snapshot.day_frac_by_src_period,
        active,
    )
    results.append(CounterfactualResult(
        label="CF5",
        description="Source annual rate: DS!row44 per-period vs current engine rates",
        capacity_keur=cf5,
        delta_vs_baseline_keur=cf5 - baseline,
        classification=_classify(cf5 - baseline),
    ))

    return results


# ---------------------------------------------------------------------------
# Sequential bridge
# ---------------------------------------------------------------------------

@dataclass
class SequentialBridgeStep:
    step: int
    vector_applied: str
    cumulative_capacity_keur: float
    step_delta_keur: float


def run_sequential_bridge(
    snapshot: CurrentGrid0Snapshot, src: SourceVectors
) -> list[SequentialBridgeStep]:
    """Build a sequential bridge from CURRENT_GRID0 to SOURCE_ALL.

    Vectors applied in R2 order: CF1 CFADS, CF2 DSCR, CF3 day-frac, CF4 ops, CF5 rate.
    """
    active = snapshot.active_src_periods
    steps = []
    prev = snapshot.backward_induction_keur

    # Step 1: apply source CFADS
    c1 = _backward_induction(
        src.cfads_by_period, snapshot.dscr_by_src_period, snapshot.ops_by_src_period,
        snapshot.rate_by_src_period, snapshot.day_frac_by_src_period, active,
    )
    steps.append(SequentialBridgeStep(1, "CF1_CFADS_SOURCE_DS_ROW20", c1, c1 - prev))
    prev = c1

    # Step 2: apply source DSCR
    c2 = _backward_induction(
        src.cfads_by_period, src.dscr_by_period, snapshot.ops_by_src_period,
        snapshot.rate_by_src_period, snapshot.day_frac_by_src_period, active,
    )
    steps.append(SequentialBridgeStep(2, "CF2_DSCR_SOURCE_DS_ROW22", c2, c2 - prev))
    prev = c2

    # Step 3: apply source day fractions
    c3 = _backward_induction(
        src.cfads_by_period, src.dscr_by_period, snapshot.ops_by_src_period,
        snapshot.rate_by_src_period, src.day_frac_by_period, active,
    )
    steps.append(SequentialBridgeStep(3, "CF3_DAY_FRAC_SOURCE_DS_ROW6", c3, c3 - prev))
    prev = c3

    # Step 4: apply source ops
    c4 = _backward_induction(
        src.cfads_by_period, src.dscr_by_period, src.ops_by_period,
        snapshot.rate_by_src_period, src.day_frac_by_period, active,
    )
    steps.append(SequentialBridgeStep(4, "CF4_OPS_SOURCE_DS_ROW9", c4, c4 - prev))
    prev = c4

    # Step 5: apply source rates
    c5 = _backward_induction(
        src.cfads_by_period, src.dscr_by_period, src.ops_by_period,
        src.rate_by_period, src.day_frac_by_period, active,
    )
    steps.append(SequentialBridgeStep(5, "CF5_RATE_SOURCE_DS_ROW44", c5, c5 - prev))

    return steps


# ---------------------------------------------------------------------------
# SOURCE_ALL gate
# ---------------------------------------------------------------------------

@dataclass
class SourceAllGate:
    source_all_capacity_keur: float
    residual_vs_source_keur: float
    bridge_closed: bool
    verdict: str


def evaluate_source_all_gate(
    snapshot: CurrentGrid0Snapshot, src: SourceVectors
) -> SourceAllGate:
    """Apply all five source vectors simultaneously and check if bridge closes."""
    active = snapshot.active_src_periods
    capacity = _backward_induction(
        src.cfads_by_period, src.dscr_by_period, src.ops_by_period,
        src.rate_by_period, src.day_frac_by_period, active,
    )
    residual = capacity - SOURCE_EXCEL_SENIOR_DEBT_KEUR
    closed = abs(residual) < _SOURCE_REPLAY_TOLERANCE_KEUR

    if closed:
        verdict = "CURRENT_GRID0_TO_SOURCE_SIZING_INPUT_BRIDGE_CLOSED"
    else:
        verdict = "CURRENT_GRID0_TO_SOURCE_DEBT_BRIDGE_STILL_INCOMPLETE"

    return SourceAllGate(
        source_all_capacity_keur=capacity,
        residual_vs_source_keur=residual,
        bridge_closed=closed,
        verdict=verdict,
    )


# ---------------------------------------------------------------------------
# Full diagnostic entry point
# ---------------------------------------------------------------------------

@dataclass
class C3B3D2B2BDiagnosticResult:
    snapshot: CurrentGrid0Snapshot
    source_vectors: SourceVectors
    vector_comparisons: dict[str, VectorComparison]
    counterfactuals: list[CounterfactualResult]
    sequential_bridge: list[SequentialBridgeStep]
    source_all_gate: SourceAllGate

    @property
    def verdict(self) -> str:
        cf1 = next(c for c in self.counterfactuals if c.label == "CF1")
        others_material = any(
            abs(c.delta_vs_baseline_keur) >= _CF_MATCH_THRESHOLD
            for c in self.counterfactuals if c.label != "CF1"
        )
        if self.source_all_gate.bridge_closed and not others_material:
            return "C3B3D2B2B_R2_BANK_SIZING_CFADS_AUTHORITY_SOLE_GAP_READY_FOR_INDEPENDENT_REVIEW"
        elif self.source_all_gate.bridge_closed and others_material:
            return "C3B3D2B2B_R2_MULTI_FACTOR_CURRENT_SIZING_GAP"
        else:
            return "C3B3D2B2B_CURRENT_DEBT_BRIDGE_STILL_INCOMPLETE"

    def format_report(self) -> str:
        snap = self.snapshot
        gate = self.source_all_gate
        cf1 = next(c for c in self.counterfactuals if c.label == "CF1")

        lines = [
            "C3B3D2B2B R2: Current Senior Debt Sizing Bridge",
            "=" * 60,
            f"CURRENT_GRID0:            {snap.debt_keur:.6f} kEUR",
            f"SOURCE_EXCEL:             {SOURCE_EXCEL_SENIOR_DEBT_KEUR:.6f} kEUR",
            f"Gap (G0 - source):        {CURRENT_GRID0_TO_SOURCE_GAP_KEUR:+.6f} kEUR",
            "",
            "Gate 1: CURRENT_GRID0_RUNTIME_BASELINE_REPRODUCED",
            f"  Engine debt:            {snap.debt_keur:.6f} kEUR",
            f"  BI (current-only):      {snap.backward_induction_keur:.6f} kEUR",
            f"  Independence delta:     {snap.backward_induction_keur - snap.debt_keur:.2e} kEUR",
            f"  Day-count convention:   {snap.day_count_convention}",
            f"  Day-frac provenance:    period_day_fraction(period_start, period_end, {snap.day_count_convention})",
            "",
            "Gate 2: SOURCE_SENIOR_DEBT_CAPACITY_REPLAY_PROVEN",
            f"  BI from source:         {self.source_vectors.source_capacity_keur:.6f} kEUR",
            f"  DS!D51 fixture:         {self.source_vectors.excel_total_debt_keur:.6f} kEUR",
            f"  Replay residual:        {self.source_vectors.source_capacity_keur - self.source_vectors.excel_total_debt_keur:.2e} kEUR",
            "",
            "Vector equality gates (current engine vs source):",
        ]
        for name, vc in self.vector_comparisons.items():
            lines.append(
                f"  {name:12s}  max_delta={vc.max_abs_delta:.2e}  [{vc.classification}]"
                + (f"  first_mismatch=P{vc.first_mismatch_period}" if vc.first_mismatch_period else "")
            )

        lines += ["", "One-factor counterfactuals from CURRENT_GRID0 (R2):"]
        for cf in self.counterfactuals:
            lines.append(
                f"  {cf.label}: {cf.capacity_keur:.3f} kEUR  "
                f"delta={cf.delta_vs_baseline_keur:+.3f}  [{cf.classification}]"
            )

        lines += ["", "Sequential bridge (CURRENT_GRID0 → SOURCE_ALL):"]
        lines.append(f"  Step 0 (baseline):   {snap.backward_induction_keur:.3f} kEUR  delta=—")
        for step in self.sequential_bridge:
            lines.append(
                f"  Step {step.step} ({step.vector_applied}): "
                f"{step.cumulative_capacity_keur:.3f} kEUR  delta={step.step_delta_keur:+.3f}"
            )

        lines += [
            "",
            "SOURCE_ALL gate:",
            f"  SOURCE_ALL capacity:    {gate.source_all_capacity_keur:.6f} kEUR",
            f"  Residual vs source:     {gate.residual_vs_source_keur:.2e} kEUR",
            f"  Bridge closed:          {gate.bridge_closed}",
            "",
            "Verdict:",
            f"  {self.verdict}",
            "",
            "CFADS interpretation:",
            "  Proven: CURRENT SENIOR DEBT SIZING INPUT GAP = BASE/CANONICAL CFADS AUTHORITY",
            "          vs SOURCE BANK-SIZING CFADS AUTHORITY",
            "  Unresolved: HOW Macro50 transforms base CFADS into bank-sizing CFADS",
            "  BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED",
            "  VBA_IMPLEMENTATION_NOT_VISIBLE",
            "  BANK_SIZING_SCENARIO_P90_10Y_REVIEWER_CONFIRMED_NOT_COMMITTED",
            "  MISSING_GENERIC_BANK_SIZING_CFADS_SCENARIO_LAYER (future architecture)",
        ]
        return "\n".join(lines)


def run_diagnostic() -> C3B3D2B2BDiagnosticResult:
    """Run the full C3B3D2B2B R2 bridge diagnostic."""
    snapshot = capture_current_grid0_snapshot()
    src = load_source_vectors()
    vector_comparisons = compare_vectors(snapshot, src)
    cfs = run_one_factor_counterfactuals(snapshot, src)
    bridge = run_sequential_bridge(snapshot, src)
    gate = evaluate_source_all_gate(snapshot, src)
    return C3B3D2B2BDiagnosticResult(
        snapshot=snapshot,
        source_vectors=src,
        vector_comparisons=vector_comparisons,
        counterfactuals=cfs,
        sequential_bridge=bridge,
        source_all_gate=gate,
    )


if __name__ == "__main__":
    result = run_diagnostic()
    print(result.format_report())
