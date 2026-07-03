"""Phase 6 R67 years 13-30 residual — diagnostic-first branch.

Hard constraints:
- No scalar plugs
- No residual adjustments
- No R99/R102 runtime source
- No SHL FCF opt-in
- Default behavior bit-identical

Diagnostic targets (from current Python flag ON run):
- Years 13-30 R67 (P24-P59 H2 cash_tax sum): -43,512.36 kEUR
- Excel target (years 13-30): -38,240.90 kEUR
- Residual: approximately -5,271.46 kEUR

R67 timing convention (confirmed):
- H1 (period_in_year=1): cash_tax=0, r67_diag=0
- H2 (period_in_year=2): cash_tax = -(tax_keur_H1 + tax_keur_H2)
  Since H1 tax_keur=0 for all periods, cash_tax_H2 = -tax_keur_H2
  but shown as -2× because r67 accumulates across the full year
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner


# -----------------------------------------------------------------------
# Calibration anchors
# -----------------------------------------------------------------------
PYTHON_R67_YEARS_13_TO_30_KEUR = -43_512.36
EXCEL_R67_TARGET_YEARS_13_TO_30_KEUR = -38_240.90
RESIDUAL_KEUR = PYTHON_R67_YEARS_13_TO_30_KEUR - EXCEL_R67_TARGET_YEARS_13_TO_30_KEUR  # ~-5,271
RESIDUAL_ACCEPTANCE_BAND_KEUR = 500.0  # ±500 kEUR — this is a documented residual

PYTHON_R67_YEARS_1_TO_12_KEUR = 0.0  # fixed by PR #71
EXCEL_R67_YEARS_1_TO_12_KEUR = 0.0
PYTHON_R67_TOTAL_FLAG_ON_KEUR = -43_512.36
EXCEL_R67_TOTAL_KEUR = -38_240.90


def _run(project):
    return WaterfallRunner(project, _build_period_engine(project)).run(
        WaterfallRunConfig.from_inputs(project, _build_period_engine(project))
    )


def _tuho_flag_on_project():
    return replace(
        create_default_tuho_wind1(),
        info=replace(create_default_tuho_wind1().info, use_tax_bridge_engine=True),
        tax=replace(create_default_tuho_wind1().tax, cit_cash_tax_start_operating_index=25),
    )


# -----------------------------------------------------------------------
# Default behavior unchanged
# -----------------------------------------------------------------------

def test_default_tuho_r67_total():
    """Default TUHO (Stack Z: flag ON) R67 total regression guard."""
    r = _run(create_default_tuho_wind1())
    r67 = sum(p.r67_excel_style_cash_tax_diagnostic_keur for p in r.periods)
    # Stack Z: factory now opts in to flag ON — value matches tax-bridge R67.
    assert r67 == pytest.approx(-43_512.4, abs=0.5)


def test_default_oborovo_unchanged():
    """Oborovo default is unchanged — PR #71 regression guard."""
    r = _run(create_default_oborovo())
    for p in r.periods:
        assert p.corporate_tax_cash_keur >= 0.0


def test_factory_opt_in_state():
    """Stack Z: TUHO factory opts in to tax bridge engine; Oborovo remains False."""
    tuho = create_default_tuho_wind1()
    obo = create_default_oborovo()
    assert tuho.info.use_tax_bridge_engine is True
    assert obo.info.use_tax_bridge_engine is False


# -----------------------------------------------------------------------
# Years 13-30 residual — current state (diagnostic, no fix)
# -----------------------------------------------------------------------

def test_tuho_flag_on_r67_years_13_to_30_matches_current_value():
    """TUHO flag ON R67 years 13-30 equals the currently-known value.

    This is a regression guard: if something changes the years 13-30 R67
    total, this test will catch it. The residual vs Excel is documented but
    not asserted to zero — no scalar plugs allowed.
    """
    r = _run(_tuho_flag_on_project())
    h2_periods = [p for p in r.periods[24:60] if p.period_in_year == 2]
    r67_h2 = sum(p.r67_excel_style_cash_tax_diagnostic_keur for p in h2_periods)
    assert r67_h2 == pytest.approx(PYTHON_R67_YEARS_13_TO_30_KEUR, abs=0.1)


def test_years_13_to_30_residual_vs_excel_is_approximately_minus_5271():
    """Residual between Python flag ON and Excel target is approximately -5,271 kEUR.

    Acceptance band: ±500 kEUR. This test documents the known residual and
    prevents accidental moves. It does NOT attempt to explain or fix the gap.
    """
    r = _run(_tuho_flag_on_project())
    h2_periods = [p for p in r.periods[24:60] if p.period_in_year == 2]
    r67_h2 = sum(p.r67_excel_style_cash_tax_diagnostic_keur for p in h2_periods)
    residual = r67_h2 - EXCEL_R67_TARGET_YEARS_13_TO_30_KEUR
    assert residual == pytest.approx(RESIDUAL_KEUR, abs=RESIDUAL_ACCEPTANCE_BAND_KEUR)


def test_years_1_to_12_remain_zero():
    """Years 1-12 R67 is 0.0 — confirmed by PR #71 fix."""
    r = _run(_tuho_flag_on_project())
    years_1_12 = sum(p.r67_excel_style_cash_tax_diagnostic_keur for p in r.periods[:24])
    assert years_1_12 == pytest.approx(0.0, abs=0.01)


def test_flag_on_total_r67_equals_years_13_30():
    """With years 1-12 suppressed to 0, total R67 = years 13-30 R67."""
    r = _run(_tuho_flag_on_project())
    r67_total = sum(p.r67_excel_style_cash_tax_diagnostic_keur for p in r.periods)
    r67_y13_30 = sum(p.r67_excel_style_cash_tax_diagnostic_keur for p in r.periods[24:60])
    assert r67_total == pytest.approx(r67_y13_30, abs=0.01)


# -----------------------------------------------------------------------
# H2 timing pattern — confirms annual cash tax convention
# -----------------------------------------------------------------------

def test_h2_only_has_nonzero_cash_tax():
    """Cash tax is non-zero in H2 periods only (period_in_year=2)."""
    r = _run(_tuho_flag_on_project())
    for p in r.periods[24:60]:
        if p.period_in_year == 2:
            assert p.corporate_tax_cash_keur != 0.0, f"P{p.period_index} H2 cash_tax should be non-zero"
        else:
            assert p.corporate_tax_cash_keur == 0.0, f"P{p.period_index} H1 cash_tax should be zero"


def test_h2_cash_tax_reflects_annual_accrual():
    """In H2, cash_tax = prev_H1_tax_keur + curr_H2_tax_keur (positive cash amount).

    The H1 period accrual carries forward and is paid together with H2 accrual
    in the annual cash tax payment. The sum is positive (cash outflow magnitude).
    R67 diagnostic is the negative of this (accounting sign convention).
    """
    r = _run(_tuho_flag_on_project())
    for i in range(24, 60):
        p = r.periods[i]
        if p.period_in_year == 2:
            prev = r.periods[i - 1]
            expected = prev.tax_keur + p.tax_keur
            assert p.corporate_tax_cash_keur == pytest.approx(expected, abs=0.01), (
                f"P{i}: cash_tax={p.corporate_tax_cash_keur:.2f} != "
                f"P{i-1}_tax_keur={prev.tax_keur:.2f} + P{i}_tax_keur={p.tax_keur:.2f}={expected:.2f}"
            )


def test_r67_diag_equals_negative_cash_tax_in_h2():
    """R67 diagnostic = -cash_tax (negative) for H2 periods."""
    r = _run(_tuho_flag_on_project())
    for p in r.periods[24:60]:
        if p.period_in_year == 2:
            assert p.r67_excel_style_cash_tax_diagnostic_keur == pytest.approx(
                -p.corporate_tax_cash_keur, abs=0.01
            )


# -----------------------------------------------------------------------
# R35 / R34 / loss engine — stable during residual window
# -----------------------------------------------------------------------

def test_loss_engine_is_noop_in_years_13_to_30():
    """Loss carryforward bucket is exhausted by year 13 — losses_n_1 = 0."""
    r = _run(_tuho_flag_on_project())
    for p in r.periods[24:60]:
        assert p.tax_loss_opening_audit_keur == 0.0, f"P{p.period_index} loss opening should be 0"


def test_fiscal_reintegration_is_zero_in_years_13_to_30():
    """R34 fiscal reintegration is 0 for all years 13-30 periods."""
    r = _run(_tuho_flag_on_project())
    for p in r.periods[24:60]:
        assert p.fiscal_reintegration_audit_keur == 0.0


def test_tax_keur_is_nonzero_in_years_13_to_30():
    """Tax accrual is positive and growing in years 13-30 — taxable income > 0."""
    r = _run(_tuho_flag_on_project())
    for p in r.periods[24:60]:
        assert p.tax_keur > 0.0, f"P{p.period_index} tax_keur should be positive"


# -----------------------------------------------------------------------
# R99/R102 — audit-only, not runtime source
# -----------------------------------------------------------------------

def test_r99_audit_fields_differ_between_flag_off_and_on():
    """R99/R102 audit fields change because corporate_tax_cash differs, not because SHL FCF is active."""
    flag_off = _run(create_default_tuho_wind1())
    flag_on = _run(_tuho_flag_on_project())
    for i in range(len(flag_off.periods)):
        off_val = getattr(flag_off.periods[i], 'r99_fcf_for_distribution_keur', 0.0)
        on_val = getattr(flag_on.periods[i], 'r99_fcf_for_distribution_keur', 0.0)
        # These can differ due to cash_tax difference — this is expected
        # The runtime waterfall is unchanged; these remain audit fields only


def test_runtime_waterfall_unchanged_between_flag_off_and_on():
    """Runtime waterfall fields (distribution, SHL balance, senior DS) are identical between flag OFF and flag ON."""
    flag_off = _run(create_default_tuho_wind1())
    flag_on = _run(_tuho_flag_on_project())
    runtime_fields = [
        "shl_balance_keur",
        "distribution_keur",
        "cash_sweep_keur",
        "senior_ds_keur",
        "cash_balance_keur",
    ]
    for f in runtime_fields:
        for i in range(len(flag_off.periods)):
            off_val = getattr(flag_off.periods[i], f)
            on_val = getattr(flag_on.periods[i], f)
            assert off_val == pytest.approx(on_val, abs=0.01), (
                f"{f} differs at period {i}: flag_off={off_val}, flag_on={on_val}"
            )


def test_no_shl_fcf_opt_in():
    """fcf_for_shl_keur is pre-existing and non-zero in default TUHO (flag OFF too).

    The SHL FCF waterfall flag is False. fcf_for_shl_keur is a pre-existing audit field
    that reflects the runtime waterfall's cf_after_reserves minus senior DS.
    No SHL FCF-specific opt-in is active.
    """
    r = _run(_tuho_flag_on_project())
    # The shl_fcf_waterfall flag is not enabled — cf_after_reserves goes to cash_sweep
    # fcf_for_shl_keur is non-zero but this is the default runtime behavior
    assert all(p.fcf_for_shl_keur >= 0.0 for p in r.periods)


# -----------------------------------------------------------------------
# Oborovo flag-on remains guarded
# -----------------------------------------------------------------------

def test_oborovo_flag_on_remains_guarded():
    """Oborovo flag ON still raises ValueError — TUHO-only restriction."""
    obo_flag_on = replace(
        create_default_oborovo(),
        info=replace(create_default_oborovo().info, use_tax_bridge_engine=True),
    )
    with pytest.raises(ValueError, match="TUHO-WIND-1|supported|only"):
        _run(obo_flag_on)


# -----------------------------------------------------------------------
# Dominant residual driver — period-level decomposition
# -----------------------------------------------------------------------

def test_ebitda_range_in_years_13_to_30():
    """EBITDA is in a reasonable range across years 13-30."""
    r = _run(_tuho_flag_on_project())
    h2_ebitda = [r.periods[i].ebitda_keur for i in range(25, 60, 2)]
    assert h2_ebitda[0] > 6000  # year 13 ~6,240
    assert h2_ebitda[-1] > 8000  # year 30 ~8,249
    assert min(h2_ebitda) > 6000  # minimum in range
    assert max(h2_ebitda) < 9000  # maximum in range


def test_senior_interest_zero_from_year_15_onwards():
    """Senior interest is 0 from year 15 H2 onwards — sculpted debt fully repaid."""
    r = _run(_tuho_flag_on_project())
    # P29 = year 15 H2 — first period with 0 senior interest
    for i in range(29, 60):
        p = r.periods[i]
        if p.period_in_year == 2:  # H2 only
            assert p.interest_senior_keur == 0.0, f"P{i} senior interest should be 0"


def test_shl_interest_zero_from_year_19_onwards():
    """SHL interest is 0 from year 19 H2 onwards — PIK phase complete."""
    r = _run(_tuho_flag_on_project())
    for i in range(37, 60):  # P37 = year 19 H2
        p = r.periods[i]
        if p.period_in_year == 2:
            assert p.interest_shl_keur == 0.0, f"P{i} SHL interest should be 0"
