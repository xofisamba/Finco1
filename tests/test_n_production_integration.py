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
    """N.3: create_default_tuho_wind1 produces SOURCE_PROVEN cash reserve schedule."""
    from app.project_factories import create_default_tuho_wind1
    r = run_project_shareholder_waterfall_model(create_default_tuho_wind1())
    fi = r.financing_result.cash_reserve_interest_schedules
    assert fi is not None
    assert fi.authority == "SOURCE_PROVEN"
    assert fi.total_financing_income_keur > 0


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
    """N.3: TUHO AV period cash interest > 0."""
    from app.project_factories import create_default_tuho_wind1
    r = run_project_shareholder_waterfall_model(create_default_tuho_wind1())
    fi = r.financing_result.cash_reserve_interest_schedules
    assert fi is not None
    non_zero = [pr for pr in fi.period_results if pr.calculated_financing_income_keur > 0.001]
    assert non_zero, "Expected non-zero cash interest periods"


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


def test_n4_oborovo_total_financing_income_positive():
    """N.4: Oborovo total financing income is positive."""
    from app.project_factories import create_default_oborovo
    r = run_project_shareholder_waterfall_model(create_default_oborovo())
    fi = r.financing_result.cash_reserve_interest_schedules
    assert fi is not None
    assert fi.total_financing_income_keur > 0


# ── N.5: Construction NI component proof ─────────────────────────────────────

def test_n5_tuho_construction_ni_components():
    """N.5: construction_NI = -(SHL_PIK + pre_op_opex) for TUHO."""
    from app.project_factories import create_default_tuho_wind1
    proj = create_default_tuho_wind1()
    r = run_project_shareholder_waterfall_model(proj)
    cf = r.financing_result.construction_financing
    shl_pik = cf.shl_construction_pik_keur
    pre_op = proj.tax.construction_pl.pre_operational_opex_keur
    # SOURCE_OPENING_LOSS_KEUR = 3568.6878026481627
    expected_ni = -(shl_pik + pre_op)
    assert abs(expected_ni - (-3568.6878026481627)) < 1e-6, (
        f"construction NI={expected_ni} != -3568.688 kEUR"
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
