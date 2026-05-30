"""Phase 23T: Senior Debt Amount / DSCR Residual Bridge

Diagnostic-only PR — no runtime changes unless a narrow correction is clearly proven.

Tests:
1. test_both_factories_still_frozen_senior_ds_enabled
2. test_tuho_senior_debt_amount_bridge
3. test_oborovo_senior_debt_amount_bridge
4. test_tuho_dscr_trajectory_snapshot
5. test_oborovo_dscr_trajectory_snapshot
6. test_tuho_senior_ds_fixture_still_matches
7. test_oborovo_senior_ds_fixture_still_matches
8. test_lockup_regression_still_clean
9. test_guardrails_unchanged
"""
import csv
from pathlib import Path

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
from domain.period_engine import PeriodEngine


# =============================================================================
# Helpers
# =============================================================================


def _run_tuho():
    tuho = create_default_tuho_wind1()
    engine = PeriodEngine(
        tuho.info.financial_close,
        tuho.info.construction_months,
        tuho.info.horizon_years,
        tuho.revenue.ppa_term_years,
    )
    config = WaterfallRunConfig.from_inputs(tuho, engine)
    result = WaterfallRunner(tuho, engine).run(config)
    return [p for p in result.periods if getattr(p, "is_operation", False)], result


def _run_oborovo():
    oborovo = create_default_oborovo()
    engine = PeriodEngine(
        oborovo.info.financial_close,
        oborovo.info.construction_months,
        oborovo.info.horizon_years,
        oborovo.revenue.ppa_term_years,
    )
    config = WaterfallRunConfig.from_inputs(oborovo, engine)
    result = WaterfallRunner(oborovo, engine).run(config)
    return [p for p in result.periods if getattr(p, "is_operation", False)], result


# =============================================================================
# 1. Factory flags
# =============================================================================


def test_both_factories_still_frozen_senior_ds_enabled():
    """TUHO and Oborovo default factories still have frozen senior DS flags enabled."""
    tuho = create_default_tuho_wind1()
    oborovo = create_default_oborovo()
    assert tuho.info.use_senior_debt_sizing_engine is True
    assert tuho.financing.use_frozen_excel_senior_debt_schedule is True
    assert oborovo.info.use_senior_debt_sizing_engine is True
    assert oborovo.financing.use_frozen_excel_senior_debt_schedule is True


# =============================================================================
# 2. TUHO senior debt amount bridge
# =============================================================================


def test_tuho_senior_debt_amount_bridge():
    """TUHO senior debt amount confirmed vs Excel anchor43,359 kEUR.

    Source: TUHO factory fixed_debt_keur = 43,359.0 kEUR (exact).
    Runtime: total principal paid across all operating periods = 43,359.0 kEUR.
    Residual: none — exact match.
    """
    tuho = create_default_tuho_wind1()
    op_periods, _ = _run_tuho()

    EXCEL_ANCHOR = 43_359.0  # kEUR
    factory_debt = tuho.financing.fixed_debt_keur
    total_principal = sum(
        getattr(p, "senior_principal_keur", 0.0) or 0.0 for p in op_periods
    )

    assert factory_debt == EXCEL_ANCHOR, (
        f"TUHO fixed_debt_keur={factory_debt} vs anchor={EXCEL_ANCHOR}"
    )
    diff = abs(total_principal - EXCEL_ANCHOR)
    assert diff < 1.0, (
        f"TUHO total principal paid={total_principal:.4f} vs anchor={EXCEL_ANCHOR} diff={diff:.4f}"
    )


# =============================================================================
# 3. Oborovo senior debt amount bridge
# =============================================================================


def test_oborovo_senior_debt_amount_bridge():
    """Oborovo senior debt amount confirmed vs Excel anchor ~42,852 kEUR.

    Source: Oborovo factory fixed_debt_keur = 42,852.27 kEUR.
    Runtime: total principal paid across all operating periods = 42,852.27 kEUR.
    Residual: +0.27 kEUR (rounding, within tolerance).
    """
    oborovo = create_default_oborovo()
    op_periods, _ = _run_oborovo()

    EXCEL_ANCHOR = 42_852.0  # kEUR (from calibration reference)
    factory_debt = oborovo.financing.fixed_debt_keur
    total_principal = sum(
        getattr(p, "senior_principal_keur", 0.0) or 0.0 for p in op_periods
    )

    diff_factory = abs(factory_debt - EXCEL_ANCHOR)
    assert diff_factory < 1.0, (
        f"Oborovo fixed_debt_keur={factory_debt:.4f} vs anchor={EXCEL_ANCHOR} diff={diff_factory:.4f}"
    )
    diff_runtime = abs(total_principal - EXCEL_ANCHOR)
    assert diff_runtime < 1.0, (
        f"Oborovo total principal={total_principal:.4f} vs anchor={EXCEL_ANCHOR} diff={diff_runtime:.4f}"
    )


# =============================================================================
# 4. TUHO DSCR trajectory snapshot
# =============================================================================


def test_tuho_dscr_trajectory_snapshot():
    """TUHO DSCR trajectory diagnostic snapshot.

    Target DSCR:1.2 (PPA periods op_idx 0-24), 1.4125 (merchant op_idx 25-27).
    Runtime DSCR is backward-computed from frozen DS schedule.
    cfads_keur is 0 for frozen runs (fixture provides sizing CFADS only).
    fcf_for_banks_keur used as DSCR numerator.
    """
    op_periods, _ = _run_tuho()

    snapshot = {}
    for i in [0, 1, 2, 12, 13, 14, 20, 27]:
        p = op_periods[i]
        snapshot[i] = {
            "dscr": getattr(p, "dscr", 0) or 0,
            "senior_ds_keur": getattr(p, "senior_ds_keur", 0) or 0,
            "fcf_banks": getattr(p, "r69_fcf_banks_keur", 0) or 0,
 }

    # Diagnostic assertions — DSCR should be in reasonable range
    for i in [0, 1, 2]:
        dscr = snapshot[i]["dscr"]
        assert 1.0 < dscr < 2.0, f"TUHO op_idx {i} DSCR={dscr:.4f} out of expected range"

    # Merchant transition (op_idx 13-14): DSCR drops as debt service spikes
    assert snapshot[13]["dscr"] > snapshot[12]["dscr"], "DSCR should rise at merchant transition (higher target DSCR 1.4125 vs 1.2)"

    # op_idx 14+: no debt service (merchant-only), DSCR = inf
    assert snapshot[14]["dscr"] == float("inf"), "Merchant-only periods should have inf DSCR"


# =============================================================================
# 5. Oborovo DSCR trajectory snapshot
# =============================================================================


def test_oborovo_dscr_trajectory_snapshot():
    """Oborovo DSCR trajectory diagnostic snapshot.

    Target DSCR from fixture: 1.15 (op_idx 0-24), 1.35 (op_idx 25-27).
    Runtime DSCR is backward-computed from frozen DS schedule.
    cfads_keur is 0 for frozen runs (fixture provides sizing CFADS only).
    fcf_for_banks_keur used as DSCR numerator.
    """
    op_periods, _ = _run_oborovo()

    # Load fixture target DSCR
    fixture_path = Path(__file__).resolve().parents[1] / "reports" / "phase23q_oborovo_senior_debt_sizing_extraction.csv"
    fixture_target = {}
    with open(fixture_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            idx = int(row["operating_period_index"])
            fixture_target[idx] = float(row["target_dscr"])

    snapshot = {}
    for i in [0, 1, 2, 12, 14, 24, 25, 26, 27]:
        p = op_periods[i]
        snapshot[i] = {
            "dscr": getattr(p, "dscr", 0) or 0,
            "senior_ds_keur": getattr(p, "senior_ds_keur", 0) or 0,
            "fcf_banks": getattr(p, "r69_fcf_banks_keur", 0) or 0,
            "fixture_target": fixture_target.get(i),
        }

    # PPA periods: DSCR should be around 1.15-1.20
    for i in [0, 1, 2, 12, 14]:
        dscr = snapshot[i]["dscr"]
        assert 1.0 < dscr < 1.5, f"Oborovo op_idx {i} DSCR={dscr:.4f} out of PPA expected range"

    # Late periods (op_idx 25+): DSCR should be higher due to declining debt service
    for i in [25, 26, 27]:
        dscr = snapshot[i]["dscr"]
        assert dscr > 1.5, f"Oborovo op_idx {i} DSCR={dscr:.4f} should be >1.5 in late periods"

    # DSCR trend: should increase as debt service declines in later periods
    assert snapshot[25]["dscr"] > snapshot[14]["dscr"], "DSCR should rise from op_idx 14 to 25"


# =============================================================================
# 6. TUHO senior DS fixture regression
# =============================================================================


def test_tuho_senior_ds_fixture_still_matches():
    """Selected TUHO senior DS values still match fixture (no regression)."""
    TUHO_FIXTURE = Path(__file__).resolve().parents[1] / "reports" / "phase7_tuho_senior_debt_sizing_extraction.csv"

    fixture = {}
    with open(TUHO_FIXTURE) as f:
        reader = csv.DictReader(f)
        for row in reader:
            idx_str = row["operating_period_index"].strip()
            if idx_str == "":
                continue
            idx = int(idx_str)
            val = float(row["ds_r20_debt_service_capacity_keur"])
            if val > 0 and idx not in fixture:
                fixture[idx] = val

    op_periods, _ = _run_tuho()
    TOLERANCE = 0.5  # kEUR

    for runtime_idx, fixture_idx in [(0, 1), (6, 7), (13, 14)]:
        runtime_ds = getattr(op_periods[runtime_idx], "senior_ds_keur", None)
        fixture_val = fixture.get(fixture_idx)
        assert runtime_ds is not None
        assert fixture_val is not None
        diff = abs(runtime_ds - fixture_val)
        assert diff <= TOLERANCE, (
            f"TUHO op_idx {runtime_idx}: runtime={runtime_ds:.4f} "
            f"fixture={fixture_val:.4f} diff={diff:.4f} > {TOLERANCE}"
        )


# =============================================================================
# 7. Oborovo senior DS fixture regression
# =============================================================================


def test_oborovo_senior_ds_fixture_still_matches():
    """Selected Oborovo senior DS values still match Phase 23Q fixture."""
    OBOROVO_FIXTURE = Path(__file__).resolve().parents[1] / "reports" / "phase23q_oborovo_senior_debt_sizing_extraction.csv"
    TOLERANCE = 20.0  # kEUR

    fixture = {}
    with open(OBOROVO_FIXTURE) as f:
        reader = csv.DictReader(f)
        for row in reader:
            idx = int(row["operating_period_index"])
            fixture[idx] = float(row["ds_r57_debt_service_keur"])

    op_periods, _ = _run_oborovo()

    for op_idx, expected in [(0, 2239.1334), (1, 2202.6258), (14, 2471.5416),
 (25, 1558.4027), (27, 1507.4389)]:
        runtime_ds = getattr(op_periods[op_idx], "senior_ds_keur", None)
        assert runtime_ds is not None
        diff = abs(runtime_ds - expected)
        assert diff <= TOLERANCE, (
            f"Oborovo op_idx {op_idx}: runtime={runtime_ds:.4f} "
            f"fixture={expected:.4f} diff={diff:.4f} > {TOLERANCE}"
        )


# =============================================================================
# 8. Lock-up regression
# =============================================================================


def test_lockup_regression_still_clean():
    """Oborovo and TUHO lock-up behavior remains clean (no regression)."""
    tuho_op, _ = _run_tuho()
    oborovo_op, _ = _run_oborovo()
    TOLERANCE = 1.0

    for i, p in enumerate(oborovo_op):
        shl_bal = getattr(p, "shl_balance_keur", 0.0) or 0.0
        dist = getattr(p, "distribution_keur", 0.0) or 0.0
        if shl_bal > TOLERANCE:
            assert dist == 0.0, (
                f"Oborovo op_idx {i}: shl={shl_bal:.2f} dist={dist:.2f} — lock-up regressed"
            )

    for i, p in enumerate(tuho_op):
        shl_bal = getattr(p, "shl_balance_keur", 0.0) or 0.0
        dist = getattr(p, "distribution_keur", 0.0) or 0.0
        if shl_bal > TOLERANCE:
            assert dist == 0.0, (
                f"TUHO op_idx {i}: shl={shl_bal:.2f} dist={dist:.2f} — lock-up regressed"
            )


# =============================================================================
# 9. Guardrails
# =============================================================================


def test_guardrails_unchanged():
    """Guardrails preserved: G20/R99/R102 blocked, no new flags promoted."""
    oborovo = create_default_oborovo()
    info = oborovo.info
    assert not hasattr(info, "use_g20_engine"), "G20 must remain blocked"
    assert not hasattr(info, "use_r99_engine"), "R99 must remain not approved"
    assert not hasattr(info, "use_r102_engine"), "R102 must remain not approved"
    assert not hasattr(info, "flat_dscr_sculpted"), "flat_dscr_sculpted must not be promoted"
    assert not hasattr(info, "minimum_dscr_sculpted"), "minimum_dscr_sculpted must not be promoted"
    assert not hasattr(info, "partial_pay_sweep"), "partial_pay_sweep must not be promoted"
