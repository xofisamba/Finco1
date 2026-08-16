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


def test_covenant_gate_does_not_lock_shl_receipts():
    """DSCR lockup affects equity distributions only — SHL cash receipts are not gated."""
    solar_tight = _solar_with_lockup(1.25)
    solar_default = _solar_with_lockup(1.10)
    total_tight_shl = (
        solar_tight.total_shl_cash_interest_received_keur
        + solar_tight.total_shl_principal_received_keur
    )
    total_default_shl = (
        solar_default.total_shl_cash_interest_received_keur
        + solar_default.total_shl_principal_received_keur
    )
    assert abs(total_tight_shl - total_default_shl) < 1e-6, (
        "SHL receipts must not change when DSCR lockup threshold changes"
    )


# ── Gate partition: covenant_locked + distribution = pre_gate_distribution ────

def test_gate_partition_holds_all_operating_periods(solar_result):
    """covenant_locked + distribution = pre_gate_distribution for all operating periods."""
    for p in solar_result.waterfall_periods:
        if p.is_construction:
            continue
        partition = p.covenant_locked_keur + p.legal_equity_distribution_keur
        assert abs(partition - p.pre_gate_distribution_keur) < 1e-9, (
            f"P{p.period_index}: partition fails: {partition} != {p.pre_gate_distribution_keur}"
        )


def test_gate_partition_holds_tight_lockup():
    result = _solar_equity_only_with_lockup(1.25)
    for p in result.waterfall_periods:
        if p.is_construction:
            continue
        partition = p.covenant_locked_keur + p.legal_equity_distribution_keur
        assert abs(partition - p.pre_gate_distribution_keur) < 1e-9


# ── Cash conservation invariant ───────────────────────────────────────────────

def test_cash_conservation_solar(solar_result):
    """actual_int + actual_prin + distribution <= max(0, signed_post_senior) per period."""
    for p in solar_result.waterfall_periods:
        if p.is_construction:
            continue
        total_out = (
            p.shl_cash_interest_receipt_keur
            + p.shl_principal_receipt_keur
            + p.legal_equity_distribution_keur
        )
        available = max(0.0, p.signed_post_senior_keur)
        assert total_out <= available + 1e-6, (
            f"P{p.period_index}: conservation violated: out={total_out:.4f}, avail={available:.4f}"
        )


def test_cash_conservation_wind(wind_result):
    for p in wind_result.waterfall_periods:
        if p.is_construction:
            continue
        total_out = (
            p.shl_cash_interest_receipt_keur
            + p.shl_principal_receipt_keur
            + p.legal_equity_distribution_keur
        )
        available = max(0.0, p.signed_post_senior_keur)
        assert total_out <= available + 1e-6, (
            f"P{p.period_index}: conservation violated"
        )


def test_cash_conservation_tight_lockup():
    """Conservation must hold when gate locks distributions."""
    result = _solar_equity_only_with_lockup(1.25)
    for p in result.waterfall_periods:
        if p.is_construction:
            continue
        total_out = (
            p.shl_cash_interest_receipt_keur
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


# ── G2B consistent return metrics at default lockup ──────────────────────────

def test_solar_return_metrics_match_g2b_at_default_lockup(solar_result):
    """G2C with default lockup_dscr=1.10 → same PE/TS returns as G2B (gate doesn't bind)."""
    assert abs(solar_result.pure_equity_xirr - 0.349346) < 1e-4
    assert abs(solar_result.total_sponsor_xirr - 0.127516) < 1e-4
    assert abs(solar_result.pure_equity_moic - 60.176) < 1e-2
    assert abs(solar_result.total_sponsor_moic - 5.009) < 1e-2


def test_wind_return_metrics_match_g2b_at_default_lockup(wind_result):
    assert abs(wind_result.pure_equity_xirr - 0.608989) < 1e-4
    assert abs(wind_result.total_sponsor_xirr - 0.176984) < 1e-4
    assert abs(wind_result.pure_equity_moic - 208.678) < 1e-2
    assert abs(wind_result.total_sponsor_moic - 11.286) < 1e-2


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


def test_total_covenant_plus_distributions_equals_sum_pre_gate(solar_result):
    per_period_sum = sum(p.pre_gate_distribution_keur for p in solar_result.waterfall_periods)
    total_both = (
        solar_result.total_covenant_locked_keur
        + solar_result.total_legal_equity_distributions_keur
    )
    assert abs(total_both - per_period_sum) < 1e-6


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
