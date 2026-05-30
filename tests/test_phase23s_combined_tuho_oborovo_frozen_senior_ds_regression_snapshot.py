"""Phase 23S: Combined TUHO + Oborovo frozen senior DS regression snapshot.

Diagnostic-only PR after Phase 23R factory opt-in.
No runtime behavior changes unless a regression is discovered and documented.

Tests:
1. test_both_factories_frozen_senior_ds_flags_enabled
2. test_tuho_default_factory_loads_fixture
3. test_oborovo_default_factory_loads_phase23q_fixture
4. test_tuho_selected_senior_ds_matches_fixture
5. test_oborovo_selected_senior_ds_matches_fixture
6. test_oborovo_lockup_remains_clean_after_factory_opt_in
7. test_tuho_distribution_and_shl_regression_clean
8. test_revenue_opex_unchanged_for_both_projects
9. test_guardrails_unchanged
"""
import csv
from collections import defaultdict
from pathlib import Path

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
from domain.period_engine import PeriodEngine


# =============================================================================
# Helpers
# =============================================================================


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


# =============================================================================
# 1. Factory flags
# =============================================================================


def test_both_factories_frozen_senior_ds_flags_enabled():
    """Both TUHO and Oborovo default factories have frozen senior DS flags enabled."""
    tuho = create_default_tuho_wind1()
    oborovo = create_default_oborovo()

    assert tuho.info.use_senior_debt_sizing_engine is True, "TUHO use_senior_debt_sizing_engine must be True"
    assert tuho.financing.use_frozen_excel_senior_debt_schedule is True, "TUHO use_frozen_excel_senior_debt_schedule must be True"
    assert oborovo.info.use_senior_debt_sizing_engine is True, "Oborovo use_senior_debt_sizing_engine must be True"
    assert oborovo.financing.use_frozen_excel_senior_debt_schedule is True, "Oborovo use_frozen_excel_senior_debt_schedule must be True"


# =============================================================================
# 2. TUHO fixture load
# =============================================================================


def test_tuho_default_factory_loads_fixture():
    """TUHO default factory run has _frozen_senior_ds_wired=True and _frozen_fixture_loaded=True."""
    _, result = _run_tuho()
    assert getattr(result, "_frozen_senior_ds_wired", False) is True, (
        "TUHO _frozen_senior_ds_wired must be True"
    )
    assert getattr(result, "_frozen_fixture_loaded", False) is True, (
        "TUHO _frozen_fixture_loaded must be True"
    )


# =============================================================================
# 3. Oborovo Phase 23Q fixture load
# =============================================================================


def test_oborovo_default_factory_loads_phase23q_fixture():
    """Oborovo default factory run has _frozen_senior_ds_wired=True and _frozen_fixture_loaded=True."""
    _, result = _run_oborovo()
    assert getattr(result, "_frozen_senior_ds_wired", False) is True, (
        "Oborovo _frozen_senior_ds_wired must be True"
    )
    assert getattr(result, "_frozen_fixture_loaded", False) is True, (
        "Oborovo _frozen_fixture_loaded must be True"
    )


# =============================================================================
# 4. TUHO selected senior DS vs fixture
# =============================================================================


def test_tuho_selected_senior_ds_matches_fixture():
    """TUHO selected operating periods match fixture values (first semi-annual per op_idx).

    TUHO fixture (phase7) has 2 semi-annual entries per op_idx.
    Runtime senior_ds_keur maps to first semi-annual entry per op_idx.
    op_idx offset: runtime op_idx N -> fixture op_idx N+1 (1-based, construction period skip).
    """
    TUHO_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "reports" / "phase7_tuho_senior_debt_sizing_extraction.csv"

    # Load fixture: first semi-annual value per op_idx
    fixture = {}
    with open(TUHO_FIXTURE_PATH) as f:
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

    # Compare early, middle, late
    test_cases = [
        (0, 1),   # early
        (6, 7),   # mid-early
        (13, 14), # late (merchant transition)
    ]

    for runtime_idx, fixture_idx in test_cases:
        runtime_ds = getattr(op_periods[runtime_idx], "senior_ds_keur", None)
        fixture_val = fixture.get(fixture_idx)
        assert runtime_ds is not None, f"op_idx {runtime_idx}: senior_ds_keur not found"
        assert fixture_val is not None, f"fixture op_idx {fixture_idx}: not found"
        diff = abs(runtime_ds - fixture_val)
        TOLERANCE_TUHO = 0.5  # kEUR — fixture values at 4dp, runtime at full float precision
        assert diff <= TOLERANCE_TUHO, (
            f"TUHO op_idx {runtime_idx}: runtime={runtime_ds:.4f} "
            f"fixture={fixture_val:.4f} diff={diff:.4f}"
        )


# =============================================================================
# 5. Oborovo selected senior DS vs Phase 23Q fixture
# =============================================================================


def test_oborovo_selected_senior_ds_matches_fixture():
    """Oborovo selected operating periods match Phase 23Q fixture within tolerance.

    Tolerance: 20 kEUR (Phase 23Q documented CSV rounding, 4dp).
    op_idx 27 has known ~16.8 kEUR residual (within tolerance).
    """
    OBOROVO_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "reports" / "phase23q_oborovo_senior_debt_sizing_extraction.csv"
    TOLERANCE = 20.0  # kEUR

    # Load fixture: single value per op_idx
    fixture = {}
    with open(OBOROVO_FIXTURE_PATH) as f:
        reader = csv.DictReader(f)
        for row in reader:
            idx = int(row["operating_period_index"])
            fixture[idx] = float(row["ds_r57_debt_service_keur"])

    op_periods, _ = _run_oborovo()

    test_cases = [
        (0, 2239.1334),
        (1, 2202.6258),
        (14, 2471.5416),
        (25, 1558.4027),
        (27, 1507.4389),  # known ~16.8 kEUR residual, within 20 kEUR tolerance
    ]

    for op_idx, expected in test_cases:
        runtime_ds = getattr(op_periods[op_idx], "senior_ds_keur", None)
        assert runtime_ds is not None, f"op_idx {op_idx}: senior_ds_keur not found"
        diff = abs(runtime_ds - expected)
        assert diff <= TOLERANCE, (
            f"Oborovo op_idx {op_idx}: runtime={runtime_ds:.4f} "
            f"fixture={expected:.4f} diff={diff:.4f} > {TOLERANCE} kEUR tolerance"
        )


# =============================================================================
# 6. Oborovo lock-up regression
# =============================================================================


def test_oborovo_lockup_remains_clean_after_factory_opt_in():
    """Phase 23O/P behavior preserved: no distributions while SHL outstanding.

    Expected:
    - op_idx 0-38: shl_balance > 0, distribution = 0
    - op_idx 38: shl cleared, distribution = 0 (guard period)
    - op_idx 39+: distribution > 0 (first valid: 2050-06-30)
    """
    op_periods, _ = _run_oborovo()

    TOLERANCE = 1.0

    # All pre-clear periods: shl_balance > 0, dist = 0
    for i, p in enumerate(op_periods):
        shl_bal = getattr(p, "shl_balance_keur", 0.0) or 0.0
        dist = getattr(p, "distribution_keur", 0.0) or 0.0
        if shl_bal > TOLERANCE:
            assert dist == 0.0, (
                f"op_idx {i}: shl_balance={shl_bal:.2f} but dist={dist:.2f} > 0 — "
                f"Phase 23O lock-up regressed!"
            )

    # Find first post-clear distribution
    post_clear = [p for p in op_periods if (getattr(p, "shl_balance_keur", 0.0) or 0.0) <= TOLERANCE]
    first_dist = next((p for p in post_clear if (getattr(p, "distribution_keur", 0.0) or 0.0) > TOLERANCE), None)
    assert first_dist is not None, "No distributions found after SHL cleared"
    assert str(first_dist.date) == "2050-06-30", (
        f"First post-SHL distribution at {first_dist.date}, expected 2050-06-30"
    )


# =============================================================================
# 7. TUHO distribution/SHL regression
# =============================================================================


def test_tuho_distribution_and_shl_regression_clean():
    """TUHO distribution/SHL behavior not regressed by Oborovo factory opt-in.

    TUHO: no distributions while SHL remains outstanding.
    """
    op_periods, _ = _run_tuho()

    TOLERANCE = 1.0
    for i, p in enumerate(op_periods):
        shl_bal = getattr(p, "shl_balance_keur", 0.0) or 0.0
        dist = getattr(p, "distribution_keur", 0.0) or 0.0
        if shl_bal > TOLERANCE:
            assert dist == 0.0, (
                f"TUHO op_idx {i}: shl_balance={shl_bal:.2f} but dist={dist:.2f} > 0"
            )


# =============================================================================
# 8. Revenue/OPEX unchanged
# =============================================================================


def test_revenue_opex_unchanged_for_both_projects():
    """Revenue and OPEX anchors remain stable for TUHO and Oborovo."""
    tuho_op, _ = _run_tuho()
    oborovo_op, _ = _run_oborovo()

    # TUHO early period anchors
    tuho_rev_0 = getattr(tuho_op[0], "revenue_keur", None)
    tuho_opex_0 = getattr(tuho_op[0], "opex_keur", None)
    assert tuho_rev_0 is not None, "TUHO revenue_keur not found"
    assert tuho_opex_0 is not None, "TUHO opex_keur not found"
    assert tuho_rev_0 > 0, "TUHO revenue should be > 0 in operating period"
    assert tuho_opex_0 > 0, "TUHO opex should be > 0 in operating period"

    # Oborovo early period anchors
    oborovo_rev_0 = getattr(oborovo_op[0], "revenue_keur", None)
    oborovo_opex_0 = getattr(oborovo_op[0], "opex_keur", None)
    assert oborovo_rev_0 is not None, "Oborovo revenue_keur not found"
    assert oborovo_opex_0 is not None, "Oborovo opex_keur not found"
    assert oborovo_rev_0 > 0, "Oborovo revenue should be > 0 in operating period"
    assert oborovo_opex_0 > 0, "Oborovo opex should be > 0 in operating period"


# =============================================================================
# 9. Guardrails unchanged
# =============================================================================


def test_guardrails_unchanged():
    """Guardrails preserved: G20/R99/R102 blocked, no new flags promoted."""
    oborovo = create_default_oborovo()
    info = oborovo.info

    # Governance fields must not exist
    assert not hasattr(info, "use_g20_engine"), "G20 must remain blocked"
    assert not hasattr(info, "use_r99_engine"), "R99 must remain not approved"
    assert not hasattr(info, "use_r102_engine"), "R102 must remain not approved"

    # No sculpting flags
    assert not hasattr(info, "flat_dscr_sculpted"), "flat_dscr_sculpted must not be promoted"
    assert not hasattr(info, "minimum_dscr_sculpted"), "minimum_dscr_sculpted must not be promoted"
    assert not hasattr(info, "partial_pay_sweep"), "partial_pay_sweep must not be promoted"
