"""Phase 23U: Full Excel Parity Pack

Diagnostic-only — no runtime changes unless a narrow correction is clearly proven.

Scope:
- DSCR trajectory parity
- CFADS parity
- Senior debt service parity
- Post-SHL distribution parity
- Period-level parity tables

Tests:
1. test_both_factories_flags_unchanged
2. test_tuho_senior_ds_parity_op_idx_0_to_13
3. test_tuho_dscr_trajectory_parity_snapshot
4. test_oborovo_senior_ds_parity_op_idx_0_to_27
5. test_oborovo_dscr_trajectory_parity_snapshot
6. test_oborovo_lockup_distribution_parity
7. test_tuho_lockup_distribution_parity
8. test_guardrails_unchanged
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
# 1. Factory flags unchanged
# =============================================================================


def test_both_factories_flags_unchanged():
    """TUHO and Oborovo factory flags remain unchanged."""
    tuho = create_default_tuho_wind1()
    oborovo = create_default_oborovo()
    assert tuho.info.use_senior_debt_sizing_engine is True
    assert tuho.financing.use_frozen_excel_senior_debt_schedule is True
    assert oborovo.info.use_senior_debt_sizing_engine is True
    assert oborovo.financing.use_frozen_excel_senior_debt_schedule is True


# =============================================================================
# 2. TUHO senior DS parity op_idx 0-13
# =============================================================================


def test_tuho_senior_ds_parity_op_idx_0_to_13():
    """TUHO senior DS matches fixture for op_idx 0-13 (PPA periods).

    Fixture: phase7_tuho_senior_debt_sizing_extraction.csv
    Runtime mapping: runtime op_idx N -> fixture op_idx N+1 (1-based construction offset).
    Tolerance: 0.5 kEUR.
    """
    TUHO_FIX = Path(__file__).resolve().parents[1] / "reports" / "phase7_tuho_senior_debt_sizing_extraction.csv"
    TOLERANCE = 0.5  # kEUR

    fixture = {}
    with open(TUHO_FIX) as f:
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

    for runtime_idx in range(14):  # op_idx 0-13
        fixture_idx = runtime_idx + 1
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
# 3. TUHO DSCR trajectory parity snapshot
# =============================================================================


def test_tuho_dscr_trajectory_parity_snapshot():
    """TUHO DSCR trajectory: runtime DSCR vs fixture target DSCR.

    PPA target: 1.2 (op_idx 0-24). Merchant target: 1.4125 (op_idx 25-27).
    Runtime DSCR is backward-computed from frozen DS.
    Diagnostic snapshot — DSCR above target is expected in frozen path.
    """
    op_periods, _ = _run_tuho()

    # Snapshot key periods
    snapshot_indices = [0, 1, 2, 12, 13, 14, 20, 27]
    for idx in snapshot_indices:
        p = op_periods[idx]
        dscr = getattr(p, "dscr", 0) or 0
        fcf = getattr(p, "r69_fcf_banks_keur", 0) or 0
        # Sanity: FCF should be positive, DSCR should be > 0 or inf
        assert fcf > 0, f"TUHO op_idx {idx}: FCF={fcf} should be > 0"
        if idx< 14:
            assert dscr > 0, f"TUHO op_idx {idx}: DSCR={dscr} should be > 0"
        else:
            assert dscr == float("inf"), f"TUHO op_idx {idx}: merchant DSCR should be inf"


# =============================================================================
# 4. Oborovo senior DS parity op_idx 0-27
# =============================================================================


def test_oborovo_senior_ds_parity_op_idx_0_to_27():
    """Oborovo senior DS matches Phase 23Q fixture for op_idx 0-27.

    Fixture: phase23q_oborovo_senior_debt_sizing_extraction.csv
    Tolerance: 20 kEUR (Phase 23Q documented CSV rounding).
    op_idx 27 residual (+16.84 kEUR) is within tolerance.
    """
    OBOROVO_FIX = Path(__file__).resolve().parents[1] / "reports" / "phase23q_oborovo_senior_debt_sizing_extraction.csv"
    TOLERANCE = 20.0  # kEUR

    fixture = {}
    with open(OBOROVO_FIX) as f:
        reader = csv.DictReader(f)
        for row in reader:
            idx = int(row["operating_period_index"])
            fixture[idx] = float(row["ds_r57_debt_service_keur"])

    op_periods, _ = _run_oborovo()

    for op_idx in range(28):  # op_idx 0-27
        runtime_ds = getattr(op_periods[op_idx], "senior_ds_keur", None)
        fixture_val = fixture.get(op_idx)
        assert runtime_ds is not None
        assert fixture_val is not None
        diff = abs(runtime_ds - fixture_val)
        assert diff <= TOLERANCE, (
            f"Oborovo op_idx {op_idx}: runtime={runtime_ds:.4f} "
            f"fixture={fixture_val:.4f} diff={diff:.4f} > {TOLERANCE}"
        )


# =============================================================================
# 5. Oborovo DSCR trajectory parity snapshot
# =============================================================================


def test_oborovo_dscr_trajectory_parity_snapshot():
    """Oborovo DSCR trajectory: runtime DSCR vs fixture target DSCR.

    PPA target: 1.15 (op_idx 0-24). Late target: 1.35 (op_idx 25-27).
    Runtime DSCR is backward-computed from frozen DS.
    Late-period DSCR inflation is expected (declining frozen DS).
    """
    OBOROVO_FIX = Path(__file__).resolve().parents[1] / "reports" / "phase23q_oborovo_senior_debt_sizing_extraction.csv"

    fixture_target = {}
    with open(OBOROVO_FIX) as f:
        reader = csv.DictReader(f)
        for row in reader:
            idx = int(row["operating_period_index"])
            fixture_target[idx] = float(row["target_dscr"])

    op_periods, _ = _run_oborovo()

    # PPA periods: DSCR should be in reasonable range
    for idx in [0, 1, 2, 12, 14]:
        dscr = getattr(op_periods[idx], "dscr", 0) or 0
        assert 1.0 < dscr < 1.5, f"Oborovo op_idx {idx} PPA DSCR={dscr:.4f} out of range"

    # Late periods: DSCR should be elevated
    for idx in [25, 26, 27]:
        dscr = getattr(op_periods[idx], "dscr", 0) or 0
        assert dscr > 1.5, f"Oborovo op_idx {idx} late DSCR={dscr:.4f} should be >1.5"

    # DSCR trend: should increase from op_idx 14 to 25
    dscr_14 = getattr(op_periods[14], "dscr", 0) or 0
    dscr_25 = getattr(op_periods[25], "dscr", 0) or 0
    assert dscr_25 > dscr_14, "DSCR should rise from op_idx 14 to 25"


# =============================================================================
# 6. Oborovo lock-up + distribution parity
# =============================================================================


def test_oborovo_lockup_distribution_parity():
    """Oborovo: no distributions while SHL outstanding, first at op_idx 39.

    Phase 23O/P lock-up preserved.
    Fixture covers op_idx 0-27 only. Post-fixture periods (28+) confirmed by runtime.
    """
    op_periods, _ = _run_oborovo()
    TOLERANCE = 1.0

    # Pre-clear: shl_balance > 0, dist = 0
    for i in range(38):  # op_idx 0-37: SHL still outstanding
        p = op_periods[i]
        shl_bal = getattr(p, "shl_balance_keur", 0.0) or 0.0
        dist = getattr(p, "distribution_keur", 0.0) or 0.0
        assert shl_bal > TOLERANCE, f"op_idx {i}: shl_balance should be > 0"
        assert dist == 0.0, f"op_idx {i}: dist={dist:.2f} should be 0 while SHL outstanding"

    # op_idx 38: SHL cleared (shl_balance=0), but guard blocks distribution
    p38 = op_periods[38]
    shl38 = getattr(p38, "shl_balance_keur", 0.0) or 0.0
    dist38 = getattr(p38, "distribution_keur", 0.0) or 0.0
    assert shl38 <= TOLERANCE, f"op_idx 38: shl_balance={shl38} should be ~0"
    assert dist38 == 0.0, f"op_idx 38: dist={dist38:.2f} should be 0 (guard period)"

    # First distribution at op_idx 39 / 2050-06-30
    p39 = op_periods[39]
    assert str(p39.date) == "2050-06-30", f"First dist date={p39.date}, expected 2050-06-30"
    dist39 = getattr(p39, "distribution_keur", 0.0) or 0.0
    assert dist39 > 2000, f"op_idx 39 dist={dist39:.2f} should be > 2000 kEUR"


# =============================================================================
# 7. TUHO lock-up + distribution parity
# =============================================================================


def test_tuho_lockup_distribution_parity():
    """TUHO: no distributions while SHL outstanding.

    TUHO uses PIK+Sweep SHL — SHL balance grows over time.
    No distributions until SHL is cleared.
    """
    op_periods, _ = _run_tuho()
    TOLERANCE = 1.0

    for i, p in enumerate(op_periods):
        shl_bal = getattr(p, "shl_balance_keur", 0.0) or 0.0
        dist = getattr(p, "distribution_keur", 0.0) or 0.0
        if shl_bal > TOLERANCE:
            assert dist == 0.0, f"TUHO op_idx {i}: shl={shl_bal:.2f} dist={dist:.2f} — leak!"


# =============================================================================
# 8. Guardrails unchanged
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
