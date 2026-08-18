"""financial_engine.financing.project_uses — Canonical Total Project Uses authority.

Single source of truth for computing Total Project Uses from a ProjectInputs contract.
Used by:
  - financial_engine.financing.project (G2A fixed-point)
  - financial_engine.senior_debt.project_adapter (gearing-basis contract)

Do NOT reproduce this arithmetic elsewhere.
"""
from __future__ import annotations

from finco_core.inputs import DebtServiceReserveSupportMode, ProjectInputs

from financial_engine.financing.contracts import ProjectUses


def compute_project_uses(project_inputs: ProjectInputs) -> ProjectUses:
    """Compute canonical Total Project Uses from a ProjectInputs contract.

    Authority: G2A financing stack definition.
      Total Project Uses = hard_capex + explicit_financing_costs + cash_reserve_funding

    DSRA modes:
      NONE      → reserve_use = 0 (requirement and legacy_cap must both be 0)
      CASH_DSRA → reserve_use = debt_service_reserve_requirement_keur (or legacy fallback)
      DSRF      → reserve_use = 0 (no cash reserve at close; requirement = sufficiency only)

    Raises ValueError for contract violations (conflicting inputs, capex mismatch).
    """
    capex = project_inputs.capex
    fin = project_inputs.financing
    financing_costs = (
        capex.idc_keur
        + capex.commitment_fees_keur
        + capex.bank_fees_keur
        + capex.other_financial_keur
        + capex.vat_costs_keur
    )

    dsra_mode = fin.dsra_support_mode
    req = getattr(fin, "debt_service_reserve_requirement_keur", 0.0) or 0.0
    legacy_cap = capex.reserve_accounts_keur

    if dsra_mode == DebtServiceReserveSupportMode.NONE:
        if legacy_cap > 0.0:
            raise ValueError(
                "G2A_RESERVE_ACCOUNTS_SET_BUT_MODE_IS_NONE: "
                f"reserve_accounts_keur={legacy_cap} but dsra_support_mode=NONE. "
                "Set reserve_accounts_keur=0 or change dsra_support_mode to CASH_DSRA."
            )
        if req > 0.0:
            raise ValueError(
                "G2A_RESERVE_REQUIREMENT_SET_BUT_MODE_IS_NONE: "
                f"debt_service_reserve_requirement_keur={req} but dsra_support_mode=NONE."
            )
        reserve_use = 0.0
    elif dsra_mode == DebtServiceReserveSupportMode.CASH_DSRA:
        if req > 0.0 and legacy_cap > 0.0 and abs(req - legacy_cap) > 1e-6:
            raise ValueError(
                "G2A_RESERVE_REQUIREMENT_CONFLICT: "
                f"debt_service_reserve_requirement_keur={req} != "
                f"capex.reserve_accounts_keur={legacy_cap}. "
                "Set one to 0 or align them."
            )
        reserve_use = req if req > 0.0 else legacy_cap
    else:  # DSRF
        reserve_use = 0.0

    total = capex.hard_capex_keur + financing_costs + reserve_use

    if dsra_mode != DebtServiceReserveSupportMode.DSRF:
        if abs(total - capex.total_capex) > 1e-9:
            raise ValueError("G2A_PROJECT_USES_CAPEX_CONTRACT_MISMATCH")

    return ProjectUses(
        hard_project_capex_keur=capex.hard_capex_keur,
        explicit_financing_cost_uses_keur=financing_costs,
        reserve_account_funding_keur=reserve_use,
        other_explicit_project_uses_keur=0.0,
        total_project_uses_keur=total,
    )
