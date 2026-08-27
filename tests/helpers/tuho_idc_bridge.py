"""
TUHO IDC counterfactual bridge diagnostic helper.

VALIDATION-ONLY — NOT A RUNTIME INPUT.
Classification: CONSTRUCTION_FINANCING_METHOD_TIMING_DIFFERENCE

This module computes the ordered sequential counterfactual bridge that
decomposes the +31.924 kEUR delta between TUHO source live IDC and Finco
clean capitalized IDC into five economic components.

Production modules (financial_engine, finco_core, app) MUST NOT import this.

Source evidence provenance
--------------------------
The source calibrated rate (6.0454%) is a LEGACY_CALIBRATED_DIAGNOSTIC rate
derived by calibrating the domain construction engine to the pasted Excel IDC
total (IDC!D57 = 1,519.564 kEUR). The actual workbook base-rate schedule and
rate components are not yet source-resolved from the workbook artifact. This
rate is therefore diagnostic evidence only, NOT SOURCE_WORKBOOK_EVIDENCE.

Source draws are produced by the domain construction engine using the
documented SHL-first waterfall allocation, which IS source-workbook-consistent
(equity first, then SHL, then Senior).

Clean mechanics provenance
--------------------------
The clean effective rate (0.0595 = 0.033 base + 0.0265 margin) is the
DECLARED typed input from the TUHO project factory
(ConstructionSeniorPricingInput, mode=FIXED_PLUS_MARGIN).
Day count: ACT_360 inclusive ((end-start).days+1)/360.
Balance basis: CURRENT_CLOSING_DRAWN (closing balance including current draw).
Capitalization timing: NEXT_PERIOD (cap[t] = raw[t-1], cap[0] = 0).
These are the exact runtime mechanics declared in the typed inputs — not
backsolved from the output.

Bridge order (S0 → S5)
-----------------------
  S0  Source pasted IDC (LEGACY_CALIBRATED_DIAGNOSTIC: calibrated rate,
      SHL-first draws, OPENING balance, 1/12 monthly DCF)
  S1  Change: Senior quantum → clean quantum (scale source draws proportionally)
  S2  Change: Draw profile → clean CAPEX-weighted draw profile
  S3  Change: Balance basis → CLOSING (includes current-period draw)
  S4  Change: DCF convention + effective rate → ACT_360 + clean declared rate
      (derived from typed inputs, not backsolved)
  S5  Apply: NEXT_PERIOD capitalization horizon (cap[t] = raw[t-1])

S5 is independently reconstructed from declared clean mechanics.
bridge_unexplained_residual = S5 - sum(CLEAN_CAP_RUNTIME) demonstrates
that the reconstruction is non-tautological.
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
    source_pasted_idc_keur: float    # LEGACY_CALIBRATED_DIAGNOSTIC reproducible
    source_circularity_residual_keur: float
    source_live_idc_keur: float      # Excel circularity artifact, not recomputed
    clean_capitalized_idc_keur: float   # runtime authority

    # Sequential component deltas (S0 = source_pasted; S5 = recomputed_clean_cap)
    senior_quantum_effect_keur: float      # ΔS1: scale Senior quantum to clean
    draw_profile_effect_keur: float        # ΔS2: source→clean draw profile
    balance_basis_effect_keur: float       # ΔS3: OPENING→CLOSING balance
    dcf_and_rate_effect_keur: float        # ΔS4: 1/12+calib_rate → ACT_360+clean_rate
    next_period_horizon_keur: float        # ΔS5: terminal accrual excluded (−recomp_raw[-1])

    # Non-tautological residuals
    # source_reconstruction_residual = sum(SOURCE_PERIOD_IDC) − SOURCE_LIVE
    #   (≈ -0.741 kEUR; SOURCE_PERIOD_IDC is pasted, SOURCE_LIVE includes circularity)
    source_reconstruction_residual_keur: float
    # clean_raw_reconstruction_residual = sum(recomputed_clean_raw) − sum(runtime_clean_raw)
    #   (must be < 0.001 kEUR; proves independent reconstruction matches engine)
    clean_raw_reconstruction_residual_keur: float
    # clean_cap_reconstruction_residual = sum(recomputed_clean_cap) − sum(runtime_clean_cap)
    #   (must be < 0.001 kEUR; proves NEXT_PERIOD transform matches engine)
    clean_cap_reconstruction_residual_keur: float
    # bridge_unexplained_residual = S0 + Σcomponents − sum(runtime_clean_cap)
    #   (non-tautological: S5 is recomputed, not copied from runtime)
    #   must be < 0.001 kEUR
    bridge_unexplained_residual_keur: float

    # Intermediate state totals
    s0_keur: float   # source_pasted
    s1_keur: float
    s2_keur: float
    s3_keur: float
    s4_keur: float   # recomputed clean raw IDC
    s5_keur: float   # recomputed clean capitalized IDC

    # Period-level source evidence
    source_period_draws_keur: tuple[float, ...]
    source_period_idc_keur: tuple[float, ...]   # LEGACY_CALIBRATED_DIAGNOSTIC
    clean_period_draws_keur: tuple[float, ...]
    recomputed_clean_raw_idc_keur: tuple[float, ...]   # from declared inputs
    recomputed_clean_cap_idc_keur: tuple[float, ...]   # from declared inputs + NEXT_PERIOD
    runtime_clean_raw_idc_keur: tuple[float, ...]      # engine output authority
    runtime_clean_cap_idc_keur: tuple[float, ...]      # engine output authority
    source_period_dcf: tuple[float, ...]   # 1/12 monthly (source convention)
    clean_period_dcf: tuple[float, ...]    # ACT_360 inclusive (clean convention)

    # Mechanics classification
    source_rate_provenance: str   # "LEGACY_CALIBRATED_DIAGNOSTIC"
    source_calibrated_rate: float
    clean_rate_declared: float    # 0.0595 from typed inputs
    clean_balance_basis: str      # "CURRENT_CLOSING_DRAWN"
    clean_dcf_convention: str     # "ACT_360_INCLUSIVE"
    clean_cap_timing: str         # "NEXT_PERIOD"


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
    source_period_idc_keur: float   # LEGACY_CALIBRATED_DIAGNOSTIC
    clean_cap_period_idc_keur: float   # recomputed NEXT_PERIOD cap
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
        Fully-computed bridge with non-tautological residuals.
    """
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

    # --- SOURCE EVIDENCE (LEGACY_CALIBRATED_DIAGNOSTIC) ---
    # The domain engine uses a target-calibrated rate to reproduce the pasted
    # Excel IDC total. The source draw profile (SHL-first waterfall) IS
    # workbook-consistent. The rate is LEGACY_CALIBRATED_DIAGNOSTIC.
    from domain.construction.templates.tuho import build_tuho_construction_config
    from domain.construction.capex_schedule import build_monthly_uses
    from domain.construction.funding_allocation import allocate_source_waterfall
    from domain.construction.idc_calculator import compute_senior_monthly_cumulative_idc

    src_config = build_tuho_construction_config()
    src_entries = allocate_source_waterfall(
        build_monthly_uses(src_config), src_config.funding_caps, tolerance_keur=0.05
    )
    SOURCE_CALIB_RATE: float = src_config.senior_interest_rate
    SOURCE_RATE_PROVENANCE: str = "LEGACY_CALIBRATED_DIAGNOSTIC"
    SOURCE_PASTED: float = 1_519.563935502677   # Excel IDC!D57 pasted total
    SOURCE_LIVE: float = 1_520.3051321075397    # Excel IDC row-57 period sum (circularity)
    SOURCE_CIRCULARITY: float = SOURCE_LIVE - SOURCE_PASTED
    SOURCE_SENIOR: float = 43_359.274
    SOURCE_DRAWS: tuple[float, ...] = tuple(e.senior_draw_keur for e in src_entries)
    SOURCE_PERIOD_IDC: tuple[float, ...] = compute_senior_monthly_cumulative_idc(
        src_entries,
        senior_interest_rate=SOURCE_CALIB_RATE,
        monthly_interest_period_fractions=src_config.senior_interest_period_fractions,
    )
    SOURCE_PERIOD_DCF: tuple[float, ...] = tuple(
        0.0 if i == 0 else 1.0 / 12.0 for i in range(len(SOURCE_DRAWS))
    )

    # source_reconstruction_residual: pasted - live (≈ -SOURCE_CIRCULARITY)
    source_reconstruction_residual = sum(SOURCE_PERIOD_IDC) - SOURCE_LIVE

    # --- CLEAN DATA (B3 production run, canonical authority) ---
    _pu, cfr = b3_uses_data
    CLEAN_DRAWS: tuple[float, ...] = cfr.senior_draws_keur
    CLEAN_SENIOR: float = cfr.final_senior_commitment_keur
    RUNTIME_CLEAN_RAW: tuple[float, ...] = cfr.senior_idc_accrual_keur
    RUNTIME_CLEAN_CAP: tuple[float, ...] = cfr.senior_idc_capitalized_uses_keur
    period_starts = cfr.period_start_dates
    period_ends = cfr.period_end_dates
    n = len(CLEAN_DRAWS)

    # --- CLEAN MECHANICS FROM DECLARED TYPED INPUTS ---
    # Rate: FIXED_PLUS_MARGIN = fixed_base_rate(0.033) + margin_rate(0.0265) = 0.0595
    # This is the declared all-in rate from create_default_tuho_wind1() factory.
    CLEAN_RATE_DECLARED: float = 0.033 + 0.0265   # = 0.0595
    CLEAN_BALANCE_BASIS: str = "CURRENT_CLOSING_DRAWN"
    CLEAN_DCF_CONVENTION: str = "ACT_360_INCLUSIVE"
    CLEAN_CAP_TIMING: str = "NEXT_PERIOD"

    # Clean period DCF: (end - start + 1) / 360 (ACT_360 inclusive)
    CLEAN_PERIOD_DCF: tuple[float, ...] = tuple(
        ((e - s).days + 1) / 360.0
        for s, e in zip(period_starts, period_ends)
    )

    # Reconstruct clean raw IDC independently from declared inputs
    # Balance basis: CURRENT_CLOSING_DRAWN → idc_basis = closing = cumul + draw
    cumul = 0.0
    recomp_raw: list[float] = []
    for t in range(n):
        closing = cumul + CLEAN_DRAWS[t]
        recomp_raw.append(closing * CLEAN_RATE_DECLARED * CLEAN_PERIOD_DCF[t])
        cumul = closing
    RECOMP_CLEAN_RAW: tuple[float, ...] = tuple(recomp_raw)

    # Reconstruct clean cap IDC via NEXT_PERIOD transformation
    RECOMP_CLEAN_CAP: tuple[float, ...] = (0.0,) + RECOMP_CLEAN_RAW[:-1]

    # Non-tautological reconstruction residuals
    clean_raw_reconstruction_residual = sum(RECOMP_CLEAN_RAW) - sum(RUNTIME_CLEAN_RAW)
    clean_cap_reconstruction_residual = sum(RECOMP_CLEAN_CAP) - sum(RUNTIME_CLEAN_CAP)

    # --- BRIDGE STATE HELPERS (source mechanics) ---
    DCF_MONTHLY: tuple[float, ...] = tuple(0.0 if i == 0 else 1.0 / 12.0 for i in range(n))

    def _idc_opening_monthly(draws: tuple, rate: float) -> tuple:
        """IDC = opening_balance × rate × (1/12); opening_balance[t] = sum(draws[:t])."""
        cumul = [0.0] + [sum(draws[:i + 1]) for i in range(n)]
        return tuple(cumul[t] * rate * DCF_MONTHLY[t] for t in range(n))

    def _idc_closing_monthly(draws: tuple, rate: float) -> tuple:
        """IDC = closing_balance × rate × (1/12); closing_balance[t] = sum(draws[:t+1])."""
        cumul = [sum(draws[:t + 1]) for t in range(n)]
        return tuple(cumul[t] * rate * DCF_MONTHLY[t] for t in range(n))

    # --- SEQUENTIAL STATES ---
    # S0: source pasted (legacy engine result, LEGACY_CALIBRATED_DIAGNOSTIC)
    S0 = SOURCE_PASTED

    # S1: scale source draws to clean Senior quantum, keep source mechanics
    scale = CLEAN_SENIOR / SOURCE_SENIOR
    S1_draws = tuple(d * scale for d in SOURCE_DRAWS)
    S1 = sum(_idc_opening_monthly(S1_draws, SOURCE_CALIB_RATE))

    # S2: switch to clean draw profile, keep opening+monthly+calibrated rate
    S2 = sum(_idc_opening_monthly(CLEAN_DRAWS, SOURCE_CALIB_RATE))

    # S3: switch to CLOSING balance basis, keep monthly+calibrated rate
    S3 = sum(_idc_closing_monthly(CLEAN_DRAWS, SOURCE_CALIB_RATE))

    # S4: switch to clean declared mechanics (ACT_360 + 0.0595 declared rate)
    #     independently reconstructed — NOT copied from runtime output
    S4 = sum(RECOMP_CLEAN_RAW)

    # S5: apply NEXT_PERIOD horizon → recomputed clean capitalized IDC
    #     independently reconstructed — NOT copied from runtime output
    S5 = sum(RECOMP_CLEAN_CAP)

    # --- COMPONENTS ---
    delta1 = S1 - S0   # Senior quantum effect
    delta2 = S2 - S1   # draw profile effect
    delta3 = S3 - S2   # balance basis effect (OPENING→CLOSING)
    delta4 = S4 - S3   # DCF + rate convention effect combined
    delta5 = S5 - S4   # NEXT_PERIOD horizon (= -RECOMP_CLEAN_RAW[-1])

    # Non-tautological: S5 is recomputed, not sum(RUNTIME_CLEAN_CAP)
    bridge_unexplained_residual = S5 - sum(RUNTIME_CLEAN_CAP)

    return TuhoIdcBridge(
        source_pasted_idc_keur=SOURCE_PASTED,
        source_circularity_residual_keur=SOURCE_CIRCULARITY,
        source_live_idc_keur=SOURCE_LIVE,
        clean_capitalized_idc_keur=sum(RUNTIME_CLEAN_CAP),
        senior_quantum_effect_keur=delta1,
        draw_profile_effect_keur=delta2,
        balance_basis_effect_keur=delta3,
        dcf_and_rate_effect_keur=delta4,
        next_period_horizon_keur=delta5,
        source_reconstruction_residual_keur=source_reconstruction_residual,
        clean_raw_reconstruction_residual_keur=clean_raw_reconstruction_residual,
        clean_cap_reconstruction_residual_keur=clean_cap_reconstruction_residual,
        bridge_unexplained_residual_keur=bridge_unexplained_residual,
        s0_keur=S0,
        s1_keur=S1,
        s2_keur=S2,
        s3_keur=S3,
        s4_keur=S4,
        s5_keur=S5,
        source_period_draws_keur=SOURCE_DRAWS,
        source_period_idc_keur=SOURCE_PERIOD_IDC,
        clean_period_draws_keur=CLEAN_DRAWS,
        recomputed_clean_raw_idc_keur=RECOMP_CLEAN_RAW,
        recomputed_clean_cap_idc_keur=RECOMP_CLEAN_CAP,
        runtime_clean_raw_idc_keur=RUNTIME_CLEAN_RAW,
        runtime_clean_cap_idc_keur=RUNTIME_CLEAN_CAP,
        source_period_dcf=SOURCE_PERIOD_DCF,
        clean_period_dcf=CLEAN_PERIOD_DCF,
        source_rate_provenance=SOURCE_RATE_PROVENANCE,
        source_calibrated_rate=SOURCE_CALIB_RATE,
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
    Both vectors are from independent reconstruction — not raw runtime outputs.

    Parameters
    ----------
    bridge : TuhoIdcBridge
        Computed bridge result.
    period_start_dates : tuple, optional
        Period start dates from clean cfr for richer output.
    period_end_dates : tuple, optional
        Period end dates from clean cfr.
    materiality_threshold_keur : float
        Threshold below which delta is considered immaterial. Default 0.5 kEUR.

    Returns
    -------
    PeriodDivergence
        First period exceeding the materiality threshold.

    Raises
    ------
    AssertionError
        If no material divergence is found.
    """
    src_draws = bridge.source_period_draws_keur
    cln_draws = bridge.clean_period_draws_keur
    src_idc = bridge.source_period_idc_keur
    cap_idc = bridge.recomputed_clean_cap_idc_keur

    n = len(src_draws)

    starts = period_start_dates if period_start_dates else tuple(None for _ in range(n))
    ends = period_end_dates if period_end_dates else tuple(None for _ in range(n))

    # Build source and clean opening/closing balances
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

    src_dcf = bridge.source_period_dcf
    cln_dcf = bridge.clean_period_dcf

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
                source_dcf=src_dcf[t],
                clean_dcf=cln_dcf[t],
                source_period_idc_keur=src_idc[t],
                clean_cap_period_idc_keur=cap_idc[t],
                delta_keur=delta,
                causal_reason=(
                    "CONSTRUCTION_FINANCING_METHOD_TIMING_DIFFERENCE: "
                    "Clean draw profile (CAPEX-weighted, SHL-exhausted) differs from "
                    "source draw profile (SHL-first allocation). "
                    "Source uses OPENING balance + 1/12 monthly (LEGACY_CALIBRATED_DIAGNOSTIC rate). "
                    "Clean uses CLOSING balance + ACT_360 + declared all-in rate 5.95%. "
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
