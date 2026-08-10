"""finco_recon.diagnose_c3b3d2b2a_tax_shl_causal_grid — C3B3D2B2A causal diagnostic grid.

EVIDENCE-ONLY DIAGNOSTIC. No production promotion.
Purpose: causally explain the CURRENT_UPSTREAM_CLEAN_CASH_RESIDUAL identified in D2B1.

Baseline (GRID-0): clean DS[40] SHL closing ≈ 2718.02 kEUR vs source 0.00 kEUR.

Known candidate contributors tested here:
  GRID-S0  Canonical callback SURROGATE (verifies GRID-S0 ≡ GRID-0 within solver tolerance)
  GRID-WS0 Workbook callback all-False SURROGATE (baseline for B/C/D/E relative claims)
  GRID-A   SHL interest feedback (SHL→tax→CFADS→SD→SHL)
  GRID-B   Workbook H2+H1 model-year CIT pairing (row 43 formula)
  GRID-C   Workbook EBT gate for loss utilisation (row 37 formula)
  GRID-D   Workbook rolling 5-period loss window (row 36 formula)
  GRID-E   Workbook row-39 carriable-loss cap (row 39 formula)
  GRID-BC, GRID-BD, GRID-CD, GRID-BCD, GRID-ABCD, GRID-ABCDE (combinations)

Source evidence for workbook mechanics:
  Row 43: SOURCE_PROVEN (WORKBOOK_COMPATIBILITY_PROFILE)
    CIT = MAX(SUM(F41:G41),0) × B43 × (G4>0) × (MOD(G4,2)=0)
    → fires only in EVEN model periods; pairs current H1/H2 with prior H2/H1.
  Row 37: SOURCE_PROVEN (WORKBOOK_COMPATIBILITY_PROFILE)
    allocated_losses = IF(AND(G36<=0, G32>0), MIN(ABS(G36), G32), 0)
    → G32 = EBT (not TI). Gate prevents utilisation when EBT <= 0.
  Row 36: SOURCE_PROVEN (WORKBOOK_COMPATIBILITY_PROFILE)
    losses_n_minus_1 = SUMIF(last-B36-periods TI, "<0") + cumulative_used; B36=5
    → Rolling 5 MODEL PERIODS (≈2.5 calendar years), NOT 5 calendar-year vintages.
  Row 39: SOURCE_PROVEN (WORKBOOK_COMPATIBILITY_PROFILE) — REPORTING/REPLAY ONLY
    carriable_losses = MIN(losses_n, prior_period_TI × B37); B37=1
    ROW39_REPORTING_OR_NON_CAUSAL_FOR_TAX_STATE_SOURCE_PROVEN:
    Row 39 does not feed the forward tax state (rows 36/37/38/41/43).
    Retained in config for source-replay validation only; not a causal mechanic.

Cause status: CURRENT_CAUSE_UNRESOLVED — no arm has yet proven a common valid baseline.

Governance constants:
  SHL draw: 14,620.773894815633 kEUR (D2A fixture, Inputs!D325) — authoritative
  SHL rate: 0.08 (Inputs!F328)
  SHL DCF: 1.0 arithmetic-implied (CONSTRUCTION_DATE_CONVENTION_UNRESOLVED)
  13,547.2 MUST NOT appear in any clean SHL calculation.
  Protected C3B2 SHA: f8f244c0660495bfb4115d4e32ba329c291ab829d1d0693e614c889457b5add7

No project-name dispatch. No DS25/DS40 hardcoding. No calibration plugs.
No production-engine modifications. No source fixture vectors in production paths.
DSRA_ORDERING_UNRESOLVED. CONSTRUCTION_DATE_CONVENTION_UNRESOLVED.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from datetime import date
from typing import Callable

# ---------------------------------------------------------------------------
# Governance constants — authoritative source values (D2A fixture)
# ---------------------------------------------------------------------------

SHL_DRAW_KEUR: float = 14_620.773894815633      # Inputs!D325 SOURCE_RAW_CACHED_VALUE
SHL_ANNUAL_RATE: float = 0.08                   # Inputs!F328 SOURCE_RAW_CACHED_VALUE
SHL_CONSTRUCTION_PIK_KEUR: float = 1_169.6619115852516   # D2A proved
SHL_FIRST_OP_OPENING_KEUR: float = 15_790.435806400885   # D2A proved
SOURCE_DEBT_SIZE_KEUR: float = 42_852.27876256299         # DS!D(192) source truth
WORKBOOK_CIT_RATE: float = 0.10                 # P&L B43 SOURCE_RAW_CACHED_VALUE (Oborovo CIT = 10%)
WORKBOOK_ROLLING_WINDOW: int = 5                # P&L B36=5 (model periods)
SOURCE_FINAL_SHL_CLOSING_KEUR: float = 0.0     # DS[40] source closing (all repaid)
D2B1_GRID0_FINAL_CLOSING_KEUR: float = 2718.02  # D2B1 production-candidate diagnostic

# Three baseline authorities — must not be conflated:
CURRENT_GRID0_DEBT_KEUR: float = 43_919.032698           # CURRENT_GRID0_PRODUCTION_CANDIDATE
HISTORICAL_GENERIC_PHASE2C_DEBT_KEUR: float = 46_053.402378616  # HISTORICAL_GENERIC_PHASE2C_SCALAR_DIAGNOSTIC
SOURCE_EXCEL_SENIOR_DEBT_KEUR: float = SOURCE_DEBT_SIZE_KEUR    # SOURCE_EXCEL_SENIOR_DEBT = 42,852.279 kEUR

_CF_FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "tests", "fixtures", "excel_oborovo_financial_truth.json",
)

_FIXTURE_PATH = _CF_FIXTURE_PATH  # alias for backward-compat internal usage


# ---------------------------------------------------------------------------
# D2B1-exact source comparators (DS[1..40] horizon)
# ---------------------------------------------------------------------------

def _source_cfads_ds1_40(cf: dict) -> list[float]:
    """D2B1 contract: cf['fcf_for_banks_keur'][1:41], DS[1..40]."""
    return list(cf["cf"]["fcf_for_banks_keur"][1:41])


def _source_senior_ds_ds1_40(cf: dict) -> list[float]:
    """D2B1 contract: -cf['senior_debt_service_keur'][1:41], sign-normalized positive."""
    return [-x for x in cf["cf"]["senior_debt_service_keur"][1:41]]


def _source_candidate_shl_cash_ds1_40(cf: dict) -> list[float]:
    """D2B1 contract: cf['free_cash_flow_for_shl_keur'][1:41], DS[1..40]."""
    return list(cf["cf"]["free_cash_flow_for_shl_keur"][1:41])


# ---------------------------------------------------------------------------
# Workbook mechanic configuration flags
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkbookTaxConfig:
    """Configuration flags for workbook-compatible tax mechanics.

    Classification: WORKBOOK_COMPATIBILITY_PROFILE for all True flags.
    When all flags are False, mechanics approximate the CANONICAL_TAX_LOGIC.

    h2h1_pairing:
        SOURCE_PROVEN (row 43). CIT fires in EVEN model periods only.
        CIT[P] = rate x max(0, TP[P-1] + TP[P]) where P even.
        Workbook model period number = period_index (construction=0, op1=1,...).

    ebt_gate:
        SOURCE_PROVEN (row 37). Losses utilised ONLY when EBT > 0.
        For Oborovo: EBT stays negative throughout loss period (SHL interest
        dominates). Effect: zero loss utilisation -> losses expire on window.

    rolling_window:
        SOURCE_PROVEN (row 36). Available losses = SUMIF of last
        WORKBOOK_ROLLING_WINDOW model periods' TI < 0.
        Not 5 calendar-year vintages (FIFO); not 5 calendar years.

    row39_cap:
        SOURCE_PROVEN (row 39) — ROW39_REPORTING_OR_NON_CAUSAL_FOR_TAX_STATE_SOURCE_PROVEN.
        Carriable = MIN(closing_loss, prior_TI). Row 39 does NOT feed forward tax
        state. Flag retained for source-replay fixture validation only.
        GRID-E arm: WITHIN_TAX_SURROGATE_ONLY — not a causal tax-state mechanic.
    """
    h2h1_pairing: bool = False
    ebt_gate: bool = False
    rolling_window: bool = False
    row39_cap: bool = False
    shl_netting_in_tax: bool = False


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GridArmResult:
    """Deterministic result for one diagnostic grid arm.

    All delta fields are (clean_arm - source) unless noted.
    Positive delta = clean arm is HIGHER than source.
    """
    arm_id: str                          # e.g. "GRID-0", "GRID-B"
    arm_label: str                       # human-readable description
    source_evidence: str                 # SOURCE_PROVEN / SOURCE_INFERRED / HYPOTHESIS
    config: WorkbookTaxConfig
    surrogate_baseline: str              # which baseline used ('GRID-0', 'GRID-WS0', etc.)

    # Tax
    total_cash_tax_keur: float           # sum of positive outflows (absolute)
    source_total_cash_tax_keur: float    # 10,443.088 kEUR source lifetime
    total_tax_delta_vs_source: float     # signed: arm - source
    max_period_tax_delta_vs_source: float  # max |arm[p] - source[p]| over operating periods

    # CFADS
    total_cfads_keur: float
    source_total_cfads_keur: float
    max_cfads_delta_vs_source: float     # max |arm[p] - source[p]|
    signed_total_cfads_delta: float      # sum(arm[p] - source[p])

    # Senior Debt
    clean_debt_size_keur: float
    debt_size_delta_keur: float          # arm - source (42,852.279)
    max_senior_ds_delta_vs_source: float
    signed_total_senior_ds_delta: float

    # Candidate SHL cash
    max_shl_cash_delta_vs_source: float
    signed_total_shl_cash_delta: float

    # SHL schedule
    gross_interest_max_delta: float
    cash_interest_max_delta: float
    pik_max_delta: float
    principal_max_delta: float
    closing_max_delta: float
    ds40_final_closing_keur: float       # clean arm DS[40] closing balance

    # vs GRID-0
    delta_vs_grid0_final_closing: float  # ds40_final_closing - GRID-0 closing

    # GRID-A convergence
    convergence_iterations: int          # 0 = not applicable
    convergence_achieved: bool
    convergence_note: str

    # Solver
    solver_converged: bool
    solver_iterations: int


@dataclass
class DiagnosticGridResult:
    """Full C3B3D2B2A diagnostic grid result."""
    grid0: GridArmResult
    grid_s0: GridArmResult
    grid_ws0: GridArmResult
    grid_a: GridArmResult
    grid_b: GridArmResult
    grid_c: GridArmResult
    grid_d: GridArmResult
    grid_e: GridArmResult
    grid_bc: GridArmResult
    grid_bd: GridArmResult
    grid_cd: GridArmResult
    grid_bcd: GridArmResult
    grid_abcd: GridArmResult
    grid_abcde: GridArmResult

    def all_arms(self) -> list[GridArmResult]:
        return [
            self.grid0, self.grid_s0, self.grid_ws0, self.grid_a,
            self.grid_b, self.grid_c, self.grid_d, self.grid_e,
            self.grid_bc, self.grid_bd, self.grid_cd, self.grid_bcd,
            self.grid_abcd, self.grid_abcde,
        ]


# ---------------------------------------------------------------------------
# Source fixture loading
# ---------------------------------------------------------------------------

def _load_source_fixture() -> dict:
    with open(_CF_FIXTURE_PATH) as f:
        return json.load(f)


def _source_cash_tax_by_period(fixture: dict) -> dict[int, float]:
    """Source CIT vector (positive outflow) for DS[1..40] periods."""
    vals = fixture["tax"]["cf_tax_chain"]["cf_cash_tax_period_values"]
    return {i: abs(v) for i, v in enumerate(vals)}


# Backward-compat aliases (D2B1-exact names)
def _source_cfads_by_period(fixture: dict) -> dict[int, float]:
    return _source_cfads_by_period_d2b1(fixture)


def _source_senior_ds_by_period(fixture: dict) -> dict[int, float]:
    return _source_senior_ds_by_period_d2b1(fixture)


def _source_shl_cash_by_period(fixture: dict) -> dict[int, float]:
    return _source_shl_cash_by_period_d2b1(fixture)


def _source_cfads_by_period_d2b1(fixture: dict) -> dict[int, float]:
    """Source CFADS vector using D2B1 exact contract: fcf_for_banks_keur[1:41].

    source_fcf_for_banks_keur = D2B1 source CFADS = cf["fcf_for_banks_keur"]
    clean_cfads_keur = seam.cfads_keur = EBITDA - canonical cash_tax
    Both are directly comparable (both = EBITDA - cash_tax).
    """
    vals = _source_cfads_ds1_40(fixture)
    return {i + 1: v for i, v in enumerate(vals)}


def _source_senior_ds_by_period_d2b1(fixture: dict) -> dict[int, float]:
    """Source senior DS using D2B1 exact contract: -senior_debt_service_keur[1:41]."""
    vals = _source_senior_ds_ds1_40(fixture)
    return {i + 1: v for i, v in enumerate(vals)}


def _source_shl_cash_by_period_d2b1(fixture: dict) -> dict[int, float]:
    """Source FCF-for-SHL using D2B1 exact contract: free_cash_flow_for_shl_keur[1:41]."""
    vals = _source_candidate_shl_cash_ds1_40(fixture)
    return {i + 1: v for i, v in enumerate(vals)}


def _aligned_source_dicts(
    clean_op_indices: list[int],
    source_fixture: dict,
) -> tuple[dict[int, float], dict[int, float], dict[int, float]]:
    """Build position-aligned source comparison dicts for CFADS, senior DS, and CIT.

    Maps k-th source DS[1..40] value to k-th clean operating period_index.
    Required because the clean Oborovo model has 2 construction periods
    (period_index 0 and 1) while the source fixture has 1, causing the
    first clean operating period to be at period_index 2, not 1.

    Returns (cfads_src, sd_src, cit_src) keyed by clean period_index.
    """
    cfads_vals = _source_cfads_ds1_40(source_fixture)
    sd_vals = _source_senior_ds_ds1_40(source_fixture)
    raw_cit = source_fixture["tax"]["cf_tax_chain"]["cf_cash_tax_period_values"]
    cit_vals = [abs(v) for v in raw_cit[1:41]]

    n = min(40, len(clean_op_indices))
    cfads_src = {clean_op_indices[k]: cfads_vals[k] for k in range(min(n, len(cfads_vals)))}
    sd_src = {clean_op_indices[k]: sd_vals[k] for k in range(min(n, len(sd_vals)))}
    cit_src = {clean_op_indices[k]: cit_vals[k] for k in range(min(n, len(cit_vals)))}
    return cfads_src, sd_src, cit_src


def _source_shl_schedule(fixture: dict) -> tuple[list[float], list[float], list[float], list[float], list[float]]:
    """Return (gross, cash_interest, pik, principal, closing) source SHL vectors."""
    ds = fixture["ds"]
    gross = ds["shl_net_interest_keur"]
    pik = ds["shl_interest_capitalised_keur"]
    ending = ds["shl_ending_keur"]
    cash_int = [g - p for g, p in zip(gross, pik)]
    beginning = ds["shl_beginning_keur"]
    principal = [b - e + pk for b, e, pk in zip(beginning, ending, pik)]
    return gross, cash_int, pik, principal, ending


# ---------------------------------------------------------------------------
# Source replay validation (workbook rows 36-43)
# ---------------------------------------------------------------------------

def _source_replay_workbook_rows(fixture: dict) -> dict:
    """Replay workbook rows 36-43 from committed source fixture and compare.

    Returns per-period comparison dict.
    SOURCE_REPLAY_PROVEN classification for rows where delta < 1e-3 kEUR.

    Workbook row formulas (Oborovo, all SOURCE_PROVEN):
      Row 36 = losses_n_minus_1: SUMIF(last-5-periods TI, "<0") + cumulative_used
      Row 37 = allocated_losses: IF(AND(row36<=0, EBT>0), MIN(|row36|, EBT), 0)
               -> 0 for Oborovo since EBT < 0 throughout loss period
      Row 38 = losses_n: MIN(row37 + row36, 0) = row36 (since row37=0)
      Row 39 = carriable_losses: MIN(row38, prior_TI * 1)
      Row 41 = taxable_profit_n: TI - row37 = TI (since row37=0)
      Row 43 = CIT: MAX(TP[P-1]+TP[P], 0) * rate * (P>0) * (P%2==0)
    """
    rows = fixture["tax"]["rows"]
    ti_vals = rows["taxable_income"]["period_values"]
    ebt_vals = fixture["pl"]["earnings_before_tax_keur"]

    source_row36 = rows["losses_n_minus_1"]["period_values"]
    source_row37 = rows["allocated_losses"]["period_values"]
    source_row38 = rows["losses_n"]["period_values"]
    source_row39 = rows["carriable_losses"]["period_values"]
    source_row41 = rows["taxable_profit_n"]["period_values"]
    source_row43 = rows["corporate_income_tax_formula"]["period_values"]

    n_ops = min(40, len(ti_vals) - 1)
    ti_history: list[float] = []
    cumulative_used: float = 0.0
    prev_tp: float = 0.0
    comparisons: dict[int, dict] = {}

    for i in range(1, n_ops + 1):
        ti = ti_vals[i] if i < len(ti_vals) else 0.0
        ebt = ebt_vals[i] if i < len(ebt_vals) else 0.0

        window = ti_history[-WORKBOOK_ROLLING_WINDOW:]
        window_losses = sum(t for t in window if t < 0.0)
        r36_replay = window_losses + cumulative_used

        if r36_replay <= 0 and ebt > 0:
            r37_replay = min(abs(r36_replay), ebt)
        else:
            r37_replay = 0.0

        r38_replay = min(r37_replay + r36_replay, 0.0)

        prior_ti = ti_vals[i - 1] if i >= 1 and (i - 1) < len(ti_vals) else 0.0
        r39_replay = min(r38_replay, prior_ti)

        r41_replay = ti - r37_replay

        if i % 2 == 0 and i > 0:
            r43_replay = max(0.0, prev_tp + r41_replay) * WORKBOOK_CIT_RATE
        else:
            r43_replay = 0.0

        def _delta(replay: float, src_list: list, idx: int) -> float:
            sv = src_list[idx] if idx < len(src_list) else 0.0
            return abs(replay - sv)

        comparisons[i] = {
            "period_index": i,
            "row36_replay": r36_replay,
            "row36_source": source_row36[i] if i < len(source_row36) else None,
            "row36_delta": _delta(r36_replay, source_row36, i),
            "row37_replay": r37_replay,
            "row37_source": source_row37[i] if i < len(source_row37) else None,
            "row37_delta": _delta(r37_replay, source_row37, i),
            "row38_replay": r38_replay,
            "row38_source": source_row38[i] if i < len(source_row38) else None,
            "row38_delta": _delta(r38_replay, source_row38, i),
            "row39_replay": r39_replay,
            "row39_source": source_row39[i] if i < len(source_row39) else None,
            "row39_delta": _delta(r39_replay, source_row39, i),
            "row41_replay": r41_replay,
            "row41_source": source_row41[i] if i < len(source_row41) else None,
            "row41_delta": _delta(r41_replay, source_row41, i),
            "row43_replay": r43_replay,
            "row43_source": source_row43[i] if i < len(source_row43) else None,
            "row43_delta": _delta(r43_replay, source_row43, i),
            "classification": (
                "SOURCE_REPLAY_PROVEN"
                if _delta(r43_replay, source_row43, i) < 1e-3
                else "SOURCE_REPLAY_MISMATCH"
            ),
        }

        cumulative_used += r37_replay
        ti_history.append(ti)
        prev_tp = r41_replay

    return comparisons


# ---------------------------------------------------------------------------
# Workbook-compatible tax computation (DIAGNOSTIC ONLY -- not production engine)
# ---------------------------------------------------------------------------

def _compute_workbook_ti_per_period(
    op_periods: list,
    senior_interest_by_period: dict[int, float],
) -> dict[int, float]:
    """Compute workbook-compatible TI per operating period.

    TI formula (Oborovo): EBITDA - tax_dep - senior_interest
    SHL interest: fully non-deductible (FR addback = SHL) -> net zero on TI.
    Note: ATAD disabled for Oborovo (thin_cap=False, BS!G45=False).

    WORKBOOK_COMPATIBILITY_PROFILE: formula matches P&L row 35 (TI = EBT + FR),
    with FR = SHL interest (row 54 mechanics). The clean engine formula differs
    slightly from the workbook decomposition but produces the same TI result
    when SHL is fully non-deductible: TI = EBITDA - tax_dep - senior_interest.
    """
    return {
        p.period_index: (
            p.ebitda_keur
            - p.tax_depreciation_keur
            - senior_interest_by_period.get(p.period_index, 0.0)
        )
        for p in op_periods
    }


def _compute_ebt_per_period(
    op_periods: list,
    senior_interest_by_period: dict[int, float],
    shl_gross_interest_by_period: dict[int, float],
) -> dict[int, float]:
    """EBT per period for the EBT gate (GRID-C).

    EBT = EBITDA - tax_dep - senior_interest - shl_interest

    For the EBT gate: losses utilised only when EBT > 0. Since SHL interest
    is substantial and always positive, EBT remains negative throughout the
    loss period for Oborovo (proved by source fixture EBT vector being
    negative for all periods 0..10 even with positive TI from p6 onwards).

    Classification: SOURCE_PROVEN via row 32 (EBT = EBIT + Financial_Earnings)
    and row 37 (gate condition uses G32 = EBT).
    """
    return {
        p.period_index: (
            p.ebitda_keur
            - p.tax_depreciation_keur
            - senior_interest_by_period.get(p.period_index, 0.0)
            - shl_gross_interest_by_period.get(p.period_index, 0.0)
        )
        for p in op_periods
    }


def _compute_workbook_lcf(
    sorted_op_pidx: list[int],
    ti_by_pidx: dict[int, float],
    ebt_by_pidx: dict[int, float],
    config: WorkbookTaxConfig,
) -> dict[int, float]:
    """Compute taxable_profit_n (= TI after workbook LCF) per operating period.

    Implements workbook rows 36-39-41 mechanics according to config flags.

    Source evidence references:
      Row 36: SUMIF last-B36-periods TI < 0 + cumulative utilised (SOURCE_PROVEN)
      Row 37: IF(AND(losses<=0, EBT>0), MIN(|losses|, EBT), 0) (SOURCE_PROVEN)
      Row 38: MIN(allocated + window_losses, 0) (SOURCE_PROVEN)
      Row 39: MIN(row38, prior_TI x 1) (SOURCE_PROVEN)
      Row 41: -allocated + TI (SOURCE_PROVEN)
    """
    taxable_profit: dict[int, float] = {}
    ti_history: list[tuple[int, float]] = []
    cumulative_used: float = 0.0

    for pidx in sorted_op_pidx:
        ti = ti_by_pidx.get(pidx, 0.0)
        ebt = ebt_by_pidx.get(pidx, 0.0)

        if config.rolling_window:
            window = ti_history[-WORKBOOK_ROLLING_WINDOW:]
        else:
            window = ti_history[-10:]

        window_losses = sum(t for _, t in window if t < 0.0)
        losses_available = window_losses + cumulative_used

        if losses_available <= 0 and ebt > 0 and config.ebt_gate:
            allocated = min(abs(losses_available), ebt)
        elif losses_available <= 0 and ti > 0 and not config.ebt_gate:
            allocated = min(abs(losses_available), ti)
        else:
            allocated = 0.0

        losses_n_uncapped = min(allocated + losses_available, 0.0)

        # ROW39_REPORTING_OR_NON_CAUSAL_FOR_TAX_STATE_SOURCE_PROVEN:
        # Source workbook inspection confirms row39 does not feed forward tax state
        # (rows 36/37/38/41/43). The cap branch below is also mathematically unreachable:
        # min(losses_n_uncapped, prior_ti) with losses_n_uncapped<=0 can only equal
        # losses_n_uncapped (when prior_ti>=0) or go more negative (when prior_ti<0),
        # never produce losses_n > losses_n_uncapped. Removed synthetic propagation.
        # row39_cap flag retained in config for fixture-replay validation only.

        tp = ti - allocated
        taxable_profit[pidx] = tp
        cumulative_used += allocated
        ti_history.append((pidx, ti))

    return taxable_profit


def _compute_cit_by_period(
    sorted_op_pidx: list[int],
    taxable_profit: dict[int, float],
    config: WorkbookTaxConfig,
    cit_rate: float = WORKBOOK_CIT_RATE,
) -> dict[int, float]:
    """Compute CIT cash payment per period from taxable_profit.

    GRID-B (h2h1_pairing=True, SOURCE_PROVEN, WORKBOOK_COMPATIBILITY_PROFILE):
      Row 43: CIT[P] = max(0, TP[P-1] + TP[P]) x rate; fires only in even P.
      Model period number = period_index. Even indices fire CIT.
      Construction (period_index=0) is excluded (row 43 guards (G4>0)).

    CANONICAL approximation (h2h1_pairing=False):
      Each period pays its share of the annual CIT accrual (simplified).
      For diagnostic cross-arm comparison only; exact canonical baseline = GRID-0.

    Returns cash_tax_keur by period_index (positive = outflow).
    """
    cit_by_pidx: dict[int, float] = {}
    prev_tp: float = 0.0

    for pidx in sorted_op_pidx:
        tp = taxable_profit.get(pidx, 0.0)

        if config.h2h1_pairing:
            if pidx % 2 == 0:
                pair_sum = prev_tp + tp
                cit = max(0.0, pair_sum) * cit_rate
            else:
                cit = 0.0
        else:
            cit = max(0.0, tp) * cit_rate

        cit_by_pidx[pidx] = cit
        prev_tp = tp

    return cit_by_pidx


# ---------------------------------------------------------------------------
# SHL metrics computation
# ---------------------------------------------------------------------------

_SHL_FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "tests", "fixtures", "excel_oborovo_shl_operating_truth.json",
)


def _load_shl_fixture() -> dict:
    with open(_SHL_FIXTURE_PATH) as f:
        return json.load(f)


def _build_shl_schedule_from_phase2c(phase2c_result: object) -> object:
    """Compute the SHL schedule from Phase 2C result using D2A authoritative inputs.

    Mirrors the D2B1 test fixture exactly: 40 operating periods from the SHL
    source fixture (excel_oborovo_shl_operating_truth.json), zipped with the
    first 40 elements of the seam_operating sequence.
    DS[40] closing = EXPECTED_PRE_D2B2_UPSTREAM_CLEAN_CASH_RESIDUAL (~2718 kEUR).
    """
    from financial_engine.shl.production import (
        ShlConstructionInput, ShlOperatingPeriodInput, ShlWaterfallPolicy, compute_shl_schedule,
    )
    from financial_engine.shl.contracts import ShlDayCountConvention
    from financial_engine.adapters.shl_cash_seam import compute_shl_cash_from_phase2c

    constr = ShlConstructionInput(
        draw_keur=SHL_DRAW_KEUR,
        annual_rate=SHL_ANNUAL_RATE,
        dcf=1.0,
        period_index=0,
    )
    policy = ShlWaterfallPolicy(
        annual_rate=SHL_ANNUAL_RATE,
        day_count_convention=ShlDayCountConvention.ACT_365_FIXED,
    )

    seam = compute_shl_cash_from_phase2c(phase2c_result)

    shl_fixture = _load_shl_fixture()
    shl_op_periods = shl_fixture["periods"][1:]

    seam_operating = [s for s in seam if not s.is_construction]
    n = min(len(seam_operating), len(shl_op_periods))
    op_inputs = []
    for s, fp in zip(seam_operating[:n], shl_op_periods[:n]):
        op_inputs.append(ShlOperatingPeriodInput(
            period_index=s.period_index,
            period_start=date.fromisoformat(fp["period_start_date"]),
            period_end=date.fromisoformat(fp["period_end_date"]),
            cash_available_for_shl_keur=s.cash_available_for_shl_keur,
            drawdown_keur=0.0,
        ))

    return compute_shl_schedule(constr, op_inputs, policy), seam


def _collect_shl_metrics(
    shl_result,
    seam,
    source_fixture: dict,
    grid0_final_closing: float,
) -> dict:
    """Compute SHL residual metrics vs D2A source oracle."""
    gross_src, cash_src, pik_src, principal_src, closing_src = _source_shl_schedule(source_fixture)
    n = min(len(shl_result.operating), len(gross_src))

    gross_deltas = []
    cash_deltas = []
    pik_deltas = []
    principal_deltas = []
    closing_deltas = []

    for i, op in enumerate(shl_result.operating[:n]):
        gross_deltas.append(abs(op.gross_accrued_interest_keur - gross_src[i]))
        cash_deltas.append(abs(op.cash_interest_keur - cash_src[i]))
        pik_deltas.append(abs(op.pik_interest_keur - pik_src[i]))
        principal_deltas.append(abs(op.principal_repaid_keur - principal_src[i]))
        closing_deltas.append(abs(op.closing_balance_keur - closing_src[i]))

    ds40_closing = shl_result.operating[-1].closing_balance_keur if shl_result.operating else 0.0

    shl_src_list = _source_candidate_shl_cash_ds1_40(source_fixture)
    seam_op = sorted(
        [s for s in seam if not s.is_construction], key=lambda s: s.period_index
    )
    n_shl = min(len(seam_op), len(shl_src_list), 40)
    shl_cash_deltas = [
        abs(seam_op[k].cash_available_for_shl_keur - shl_src_list[k])
        for k in range(n_shl)
    ]
    shl_cash_signed = sum(
        seam_op[k].cash_available_for_shl_keur - shl_src_list[k]
        for k in range(n_shl)
    )

    return {
        "gross_interest_max_delta": max(gross_deltas) if gross_deltas else 0.0,
        "cash_interest_max_delta": max(cash_deltas) if cash_deltas else 0.0,
        "pik_max_delta": max(pik_deltas) if pik_deltas else 0.0,
        "principal_max_delta": max(principal_deltas) if principal_deltas else 0.0,
        "closing_max_delta": max(closing_deltas) if closing_deltas else 0.0,
        "ds40_final_closing_keur": ds40_closing,
        "delta_vs_grid0_final_closing": ds40_closing - grid0_final_closing,
        "max_shl_cash_delta_vs_source": max(shl_cash_deltas) if shl_cash_deltas else 0.0,
        "signed_total_shl_cash_delta": shl_cash_signed,
    }


# ---------------------------------------------------------------------------
# Canonical tax callback builder (GRID-S0)
# ---------------------------------------------------------------------------

def _make_canonical_tax_callback(phase2b_result, base_tax_input):
    """Returns tax_cfads_fn using canonical calculate_tax() -- same as run_senior_debt_model."""
    from financial_engine.inputs import TaxCalculationInput, PeriodInterestInput
    from financial_engine.tax.engine import calculate_tax
    from financial_engine.cfads import calculate_canonical_cfads

    def tax_cfads_fn(senior_interest_by_period: dict) -> tuple:
        merged = {}
        for pi in base_tax_input.period_interest:
            merged[pi.period_index] = pi
        for idx, sr in senior_interest_by_period.items():
            existing = merged.get(idx)
            if existing:
                merged[idx] = PeriodInterestInput(
                    period_index=idx,
                    senior_interest_keur=sr,
                    shl_interest_keur=existing.shl_interest_keur,
                    other_interest_keur=existing.other_interest_keur,
                )
            else:
                merged[idx] = PeriodInterestInput(
                    period_index=idx,
                    senior_interest_keur=sr,
                )
        updated = TaxCalculationInput(
            policy=base_tax_input.policy,
            opening_loss_vintages=base_tax_input.opening_loss_vintages,
            period_interest=tuple(merged.values()),
            period_adjustments=base_tax_input.period_adjustments,
        )
        tax_result = calculate_tax(phase2b_result.periods, updated)
        cfads_results = calculate_canonical_cfads(phase2b_result.periods, tax_result.period_results)
        cfads_by_period = {cr.period_index: cr.cfads_keur for cr in cfads_results}
        cash_tax_by_period = {pr.period_index: pr.cash_tax_keur for pr in tax_result.period_results}
        return cfads_by_period, cash_tax_by_period

    return tax_cfads_fn


# ---------------------------------------------------------------------------
# Grid arm runners
# ---------------------------------------------------------------------------

def run_grid_0(source_fixture: dict) -> GridArmResult:
    """GRID-0: Exact current main baseline -- reproduces D2B1 production-candidate metrics.

    source_fcf_for_banks_keur = D2B1 source CFADS (D2B1 contract: fcf_for_banks_keur[1:41])
    clean_cfads_keur = seam.cfads_keur = EBITDA - canonical cash_tax
    Both are directly comparable (both = EBITDA - cash_tax).
    """
    from app.project_factories import create_default_oborovo
    from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
    from financial_engine.orchestrator import run_senior_debt_model

    proj = create_default_oborovo()
    sd_input = build_senior_debt_model_input_from_project_inputs(
        proj, source_id="c3b3d2b2a-grid0"
    )
    phase2c = run_senior_debt_model(sd_input)

    shl_result, seam = _build_shl_schedule_from_phase2c(phase2c)

    tac = phase2c.tax_and_cfads
    sd = phase2c.senior_debt

    tac_pidx = list(tac.period_indices)
    tac_cit = list(tac.corporate_tax_cash_keur)
    tac_cfads = list(tac.cfads_keur)

    cit_by_pidx = dict(zip(tac_pidx, tac_cit))
    cfads_by_pidx = dict(zip(tac_pidx, tac_cfads))

    # Position-aligned source comparison: k-th clean operating period maps to
    # k-th source DS[1..40] value. Required because clean model has 2 construction
    # periods (period_index 0 and 1), so first operating period_index = 2.
    seam_op_sorted = sorted(
        [s for s in seam if not s.is_construction], key=lambda s: s.period_index
    )
    clean_op_indices = [s.period_index for s in seam_op_sorted]
    cfads_src, sd_src, cit_src = _aligned_source_dicts(clean_op_indices, source_fixture)
    n_op = len(clean_op_indices[:40])

    total_cit = sum(cit_by_pidx.get(idx, 0.0) for idx in clean_op_indices[:40])
    tax_deltas = [abs(cit_by_pidx.get(clean_op_indices[k], 0.0) - cit_src.get(clean_op_indices[k], 0.0)) for k in range(n_op)]
    signed_tax = sum(cit_by_pidx.get(clean_op_indices[k], 0.0) - cit_src.get(clean_op_indices[k], 0.0) for k in range(n_op))

    cfads_deltas_abs = [abs(cfads_by_pidx.get(clean_op_indices[k], 0.0) - cfads_src.get(clean_op_indices[k], 0.0)) for k in range(n_op)]
    cfads_signed = sum(cfads_by_pidx.get(clean_op_indices[k], 0.0) - cfads_src.get(clean_op_indices[k], 0.0) for k in range(n_op))
    total_cfads = sum(cfads_by_pidx.get(idx, 0.0) for idx in clean_op_indices[:40])
    source_total_cfads = sum(cfads_src.values())

    sd_service_by_pidx = dict(zip(sd.period_indices, sd.senior_debt_service_keur))
    sd_deltas = [abs(sd_service_by_pidx.get(clean_op_indices[k], 0.0) - sd_src.get(clean_op_indices[k], 0.0)) for k in range(n_op)]
    sd_signed = sum(sd_service_by_pidx.get(clean_op_indices[k], 0.0) - sd_src.get(clean_op_indices[k], 0.0) for k in range(n_op))

    clean_debt = sd.diagnostics.get("final_debt_size_keur", 0.0)

    ds40_closing = shl_result.operating[-1].closing_balance_keur
    shl_m = _collect_shl_metrics(shl_result, seam, source_fixture, ds40_closing)

    source_total_cit = 10_443.088331999998

    return GridArmResult(
        arm_id="GRID-0",
        arm_label="Current clean baseline (C3B3D2B1 main)",
        source_evidence="CANONICAL_TAX_LOGIC",
        config=WorkbookTaxConfig(),
        surrogate_baseline="GRID-0",
        total_cash_tax_keur=total_cit,
        source_total_cash_tax_keur=source_total_cit,
        total_tax_delta_vs_source=signed_tax,
        max_period_tax_delta_vs_source=max(tax_deltas) if tax_deltas else 0.0,
        total_cfads_keur=total_cfads,
        source_total_cfads_keur=source_total_cfads,
        max_cfads_delta_vs_source=max(cfads_deltas_abs) if cfads_deltas_abs else 0.0,
        signed_total_cfads_delta=cfads_signed,
        clean_debt_size_keur=clean_debt,
        debt_size_delta_keur=clean_debt - SOURCE_DEBT_SIZE_KEUR,
        max_senior_ds_delta_vs_source=max(sd_deltas) if sd_deltas else 0.0,
        signed_total_senior_ds_delta=sd_signed,
        max_shl_cash_delta_vs_source=shl_m["max_shl_cash_delta_vs_source"],
        signed_total_shl_cash_delta=shl_m["signed_total_shl_cash_delta"],
        gross_interest_max_delta=shl_m["gross_interest_max_delta"],
        cash_interest_max_delta=shl_m["cash_interest_max_delta"],
        pik_max_delta=shl_m["pik_max_delta"],
        principal_max_delta=shl_m["principal_max_delta"],
        closing_max_delta=shl_m["closing_max_delta"],
        ds40_final_closing_keur=ds40_closing,
        delta_vs_grid0_final_closing=0.0,
        convergence_iterations=0,
        convergence_achieved=True,
        convergence_note="N/A -- exact canonical clean engine",
        solver_converged=sd.diagnostics.get("converged", False),
        solver_iterations=sd.diagnostics.get("iteration_count", 0),
    )


def run_grid_s0(source_fixture: dict, grid0: GridArmResult) -> GridArmResult:
    """GRID-S0: Canonical callback SURROGATE-0.

    Uses solve_senior_debt() with a callback that calls the canonical
    calculate_tax() engine inside. Must prove GRID-S0 equiv GRID-0 within
    solver tolerance. If they differ materially, reports SURROGATE_MISMATCH.

    This validates that the surrogate callback pattern produces identical
    results to run_senior_debt_model(), establishing it as a valid baseline
    for B/C/D/E relative arms.
    """
    from app.project_factories import create_default_oborovo
    from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
    from financial_engine.orchestrator import run_tax_cfads_model
    from financial_engine.senior_debt.solver import solve_senior_debt
    from financial_engine.inputs import TaxCfadsModelInput

    proj = create_default_oborovo()
    sd_input = build_senior_debt_model_input_from_project_inputs(
        proj, source_id="c3b3d2b2a-grids0"
    )

    op_input = TaxCfadsModelInput(operating=sd_input.operating, tax=sd_input.tax)
    phase2b = run_tax_cfads_model(op_input)

    base_tax_input = sd_input.tax
    tax_cfads_fn = _make_canonical_tax_callback(phase2b, base_tax_input)

    policy = sd_input.senior_debt_policy
    op_periods = phase2b.periods
    debt_start = policy.repayment_start_period_index
    debt_end = policy.maturity_period_index
    debt_periods = tuple(
        p for p in op_periods
        if p.is_operation and debt_start <= p.period_index <= debt_end
    )

    sd_result = solve_senior_debt(
        policy=policy,
        inputs=sd_input.senior_debt_inputs,
        periods=debt_periods,
        tax_cfads_fn=tax_cfads_fn,
    )

    final_senior_int = dict(zip(sd_result.period_indices, sd_result.senior_interest_keur))
    cfads_final, cit_final = tax_cfads_fn(final_senior_int)

    phase2c_proxy = _build_phase2c_proxy(
        op_periods=op_periods,
        cfads_by_pidx=cfads_final,
        cash_tax_by_pidx=cit_final,
        sd_result=sd_result,
        policy=policy,
    )
    shl_result, seam = _build_shl_schedule_from_phase2c(phase2c_proxy)

    # Position-aligned source comparison
    clean_op_indices = sorted([p.period_index for p in op_periods if p.is_operation])
    cfads_src, sd_src, cit_src = _aligned_source_dicts(clean_op_indices, source_fixture)
    n_op = len(clean_op_indices[:40])

    total_cit = sum(cit_final.get(idx, 0.0) for idx in clean_op_indices[:40])
    total_cfads_val = sum(cfads_final.get(idx, 0.0) for idx in clean_op_indices[:40])
    source_total_cfads = sum(cfads_src.values())
    tax_deltas = [abs(cit_final.get(clean_op_indices[k], 0.0) - cit_src.get(clean_op_indices[k], 0.0)) for k in range(n_op)]
    signed_tax = sum(cit_final.get(clean_op_indices[k], 0.0) - cit_src.get(clean_op_indices[k], 0.0) for k in range(n_op))
    cfads_deltas = [abs(cfads_final.get(clean_op_indices[k], 0.0) - cfads_src.get(clean_op_indices[k], 0.0)) for k in range(n_op)]
    cfads_signed = sum(cfads_final.get(clean_op_indices[k], 0.0) - cfads_src.get(clean_op_indices[k], 0.0) for k in range(n_op))

    sd_service_by_pidx = dict(zip(sd_result.period_indices, sd_result.senior_debt_service_keur))
    sd_deltas = [abs(sd_service_by_pidx.get(clean_op_indices[k], 0.0) - sd_src.get(clean_op_indices[k], 0.0)) for k in range(n_op)]
    sd_signed = sum(sd_service_by_pidx.get(clean_op_indices[k], 0.0) - sd_src.get(clean_op_indices[k], 0.0) for k in range(n_op))
    clean_debt = sd_result.diagnostics.final_debt_size_keur

    ds40_closing = shl_result.operating[-1].closing_balance_keur if shl_result.operating else 0.0
    shl_m = _collect_shl_metrics(shl_result, seam, source_fixture, grid0.ds40_final_closing_keur)

    closing_diff = abs(ds40_closing - grid0.ds40_final_closing_keur)
    if closing_diff > 1.0:
        convergence_note = (
            f"SURROGATE_MISMATCH: GRID-S0 DS40={ds40_closing:.3f} vs "
            f"GRID-0 DS40={grid0.ds40_final_closing_keur:.3f} -- "
            f"diff={closing_diff:.3f} kEUR exceeds solver tolerance. "
            f"Solver: {sd_result.diagnostics.termination_reason}"
        )
    else:
        convergence_note = (
            f"GRID-S0 equiv GRID-0 within {closing_diff:.4f} kEUR. "
            f"Canonical callback surrogate validated. "
            f"Solver: {sd_result.diagnostics.termination_reason}"
        )

    return GridArmResult(
        arm_id="GRID-S0",
        arm_label="Canonical callback SURROGATE-0 (validates solve_senior_debt pattern)",
        source_evidence="CANONICAL_TAX_LOGIC via solve_senior_debt callback",
        config=WorkbookTaxConfig(),
        surrogate_baseline="GRID-0",
        total_cash_tax_keur=total_cit,
        source_total_cash_tax_keur=10_443.088331999998,
        total_tax_delta_vs_source=signed_tax,
        max_period_tax_delta_vs_source=max(tax_deltas) if tax_deltas else 0.0,
        total_cfads_keur=total_cfads_val,
        source_total_cfads_keur=source_total_cfads,
        max_cfads_delta_vs_source=max(cfads_deltas) if cfads_deltas else 0.0,
        signed_total_cfads_delta=cfads_signed,
        clean_debt_size_keur=clean_debt,
        debt_size_delta_keur=clean_debt - SOURCE_DEBT_SIZE_KEUR,
        max_senior_ds_delta_vs_source=max(sd_deltas) if sd_deltas else 0.0,
        signed_total_senior_ds_delta=sd_signed,
        max_shl_cash_delta_vs_source=shl_m["max_shl_cash_delta_vs_source"],
        signed_total_shl_cash_delta=shl_m["signed_total_shl_cash_delta"],
        gross_interest_max_delta=shl_m["gross_interest_max_delta"],
        cash_interest_max_delta=shl_m["cash_interest_max_delta"],
        pik_max_delta=shl_m["pik_max_delta"],
        principal_max_delta=shl_m["principal_max_delta"],
        closing_max_delta=shl_m["closing_max_delta"],
        ds40_final_closing_keur=ds40_closing,
        delta_vs_grid0_final_closing=shl_m["delta_vs_grid0_final_closing"],
        convergence_iterations=sd_result.diagnostics.iteration_count,
        convergence_achieved=sd_result.diagnostics.converged,
        convergence_note=convergence_note,
        solver_converged=sd_result.diagnostics.converged,
        solver_iterations=sd_result.diagnostics.iteration_count,
    )


def run_grid_ws0(source_fixture: dict, grid0: GridArmResult) -> GridArmResult:
    """GRID-WS0: Workbook callback SURROGATE-0, all flags False.

    Uses solve_senior_debt() with workbook callback and all WorkbookTaxConfig
    flags=False. This is the baseline for relative B/C/D/E arm claims.
    Must be validated against GRID-0 before causal conclusions can be drawn.
    Any difference GRID-WS0 vs GRID-0 is the diagnostic callback approximation
    error, not a causal factor.

    Classification: CURRENT_CAUSE_UNRESOLVED until GRID-WS0 equiv GRID-0 proven.
    """
    config = WorkbookTaxConfig()
    arm_result = _run_workbook_arm(
        arm_id="GRID-WS0",
        arm_label="Workbook callback all-False SURROGATE (baseline for B/C/D/E)",
        source_evidence="WORKBOOK_CALLBACK_SURROGATE: all flags False. Relative baseline only.",
        config=config,
        source_fixture=source_fixture,
        grid0=grid0,
        shl_gross_by_period={},
    )
    # Re-stamp surrogate_baseline field for this special arm
    return GridArmResult(
        arm_id=arm_result.arm_id,
        arm_label=arm_result.arm_label,
        source_evidence=arm_result.source_evidence,
        config=arm_result.config,
        surrogate_baseline="GRID-WS0",
        total_cash_tax_keur=arm_result.total_cash_tax_keur,
        source_total_cash_tax_keur=arm_result.source_total_cash_tax_keur,
        total_tax_delta_vs_source=arm_result.total_tax_delta_vs_source,
        max_period_tax_delta_vs_source=arm_result.max_period_tax_delta_vs_source,
        total_cfads_keur=arm_result.total_cfads_keur,
        source_total_cfads_keur=arm_result.source_total_cfads_keur,
        max_cfads_delta_vs_source=arm_result.max_cfads_delta_vs_source,
        signed_total_cfads_delta=arm_result.signed_total_cfads_delta,
        clean_debt_size_keur=arm_result.clean_debt_size_keur,
        debt_size_delta_keur=arm_result.debt_size_delta_keur,
        max_senior_ds_delta_vs_source=arm_result.max_senior_ds_delta_vs_source,
        signed_total_senior_ds_delta=arm_result.signed_total_senior_ds_delta,
        max_shl_cash_delta_vs_source=arm_result.max_shl_cash_delta_vs_source,
        signed_total_shl_cash_delta=arm_result.signed_total_shl_cash_delta,
        gross_interest_max_delta=arm_result.gross_interest_max_delta,
        cash_interest_max_delta=arm_result.cash_interest_max_delta,
        pik_max_delta=arm_result.pik_max_delta,
        principal_max_delta=arm_result.principal_max_delta,
        closing_max_delta=arm_result.closing_max_delta,
        ds40_final_closing_keur=arm_result.ds40_final_closing_keur,
        delta_vs_grid0_final_closing=arm_result.delta_vs_grid0_final_closing,
        convergence_iterations=arm_result.convergence_iterations,
        convergence_achieved=arm_result.convergence_achieved,
        convergence_note=arm_result.convergence_note,
        solver_converged=arm_result.solver_converged,
        solver_iterations=arm_result.solver_iterations,
    )


def run_grid_a(
    source_fixture: dict,
    grid0: GridArmResult,
) -> GridArmResult:
    """GRID-A: SHL interest feedback into tax (SHL->tax->CFADS->SD->SHL loop).

    For Oborovo: SHL is FULLY NON-DEDUCTIBLE (C59=1.0, D59=True -> FR=SHL).
    The typed tax execution path:
      1. Get gross SHL interest per period from preliminary SHL schedule
      2. Build PeriodInterestInput with shl_interest_keur=gross_shl_keur
      3. Build PeriodTaxAdjustmentInput with other_fiscal_reintegration_keur=gross_shl_keur
         (non-deductible addback for Oborovo)
      4. Net TI effect = -gross_shl (deduction) + gross_shl (addback) = 0

    Result: GRID-A equiv GRID-0 for Oborovo.
    Classification: FIXED_POINT_COLLAPSES_ANALYTICALLY_TO_IDENTITY_FOR_OBOROVO
    Source evidence: P&L rows 54, 59 (non-deductible SHL, SOURCE_PROVEN).
    C59=1.0, D59=True -> full reintegration -> deductible_SHL = 0.
    """
    from app.project_factories import create_default_oborovo
    from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
    from financial_engine.orchestrator import run_senior_debt_model, run_tax_cfads_model
    from financial_engine.inputs import (
        TaxCalculationInput, PeriodInterestInput, TaxCfadsModelInput,
    )
    from financial_engine.tax.engine import calculate_tax
    from financial_engine.cfads import calculate_canonical_cfads
    from financial_engine.senior_debt.solver import solve_senior_debt

    try:
        from financial_engine.inputs import PeriodTaxAdjustmentInput
    except ImportError:
        PeriodTaxAdjustmentInput = None

    proj = create_default_oborovo()
    sd_input = build_senior_debt_model_input_from_project_inputs(
        proj, source_id="c3b3d2b2a-grida"
    )

    # Preliminary SHL gross from GRID-0 SHL schedule
    phase2c_base = run_senior_debt_model(sd_input)
    shl_base, _ = _build_shl_schedule_from_phase2c(phase2c_base)
    shl_gross_by_pidx: dict[int, float] = {}
    for op in shl_base.operating:
        shl_gross_by_pidx[op.period_index] = op.gross_accrued_interest_keur

    op_input = TaxCfadsModelInput(operating=sd_input.operating, tax=sd_input.tax)
    phase2b = run_tax_cfads_model(op_input)
    base_tax_input = sd_input.tax

    def tax_cfads_fn_a(senior_interest_by_period: dict) -> tuple:
        merged = {}
        for pi in base_tax_input.period_interest:
            merged[pi.period_index] = pi
        # Debt tenor periods: inject senior_interest + shl_interest together
        for idx, sr in senior_interest_by_period.items():
            existing = merged.get(idx)
            gross_shl = shl_gross_by_pidx.get(idx, 0.0)
            shl_keur = (existing.shl_interest_keur if existing else 0.0) + gross_shl
            merged[idx] = PeriodInterestInput(
                period_index=idx,
                senior_interest_keur=sr,
                shl_interest_keur=shl_keur,
                other_interest_keur=existing.other_interest_keur if existing else 0.0,
            )
        # Full horizon: also inject shl_interest for post-maturity SHL periods.
        # Both shl_interest (deduction) and reintegration (addback below) are needed
        # so the net TI effect stays 0 for all periods, not just debt tenor.
        for idx in set(shl_gross_by_pidx.keys()) - set(senior_interest_by_period.keys()):
            gross_shl = shl_gross_by_pidx.get(idx, 0.0)
            if gross_shl == 0.0:
                continue
            existing = merged.get(idx)
            shl_keur = (existing.shl_interest_keur if existing else 0.0) + gross_shl
            merged[idx] = PeriodInterestInput(
                period_index=idx,
                senior_interest_keur=existing.senior_interest_keur if existing else 0.0,
                shl_interest_keur=shl_keur,
                other_interest_keur=existing.other_interest_keur if existing else 0.0,
            )

        if PeriodTaxAdjustmentInput is not None:
            existing_adj = {a.period_index: a for a in (base_tax_input.period_adjustments or ())}
            new_adj = list(existing_adj.values())
            injected_periods = set(senior_interest_by_period.keys()) | set(shl_gross_by_pidx.keys())
            for idx in injected_periods:
                gross_shl = shl_gross_by_pidx.get(idx, 0.0)
                if gross_shl == 0.0:
                    continue
                prior = existing_adj.get(idx)
                prior_reint = getattr(prior, "other_fiscal_reintegration_keur", 0.0) if prior else 0.0
                entry = PeriodTaxAdjustmentInput(
                    period_index=idx,
                    other_fiscal_reintegration_keur=prior_reint + gross_shl,
                )
                new_adj = [a for a in new_adj if a.period_index != idx]
                new_adj.append(entry)
            period_adjustments = tuple(new_adj)
        else:
            period_adjustments = base_tax_input.period_adjustments

        updated = TaxCalculationInput(
            policy=base_tax_input.policy,
            opening_loss_vintages=base_tax_input.opening_loss_vintages,
            period_interest=tuple(merged.values()),
            period_adjustments=period_adjustments,
        )
        tax_result = calculate_tax(phase2b.periods, updated)
        cfads_results = calculate_canonical_cfads(phase2b.periods, tax_result.period_results)
        cfads_by_period = {cr.period_index: cr.cfads_keur for cr in cfads_results}
        cash_tax_by_period = {pr.period_index: pr.cash_tax_keur for pr in tax_result.period_results}
        return cfads_by_period, cash_tax_by_period

    policy = sd_input.senior_debt_policy
    op_periods = phase2b.periods
    debt_start = policy.repayment_start_period_index
    debt_end = policy.maturity_period_index
    debt_periods = tuple(
        p for p in op_periods
        if p.is_operation and debt_start <= p.period_index <= debt_end
    )

    sd_result = solve_senior_debt(
        policy=policy,
        inputs=sd_input.senior_debt_inputs,
        periods=debt_periods,
        tax_cfads_fn=tax_cfads_fn_a,
    )

    final_senior_int = dict(zip(sd_result.period_indices, sd_result.senior_interest_keur))
    cfads_final, cit_final = tax_cfads_fn_a(final_senior_int)

    phase2c_proxy = _build_phase2c_proxy(
        op_periods=op_periods,
        cfads_by_pidx=cfads_final,
        cash_tax_by_pidx=cit_final,
        sd_result=sd_result,
        policy=policy,
    )
    shl_result, seam = _build_shl_schedule_from_phase2c(phase2c_proxy)

    # Position-aligned source comparison
    clean_op_indices = sorted([p.period_index for p in op_periods if p.is_operation])
    cfads_src, sd_src, cit_src = _aligned_source_dicts(clean_op_indices, source_fixture)
    n_op = len(clean_op_indices[:40])

    total_cit = sum(cit_final.get(idx, 0.0) for idx in clean_op_indices[:40])
    total_cfads_val = sum(cfads_final.get(idx, 0.0) for idx in clean_op_indices[:40])
    source_total_cfads = sum(cfads_src.values())
    tax_deltas = [abs(cit_final.get(clean_op_indices[k], 0.0) - cit_src.get(clean_op_indices[k], 0.0)) for k in range(n_op)]
    signed_tax = sum(cit_final.get(clean_op_indices[k], 0.0) - cit_src.get(clean_op_indices[k], 0.0) for k in range(n_op))
    cfads_deltas = [abs(cfads_final.get(clean_op_indices[k], 0.0) - cfads_src.get(clean_op_indices[k], 0.0)) for k in range(n_op)]
    cfads_signed = sum(cfads_final.get(clean_op_indices[k], 0.0) - cfads_src.get(clean_op_indices[k], 0.0) for k in range(n_op))

    sd_service_by_pidx = dict(zip(sd_result.period_indices, sd_result.senior_debt_service_keur))
    sd_deltas = [abs(sd_service_by_pidx.get(clean_op_indices[k], 0.0) - sd_src.get(clean_op_indices[k], 0.0)) for k in range(n_op)]
    sd_signed = sum(sd_service_by_pidx.get(clean_op_indices[k], 0.0) - sd_src.get(clean_op_indices[k], 0.0) for k in range(n_op))
    clean_debt = sd_result.diagnostics.final_debt_size_keur

    ds40_closing = shl_result.operating[-1].closing_balance_keur if shl_result.operating else 0.0
    shl_m = _collect_shl_metrics(shl_result, seam, source_fixture, grid0.ds40_final_closing_keur)

    closing_diff = abs(ds40_closing - grid0.ds40_final_closing_keur)
    convergence_note = (
        f"FIXED_POINT_COLLAPSES_ANALYTICALLY_TO_IDENTITY_FOR_OBOROVO. "
        f"SHL fully non-deductible (C59=1.0, D59=True): "
        f"net TI = -gross_shl + gross_shl = 0. "
        f"Delta vs GRID-0: {closing_diff:.4f} kEUR. "
        f"Solver: {sd_result.diagnostics.termination_reason}"
    )

    return GridArmResult(
        arm_id="GRID-A",
        arm_label="SHL interest feedback (non-deductible: net TI=0 for Oborovo)",
        source_evidence=(
            "SOURCE_PROVEN: P&L row 59 C59=1.0, D59=True -> full SHL non-deductibility. "
            "Typed execution: shl_interest + other_fiscal_reintegration=gross_shl -> net TI=0. "
            "FIXED_POINT_COLLAPSES_ANALYTICALLY_TO_IDENTITY_FOR_OBOROVO."
        ),
        config=WorkbookTaxConfig(shl_netting_in_tax=True),
        surrogate_baseline="GRID-0",
        total_cash_tax_keur=total_cit,
        source_total_cash_tax_keur=10_443.088331999998,
        total_tax_delta_vs_source=signed_tax,
        max_period_tax_delta_vs_source=max(tax_deltas) if tax_deltas else 0.0,
        total_cfads_keur=total_cfads_val,
        source_total_cfads_keur=source_total_cfads,
        max_cfads_delta_vs_source=max(cfads_deltas) if cfads_deltas else 0.0,
        signed_total_cfads_delta=cfads_signed,
        clean_debt_size_keur=clean_debt,
        debt_size_delta_keur=clean_debt - SOURCE_DEBT_SIZE_KEUR,
        max_senior_ds_delta_vs_source=max(sd_deltas) if sd_deltas else 0.0,
        signed_total_senior_ds_delta=sd_signed,
        max_shl_cash_delta_vs_source=shl_m["max_shl_cash_delta_vs_source"],
        signed_total_shl_cash_delta=shl_m["signed_total_shl_cash_delta"],
        gross_interest_max_delta=shl_m["gross_interest_max_delta"],
        cash_interest_max_delta=shl_m["cash_interest_max_delta"],
        pik_max_delta=shl_m["pik_max_delta"],
        principal_max_delta=shl_m["principal_max_delta"],
        closing_max_delta=shl_m["closing_max_delta"],
        ds40_final_closing_keur=ds40_closing,
        delta_vs_grid0_final_closing=shl_m["delta_vs_grid0_final_closing"],
        convergence_iterations=sd_result.diagnostics.iteration_count,
        convergence_achieved=sd_result.diagnostics.converged,
        convergence_note=convergence_note,
        solver_converged=sd_result.diagnostics.converged,
        solver_iterations=sd_result.diagnostics.iteration_count,
    )


def _run_workbook_arm(
    arm_id: str,
    arm_label: str,
    source_evidence: str,
    config: WorkbookTaxConfig,
    source_fixture: dict,
    grid0: GridArmResult,
    shl_gross_by_period: dict[int, float],
) -> GridArmResult:
    """Run a workbook-compatible grid arm with the Phase2C debt solver.

    Uses the authoritative D2A SHL inputs and D2B1 SHL gross interest vector
    (fixed from GRID-0, since all tested arms have non-deductible SHL).

    Architecture note:
      The Phase2C solver (solve_senior_debt) accepts a custom tax_cfads_fn.
      This function provides the workbook-compatible tax mechanics as the
      callback. The solver iterates debt size while calling back into the
      workbook tax function with updated senior interest per iteration.

    Convergence: the solver's inner loop converges on debt size. The outer
    SHL->tax loop is not run for B/C/D/E arms because SHL is non-deductible
    and GRID-A proved this adds zero TI change.

    Relative claims vs GRID-WS0 only valid after GRID-WS0 equiv GRID-0 is proven.
    """
    from app.project_factories import create_default_oborovo
    from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
    from financial_engine.orchestrator import run_tax_cfads_model
    from financial_engine.senior_debt.solver import solve_senior_debt
    from financial_engine.inputs import TaxCfadsModelInput

    proj = create_default_oborovo()
    sd_input = build_senior_debt_model_input_from_project_inputs(
        proj, source_id=f"c3b3d2b2a-{arm_id.lower().replace('-', '')}"
    )

    op_input = TaxCfadsModelInput(operating=sd_input.operating, tax=sd_input.tax)
    phase2b = run_tax_cfads_model(op_input)
    op_periods = phase2b.periods

    op_sorted = sorted([p for p in op_periods if p.is_operation], key=lambda p: p.period_index)
    sorted_op_pidx = [p.period_index for p in op_sorted]

    policy = sd_input.senior_debt_policy
    corporate_rate = WORKBOOK_CIT_RATE

    def tax_cfads_fn(senior_interest_by_period: dict[int, float]) -> tuple[dict, dict]:
        """Workbook-compatible tax callback for solve_senior_debt."""
        ti_by_pidx = _compute_workbook_ti_per_period(op_sorted, senior_interest_by_period)
        ebt_by_pidx = _compute_ebt_per_period(
            op_sorted, senior_interest_by_period, shl_gross_by_period
        )
        taxable_profit = _compute_workbook_lcf(
            sorted_op_pidx, ti_by_pidx, ebt_by_pidx, config
        )
        cit_by_pidx = _compute_cit_by_period(
            sorted_op_pidx, taxable_profit, config, corporate_rate
        )
        cfads_by_period = {
            p.period_index: p.ebitda_keur - cit_by_pidx.get(p.period_index, 0.0)
            for p in op_sorted
        }
        cash_tax_by_period = dict(cit_by_pidx)
        return cfads_by_period, cash_tax_by_period

    debt_start = policy.repayment_start_period_index
    debt_end = policy.maturity_period_index
    debt_periods = tuple(
        p for p in op_periods
        if p.is_operation and debt_start <= p.period_index <= debt_end
    )

    sd_result = solve_senior_debt(
        policy=policy,
        inputs=sd_input.senior_debt_inputs,
        periods=debt_periods,
        tax_cfads_fn=tax_cfads_fn,
    )

    final_senior_int = dict(zip(sd_result.period_indices, sd_result.senior_interest_keur))
    ti_final = _compute_workbook_ti_per_period(op_sorted, final_senior_int)
    ebt_final = _compute_ebt_per_period(op_sorted, final_senior_int, shl_gross_by_period)
    tp_final = _compute_workbook_lcf(sorted_op_pidx, ti_final, ebt_final, config)
    cit_final = _compute_cit_by_period(sorted_op_pidx, tp_final, config, corporate_rate)

    cfads_final = {
        p.period_index: p.ebitda_keur - cit_final.get(p.period_index, 0.0)
        for p in op_sorted
    }
    phase2c_proxy = _build_phase2c_proxy(
        op_periods=op_periods,
        cfads_by_pidx=cfads_final,
        cash_tax_by_pidx=cit_final,
        sd_result=sd_result,
        policy=policy,
    )
    shl_result, seam = _build_shl_schedule_from_phase2c(phase2c_proxy)

    # Position-aligned source comparison; total_cit restricted to DS[1..40] (first 40 op periods)
    n_first40 = min(40, len(sorted_op_pidx))
    first40_pidx = sorted_op_pidx[:n_first40]
    cfads_src, sd_src, cit_src = _aligned_source_dicts(first40_pidx, source_fixture)

    total_cit = sum(cit_final.get(idx, 0.0) for idx in first40_pidx)
    tax_deltas = [abs(cit_final.get(first40_pidx[k], 0.0) - cit_src.get(first40_pidx[k], 0.0)) for k in range(n_first40)]
    signed_tax = sum(cit_final.get(first40_pidx[k], 0.0) - cit_src.get(first40_pidx[k], 0.0) for k in range(n_first40))
    cfads_deltas = [abs(cfads_final.get(first40_pidx[k], 0.0) - cfads_src.get(first40_pidx[k], 0.0)) for k in range(n_first40)]
    signed_cfads = sum(cfads_final.get(first40_pidx[k], 0.0) - cfads_src.get(first40_pidx[k], 0.0) for k in range(n_first40))
    total_cfads = sum(cfads_final.get(idx, 0.0) for idx in first40_pidx)
    source_total_cfads = sum(cfads_src.values())

    sd_service_by_pidx = dict(zip(sd_result.period_indices, sd_result.senior_debt_service_keur))
    sd_deltas = [abs(sd_service_by_pidx.get(first40_pidx[k], 0.0) - sd_src.get(first40_pidx[k], 0.0)) for k in range(n_first40)]
    signed_sd = sum(sd_service_by_pidx.get(first40_pidx[k], 0.0) - sd_src.get(first40_pidx[k], 0.0) for k in range(n_first40))
    clean_debt = sd_result.diagnostics.final_debt_size_keur

    ds40_closing = shl_result.operating[-1].closing_balance_keur if shl_result.operating else 0.0
    shl_m = _collect_shl_metrics(shl_result, seam, source_fixture, grid0.ds40_final_closing_keur)

    return GridArmResult(
        arm_id=arm_id,
        arm_label=arm_label,
        source_evidence=source_evidence,
        config=config,
        surrogate_baseline="GRID-WS0",
        total_cash_tax_keur=total_cit,
        source_total_cash_tax_keur=10_443.088331999998,
        total_tax_delta_vs_source=signed_tax,
        max_period_tax_delta_vs_source=max(tax_deltas) if tax_deltas else 0.0,
        total_cfads_keur=total_cfads,
        source_total_cfads_keur=source_total_cfads,
        max_cfads_delta_vs_source=max(cfads_deltas) if cfads_deltas else 0.0,
        signed_total_cfads_delta=signed_cfads,
        clean_debt_size_keur=clean_debt,
        debt_size_delta_keur=clean_debt - SOURCE_DEBT_SIZE_KEUR,
        max_senior_ds_delta_vs_source=max(sd_deltas) if sd_deltas else 0.0,
        signed_total_senior_ds_delta=signed_sd,
        max_shl_cash_delta_vs_source=shl_m["max_shl_cash_delta_vs_source"],
        signed_total_shl_cash_delta=shl_m["signed_total_shl_cash_delta"],
        gross_interest_max_delta=shl_m["gross_interest_max_delta"],
        cash_interest_max_delta=shl_m["cash_interest_max_delta"],
        pik_max_delta=shl_m["pik_max_delta"],
        principal_max_delta=shl_m["principal_max_delta"],
        closing_max_delta=shl_m["closing_max_delta"],
        ds40_final_closing_keur=ds40_closing,
        delta_vs_grid0_final_closing=shl_m["delta_vs_grid0_final_closing"],
        convergence_iterations=sd_result.diagnostics.iteration_count,
        convergence_achieved=sd_result.diagnostics.converged,
        convergence_note=f"Solver: {sd_result.diagnostics.termination_reason}",
        solver_converged=sd_result.diagnostics.converged,
        solver_iterations=sd_result.diagnostics.iteration_count,
    )


def _build_phase2c_proxy(
    op_periods: tuple,
    cfads_by_pidx: dict[int, float],
    cash_tax_by_pidx: dict[int, float],
    sd_result,
    policy,
):
    """Build a minimal ProjectModelResult proxy for the SHL seam adapter.

    The seam adapter reads:
      - phase2c_result.periods -> for period indices and is_construction
      - phase2c_result.tax_and_cfads -> period_indices, cfads_keur
      - phase2c_result.senior_debt -> period_indices, senior_debt_service_keur

    This is DIAGNOSTIC ONLY -- not a production object.
    """
    class _TacProxy:
        def __init__(self, pidx, cfads):
            self.period_indices = tuple(pidx)
            self.cfads_keur = tuple(cfads)

    class _SdProxy:
        def __init__(self, sd):
            self.period_indices = sd.period_indices
            self.senior_debt_service_keur = sd.senior_debt_service_keur

    class _PeriodProxy:
        def __init__(self, period_index, is_construction):
            self.period_index = period_index
            self.is_construction = is_construction

    all_pidx = [p.period_index for p in op_periods]
    all_cfads = [cfads_by_pidx.get(p.period_index, 0.0) for p in op_periods]

    _periods = tuple(_PeriodProxy(p.period_index, p.is_construction) for p in op_periods)
    _tac = _TacProxy(all_pidx, all_cfads)
    _sd = _SdProxy(sd_result)

    class _Proxy:
        periods = _periods
        tax_and_cfads = _tac
        senior_debt = _sd

    return _Proxy()


def _get_shl_gross_from_grid0(source_fixture: dict) -> dict[int, float]:
    """Get SHL gross interest per operating period from GRID-0 SHL schedule.

    Used as fixed SHL gross for EBT computation in GRID-C/D/E arms.
    SHL is outside the debt fixed-point loop; using GRID-0 values is the
    correct first-order approximation (proved by GRID-A: SHL->tax effect = 0).
    """
    from app.project_factories import create_default_oborovo
    from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
    from financial_engine.orchestrator import run_senior_debt_model

    proj = create_default_oborovo()
    sd_input = build_senior_debt_model_input_from_project_inputs(
        proj, source_id="c3b3d2b2a-shl-gross"
    )
    phase2c = run_senior_debt_model(sd_input)
    shl_result, _ = _build_shl_schedule_from_phase2c(phase2c)

    gross_by_pidx: dict[int, float] = {}
    for op in shl_result.operating:
        gross_by_pidx[op.period_index] = op.gross_accrued_interest_keur
    return gross_by_pidx


# ---------------------------------------------------------------------------
# Main grid runner
# ---------------------------------------------------------------------------

def run_diagnostic_grid() -> DiagnosticGridResult:
    """Run the full C3B3D2B2A causal diagnostic grid.

    Returns DiagnosticGridResult with all arm results.
    Not a production engine call -- diagnostic only.

    Cause status: CURRENT_CAUSE_UNRESOLVED.
    Relative claims for B/C/D/E arms are vs GRID-WS0 baseline only.
    """
    fixture = _load_source_fixture()

    # GRID-0: canonical clean baseline (reproduces D2B1)
    grid0 = run_grid_0(fixture)

    # GRID-S0: canonical callback surrogate (must equiv GRID-0)
    grid_s0 = run_grid_s0(fixture, grid0)

    # GRID-WS0: workbook callback all-False surrogate (baseline for B/C/D/E)
    grid_ws0 = run_grid_ws0(fixture, grid0)

    # GRID-A: SHL feedback (typed execution; non-deductible -> analytically GRID-0)
    grid_a = run_grid_a(fixture, grid0)

    # Get fixed SHL gross for EBT computation in B/C/D/E arms
    shl_gross = _get_shl_gross_from_grid0(fixture)

    # Isolated single-mechanic arms (relative to GRID-WS0)
    grid_b = _run_workbook_arm(
        "GRID-B", "H2+H1 model-year CIT pairing only",
        "SOURCE_PROVEN: P&L row 43 WORKBOOK_COMPATIBILITY_PROFILE",
        WorkbookTaxConfig(h2h1_pairing=True),
        fixture, grid0, shl_gross,
    )
    grid_c = _run_workbook_arm(
        "GRID-C", "EBT gate for loss utilisation only",
        "SOURCE_PROVEN: P&L row 37 WORKBOOK_COMPATIBILITY_PROFILE",
        WorkbookTaxConfig(ebt_gate=True),
        fixture, grid0, shl_gross,
    )
    grid_d = _run_workbook_arm(
        "GRID-D", "Rolling 5-period loss window only",
        "SOURCE_PROVEN: P&L row 36 B36=5 WORKBOOK_COMPATIBILITY_PROFILE",
        WorkbookTaxConfig(rolling_window=True),
        fixture, grid0, shl_gross,
    )
    grid_e = _run_workbook_arm(
        "GRID-E", "Row-39 carriable-loss cap only",
        "SOURCE_PROVEN: P&L row 39 WORKBOOK_COMPATIBILITY_PROFILE",
        WorkbookTaxConfig(row39_cap=True),
        fixture, grid0, shl_gross,
    )

    # Two-way combinations
    grid_bc = _run_workbook_arm(
        "GRID-BC", "H2+H1 pairing + EBT gate",
        "SOURCE_PROVEN both (WORKBOOK_COMPATIBILITY_PROFILE)",
        WorkbookTaxConfig(h2h1_pairing=True, ebt_gate=True),
        fixture, grid0, shl_gross,
    )
    grid_bd = _run_workbook_arm(
        "GRID-BD", "H2+H1 pairing + rolling window",
        "SOURCE_PROVEN both (WORKBOOK_COMPATIBILITY_PROFILE)",
        WorkbookTaxConfig(h2h1_pairing=True, rolling_window=True),
        fixture, grid0, shl_gross,
    )
    grid_cd = _run_workbook_arm(
        "GRID-CD", "EBT gate + rolling window",
        "SOURCE_PROVEN both (WORKBOOK_COMPATIBILITY_PROFILE)",
        WorkbookTaxConfig(ebt_gate=True, rolling_window=True),
        fixture, grid0, shl_gross,
    )
    grid_bcd = _run_workbook_arm(
        "GRID-BCD", "H2+H1 + EBT gate + rolling window",
        "SOURCE_PROVEN all three (WORKBOOK_COMPATIBILITY_PROFILE)",
        WorkbookTaxConfig(h2h1_pairing=True, ebt_gate=True, rolling_window=True),
        fixture, grid0, shl_gross,
    )
    grid_abcd = _run_workbook_arm(
        "GRID-ABCD", "SHL feedback + H2+H1 + EBT gate + rolling window",
        (
            "SOURCE_PROVEN: A=non-deductible (zero TI effect, FIXED_POINT_COLLAPSES_ANALYTICALLY_TO_IDENTITY_FOR_OBOROVO). "
            "GRID-ABCD derived from BCD with A=0 identity. shl_netting_in_tax=True reflects A wiring."
        ),
        WorkbookTaxConfig(h2h1_pairing=True, ebt_gate=True, rolling_window=True, shl_netting_in_tax=True),
        fixture, grid0, shl_gross,
    )
    grid_abcde = _run_workbook_arm(
        "GRID-ABCDE", "All source-proven mechanics including row39 cap",
        "SOURCE_PROVEN: A/B/C/D/E all source-proven (WORKBOOK_COMPATIBILITY_PROFILE)",
        WorkbookTaxConfig(h2h1_pairing=True, ebt_gate=True, rolling_window=True, row39_cap=True,
                          shl_netting_in_tax=True),
        fixture, grid0, shl_gross,
    )

    return DiagnosticGridResult(
        grid0=grid0,
        grid_s0=grid_s0,
        grid_ws0=grid_ws0,
        grid_a=grid_a,
        grid_b=grid_b,
        grid_c=grid_c,
        grid_d=grid_d,
        grid_e=grid_e,
        grid_bc=grid_bc,
        grid_bd=grid_bd,
        grid_cd=grid_cd,
        grid_bcd=grid_bcd,
        grid_abcd=grid_abcd,
        grid_abcde=grid_abcde,
    )


# ---------------------------------------------------------------------------
# Causal attribution table
# ---------------------------------------------------------------------------

def format_causal_attribution_table(result: DiagnosticGridResult) -> str:
    """Format the causal attribution table for reporting.

    Cause status: CURRENT_CAUSE_UNRESOLVED.
    Relative claims for B/C/D/E are vs GRID-WS0 (surrogate_baseline field).
    """
    header = (
        f"{'Grid':<12} {'Tax Delta (kEUR)':>16} {'Debt-size Delta':>15} "
        f"{'SHL cash Delta':>14} {'Final SHL closing':>18} {'Baseline':<10} {'Interpretation'}"
    )
    sep = "-" * 115
    rows = [header, sep]

    for arm in result.all_arms():
        row = (
            f"{arm.arm_id:<12} "
            f"{arm.total_tax_delta_vs_source:>+16.1f} "
            f"{arm.debt_size_delta_keur:>+15.1f} "
            f"{arm.signed_total_shl_cash_delta:>+14.1f} "
            f"{arm.ds40_final_closing_keur:>18.2f} "
            f"{arm.surrogate_baseline:<10} "
            f"{arm.arm_label}"
        )
        rows.append(row)

    rows.append(sep)
    rows.append("Cause status: CURRENT_CAUSE_UNRESOLVED. DSRA_ORDERING_UNRESOLVED.")
    return "\n".join(rows)
