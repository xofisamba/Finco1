"""domain/senior_debt_sizing/canonical_wiring.py

Runtime adapter for canonical SeniorDebtSizingEngine.

This module wires the canonical SeniorDebtSizingEngine into the runtime waterfall
when use_senior_debt_sizing_engine=True.

Core architectural principle:
    actual_cfads != sizing_cfads

    - sizing_cfads: explicit per-period CFADS for debt sizing (from Macro!R50 or equivalent)
      This is the hardcoded-style Excel basis for debt capacity computation.
    - actual_cfads: computed CFADS from full model run (CF!R69)
      This is the actual cash flow available for debt service after all model computations.

The SeniorDebtSizingEngine uses sizing_cfads (not actual_cfads) for debt capacity
computation. This explicit separation is the key architectural invariant.

DSCR target governance:
    The per-period DSCR target (dscr_schedule) is a CONFIGURABLE INPUT.
    It is NOT hardcoded to any single value (e.g., 1.45).
    TUHO: DS!R19 dual-DSCR (PPA 1.20 / Merchant 1.41)
    Oborovo: from FinancingParams.dscr_schedule

When use_senior_debt_sizing_engine=False (default):
    Legacy waterfall behavior unchanged.
    Debt sizing uses waterfall's internal cfads_for_sculpt = ebitda * (1 - tax_rate).

When use_senior_debt_sizing_engine=True:
    Canonical SeniorDebtSizingEngine computes debt service capacity from explicit
    sizing_cfads and per-period dscr_schedule.
    Result is attached as _canonical_senior_debt_sizing audit attribute.
    R99/R102: BLOCKED — this wiring does not touch R99/R102 gates.
    DistributionAccount: unchanged.
    Senior debt runtime: unchanged by this adapter (future phases may wire overrides).

R99/R102: BLOCKED — this adapter does not compute distribution gates.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

from domain.senior_debt_sizing.engine import SeniorDebtSizingEngine
from domain.senior_debt_sizing.policy import (
    SeniorDebtSizingPolicy,
    SeniorDebtDSCRPolicy,
    SizingMode,
)


@dataclass(frozen=True)
class CanonicalSeniorDebtSizingResult:
    """Result of wiring canonical SeniorDebtSizingEngine into runtime.

    Attributes
    ----------
    sizing_cfads_keur_by_period : tuple[float, ...]
        Explicit sizing CFADS per semiannual period (kEUR).
        Derived from project inputs (FinancingParams.sizing_cfads_keur_by_period).
    target_dscr_by_period : tuple[float, ...]
        Per-period DSCR targets used for canonical computation.
    debt_service_capacity_keur_by_period : tuple[float, ...]
        Per-period debt service capacity = sizing_cfads / target_dscr.
        This is the canonical "what the sizing CFADS can support" per period.
    total_debt_service_capacity_keur : float
        Sum of per-period debt service capacities.
    annuity_keur : float
        Implied fixed debt service annuity (total / period_count).
        For reference/comparison only — not a runtime override.
    sizing_mode : SizingMode
        The sizing mode used.
    source : str
        Provenance: "canonical_senior_debt_sizing_engine".
    notes : str
        Additional notes about the computation.
    """
    sizing_cfads_keur_by_period: Tuple[float, ...]
    target_dscr_by_period: Tuple[float, ...]
    debt_service_capacity_keur_by_period: Tuple[float, ...]
    total_debt_service_capacity_keur: float
    annuity_keur: float
    sizing_mode: SizingMode
    source: str = "canonical_senior_debt_sizing_engine"
    notes: str = ""


def compute_canonical_senior_debt_sizing(
    project_name: str,
    sizing_cfads_keur_by_period: Tuple[float, ...],
    target_dscr_by_period: Tuple[float, ...],
    sizing_mode: SizingMode = SizingMode.EXPLICIT_CFADS,
    source_cell: str = "Macro!R50",
    notes: str = "",
) -> CanonicalSeniorDebtSizingResult:
    """Compute canonical senior debt sizing result.

    This function is the canonical wiring entry point for the SeniorDebtSizingEngine.
    It takes explicit sizing CFADS and per-period DSCR targets and produces the
    canonical debt service capacity result.

    Parameters
    ----------
    project_name : str
        Project name (e.g., "TUHO-WIND-1", "OBOROVO-SOLAR-1").
    sizing_cfads_keur_by_period : tuple[float, ...]
        Explicit sizing CFADS per semiannual period (kEUR).
        Must be provided explicitly — not derived from actual CFADS.
        Source: Macro!R50 (TUHO) or equivalent for other projects.
    target_dscr_by_period : tuple[float, ...]
        Per-period DSCR targets. Source: DS!R19 or FinancingParams.dscr_schedule.
        Must be configurable — NOT hardcoded to a single value.
    sizing_mode : SizingMode
        Sizing mode (default: EXPLICIT_CFADS).
    source_cell : str
        Provenance marker for sizing CFADS source.
    notes : str
        Additional notes.

    Returns
    -------
    CanonicalSeniorDebtSizingResult
        Canonical debt service capacity result with per-period and total values.

    Raises
    ------
    ValueError
        If sizing_mode is DERIVE_FROM_MINIMUM_DSCR (not implemented yet).
    """
    # Build canonical policy and DSCR policy
    sizing_policy = SeniorDebtSizingPolicy(
        project_name=project_name,
        sizing_mode=sizing_mode,
        sizing_cfads_keur_by_period=sizing_cfads_keur_by_period,
        source_cell=source_cell,
        notes=notes,
    )

    dscr_policy = SeniorDebtDSCRPolicy(
        target_dscr_by_period=target_dscr_by_period,
        source_cell="FinancingParams.dscr_schedule",
    )

    # Compute via canonical engine
    engine_result = SeniorDebtSizingEngine.compute(sizing_policy, dscr_policy)

    # Compute annuity for reference (total_ds_capacity / period_count)
    period_count = len(sizing_cfads_keur_by_period)
    annuity_keur = (
        engine_result.total_debt_service_capacity_keur / period_count
        if period_count > 0 else 0.0
    )

    return CanonicalSeniorDebtSizingResult(
        sizing_cfads_keur_by_period=engine_result.sizing_cfads_keur_by_period,
        target_dscr_by_period=engine_result.target_dscr_by_period,
        debt_service_capacity_keur_by_period=engine_result.debt_service_capacity_keur_by_period,
        total_debt_service_capacity_keur=engine_result.total_debt_service_capacity_keur,
        annuity_keur=annuity_keur,
        sizing_mode=engine_result.sizing_mode,
        source="canonical_senior_debt_sizing_engine",
        notes=notes,
    )


def derive_sizing_cfads_from_ebitda(
    ebitda_schedule: Tuple[float, ...],
    tax_rate: float = 0.10,
) -> Tuple[float, ...]:
    """Derive sizing CFADS from EBITDA schedule using tax adjustment.

    This is a PROXY function for cases where explicit sizing CFADS (Macro!R50)
    has not yet been wired into project inputs. It replicates the legacy
    waterfall's internal cfads_for_sculpt derivation:

        sizing_cfads[t] = ebitda[t] * (1 - tax_rate)

    The explicit separation (actual_cfads != sizing_cfads) is preserved
    by labeling this clearly as a proxy/derivation.

    FUTURE: Replace with actual Macro!R50 values from project inputs once
    FinancingParams.sizing_cfads_keur_by_period is wired.

    Parameters
    ----------
    ebitda_schedule : tuple[float, ...]
        EBITDA per period (kEUR).
    tax_rate : float
        Tax rate for CFADS derivation (default 0.10 for legacy parity).

    Returns
    -------
    tuple[float, ...]
        Derived sizing CFADS per period.
    """
    return tuple(max(0.0, e) * (1.0 - tax_rate) for e in ebitda_schedule)


def build_canonical_senior_debt_sizing_from_inputs(
    project_name: str,
    project_code: str,
    ebitda_schedule: Tuple[float, ...],
    tax_rate: float,
    dscr_schedule: Tuple[float, ...],
    use_explicit_sizing_cfads: bool = False,
    explicit_sizing_cfads: Optional[Tuple[float, ...]] = None,
) -> CanonicalSeniorDebtSizingResult:
    """Build canonical senior debt sizing from project inputs.

    This is the main wiring helper that handles the actual_cfads vs sizing_cfads
    separation automatically:

    - If use_explicit_sizing_cfads=True and explicit_sizing_cfads is provided:
      Use explicit_sizing_cfads as sizing_cfads (correct canonical path)
    - Otherwise:
      Derive sizing_cfads from ebitda_schedule using legacy tax adjustment
      (proxy path — for validation only until real Macro!R50 values are wired)

    Parameters
    ----------
    project_name : str
        Project name.
    project_code : str
        Project code (e.g., "TUHO-WIND-1").
    ebitda_schedule : tuple[float, ...]
        EBITDA per period from project.
    tax_rate : float
        Tax rate for CFADS derivation.
    dscr_schedule : tuple[float, ...]
        Per-period DSCR targets from FinancingParams.
    use_explicit_sizing_cfads : bool
        If True, use explicit_sizing_cfads (canonical path).
        If False, derive from ebitda (legacy proxy path).
    explicit_sizing_cfads : tuple[float, ...], optional
        Explicit sizing CFADS per period. Required when
        use_explicit_sizing_cfads=True.

    Returns
    -------
    CanonicalSeniorDebtSizingResult
        Canonical debt service capacity result.
    """
    if use_explicit_sizing_cfads and explicit_sizing_cfads is not None:
        sizing_cfads = explicit_sizing_cfads
        notes = f"Explicit sizing CFADS for {project_code} (Macro!R50)"
    else:
        sizing_cfads = derive_sizing_cfads_from_ebitda(ebitda_schedule, tax_rate)
        notes = (
            f"Derived sizing CFADS from ebitda * (1 - {tax_rate}) "
            f"[LEGACY PROXY — replace with Macro!R50 values]"
        )

    return compute_canonical_senior_debt_sizing(
        project_name=project_name,
        sizing_cfads_keur_by_period=sizing_cfads,
        target_dscr_by_period=dscr_schedule,
        notes=notes,
    )