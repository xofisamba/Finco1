"""Phase 23E: SHL/distribution lock-up diagnostic — fixture-backed frozen TUHO senior DS.

Diagnostic-only: verifies downstream SHL/distribution behavior with actual fixture-backed
senior DS. Does NOT enable TUHO factory opt-in. Does NOT change runtime wiring.

Run after Phase 23D (PR #301) merge.

Guardrails (HARD):
- G20 BLOCKED
- R99/R102 NOT APPROVED
- partial_pay_sweep opt-in only
- Do NOT enable TUHO factory opt-in
- Do NOT enable Oborovo frozen schedule
- Do NOT merge or modify PR #299
- Do NOT change Revenue/OPEX/CAPEX/Tax logic
"""

import dataclasses
import csv
import warnings
from pathlib import Path

import pytest

from app.project_factories import create_default_tuho_wind1, create_default_solar_project
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "reports" / "phase7_tuho_senior_debt_sizing_extraction.csv"
FIXTURE_PATH_STR = str(FIXTURE_PATH)


def _load_fixture():
    """Load fixture values keyed by CSV operating_period_index (1-based).

    Returns dict: op_idx (1-14) → {sizing_cfads, dscr, capacity}.
    Keeps first row per op_idx with capacity > 0.
    """
    by_op = {}
    with open(FIXTURE_PATH, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            op_str = row.get("operating_period_index", "").strip()
            cap_str = row.get("ds_r20_debt_service_capacity_keur", "").strip()
            if op_str and cap_str:
                op_i = int(op_str)
                cap_f = float(cap_str)
                if cap_f > 0 and op_i not in by_op:
                    by_op[op_i] = {
                        "sizing_cfads": float(row.get("macro_r50_sizing_cfads_keur", "0") or "0"),
                        "dscr": float(row.get("ds_r19_target_dscr", "1.2") or "1.2"),
                        "capacity": cap_f,
                    }
    return by_op


def _run_tuho_with_flags(
    use_senior_debt_sizing_engine: bool,
    use_frozen_excel_senior_debt_schedule: bool,
):
    """Run TUHO waterfall with explicit flag settings.

    IMPORTANT: must pass explicit WaterfallRunConfig, otherwise defaults have flags=False.
    """
    tuho = create_default_tuho_wind1()
    fin = dataclasses.replace(tuho.financing, use_frozen_excel_senior_debt_schedule=use_frozen_excel_senior_debt_schedule)
    info = dataclasses.replace(tuho.info, use_senior_debt_sizing_engine=use_senior_debt_sizing_engine)
    tuho2 = dataclasses.replace(tuho, financing=fin, info=info)
    engine = _build_period_engine(tuho2)
    base = WaterfallRunConfig.from_inputs(tuho2, engine)
    config = WaterfallRunConfig(
        use_senior_debt_sizing_engine=use_senior_debt_sizing_engine,
        use_frozen_excel_senior_debt_schedule=use_frozen_excel_senior_debt_schedule,
        rate_per_period=base.rate_per_period,
        tenor_periods=base.tenor_periods,
        target_dscr=base.target_dscr,
        lockup_dscr=base.lockup_dscr,
        tax_rate=base.tax_rate,
        dsra_months=base.dsra_months,
        shl_amount_keur=base.shl_amount_keur,
        shl_rate=base.shl_rate,
        shl_idc_keur=base.shl_idc_keur,
        shl_repayment_method=base.shl_repayment_method,
        shl_tenor_years=base.shl_tenor_years,
        shl_wht_rate=base.shl_wht_rate,
        equity_irr_method=base.equity_irr_method,
        share_capital_keur=base.share_capital_keur,
        sculpt_capex_keur=base.sculpt_capex_keur,
        debt_sizing_method=base.debt_sizing_method,
        dscr_schedule=base.dscr_schedule,
    )
    return WaterfallRunner(tuho2, engine).run(config)


def _run_tuho_default():
    return _run_tuho_with_flags(
        use_senior_debt_sizing_engine=False,
        use_frozen_excel_senior_debt_schedule=False,
    )


def _run_tuho_fixture_backed():
    return _run_tuho_with_flags(
        use_senior_debt_sizing_engine=True,
        use_frozen_excel_senior_debt_schedule=True,
    )


# ---------------------------------------------------------------------------
# Test 1: fixture-backed frozen path is active
# ---------------------------------------------------------------------------

def test_tuho_fixture_backed_frozen_path_active():
    """Fixture markers are set and frozen senior_ds matches fixture values."""
    result = _run_tuho_fixture_backed()
    fixture = _load_fixture()

    # Audit markers confirm fixture was loaded
    assert getattr(result, "_frozen_fixture_loaded", False) is True, \
        "Fixture should be loaded when both flags are ON"
    assert getattr(result, "_frozen_fixture_error", "NOT None") is None, \
        "Fixture error should be None"
    assert getattr(result, "_frozen_senior_ds_wired", False) is True, \
        "_frozen_senior_ds_wired should be True"

    # Fixture path is repo-root anchored (verify file exists)
    assert FIXTURE_PATH.exists(), f"Fixture CSV should exist at {FIXTURE_PATH}"

    # Frozen senior_ds matches fixture capacity for all 14 operating periods
    op_periods = [p for p in result.periods if p.is_operation]
    mismatches = []
    for i, op_period in enumerate(op_periods[:14]):
        op_idx = i + 1  # 1-based, matching on_waterfall operating period index
        expected = fixture.get(op_idx, {}).get("capacity", None)
        if expected is None:
            mismatches.append(f"op_idx={op_idx}: no fixture entry")
            continue
        actual = op_period.senior_ds_keur
        if abs(actual - expected) > 0.5:
            mismatches.append(f"op_idx={op_idx}: expected={expected:.4f}, actual={actual:.4f}")

    assert not mismatches, "\n".join(["senior_ds_keur mismatch with fixture:"] + mismatches)


# ---------------------------------------------------------------------------
# Test 2: fixture-backed frozen DS changes downstream values
# ---------------------------------------------------------------------------

def test_tuho_fixture_backed_frozen_ds_changes_downstream_values():
    """senior_ds_keur differs between default and frozen paths for all operating periods."""
    result_default = _run_tuho_default()
    result_frozen = _run_tuho_fixture_backed()

    op_def = [p for p in result_default.periods if p.is_operation]
    op_fb = [p for p in result_frozen.periods if p.is_operation]

    # Senior DS must differ for all 14 operating years
    diffs = []
    for i in range(14):
        d = op_def[i].senior_ds_keur
        f = op_fb[i].senior_ds_keur
        if abs(d - f) < 0.5:
            diffs.append(f"op_idx={i+1}: default={d:.4f}, frozen={f:.4f} (too close)")

    assert not diffs, f"senior_ds should differ for all 14 ops:\n" + "\n".join(diffs)

    # Frozen path produces all expected downstream fields
    for i in range(14):
        p = op_fb[i]
        assert p.senior_ds_keur is not None
        assert p.senior_interest_keur is not None
        assert p.senior_balance_keur is not None
        assert p.shl_balance_keur is not None
        assert p.distribution_keur is not None
        assert p.dscr is not None


# ---------------------------------------------------------------------------
# Test 3: no distribution while SHL outstanding (fixture-backed)
# ---------------------------------------------------------------------------

def test_tuho_no_distribution_while_shl_outstanding_fixture_backed():
    """No distribution while SHL principal or unpaid/accrued/PIK interest remains outstanding.

    Breaks if distribution_keur > tolerance AND any of shl_balance_keur, shl_pik_keur,
    or shl_gross_accrued_interest_keur > tolerance.
    """
    result = _run_tuho_fixture_backed()
    op_periods = [p for p in result.periods if p.is_operation]

    TOLERANCE = 0.01  # kEUR
    breaches = []
    for i, p in enumerate(op_periods[:14]):
        shl_outstanding = (
            p.shl_balance_keur > TOLERANCE
            or p.shl_pik_keur > TOLERANCE
            or p.shl_gross_accrued_interest_keur > TOLERANCE
        )
        dist_active = p.distribution_keur > TOLERANCE
        if dist_active and shl_outstanding:
            breaches.append(
                f"op_idx={i+1} (period={p.period}): "
                f"distribution={p.distribution_keur:.4f}, "
                f"shl_bal={p.shl_balance_keur:.2f}, "
                f"shl_pik={p.shl_pik_keur:.2f}, "
                f"shl_acc={p.shl_gross_accrued_interest_keur:.2f}"
            )

    assert not breaches, "Distribution while SHL outstanding:\n" + "\n".join(breaches)


# ---------------------------------------------------------------------------
# Test 4: TUHO factory opt-in still blocked
# ---------------------------------------------------------------------------

def test_tuho_factory_opt_in_still_blocked():
    """TUHO factory flags remain False (factory opt-in BLOCKED pending downstream diagnostic)."""
    tuho = create_default_tuho_wind1()
    assert tuho.info.use_senior_debt_sizing_engine is False, \
        "TUHO use_senior_debt_sizing_engine factory default must remain False"
    assert tuho.financing.use_frozen_excel_senior_debt_schedule is False, \
        "TUHO use_frozen_excel_senior_debt_schedule factory default must remain False"


# ---------------------------------------------------------------------------
# Test 5: Oborovo remains OFF and unfixed
# ---------------------------------------------------------------------------

def test_oborovo_remains_off_and_unfixed():
    """Oborovo frozen flags remain False. No lock-up pass required in this PR."""
    oborovo = create_default_solar_project()
    assert oborovo.info.use_senior_debt_sizing_engine is False, \
        "Oborovo use_senior_debt_sizing_engine must remain False"
    assert oborovo.financing.use_frozen_excel_senior_debt_schedule is False, \
        "Oborovo use_frozen_excel_senior_debt_schedule must remain False"


# ---------------------------------------------------------------------------
# Test 6: Revenue/OPEX unchanged between default and frozen
# ---------------------------------------------------------------------------

def test_revenue_opex_unchanged_between_default_and_frozen():
    """Revenue and OPEX are not altered by frozen senior DS wiring."""
    result_default = _run_tuho_default()
    result_frozen = _run_tuho_fixture_backed()

    op_def = [p for p in result_default.periods if p.is_operation]
    op_fb = [p for p in result_frozen.periods if p.is_operation]

    mismatches = []
    for i in range(min(14, len(op_def), len(op_fb))):
        pd = op_def[i]
        pf = op_fb[i]
        if abs(pd.revenue_keur - pf.revenue_keur) > 0.01:
            mismatches.append(f"op_idx={i+1}: revenue default={pd.revenue_keur:.4f} frozen={pf.revenue_keur:.4f}")
        if abs(pd.opex_keur - pf.opex_keur) > 0.01:
            mismatches.append(f"op_idx={i+1}: opex default={pd.opex_keur:.4f} frozen={pf.opex_keur:.4f}")

    assert not mismatches, "Revenue/OPEX changed between default and frozen:\n" + "\n".join(mismatches)


# ---------------------------------------------------------------------------
# Test 7: fixture path is repo-root anchored
# ---------------------------------------------------------------------------

def test_fixture_path_is_repo_root_anchored():
    """Fixture CSV path resolves correctly regardless of cwd."""
    # The fixture path uses Path(__file__).resolve().parents[1] / "reports" / ...
    # which anchors to repo root, not cwd
    assert FIXTURE_PATH.exists(), f"Fixture should be found at repo-root-anchored path: {FIXTURE_PATH}"

    # Load sanity check: fixture has 14 operating period entries
    fixture = _load_fixture()
    assert len(fixture) == 14, f"Fixture should have 14 operating periods, got {len(fixture)}"
    assert all(k in fixture for k in range(1, 15)), "Fixture should have op_idx 1-14"


# ---------------------------------------------------------------------------
# Test 8: default TUHO (no fixture) path still works
# ---------------------------------------------------------------------------

def test_tuho_default_path_still_works():
    """Default TUHO run (no fixture) produces valid results and distribution_keur=0."""
    result = _run_tuho_default()
    op_periods = [p for p in result.periods if p.is_operation][:14]

    assert all(p.distribution_keur == 0.0 for p in op_periods), \
        "Default TUHO distribution should be 0"
    assert all(p.shl_balance_keur > 0 for p in op_periods), \
        "Default TUHO SHL balance should be > 0"

    # Default senior_ds_keur is NOT from fixture (it's ebitda-derived)
    assert all(p.senior_ds_keur != 0.0 for p in op_periods[:13]) or any(
        p.senior_ds_keur != 0.0 for p in op_periods[:13]
    ), "Default senior_ds_keur should be non-zero"
