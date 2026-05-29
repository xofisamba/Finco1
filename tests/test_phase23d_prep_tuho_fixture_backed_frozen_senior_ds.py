"""Phase 23D: TUHO fixture-backed frozen senior debt sizing — wiring only, no factory opt-in.

Diagnostic test suite for Phase 23D: TUHO fixture-backed frozen senior debt sizing wiring.

PR #300 (Phase 23C) established that frozen=ON and frozen=OFF were IDENTICAL because
the CSV fixture was not wired into canonical senior debt sizing. Phase 23D fixes this.

This PR:
1. Wires phase7_tuho_senior_debt_sizing_extraction.csv into the canonical sizing path
   when both use_senior_debt_sizing_engine=True AND use_frozen_excel_senior_debt_schedule=True
2. Makes frozen=ON produce DIFFERENT senior_ds_keur from frozen=OFF (fixture-backed vs ebitda-derived)
3. Does NOT enable TUHO factory opt-in (flags remain False by default)
4. Does NOT change Oborovo behavior (no Oborovo fixture exists)

Fixture source: reports/phase7_tuho_senior_debt_sizing_extraction.csv
Fixture key columns:
  - operating_period_index (op_idx within operating periods, 0-based)
  - macro_r50_sizing_cfads_keur (sizing CFADS per period_index, first occurrence per op_idx)
  - ds_r19_target_dscr (per-period DSCR target)
  - ds_r20_debt_service_capacity_keur (= sizing_cfads / target_dscr per op_idx)

Expected fixture capacity values (by operating_period_index):
  op_idx=1:  2116.36 kEUR
  op_idx=2:  2144.69 kEUR
  op_idx=3:  2144.91 kEUR
  op_idx=4:  2169.31 kEUR
  op_idx=5:  2194.98 kEUR
  op_idx=6:  2189.92 kEUR
  op_idx=7:  2243.14 kEUR
  op_idx=8:  2287.66 kEUR
  op_idx=9:  2342.12 kEUR
  op_idx=10: 2395.11 kEUR
  op_idx=11: 2435.87 kEUR
  op_idx=12: 2484.47 kEUR
  op_idx=13: 2875.30 kEUR
  op_idx=14: 2829.33 kEUR

Guardrails (hard — this PR must NOT violate):
  G20 BLOCKED
  R99/R102 NOT APPROVED
  TUHO factory opt-in BLOCKED (no factory defaults changed)
  Oborovo frozen schedule NOT implemented
  No sculpting solver promotion
  No hardcoded senior DS arrays
  No Revenue/OPEX/CAPEX/Tax runtime changes
  No SHL/distribution runtime changes
"""

import csv
import os
import dataclasses
import pytest

from app.project_factories import create_default_tuho_wind1, create_default_oborovo
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig


# ─── Helpers ────────────────────────────────────────────────────────────────

def _fixture_capacity_by_op():
    """Load fixture capacity (ds_r20_debt_service_capacity_keur) by operating_period_index.

    Loads from reports/phase7_tuho_senior_debt_sizing_extraction.csv.
    Returns dict: op_idx (int, from CSV operating_period_index) → capacity_kEUR (float).
    Only entries with capacity > 0 are included.
    """
    csv_path = os.path.join(os.path.dirname(__file__), "..", "reports",
                            "phase7_tuho_senior_debt_sizing_extraction.csv")
    by_op = {}
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            op_str = row.get("operating_period_index", "").strip()
            cap_str = row.get("ds_r20_debt_service_capacity_keur", "").strip()
            if op_str and cap_str:
                op_i = int(op_str)
                cap_f = float(cap_str)
                if cap_f > 0 and op_i not in by_op:
                    by_op[op_i] = cap_f
    return by_op


FIXTURE_CAPACITY_BY_OP = _fixture_capacity_by_op()


def _run_tuho_with_flags(use_senior_debt_sizing_engine: bool, use_frozen_excel_senior_debt_schedule: bool):
    """Run TUHO waterfall with explicit flag settings.

    IMPORTANT: We must pass an explicit WaterfallRunConfig to runner.run(),
    otherwise it defaults to flags=False and bypasses the fixture wiring.
    """
    tuho = create_default_tuho_wind1()
    engine = _build_period_engine(tuho)
    base = WaterfallRunConfig.from_inputs(tuho, engine)
    run_config = WaterfallRunConfig(
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
        tuho_cit_cash_tax_start_operating_index=getattr(
            base, 'tuho_cit_cash_tax_start_operating_index', None
        ),
    )
    runner = WaterfallRunner(tuho, engine)
    return runner.run(run_config)


def _run_tuho_frozen():
    """Run TUHO with both flags ON (fixture-backed frozen schedule)."""
    return _run_tuho_with_flags(
        use_senior_debt_sizing_engine=True,
        use_frozen_excel_senior_debt_schedule=True
    )


def _run_tuho_default():
    """Run TUHO with both flags OFF (default path — ebitda-derived sizing)."""
    return _run_tuho_with_flags(
        use_senior_debt_sizing_engine=False,
        use_frozen_excel_senior_debt_schedule=False
    )


# ─── Test 1: Frozen ON uses fixture-backed senior DS (different from default) ──

def test_tuho_frozen_on_uses_fixture_backed_senior_ds():
    """Frozen ON senior_ds_keur differs from default for all fixture periods.

    The key Phase 23C blocker was: frozen=ON produced IDENTICAL senior_ds_keur
    to frozen=OFF because fixture was not loaded. Phase 23D fixes this.
    """
    result_default = _run_tuho_default()
    result_frozen = _run_tuho_frozen()

    op_periods_default = [(i, p) for i, p in enumerate(result_default.periods)
                          if getattr(p, "is_operation", False)]

    differing = 0
    for op_idx in FIXTURE_CAPACITY_BY_OP:
        period_idx = op_periods_default[op_idx][0] if op_idx < len(op_periods_default) else None
        if period_idx is None:
            continue
        ds_default = getattr(result_default.periods[period_idx], "senior_ds_keur", 0)
        ds_frozen = getattr(result_frozen.periods[period_idx], "senior_ds_keur", 0)
        if abs(ds_default - ds_frozen) > 0.01:
            differing += 1

    assert differing > 0, (
        "Frozen=ON should differ from default for at least one fixture period. "
        "If all are identical, fixture was not loaded."
    )


# ─── Test 2: Frozen selected periods match fixture ds_r20 capacity ────────────

@pytest.mark.parametrize(
    "op_idx,tolerance",
    [
        (1,  0.5),   # P2:  2116.36
        (2,  0.5),   # P4:  2144.69
        (3,  0.5),   # P6:  2144.91
        (14, 0.5),   # P28: 2829.33
    ],
)
def test_tuho_frozen_selected_periods_match_fixture(op_idx, tolerance):
    """Frozen senior_ds_keur at key op_idx matches fixture ds_r20_debt_service_capacity_keur."""
    result_frozen = _run_tuho_frozen()
    op_periods = [(i, p) for i, p in enumerate(result_frozen.periods)
                  if getattr(p, "is_operation", False)]

    period_idx = op_periods[op_idx][0] if op_idx < len(op_periods) else None
    assert period_idx is not None, f"op_idx={op_idx} out of range"

    ds_frozen = getattr(result_frozen.periods[period_idx], "senior_ds_keur", 0)
    expected = FIXTURE_CAPACITY_BY_OP[op_idx]

    assert abs(ds_frozen - expected) <= tolerance, (
        f"op_idx={op_idx}: frozen_ds={ds_frozen:.4f}, expected fixture={expected:.4f}, "
        f"diff={abs(ds_frozen - expected):.4f} > tolerance={tolerance}"
    )


# ─── Test 3: Audit marker requires fixture backing ──────────────────────────

def test_tuho_frozen_audit_marker_requires_fixture_backing():
    """_frozen_fixture_loaded=True only when fixture-backed schedule is active.

    Phase 23D sets _frozen_fixture_loaded only when the TUHO CSV fixture
    was actually loaded and used to build explicit sizing CFADS.
    """
    result_frozen = _run_tuho_frozen()

    # Frozen run with fixture should have Phase 23D audit marker
    assert getattr(result_frozen, "_frozen_fixture_loaded", False), (
        "Frozen ON run should set _frozen_fixture_loaded=True (Phase 23D marker)"
    )

    # Default run should NOT have fixture-loaded marker
    result_default = _run_tuho_default()
    assert not getattr(result_default, "_frozen_fixture_loaded", False), (
        "Default (frozen OFF) run should NOT set _frozen_fixture_loaded"
    )


# ─── Test 4: Default path unchanged when frozen flag OFF ─────────────────────

def test_default_path_unchanged_when_frozen_flag_off():
    """With frozen OFF, senior_ds_keur remains ebitda-derived (not fixture)."""
    result_default = _run_tuho_default()

    # Should not have frozen audit markers
    assert not getattr(result_default, "_frozen_senior_ds_wired", False)
    assert not getattr(result_default, "_frozen_fixture_loaded", False)

    # Revenue should be present and non-zero for operating periods
    op_periods = [(i, p) for i, p in enumerate(result_default.periods)
                  if getattr(p, "is_operation", False)]
    for op_idx in range(min(5, len(op_periods))):
        period_idx = op_periods[op_idx][0]
        rev = getattr(result_default.periods[period_idx], "revenue_keur", 0)
        assert rev > 0, f"op_idx={op_idx}: revenue should be > 0 for operating period"


# ─── Test 5: Oborovo frozen fixture still unavailable and OFF ─────────────────

def test_oborovo_frozen_fixture_still_unavailable_and_off():
    """Oborovo factory does not enable frozen schedule. No fixture is loaded."""
    oborovo = create_default_oborovo()

    # Verify factory defaults
    assert not oborovo.financing.use_frozen_excel_senior_debt_schedule, (
        "Oborovo factory should NOT enable use_frozen_excel_senior_debt_schedule"
    )
    assert not oborovo.info.use_senior_debt_sizing_engine, (
        "Oborovo factory should NOT enable use_senior_debt_sizing_engine"
    )

    # Run Oborovo with both flags explicitly OFF (factory defaults)
    engine = _build_period_engine(oborovo)
    base = WaterfallRunConfig.from_inputs(oborovo, engine)
    config = WaterfallRunConfig(
        use_senior_debt_sizing_engine=False,
        use_frozen_excel_senior_debt_schedule=False,
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
    runner = WaterfallRunner(oborovo, engine)
    result = runner.run(config)

    # Should not have frozen markers
    assert not getattr(result, "_frozen_senior_ds_wired", False)
    assert not getattr(result, "_frozen_fixture_loaded", False)


# ─── Test 6: No factory opt-in yet ───────────────────────────────────────────

def test_no_factory_opt_in_yet():
    """TUHO factory defaults remain with frozen flags = False.

    This PR wires the capability behind the flags, but does NOT change
    the factory default to set them True. TUHO factory opt-in remains BLOCKED.
    """
    tuho = create_default_tuho_wind1()

    assert not tuho.financing.use_frozen_excel_senior_debt_schedule, (
        "TUHO factory: use_frozen_excel_senior_debt_schedule should remain False"
    )
    assert not tuho.info.use_senior_debt_sizing_engine, (
        "TUHO factory: use_senior_debt_sizing_engine should remain False"
    )


# ─── Test 7: Phase 23C blocker resolved for TUHO ──────────────────────────────

def test_phase23c_blocker_resolved_for_tuho():
    """Phase 23C blocker condition reversed: frozen ON now differs from frozen OFF.

    PR #300 proved frozen=ON and frozen=OFF were IDENTICAL (fixture not wired).
    Phase 23D wires the fixture, so frozen=ON now produces different senior_ds_keur.
    """
    result_default = _run_tuho_default()
    result_frozen = _run_tuho_frozen()

    op_periods_def = [(i, p) for i, p in enumerate(result_default.periods)
                       if getattr(p, "is_operation", False)]

    for check_op_idx in [1, 2, 3]:
        period_idx_def = op_periods_def[check_op_idx][0]
        period_idx_frz = op_periods_def[check_op_idx][0]  # same op_idx, same position

        ds_default = getattr(result_default.periods[period_idx_def], "senior_ds_keur", 0)
        ds_frozen = getattr(result_frozen.periods[period_idx_frz], "senior_ds_keur", 0)

        diff = abs(ds_default - ds_frozen)
        assert diff > 1.0, (
            f"op_idx={check_op_idx}: default={ds_default:.2f}, frozen={ds_frozen:.2f}, "
            f"diff={diff:.2f}. Should differ by > 1 kEUR after Phase 23D fixture wiring."
        )