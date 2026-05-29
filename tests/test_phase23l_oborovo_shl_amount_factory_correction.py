"""Phase 23L: Oborovo SHL amount factory correction.

Change: shl_amount_keur 13,547.2 → 14,621.0 kEUR (Excel draw alignment)

Before: shl_amount=13,547.2 + shl_idc=1,169.0 = 14,716.2 kEUR opening SHL
After:  shl_amount=14,621.0 + shl_idc=1,169.0 = 15,790.0 kEUR opening SHL

Excel target: 14,621 + 1,170 ≈ 15,791 kEUR → Python 15,790 kEUR ≈ Excel ✓

Context:
  PR #304/23H: SHL/distribution shortfall guard (2-tier bug fix)
  PR #306/23J: shl_tenor_years 0→20 (Excel 20-year bullet timing)
  PR #308/23K: diagnostic — gap in SHL draw, not IDC
  This PR:    narrow factory correction only

Guardrails (HARD):
  - G20 BLOCKED, R99/R102 NOT APPROVED
  - Do NOT enable Oborovo frozen schedule
  - Do NOT change TUHO factory flags
  - Do NOT change senior debt sizing
  - partial_pay_sweep opt-in only, no sculpting solver
"""

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig


# ---------------------------------------------------------------------------
# Test 1: Factory shl_amount matches Excel draw
# ---------------------------------------------------------------------------

def test_oborovo_factory_shl_amount_matches_excel_draw():
    """shl_amount_keur = 14,621.0 kEUR (Excel draw from construction template).

    IDC unchanged at 1,169.0 kEUR.
    Total opening: 14,621 + 1,169 = 15,790 kEUR ≈ Excel 15,791 kEUR.
    """
    oborovo = create_default_oborovo()
    fin = oborovo.financing

    assert fin.shl_amount_keur == pytest.approx(14_621.0, abs=0.1), (
        f"shl_amount_keur = {fin.shl_amount_keur} — expected 14,621.0"
    )
    assert fin.shl_idc_keur == pytest.approx(1_169.0, abs=1.0), (
        f"shl_idc_keur = {fin.shl_idc_keur} — expected 1,169.0 (unchanged)"
    )
    opening = fin.shl_amount_keur + fin.shl_idc_keur
    assert opening == pytest.approx(15_790.0, abs=1.0), (
        f"Opening SHL = {opening:.1f} kEUR — expected 15,790.0 (≈ Excel 15,791)"
    )


# ---------------------------------------------------------------------------
# Test 2: First-period SHL balance matches Excel
# ---------------------------------------------------------------------------

def test_oborovo_first_period_opening_shl_balance_matches_excel():
    """First operating-period SHL balance ≈ 15,790 kEUR.

    Python waterfall uses shl_amount + shl_idc as opening balance.
    After fix: opening = 14,621 + 1,169 = 15,790 kEUR.
    The closing balance after first period should also reflect this.
    """
    oborovo = create_default_oborovo()
    engine = _build_period_engine(oborovo)
    config = WaterfallRunConfig.from_inputs(oborovo, engine)
    result = WaterfallRunner(oborovo, engine).run(config)

    op_periods = [p for p in result.periods if p.is_operation]
    first = op_periods[0]

    # shl_balance in first period = opening balance = shl_amount + shl_idc
    # = 14,621 + 1,169 = 15,790 kEUR (closing balance after first period)
    opening_expected = 14_621.0 + 1_169.0  # = 15,790
    assert first.shl_balance_keur == pytest.approx(opening_expected, abs=1.0), (
        f"First-period shl_balance_keur = {first.shl_balance_keur:.2f} — "
        f"expected ~{opening_expected:.0f} kEUR after shl_amount correction"
    )


# ---------------------------------------------------------------------------
# Test 3: Distribution timing still aligned (no regression of 23H/23J)
# ---------------------------------------------------------------------------

def test_oborovo_distribution_timing_still_aligned():
    """Confirm PR #304/23H guard and PR #306/23J tenor still work correctly.

    With shl_tenor_years=20 (PR #306), SHL bullet fires at op_counter=39 (2050-06-30).
    At period 38 (2049-12-31): shl_svc = 15,790+ kEUR (principal + interest),
    which exceeds fcf_for_shl → PR #304 guard blocks distribution.
    At period 39 (2050-06-30): SHL cleared → large distributions begin.

    No distributions should appear in 2030-2049 that contradict the guard.
    """
    oborovo = create_default_oborovo()
    engine = _build_period_engine(oborovo)
    config = WaterfallRunConfig.from_inputs(oborovo, engine)
    result = WaterfallRunner(oborovo, engine).run(config)

    op_periods = [p for p in result.periods if p.is_operation]

    # Period 38 (2049-12-31): is_final_shl_period for shl_tenor_years=20
    p38 = op_periods[38]
    assert str(p38.date) == "2049-12-31", f"Expected period 38 at 2049-12-31, got {p38.date}"

    # SHL service = interest (593) + principal bullet (15,790) ≈ 16,383 kEUR
    # fcf_for_shl ≈ 3,278 kEUR → guard blocks distribution
    assert p38.distribution_keur == 0.0, (
        f"Period 38 (SHL final period): distribution = {p38.distribution_keur:.2f} — "
        f"should be 0 via PR #304 guard; shl_svc={p38.shl_service_keur:.2f}"
    )
    assert p38.shl_principal_keur > 15_000, (
        f"Period 38 SHL principal = {p38.shl_principal_keur:.2f} — "
        f"should be ~15,790 (bullet)"
    )

    # Period 39 (2050-06-30): SHL cleared, distributions start
    p39 = op_periods[39]
    assert str(p39.date) == "2050-06-30", f"Expected period 39 at 2050-06-30, got {p39.date}"
    assert p39.distribution_keur > 2_000, (
        f"Period 39 (first after SHL clear): distribution = {p39.distribution_keur:.2f} — "
        f"should be large (>2,000 kEUR)"
    )
    assert p39.shl_balance_keur == 0.0, "Period 39 SHL balance should be 0 after bullet"


# ---------------------------------------------------------------------------
# Test 4: Oborovo frozen schedule still OFF
# ---------------------------------------------------------------------------

def test_oborovo_frozen_schedule_still_off():
    """Oborovo use_frozen_excel_senior_debt_schedule and use_senior_debt_sizing_engine remain False."""
    oborovo = create_default_oborovo()
    engine = _build_period_engine(oborovo)
    config = WaterfallRunConfig.from_inputs(oborovo, engine)

    assert config.use_frozen_excel_senior_debt_schedule is False, (
        "Oborovo frozen schedule must remain OFF — guardrail violation"
    )
    assert config.use_senior_debt_sizing_engine is False, (
        "Oborovo senior debt sizing engine must remain OFF — guardrail violation"
    )


# ---------------------------------------------------------------------------
# Test 5: TUHO regression — flags and fixture unchanged
# ---------------------------------------------------------------------------

def test_tuho_regression_flags_and_fixture():
    """TUHO factory flags remain True (PR #303 opt-in) after Oborovo shl_amount change."""
    tuho = create_default_tuho_wind1()
    engine = _build_period_engine(tuho)
    config = WaterfallRunConfig.from_inputs(tuho, engine)

    assert config.use_frozen_excel_senior_debt_schedule is True, (
        "TUHO should have use_frozen_excel_senior_debt_schedule=True (PR #303)"
    )
    assert config.use_senior_debt_sizing_engine is True, (
        "TUHO should have use_senior_debt_sizing_engine=True (PR #303)"
    )

    # TUHO waterfall should run without error
    result = WaterfallRunner(tuho, engine).run(config)
    assert len(result.periods) > 0, "TUHO waterfall must produce periods"


# ---------------------------------------------------------------------------
# Test 6: Guardrails unchanged
# ---------------------------------------------------------------------------

def test_guardrails_unchanged():
    """Confirm all hard guardrails preserved."""
    from app.project_factories import create_default_oborovo

    oborovo = create_default_oborovo()
    engine = _build_period_engine(oborovo)
    config = WaterfallRunConfig.from_inputs(oborovo, engine)

    # Oborovo frozen schedule must remain OFF
    assert config.use_frozen_excel_senior_debt_schedule is False, (
        "G20 guardrail violated: Oborovo frozen schedule must remain OFF"
    )
    assert config.use_senior_debt_sizing_engine is False, (
        "G20 guardrail violated: Oborovo senior sizing engine must remain OFF"
    )

    # SHL method = bullet for Oborovo
    method_val = config.shl_repayment_method
    method_str = method_val.value if hasattr(method_val, 'value') else str(method_val)
    assert method_str == "bullet", (
        f"Oborovo SHL method = {method_val} — expected 'bullet'"
    )

    print(f"\nGuardrails: Oborovo frozen={config.use_frozen_excel_senior_debt_schedule}, "
          f"sizing={config.use_senior_debt_sizing_engine}, method={method_str}")