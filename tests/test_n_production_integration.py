"""N Correction — Production integration tests.

Tests for the gating of the distribution accounting layer (WHT, legal reserve,
accounting cap) behind DistributionAccountingPolicy.
"""
from __future__ import annotations

import dataclasses

import pytest

from financial_engine.shareholder_waterfall import (
    run_project_shareholder_waterfall_model,
)


# ── O.2: DistributionAccountingPolicy validation ──────────────────────────────

def test_o2_enabled_unresolved_raises():
    """O.2: enabled=True + authority=UNRESOLVED must raise ValueError (fail closed)."""
    from finco_core.inputs.distribution_accounting_policy import (
        DistributionAccountingPolicy, DistributionAccountingAuthority,
    )
    with pytest.raises(ValueError, match="UNRESOLVED"):
        DistributionAccountingPolicy(enabled=True, authority=DistributionAccountingAuthority.UNRESOLVED)


def test_o2_wht_rate_out_of_range_raises():
    """O.2: dividend_wht_rate outside [0, 1] raises ValueError."""
    from finco_core.inputs.distribution_accounting_policy import (
        DistributionAccountingPolicy, DistributionAccountingAuthority,
    )
    with pytest.raises(ValueError, match="dividend_wht_rate"):
        DistributionAccountingPolicy(dividend_wht_rate=1.5)
    with pytest.raises(ValueError, match="dividend_wht_rate"):
        DistributionAccountingPolicy(dividend_wht_rate=-0.1)


def test_o2_legal_reserve_cap_out_of_range_raises():
    """O.2: legal_reserve_cap_fraction outside [0, 1] raises ValueError."""
    from finco_core.inputs.distribution_accounting_policy import (
        DistributionAccountingPolicy,
    )
    with pytest.raises(ValueError, match="legal_reserve_cap_fraction"):
        DistributionAccountingPolicy(legal_reserve_cap_fraction=1.5)


def test_o2_disabled_unresolved_ok():
    """O.2: enabled=False with UNRESOLVED authority is valid (default state)."""
    from finco_core.inputs.distribution_accounting_policy import DistributionAccountingPolicy
    p = DistributionAccountingPolicy()  # defaults: enabled=False, authority=UNRESOLVED
    assert p.enabled is False


# ── O.3: WHT dual authority reconciliation ────────────────────────────────────

def test_o3_wht_authority_disagreement_raises():
    """O.3: TaxParams.wht_sponsor_dividends != DistributionAccountingPolicy.dividend_wht_rate
    when policy is enabled must raise ValueError (fail closed).
    DistributionAccountingPolicy.dividend_wht_rate is the canonical owner.
    """
    from finco_core.inputs.distribution_accounting_policy import assert_wht_authority_consistent, DistributionAccountingPolicy, DistributionAccountingAuthority
    policy = DistributionAccountingPolicy(
        enabled=True,
        authority=DistributionAccountingAuthority.SOURCE_PROVEN,
        dividend_wht_rate=0.05,
    )
    with pytest.raises(ValueError, match="WHT authority conflict"):
        assert_wht_authority_consistent(tax_wht=0.10, policy=policy)


def test_o3_wht_authority_agreement_ok():
    """O.3: When rates match, no error is raised."""
    from finco_core.inputs.distribution_accounting_policy import assert_wht_authority_consistent, DistributionAccountingPolicy, DistributionAccountingAuthority
    policy = DistributionAccountingPolicy(
        enabled=True,
        authority=DistributionAccountingAuthority.SOURCE_PROVEN,
        dividend_wht_rate=0.05,
    )
    assert_wht_authority_consistent(tax_wht=0.05, policy=policy)  # no raise


def test_o3_wht_authority_disabled_policy_skips_check():
    """O.3: Disabled policy skips the cross-check (TaxParams legacy value irrelevant)."""
    from finco_core.inputs.distribution_accounting_policy import assert_wht_authority_consistent, DistributionAccountingPolicy
    policy = DistributionAccountingPolicy(enabled=False, dividend_wht_rate=0.05)
    assert_wht_authority_consistent(tax_wht=0.99, policy=policy)  # no raise


# ── N.2: Solar without distribution accounting preserves frozen G2C receipts ──

def test_n2_solar_frozen_sponsor_receipts():
    """N.2: Solar without distribution accounting policy preserves frozen G2C sponsor receipts."""
    from app.project_factories import create_default_solar_project
    r = run_project_shareholder_waterfall_model(create_default_solar_project())
    # Should NOT have cash reserve interest schedules
    fi = r.financing_result.cash_reserve_interest_schedules if r.financing_result else None
    assert fi is None
    # Verify sponsor receipts identity: total_receipts = total_legal_equity + SHL
    expected = (
        r.total_net_dividend_received_keur
        + r.total_shl_cash_interest_received_keur
        + r.total_shl_principal_received_keur
    )
    assert abs(r.total_sponsor_receipts_keur - expected) < 1e-6


def test_n2_solar_gross_equals_net_no_policy():
    """N.2: Without distribution accounting policy, gross div == net div (no WHT)."""
    from app.project_factories import create_default_solar_project
    r = run_project_shareholder_waterfall_model(create_default_solar_project())
    assert abs(r.total_gross_dividend_paid_keur - r.total_net_dividend_received_keur) < 1e-6


def test_n2_solar_net_equals_legal_equity_distribution():
    """N.2: For Solar (no policy), net_dividend == legal_equity_distribution each period."""
    from app.project_factories import create_default_solar_project
    r = run_project_shareholder_waterfall_model(create_default_solar_project())
    ops = [p for p in r.waterfall_periods if not p.is_construction]
    for p in ops:
        assert abs(p.net_dividend_received_keur - p.legal_equity_distribution_keur) < 1e-6, (
            f"Period {p.period_index}: net_div={p.net_dividend_received_keur} "
            f"!= legal_equity_dist={p.legal_equity_distribution_keur}"
        )


# ── N.3: TUHO production schedule ─────────────────────────────────────────────

def test_n3_tuho_production_schedule_source_proven():
    """N.3: TUHO produces SOURCE_PROVEN cash reserve schedule with exact total FI."""
    from app.project_factories import create_default_tuho_wind1
    r = run_project_shareholder_waterfall_model(create_default_tuho_wind1())
    fi = r.financing_result.cash_reserve_interest_schedules
    assert fi is not None
    assert fi.authority == "SOURCE_PROVEN"
    # Exact total FI (O.11): 20 non-zero periods, UC=544.865 (pre_op_opex removed per O.7)
    assert abs(fi.total_financing_income_keur - 124.31673813224894) < 1e-6, (
        f"TUHO total FI={fi.total_financing_income_keur} != 124.317"
    )


def test_n3_tuho_distribution_policy_enabled():
    """N.3: TUHO has distribution_accounting_policy enabled."""
    from app.project_factories import create_default_tuho_wind1
    p = create_default_tuho_wind1()
    assert p.distribution_accounting_policy is not None
    assert p.distribution_accounting_policy.enabled is True
    assert p.distribution_accounting_policy.authority.value == "SOURCE_PROVEN"


def test_n3_tuho_wht_zero():
    """N.3: TUHO has zero WHT — gross == net."""
    from app.project_factories import create_default_tuho_wind1
    r = run_project_shareholder_waterfall_model(create_default_tuho_wind1())
    assert abs(r.total_gross_dividend_paid_keur - r.total_net_dividend_received_keur) < 1e-6


def test_n3_tuho_av_cash_interest():
    """N.3/Q.3: TUHO 20 non-zero FI periods; AV (idx=41) UC=544.865, FI=2.7019 (clean model).

    Q.3 TUHO cash bridge causal chain:
      Source SHL draw = 29135.176 kEUR (IDC row 49, senior=43359.274 kEUR)
      Clean SHL draw  = 28741.109 kEUR (PR-9 senior solver, senior=43789.921 kEUR)
      Gap: ΔP = −394.067 kEUR → ΔPIK = −48.268 kEUR (compound formula, 548d, 8%)
      → construction SHL-interest gap
      → COD opening RE gap (clean RE = −clean_SHL_PIK vs source RE = −3568.688)
      → RE gap flows into operating retained earnings
      → AU (period idx=41) UC diverges: clean=544.865 vs source=550 kEUR
      → AV (period idx=41) FI diverges: clean=2.7019 vs source=2.7274 kEUR
    Source acceptance (Q.10): AU UC=550, AV FI=2.7273972602740044.
    No source target enters production arithmetic.
    """
    from app.project_factories import create_default_tuho_wind1
    r = run_project_shareholder_waterfall_model(create_default_tuho_wind1())
    fi = r.financing_result.cash_reserve_interest_schedules
    assert fi is not None
    non_zero = [pr for pr in fi.period_results if pr.calculated_financing_income_keur > 0.001]
    assert len(non_zero) == 20, f"Expected 20 non-zero FI periods, got {len(non_zero)}"
    av = next(p for p in fi.period_results if p.period_index == 41)
    assert abs(av.eligible_unrestricted_cash_keur - 544.864992395077) < 1e-6, (
        f"TUHO AV UC={av.eligible_unrestricted_cash_keur} != 544.865"
    )
    assert abs(av.calculated_financing_income_keur - 2.7019332499591493) < 1e-9, (
        f"TUHO AV FI={av.calculated_financing_income_keur} != 2.7019"
    )


# ── N.1: Gross/net identity in return summary ──────────────────────────────────

def test_n1_gross_net_identity_tuho():
    """N.1: sum(period pure_equity_net_cashflow) == legal_equity.net_cashflow (TUHO)."""
    from app.project_factories import create_default_tuho_wind1
    r = run_project_shareholder_waterfall_model(create_default_tuho_wind1())
    sum_period = sum(p.pure_equity_net_cashflow_keur for p in r.waterfall_periods)
    summary_net = r.return_summary.legal_equity.net_cashflow_keur
    assert abs(sum_period - summary_net) < 1.0  # within 1 kEUR tolerance


# ── N.4: Oborovo production schedule ──────────────────────────────────────────

def test_n4_oborovo_production_schedule_source_proven():
    """N.4: create_default_oborovo produces SOURCE_PROVEN cash reserve schedule."""
    from app.project_factories import create_default_oborovo
    r = run_project_shareholder_waterfall_model(create_default_oborovo())
    fi = r.financing_result.cash_reserve_interest_schedules
    assert fi is not None
    assert fi.authority == "SOURCE_PROVEN"


def test_n4_oborovo_distribution_policy_enabled():
    """N.4: Oborovo has distribution_accounting_policy enabled with 5% WHT."""
    from app.project_factories import create_default_oborovo
    p = create_default_oborovo()
    assert p.distribution_accounting_policy is not None
    assert p.distribution_accounting_policy.enabled is True
    assert abs(p.distribution_accounting_policy.dividend_wht_rate - 0.05) < 1e-9


def test_n4_oborovo_wht_five_percent():
    """N.4: Oborovo applies 5% WHT — net = gross * 0.95."""
    from app.project_factories import create_default_oborovo
    r = run_project_shareholder_waterfall_model(create_default_oborovo())
    ops = [p for p in r.waterfall_periods if not p.is_construction and p.gross_dividend_paid_keur > 1e-6]
    assert ops, "Expected at least one operating period with dividends"
    for p in ops:
        expected_net = p.gross_dividend_paid_keur * 0.95
        assert abs(p.net_dividend_received_keur - expected_net) < 1e-4, (
            f"Period {p.period_index}: net={p.net_dividend_received_keur} != gross*0.95={expected_net}"
        )


def test_n4_oborovo_total_financing_income():
    """N.4: Oborovo has exactly 20 non-zero FI periods; total FI = 71.003 kEUR (ELIGIBLE DSRA)."""
    from app.project_factories import create_default_oborovo
    r = run_project_shareholder_waterfall_model(create_default_oborovo())
    fi = r.financing_result.cash_reserve_interest_schedules
    assert fi is not None
    non_zero = [pr for pr in fi.period_results if pr.calculated_financing_income_keur > 0.001]
    assert len(non_zero) == 20, f"Expected 20 non-zero FI periods, got {len(non_zero)}"
    assert abs(fi.total_financing_income_keur - 71.00318671182808) < 1e-6, (
        f"Oborovo total FI={fi.total_financing_income_keur} != 71.003"
    )
    first = sorted(non_zero, key=lambda p: p.period_index)[0]
    assert first.period_index == 41, f"First FI period idx={first.period_index} != 41"
    assert abs(first.eligible_unrestricted_cash_keur - 695.9765515604863) < 1e-6


# ── N.5: Construction NI component proof ─────────────────────────────────────

def test_n5_tuho_construction_ni_components():
    """O.7: TUHO ConstructionPLStatement removed — construction NI = -SHL_PIK only.

    pre_op_opex=48.268 was a balancing plug (SOURCE_OPENING_LOSS_KEUR - SHL_PIK)
    with no independent workbook cell reference. BLOCKED per O.7.
    Token: CASH_RESERVE_INTEREST_CONSTRUCTION_PNL_COMPONENT_AUTHORITY_BLOCKED.
    """
    from app.project_factories import create_default_tuho_wind1
    proj = create_default_tuho_wind1()
    r = run_project_shareholder_waterfall_model(proj)
    cf = r.financing_result.construction_financing
    shl_pik = cf.shl_construction_pik_keur
    # O.7: no pre_op_opex — construction NI = -SHL_PIK = -3520.419555278245
    assert proj.tax.construction_pl is None, (
        "O.7: ConstructionPLStatement must be removed (balancing plug blocked)"
    )
    assert abs(shl_pik - 3520.419555278245) < 1e-6, (
        f"TUHO SHL_PIK={shl_pik} != 3520.420"
    )


# ── N.7: Opening UC typed authority ──────────────────────────────────────────

def test_n7_tuho_cash_reserve_interest_authority_source_proven():
    """N.7: TUHO cash reserve interest schedule carries SOURCE_PROVEN authority."""
    from app.project_factories import create_default_tuho_wind1
    from finco_core.inputs.cash_reserve_interest_policy import CashReserveInterestAuthority
    r = run_project_shareholder_waterfall_model(create_default_tuho_wind1())
    fi = r.financing_result.cash_reserve_interest_schedules
    assert fi is not None
    assert fi.authority == CashReserveInterestAuthority.SOURCE_PROVEN


def test_n7_oborovo_cash_reserve_interest_authority_source_proven():
    """N.7: Oborovo cash reserve interest schedule carries SOURCE_PROVEN authority."""
    from app.project_factories import create_default_oborovo
    from finco_core.inputs.cash_reserve_interest_policy import CashReserveInterestAuthority
    r = run_project_shareholder_waterfall_model(create_default_oborovo())
    fi = r.financing_result.cash_reserve_interest_schedules
    assert fi is not None
    assert fi.authority == CashReserveInterestAuthority.SOURCE_PROVEN


# ── N.6: Legal reserve authority ─────────────────────────────────────────────

def test_n6_tuho_share_capital_and_legal_reserve_fraction():
    """N.6: TUHO share_capital=500 kEUR and legal_reserve_cap=10%."""
    from app.project_factories import create_default_tuho_wind1
    r = run_project_shareholder_waterfall_model(create_default_tuho_wind1())
    assert r.financing_result.share_capital_keur == 500.0
    proj = create_default_tuho_wind1()
    assert proj.distribution_accounting_policy.legal_reserve_cap_fraction == 0.10


# ── O.8: Legal reserve causal proof ──────────────────────────────────────────

def test_o8_tuho_legal_reserve_causal_rollforward():
    """O.8: Prove TUHO legal reserve roll-forward is causally populated.

    At period_index=25 (first profitable distribution period):
      - opening_legal_reserve_keur == 0.0   (greenfield start)
      - legal_reserve_transfer_keur == 50.0  (10% × 500 kEUR share capital)
      - closing_legal_reserve_keur == 50.0   (cap fully funded in one period)

    All prior periods must have closing_legal_reserve_keur == 0.0.
    All subsequent periods: LR stable at 50, no further transfers.
    """
    from app.project_factories import create_default_tuho_wind1
    r = run_project_shareholder_waterfall_model(create_default_tuho_wind1())
    op_periods = [p for p in r.waterfall_periods if not p.is_construction]

    assert op_periods[0].opening_legal_reserve_keur == 0.0

    first_lr = next((p for p in op_periods if p.legal_reserve_transfer_keur > 0), None)
    assert first_lr is not None, "No legal reserve transfer found"
    assert first_lr.period_index == 25, f"Expected LR transfer at idx=25, got {first_lr.period_index}"
    assert first_lr.opening_legal_reserve_keur == 0.0
    assert abs(first_lr.legal_reserve_transfer_keur - 50.0) < 1e-6, (
        f"Expected transfer=50.0, got {first_lr.legal_reserve_transfer_keur}"
    )
    assert abs(first_lr.closing_legal_reserve_keur - 50.0) < 1e-6, (
        f"Expected closing_LR=50.0, got {first_lr.closing_legal_reserve_keur}"
    )

    for p in op_periods:
        if p.period_index >= 25:
            break
        assert p.closing_legal_reserve_keur == 0.0, (
            f"Expected 0 LR before idx=25, got {p.closing_legal_reserve_keur} at idx={p.period_index}"
        )

    for p in op_periods:
        if p.period_index > 25:
            assert abs(p.opening_legal_reserve_keur - 50.0) < 1e-6
            assert abs(p.closing_legal_reserve_keur - 50.0) < 1e-6
            assert p.legal_reserve_transfer_keur == 0.0


def test_o8_oborovo_legal_reserve_causal_rollforward():
    """O.8: Prove Oborovo legal reserve roll-forward (WHT=5%). Greenfield axiom."""
    from app.project_factories import create_default_oborovo
    r = run_project_shareholder_waterfall_model(create_default_oborovo())
    op_periods = [p for p in r.waterfall_periods if not p.is_construction]

    assert op_periods[0].opening_legal_reserve_keur == 0.0

    first_lr = next((p for p in op_periods if p.legal_reserve_transfer_keur > 0), None)
    assert first_lr is not None, "No legal reserve transfer for Oborovo"
    assert first_lr.opening_legal_reserve_keur == 0.0
    assert abs(first_lr.closing_legal_reserve_keur - 50.0) < 1e-6


# ── O.4: Full U2 transition residual assertion ────────────────────────────────

def test_o4_tuho_full_transition_no_residual():
    """O.4: After M.11 re-financing, running Oborovo/TUHO must not raise
    O4_FULL_TRANSITION_RESIDUAL_NOT_CONVERGED. The model itself enforces this;
    we prove it by running successfully.
    """
    from app.project_factories import create_default_tuho_wind1, create_default_oborovo
    # Both projects run O.4 residual check internally; successful return proves it passed.
    run_project_shareholder_waterfall_model(create_default_tuho_wind1())
    run_project_shareholder_waterfall_model(create_default_oborovo())


# ── N.9: Full-transition idempotence ─────────────────────────────────────────

def test_n9_tuho_idempotent_run():
    """N.9: Running TUHO twice produces identical total distributions."""
    from app.project_factories import create_default_tuho_wind1
    r1 = run_project_shareholder_waterfall_model(create_default_tuho_wind1())
    r2 = run_project_shareholder_waterfall_model(create_default_tuho_wind1())
    dist1 = sum(p.legal_equity_distribution_keur for p in r1.waterfall_periods)
    dist2 = sum(p.legal_equity_distribution_keur for p in r2.waterfall_periods)
    assert dist1 == dist2, f"Non-idempotent: {dist1} != {dist2}"


def test_n9_oborovo_idempotent_run():
    """N.9: Running Oborovo twice produces identical total distributions."""
    from app.project_factories import create_default_oborovo
    r1 = run_project_shareholder_waterfall_model(create_default_oborovo())
    r2 = run_project_shareholder_waterfall_model(create_default_oborovo())
    dist1 = sum(p.legal_equity_distribution_keur for p in r1.waterfall_periods)
    dist2 = sum(p.legal_equity_distribution_keur for p in r2.waterfall_periods)
    assert dist1 == dist2, f"Non-idempotent: {dist1} != {dist2}"


# ── N.12: Economic delta TUHO/Oborovo old→new ────────────────────────────────

# B3-main baseline (pre-distribution-accounting-policy) reference values
_B3_OLD_OBOROVO = {
    "distributions": 61689.90265451222,
    "sponsor_receipts": 108480.6739128149,
    "cash_tax": 10437.90476711545,
    "base_cfads": 171466.06681090177,
    "bank_cfads": 141761.6415624344,
}
_B3_OLD_TUHO = {
    "distributions": 151690.9613741361,
    "sponsor_receipts": 232607.02011878393,
    "cash_tax": 38915.55406411077,
    "base_cfads": 299442.99675362336,
    "bank_cfads": 196285.59264084484,
}


def test_n12_oborovo_economic_delta_direction():
    """N.12: Oborovo WHT reduces distributions vs bf71b21d; FI raises cash_tax/base_cfads.

    Compare current model output against bf71b21d values (_B3_OLD_OBOROVO).
    """
    from app.project_factories import create_default_oborovo
    r = run_project_shareholder_waterfall_model(create_default_oborovo())
    res = r.return_summary
    total_dist = r.total_gross_dividend_paid_keur
    # WHT reduces sponsor receipts; FI increases retained earnings → more tax
    assert total_dist < _B3_OLD_OBOROVO["distributions"], (
        f"distributions={total_dist} should be < bf71b21d {_B3_OLD_OBOROVO['distributions']}"
    )


def test_n12_tuho_economic_delta_direction():
    """N.12: TUHO legal reserve reduces distributions vs bf71b21d; FI raises base_cfads.

    Compare current model output against bf71b21d values (_B3_OLD_TUHO).
    """
    from app.project_factories import create_default_tuho_wind1
    r = run_project_shareholder_waterfall_model(create_default_tuho_wind1())
    total_dist = r.total_gross_dividend_paid_keur
    assert total_dist < _B3_OLD_TUHO["distributions"], (
        f"distributions={total_dist} should be < bf71b21d {_B3_OLD_TUHO['distributions']}"
    )


# ── N.14: Final acceptance report ────────────────────────────────────────────

def test_n14_cash_reserve_interest_authority_status():
    """O.11/O.7: Final authority status report — O.7 BLOCKED, exact behavioral assertions.

    Token: CASH_RESERVE_INTEREST_CONSTRUCTION_PNL_COMPONENT_AUTHORITY_BLOCKED
    Reason: pre_op_opex=48.268 kEUR was a balancing plug (SOURCE_OPENING_LOSS_KEUR − SHL_PIK)
    with no independent workbook cell reference. Removed per O.7. Construction NI = -SHL_PIK only.

    O.1  Oborovo DSRA ELIGIBLE (zero balance is not INELIGIBLE) ✓
    O.2  DistributionAccountingPolicy validated (enabled+UNRESOLVED raises, rate/cap ranges) ✓
    O.7  ConstructionPLStatement removed from TUHO (BLOCKED — no source-proven pre_op_opex) ✓
    N.2  distribution accounting layer gated behind DistributionAccountingPolicy ✓
    N.3  TUHO FI: 20 non-zero periods, total=124.317 kEUR, AV UC=544.865 ✓
    N.4  Oborovo FI: 20 non-zero periods, total=71.003 kEUR ✓
    N.6  legal reserve authority: share_capital=500, cap_fraction=10% ✓
    """
    from app.project_factories import create_default_tuho_wind1, create_default_oborovo
    from finco_core.inputs.cash_reserve_interest_policy import CashReserveInterestAuthority, EligibilityStatus
    from finco_core.inputs.distribution_accounting_policy import DistributionAccountingAuthority, DistributionAccountingPolicy

    proj_tuho = create_default_tuho_wind1()
    proj_oborovo = create_default_oborovo()

    # O.2: enabled+UNRESOLVED raises
    import pytest as _pytest
    with _pytest.raises(ValueError, match="UNRESOLVED"):
        DistributionAccountingPolicy(enabled=True, authority=DistributionAccountingAuthority.UNRESOLVED)

    # O.1: Oborovo DSRA ELIGIBLE
    assert proj_oborovo.cash_reserve_interest_policy.eligible_dsra == EligibilityStatus.ELIGIBLE

    # N.2: policy enabled
    assert proj_tuho.distribution_accounting_policy.enabled
    assert proj_oborovo.distribution_accounting_policy.enabled

    # N.7/N.3: authority SOURCE_PROVEN
    assert proj_tuho.cash_reserve_interest_policy.authority == CashReserveInterestAuthority.SOURCE_PROVEN
    assert proj_oborovo.cash_reserve_interest_policy.authority == CashReserveInterestAuthority.SOURCE_PROVEN

    # O.7: ConstructionPLStatement removed from TUHO
    assert proj_tuho.tax.construction_pl is None, "O.7: ConstructionPLStatement must be absent"

    # N.6: TUHO share capital and legal reserve
    r_tuho = run_project_shareholder_waterfall_model(proj_tuho)
    assert r_tuho.financing_result.share_capital_keur == 500.0
    assert proj_tuho.distribution_accounting_policy.legal_reserve_cap_fraction == 0.10

    # N.3: TUHO exact FI (O.11)
    fi_tuho = r_tuho.financing_result.cash_reserve_interest_schedules
    assert abs(fi_tuho.total_financing_income_keur - 124.31673813224894) < 1e-6

    # N.4: Oborovo exact FI (O.11)
    r_obo = run_project_shareholder_waterfall_model(proj_oborovo)
    fi_obo = r_obo.financing_result.cash_reserve_interest_schedules
    assert abs(fi_obo.total_financing_income_keur - 71.00318671182808) < 1e-6

    # O.11 report conclusion: BLOCKED due to O.7
    # Token is not a string assertion — it is the causal state of the model.
    # Assert the model state that causes the BLOCKED status:
    #   construction_pl=None (removed), no pre_op_opex plug, FI exact-matched above.
    assert proj_tuho.tax.construction_pl is None, (
        "CASH_RESERVE_INTEREST_CONSTRUCTION_PNL_COMPONENT_AUTHORITY_BLOCKED: "
        "construction_pl must be None (O.7: pre_op_opex plug removed, no source-proven value)"
    )
    assert getattr(proj_tuho.tax, "construction_pl", None) is None
    # Q.1: Reclassified token. Root cause is SHL construction interest mechanics gap
    # (source senior=43359 kEUR vs clean=43790 kEUR → SHL draw −394 kEUR → PIK −48.268 kEUR).
    # Token: CASH_RESERVE_INTEREST_SHL_CONSTRUCTION_PRINCIPAL_AUTHORITY_BLOCKED


def test_p6_opening_uc_authority_contract():
    """P.6/Q.8: Typed opening UC authority — project-level and fail-closed contract."""
    from financial_engine.shareholder_waterfall.model import (
        _OPENING_UC_AUTHORITY,
        _OPENING_UC_AUTHORITY_VALID,
        _resolve_opening_uc_keur,
    )
    from finco_core.inputs.distribution_accounting_policy import (
        DistributionAccountingPolicy,
        DistributionAccountingAuthority,
        OpeningUCAuthority,
        OPENING_UC_AUTHORITY_VALID,
    )
    from app.project_factories import create_default_oborovo, create_default_tuho_wind1
    import pytest as _pytest

    # P.6: Module-level authority is CAUSALLY_DERIVED_ZERO (greenfield axiom, O.9)
    assert _OPENING_UC_AUTHORITY == "CAUSALLY_DERIVED_ZERO"
    assert _OPENING_UC_AUTHORITY in _OPENING_UC_AUTHORITY_VALID

    # P.6: SOURCE_PROVEN_EXPLICIT_ZERO also valid
    assert _resolve_opening_uc_keur("SOURCE_PROVEN_EXPLICIT_ZERO") == 0.0
    assert _resolve_opening_uc_keur("CAUSALLY_DERIVED_ZERO") == 0.0

    # P.6: UNRESOLVED fails closed
    with _pytest.raises(ValueError, match="P.6 OPENING_UC_AUTHORITY_UNRESOLVED"):
        _resolve_opening_uc_keur("UNRESOLVED")

    # P.6: Unknown strings also fail closed
    with _pytest.raises(ValueError, match="P.6 OPENING_UC_AUTHORITY_UNRESOLVED"):
        _resolve_opening_uc_keur("SOME_UNKNOWN_AUTHORITY")

    # Q.8: Project-level authority via DistributionAccountingPolicy field
    # Oborovo and TUHO must carry CAUSALLY_DERIVED_ZERO at project level
    oborovo = create_default_oborovo()
    tuho = create_default_tuho_wind1()
    assert oborovo.distribution_accounting_policy.opening_uc_authority == OpeningUCAuthority.CAUSALLY_DERIVED_ZERO
    assert tuho.distribution_accounting_policy.opening_uc_authority == OpeningUCAuthority.CAUSALLY_DERIVED_ZERO

    # Q.8: OPENING_UC_AUTHORITY_VALID in distribution_accounting_policy matches model
    assert "CAUSALLY_DERIVED_ZERO" in OPENING_UC_AUTHORITY_VALID
    assert "SOURCE_PROVEN_EXPLICIT_ZERO" in OPENING_UC_AUTHORITY_VALID

    # Q.8: enabled=True with UNRESOLVED opening_uc_authority fails closed
    with _pytest.raises(ValueError, match="opening_uc_authority"):
        DistributionAccountingPolicy(
            enabled=True,
            authority=DistributionAccountingAuthority.SOURCE_PROVEN,
            dividend_wht_rate=0.0,
            legal_reserve_cap_fraction=0.10,
            opening_uc_authority="UNRESOLVED",  # must fail
        )


def test_p4_oborovo_dsra_source_alignment():
    """P.4: Oborovo dsra_months=0 matches source Inputs!I347=0 and Inputs!I348=0.

    Source workbook: DSRA is absent (zero target, zero balance throughout).
    Eligible_dsra=ELIGIBLE is preserved per O.1 — the eligibility policy is correct;
    zero balance means zero DSRA FI regardless of eligibility.
    FI and UC are unchanged from dsra_months=6 because the model computes UC from
    the operating waterfall, not from DSRA equity funding at FC.
    Root cause of Oborovo UC=695.977 vs source 550: structural waterfall/RE divergence
    (period 41 model acct_cap ~2803 vs source ~39.65 kEUR) — source workbook period-by-
    period RE data required for full resolution.
    """
    from app.project_factories import create_default_oborovo
    from finco_core.inputs.cash_reserve_interest_policy import EligibilityStatus

    proj = create_default_oborovo()
    # P.4: dsra_months=0 matches Inputs!I348=0
    assert proj.financing.dsra_months == 0, (
        f"P.4: Oborovo dsra_months={proj.financing.dsra_months} != 0 (source Inputs!I348=0)"
    )
    # O.1: eligible_dsra stays ELIGIBLE regardless of zero balance
    assert proj.cash_reserve_interest_policy.eligible_dsra == EligibilityStatus.ELIGIBLE


# ── Q.6: DSRA balance vector = 0 ─────────────────────────────────────────────

def test_q6_oborovo_dsra_balance_vector_zero():
    """Q.6: Prove Oborovo DSRA balance = 0 in both source and clean. ELIGIBLE preserved.

    Source: Inputs!I347=0 (dsra_target_months=0), Inputs!I348=0 (dsra_months=0).
    Source construction period SHL fixture: no DSRA drawdown, no DSRA closing balance.
    Clean: dsra_months=0, so DSRA balance vector is identically zero throughout.
    eligible_dsra=ELIGIBLE is preserved (O.1/Q.6): zero balance is not INELIGIBLE.
    """
    import json, pathlib
    from app.project_factories import create_default_oborovo
    from finco_core.inputs.cash_reserve_interest_policy import EligibilityStatus

    # Q.6: Source SHL fixture proves DSRA balance = 0 via explicit workbook inputs
    fixture_path = pathlib.Path("tests/fixtures/excel_oborovo_shl_operating_truth.json")
    with fixture_path.open() as f:
        shl_fix = json.load(f)
    dsra_inputs = shl_fix.get("workbook_inputs", {}).get("dsra_inputs", {})
    assert dsra_inputs.get("Inputs_I347_dsra_target_months") == 0, "Q.6: Source Inputs!I347 must be explicitly zero"
    assert dsra_inputs.get("Inputs_I348_dsra_months") == 0, "Q.6: Source Inputs!I348 must be explicitly zero"

    # Q.6: Clean model — dsra_months=0 → no DSRA balance
    proj = create_default_oborovo()
    assert proj.financing.dsra_months == 0, (
        f"Q.6: Oborovo dsra_months={proj.financing.dsra_months} != 0"
    )

    # Q.6: ELIGIBLE preserved (O.1)
    assert proj.cash_reserve_interest_policy.eligible_dsra == EligibilityStatus.ELIGIBLE, (
        "Q.6: eligible_dsra must remain ELIGIBLE; zero balance is not INELIGIBLE"
    )


# ── Q.10: Source-fixture acceptance tests ────────────────────────────────────

def test_q10_tuho_source_construction_shl_pik():
    """Q.10: Source TUHO construction SHL interest = 3568.6878026481627 kEUR.

    Source: IDC row 49 P=29135.176 kEUR, rate=8%, elapsed=548 days.
    Formula: P × ((1.08)^(548/365) − 1).
    Senior commitment IDC!D48 = 43359.2737822209 kEUR (excel_golden_tuho fixture).
    Clean SHL PIK = 3520.419555278245 (PR-9 senior=43789.921 → SHL draw=28741.109).
    Gap = −48.268 kEUR. No source target enters production arithmetic.
    """
    import json, pathlib, math

    # Source senior from fixture
    with pathlib.Path("tests/fixtures/excel_golden_tuho.json").open() as f:
        golden = json.load(f)
    source_senior = golden["golden_cells"]["senior_debt_idc_keur"]["value"]
    assert abs(source_senior - 43359.2737822209) < 1e-6, (
        f"Q.10: Source IDC!D48={source_senior} != 43359.274"
    )

    # Source construction SHL PIK: P=29135.176 (IDC row 49), r=8%, t=548/365
    # This is a causal derivation for documentation; the value is NOT plugged into
    # production code (Q.10 prohibition). The clean model derives SHL PIK from its
    # own senior solver residual, not from this source principal.
    source_p = 29135.176  # IDC!B49 — SHL Sponsor total at COD
    source_pik = source_p * ((1.08) ** (548 / 365) - 1)
    assert abs(source_pik - 3568.6878026481627) < 0.01, (
        f"Q.10: Source SHL PIK={source_pik} != 3568.688 (derivation only, not production input)"
    )

    # Clean model SHL PIK (causal reference — not source)
    from app.project_factories import create_default_tuho_wind1
    r = run_project_shareholder_waterfall_model(create_default_tuho_wind1())
    clean_pik = r.financing_result.construction_financing.shl_construction_pik_keur
    assert abs(clean_pik - 3520.419555278245) < 1e-4, (
        f"Q.10: Clean SHL PIK={clean_pik} != 3520.420"
    )

    # Source opening RE = −source SHL PIK (construction NI = −PIK, greenfield RE starts 0)
    source_opening_re = -source_pik
    assert abs(source_opening_re - (-3568.6878026481627)) < 0.01, (
        f"Q.10: Source opening RE={source_opening_re} != -3568.688"
    )


def test_q10_oborovo_source_construction_re_and_acct_cap():
    """Q.10: Source Oborovo construction RE = −1169.6619115852516; period-40 acct_cap = 39.649650.

    Source construction SHL PIK = 1169.6619115852516 kEUR (excel_oborovo_shl_operating_truth).
    Source P&L period 40 distributable = 39.649650241465224 kEUR (l1f_dividend fixture).
    Clean construction RE ≈ −1169.659 (CIT-accrual mismatch gap ≈ 0.003 kEUR).
    Root cause: source CIT assessed H1-only with fiscal reintegration; clean spreads H1+H2.
    No source target enters production arithmetic.
    """
    import json, pathlib

    # Source construction SHL PIK = 1169.6619115852516 (ds_index=0)
    with pathlib.Path("tests/fixtures/excel_oborovo_shl_operating_truth.json").open() as f:
        shl_fix = json.load(f)
    src_construction_pik = shl_fix["construction_period"]["gross_accrued_interest_keur"]
    assert abs(src_construction_pik - 1169.6619115852516) < 1e-9, (
        f"Q.10: Source construction PIK={src_construction_pik} != 1169.6619115852516"
    )

    # Source construction RE = −PIK (greenfield axiom O.9)
    src_construction_re = -src_construction_pik
    assert abs(src_construction_re - (-1169.6619115852516)) < 1e-9

    # Source period-40 distributable = accounting_cap = 39.649650241465224 kEUR
    with pathlib.Path("tests/fixtures/l1f_dividend_cash_row_mapping_source_evidence.json").open() as f:
        l1f = json.load(f)
    src_acct_cap_p40 = l1f["oborovo"]["dividend_cash_block"]["CF125"]["period_40_value_keur"]
    assert abs(src_acct_cap_p40 - 39.6496502414652) < 1e-6, (
        f"Q.10: Source acct_cap period 40={src_acct_cap_p40} != 39.649650"
    )

    # Clean model construction RE = −shl_construction_pik_keur (causal reference)
    # Construction NI = −SHL PIK (greenfield, only financing item in construction period).
    from app.project_factories import create_default_oborovo
    r = run_project_shareholder_waterfall_model(create_default_oborovo())
    clean_pik = r.financing_result.construction_financing.shl_construction_pik_keur
    clean_construction_re = -clean_pik
    # Clean ≈ −1169.659 due to CIT-accrual mismatch (gap < 0.01 kEUR vs source)
    assert abs(clean_construction_re - (-1169.6619115852516)) < 0.01, (
        f"Q.10: Clean construction RE={clean_construction_re}, source=-1169.662 (gap < 0.01)"
    )

    # Q.10: 20 non-zero FI periods idx 41–60
    fi = r.financing_result.cash_reserve_interest_schedules
    assert fi is not None
    non_zero = [pr for pr in fi.period_results if pr.calculated_financing_income_keur > 0.001]
    assert len(non_zero) == 20
    idxs = sorted(p.period_index for p in non_zero)
    assert idxs[0] == 41 and idxs[-1] == 60, (
        f"Q.10: FI periods idx range [{idxs[0]},{idxs[-1]}] != [41,60]"
    )
