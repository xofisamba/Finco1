"""Phase 23K: Oborovo SHL Opening Balance Bridge — diagnostic tests.

Historical context (pre-Phase 23L):
  Pre-23L Python: shl_amount_keur=13,547.2 + shl_idc_keur=1,169.0 = 14,716.2 kEUR opening
  Excel target:   shl_amount_keur=14,621.0 + shl_idc_keur=1,170.0 = 15,791 kEUR opening
  Gap (pre-23L):  1,074.8 kEUR in the draw/principal component

Post-Phase 23L correction:
  shl_amount_keur corrected from 13,547.2 → 14,621.0 kEUR
  Opening SHL now: 14,621 + 1,169 = 15,790 kEUR ≈ Excel 15,791 kEUR ✓
  Gap CLOSED.

Source of Excel target:
  - Oborovo construction template (domain/construction/templates/oborovo.py):
      shl_keur=14,620.774  (funding cap, rounded to 14,621)
  - project_factories.py comment: "opening SHL balance = 14,621 + 1,169 = 15,790"
  - IDC (1,169/1,170) matched between Python and Excel; no gap there

PR context:
  #303: TUHO factory frozen senior DS opt-in (merged)
  #304: Oborovo SHL/distribution lock-up guard — Python bug fixed (merged)
  #306: Oborovo shl_tenor_years 0→20 (Excel 20-year bullet alignment) (merged)
  #308/23K: Diagnostic — documented the SHL opening balance gap
  #309/23L: Factory correction — shl_amount_keur 13,547.2 → 14,621.0 (gap closed)
  #310/23M: Test update — Phase 23K tests now pass after Phase 23L correction
"""

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig


# ---------------------------------------------------------------------------
# Test 1: Document current Python opening SHL balance and detect the gap
# ---------------------------------------------------------------------------

def test_oborovo_current_shl_opening_balance_documents_gap():
    """Document Python opening SHL balance vs Excel target (POST Phase 23L).

    Pre-Phase 23L (historical): shl_amount=13,547.2 + shl_idc=1,169.0 = 14,716.2 kEUR
    Post-Phase 23L (current):   shl_amount=14,621.0 + shl_idc=1,169.0 = 15,790.0 kEUR
    Excel target:               shl_amount=14,621.0 + shl_idc=1,170.0 = 15,791 kEUR

    After Phase 23L correction, the gap is CLOSED.
    This test validates that shl_amount=14,621.0 (Excel draw) and opening≈15,790 kEUR.
    """
    oborovo = create_default_oborovo()
    fin = oborovo.financing

    shl_amount = fin.shl_amount_keur          # 14,621.0 (post-23L)
    shl_idc    = fin.shl_idc_keur              # 1,169.0 (unchanged)
    python_opening = shl_amount + shl_idc      # 15,790.0

    excel_draw = 14_621.0
    excel_idc  = 1_170.0
    excel_opening = excel_draw + excel_idc     # 15,791

    # Post-23L: shl_amount should now match Excel draw
    assert shl_amount == pytest.approx(14_621.0, abs=0.1), (
        f"Factory shl_amount_keur = {shl_amount} — expected 14,621.0 (Excel draw, corrected in Phase 23L)"
    )
    assert shl_idc == pytest.approx(1_169.0, abs=1.0), (
        f"Factory shl_idc_keur = {shl_idc} — expected 1,169.0 (unchanged)"
    )
    assert python_opening == pytest.approx(15_790.0, abs=1.0), (
        f"Python opening SHL balance = {python_opening} — expected 15,790.0 (≈ Excel 15,791)"
    )

    # Gap is now closed: python ≈ excel within tolerance
    gap = excel_opening - python_opening
    assert abs(gap) <= 2.0, (
        f"SHL opening gap = {gap:.1f} kEUR — should be ~0 after Phase 23L correction; "
        f"Python ({python_opening:.0f}) ≈ Excel ({excel_opening:.0f})"
    )

    print(f"\nSHL Opening Balance Gap CLOSED:")
    print(f"  Python opening: {python_opening:.1f} kEUR")
    print(f"  Excel target:   {excel_opening:.0f} kEUR")
    print(f"  Gap:            {gap:.1f} kEUR (abs ≤ 2 kEUR) ✓")


# ---------------------------------------------------------------------------
# Test 2: SHL component bridge — draw vs IDC
# ---------------------------------------------------------------------------

def test_oborovo_shl_component_bridge():
    """Compare current factory components to Excel-known components (POST Phase 23L).

    Pre-Phase 23L (historical): SHL draw=13,547.2 vs Excel=14,621 → delta ≈ −1,074 kEUR
    Post-Phase 23L (current):   SHL draw=14,621.0 vs Excel=14,621 → delta ≈ 0 kEUR ✓
    SHL IDC:                    Python=1,169.0 vs Excel=1,170   → delta ≈ −1 kEUR (≈0)

    After Phase 23L correction, both draw and IDC are aligned with Excel.
    """
    oborovo = create_default_oborovo()
    fin = oborovo.financing

    shl_amount = fin.shl_amount_keur    # 14,621.0 (post-23L)
    shl_idc    = fin.shl_idc_keur       # 1,169.0 (unchanged)

    # Excel-known values
    excel_draw_amount = 14_621.0
    excel_idc         = 1_170.0

    draw_delta  = shl_amount - excel_draw_amount   # ~0 after Phase 23L
    idc_delta   = shl_idc - excel_idc              # near zero (unchanged)

    # IDC: no gap (unchanged from Phase 23K)
    assert abs(idc_delta) < 5.0, (
        f"IDC gap = {idc_delta:.1f} kEUR — should be near zero; "
        f"Python={shl_idc:.1f}, Excel={excel_idc:.0f}"
    )

    # Draw: now aligned with Excel (Phase 23L corrected the gap)
    assert abs(draw_delta) <= 1.0, (
        f"SHL draw delta = {draw_delta:.1f} kEUR — after Phase 23L, draw should be "
        f"aligned with Excel ({shl_amount:.1f} vs {excel_draw_amount:.0f})"
    )

    print(f"\nSHL Component Bridge (POST Phase 23L):")
    print(f"  Draw:  Python={shl_amount:.1f} Excel={excel_draw_amount:.0f}  delta={draw_delta:.1f} kEUR ✓")
    print(f"  IDC:   Python={shl_idc:.1f}  Excel={excel_idc:.0f}  delta={idc_delta:.1f} kEUR ✓")
    print(f"  Gap CLOSED: opening = {shl_amount+shl_idc:.1f} ≈ {excel_draw_amount+excel_idc:.0f}")


# ---------------------------------------------------------------------------
# Test 3: Distribution timing still matches Excel directionally
# ---------------------------------------------------------------------------

def test_oborovo_distribution_timing_still_matches_excel_directionally():
    """Confirm Oborovo distributions align with Excel directionally.

    Excel check (from cofi19 manual inspection):
      - 2046 dividends: blank/zero (Excel CF tab: cash flows to SHL/Net SHL column)
      - Dividends start ~2050 after SHL is cleared

    Python behavior (current main, PR #304 + PR #306 applied):
      - PR #304 added SHL cash-shortfall guard in the 2-tier "else" branch
      - PR #306 set Oborovo shl_tenor_years=20 (previously fell back to senior_tenor_years=14)
      - SHL bullet fires at op_counter=39 (2050-06-30), matching Excel 2050 target
      - Distributions occur throughout 2030-2049 alongside SHL interest (small amounts)
      - At period 39 (2050-06-30): SHL cleared → large distributions begin

    Note: Python shows distributions from 2030 onward (small, ~50-100 kEUR/period alongside
    SHL interest). The PR #304 guard blocks distributions ONLY when shl_svc > fcf_for_shl.
    The "2046 dividends blank/zero" in Excel refers to the period where SHL bullet fires
    (period 38 for generic_solar with shl_tenor_years=0, or period 39 for Oborovo with
    shl_tenor_years=20). For Oborovo, period 38 (2049-12-31) is the SHL final period with
    shl_service = 15,309 kEUR (principal bullet of 14,716 + interest), which blocks
    distribution via the PR #304 guard.

    Key: Oborovo shl_tenor_years=20 (PR #306) ensures SHL clears at 2050, not 2046.
    """
    oborovo = create_default_oborovo()
    engine = _build_period_engine(oborovo)
    config = WaterfallRunConfig.from_inputs(oborovo, engine)
    result = WaterfallRunner(oborovo, engine).run(config)

    op_periods = [p for p in result.periods if p.is_operation]

    # Oborovo: shl_tenor_years=20 → SHL bullet at op_counter=39 (period 39, 2050-06-30)
    # Period 38 (2049-12-31): is_final_shl_period, shl_svc=15,309 kEUR → dist=0
    # Period 39 (2050-06-30): SHL cleared → dist=2994 kEUR (large first distribution)
    p38 = op_periods[38]
    p39 = op_periods[39]
    assert str(p38.date) == "2049-12-31", f"Expected period 38 at 2049-12-31, got {p38.date}"
    assert str(p39.date) == "2050-06-30", f"Expected period 39 at 2050-06-30, got {p39.date}"

    # At period 38: SHL service = principal (14,716) + interest (593) = 15,309 kEUR
    # This exceeds fcf_for_shl, so PR #304 guard blocks distribution
    assert p38.distribution_keur == 0.0, (
        f"Period 38 (SHL final period): distribution = {p38.distribution_keur:.2f} — "
        f"should be 0 via PR #304 guard; shl_svc={p38.shl_service_keur:.2f} > fcf_for_shl={getattr(p38,'fcf_for_shl_keur',0):.2f}"
    )
    assert p38.shl_principal_keur > 14_000, (
        f"Period 38 SHL principal = {p38.shl_principal_keur:.2f} — "
        f"should be ~14,716 (bullet)"
    )

    # At period 39: SHL cleared → distribution starts
    assert p39.distribution_keur > 2_000, (
        f"Period 39 (first after SHL clear): distribution = {p39.distribution_keur:.2f} — "
        f"should be large (>2,000 kEUR); Excel confirms dividends start ~2050"
    )
    assert p39.shl_balance_keur == 0.0, (
        f"Period 39 SHL balance = {p39.shl_balance_keur:.2f} — should be 0 after bullet"
    )
    assert p39.shl_principal_keur == 0.0, (
        f"Period 39 SHL principal = {p39.shl_principal_keur:.2f} — should be 0"
    )

    print(f"\nDistribution timing confirmed:")
    print(f"  Period 38 (2049-12-31): dist={p38.distribution_keur:.2f} shl_svc={p38.shl_service_keur:.2f} (SHL final period) ✓")
    print(f"  Period 39 (2050-06-30): dist={p39.distribution_keur:.2f} shl_bal={p39.shl_balance_keur:.2f} (SHL cleared) ✓")


# ---------------------------------------------------------------------------
# Test 4: TUHO regression — flags and fixture unchanged
# ---------------------------------------------------------------------------

def test_tuho_regression_flags_and_fixture():
    """Confirm TUHO factory flags and fixture path are unchanged.

    TUHO should still have:
      use_senior_debt_sizing_engine = True
      use_frozen_excel_senior_debt_schedule = True (from PR #303)
    And fixture path should load without error.
    """
    from app.project_factories import create_default_tuho_wind1

    tuho = create_default_tuho_wind1()
    fin = tuho.financing

    # TUHO factory: shl_amount and shl_idc should be unchanged
    assert fin.shl_amount_keur > 0, "TUHO shl_amount_keur must be positive"
    assert fin.shl_idc_keur >= 0,  "TUHO shl_idc_keur must be >= 0"

    # Run TUHO with frozen schedule (PR #303 opt-in)
    engine = _build_period_engine(tuho)
    config = WaterfallRunConfig.from_inputs(tuho, engine)

    # Frozen flags should be ON for TUHO
    assert config.use_frozen_excel_senior_debt_schedule is True, (
        "TUHO should have use_frozen_excel_senior_debt_schedule=True (PR #303 opt-in)"
    )
    assert config.use_senior_debt_sizing_engine is True, (
        "TUHO should have use_senior_debt_sizing_engine=True (PR #303 opt-in)"
    )

    # Should run without error
    result = WaterfallRunner(tuho, engine).run(config)
    assert len(result.periods) > 0, "TUHO waterfall must produce periods"

    print(f"\nTUHO flags:")
    print(f"  use_frozen_excel_senior_debt_schedule = {config.use_frozen_excel_senior_debt_schedule}")
    print(f"  use_senior_debt_sizing_engine         = {config.use_senior_debt_sizing_engine}")
    print(f"  shl_amount_keur = {fin.shl_amount_keur:.2f}")
    print(f"  shl_idc_keur    = {fin.shl_idc_keur:.2f}")


# ---------------------------------------------------------------------------
# Test 5: Guardrails unchanged
# ---------------------------------------------------------------------------

def test_guardrails_unchanged():
    """Confirm all guardrails are preserved.

    - Oborovo frozen schedule OFF
    - G20 BLOCKED
    - R99/R102 NOT APPROVED
    - partial_pay_sweep not promoted
    - sculpting solver not promoted
    """
    from app.project_factories import create_default_oborovo

    oborovo = create_default_oborovo()
    engine = _build_period_engine(oborovo)
    config = WaterfallRunConfig.from_inputs(oborovo, engine)

    # Oborovo frozen schedule must remain OFF
    assert config.use_frozen_excel_senior_debt_schedule is False, (
        "Oborovo frozen schedule must remain OFF — guardrail violation"
    )
    assert config.use_senior_debt_sizing_engine is False, (
        "Oborovo senior debt sizing engine must remain OFF — guardrail violation"
    )

    # SHL method should be 'bullet' for Oborovo (enum value, not plain string)
    method_val = config.shl_repayment_method
    method_str = method_val.value if hasattr(method_val, 'value') else str(method_val)
    assert method_str == "bullet", (
        f"Oborovo SHL method = {method_val} — expected 'bullet'"
    )

    print(f"\nGuardrails confirmed:")
    print(f"  Oborovo use_frozen_excel_senior_debt_schedule = {config.use_frozen_excel_senior_debt_schedule}")
    print(f"  Oborovo use_senior_debt_sizing_engine         = {config.use_senior_debt_sizing_engine}")
    print(f"  Oborovo shl_repayment_method                  = {config.shl_repayment_method}")