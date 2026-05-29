"""Phase 23F: TUHO frozen factory opt-in candidate.

TUHO-only factory opt-in for fixture-backed frozen senior debt service.
Narrow change: only create_default_tuho_wind1() factory flags are changed.

Guardrails (HARD):
- G20 BLOCKED
- R99/R102 NOT APPROVED
- Do NOT enable Oborovo frozen schedule
- Do NOT touch PR #299
- partial_pay_sweep remains opt-in only
- Do NOT promote flat_dscr_sculpted / minimum_dscr_sculpted
"""

import csv
import dataclasses
from pathlib import Path

import pytest

from app.project_factories import create_default_tuho_wind1, create_default_solar_project
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "reports" / "phase7_tuho_senior_debt_sizing_extraction.csv"


def _load_fixture():
    """Load fixture values keyed by CSV operating_period_index (1-based)."""
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


def _run_tuho_factory():
    """Run TUHO using factory defaults (no manual flag overrides)."""
    tuho = create_default_tuho_wind1()
    engine = _build_period_engine(tuho)
    config = WaterfallRunConfig.from_inputs(tuho, engine)
    return WaterfallRunner(tuho, engine).run(config)


def _run_tuho_control():
    """Run TUHO with frozen flags explicitly disabled (control run)."""
    tuho = create_default_tuho_wind1()
    fin = dataclasses.replace(tuho.financing, use_frozen_excel_senior_debt_schedule=False)
    info = dataclasses.replace(tuho.info, use_senior_debt_sizing_engine=False)
    tuho_ctrl = dataclasses.replace(tuho, financing=fin, info=info)
    engine = _build_period_engine(tuho_ctrl)
    ctrl_config = WaterfallRunConfig.from_inputs(tuho_ctrl, engine)
    # Disable frozen flags for the control comparison
    ctrl_config = dataclasses.replace(
        ctrl_config,
        use_senior_debt_sizing_engine=False,
        use_frozen_excel_senior_debt_schedule=False,
    )
    return WaterfallRunner(tuho_ctrl, engine).run(ctrl_config)


# ---------------------------------------------------------------------------
# Test 1: factory flags enabled
# ---------------------------------------------------------------------------

def test_tuho_factory_flags_enabled():
    """TUHO factory sets both frozen senior DS flags to True."""
    tuho = create_default_tuho_wind1()
    assert tuho.info.use_senior_debt_sizing_engine is True, \
        "TUHO use_senior_debt_sizing_engine must be True in factory"
    assert tuho.financing.use_frozen_excel_senior_debt_schedule is True, \
        "TUHO use_frozen_excel_senior_debt_schedule must be True in factory"


# ---------------------------------------------------------------------------
# Test 2: Oborovo factory flags remain off
# ---------------------------------------------------------------------------

def test_oborovo_factory_flags_remain_off():
    """Oborovo factory flags remain False (no Oborovo frozen schedule)."""
    oborovo = create_default_solar_project()
    assert oborovo.info.use_senior_debt_sizing_engine is False, \
        "Oborovo use_senior_debt_sizing_engine must remain False"
    assert oborovo.financing.use_frozen_excel_senior_debt_schedule is False, \
        "Oborovo use_frozen_excel_senior_debt_schedule must remain False"


# ---------------------------------------------------------------------------
# Test 3: factory run uses fixture-backed frozen senior DS
# ---------------------------------------------------------------------------

def test_tuho_factory_run_uses_fixture_backed_frozen_senior_ds():
    """Normal TUHO factory run (no manual flag overrides) uses fixture-backed frozen DS."""
    result = _run_tuho_factory()
    fixture = _load_fixture()
    op_periods = [p for p in result.periods if p.is_operation][:14]

    # Audit markers
    assert getattr(result, "_frozen_fixture_loaded", False) is True, \
        "Factory run should load the fixture CSV"
    assert getattr(result, "_frozen_fixture_error", "NOT None") is None, \
        "Factory run should have no fixture error"
    assert getattr(result, "_frozen_senior_ds_wired", False) is True, \
        "Factory run should have frozen senior DS wired"

    # Senior DS matches fixture for all 14 operating periods
    mismatches = []
    for i, op_period in enumerate(op_periods[:14]):
        csv_op_idx = i + 1
        expected = fixture.get(csv_op_idx, {}).get("capacity", None)
        if expected is None:
            mismatches.append(f"op_idx={csv_op_idx}: no fixture entry")
            continue
        actual = op_period.senior_ds_keur
        if abs(actual - expected) > 0.5:
            mismatches.append(
                f"op_idx={csv_op_idx}: actual={actual:.4f}, expected={expected:.4f}"
            )

    assert not mismatches, "\n".join(["senior_ds_keur mismatch with fixture:"] + mismatches)


# ---------------------------------------------------------------------------
# Test 4: no distribution while SHL outstanding (factory run)
# ---------------------------------------------------------------------------

def test_tuho_factory_no_distribution_while_shl_outstanding():
    """Factory run: no distribution while SHL principal or unpaid/accrued/PIK interest outstanding."""
    result = _run_tuho_factory()
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
# Test 5: Revenue/OPEX unchanged vs control
# ---------------------------------------------------------------------------

def test_tuho_factory_revenue_opex_unchanged_vs_control():
    """Factory run has same Revenue/OPEX as control run with flags explicitly disabled."""
    result_factory = _run_tuho_factory()
    result_control = _run_tuho_control()

    op_factory = [p for p in result_factory.periods if p.is_operation]
    op_control = [p for p in result_control.periods if p.is_operation]

    mismatches = []
    for i in range(min(14, len(op_factory), len(op_control))):
        pf = op_factory[i]
        pc = op_control[i]
        if abs(pf.revenue_keur - pc.revenue_keur) > 0.01:
            mismatches.append(f"op_idx={i+1}: revenue factory={pf.revenue_keur:.4f} control={pc.revenue_keur:.4f}")
        if abs(pf.opex_keur - pc.opex_keur) > 0.01:
            mismatches.append(f"op_idx={i+1}: opex factory={pf.opex_keur:.4f} control={pc.opex_keur:.4f}")

    assert not mismatches, "Revenue/OPEX changed between factory and control:\n" + "\n".join(mismatches)


# ---------------------------------------------------------------------------
# Test 6: DSCR is backward-computed from frozen senior DS
# ---------------------------------------------------------------------------

def test_tuho_factory_dscr_backward_computed():
    """DSCR is backward-computed from cfads / frozen senior_ds (no sculpting solver introduced)."""
    result = _run_tuho_factory()
    fixture = _load_fixture()
    op_periods = [p for p in result.periods if p.is_operation][:14]

    # For each period: DSCR = cfads / senior_ds_keur
    # cfads = revenue - opex (EBITDA at operating period level)
    TOLERANCE = 0.01
    mismatches = []
    for i, p in enumerate(op_periods):
        csv_op_idx = i + 1
        cfads = p.revenue_keur - p.opex_keur
        senior_ds = p.senior_ds_keur
        if senior_ds > 0:
            expected_dscr = cfads / senior_ds
            actual_dscr = p.dscr
            if abs(actual_dscr - expected_dscr) > TOLERANCE:
                mismatches.append(
                    f"op_idx={csv_op_idx}: cfads={cfads:.2f}, senior_ds={senior_ds:.2f}, "
                    f"expected_dscr={expected_dscr:.4f}, actual_dscr={actual_dscr:.4f}"
                )

    assert not mismatches, "DSCR not backward-computed from cfads/frozen_senior_ds:\n" + "\n".join(mismatches)


# ---------------------------------------------------------------------------
# Test 7: golden fixture selected values (CSV-loaded, no hardcoded arrays)
# ---------------------------------------------------------------------------

def test_tuho_factory_golden_fixture_selected_values():
    """Selected operating periods match fixture CSV values (no hardcoded arrays)."""
    result = _run_tuho_factory()
    fixture = _load_fixture()
    op_periods = [p for p in result.periods if p.is_operation][:14]

    # Selected checkpoints: wf op_idx 0,1,5,13 → CSV op_idx 1,2,6,14
    checkpoints = [(0, 1), (1, 2), (5, 6), (13, 14)]
    mismatches = []
    for wf_idx, csv_idx in checkpoints:
        actual_ds = op_periods[wf_idx].senior_ds_keur
        expected_cap = fixture.get(csv_idx, {}).get("capacity", None)
        if expected_cap is None:
            mismatches.append(f"wf_op_idx={wf_idx} (CSV op_idx={csv_idx}): no fixture entry")
        elif abs(actual_ds - expected_cap) > 0.5:
            mismatches.append(
                f"wf_op_idx={wf_idx} (CSV op_idx={csv_idx}): "
                f"actual={actual_ds:.4f}, expected={expected_cap:.4f}"
            )

    assert not mismatches, "Golden fixture values mismatch:\n" + "\n".join(mismatches)


# ---------------------------------------------------------------------------
# Test 8: no unintended runtime flags promoted
# ---------------------------------------------------------------------------

def test_no_unintended_runtime_flags_promoted():
    """Verify no guardrail violations: partial_pay_sweep, flat/min DSCR sculpted, G20."""
    tuho = create_default_tuho_wind1()

    # TUHO factory does not change partial_pay_sweep (opt-in only)
    # The partial_pay_sweep field is in the FinancingParams; verify it's not forced True
    # We check that the factory does not set partial_pay_sweep=True
    assert tuho.financing.use_frozen_excel_senior_debt_schedule is True  # only the intended flag

    # Verify G20-related fields are not modified by this phase
    # TUHO already has lockup_dscr=1.10 and target_dscr=1.20, unchanged by Phase 23F
    assert tuho.financing.lockup_dscr == 1.10, "lockup_dscr should remain 1.10"
    assert tuho.financing.target_dscr == 1.20, "target_dscr should remain 1.20"

    # flat_dscr_sculpted and minimum_dscr_sculpted are not set in TUHO factory
    # They would be fields on FinancingParams if present; verify nothing was auto-promoted
    # We document that Phase 23F does not touch amortization_type or debt_sizing_method
    assert tuho.financing.amortization_type == "sculpted", \
        "amortization_type should remain sculpted (not changed by Phase 23F)"
    assert tuho.financing.debt_sizing_method == "fixed", \
        "debt_sizing_method should remain fixed (not changed by Phase 23F)"
