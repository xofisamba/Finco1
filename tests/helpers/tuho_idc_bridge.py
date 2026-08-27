"""
TUHO IDC counterfactual bridge diagnostic helper.

VALIDATION-ONLY — NOT A RUNTIME INPUT.
Classification: CONSTRUCTION_FINANCING_METHOD_TIMING_DIFFERENCE

This module computes the ordered sequential counterfactual bridge that
decomposes the +31.924 kEUR delta between TUHO source live IDC and Finco
clean capitalized IDC into two economic components.

Source evidence provenance
--------------------------
Classification: SOURCE_WORKBOOK_EVIDENCE

Source workbook: 20260330_TUHO_BP.xlsm
SHA-256: 780779eba4278ccc2b8546a9411ccee24917d388f411ba60c88aa342cb5c727a

Source Senior IDC mechanics (verified from IDC sheet, Inputs/Senior Debt area):
  - All-in IDC rate: 3.30% (Fixed Base Rate) + 2.65% (IDC Margin) = 5.95%
  - Fixed Base Rate (IDC!cell): 3.30%
  - Blended Base Rate (IDC!cell): 3.30%
  - IDC Margin (IDC!cell): 2.65%
  - Day count: ACT/360 inclusive — (end - start).days + 1 / 360
  - Balance basis: CLOSING (current-period closing balance including the period draw)
  - Capitalization timing: periods t=0..n-2 are capitalized (last raw period excluded)

Source formula (per construction period):
  IDC[t] = CLOSING_BALANCE[t] × 5.95% × (actual_days_inclusive / 360)
  where CLOSING_BALANCE[t] = cumulative Senior drawn at END of period t

Proof examples (from IDC/Funding sheets):
  Period Aug 2028 (t=2, closing=181.234932551790 kEUR, 31 incl days):
    IDC = 181.234932551790 × 0.0595 × 31/360 = 0.928577314143823 kEUR
  Period Sep 2028 (t=3, closing=2,985.959586355897 kEUR, 30 incl days):
    IDC = 2,985.959586355897 × 0.0595 × 30/360 = 14.805382949014653 kEUR
  Period Oct 2028 (t=4, closing=5,802.792725860847 kEUR, 31 incl days):
    IDC = 5,802.792725860847 × 0.0595 × 31/360 = 29.731253285695367 kEUR

Source live total (IDC row-sum, circularity-inclusive): 1,520.3051321075397 kEUR
Source pasted total (IDC!D57 snapshot):                 1,519.563935502677 kEUR
Source circularity residual (live − pasted):           +0.741196604863 kEUR
  → The circularity residual is a workbook recalculation artifact, NOT a
    Finco model error or bridge residual.

The legacy calibrated rate (6.0454449%) in domain/construction/templates/tuho.py
is a LEGACY_CALIBRATED_DIAGNOSTIC: it reproduced the pasted total (not live)
using 1/12 monthly DCF. It is NOT used in this bridge.

Clean mechanics provenance
--------------------------
Clean mechanics are read from the typed ConstructionFinancingInput passed to
the B3 production run (create_default_tuho_wind1 → run_clean_production).
No constants are duplicated here.

Clean mechanics (per typed inputs):
  - Rate mode: FIXED_PLUS_MARGIN (fixed_base_rate=0.033, margin_rate=0.0265)
  - All-in rate: 5.95% (same as source)
  - Day count: ACT_360 inclusive (same as source)
  - Balance basis: CLOSING_DRAWN / CURRENT_CLOSING_DRAWN (same as source)
  - Capitalization timing: NEXT_PERIOD (cap[t]=raw[t-1], cap[0]=0)

Because source and clean share the same rate, day-count, and balance-basis
mechanics, the bridge has only two active components:
  ΔS1 — Senior quantum difference (source 43,359.274 → clean 43,789.921 kEUR)
  ΔS2 — Draw profile difference (SHL-first allocation → CAPEX-weighted)

No balance-basis component (both CLOSING).
No DCF/rate component (both 5.95% ACT/360 inclusive).
No NEXT_PERIOD timing component (both exclude terminal raw period from cap).

Bridge order (S0 → S3)
-----------------------
  S0  Source LIVE IDC (workbook authority: 5.95%, CLOSING, ACT/360 incl,
      source current-period recognition, last period excluded)
  S1  Change: Senior quantum → clean quantum (scale source draws proportionally)
  S2  Change: Draw profile → clean CAPEX-weighted draws (source current-period
      recognition retained — not yet NEXT_PERIOD)
  S3  TIMING RECLASSIFICATION: transform from source current-period recognition
      to clean NEXT_PERIOD recognition.
      Aggregate monetary effect: sum(S3) - sum(S2) = 0.000 kEUR (exactly zero —
      same raw values shifted one period; IDC_PERIOD_TIMING_RECLASSIFICATION_ZERO_AGGREGATE_EFFECT)
      Period-level effect: material redistribution between adjacent periods
      (S3_period_vector != S2_period_vector for periods 0..n-1)
      S3_period_vector = recomputed_clean_cap_idc (independently verified)

Production modules (financial_engine, finco_core, app, domain) MUST NOT import this.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TuhoIdcBridge:
    """Ordered sequential counterfactual bridge result.

    All monetary values in kEUR.
    Component attribution is bridge-order-dependent (see module docstring).
    """
    # Workbook anchors
    source_pasted_idc_keur: float    # IDC!D57 snapshot (circularity-free)
    source_circularity_residual_keur: float  # SOURCE_LIVE - SOURCE_PASTED (≈ +0.741)
    source_live_idc_keur: float      # workbook row-sum authority
    clean_capitalized_idc_keur: float   # runtime authority

    # Sequential component deltas
    senior_quantum_effect_keur: float   # ΔS1: source→clean Senior quantum
    draw_profile_effect_keur: float     # ΔS2: source SHL-first → clean CAPEX-weighted

    # Non-tautological residuals
    # source_reconstruction_residual = reconstructed_source_live − workbook_source_live
    #   (≈ +0.000038 kEUR; small due to rounded domain draws vs workbook precision)
    source_reconstruction_residual_keur: float
    # source_circularity_residual = SOURCE_LIVE − SOURCE_PASTED (≈ +0.741 kEUR)
    #   → NOT a reconstruction error; explicit workbook artifact
    # clean_raw_reconstruction_residual = sum(recomputed_clean_raw) − sum(runtime_clean_raw)
    #   (must be < 0.001 kEUR)
    clean_raw_reconstruction_residual_keur: float
    # clean_cap_reconstruction_residual = sum(recomputed_clean_cap) − sum(runtime_clean_cap)
    #   (must be < 0.001 kEUR)
    clean_cap_reconstruction_residual_keur: float
    # bridge_unexplained_residual = S3 − sum(runtime_clean_cap)
    #   (must be < 0.001 kEUR; S3 is independently reconstructed via S2_raw → NEXT_PERIOD,
    #    not copied from runtime — non-tautological)
    bridge_unexplained_residual_keur: float

    # Timing reclassification (S2 → S3)
    # S2 uses source current-period recognition (cap[t]=raw[t], last=0)
    # S3 applies NEXT_PERIOD transformation (cap[t]=raw[t-1], cap[0]=0)
    # Proof: sum(S3) - sum(S2) = 0 exactly (same included raw values, shifted one period)
    # But S3_period_vector != S2_period_vector (material period-by-period redistribution)
    # S3_period_vector == recomputed_clean_cap_idc (reproduces clean NEXT_PERIOD vector)
    timing_aggregate_effect_keur: float   # S3 - S2; exactly 0.0
    s2_period_vector: tuple[float, ...]   # source current-period recognition
    s3_period_vector: tuple[float, ...]   # NEXT_PERIOD recognition (= recomputed_clean_cap)

    # Intermediate state totals
    s0_keur: float   # reconstructed source live (≈ SOURCE_LIVE)
    s1_keur: float   # scaled to clean Senior quantum
    s2_keur: float   # clean draw profile, source current-period recognition
    s3_keur: float   # timing reclassification to NEXT_PERIOD (= S2, zero aggregate delta)

    # Period-level data
    source_period_draws_keur: tuple[float, ...]
    source_period_idc_keur: tuple[float, ...]    # workbook-proven (CLOSING, 5.95%, ACT/360)
    clean_period_draws_keur: tuple[float, ...]
    recomputed_clean_raw_idc_keur: tuple[float, ...]   # from typed inputs
    recomputed_clean_cap_idc_keur: tuple[float, ...]   # from typed inputs + NEXT_PERIOD
    runtime_clean_raw_idc_keur: tuple[float, ...]      # engine output authority
    runtime_clean_cap_idc_keur: tuple[float, ...]      # engine output authority
    source_period_dcf: tuple[float, ...]   # ACT/360 incl (workbook-proven convention)
    clean_period_dcf: tuple[float, ...]    # ACT/360 incl (typed input convention)

    # Mechanics classification
    source_rate_provenance: str    # "SOURCE_WORKBOOK_EVIDENCE"
    source_workbook_rate: float    # 0.0595 (3.30% base + 2.65% margin)
    source_balance_basis: str      # "CLOSING"
    source_dcf_convention: str     # "ACT_360_INCLUSIVE"
    source_cap_timing: str         # "EXCL_TERMINAL_PERIOD"
    clean_rate_declared: float     # 0.0595 from typed inputs (same as source)
    clean_balance_basis: str       # "CURRENT_CLOSING_DRAWN" (same as source)
    clean_dcf_convention: str      # "ACT_360_INCLUSIVE" (same as source)
    clean_cap_timing: str          # "NEXT_PERIOD" (same as source)


@dataclass(frozen=True)
class PeriodDivergence:
    """First material IDC divergence between source and clean."""
    period_index: int
    period_start: object
    period_end: object
    source_senior_draw_keur: float
    clean_senior_draw_keur: float
    source_opening_balance_keur: float
    source_closing_balance_keur: float
    clean_opening_balance_keur: float
    clean_closing_balance_keur: float
    source_dcf: float
    clean_dcf: float
    source_period_idc_keur: float    # SOURCE_WORKBOOK_EVIDENCE
    clean_cap_period_idc_keur: float
    delta_keur: float
    causal_reason: str


def _compute_idc_vector(
    draws: list[float],
    rate: float,
    period_starts: tuple,
    period_ends: tuple,
) -> tuple[float, ...]:
    """CLOSING × rate × ACT/360_incl / 360, last period set to 0 (excluded from cap)."""
    cumul = 0.0
    result: list[float] = []
    for t in range(len(draws)):
        s, e = period_starts[t], period_ends[t]
        days_incl = (e - s).days + 1 if (e - s).days > 0 else 0
        closing = cumul + draws[t]
        result.append(closing * rate * days_incl / 360.0)
        cumul = closing
    # Exclude last period from capitalized IDC (same terminal exclusion as clean NEXT_PERIOD)
    result[-1] = 0.0
    return tuple(result)


def compute_tuho_idc_counterfactual_bridge(
    b3_uses_data: tuple,
) -> TuhoIdcBridge:
    """Compute the ordered sequential counterfactual IDC bridge.

    Arguments
    ---------
    b3_uses_data : tuple
        (project_uses, construction_financing_result) from the clean B3 run.
        Used as the clean authority for Senior draws, raw IDC, and cap IDC.

    Returns
    -------
    TuhoIdcBridge
        Fully-computed bridge with workbook-proven source mechanics.
    """
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

    # --- SOURCE EVIDENCE (SOURCE_WORKBOOK_EVIDENCE) ---
    # Rate: 5.95% all-in = 3.30% Fixed Base Rate + 2.65% IDC Margin
    # (verified from IDC sheet / Senior Debt Inputs in 20260330_TUHO_BP.xlsm)
    # Day count: ACT/360 inclusive (verified from IDC sheet formula)
    # Balance: CLOSING (verified: IDC[t] = closing_balance[t] × rate × dcf[t])
    # Termination: last raw period excluded from capitalized IDC
    from domain.construction.templates.tuho import build_tuho_construction_config
    from domain.construction.capex_schedule import build_monthly_uses
    from domain.construction.funding_allocation import allocate_source_waterfall

    src_config = build_tuho_construction_config()
    src_entries = allocate_source_waterfall(
        build_monthly_uses(src_config), src_config.funding_caps, tolerance_keur=0.05
    )

    SOURCE_RATE: float = 0.0595          # SOURCE_WORKBOOK_EVIDENCE: 3.30% + 2.65%
    SOURCE_RATE_PROVENANCE: str = "SOURCE_WORKBOOK_EVIDENCE"
    SOURCE_BALANCE_BASIS: str = "CLOSING"
    SOURCE_DCF_CONVENTION: str = "ACT_360_INCLUSIVE"
    SOURCE_CAP_TIMING: str = "EXCL_TERMINAL_PERIOD"
    SOURCE_PASTED: float = 1_519.563935502677    # IDC!D57 snapshot
    SOURCE_LIVE: float = 1_520.3051321075397     # IDC row-sum (circularity-inclusive)
    SOURCE_CIRCULARITY: float = SOURCE_LIVE - SOURCE_PASTED
    SOURCE_QUANTUM: float = 43_359.274           # total source Senior draws
    SOURCE_DRAWS: list[float] = [e.senior_draw_keur for e in src_entries]

    # --- CLEAN DATA (B3 production run, canonical authority) ---
    _pu, cfr = b3_uses_data
    CLEAN_DRAWS: tuple[float, ...] = cfr.senior_draws_keur
    CLEAN_SENIOR: float = cfr.final_senior_commitment_keur
    RUNTIME_CLEAN_RAW: tuple[float, ...] = cfr.senior_idc_accrual_keur
    RUNTIME_CLEAN_CAP: tuple[float, ...] = cfr.senior_idc_capitalized_uses_keur
    period_starts = cfr.period_start_dates
    period_ends = cfr.period_end_dates
    n = len(CLEAN_DRAWS)

    # --- CLEAN MECHANICS FROM TYPED RUNTIME CONFIG ---
    # Read from the actual ConstructionFinancingInput used by the B3 production run.
    # These values are not duplicated here — they are derived from the engine.
    from app.project_factories import create_default_tuho_wind1
    from finco_core.inputs.senior_rate_schedule import SeniorRateMode
    _proj = create_default_tuho_wind1()
    _pricing = _proj.financing.construction_financing.senior_pricing
    assert _pricing.mode == SeniorRateMode.FIXED_PLUS_MARGIN, (
        f"Expected FIXED_PLUS_MARGIN, got {_pricing.mode}"
    )
    CLEAN_RATE_DECLARED: float = _pricing.fixed_base_rate + _pricing.margin_rate
    CLEAN_BALANCE_BASIS: str = _proj.financing.construction_financing.idc_balance_basis
    CLEAN_CAP_TIMING: str = _proj.financing.construction_financing.idc_capitalization_timing
    CLEAN_DCF_CONVENTION: str = str(_pricing.day_count.value).upper()

    # Period DCF fractions (ACT/360 inclusive) — same for source and clean
    PERIOD_DCF: tuple[float, ...] = tuple(
        ((e - s).days + 1) / 360.0 if (e - s).days > 0 else 0.0
        for s, e in zip(period_starts, period_ends)
    )

    # --- SOURCE PERIOD IDC VECTOR (workbook-proven formula) ---
    SOURCE_PERIOD_IDC: tuple[float, ...] = _compute_idc_vector(
        SOURCE_DRAWS, SOURCE_RATE, period_starts, period_ends
    )

    # Source reconstruction residual
    source_reconstruction_residual = sum(SOURCE_PERIOD_IDC) - SOURCE_LIVE

    # --- CLEAN RECONSTRUCTION FROM TYPED INPUTS ---
    cumul = 0.0
    recomp_raw: list[float] = []
    for t in range(n):
        closing = cumul + CLEAN_DRAWS[t]
        recomp_raw.append(closing * CLEAN_RATE_DECLARED * PERIOD_DCF[t])
        cumul = closing
    RECOMP_CLEAN_RAW: tuple[float, ...] = tuple(recomp_raw)
    RECOMP_CLEAN_CAP: tuple[float, ...] = (0.0,) + RECOMP_CLEAN_RAW[:-1]

    clean_raw_reconstruction_residual = sum(RECOMP_CLEAN_RAW) - sum(RUNTIME_CLEAN_RAW)
    clean_cap_reconstruction_residual = sum(RECOMP_CLEAN_CAP) - sum(RUNTIME_CLEAN_CAP)

    # --- SEQUENTIAL BRIDGE STATES ---
    # S0: source live IDC (workbook authority — reconstructed)
    S0 = sum(SOURCE_PERIOD_IDC)

    # S1: scale source draws to clean Senior quantum (keep source mechanics)
    scale = CLEAN_SENIOR / SOURCE_QUANTUM
    S1_draws = [d * scale for d in SOURCE_DRAWS]
    S1_vec = _compute_idc_vector(S1_draws, SOURCE_RATE, period_starts, period_ends)
    S1 = sum(S1_vec)

    # S2: switch to clean CAPEX-weighted draw profile
    # Same rate (5.95%), same day count (ACT/360 incl), same balance basis (CLOSING)
    # S2 retains SOURCE current-period recognition (cap[t]=raw[t], last excluded)
    S2_vec = _compute_idc_vector(list(CLEAN_DRAWS), SOURCE_RATE, period_starts, period_ends)
    S2 = sum(S2_vec)

    # S3: TIMING RECLASSIFICATION — transform S2 from source current-period recognition
    # to clean NEXT_PERIOD recognition (cap[t] = raw[t-1], cap[0] = 0)
    # Proof of zero aggregate effect:
    #   S2 sums raw[0..n-2] (terminal period excluded by source convention)
    #   S3 sums raw[0..n-2] shifted one period right = same values, different distribution
    #   Therefore sum(S3) - sum(S2) = 0 exactly (period redistribution, not a monetary delta)
    # Compute S2 raw (without terminal zeroing) to derive S3:
    cumul_s2 = 0.0
    s2_raw: list[float] = []
    for t in range(n):
        s, e = period_starts[t], period_ends[t]
        days_incl = (e - s).days + 1 if (e - s).days > 0 else 0
        closing = cumul_s2 + list(CLEAN_DRAWS)[t]
        s2_raw.append(closing * SOURCE_RATE * days_incl / 360.0)
        cumul_s2 = closing
    S3_vec = (0.0,) + tuple(s2_raw[:-1])  # NEXT_PERIOD of S2_raw
    S3 = sum(S3_vec)
    timing_aggregate_effect = S3 - S2  # must be exactly 0.0

    # Components
    delta1 = S1 - S0   # Senior quantum effect
    delta2 = S2 - S1   # draw profile effect
    # delta3 = S3 - S2 = 0 (timing reclassification — zero aggregate, non-zero period)

    # Non-tautological: S3 independently reproduces clean NEXT_PERIOD capitalized IDC.
    # S3 is computed from S2_raw (not copied from runtime output).
    bridge_unexplained_residual = S3 - sum(RUNTIME_CLEAN_CAP)

    return TuhoIdcBridge(
        source_pasted_idc_keur=SOURCE_PASTED,
        source_circularity_residual_keur=SOURCE_CIRCULARITY,
        source_live_idc_keur=SOURCE_LIVE,
        clean_capitalized_idc_keur=sum(RUNTIME_CLEAN_CAP),
        senior_quantum_effect_keur=delta1,
        draw_profile_effect_keur=delta2,
        timing_aggregate_effect_keur=timing_aggregate_effect,
        s2_period_vector=S2_vec,
        s3_period_vector=S3_vec,
        source_reconstruction_residual_keur=source_reconstruction_residual,
        clean_raw_reconstruction_residual_keur=clean_raw_reconstruction_residual,
        clean_cap_reconstruction_residual_keur=clean_cap_reconstruction_residual,
        bridge_unexplained_residual_keur=bridge_unexplained_residual,
        s0_keur=S0,
        s1_keur=S1,
        s2_keur=S2,
        s3_keur=S3,
        source_period_draws_keur=tuple(SOURCE_DRAWS),
        source_period_idc_keur=SOURCE_PERIOD_IDC,
        clean_period_draws_keur=CLEAN_DRAWS,
        recomputed_clean_raw_idc_keur=RECOMP_CLEAN_RAW,
        recomputed_clean_cap_idc_keur=RECOMP_CLEAN_CAP,
        runtime_clean_raw_idc_keur=RUNTIME_CLEAN_RAW,
        runtime_clean_cap_idc_keur=RUNTIME_CLEAN_CAP,
        source_period_dcf=PERIOD_DCF,
        clean_period_dcf=PERIOD_DCF,
        source_rate_provenance=SOURCE_RATE_PROVENANCE,
        source_workbook_rate=SOURCE_RATE,
        source_balance_basis=SOURCE_BALANCE_BASIS,
        source_dcf_convention=SOURCE_DCF_CONVENTION,
        source_cap_timing=SOURCE_CAP_TIMING,
        clean_rate_declared=CLEAN_RATE_DECLARED,
        clean_balance_basis=CLEAN_BALANCE_BASIS,
        clean_dcf_convention=CLEAN_DCF_CONVENTION,
        clean_cap_timing=CLEAN_CAP_TIMING,
    )


def find_first_material_period_divergence(
    bridge: TuhoIdcBridge,
    *,
    period_start_dates: tuple = (),
    period_end_dates: tuple = (),
    materiality_threshold_keur: float = 0.5,
) -> PeriodDivergence:
    """Find the first period where clean cap IDC diverges materially from source IDC.

    Compares `recomputed_clean_cap_idc_keur[t]` vs `source_period_idc_keur[t]`.

    Parameters
    ----------
    bridge : TuhoIdcBridge
        Computed bridge result.
    period_start_dates : tuple, optional
        Period start dates from clean cfr.
    period_end_dates : tuple, optional
        Period end dates from clean cfr.
    materiality_threshold_keur : float
        Threshold below which delta is considered immaterial. Default 0.5 kEUR.
    """
    src_draws = bridge.source_period_draws_keur
    cln_draws = bridge.clean_period_draws_keur
    src_idc = bridge.source_period_idc_keur
    cap_idc = bridge.recomputed_clean_cap_idc_keur

    n = len(src_draws)
    starts = period_start_dates if period_start_dates else tuple(None for _ in range(n))
    ends = period_end_dates if period_end_dates else tuple(None for _ in range(n))

    src_open = 0.0
    src_opens: list[float] = []
    src_closes: list[float] = []
    for draw in src_draws:
        src_opens.append(src_open)
        src_open += draw
        src_closes.append(src_open)

    cln_open = 0.0
    cln_opens: list[float] = []
    cln_closes: list[float] = []
    for draw in cln_draws:
        cln_opens.append(cln_open)
        cln_open += draw
        cln_closes.append(cln_open)

    dcf = bridge.source_period_dcf

    for t in range(n):
        delta = cap_idc[t] - src_idc[t]
        if abs(delta) >= materiality_threshold_keur:
            return PeriodDivergence(
                period_index=t,
                period_start=starts[t],
                period_end=ends[t],
                source_senior_draw_keur=src_draws[t],
                clean_senior_draw_keur=cln_draws[t],
                source_opening_balance_keur=src_opens[t],
                source_closing_balance_keur=src_closes[t],
                clean_opening_balance_keur=cln_opens[t],
                clean_closing_balance_keur=cln_closes[t],
                source_dcf=dcf[t],
                clean_dcf=dcf[t],
                source_period_idc_keur=src_idc[t],
                clean_cap_period_idc_keur=cap_idc[t],
                delta_keur=delta,
                causal_reason=(
                    "CONSTRUCTION_FINANCING_METHOD_TIMING_DIFFERENCE: "
                    "Source Senior draws (SHL-first waterfall) produce a smaller "
                    "closing balance in early periods than clean (CAPEX-weighted). "
                    "Clean NEXT_PERIOD capitalization (cap[t]=raw[t-1]) means the "
                    "first period's raw IDC is not capitalized until the next period. "
                    "Source and clean share the same rate (5.95%), day count (ACT/360 "
                    "inclusive), and balance basis (CLOSING). "
                    "Rate/DCF provenance: SOURCE_WORKBOOK_EVIDENCE."
                ),
            )

    raise AssertionError("No material divergence found — unexpected for TUHO")


__all__ = [
    "TuhoIdcBridge",
    "PeriodDivergence",
    "compute_tuho_idc_counterfactual_bridge",
    "find_first_material_period_divergence",
]
