"""Phase 23P: Oborovo Post-Lockup Parity Snapshot.

Diagnostic-only: confirms Phase 23O bullet SHL distribution lock-up fix
has successfully resolved the Phase 23N blocker.

Phase 23N (PR #313): detected Oborovo distributing pre-2050 while SHL outstanding.
Phase 23O (PR #314): fixed bullet SHL lock-up gate — shl_balance > 0 blocks distribution.
Phase 23P (this PR): confirms fix is working — no runtime changes.

No runtime changes. All assertions verify the corrected post-fix state.
"""

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _oborovo_result():
    oborovo = create_default_oborovo()
    engine = _build_period_engine(oborovo)
    config = WaterfallRunConfig.from_inputs(oborovo, engine)
    result = WaterfallRunner(oborovo, engine).run(config)
    return [p for p in result.periods if p.is_operation]


# ---------------------------------------------------------------------------
# Test 1: Corrected anchors still valid
# ---------------------------------------------------------------------------

def test_oborovo_corrected_anchors_still_valid():
    """Oborovo factory anchors remain correctly set after Phase 23O fix."""
    oborovo = create_default_oborovo()
    fin = oborovo.financing
    engine = _build_period_engine(oborovo)
    config = WaterfallRunConfig.from_inputs(oborovo, engine)

    assert fin.shl_amount_keur == pytest.approx(14_621.0, abs=0.1), (
        f"shl_amount_keur = {fin.shl_amount_keur} — expected 14,621.0"
    )
    assert fin.shl_idc_keur == pytest.approx(1_169.0, abs=1.0), (
        f"shl_idc_keur = {fin.shl_idc_keur} — expected 1,169.0"
    )
    assert fin.shl_tenor_years == 20, (
        f"shl_tenor_years = {fin.shl_tenor_years} — expected 20"
    )
    opening = fin.shl_amount_keur + fin.shl_idc_keur
    assert opening == pytest.approx(15_790.0, abs=1.0), (
        f"Opening SHL = {opening:.1f} — expected 15,790.0"
    )
    assert config.use_frozen_excel_senior_debt_schedule is False, (
        "Oborovo frozen schedule must remain OFF"
    )
    assert config.use_senior_debt_sizing_engine is False, (
        "Oborovo senior sizing must remain OFF"
    )


# ---------------------------------------------------------------------------
# Test 2: No distributions while SHL principal outstanding
# ---------------------------------------------------------------------------

def test_oborovo_no_distribution_while_shl_principal_outstanding():
    """All operating periods with SHL balance > tolerance show distribution_keur == 0.

    This is the core Phase 23O lock-up confirmation: after the fix,
    no period should distribute while SHL principal remains outstanding.
    """
    op_periods = _oborovo_result()

    TOLERANCE = 1.0
    violations = [
        (p.date, p.shl_balance_keur, p.distribution_keur)
        for p in op_periods
        if p.shl_balance_keur > TOLERANCE
        and p.distribution_keur > TOLERANCE
    ]

    assert len(violations) == 0, (
        f"Oborovo: {len(violations)} period(s) distributing while SHL outstanding:\n" +
        "\n".join(f"  {d}: bal={b:.1f}, dist={dist:.2f}" for d, b, dist in violations)
    )


# ---------------------------------------------------------------------------
# Test 3: Pre-2050 distributions now blocked
# ---------------------------------------------------------------------------

def test_oborovo_pre_2050_distributions_now_blocked():
    """Known Phase 23N leaking periods: distribution_keur == 0 after Phase 23O fix.

    Phase 23N identified these periods as incorrectly distributing:
      op 0, 28, 29, 31 (and 32-37) — distributions while SHL = 15,790 kEUR
    Phase 23O block now makes all of them 0.
    """
    op_periods = _oborovo_result()

    TOLERANCE = 1.0
    known_leaking = {0, 28, 29, 31, 32, 33, 34, 35, 36, 37}
    failures = []
    for idx in known_leaking:
        p = op_periods[idx]
        if p.distribution_keur > TOLERANCE:
            failures.append(f"Op[{idx}] {p.date}: dist={p.distribution_keur:.2f} (shl_bal={p.shl_balance_keur:.1f})")

    assert not failures, (
        f"Pre-2050 distributions still leaking after Phase 23O fix:\n" +
        "\n".join(f"  {f}" for f in failures)
    )


# ---------------------------------------------------------------------------
# Test 4: Distribution resumes after SHL cleared
# ---------------------------------------------------------------------------

def test_oborovo_distribution_resumes_after_shl_cleared():
    """First distribution after SHL balance == 0 occurs at op 39 / 2050-06-30.

    SHL cleared at op 38 (2049-12-31, shl_balance=0). First valid
    distribution: op 39 (2050-06-30).
    """
    op_periods = _oborovo_result()

    TOLERANCE = 1.0
    post_clear = [p for p in op_periods if p.shl_balance_keur < TOLERANCE and p.distribution_keur > TOLERANCE]

    assert len(post_clear) > 0, "No post-SHL distributions found"

    first = post_clear[0]
    assert str(first.date) == "2050-06-30", (
        f"First post-SHL distribution at {first.date}, expected 2050-06-30"
    )
    assert first.distribution_keur > 2_000, (
        f"First distribution = {first.distribution_keur:.2f} kEUR — expected large (>2,000)"
    )

    print(f"\nPost-SHL distributions confirmed:")
    print(f"  First: op[39] {first.date}  dist={first.distribution_keur:.2f}  shl_bal={first.shl_balance_keur:.1f} ✓")


# ---------------------------------------------------------------------------
# Test 5: Phase 23N blocker remains resolved
# ---------------------------------------------------------------------------

def test_phase23n_blocker_remains_resolved():
    """Phase 23N mismatch detector: count must be 0 after Phase 23O fix.

    Phase 23N pre-fix: len(mismatch) > 0 — bug existed.
    Phase 23O: bug fixed — mismatch list now empty.
    """
    op_periods = _oborovo_result()

    TOLERANCE = 1.0
    mismatch = [
        p for p in op_periods
        if str(p.date) < "2050-01-01"
        and p.shl_balance_keur > TOLERANCE
        and p.distribution_keur > TOLERANCE
    ]

    print(f"\n[resolved] Pre-2050 mismatch count: {len(mismatch)}")
    if mismatch:
        for p in mismatch[:5]:
            print(f"  {p.date}: dist={p.distribution_keur:.2f}  shl_bal={p.shl_balance_keur:.1f}")

    assert len(mismatch) == 0, (
        f"Phase 23N blocker NOT resolved — {len(mismatch)} period(s) still leaking"
    )


# ---------------------------------------------------------------------------
# Test 6: TUHO regression — flags and fixture
# ---------------------------------------------------------------------------

def test_tuho_regression_flags_and_fixture():
    """TUHO flags remain True; fixture-backed frozen senior DS still loads."""
    tuho = create_default_tuho_wind1()
    engine = _build_period_engine(tuho)
    config = WaterfallRunConfig.from_inputs(tuho, engine)

    assert config.use_frozen_excel_senior_debt_schedule is True, (
        "TUHO frozen schedule must remain True (PR #303)"
    )
    assert config.use_senior_debt_sizing_engine is True, (
        "TUHO senior sizing must remain True"
    )

    result = WaterfallRunner(tuho, engine).run(config)
    assert len(result.periods) > 0, "TUHO waterfall must produce periods"


# ---------------------------------------------------------------------------
# Test 7: Guardrails unchanged
# ---------------------------------------------------------------------------

def test_guardrails_unchanged():
    """Confirm all hard guardrails preserved after Phase 23O."""
    oborovo = create_default_oborovo()
    engine = _build_period_engine(oborovo)
    config = WaterfallRunConfig.from_inputs(oborovo, engine)

    assert config.use_frozen_excel_senior_debt_schedule is False, (
        "G20 guardrail violated: Oborovo frozen must remain OFF"
    )
    assert config.use_senior_debt_sizing_engine is False, (
        "G20 guardrail violated: Oborovo sizing must remain OFF"
    )

    tuho = create_default_tuho_wind1()
    tuho_engine = _build_period_engine(tuho)
    tuho_config = WaterfallRunConfig.from_inputs(tuho, tuho_engine)
    assert tuho_config.use_frozen_excel_senior_debt_schedule is True, (
        "TUHO frozen schedule must remain True"
    )

    print(f"\nGuardrails intact: Oborovo frozen={config.use_frozen_excel_senior_debt_schedule}, "
          f"TUHO frozen={tuho_config.use_frozen_excel_senior_debt_schedule}")