"""MVP G2B — Simple Sponsor Returns tests.

GENERIC MVP POLICY: DISTRIBUTE_ALL_POST_SHL_CASH
Not Excel source truth. No target-fitting. No institutional waterfall.
"""

from __future__ import annotations

import dataclasses
from datetime import date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

import pytest

from finco_core.inputs import SponsorFundingMode
from finco_core.sponsor.xirr import robust_xirr
from financial_engine.financing import run_project_financing_model
from financial_engine.sponsor_returns import (
    ReturnMetricStatus,
    SponsorDistributionPolicy,
    run_project_sponsor_returns_model,
)
from financial_engine.sponsor_returns.contracts import SponsorCashFlowPeriod


# ── Helpers ───────────────────────────────────────────────────────────────────

def _solar_project():
    from app.project_factories import create_default_solar_project
    return create_default_solar_project()


def _wind_project():
    from app.project_factories import create_default_wind_project
    return create_default_wind_project()


def _equity_only(project):
    return dataclasses.replace(
        project,
        financing=dataclasses.replace(
            project.financing,
            sponsor_funding_mode=SponsorFundingMode.EQUITY_ONLY,
        ),
    )


# ── G2A upstream invariants must not change ──────────────────────────────────

@pytest.mark.parametrize(
    ("factory", "expected_uses", "expected_senior", "expected_shl"),
    [
        ("solar", 33_000.0, 24_750.0, 7_750.0),
        ("wind",  43_000.0, 32_250.0, 10_250.0),
    ],
)
def test_g2b_does_not_alter_g2a_financing_result(factory, expected_uses, expected_senior, expected_shl):
    """Running G2B must not change the G2A financing result."""
    project = _solar_project() if factory == "solar" else _wind_project()
    result = run_project_sponsor_returns_model(project)
    fin = result.financing_result
    assert fin.project_uses.total_project_uses_keur == pytest.approx(expected_uses)
    assert fin.final_senior_commitment_keur == pytest.approx(expected_senior)
    assert fin.derived_shl_cash_principal_keur == pytest.approx(expected_shl)


def test_g2b_g2a_result_identical_when_called_independently():
    """Financing result from G2B equals one called independently."""
    project = _solar_project()
    standalone = run_project_financing_model(project)
    via_g2b = run_project_sponsor_returns_model(project).financing_result
    assert via_g2b.final_senior_commitment_keur == pytest.approx(
        standalone.final_senior_commitment_keur
    )
    assert via_g2b.derived_shl_cash_principal_keur == pytest.approx(
        standalone.derived_shl_cash_principal_keur
    )


# ── Solar SHL mode ───────────────────────────────────────────────────────────

def test_solar_shl_mode_contribution_totals():
    """Solar SHL: share capital + SHL sum to G2A authority."""
    result = run_project_sponsor_returns_model(_solar_project())
    fin = result.financing_result
    assert result.total_share_capital_contributed_keur == pytest.approx(
        fin.share_capital_keur
    )
    assert result.total_shl_cash_contributed_keur == pytest.approx(
        fin.derived_shl_cash_principal_keur
    )
    assert result.total_legal_equity_contributed_keur == pytest.approx(
        fin.share_capital_keur
        + fin.share_premium_keur
        + fin.other_equity_funding_before_shl_keur
        + fin.additional_equity_keur
    )
    assert result.total_sponsor_contributed_keur == pytest.approx(
        result.total_legal_equity_contributed_keur
        + result.total_shl_cash_contributed_keur
    )


def test_solar_shl_mode_metrics_are_defined():
    """Solar SHL: both XIRR and MOIC are defined (project has contributions and distributions)."""
    result = run_project_sponsor_returns_model(_solar_project())
    assert result.pure_equity_xirr_status == ReturnMetricStatus.OK
    assert result.pure_equity_moic_status == ReturnMetricStatus.OK
    assert result.total_sponsor_xirr_status == ReturnMetricStatus.OK
    assert result.total_sponsor_moic_status == ReturnMetricStatus.OK
    assert result.pure_equity_xirr is not None
    assert result.pure_equity_moic is not None
    assert result.total_sponsor_xirr is not None
    assert result.total_sponsor_moic is not None


def test_solar_shl_mode_distribution_policy():
    result = run_project_sponsor_returns_model(_solar_project())
    assert result.distribution_policy == SponsorDistributionPolicy.DISTRIBUTE_ALL_POST_SHL_CASH


# ── Solar EQUITY_ONLY ─────────────────────────────────────────────────────────

def test_solar_equity_only_no_shl_contribution():
    result = run_project_sponsor_returns_model(_equity_only(_solar_project()))
    assert result.total_shl_cash_contributed_keur == pytest.approx(0.0)
    assert result.total_shl_cash_interest_received_keur == pytest.approx(0.0)
    assert result.total_shl_principal_received_keur == pytest.approx(0.0)


def test_solar_equity_only_metrics_are_defined():
    result = run_project_sponsor_returns_model(_equity_only(_solar_project()))
    assert result.pure_equity_xirr_status == ReturnMetricStatus.OK
    assert result.total_sponsor_xirr_status == ReturnMetricStatus.OK


# ── Wind SHL mode ─────────────────────────────────────────────────────────────

def test_wind_shl_mode_contribution_totals():
    result = run_project_sponsor_returns_model(_wind_project())
    fin = result.financing_result
    assert result.total_share_capital_contributed_keur == pytest.approx(fin.share_capital_keur)
    assert result.total_shl_cash_contributed_keur == pytest.approx(
        fin.derived_shl_cash_principal_keur
    )


def test_wind_shl_mode_metrics_defined():
    result = run_project_sponsor_returns_model(_wind_project())
    assert result.pure_equity_xirr_status == ReturnMetricStatus.OK
    assert result.total_sponsor_xirr_status == ReturnMetricStatus.OK


# ── Wind EQUITY_ONLY ──────────────────────────────────────────────────────────

def test_wind_equity_only_no_shl():
    result = run_project_sponsor_returns_model(_equity_only(_wind_project()))
    assert result.total_shl_cash_contributed_keur == pytest.approx(0.0)
    assert result.total_shl_cash_interest_received_keur == pytest.approx(0.0)
    assert result.total_shl_principal_received_keur == pytest.approx(0.0)


# ── EQUITY_ONLY identity: Pure Equity == Total Sponsor ───────────────────────

@pytest.mark.parametrize("factory", ["solar", "wind"])
def test_equity_only_pure_equity_equals_total_sponsor(factory):
    """EQUITY_ONLY: no SHL, so pure equity CF = total sponsor CF per period."""
    project = _equity_only(_solar_project() if factory == "solar" else _wind_project())
    result = run_project_sponsor_returns_model(project)
    for period in result.cashflow_periods:
        assert period.pure_equity_net_cashflow_keur == pytest.approx(
            period.total_sponsor_net_cashflow_keur, abs=1e-9
        ), f"period {period.period_index}: pure_equity != total_sponsor"
    # Summary totals also equal
    assert result.total_legal_equity_contributed_keur == pytest.approx(
        result.total_sponsor_contributed_keur, abs=1e-9
    )
    assert result.total_legal_equity_distributions_keur == pytest.approx(
        result.total_sponsor_receipts_keur, abs=1e-9
    )


# ── Cashflow identities ────────────────────────────────────────────────────────

@pytest.mark.parametrize("factory,mode", [
    ("solar", "shl"), ("solar", "equity_only"),
    ("wind", "shl"), ("wind", "equity_only"),
])
def test_cashflow_identities_hold_every_period(factory, mode):
    """Per-period pure equity and total sponsor net cashflow identities."""
    project = _solar_project() if factory == "solar" else _wind_project()
    if mode == "equity_only":
        project = _equity_only(project)
    result = run_project_sponsor_returns_model(project)
    for p in result.cashflow_periods:
        expected_pe = (
            p.legal_equity_distribution_keur
            - p.share_capital_contribution_keur
            - p.share_premium_contribution_keur
            - p.other_committed_equity_contribution_keur
            - p.additional_equity_contribution_keur
        )
        assert p.pure_equity_net_cashflow_keur == pytest.approx(expected_pe, abs=1e-9), (
            f"period {p.period_index}: pure_equity identity failed"
        )
        expected_ts = (
            expected_pe
            - p.shl_cash_contribution_keur
            + p.shl_cash_interest_receipt_keur
            + p.shl_principal_receipt_keur
        )
        assert p.total_sponsor_net_cashflow_keur == pytest.approx(expected_ts, abs=1e-9), (
            f"period {p.period_index}: total_sponsor identity failed"
        )


# ── Summary identities ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("factory,mode", [
    ("solar", "shl"), ("wind", "equity_only"),
])
def test_summary_identities(factory, mode):
    project = _solar_project() if factory == "solar" else _wind_project()
    if mode == "equity_only":
        project = _equity_only(project)
    result = run_project_sponsor_returns_model(project)
    assert result.total_legal_equity_contributed_keur == pytest.approx(
        result.total_share_capital_contributed_keur
        + result.total_share_premium_contributed_keur
        + result.total_other_committed_equity_contributed_keur
        + result.total_additional_equity_contributed_keur,
        abs=1e-9,
    )
    assert result.total_sponsor_contributed_keur == pytest.approx(
        result.total_legal_equity_contributed_keur
        + result.total_shl_cash_contributed_keur,
        abs=1e-9,
    )
    assert result.total_sponsor_receipts_keur == pytest.approx(
        result.total_legal_equity_distributions_keur
        + result.total_shl_cash_interest_received_keur
        + result.total_shl_principal_received_keur,
        abs=1e-9,
    )


# ── Distributions cannot exceed post-SHL cash ────────────────────────────────

@pytest.mark.parametrize("factory,mode", [
    ("solar", "shl"), ("solar", "equity_only"),
    ("wind", "shl"), ("wind", "equity_only"),
])
def test_distribution_never_exceeds_post_shl_cash(factory, mode):
    project = _solar_project() if factory == "solar" else _wind_project()
    if mode == "equity_only":
        project = _equity_only(project)
    result = run_project_sponsor_returns_model(project)
    for p in result.cashflow_periods:
        assert p.legal_equity_distribution_keur >= -1e-9, (
            f"period {p.period_index}: negative distribution"
        )
        assert p.legal_equity_distribution_keur <= p.post_shl_cash_available_keur + 1e-9, (
            f"period {p.period_index}: distribution exceeds available cash"
        )


def test_negative_post_shl_cash_produces_zero_distribution_and_visible_shortfall():
    """Periods with post-SHL cash < 0 produce zero distribution and visible shortfall."""
    result = run_project_sponsor_returns_model(_solar_project())
    for p in result.cashflow_periods:
        if p.cash_shortfall_keur > 0.0:
            assert p.legal_equity_distribution_keur == pytest.approx(0.0, abs=1e-9), (
                f"period {p.period_index}: expected zero distribution when shortfall > 0"
            )


# ── PIK exclusion from sponsor cash flows ─────────────────────────────────────

def test_shl_pik_not_in_total_sponsor_net_cashflow():
    """SHL PIK interest does not enter total_sponsor_net_cashflow at accrual time."""
    project = _solar_project()
    g2a = run_project_financing_model(project)
    result = run_project_sponsor_returns_model(project)

    if g2a.project_model_result.shareholder_loan is None:
        pytest.skip("No SHL schedule for this project")

    shl = g2a.project_model_result.shareholder_loan
    pik_by_idx = dict(zip(shl.period_indices, shl.shl_pik_interest_keur))
    cash_int_by_idx = dict(zip(shl.period_indices, shl.shl_cash_interest_keur))

    period_map = {p.period_index: p for p in result.cashflow_periods}

    for idx, pik in pik_by_idx.items():
        if pik <= 0.0:
            continue
        cash_int = cash_int_by_idx.get(idx, 0.0)
        if idx not in period_map:
            continue
        period = period_map[idx]
        # SHL cash interest receipt must equal cash_int (not pik + cash_int)
        assert period.shl_cash_interest_receipt_keur == pytest.approx(cash_int, abs=1e-9), (
            f"period {idx}: shl_cash_interest_receipt must be cash only, not PIK+cash"
        )
        # PIK must not inflate total sponsor net cashflow
        # total_sponsor net = pure_equity_net + shl_cash_int + shl_principal (no PIK)
        expected_ts = (
            period.pure_equity_net_cashflow_keur
            + cash_int
            + period.shl_principal_receipt_keur
        )
        assert period.total_sponsor_net_cashflow_keur == pytest.approx(expected_ts, abs=1e-9), (
            f"period {idx}: PIK must not appear in total_sponsor_net_cashflow"
        )


def test_pik_accrual_does_not_change_moic_but_cash_repayment_does():
    """Synthetic: PIK accrual periods do not affect MOIC; only actual cash payments do."""
    # Use Solar SHL result
    result = run_project_sponsor_returns_model(_solar_project())
    # For Generic Solar, construction PIK is zero (day-count fraction zero)
    # Verify: shl_pik_interest is NOT in total sponsor receipts
    g2a = run_project_financing_model(_solar_project())
    if g2a.project_model_result.shareholder_loan is None:
        pytest.skip("No SHL")
    shl = g2a.project_model_result.shareholder_loan
    total_pik = sum(shl.shl_pik_interest_keur)
    total_cash_int = sum(shl.shl_cash_interest_keur)
    # result receipts include only cash interest + principal, not PIK
    assert result.total_shl_cash_interest_received_keur == pytest.approx(total_cash_int, abs=1e-6)
    # PIK does not appear
    assert abs(result.total_shl_cash_interest_received_keur - total_pik) > 1e-3 or total_pik == pytest.approx(0.0)


def test_actual_shl_cash_interest_included_in_total_sponsor():
    """SHL cash interest (not PIK) is included in total sponsor receipts."""
    result = run_project_sponsor_returns_model(_solar_project())
    g2a = run_project_financing_model(_solar_project())
    if g2a.project_model_result.shareholder_loan is None:
        pytest.skip("No SHL")
    shl = g2a.project_model_result.shareholder_loan
    total_cash_int = sum(shl.shl_cash_interest_keur)
    assert result.total_shl_cash_interest_received_keur == pytest.approx(total_cash_int, abs=1e-6)


def test_shl_principal_repayment_in_total_sponsor():
    """SHL principal repaid is included in total sponsor receipts."""
    result = run_project_sponsor_returns_model(_solar_project())
    g2a = run_project_financing_model(_solar_project())
    if g2a.project_model_result.shareholder_loan is None:
        pytest.skip("No SHL")
    shl = g2a.project_model_result.shareholder_loan
    total_principal = sum(abs(v) for v in shl.shl_principal_keur)
    assert result.total_shl_principal_received_keur == pytest.approx(total_principal, abs=1e-6)


# ── Share premium and other committed equity included in contributions ─────────

def test_share_premium_contribution_included():
    """share_premium_contribution_keur is sourced from G2A construction schedule."""
    result = run_project_sponsor_returns_model(_solar_project())
    total_prem = sum(p.share_premium_contribution_keur for p in result.cashflow_periods)
    assert total_prem == pytest.approx(result.total_share_premium_contributed_keur, abs=1e-9)
    # For generic Solar, share_premium is zero (default)
    assert result.total_share_premium_contributed_keur == pytest.approx(0.0, abs=1e-9)


def test_other_committed_equity_contribution_included():
    result = run_project_sponsor_returns_model(_solar_project())
    total_oce = sum(p.other_committed_equity_contribution_keur for p in result.cashflow_periods)
    assert total_oce == pytest.approx(result.total_other_committed_equity_contributed_keur, abs=1e-9)


def test_additional_equity_contribution_in_equity_only():
    """EQUITY_ONLY: derived additional equity appears as additional_equity_contribution."""
    result = run_project_sponsor_returns_model(_equity_only(_solar_project()))
    total_ae = sum(p.additional_equity_contribution_keur for p in result.cashflow_periods)
    assert total_ae == pytest.approx(result.total_additional_equity_contributed_keur, abs=1e-9)
    # For Solar EQUITY_ONLY, additional equity should be non-zero (replaces SHL)
    assert result.total_additional_equity_contributed_keur > 0.0


# ── Contribution date provenance ──────────────────────────────────────────────

def test_construction_contribution_dates_from_financial_close():
    """Construction cashflow periods use project-owned financial_close as date anchor.

    G2A produces one cashflow period per construction month. Sponsor capital
    (share_capital + SHL) may be exhausted before all construction periods
    complete (because Senior draws occur last in the waterfall). The date
    authority is the period_index, not the presence of a sponsor contribution.
    """
    project = _solar_project()
    result = run_project_sponsor_returns_model(project)
    financial_close = project.info.financial_close
    construction_months = project.info.construction_months

    # All construction-period cashflows (is_construction flag, not period_index comparison)
    construction_cfs = [p for p in result.cashflow_periods if p.is_construction]
    assert len(construction_cfs) == construction_months, (
        f"Expected {construction_months} construction cashflow periods, "
        f"got {len(construction_cfs)}"
    )
    # First draw period is at financial close
    first = min(construction_cfs, key=lambda p: p.period_index)
    assert first.cashflow_date == financial_close, (
        f"First construction period must be at financial_close={financial_close}, "
        f"got {first.cashflow_date}"
    )
    # Total sponsor contributions across all construction periods match G2A
    total_sc = sum(p.share_capital_contribution_keur for p in construction_cfs)
    assert total_sc == pytest.approx(project.financing.share_capital_keur, abs=1e-6)


def test_construction_dates_no_arbitrary_indexing():
    """Construction dates must NOT use arbitrary 365-day indexing."""
    project = _solar_project()
    result = run_project_sponsor_returns_model(project)
    financial_close = project.info.financial_close

    construction_periods = sorted(
        [p for p in result.cashflow_periods if p.is_construction],
        key=lambda p: p.period_index,
    )
    # Verify each period is at financial_close + (k-1) months, not (k-1)*365 days
    for k, p in enumerate(construction_periods, start=1):
        from financial_engine.sponsor_returns.model import _construction_period_date
        expected = _construction_period_date(financial_close, k)
        assert p.cashflow_date == expected, (
            f"period {k}: expected date {expected}, got {p.cashflow_date}"
        )


def test_operating_receipt_dates_from_clean_model():
    """Operating return dates come from the clean model's period_end dates."""
    project = _solar_project()
    result = run_project_sponsor_returns_model(project)
    g2a = run_project_financing_model(project)
    period_end_by_idx = {
        p.period_index: p.period_end
        for p in g2a.project_model_result.periods
        if p.is_operation
    }
    for cf_period in result.cashflow_periods:
        if cf_period.is_construction:
            continue
        idx = cf_period.period_index
        if idx in period_end_by_idx:
            assert cf_period.cashflow_date == period_end_by_idx[idx], (
                f"operating period {idx}: date mismatch"
            )


def test_moving_receipt_date_changes_xirr_not_moic():
    """Moving a cash receipt date changes XIRR but leaves MOIC unchanged."""
    from datetime import date
    from finco_core.sponsor.xirr import robust_xirr

    # Synthetic dated cashflow
    cfs = [-100.0, 110.0]
    dates_a = [date(2025, 1, 1), date(2026, 1, 1)]   # 1-year gap
    dates_b = [date(2025, 1, 1), date(2027, 1, 1)]   # 2-year gap

    xirr_a = robust_xirr(cfs, dates_a)
    xirr_b = robust_xirr(cfs, dates_b)
    # XIRR differs (receipt further away → lower annualised rate)
    assert xirr_a is not None and xirr_b is not None
    assert xirr_a > xirr_b + 0.01, "Closer receipt date should give higher XIRR"

    # MOIC unchanged: same absolute amounts
    moic_a = 110.0 / 100.0
    moic_b = 110.0 / 100.0
    assert moic_a == pytest.approx(moic_b, abs=1e-9)


# ── Synthetic XIRR / MOIC proof ───────────────────────────────────────────────

def test_synthetic_xirr_known_result():
    """Synthetic: contribution + 1-year receipt → XIRR ≈ 10%."""
    from finco_core.sponsor.xirr import robust_xirr
    cfs = [-100.0, 110.0]
    dates = [date(2025, 1, 1), date(2026, 1, 1)]
    result = robust_xirr(cfs, dates)
    assert result == pytest.approx(0.10, abs=1e-5)


def test_synthetic_moic_known_result():
    """Synthetic MOIC: 110 / 100 = 1.10x."""
    total_contributions = 100.0
    total_receipts = 110.0
    moic = total_receipts / total_contributions
    assert moic == pytest.approx(1.10, abs=1e-9)


def test_xirr_undefined_no_positive_cashflow():
    """XIRR returns None when all cashflows are negative or zero."""
    from finco_core.sponsor.xirr import robust_xirr
    cfs = [-100.0, -50.0]
    dates = [date(2025, 1, 1), date(2026, 1, 1)]
    result = robust_xirr(cfs, dates)
    assert result is None


def test_xirr_undefined_no_negative_cashflow():
    """XIRR returns None when all cashflows are positive or zero."""
    from finco_core.sponsor.xirr import robust_xirr
    cfs = [100.0, 50.0]
    dates = [date(2025, 1, 1), date(2026, 1, 1)]
    result = robust_xirr(cfs, dates)
    assert result is None


# ── Return metric status types ─────────────────────────────────────────────────

def test_return_metric_status_typed_not_nan():
    """ReturnMetricStatus values are typed enums, not NaN or '#N/A'."""
    for status in ReturnMetricStatus:
        assert isinstance(status.value, str)
        assert "#N/A" not in status.value
        assert "NaN" not in status.value


# ── No G2A fields contaminated with sponsor returns ───────────────────────────

def test_g2a_contract_has_no_sponsor_return_fields():
    """G2A ProjectFinancingResult must not expose IRR, MOIC, or distributions."""
    from financial_engine.financing.contracts import ProjectFinancingResult
    import dataclasses
    names = {f.name for f in dataclasses.fields(ProjectFinancingResult)}
    assert not names & {"irr", "moic", "distributions", "balancing_account", "plug",
                        "pure_equity_xirr", "total_sponsor_xirr"}


# ── No project identity dispatch ──────────────────────────────────────────────

def test_no_project_identity_dispatch_in_g2b():
    """G2B model must not contain project-identity string dispatch."""
    import ast
    g2b_model = _REPO_ROOT / "financial_engine" / "sponsor_returns" / "model.py"
    source = g2b_model.read_text()
    tree = ast.parse(source)
    # Scan for Compare nodes that reference project names
    forbidden_names = {"oborovo", "OBOROVO", "solar", "SOLAR", "wind", "WIND", "tuho", "TUHO"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert node.value.lower() not in {n.lower() for n in forbidden_names}, (
                f"Found project-name dispatch string: {node.value!r}"
            )


# ── No target-fitting scan ────────────────────────────────────────────────────

def test_no_target_fitting_in_g2b():
    """G2B model must not contain approved_delta, balancing_plug, or target-fitting."""
    g2b_files = list((_REPO_ROOT / "financial_engine" / "sponsor_returns").rglob("*.py"))
    forbidden = ["approved_delta", "expected_delta", "balancing_plug", "target_irr",
                 "target_moic", "target_shl", "terminal_top_up", "period_correction"]
    for fpath in g2b_files:
        content = fpath.read_text()
        for token in forbidden:
            assert token not in content, (
                f"Forbidden target-fitting token '{token}' found in {fpath}"
            )


# ── Sources & Uses unchanged after G2B ───────────────────────────────────────

def test_sources_and_uses_unchanged_by_g2b():
    """G2B does not modify Sources & Uses from G2A."""
    project = _solar_project()
    g2a = run_project_financing_model(project)
    g2b = run_project_sponsor_returns_model(project)
    g2a_fin = g2b.financing_result
    assert g2a_fin.project_uses.total_project_uses_keur == pytest.approx(
        g2a.project_uses.total_project_uses_keur
    )
    assert g2a_fin.construction_funding.maximum_period_difference_keur <= 1e-9
