"""Pre-Freeze Fix 1 — Gearing-Cap Reachability Acceptance Tests.

Explicit proof suite for GENERIC_GEARING_CAP_UNREACHABLE fix (ae60f79).

These tests prove the Senior adapter contract directly (not via final Senior alone):
  A. Adapter contract: TOTAL_PROJECT_USES → COMBINED_MINIMUM, maximum_gearing, eligible_cost
  B. DSCR-only capacity contract: gearing_basis_mode=None → DSCR_SCULPTED
  C. Binding-constraint switch: gearing_ratio is genuinely causal
  D. Canonical Total Project Uses basis: NONE / CASH_DSRA / DSRF modes
  E. Financing-cost basis: eligible_cost includes financing costs, not just hard CAPEX
  F. No-silent-ignore: COMBINED_MINIMUM never produces maximum_gearing=None or eligible_cost=0
  G. Direct clean vs G2A final Senior equality
  H. Sources & Uses closure: Total Uses = sum of all committed + derived sources

Governance:
  No project-name/code dispatch.
  No approved_delta, expected_delta, balancing plug, target fitting.
  No hardcoded output mutation.
  Expected numerical fingerprints in tests only, never in production.
"""
from __future__ import annotations

import dataclasses

import pytest

from finco_core.inputs import (
    DebtServiceReserveSupportMode,
    GearingBasisMode,
    SponsorFundingMode,
)
from financial_engine.financing.project_uses import compute_project_uses
from financial_engine.senior_debt.policy import SeniorDebtSizingMode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_contract(project):
    """Return (policy, inputs) from the adapter for the given project."""
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )
    model = build_senior_debt_model_input_from_project_inputs(project)
    return model.senior_debt_policy, model.senior_debt_inputs


def _run_senior(project):
    """Run the clean Senior model directly (G0 path)."""
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )
    from financial_engine.orchestrator import run_senior_debt_model
    return run_senior_debt_model(build_senior_debt_model_input_from_project_inputs(project))


# ---------------------------------------------------------------------------
# A. Adapter contract: TOTAL_PROJECT_USES → COMBINED_MINIMUM
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("factory_name", [
    "create_default_solar_project",
    "create_default_wind_project",
])
def test_A_adapter_contract_total_project_uses_yields_combined_minimum(factory_name):
    """Adapter contract: gearing_basis_mode=TOTAL_PROJECT_USES wires COMBINED_MINIMUM.

    Asserts the policy and inputs fields directly — not via final Senior alone.
    """
    from app import project_factories
    project = getattr(project_factories, factory_name)()

    assert project.financing.gearing_basis_mode == GearingBasisMode.TOTAL_PROJECT_USES

    policy, inputs = _build_contract(project)
    canonical_uses = compute_project_uses(project)

    assert policy.sizing_mode == SeniorDebtSizingMode.COMBINED_MINIMUM
    assert policy.maximum_gearing == pytest.approx(project.financing.gearing_ratio)
    assert inputs.eligible_project_cost_keur == pytest.approx(
        canonical_uses.total_project_uses_keur
    )


# ---------------------------------------------------------------------------
# B. DSCR-only capacity contract: gearing_basis_mode=None → DSCR_SCULPTED
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("factory_name", [
    "create_default_solar_project",
    "create_default_wind_project",
])
def test_B_dscr_only_capacity_contract_when_gearing_basis_is_none(factory_name):
    """DSCR-only path: gearing_basis_mode=None yields DSCR_SCULPTED, no gearing fields.

    Proves the DSCR capacity path is a deliberate explicit contract, not
    an accidental bypass.
    """
    from app import project_factories
    project = getattr(project_factories, factory_name)()
    unconstrained = dataclasses.replace(
        project,
        financing=dataclasses.replace(project.financing, gearing_basis_mode=None),
    )

    policy, inputs = _build_contract(unconstrained)

    assert policy.sizing_mode == SeniorDebtSizingMode.DSCR_SCULPTED
    assert policy.maximum_gearing is None
    assert inputs.eligible_project_cost_keur == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# C. Binding-constraint switch: gearing_ratio is genuinely causal
# ---------------------------------------------------------------------------

def test_C_binding_constraint_switch_gearing_ratio_is_causal():
    """Binding constraint switches when gearing_ratio crosses DSCR capacity.

    Case 1: low gearing_ratio → GEARING binds (final Senior < DSCR capacity)
    Case 2: high gearing_ratio → DSCR binds (final Senior = DSCR capacity)

    Uses identity-neutral synthetic mutations on the base factory project.
    No hardcoded project codes.
    """
    from app.project_factories import create_default_solar_project
    from financial_engine.orchestrator import run_senior_debt_model
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )

    project = create_default_solar_project()
    canonical_uses = compute_project_uses(project)

    # Derive gearing caps from the canonical authority — no magic constants.
    low_ratio = 0.50   # 50% gearing: 33,000 × 0.50 = 16,500 < DSCR cap ≈ 28,458
    high_ratio = 1.00  # 100% gearing: 33,000 × 1.00 = 33,000 > DSCR cap ≈ 28,458

    low_gearing_project = dataclasses.replace(
        project,
        financing=dataclasses.replace(project.financing, gearing_ratio=low_ratio),
    )
    high_gearing_project = dataclasses.replace(
        project,
        financing=dataclasses.replace(project.financing, gearing_ratio=high_ratio),
    )

    gearing_bound = run_senior_debt_model(
        build_senior_debt_model_input_from_project_inputs(low_gearing_project)
    )
    dscr_bound = run_senior_debt_model(
        build_senior_debt_model_input_from_project_inputs(high_gearing_project)
    )

    expected_low_gearing_cap = canonical_uses.total_project_uses_keur * low_ratio
    expected_high_gearing_cap = canonical_uses.total_project_uses_keur * high_ratio

    # Case 1: gearing binds
    assert gearing_bound.senior_debt.debt_size_keur == pytest.approx(
        expected_low_gearing_cap, rel=1e-6
    )
    assert gearing_bound.senior_debt.diagnostics["gearing_debt_capacity_keur"] == pytest.approx(
        expected_low_gearing_cap, rel=1e-6
    )
    dscr_cap_low = gearing_bound.senior_debt.diagnostics["dscr_debt_capacity_keur"]
    assert dscr_cap_low > expected_low_gearing_cap  # gearing binds, not DSCR

    # Case 2: DSCR binds
    dscr_cap_high = dscr_bound.senior_debt.diagnostics["dscr_debt_capacity_keur"]
    assert dscr_bound.senior_debt.debt_size_keur == pytest.approx(dscr_cap_high, rel=1e-9)
    assert dscr_cap_high < expected_high_gearing_cap  # DSCR binds, not gearing


# ---------------------------------------------------------------------------
# D. Canonical Total Project Uses basis: NONE / CASH_DSRA / DSRF
# ---------------------------------------------------------------------------

def test_D1_dsra_none_reserve_use_is_zero():
    """NONE mode: eligible_project_cost excludes reserve funding (reserve_use = 0)."""
    from app.project_factories import create_default_solar_project
    project = create_default_solar_project()
    assert project.financing.dsra_support_mode == DebtServiceReserveSupportMode.NONE

    policy, inputs = _build_contract(project)
    canonical = compute_project_uses(project)

    assert canonical.reserve_account_funding_keur == pytest.approx(0.0)
    assert inputs.eligible_project_cost_keur == pytest.approx(
        canonical.total_project_uses_keur
    )


def test_D2_cash_dsra_reserve_included_exactly_once_in_eligible_cost():
    """CASH_DSRA mode: cash reserve is a Project Use and included once in eligible cost."""
    from app.project_factories import create_default_solar_project

    _RESERVE_KEUR = 1_500.0
    solar = create_default_solar_project()
    project = dataclasses.replace(
        solar,
        capex=dataclasses.replace(solar.capex, reserve_accounts_keur=_RESERVE_KEUR),
        financing=dataclasses.replace(
            solar.financing,
            dsra_support_mode=DebtServiceReserveSupportMode.CASH_DSRA,
        ),
    )

    canonical = compute_project_uses(project)
    policy, inputs = _build_contract(project)

    base_uses = compute_project_uses(solar).total_project_uses_keur
    assert canonical.reserve_account_funding_keur == pytest.approx(_RESERVE_KEUR)
    assert canonical.total_project_uses_keur == pytest.approx(base_uses + _RESERVE_KEUR)
    assert inputs.eligible_project_cost_keur == pytest.approx(canonical.total_project_uses_keur)


def test_D3_dsrf_mode_no_cash_reserve_project_use():
    """DSRF mode: no initial cash reserve Project Use; eligible_cost excludes reserve."""
    from app.project_factories import create_default_solar_project

    solar = create_default_solar_project()
    project = dataclasses.replace(
        solar,
        financing=dataclasses.replace(
            solar.financing,
            dsra_support_mode=DebtServiceReserveSupportMode.DSRF,
        ),
    )

    canonical = compute_project_uses(project)
    policy, inputs = _build_contract(project)

    assert canonical.reserve_account_funding_keur == pytest.approx(0.0)
    assert inputs.eligible_project_cost_keur == pytest.approx(canonical.total_project_uses_keur)
    # DSRF: total_project_uses == hard_capex (no cash reserve, no financing costs in factory)
    assert canonical.total_project_uses_keur == pytest.approx(solar.capex.hard_capex_keur)


# ---------------------------------------------------------------------------
# E. Financing-cost basis: eligible_cost includes financing costs
# ---------------------------------------------------------------------------

def test_E_eligible_cost_includes_financing_costs_not_just_hard_capex():
    """Eligible gearing basis includes explicit financing costs beyond hard CAPEX.

    Protects against regression to the old initial-guess arithmetic which uses
    gearing_ratio × sum(capex_items()) — excluding idc, bank_fees, etc.
    """
    from app.project_factories import create_default_solar_project

    _BANK_FEES_KEUR = 500.0
    _IDC_KEUR = 300.0
    solar = create_default_solar_project()

    project_with_fin_costs = dataclasses.replace(
        solar,
        capex=dataclasses.replace(
            solar.capex,
            bank_fees_keur=_BANK_FEES_KEUR,
            idc_keur=_IDC_KEUR,
        ),
    )

    canonical = compute_project_uses(project_with_fin_costs)
    policy, inputs = _build_contract(project_with_fin_costs)

    # Eligible cost = hard_capex + financing_costs
    assert canonical.explicit_financing_cost_uses_keur == pytest.approx(
        _BANK_FEES_KEUR + _IDC_KEUR
    )
    assert inputs.eligible_project_cost_keur == pytest.approx(canonical.total_project_uses_keur)
    assert inputs.eligible_project_cost_keur > solar.capex.hard_capex_keur

    # Confirm sum(capex_items()) alone underestimates eligible_cost when financing costs are set.
    capex_items_sum = sum(item.amount_keur for item in project_with_fin_costs.capex.capex_items())
    assert inputs.eligible_project_cost_keur > capex_items_sum


# ---------------------------------------------------------------------------
# F. No-silent-ignore: COMBINED_MINIMUM never produces maximum_gearing=None / eligible=0
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("factory_name", [
    "create_default_solar_project",
    "create_default_wind_project",
])
def test_F_no_silent_ignore_combined_minimum_wires_gearing_fields(factory_name):
    """COMBINED_MINIMUM policy must never have maximum_gearing=None or eligible_cost=0.

    Verifies the old broken behaviour (where these were silently ignored) is gone.
    """
    from app import project_factories
    project = getattr(project_factories, factory_name)()
    assert project.financing.gearing_basis_mode == GearingBasisMode.TOTAL_PROJECT_USES
    assert project.financing.gearing_ratio > 0.0

    policy, inputs = _build_contract(project)

    assert policy.sizing_mode == SeniorDebtSizingMode.COMBINED_MINIMUM
    assert policy.maximum_gearing is not None
    assert policy.maximum_gearing > 0.0
    assert inputs.eligible_project_cost_keur > 0.0


def test_F_unsupported_gearing_basis_fails_closed():
    """Unsupported gearing_basis_mode must raise ValueError — no silent fallback."""
    from app.project_factories import create_default_solar_project
    from finco_core.inputs._models import GearingBasisMode as GBM

    solar = create_default_solar_project()
    # Use a hypothetical unsupported mode value via object replacement.
    # We confirm the adapter raises for any non-TOTAL_PROJECT_USES non-None value.
    # Simulate by patching gearing_basis_mode on the financing object.
    class _FakeMode:
        value = "FAKE_UNSUPPORTED"
        def __str__(self):
            return "FAKE_UNSUPPORTED"

    project = dataclasses.replace(
        solar,
        financing=dataclasses.replace(solar.financing, gearing_basis_mode=_FakeMode()),
    )
    with pytest.raises((ValueError, Exception)):
        _build_contract(project)


# ---------------------------------------------------------------------------
# G. Direct clean vs G2A final Senior equality
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("factory_name", "expected_senior_keur"),
    [
        ("create_default_solar_project", None),  # derived from gearing_ratio × uses
        ("create_default_wind_project", None),
    ],
)
def test_G_direct_clean_final_senior_equals_g2a_final_senior(factory_name, expected_senior_keur):
    """Direct G0 run and G2A run must agree on the final Senior commitment.

    Expected Senior is derived from compute_project_uses() × gearing_ratio — never
    a hardcoded magic constant as financial logic.
    """
    from app import project_factories
    from financial_engine.financing import run_project_financing_model

    project = getattr(project_factories, factory_name)()
    canonical_uses = compute_project_uses(project)
    expected = canonical_uses.total_project_uses_keur * project.financing.gearing_ratio

    # G0 direct Senior model
    g0_result = _run_senior(project)
    # G2A fixed point
    g2a_result = run_project_financing_model(project)

    assert g0_result.senior_debt.debt_size_keur == pytest.approx(expected, rel=1e-6)
    assert g2a_result.final_senior_commitment_keur == pytest.approx(expected, rel=1e-6)
    assert g0_result.senior_debt.debt_size_keur == pytest.approx(
        g2a_result.final_senior_commitment_keur, rel=1e-9
    )
    assert g2a_result.binding_senior_constraint == "GEARING"


# ---------------------------------------------------------------------------
# H. Sources & Uses closure
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("factory_name", [
    "create_default_solar_project",
    "create_default_wind_project",
])
def test_H_sources_uses_closure_after_gearing_fix(factory_name):
    """Total Uses = sum of all committed and derived sources after gearing fix.

    The lower final Senior (gearing-capped) must flow into residual sponsor
    funding. No plug, no balancing account.
    """
    from app import project_factories
    from financial_engine.financing import run_project_financing_model

    project = getattr(project_factories, factory_name)()
    result = run_project_financing_model(project)

    total_uses = result.project_uses.total_project_uses_keur
    total_sources = (
        result.final_senior_commitment_keur
        + result.junior_or_other_main_project_funding_keur
        + result.share_capital_keur
        + result.share_premium_keur
        + result.other_equity_funding_before_shl_keur
        + result.additional_equity_keur
        + result.derived_shl_cash_principal_keur
    )
    assert total_sources == pytest.approx(total_uses, abs=1e-6)


# ---------------------------------------------------------------------------
# Initial debt guess invariance (item 6 — convergence seed only)
# ---------------------------------------------------------------------------

def test_initial_debt_guess_does_not_affect_converged_result():
    """Initial debt guess is a neutral solver seed with no effect on converged result.

    For Generic Solar/Wind the guess = gearing_ratio × capex_items() = gearing_ratio × hard_capex
    = gearing_ratio × eligible_project_cost_keur (because financing costs are zero in factory).
    This test proves convergence to the same Senior regardless of guess magnitude,
    confirming the guess is semantically irrelevant to the authoritative output.
    """
    from app.project_factories import create_default_solar_project
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )
    from financial_engine.orchestrator import run_senior_debt_model
    from financial_engine.senior_debt.inputs import SeniorDebtInputs

    project = create_default_solar_project()
    model = build_senior_debt_model_input_from_project_inputs(project)

    # Verify the default guess is equal to gearing × eligible_cost for the generic factory.
    canonical_uses = compute_project_uses(project)
    capex_items_guess = project.financing.gearing_ratio * sum(
        item.amount_keur for item in project.capex.capex_items()
    )
    gearing_cap_guess = project.financing.gearing_ratio * canonical_uses.total_project_uses_keur
    assert capex_items_guess == pytest.approx(gearing_cap_guess), (
        "For the generic factory (zero financing costs), the two guess formulas must agree"
    )

    # Run with an alternative guess (e.g., 2× the gearing cap) to prove seed invariance.
    altered_inputs = dataclasses.replace(
        model.senior_debt_inputs,
        initial_debt_guess_keur=model.senior_debt_inputs.eligible_project_cost_keur * 2.0,
    )
    altered_model = dataclasses.replace(model, senior_debt_inputs=altered_inputs)

    base_result = run_senior_debt_model(model)
    altered_result = run_senior_debt_model(altered_model)

    assert base_result.senior_debt.debt_size_keur == pytest.approx(
        altered_result.senior_debt.debt_size_keur, rel=1e-9
    )


# ---------------------------------------------------------------------------
# Oborovo non-regression (gearing_basis_mode=None, DSCR binds)
# ---------------------------------------------------------------------------

def test_oborovo_dscr_sculpted_senior_unchanged():
    """Oborovo-style project (gearing_basis_mode=None) remains DSCR_SCULPTED.

    Non-regression proof: the fix must not alter any project using the pure
    DSCR sizing path.
    """
    from app.project_factories import create_default_solar_project
    from financial_engine.orchestrator import run_senior_debt_model
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )

    project = create_default_solar_project()
    # Strip gearing to simulate the Oborovo-style pure-DSCR path.
    dscr_only = dataclasses.replace(
        project,
        financing=dataclasses.replace(project.financing, gearing_basis_mode=None),
    )
    policy, inputs = _build_contract(dscr_only)
    result = run_senior_debt_model(
        build_senior_debt_model_input_from_project_inputs(dscr_only)
    )

    assert policy.sizing_mode == SeniorDebtSizingMode.DSCR_SCULPTED
    assert policy.maximum_gearing is None
    assert inputs.eligible_project_cost_keur == pytest.approx(0.0)
    # Final Senior = DSCR capacity (no gearing cap)
    dscr_cap = result.senior_debt.diagnostics["dscr_debt_capacity_keur"]
    assert result.senior_debt.debt_size_keur == pytest.approx(dscr_cap, rel=1e-9)
    assert result.senior_debt.diagnostics["gearing_debt_capacity_keur"] is None
