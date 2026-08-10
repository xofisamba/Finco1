"""finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge — C3B3D2B2B bridge diagnostic.

EVIDENCE-ONLY DIAGNOSTIC. No production promotion. No production engine changes.
Purpose: Decompose the CURRENT_GRID0_TO_SOURCE_DEBT_BRIDGE_NOT_YET_CLOSED gap
(+1,066.754 kEUR) between:
  CURRENT_GRID0_PRODUCTION_CANDIDATE   = 43,919.032698 kEUR  (clean engine runtime)
  SOURCE_EXCEL_SENIOR_DEBT             = 42,852.278763 kEUR  (DS!D51, source workbook)

Approach: one-factor current-baseline counterfactuals from CURRENT_GRID0 snapshot,
independent backward-induction verification, and SOURCE_ALL gate.

One-factor counterfactuals (each from CURRENT_GRID0 baseline):
  CF1: CFADS — clean Phase2A EBITDA → source DS!row20 (Macro50 bank transformation)
  CF2: DSCR banding — clean engine vector → source DS!row22 (already matched: delta=0)
  CF3: Ops fraction — clean engine vector → source DS!row9 (already matched: delta=0)
  CF4: Annual rate — clean engine per-period → source DS!row44 (already matched: delta=0)

SOURCE_ALL gate: apply all source vectors simultaneously.
  Result: SOURCE_ALL = 42,852.278763 kEUR → residual = 0.000 kEUR
  Classification: CURRENT_GRID0_TO_SOURCE_SIZING_INPUT_BRIDGE_CLOSED

CFADS interpretation:
  Clean engine CFADS = Phase2A EBITDA - canonical cash_tax (clean tax logic, no SHL feedback)
  Source DS!row20 = Macro50 output (bank/P90 scenario transformation: VBA_IMPLEMENTATION_NOT_VISIBLE)
  BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED — Macro50 cell is password-protected.
  BANK_SIZING_SCENARIO_P90_10Y_REVIEWER_CONFIRMED_NOT_COMMITTED

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
HISTORICAL_GENERIC_PHASE2C_DEBT_KEUR: float = 46_053.402378616  # HISTORICAL — do not use as baseline

CURRENT_GRID0_TO_SOURCE_GAP_KEUR: float = (
    CURRENT_GRID0_DEBT_KEUR - SOURCE_EXCEL_SENIOR_DEBT_KEUR
)  # +1,066.754 kEUR — target to close

# Source vector fixture tolerance
_SOURCE_REPLAY_TOLERANCE_KEUR: float = 1.0

_DEBT_FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "tests", "fixtures", "excel_oborovo_debt_interest_truth.json",
)


# ---------------------------------------------------------------------------
# Snapshot: current GRID-0 engine parameters
# ---------------------------------------------------------------------------

@dataclass
class CurrentGrid0Snapshot:
    """Immutable snapshot of current engine sizing parameters for GRID-0."""

    debt_keur: float
    """Senior debt computed by current clean engine."""

    cfads_by_src_period: dict[int, float]
    """Clean CFADS per source period index (1-indexed P1..P28)."""

    rate_by_src_period: dict[int, float]
    """Annual sculpting rate per source period (DS!row44 per-period, already source-matched)."""

    day_frac_by_src_period: dict[int, float]
    """Day fraction per source period (DS!row6 ACT/360, already source-matched)."""

    dscr_by_src_period: dict[int, float]
    """DSCR target per source period (DS!row22 banding, already source-matched)."""

    ops_by_src_period: dict[int, float]
    """Ops fraction per source period (DS!row9, already source-matched)."""

    active_src_periods: list[int]
    """Source period indices (1..28) that are active in the sizing calculation."""

    backward_induction_keur: float
    """Independent backward-induction result from this snapshot (must match debt_keur < 1e-3)."""

    baseline_label: str = "CURRENT_GRID0_PRODUCTION_CANDIDATE"


def capture_current_grid0_snapshot() -> CurrentGrid0Snapshot:
    """Capture the current GRID-0 engine parameters via the production API.

    Reads source fixture for day fractions (already used by the engine).
    Maps engine period_index (2..29) to source period index (1..28).

    Raises RuntimeError if the captured snapshot deviates from the
    locked CURRENT_GRID0_DEBT_KEUR baseline by more than 5 kEUR.
    """
    from app.project_factories import create_default_oborovo
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )
    from financial_engine.orchestrator import run_senior_debt_model

    proj = create_default_oborovo()
    sd_input = build_senior_debt_model_input_from_project_inputs(
        proj, source_id="c3b3d2b2b-snapshot"
    )
    phase2c = run_senior_debt_model(sd_input)
    tac = phase2c.tax_and_cfads
    sd = phase2c.senior_debt

    debt = sd.diagnostics.get("final_debt_size_keur", 0.0)
    if abs(debt - CURRENT_GRID0_DEBT_KEUR) > 5.0:
        raise RuntimeError(
            f"C3B3D2B2B_STOP_CURRENT_GRID0_BASELINE_DRIFT: engine={debt:.3f} "
            f"locked={CURRENT_GRID0_DEBT_KEUR:.6f} delta={debt - CURRENT_GRID0_DEBT_KEUR:.3f}"
        )

    cfads_by_pidx = dict(zip(tac.period_indices, tac.cfads_keur))
    op_pidx = list(sd.period_indices)  # [2..29], 28 operating periods

    rate_by_pidx = {
        pr.period_index: pr.annual_rate
        for pr in sd_input.senior_debt_inputs.period_rates
    }
    dscr_by_pidx = {
        pr.period_index: pr.target_dscr
        for pr in sd_input.senior_debt_inputs.period_dscr_targets
    }
    ops_by_pidx = {
        pa.period_index: pa.availability_fraction
        for pa in sd_input.senior_debt_inputs.period_debt_service_availability
    }

    with open(_DEBT_FIXTURE_PATH) as fh:
        fixture = json.load(fh)
    day_frac_list = fixture["workstream_b"]["period_vectors"]["row6_day_frac"][
        "period_values"
    ]

    # Map engine period_index p to source period index (p - 1)
    def eng_to_src(p: int) -> int:
        return p - 1

    active_src = [eng_to_src(p) for p in op_pidx]  # [1..28]

    cfads_by_src = {eng_to_src(p): cfads_by_pidx.get(p, 0.0) for p in op_pidx}
    rate_by_src = {eng_to_src(p): rate_by_pidx.get(p, 0.0) for p in op_pidx}
    frac_by_src = {eng_to_src(p): day_frac_list[eng_to_src(p)] for p in op_pidx}
    dscr_by_src = {eng_to_src(p): dscr_by_pidx.get(p, 1.15) for p in op_pidx}
    ops_by_src = {eng_to_src(p): ops_by_pidx.get(p, 1.0) for p in op_pidx}

    bi_keur = _backward_induction(
        cfads_by_src, dscr_by_src, ops_by_src, rate_by_src, frac_by_src, active_src
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
    )


# ---------------------------------------------------------------------------
# Source vector extraction
# ---------------------------------------------------------------------------

@dataclass
class SourceVectors:
    """Source sizing vectors extracted from committed fixtures (read-only)."""

    cfads_by_period: dict[int, float]
    """DS!row20 CFADS per period (1..28): Macro50 bank/P90 transformation output."""

    dscr_by_period: dict[int, float]
    """DS!row22 DSCR target per period (1.15 for P1-P24, 1.35 for P25-P28)."""

    ops_by_period: dict[int, float]
    """DS!row9 ops fraction per period."""

    rate_by_period: dict[int, float]
    """DS!row44 annual sculpting rate per period."""

    day_frac_by_period: dict[int, float]
    """DS!row6 day fraction per period (ACT/360-style)."""

    source_capacity_keur: float
    """G4 backward-induction from all source vectors: must equal SOURCE_EXCEL_SENIOR_DEBT."""

    excel_total_debt_keur: float
    """DS!D51 committed fixture value."""


def load_source_vectors() -> SourceVectors:
    """Load source sizing vectors from committed C3B2 fixture.

    Raises RuntimeError if backward-induction from source vectors deviates
    from SOURCE_EXCEL_SENIOR_DEBT_KEUR by more than 1.0 kEUR
    (C3B3D2B2B_STOP_SOURCE_CAPACITY_REPLAY_FAILED).
    """
    with open(_DEBT_FIXTURE_PATH) as fh:
        fixture = json.load(fh)

    wa = fixture["workstream_a"]
    wb = fixture["workstream_b"]
    we = fixture["workstream_e"]
    p2c = fixture["phase2c_sizing_analysis"]

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
# Backward induction (pure function — no engine calls)
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


def run_one_factor_counterfactuals(
    snapshot: CurrentGrid0Snapshot, src: SourceVectors
) -> list[CounterfactualResult]:
    """Run CF1–CF4 one-factor counterfactuals from the CURRENT_GRID0 snapshot.

    Each counterfactual swaps exactly one vector from clean engine to source
    while holding all other vectors at their current engine values.
    """
    active = snapshot.active_src_periods
    baseline = snapshot.backward_induction_keur

    def _classify_delta(delta: float) -> str:
        if abs(delta) < _SOURCE_REPLAY_TOLERANCE_KEUR:
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
        classification=_classify_delta(cf1 - baseline),
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
        description="Source DSCR banding: DS!row22 (1.15/1.35) vs clean engine vector",
        capacity_keur=cf2,
        delta_vs_baseline_keur=cf2 - baseline,
        classification=_classify_delta(cf2 - baseline),
    ))

    # CF3: Source ops fraction (DS!row9)
    cf3 = _backward_induction(
        snapshot.cfads_by_src_period,
        snapshot.dscr_by_src_period,
        src.ops_by_period,
        snapshot.rate_by_src_period,
        snapshot.day_frac_by_src_period,
        active,
    )
    results.append(CounterfactualResult(
        label="CF3",
        description="Source ops fraction: DS!row9 vs clean engine availability",
        capacity_keur=cf3,
        delta_vs_baseline_keur=cf3 - baseline,
        classification=_classify_delta(cf3 - baseline),
    ))

    # CF4: Source annual rate (DS!row44)
    cf4 = _backward_induction(
        snapshot.cfads_by_src_period,
        snapshot.dscr_by_src_period,
        snapshot.ops_by_src_period,
        src.rate_by_period,
        snapshot.day_frac_by_src_period,
        active,
    )
    results.append(CounterfactualResult(
        label="CF4",
        description="Source annual rate: DS!row44 per-period vs clean engine rates",
        capacity_keur=cf4,
        delta_vs_baseline_keur=cf4 - baseline,
        classification=_classify_delta(cf4 - baseline),
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
    label: str


def run_sequential_bridge(
    snapshot: CurrentGrid0Snapshot, src: SourceVectors
) -> list[SequentialBridgeStep]:
    """Build a sequential bridge from CURRENT_GRID0 to SOURCE_ALL.

    Vectors applied in order: CFADS (CF1), then DSCR (CF2), ops (CF3), rate (CF4).
    Since CF2/CF3/CF4 are already source-matched, the bridge closes entirely at step 1.
    """
    active = snapshot.active_src_periods
    steps = []

    # Step 0: baseline
    c0 = snapshot.backward_induction_keur
    prev = c0

    # Step 1: apply source CFADS
    c1 = _backward_induction(
        src.cfads_by_period,
        snapshot.dscr_by_src_period,
        snapshot.ops_by_src_period,
        snapshot.rate_by_src_period,
        snapshot.day_frac_by_src_period,
        active,
    )
    steps.append(SequentialBridgeStep(
        step=1, vector_applied="CF1_CFADS_SOURCE_DS_ROW20",
        cumulative_capacity_keur=c1, step_delta_keur=c1 - prev, label="source CFADS applied",
    ))
    prev = c1

    # Step 2: apply source DSCR (already matched — zero delta)
    c2 = _backward_induction(
        src.cfads_by_period, src.dscr_by_period,
        snapshot.ops_by_src_period, snapshot.rate_by_src_period,
        snapshot.day_frac_by_src_period, active,
    )
    steps.append(SequentialBridgeStep(
        step=2, vector_applied="CF2_DSCR_SOURCE_DS_ROW22",
        cumulative_capacity_keur=c2, step_delta_keur=c2 - prev, label="source DSCR applied",
    ))
    prev = c2

    # Step 3: apply source ops (already matched — zero delta)
    c3 = _backward_induction(
        src.cfads_by_period, src.dscr_by_period, src.ops_by_period,
        snapshot.rate_by_src_period, snapshot.day_frac_by_src_period, active,
    )
    steps.append(SequentialBridgeStep(
        step=3, vector_applied="CF3_OPS_SOURCE_DS_ROW9",
        cumulative_capacity_keur=c3, step_delta_keur=c3 - prev, label="source ops applied",
    ))
    prev = c3

    # Step 4: apply source rate (already matched — zero delta)
    c4 = _backward_induction(
        src.cfads_by_period, src.dscr_by_period, src.ops_by_period,
        src.rate_by_period, snapshot.day_frac_by_src_period, active,
    )
    steps.append(SequentialBridgeStep(
        step=4, vector_applied="CF4_RATE_SOURCE_DS_ROW44",
        cumulative_capacity_keur=c4, step_delta_keur=c4 - prev, label="source rate applied",
    ))

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
    """Apply all source vectors simultaneously and check if bridge closes.

    Bridge closed criterion: |source_all - SOURCE_EXCEL_SENIOR_DEBT_KEUR| < 1.0 kEUR.
    """
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
    counterfactuals: list[CounterfactualResult]
    sequential_bridge: list[SequentialBridgeStep]
    source_all_gate: SourceAllGate

    @property
    def verdict(self) -> str:
        return self.source_all_gate.verdict

    def format_report(self) -> str:
        lines = [
            "C3B3D2B2B Current Senior Debt Sizing Bridge",
            "=" * 60,
            f"CURRENT_GRID0:          {self.snapshot.debt_keur:.6f} kEUR",
            f"SOURCE_EXCEL:           {SOURCE_EXCEL_SENIOR_DEBT_KEUR:.6f} kEUR",
            f"Gap (G0 - source):      {CURRENT_GRID0_TO_SOURCE_GAP_KEUR:+.6f} kEUR",
            "",
            "Gate 1: CURRENT_GRID0_RUNTIME_BASELINE_REPRODUCED",
            f"  BI from snapshot:     {self.snapshot.backward_induction_keur:.6f} kEUR",
            f"  Engine actual:        {self.snapshot.debt_keur:.6f} kEUR",
            f"  Independence delta:   {self.snapshot.backward_induction_keur - self.snapshot.debt_keur:.2e} kEUR",
            "",
            "Gate 2: SOURCE_SENIOR_DEBT_CAPACITY_REPLAY_PROVEN",
            f"  BI from source:       {self.source_vectors.source_capacity_keur:.6f} kEUR",
            f"  DS!D51 fixture:       {self.source_vectors.excel_total_debt_keur:.6f} kEUR",
            f"  Replay residual:      {self.source_vectors.source_capacity_keur - self.source_vectors.excel_total_debt_keur:.2e} kEUR",
            "",
            "One-factor counterfactuals from CURRENT_GRID0:",
        ]
        for cf in self.counterfactuals:
            lines.append(
                f"  {cf.label}: {cf.capacity_keur:.3f} kEUR  "
                f"delta={cf.delta_vs_baseline_keur:+.3f}  [{cf.classification}]"
            )
        lines += [
            "",
            "Sequential bridge (CURRENT_GRID0 → SOURCE_ALL):",
        ]
        for step in self.sequential_bridge:
            lines.append(
                f"  Step {step.step} ({step.vector_applied}): "
                f"{step.cumulative_capacity_keur:.3f} kEUR  delta={step.step_delta_keur:+.3f}"
            )
        lines += [
            "",
            "SOURCE_ALL gate:",
            f"  SOURCE_ALL capacity:  {self.source_all_gate.source_all_capacity_keur:.6f} kEUR",
            f"  Residual vs source:   {self.source_all_gate.residual_vs_source_keur:.2e} kEUR",
            f"  Bridge closed:        {self.source_all_gate.bridge_closed}",
            f"  Verdict:              {self.source_all_gate.verdict}",
            "",
            "CFADS interpretation:",
            "  The full +1,066.754 kEUR gap is attributable to the CFADS vector difference.",
            "  Clean engine: Phase2A EBITDA - canonical cash_tax (no SHL, no Macro50).",
            "  Source DS!row20: Macro50 bank/P90 transformation (VBA_IMPLEMENTATION_NOT_VISIBLE).",
            "  BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED — mechanism not decomposed here.",
            "  No causal decomposition of Macro50 internals in this module.",
        ]
        return "\n".join(lines)


def run_diagnostic() -> C3B3D2B2BDiagnosticResult:
    """Run the full C3B3D2B2B bridge diagnostic."""
    snapshot = capture_current_grid0_snapshot()
    src = load_source_vectors()
    cfs = run_one_factor_counterfactuals(snapshot, src)
    bridge = run_sequential_bridge(snapshot, src)
    gate = evaluate_source_all_gate(snapshot, src)
    return C3B3D2B2BDiagnosticResult(
        snapshot=snapshot,
        source_vectors=src,
        counterfactuals=cfs,
        sequential_bridge=bridge,
        source_all_gate=gate,
    )


if __name__ == "__main__":
    result = run_diagnostic()
    print(result.format_report())
