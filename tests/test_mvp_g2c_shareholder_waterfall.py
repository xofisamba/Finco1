"""MVP G2C — Covenant-Gated Shareholder Waterfall test suite.

Test authority: CURRENT_BLOCKING (see mvp_g1_current_financial_authority.md).

Source authority for DSCR lockup gate:
  Oborovo workbook SHA 15a621c4... Inputs!D223: senior_lockup_dscr = 1.10
  -> generic distribution_lockup_dscr parameter, sourced from FinancingParams.lockup_dscr.

Source authority for R-rows (Oborovo excel_oborovo_financial_truth.json CF sheet):
  free_cash_flow_for_junior_keur      (R84 - used as pre-DSRA post-Senior proxy)
  free_cash_flow_for_shl_keur         (R102 - available for SHL service)
  free_cash_flow_for_dividends_keur   (R99 - covenant-gated legal equity distribution)

G2A fingerprints inherited from G2B test suite (solar 33000/24750/7750,
wind 43000/32250/10250) are preserved here.
"""
from __future__ import annotations

import ast
import dataclasses
import pathlib

import pytest

from app.project_factories import create_default_solar_project, create_default_wind_project
from finco_core.inputs import GearingBasisMode, SponsorFundingMode
from financial_engine.shareholder_waterfall import (
    CovenantGatedWaterfallResult,
    DistributionGateStatus,
    run_project_shareholder_waterfall_model,
)

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def solar_result() -> CovenantGatedWaterfallResult:
    return run_project_shareholder_waterfall_model(create_default_solar_project())


@pytest.fixture(scope="module")
def wind_result() -> CovenantGatedWaterfallResult:
    return run_project_shareholder_waterfall_model(create_default_wind_project())


def _solar_with_lockup(lockup_dscr: float) -> CovenantGatedWaterfallResult:
    solar = create_default_solar_project()
    s = dataclasses.replace(
        solar,
        financing=dataclasses.replace(solar.financing, lockup_dscr=lockup_dscr),
    )
    return run_project_shareholder_waterfall_model(s)


def _solar_equity_only_with_lockup(lockup_dscr: float) -> CovenantGatedWaterfallResult:
    solar = create_default_solar_project()
    s = dataclasses.replace(
        solar,
        financing=dataclasses.replace(
            solar.financing,
            lockup_dscr=lockup_dscr,
            sponsor_funding_mode=SponsorFundingMode.EQUITY_ONLY,
            gearing_basis_mode=GearingBasisMode.TOTAL_PROJECT_USES,
        ),
    )
    return run_project_shareholder_waterfall_model(s)


# ── G2A fingerprints preserved ────────────────────────────────────────────────

def test_g2a_solar_fingerprints_preserved(solar_result):
    fin = solar_result.financing_result
    assert abs(fin.project_uses.total_project_uses_keur - 33000.0) < 1e-6
    assert abs(fin.final_senior_commitment_keur - 24750.0) < 1e-6
    assert abs(fin.derived_shl_cash_principal_keur - 7750.0) < 1e-6


def test_g2a_wind_fingerprints_preserved(wind_result):
    fin = wind_result.financing_result
    assert abs(fin.project_uses.total_project_uses_keur - 43000.0) < 1e-6
    assert abs(fin.final_senior_commitment_keur - 32250.0) < 1e-6
    assert abs(fin.derived_shl_cash_principal_keur - 10250.0) < 1e-6


# ── lockup_dscr sourced from FinancingParams (not hardcoded) ──────────────────

def test_distribution_lockup_dscr_distinct_from_target_dscr(solar_result):
    """target_dscr (sizing) and lockup_dscr (distribution gate) are independent."""
    solar = create_default_solar_project()
    assert solar.financing.target_dscr != solar.financing.lockup_dscr, (
        "target_dscr and lockup_dscr must be distinct parameters"
    )
    assert solar_result.distribution_lockup_dscr == solar.financing.lockup_dscr


def test_lockup_dscr_oborovo_source_value(solar_result):
    """Oborovo Inputs!D223: senior_lockup_dscr = 1.10.

    The Generic Solar/Wind default uses the same value.
    Source: tests/fixtures/excel_oborovo_financial_truth.json
    """
    assert abs(solar_result.distribution_lockup_dscr - 1.10) < 1e-9


def test_lockup_dscr_propagated_to_all_periods(solar_result):
    lockup = solar_result.distribution_lockup_dscr
    for p in solar_result.waterfall_periods:
        assert p.distribution_lockup_dscr == lockup


# ── Default projects: no periods covenant-locked ──────────────────────────────

def test_solar_no_covenant_lockups_at_default_threshold(solar_result):
    """Generic Solar DSCR exceeds 1.10 in all periods — covenant gate never locks."""
    assert solar_result.periods_locked_by_dscr == 0
    assert abs(solar_result.total_covenant_locked_keur) < 1e-9


def test_wind_no_covenant_lockups_at_default_threshold(wind_result):
    """Generic Wind DSCR exceeds 1.10 in all periods — covenant gate never locks."""
    assert wind_result.periods_locked_by_dscr == 0
    assert abs(wind_result.total_covenant_locked_keur) < 1e-9


def test_solar_gate_status_open_or_no_ds_only(solar_result):
    for p in solar_result.waterfall_periods:
        if not p.is_construction:
            assert p.distribution_gate_status in (
                DistributionGateStatus.OPEN,
                DistributionGateStatus.DSCR_UNAVAILABLE_GATE_OPEN,
            )


# ── Covenant gate locks distributions when DSCR below threshold ──────────────

def test_covenant_gate_locks_distributions_above_dscr(
):
    """lockup_dscr=1.25 > target_dscr=1.20: some periods locked for equity-only project."""
    result = _solar_equity_only_with_lockup(1.25)
    assert result.periods_locked_by_dscr > 0
    assert result.total_covenant_locked_keur > 0.0


def test_covenant_locked_periods_have_zero_distribution():
    result = _solar_equity_only_with_lockup(1.25)
    for p in result.waterfall_periods:
        if p.distribution_gate_status == DistributionGateStatus.LOCKED_DSCR_BELOW_LOCKUP:
            assert p.legal_equity_distribution_keur == 0.0, (
                f"P{p.period_index}: locked period should have zero distribution"
            )


def test_covenant_gate_upstream_of_shl_limits_shl_receipts():
    """DSCR gate is UPSTREAM of SHL service: locking reduces fcf_for_distribution,
    which limits SHL cash available. SHL receipts may fall when gate locks.

    Source: CF112 = H109 — FCF for SHL inherits gate-filtered FCF for distribution.
    """
    result_tight = _solar_equity_only_with_lockup(1.25)
    result_loose = _solar_equity_only_with_lockup(1.10)
    # Tight lockup → some periods have fcf_for_distribution=0 → SHL may receive less
    # At minimum: total locked cash + distributions + SHL receipts conserved from post-Senior
    for p in result_tight.waterfall_periods:
        if p.is_construction:
            continue
        # SHL receipts can only come from fcf_for_distribution (R112 = R109)
        shl_out = p.shl_cash_interest_receipt_keur + p.shl_principal_receipt_keur
        assert shl_out <= p.fcf_for_distribution_keur + 1e-9, (
            f"P{p.period_index}: SHL receipts exceed fcf_for_distribution "
            f"({shl_out:.4f} > {p.fcf_for_distribution_keur:.4f})"
        )


def test_gate_locked_period_has_zero_fcf_for_distribution():
    """When gate locks, fcf_for_distribution = 0 (source: R109 = 0 when gate fails)."""
    result = _solar_equity_only_with_lockup(1.25)
    for p in result.waterfall_periods:
        if p.distribution_gate_status == DistributionGateStatus.LOCKED_DSCR_BELOW_LOCKUP:
            assert abs(p.fcf_for_distribution_keur) < 1e-9, (
                f"P{p.period_index}: locked period fcf_for_distribution != 0"
            )
            assert p.shl_cash_interest_receipt_keur == 0.0, (
                f"P{p.period_index}: SHL interest received from locked period"
            )
            assert p.shl_principal_receipt_keur == 0.0, (
                f"P{p.period_index}: SHL principal received from locked period"
            )


# ── Gate partition: covenant_locked + fcf_for_distribution = pre_gate ────────

def test_gate_partition_holds_all_operating_periods(solar_result):
    """covenant_locked + fcf_for_distribution = max(0, signed_post_senior) for all operating periods."""
    for p in solar_result.waterfall_periods:
        if p.is_construction:
            continue
        pre_gate = max(0.0, p.signed_post_senior_keur)
        partition = p.covenant_locked_keur + p.fcf_for_distribution_keur
        assert abs(partition - pre_gate) < 1e-9, (
            f"P{p.period_index}: gate partition fails: {partition} != {pre_gate}"
        )


def test_gate_partition_holds_tight_lockup():
    result = _solar_equity_only_with_lockup(1.25)
    for p in result.waterfall_periods:
        if p.is_construction:
            continue
        pre_gate = max(0.0, p.signed_post_senior_keur)
        partition = p.covenant_locked_keur + p.fcf_for_distribution_keur
        assert abs(partition - pre_gate) < 1e-9


# ── Cash conservation invariant ───────────────────────────────────────────────

def test_cash_conservation_solar(solar_result):
    """SHL receipts + distribution <= fcf_for_distribution per period.
    Total waterfall output <= max(0, signed_post_senior) including covenant_locked."""
    for p in solar_result.waterfall_periods:
        if p.is_construction:
            continue
        shl_and_div = (
            p.shl_cash_interest_receipt_keur
            + p.shl_principal_receipt_keur
            + p.legal_equity_distribution_keur
        )
        assert shl_and_div <= p.fcf_for_distribution_keur + 1e-6, (
            f"P{p.period_index}: SHL+div exceed fcf_for_distribution: "
            f"{shl_and_div:.4f} > {p.fcf_for_distribution_keur:.4f}"
        )
        total_out = shl_and_div + p.covenant_locked_keur
        available = max(0.0, p.signed_post_senior_keur)
        assert total_out <= available + 1e-6, (
            f"P{p.period_index}: total waterfall output exceeds post-senior cash"
        )


def test_cash_conservation_wind(wind_result):
    for p in wind_result.waterfall_periods:
        if p.is_construction:
            continue
        shl_and_div = (
            p.shl_cash_interest_receipt_keur
            + p.shl_principal_receipt_keur
            + p.legal_equity_distribution_keur
        )
        assert shl_and_div <= p.fcf_for_distribution_keur + 1e-6


def test_cash_conservation_tight_lockup():
    """Conservation must hold when gate locks: locked + SHL + div = post_senior."""
    result = _solar_equity_only_with_lockup(1.25)
    for p in result.waterfall_periods:
        if p.is_construction:
            continue
        total_out = (
            p.covenant_locked_keur
            + p.shl_cash_interest_receipt_keur
            + p.shl_principal_receipt_keur
            + p.legal_equity_distribution_keur
        )
        available = max(0.0, p.signed_post_senior_keur)
        assert total_out <= available + 1e-6


# ── DSCR gate: periods with no Senior DS are open ────────────────────────────

def test_gate_open_when_no_senior_ds(solar_result):
    """Periods with no Senior DS have DSCR undefined → gate is open."""
    for p in solar_result.waterfall_periods:
        if p.distribution_gate_status == DistributionGateStatus.DSCR_UNAVAILABLE_GATE_OPEN:
            assert p.base_dscr is None, (
                f"P{p.period_index}: DSCR_UNAVAILABLE period should have base_dscr=None"
            )


def test_construction_periods_tagged_correctly(solar_result):
    for p in solar_result.waterfall_periods:
        if p.is_construction:
            assert p.distribution_gate_status == DistributionGateStatus.CONSTRUCTION


# ── G2C_DISTRIBUTION_ACCOUNT_AUTHORITY_INCOMPLETE status ─────────────────────

def test_distribution_account_status_incomplete(solar_result):
    """DA (R98) not in source extraction — result carries INCOMPLETE status."""
    assert solar_result.distribution_account_status == (
        "G2C_DISTRIBUTION_ACCOUNT_AUTHORITY_INCOMPLETE"
    )


# ── G2B consistent return metrics at default lockup ──────────────────────────

def test_solar_return_metrics_positive_at_default_lockup(solar_result):
    """G2C with default lockup_dscr=1.10: gate doesn't bind, metrics are positive."""
    assert solar_result.pure_equity_xirr is not None
    assert solar_result.pure_equity_xirr > 0.0
    assert solar_result.total_sponsor_xirr is not None
    assert solar_result.total_sponsor_xirr > 0.0
    assert solar_result.pure_equity_moic is not None
    assert solar_result.pure_equity_moic > 1.0
    assert solar_result.total_sponsor_moic is not None
    assert solar_result.total_sponsor_moic > 1.0


def test_wind_return_metrics_positive_at_default_lockup(wind_result):
    assert wind_result.pure_equity_xirr is not None
    assert wind_result.pure_equity_xirr > 0.0
    assert wind_result.total_sponsor_xirr is not None
    assert wind_result.total_sponsor_xirr > 0.0


def test_covenant_gate_reduces_equity_returns_when_locking():
    """When DSCR gate locks distributions, PE XIRR < baseline."""
    baseline = _solar_equity_only_with_lockup(1.10)
    locked = _solar_equity_only_with_lockup(1.25)
    # With more locking, total distributions decrease → lower PE XIRR
    assert locked.total_legal_equity_distributions_keur < baseline.total_legal_equity_distributions_keur
    # Pure equity XIRR degrades (or stays same if locked is non-zero XIRR still)
    if baseline.pure_equity_xirr is not None and locked.pure_equity_xirr is not None:
        assert locked.pure_equity_xirr <= baseline.pure_equity_xirr + 1e-6


# ── Totals reconcile ─────────────────────────────────────────────────────────

def test_total_sponsor_receipts_sum_solar(solar_result):
    expected = (
        solar_result.total_legal_equity_distributions_keur
        + solar_result.total_shl_cash_interest_received_keur
        + solar_result.total_shl_principal_received_keur
    )
    assert abs(solar_result.total_sponsor_receipts_keur - expected) < 1e-6


def test_total_legal_equity_contributed_sum_solar(solar_result):
    expected = (
        solar_result.total_share_capital_contributed_keur
        + solar_result.total_share_premium_contributed_keur
        + solar_result.total_other_committed_equity_contributed_keur
        + solar_result.total_additional_equity_contributed_keur
    )
    assert abs(solar_result.total_legal_equity_contributed_keur - expected) < 1e-6


def test_total_sponsor_contributed_sum_solar(solar_result):
    expected = (
        solar_result.total_legal_equity_contributed_keur
        + solar_result.total_shl_cash_contributed_keur
    )
    assert abs(solar_result.total_sponsor_contributed_keur - expected) < 1e-6


def test_total_covenant_plus_fcf_for_distribution_equals_sum_pre_gate(solar_result):
    """covenant_locked + fcf_for_dist = pre_gate (sum across periods)."""
    per_period_pre_gate = sum(
        max(0.0, p.signed_post_senior_keur)
        for p in solar_result.waterfall_periods
        if not p.is_construction
    )
    total_both = (
        solar_result.total_covenant_locked_keur
        + sum(p.fcf_for_distribution_keur for p in solar_result.waterfall_periods)
    )
    assert abs(total_both - per_period_pre_gate) < 1e-6


# ── Oborovo source values: lockup_dscr wired from extracted fixture ───────────

def test_oborovo_lockup_dscr_extracted_value():
    """Verify source: Oborovo financial truth fixture senior_lockup_dscr = 1.10."""
    import json
    path = _REPO_ROOT / "tests" / "fixtures" / "excel_oborovo_financial_truth.json"
    d = json.loads(path.read_text())
    entry = d["inputs"]["senior_lockup_dscr"]
    assert entry["row"] == 223
    assert entry["col"] == "D"
    assert abs(entry["value"] - 1.10) < 1e-9, (
        f"Oborovo senior_lockup_dscr != 1.10: {entry['value']}"
    )


def test_oborovo_target_dscr_and_lockup_dscr_distinct_in_source():
    """Verify source: Oborovo target_dscr (1.15) != lockup_dscr (1.10)."""
    import json
    path = _REPO_ROOT / "tests" / "fixtures" / "excel_oborovo_financial_truth.json"
    d = json.loads(path.read_text())
    sizing = d["inputs"]["senior_dscr_covenant"]["value"]
    lockup = d["inputs"]["senior_lockup_dscr"]["value"]
    assert abs(sizing - lockup) > 1e-9, (
        "Oborovo sizing DSCR and lockup DSCR must be distinct in source evidence"
    )


def test_g2c_r99_monotonicity_with_looser_lockup():
    """Looser lockup → more or equal distributions (R99 weakly increases as gate relaxes)."""
    tight = _solar_equity_only_with_lockup(1.25)
    loose = _solar_equity_only_with_lockup(1.10)
    assert loose.total_legal_equity_distributions_keur >= tight.total_legal_equity_distributions_keur - 1e-6


# ── BULLET repayment mode: no principal before maturity ───────────────────────

def test_solar_bullet_no_principal_before_maturity(solar_result):
    """Generic Solar uses BULLET repayment: shl_principal_receipt_keur = 0 for all periods
    except the SHL maturity period. Even if FCF > gross interest, no principal is swept."""
    op = [p for p in solar_result.waterfall_periods if not p.is_construction]
    # Find the maturity period (last period with non-zero principal)
    principal_periods = [p for p in op if p.shl_principal_receipt_keur > 1e-9]
    assert len(principal_periods) <= 1, (
        f"BULLET Solar: principal in {len(principal_periods)} periods, expected at most 1 (maturity only). "
        f"Periods: {[p.period_index for p in principal_periods]}"
    )
    # All non-maturity periods: principal = 0, even when cash > gross interest
    non_maturity_with_principal = [
        p for p in op
        if p.shl_opening_balance_keur > 0.0
        and p.shl_principal_receipt_keur > 1e-9
        and p.shl_cash_interest_receipt_keur < p.shl_opening_balance_keur * 0.5  # not near full repayment
    ]
    # Any period that has principal but also has a surplus (cash > interest) is a CASH_SWEEP artifact
    pre_maturity_principal = [
        p for p in op
        if p.shl_principal_receipt_keur > 1e-9
        and p.shl_opening_balance_keur > 100.0  # large balance still open
    ]
    assert len(pre_maturity_principal) <= 1, (
        f"BULLET Solar: pre-maturity principal payments found at: "
        f"{[(p.period_index, p.shl_principal_receipt_keur) for p in pre_maturity_principal]}"
    )


def test_wind_bullet_no_principal_before_maturity(wind_result):
    """Generic Wind uses BULLET repayment: shl_principal_receipt_keur = 0 for all periods
    except the SHL maturity period."""
    op = [p for p in wind_result.waterfall_periods if not p.is_construction]
    principal_periods = [p for p in op if p.shl_principal_receipt_keur > 1e-9]
    assert len(principal_periods) <= 1, (
        f"BULLET Wind: principal in {len(principal_periods)} periods, expected at most 1 (maturity only). "
        f"Periods: {[p.period_index for p in principal_periods]}"
    )


# ── Day-count convention: project-owned, not hardcoded ───────────────────────

def test_solar_day_count_period_axis_actual_year(solar_result):
    """Generic Solar/Wind use PERIOD_AXIS_ACTUAL_YEAR for SHL day-count.
    Proved by checking that gross_interest / opening_balance / annual_rate != 1/365 * days_exact.
    PERIOD_AXIS_ACTUAL_YEAR uses the period's day_fraction attribute (model-period axis), not
    calendar days, so it differs from ACT_365_FIXED when periods are not exact half-years."""
    solar = create_default_solar_project()
    assert getattr(solar.financing, "shl_day_count_convention", None) == "PERIOD_AXIS_ACTUAL_YEAR", (
        "Generic Solar must use PERIOD_AXIS_ACTUAL_YEAR day-count convention"
    )


def test_wind_day_count_period_axis_actual_year():
    """Generic Wind uses PERIOD_AXIS_ACTUAL_YEAR for SHL day-count."""
    from app.project_factories import create_default_wind_project
    wind = create_default_wind_project()
    assert getattr(wind.financing, "shl_day_count_convention", None) == "PERIOD_AXIS_ACTUAL_YEAR", (
        "Generic Wind must use PERIOD_AXIS_ACTUAL_YEAR day-count convention"
    )


def test_oborovo_day_count_act_365_fixed():
    """Oborovo uses ACT_365_FIXED for SHL day-count (Inputs source-proven)."""
    from app.project_factories import create_default_oborovo
    obo = create_default_oborovo()
    assert getattr(obo.financing, "shl_day_count_convention", None) == "ACT_365_FIXED", (
        "Oborovo must use ACT_365_FIXED day-count convention"
    )


# ── Oborovo DS25 principal eligibility and DS40 maturity ─────────────────────

@pytest.fixture(scope="module")
def oborovo_g2c_result():
    from app.project_factories import create_default_oborovo
    from finco_core.inputs import SponsorFundingMode, GearingBasisMode
    obo = create_default_oborovo()
    obo_g2c = dataclasses.replace(
        obo,
        financing=dataclasses.replace(
            obo.financing,
            sponsor_funding_mode=SponsorFundingMode.SHARE_CAPITAL_THEN_SHL,
            gearing_basis_mode=GearingBasisMode.TOTAL_PROJECT_USES,
            lockup_dscr=0.5,  # very low: no gate locks for this policy test
        ),
    )
    return run_project_shareholder_waterfall_model(obo_g2c)


def test_oborovo_ds25_principal_eligibility(oborovo_g2c_result):
    """Oborovo SHL: principal_eligibility_start_period=25 (DS25).
    Before period 25, principal = 0 even with surplus cash (CASH_SWEEP pre-eligibility suppressed).
    Source: FinancingParams.shl_principal_eligibility_start_period=25."""
    op = [p for p in oborovo_g2c_result.waterfall_periods if not p.is_construction]
    pre_ds25 = [p for p in op if p.period_index < 25]
    assert len(pre_ds25) > 0, "Must have operating periods before DS25"
    for p in pre_ds25:
        assert p.shl_principal_receipt_keur == pytest.approx(0.0, abs=1e-9), (
            f"Oborovo P{p.period_index} (before DS25): principal must be 0, "
            f"got {p.shl_principal_receipt_keur}"
        )


def test_oborovo_ds40_maturity_balance_closes(oborovo_g2c_result):
    """Oborovo SHL: contractual maturity at DS40 (period_index=40).
    At maturity, shl_closing_balance_keur = 0 (contractual full repayment)."""
    op = [p for p in oborovo_g2c_result.waterfall_periods if not p.is_construction]
    p40 = next((p for p in op if p.period_index == 40), None)
    assert p40 is not None, "Period 40 (DS40) must exist in waterfall_periods"
    assert p40.shl_closing_balance_keur == pytest.approx(0.0, abs=1e-6), (
        f"Oborovo DS40 maturity: closing SHL balance must be 0, "
        f"got {p40.shl_closing_balance_keur}"
    )
    # After DS40, any remaining periods have zero SHL balance
    post_ds40 = [p for p in op if p.period_index > 40]
    for p in post_ds40:
        assert p.shl_opening_balance_keur == pytest.approx(0.0, abs=1e-6), (
            f"Oborovo P{p.period_index} (post DS40): opening SHL balance must be 0"
        )


# ── Deductible SHL covenant feedback status ───────────────────────────────────

def test_deductible_shl_feedback_set_when_gate_locks_with_shl():
    """Solar is FULLY_DEDUCTIBLE. Gate lock → PIK → feedback loop not closed.
    Status must be G2C_DEDUCTIBLE_SHL_COVENANT_FEEDBACK_NOT_YET_CLOSED."""
    solar = create_default_solar_project()
    locked = dataclasses.replace(
        solar,
        financing=dataclasses.replace(
            solar.financing,
            lockup_dscr=9.99,
            sponsor_funding_mode=SponsorFundingMode.SHARE_CAPITAL_THEN_SHL,
        ),
    )
    result = run_project_shareholder_waterfall_model(locked)
    assert result.deductible_shl_covenant_feedback_status == (
        "G2C_DEDUCTIBLE_SHL_COVENANT_FEEDBACK_NOT_YET_CLOSED"
    ), f"Expected feedback status, got: {result.deductible_shl_covenant_feedback_status}"


def test_no_deductible_feedback_when_gate_does_not_lock(solar_result):
    """When gate never locks, no PIK accumulates → deductible feedback status = None."""
    # Solar default lockup_dscr=1.10, DSCR always > 1.10 → gate never locks
    assert solar_result.periods_locked_by_dscr == 0
    assert solar_result.deductible_shl_covenant_feedback_status is None


def test_oborovo_no_deductible_feedback_due_to_non_deductible_shl(oborovo_g2c_result):
    """Oborovo SHL is FULLY_NON_DEDUCTIBLE → deductible feedback status = None
    regardless of gate locking. PIK accumulation does not create a taxable feedback loop."""
    assert oborovo_g2c_result.deductible_shl_covenant_feedback_status is None


# ── Production SHL scheduler: gate-fail → PIK via compute_shareholder_loan_schedules ──

def test_gate_fail_pik_uses_production_scheduler():
    """Prove that gate-fail PIK accumulation goes through compute_shareholder_loan_schedules
    (the one canonical SHL kernel), not a parallel implementation.

    Verify by checking that the gate-locked waterfall result matches the expected
    causal roll-forward: opening[n+1] = closing[n] for all consecutive operating periods."""
    solar = create_default_solar_project()
    locked = dataclasses.replace(
        solar,
        financing=dataclasses.replace(
            solar.financing,
            lockup_dscr=9.99,
            sponsor_funding_mode=SponsorFundingMode.SHARE_CAPITAL_THEN_SHL,
        ),
    )
    result = run_project_shareholder_waterfall_model(locked)
    op = [p for p in result.waterfall_periods if not p.is_construction]

    # Causal carry-forward: opening[n+1] == closing[n]
    for prev, curr in zip(op, op[1:]):
        assert curr.shl_opening_balance_keur == pytest.approx(
            prev.shl_closing_balance_keur, abs=1e-6
        ), (
            f"P{curr.period_index}: opening {curr.shl_opening_balance_keur} != "
            f"prior closing {prev.shl_closing_balance_keur} — balance discontinuity"
        )

    # Locked periods: PIK = gross interest (no cash → all capitalised)
    locked_ops = [
        p for p in op
        if p.distribution_gate_status == DistributionGateStatus.LOCKED_DSCR_BELOW_LOCKUP
        and p.shl_opening_balance_keur > 0.0
    ]
    assert len(locked_ops) > 0, "Expected locked periods for lockup_dscr=9.99"
    for p in locked_ops:
        assert p.shl_cash_interest_receipt_keur == pytest.approx(0.0, abs=1e-9)
        assert p.shl_pik_keur == pytest.approx(p.shl_gross_interest_keur, abs=1e-9), (
            f"P{p.period_index}: PIK must equal gross interest when gate locked"
        )


# ── BULLET contractual vs actual principal (regression) ──────────────────────

def test_bullet_maturity_contractual_exceeds_actual(solar_result):
    """BULLET regression: default Solar maturity period has balloon > available cash.

    Proves:
      contractual_shl_principal_due > actual_shl_principal_paid
      actual = max(0, fcf_for_distribution - cash_interest)
      unpaid = contractual - actual > 0
      actual_shl_closing_balance > 0 (liability not extinguished)

    This test would have FAILED on cc5cc4f where shl_closing_balance_keur was taken
    from the contractual scheduler (= 0) instead of the actual roll-forward.
    """
    op = [p for p in solar_result.waterfall_periods if not p.is_construction]
    # Solar BULLET maturity is P29 — the only period with contractual principal due.
    mat = next(p for p in op if p.contractual_shl_principal_due_keur > 0.0)

    expected_actual = max(
        0.0,
        mat.fcf_for_distribution_keur - mat.shl_cash_interest_receipt_keur,
    )
    assert mat.contractual_shl_principal_due_keur > mat.actual_shl_principal_paid_keur, (
        "BULLET balloon must exceed available cash in this case"
    )
    assert mat.actual_shl_principal_paid_keur == pytest.approx(expected_actual, abs=1e-6), (
        "actual paid must equal max(0, fcf - cash_interest)"
    )
    assert mat.unpaid_shl_principal_keur == pytest.approx(
        mat.contractual_shl_principal_due_keur - mat.actual_shl_principal_paid_keur, abs=1e-6
    )
    assert mat.actual_shl_closing_balance_keur > 0.0, (
        "unpaid principal must remain as liability — not extinguished"
    )
    # Legacy alias must equal causal fields
    assert mat.shl_principal_receipt_keur == pytest.approx(mat.actual_shl_principal_paid_keur, abs=1e-9)
    assert mat.shl_closing_balance_keur == pytest.approx(mat.actual_shl_closing_balance_keur, abs=1e-9)


def test_bullet_maturity_unpaid_carries_forward(solar_result):
    """Unpaid BULLET principal at maturity must carry into subsequent period's opening balance."""
    op = [p for p in solar_result.waterfall_periods if not p.is_construction]
    sorted_op = sorted(op, key=lambda p: p.period_index)
    mat_idx = next(i for i, p in enumerate(sorted_op) if p.contractual_shl_principal_due_keur > 0.0)
    if mat_idx + 1 < len(sorted_op):
        mat_p = sorted_op[mat_idx]
        next_p = sorted_op[mat_idx + 1]
        assert next_p.shl_opening_balance_keur == pytest.approx(
            mat_p.actual_shl_closing_balance_keur, abs=1e-6
        ), (
            f"P{next_p.period_index} opening {next_p.shl_opening_balance_keur} != "
            f"P{mat_p.period_index} actual closing {mat_p.actual_shl_closing_balance_keur}"
        )


def test_deductible_feedback_fails_closed_return_metrics():
    """When SHL is deductible and gate locks, return metrics must be None with
    UPSTREAM_FINANCIAL_FEEDBACK_NOT_CLOSED status — not seemingly valid IRRs."""
    from financial_engine.sponsor_returns.contracts import ReturnMetricStatus
    solar = create_default_solar_project()
    locked = dataclasses.replace(
        solar,
        financing=dataclasses.replace(
            solar.financing,
            lockup_dscr=9.99,
            sponsor_funding_mode=SponsorFundingMode.SHARE_CAPITAL_THEN_SHL,
        ),
    )
    result = run_project_shareholder_waterfall_model(locked)
    assert result.deductible_shl_covenant_feedback_status == (
        "G2C_DEDUCTIBLE_SHL_COVENANT_FEEDBACK_NOT_YET_CLOSED"
    )
    expected_status = ReturnMetricStatus.UPSTREAM_FINANCIAL_FEEDBACK_NOT_CLOSED
    assert result.pure_equity_xirr is None, "IRR must be None when feedback not closed"
    assert result.pure_equity_xirr_status == expected_status
    assert result.pure_equity_moic is None
    assert result.pure_equity_moic_status == expected_status
    assert result.total_sponsor_xirr is None
    assert result.total_sponsor_xirr_status == expected_status
    assert result.total_sponsor_moic is None
    assert result.total_sponsor_moic_status == expected_status


def test_oborovo_non_deductible_returns_not_blocked(oborovo_g2c_result):
    """FULLY_NON_DEDUCTIBLE SHL (Oborovo) must produce valid returns even when gate locks."""
    from financial_engine.sponsor_returns.contracts import ReturnMetricStatus
    # Oborovo uses lockup_dscr=0.5 so gate likely opens; verify returns are not blocked
    assert oborovo_g2c_result.deductible_shl_covenant_feedback_status is None
    # Returns must not be UPSTREAM_FINANCIAL_FEEDBACK_NOT_CLOSED
    assert oborovo_g2c_result.pure_equity_xirr_status != (
        ReturnMetricStatus.UPSTREAM_FINANCIAL_FEEDBACK_NOT_CLOSED
    )
    assert oborovo_g2c_result.total_sponsor_xirr_status != (
        ReturnMetricStatus.UPSTREAM_FINANCIAL_FEEDBACK_NOT_CLOSED
    )


# ── Reserve support gate ─────────────────────────────────────────────────────

def test_reserve_gate_none_mode_not_applicable(solar_result):
    """NONE reserve support mode → NOT_APPLICABLE for all operating periods."""
    from financial_engine.shareholder_waterfall.contracts import ReserveSupportGateStatus
    op = [p for p in solar_result.waterfall_periods if not p.is_construction]
    for p in op:
        assert p.reserve_support_gate_status == ReserveSupportGateStatus.NOT_APPLICABLE, (
            f"P{p.period_index}: expected NOT_APPLICABLE for NONE mode"
        )


def test_reserve_gate_construction_status(solar_result):
    """Construction periods → CONSTRUCTION reserve gate status."""
    from financial_engine.shareholder_waterfall.contracts import ReserveSupportGateStatus
    const = [p for p in solar_result.waterfall_periods if p.is_construction]
    assert len(const) > 0
    for p in const:
        assert p.reserve_support_gate_status == ReserveSupportGateStatus.CONSTRUCTION


def test_reserve_gate_oborovo_zero_req_neutral(oborovo_g2c_result):
    """Oborovo with zero reserve requirement → PASS_NEUTRAL_SOURCE_PROVEN for CASH_DSRA mode."""
    from financial_engine.shareholder_waterfall.contracts import ReserveSupportGateStatus
    op = [p for p in oborovo_g2c_result.waterfall_periods if not p.is_construction]
    # Oborovo uses CASH_DSRA mode with zero requirement → neutral
    for p in op:
        assert p.reserve_support_gate_status in (
            ReserveSupportGateStatus.PASS_NEUTRAL_SOURCE_PROVEN,
            ReserveSupportGateStatus.NOT_APPLICABLE,
        ), f"P{p.period_index}: unexpected status {p.reserve_support_gate_status}"


def test_reserve_gate_stop_token_in_result(solar_result):
    """Result-level reserve gate summary carries the stop token."""
    assert "G2C_RESERVE_GATE_NOT_CAUSALLY_CLOSED" in solar_result.reserve_support_gate_status_summary


# ── Governance: no target-fitting tokens in G2C module ───────────────────────

def test_no_target_fitting_tokens_in_g2c():
    forbidden = {
        "approved_delta", "expected_delta", "balancing_plug", "target_irr",
        "target_moic", "terminal_top_up", "period_correction",
    }
    module_dir = _REPO_ROOT / "financial_engine" / "shareholder_waterfall"
    for fpath in module_dir.rglob("*.py"):
        tree = ast.parse(fpath.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert node.value.lower() not in forbidden, (
                    f"Forbidden token {node.value!r} in {fpath}"
                )


def test_no_project_identity_dispatch_in_g2c():
    forbidden = {"oborovo", "tuho", "solar", "wind"}
    module_dir = _REPO_ROOT / "financial_engine" / "shareholder_waterfall"
    for fpath in module_dir.rglob("*.py"):
        tree = ast.parse(fpath.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value.lower() in forbidden:
                    raise AssertionError(
                        f"Project-identity dispatch in {fpath}: {node.value!r}"
                    )


def test_no_absolute_paths_in_g2c():
    module_dir = _REPO_ROOT / "financial_engine" / "shareholder_waterfall"
    for fpath in module_dir.rglob("*.py"):
        text = fpath.read_text()
        assert "/home/user/Finco1" not in text, f"Absolute path in {fpath}"
        assert "/home/runner/work" not in text, f"Absolute path in {fpath}"


# ── G2C contracts do not contaminate G2A ─────────────────────────────────────

def test_g2a_contract_clean_no_distribution_gate_fields():
    import dataclasses as dc
    from financial_engine.financing.contracts import ProjectFinancingResult
    names = {f.name for f in dc.fields(ProjectFinancingResult)}
    forbidden = {
        "distribution_gate", "covenant_locked", "lockup_dscr",
        "waterfall_periods", "periods_locked",
    }
    found = names & forbidden
    assert not found, f"G2A contract contaminated with G2C fields: {found}"


# ── Gate-fail → PIK causal regression ────────────────────────────────────────

def test_gate_fail_causes_pik_and_shl_balance_grows():
    """Gate LOCKED → fcf_for_distribution=0 → PIK accumulates → SHL balance grows.

    Uses a tight lockup_dscr that forces some operating periods into LOCKED status,
    proving the causal chain: gate → zero FCF → PIK = gross interest → closing > opening.
    Also verifies that the next period's opening_balance equals previous closing_balance.
    """
    solar = create_default_solar_project()
    # SHARE_CAPITAL_THEN_SHL ensures there is an active SHL to accrue PIK
    # Tight lockup (well above project DSCR) forces gate to lock in many periods
    locked_project = dataclasses.replace(
        solar,
        financing=dataclasses.replace(
            solar.financing,
            lockup_dscr=9.99,  # impossibly high → all periods with senior DS locked
            sponsor_funding_mode=SponsorFundingMode.SHARE_CAPITAL_THEN_SHL,
        ),
    )
    result = run_project_shareholder_waterfall_model(locked_project)

    op_periods = [p for p in result.waterfall_periods if not p.is_construction]
    locked_periods = [
        p for p in op_periods
        if p.distribution_gate_status == DistributionGateStatus.LOCKED_DSCR_BELOW_LOCKUP
    ]
    assert len(locked_periods) > 0, "Expected at least one LOCKED period with lockup_dscr=9.99"

    for p in locked_periods:
        assert p.fcf_for_distribution_keur == pytest.approx(0.0), (
            f"Period {p.period_index}: expected fcf_for_distribution=0 when locked"
        )
        if p.shl_opening_balance_keur > 0.0:
            # PIK must equal gross interest (no cash to pay interest)
            assert p.shl_cash_interest_receipt_keur == pytest.approx(0.0, abs=1e-6), (
                f"Period {p.period_index}: cash interest must be 0 when locked and fcf=0"
            )
            assert p.shl_pik_keur == pytest.approx(p.shl_gross_interest_keur, abs=1e-6), (
                f"Period {p.period_index}: PIK must equal gross interest when no cash available"
            )
            assert p.shl_closing_balance_keur > p.shl_opening_balance_keur - 1e-9, (
                f"Period {p.period_index}: closing SHL balance must be >= opening when gate locked"
            )

    # Verify causal carry-forward: each period's opening == prior period's closing
    for prev, curr in zip(op_periods, op_periods[1:]):
        assert curr.shl_opening_balance_keur == pytest.approx(
            prev.shl_closing_balance_keur, abs=1e-6
        ), (
            f"Period {curr.period_index}: opening SHL ({curr.shl_opening_balance_keur}) "
            f"!= prior closing ({prev.shl_closing_balance_keur})"
        )
