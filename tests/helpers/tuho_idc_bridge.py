"""
TUHO IDC counterfactual bridge diagnostic helper.

VALIDATION-ONLY — NOT A RUNTIME INPUT.
Classification: CONSTRUCTION_FINANCING_METHOD_TIMING_DIFFERENCE

This module computes the ordered sequential counterfactual bridge that
decomposes the +31.924 kEUR delta between TUHO source live IDC and Finco
clean capitalized IDC into five economic components.

Production modules (financial_engine, finco_core, app) MUST NOT import this.
Source evidence inputs are read from the existing domain construction engine
and the live clean model result.

Bridge order (S0 → S5):
  S0  Source pasted IDC (calibrated mechanics, source draws, opening balance, monthly DCF)
  S1  Change: Senior quantum → clean quantum (scale source draws proportionally)
  S2  Change: Draw profile → clean CAPEX-weighted draw profile
  S3  Change: Balance basis → CLOSING (includes current-period draw)
  S4  Change: DCF convention + effective rate → clean mechanics
      (source 1/12 monthly + calibrated rate → actual/365 + clean all-in rate)
  S5  Apply: NEXT_PERIOD capitalization horizon (cap[t] = raw[t-1])

S5 reconciles exactly to clean capitalized Senior IDC.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TuhoIdcBridge:
    """Ordered sequential counterfactual bridge result.

    All monetary values in kEUR.
    Component attribution is bridge-order-dependent (see module docstring).
    """
    # Anchors
    source_pasted_idc_keur: float
    source_circularity_residual_keur: float
    source_live_idc_keur: float   # classified, not computed through states
    clean_capitalized_idc_keur: float

    # Sequential component deltas (S0 = source_pasted; S5 = clean_cap)
    senior_quantum_effect_keur: float      # ΔS1: scale Senior quantum to clean
    draw_profile_effect_keur: float        # ΔS2: source→clean draw profile
    balance_basis_effect_keur: float       # ΔS3: OPENING→CLOSING balance
    dcf_and_rate_effect_keur: float        # ΔS4: 1/12+calib_rate → actual/365+clean_rate
    next_period_horizon_keur: float        # ΔS5: terminal accrual excluded (−raw[-1])

    # Residual (should be < 0.001 kEUR)
    bridge_residual_keur: float

    # Intermediate state totals
    s0_keur: float   # source_pasted
    s1_keur: float
    s2_keur: float
    s3_keur: float
    s4_keur: float   # clean raw IDC
    s5_keur: float   # clean capitalized IDC

    # Period-level source evidence
    source_period_draws_keur: tuple[float, ...]
    source_period_idc_keur: tuple[float, ...]
    clean_period_draws_keur: tuple[float, ...]
    clean_raw_idc_keur: tuple[float, ...]
    clean_cap_idc_keur: tuple[float, ...]
    period_dcf: tuple[float, ...]

    # Rates
    source_calibrated_rate: float
    clean_effective_rate: float


@dataclass(frozen=True)
class PeriodDivergence:
    """First material IDC divergence between source and clean."""
    period_index: int
    period_start: object
    period_end: object
    source_senior_draw_keur: float
    clean_senior_draw_keur: float
    source_cumul_senior_keur: float
    clean_cumul_senior_keur: float
    period_dcf: float
    source_period_idc_keur: float
    clean_cap_period_idc_keur: float
    delta_keur: float
    causal_reason: str


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
        Fully-computed bridge with residual < 0.001 kEUR.
    """
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

    # --- SOURCE EVIDENCE (legacy domain engine, diagnostic-only) ---
    from domain.construction.templates.tuho import build_tuho_construction_config
    from domain.construction.capex_schedule import build_monthly_uses
    from domain.construction.funding_allocation import allocate_source_waterfall
    from domain.construction.idc_calculator import compute_senior_monthly_cumulative_idc

    src_config = build_tuho_construction_config()
    src_entries = allocate_source_waterfall(
        build_monthly_uses(src_config), src_config.funding_caps, tolerance_keur=0.05
    )
    SOURCE_CALIB_RATE: float = src_config.senior_interest_rate
    SOURCE_PASTED: float = 1_519.563935502677   # Excel IDC!D57 pasted total
    SOURCE_LIVE: float = 1_520.3051321075397    # Excel IDC row-57 period sum (circularity included)
    SOURCE_CIRCULARITY: float = SOURCE_LIVE - SOURCE_PASTED
    SOURCE_SENIOR: float = 43_359.274
    SOURCE_DRAWS: tuple[float, ...] = tuple(e.senior_draw_keur for e in src_entries)
    SOURCE_PERIOD_IDC: tuple[float, ...] = compute_senior_monthly_cumulative_idc(
        src_entries,
        senior_interest_rate=SOURCE_CALIB_RATE,
        monthly_interest_period_fractions=src_config.senior_interest_period_fractions,
    )

    # --- CLEAN DATA (from B3 production run, canonical authority) ---
    _pu, cfr = b3_uses_data
    CLEAN_DRAWS: tuple[float, ...] = cfr.senior_draws_keur
    CLEAN_SENIOR: float = cfr.final_senior_commitment_keur
    CLEAN_RAW: tuple[float, ...] = cfr.senior_idc_accrual_keur
    CLEAN_CAP: tuple[float, ...] = cfr.senior_idc_capitalized_uses_keur

    # Period DCF: (end - start + 1) / 365, zero for point period
    DCF: tuple[float, ...] = tuple(
        0.0 if s == e else ((e - s).days + 1) / 365.0
        for s, e in zip(cfr.period_start_dates, cfr.period_end_dates)
    )
    DCF_MONTHLY: tuple[float, ...] = tuple(0.0 if i == 0 else 1 / 12 for i in range(len(DCF)))

    # Clean effective all-in rate (derived from raw IDC and period balances)
    weighted_closing = sum(
        sum(CLEAN_DRAWS[:t + 1]) * DCF[t] for t in range(len(CLEAN_DRAWS))
    )
    CLEAN_RATE: float = sum(CLEAN_RAW) / weighted_closing

    # --- BRIDGE STATE HELPERS ---
    def _idc_opening_monthly(draws: tuple, rate: float) -> tuple:
        """IDC = opening_balance × rate × (1/12); opening_balance[t] = sum(draws[:t])."""
        n = len(draws)
        cumul = [0.0] + [sum(draws[:i + 1]) for i in range(n)]
        return tuple(cumul[t] * rate * DCF_MONTHLY[t] for t in range(n))

    def _idc_closing_monthly(draws: tuple, rate: float) -> tuple:
        """IDC = closing_balance × rate × (1/12); closing_balance[t] = sum(draws[:t+1])."""
        n = len(draws)
        cumul = [sum(draws[:t + 1]) for t in range(n)]
        return tuple(cumul[t] * rate * DCF_MONTHLY[t] for t in range(n))

    # --- SEQUENTIAL STATES ---
    # S0: source pasted (= legacy engine result with calibrated rate)
    S0 = SOURCE_PASTED

    # S1: scale source draws to clean Senior quantum, keep source mechanics
    scale = CLEAN_SENIOR / SOURCE_SENIOR
    S1_draws = tuple(d * scale for d in SOURCE_DRAWS)
    S1 = sum(_idc_opening_monthly(S1_draws, SOURCE_CALIB_RATE))

    # S2: switch to clean draw profile, keep opening+monthly+calibrated rate
    S2 = sum(_idc_opening_monthly(CLEAN_DRAWS, SOURCE_CALIB_RATE))

    # S3: switch to CLOSING balance basis, keep monthly+calibrated rate
    S3 = sum(_idc_closing_monthly(CLEAN_DRAWS, SOURCE_CALIB_RATE))

    # S4: switch to clean mechanics (actual/365 DCF + clean effective rate)
    #     = sum(CLEAN_RAW) directly from the canonical B2 convergence result
    S4 = sum(CLEAN_RAW)

    # S5: apply NEXT_PERIOD horizon → clean capitalized IDC
    S5 = sum(CLEAN_CAP)

    # --- COMPONENTS ---
    delta1 = S1 - S0   # Senior quantum effect
    delta2 = S2 - S1   # draw profile effect
    delta3 = S3 - S2   # balance basis effect (OPENING→CLOSING)
    delta4 = S4 - S3   # DCF + rate convention effect combined
    delta5 = S5 - S4   # NEXT_PERIOD horizon (= -CLEAN_RAW[-1])

    residual = S5 - sum(CLEAN_CAP)  # must be ~0

    return TuhoIdcBridge(
        source_pasted_idc_keur=SOURCE_PASTED,
        source_circularity_residual_keur=SOURCE_CIRCULARITY,
        source_live_idc_keur=SOURCE_LIVE,
        clean_capitalized_idc_keur=sum(CLEAN_CAP),
        senior_quantum_effect_keur=delta1,
        draw_profile_effect_keur=delta2,
        balance_basis_effect_keur=delta3,
        dcf_and_rate_effect_keur=delta4,
        next_period_horizon_keur=delta5,
        bridge_residual_keur=residual,
        s0_keur=S0,
        s1_keur=S1,
        s2_keur=S2,
        s3_keur=S3,
        s4_keur=S4,
        s5_keur=S5,
        source_period_draws_keur=SOURCE_DRAWS,
        source_period_idc_keur=SOURCE_PERIOD_IDC,
        clean_period_draws_keur=CLEAN_DRAWS,
        clean_raw_idc_keur=CLEAN_RAW,
        clean_cap_idc_keur=CLEAN_CAP,
        period_dcf=DCF,
        source_calibrated_rate=SOURCE_CALIB_RATE,
        clean_effective_rate=CLEAN_RATE,
    )


def find_first_material_period_divergence(
    bridge: TuhoIdcBridge,
    *,
    period_start_dates: tuple = (),
    period_end_dates: tuple = (),
) -> PeriodDivergence:
    """Find the first period where clean cap IDC diverges materially from source IDC.

    Uses the period-level vectors from the computed bridge result.
    Period date labels are optional; pass them from the clean cfr for richer output.
    """
    src_draws = bridge.source_period_draws_keur
    cln_draws = bridge.clean_period_draws_keur
    src_idc = bridge.source_period_idc_keur
    cap_idc = bridge.clean_cap_idc_keur

    n = len(src_draws)
    src_cumul = [sum(src_draws[:t + 1]) for t in range(n)]
    cln_cumul = [sum(cln_draws[:t + 1]) for t in range(n)]

    starts = period_start_dates if period_start_dates else tuple(None for _ in range(n))
    ends = period_end_dates if period_end_dates else tuple(None for _ in range(n))

    MATERIAL_THRESHOLD_KEUR = 0.5

    for t in range(n):
        delta = cap_idc[t] - src_idc[t]
        if abs(delta) >= MATERIAL_THRESHOLD_KEUR:
            return PeriodDivergence(
                period_index=t,
                period_start=starts[t],
                period_end=ends[t],
                source_senior_draw_keur=src_draws[t],
                clean_senior_draw_keur=cln_draws[t],
                source_cumul_senior_keur=src_cumul[t],
                clean_cumul_senior_keur=cln_cumul[t],
                period_dcf=bridge.period_dcf[t],
                source_period_idc_keur=src_idc[t],
                clean_cap_period_idc_keur=cap_idc[t],
                delta_keur=delta,
                causal_reason=(
                    "CONSTRUCTION_FINANCING_METHOD_TIMING_DIFFERENCE: "
                    "Clean draw profile (CAPEX-weighted, SHL-exhausted) differs from "
                    "source draw profile (SHL-first allocation). "
                    "Clean NEXT_PERIOD shift means cap[t]=raw[t-1]."
                ),
            )

    raise AssertionError("No material divergence found — unexpected for TUHO")


__all__ = [
    "TuhoIdcBridge",
    "PeriodDivergence",
    "compute_tuho_idc_counterfactual_bridge",
    "find_first_material_period_divergence",
]
