"""tests.helpers.offline_sponsor_engine — OFFLINE_VALIDATION_ONLY (Phase B4).

The legacy sponsor engine bridge (hardcoded TUHO/Oborovo capital structures)
was removed from the production run path in Phase B4. This offline copy
serves historical characterization tests via
tests.helpers.offline_calibration.run_project_legacy only.
"""
from __future__ import annotations


_SPONSOR_CAPITAL_STRUCTURES = {
    "TUHO": {
        "lp_commitment_keur": 400.0,
        "gp_commitment_keur": 100.0,
        "ownership": {"LP-1": 0.80, "GP-1": 0.20},
        "hurdle_rate_pa": 0.08,
        "gp_promote_share": 0.20,
        "compounding_convention": "SEMIANNUAL",
    },
    "Oborovo": {
        "lp_commitment_keur": 400.0,
        "gp_commitment_keur": 100.0,
        "ownership": {"LP-1": 0.80, "GP-1": 0.20},
        "hurdle_rate_pa": 0.08,
        "gp_promote_share": 0.20,
        "compounding_convention": "SEMIANNUAL",
    },
}


def _run_sponsor_engine(waterfall_result, project_inputs, project_type: str):
    """Call the Sponsor engine after the waterfall completes.

    Phase H2: This is a thin bridge that calls the Sponsor engine's public interface
    from project_runner. No engine internals are modified. No circular imports.
    Only wired for projects with a known capital structure (TUHO, Oborovo).

    Returns (cashflow_result, irr_result, moic_result) tuple, or None if not wired.
    """
    cap_struct = _SPONSOR_CAPITAL_STRUCTURES.get(project_type)
    if cap_struct is None:
        return None

    from app.sponsor_runner import SponsorRunConfig, run_sponsor_waterfall
    from domain.sponsor.sponsor_cashflow_runner import (
        SponsorCashflowRunnerInputs,
        run_sponsor_cashflows,
    )
    from domain.sponsor.sponsor_irr_runner import (
        SponsorIrrRunnerInputs,
        SponsorMoicRunnerInputs,
        run_sponsor_irr,
        run_sponsor_moic,
    )
    from domain.sponsor.equity_injection import EquityInjection

    # Extract SPV distributions from the completed waterfall result.
    # WaterfallResult.periods[].distribution_keur is the per-period equity distribution.
    spv_distributions = tuple(
        float(getattr(p, "distribution_keur", 0.0) or 0.0)
        for p in getattr(waterfall_result, "periods", [])
    )
    num_periods = len(spv_distributions)
    if num_periods == 0:
        return None

    # Build equity injections from capital structure.
    # Total equity = lp + gp, injected at period 0.
    total_equity = cap_struct["lp_commitment_keur"] + cap_struct["gp_commitment_keur"]
    equity_injections = (
        EquityInjection(
            period_index=0,
            amount_keur=total_equity,
            investor_id="SPONSOR-1",
            target_entity="SPV",
            purpose="equityContribution",
        ),
    )

    # Build SponsorCashflowRunnerInputs.
    # holdco_dividend_by_period and holdco_opex_by_period are set to zero
    # (we are at SPV level, not HoldCo; the cashflow is the SPV distribution).
    cashflow_inputs = SponsorCashflowRunnerInputs(
        investor_id="SPONSOR-1",
        entity_code="SPV",
        equity_injections=equity_injections,
        holdco_distribution_by_period=spv_distributions,
        holdco_dividend_by_period=tuple(0.0 for _ in range(num_periods)),
        wht_rate=0.0,
        holdco_opex_by_period=tuple(0.0 for _ in range(num_periods)),
        period_count=num_periods,
    )

    cashflow_result = run_sponsor_cashflows(cashflow_inputs)

    # Compute IRR and MOIC from the cashflow result.
    irr_result = run_sponsor_irr(SponsorIrrRunnerInputs(sponsor_result=cashflow_result))
    moic_result = run_sponsor_moic(SponsorMoicRunnerInputs(sponsor_result=cashflow_result))

    return cashflow_result, irr_result, moic_result
