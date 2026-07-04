"""Phase 20O: Debt Sizing Mode Architecture tests.

These tests verify:
1. Mode config defaults
2. Runtime regression (TUHO + Oborovo unchanged)
3. Future-mode guards (NotImplementedError)
4. Documentation mentions (manual — checked in docstring)
"""
import pytest
from app.project_factories import create_default_tuho_wind1, create_default_oborovo
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.inputs import (
    DebtSizingMode,
    DebtSizingMethod,
    FinancingParams,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Mode config defaults
# ─────────────────────────────────────────────────────────────────────────────

def test_default_debt_sizing_mode_is_frozen_excel_schedule():
    """Default debt_sizing_mode on FinancingParams is None, which resolves
    to FROZEN_EXCEL_SCHEDULE for backward compatibility."""
    fp = FinancingParams()
    assert fp.debt_sizing_mode is None
    assert fp.resolved_debt_sizing_mode() == DebtSizingMode.FROZEN_EXCEL_SCHEDULE


def test_debt_sizing_mode_enum_values_present():
    """All three required mode values exist on the enum."""
    assert DebtSizingMode.FROZEN_EXCEL_SCHEDULE.value == "frozen_excel_schedule"
    assert DebtSizingMode.MINIMUM_DSCR_SCULPTED.value == "minimum_dscr_sculpted"
    assert DebtSizingMode.FLAT_DSCR_SCULPTED.value == "flat_dscr_sculpted"


def test_frozen_excel_schedule_resolves_cleanly():
    """FROZEN_EXCEL_SCHEDULE.validate_and_resolve() returns itself with no error."""
    mode = DebtSizingMode.FROZEN_EXCEL_SCHEDULE.validate_and_resolve()
    assert mode == DebtSizingMode.FROZEN_EXCEL_SCHEDULE


# ─────────────────────────────────────────────────────────────────────────────
# 2. Runtime regression — TUHO
# ─────────────────────────────────────────────────────────────────────────────

def _run_tuho():
    tuho = create_default_tuho_wind1()
    eng = _build_period_engine(tuho)
    cfg = WaterfallRunConfig.from_inputs(tuho, eng)
    r = WaterfallRunner(inputs=tuho, engine=eng)
    return r.run(cfg)


def test_tuho_default_outputs_unchanged_total_senior_ds():
    """TUHO total_senior_ds_keur baseline: 65,826 kEUR."""
    result = _run_tuho()
    assert abs(result.total_senior_ds_keur - 65_826) < 1


def test_tuho_default_outputs_unchanged_total_distribution():
    """TUHO total_distribution_keur baseline: 173,572 kEUR."""
    result = _run_tuho()
    assert abs(result.total_distribution_keur - 173_572) < 1


def test_tuho_default_outputs_unchanged_avg_dscr():
    """TUHO avg_dscr baseline: 1.230."""
    result = _run_tuho()
    assert abs(result.avg_dscr - 1.230) < 0.005


def test_tuho_default_outputs_unchanged_equity_irr():
    """TUHO equity_irr baseline: ~0.1115."""
    result = _run_tuho()
    assert abs(result.equity_irr - 0.1115) < 0.002


# ─────────────────────────────────────────────────────────────────────────────
# 3. Runtime regression — Oborovo
# ─────────────────────────────────────────────────────────────────────────────

def _run_oboro():
    obor = create_default_oborovo()
    eng = _build_period_engine(obor)
    cfg = WaterfallRunConfig.from_inputs(obor, eng)
    r = WaterfallRunner(inputs=obor, engine=eng)
    return r.run(cfg)


def test_oborovo_default_outputs_unchanged_total_senior_ds():
    """Oborovo total_senior_ds_keur baseline: 63,501 kEUR."""
    result = _run_oboro()
    assert abs(result.total_senior_ds_keur - 63_501) < 1


def test_oborovo_default_outputs_unchanged_total_distribution():
    """Oborovo total_distribution_keur baseline: 104,699 kEUR."""
    result = _run_oboro()
    assert abs(result.total_distribution_keur - 104_699) < 1


def test_oborovo_default_outputs_unchanged_avg_dscr():
    """Oborovo avg_dscr baseline: 1.150."""
    result = _run_oboro()
    assert abs(result.avg_dscr - 1.150) < 0.005


def test_oborovo_default_outputs_unchanged_equity_irr():
    """Oborovo equity_irr baseline: ~0.0917."""
    result = _run_oboro()
    assert abs(result.equity_irr - 0.0917) < 0.002


# ─────────────────────────────────────────────────────────────────────────────
# 4. Mode resolution — V3-3: both sculpted modes now implemented
# ─────────────────────────────────────────────────────────────────────────────

def test_minimum_dscr_sculpted_resolves_cleanly():
    """V3-3: MINIMUM_DSCR_SCULPTED.validate_and_resolve() no longer raises."""
    mode = DebtSizingMode.MINIMUM_DSCR_SCULPTED
    resolved = mode.validate_and_resolve()
    assert resolved == DebtSizingMode.MINIMUM_DSCR_SCULPTED


def test_flat_dscr_sculpted_resolves_cleanly():
    """V3-3: FLAT_DSCR_SCULPTED.validate_and_resolve() no longer raises."""
    mode = DebtSizingMode.FLAT_DSCR_SCULPTED
    resolved = mode.validate_and_resolve()
    assert resolved == DebtSizingMode.FLAT_DSCR_SCULPTED


def test_explicit_frozen_mode_on_financing_params_resolves():
    """Setting debt_sizing_mode=FROZEN_EXCEL_SCHEDULE explicitly resolves cleanly."""
    fp = FinancingParams(debt_sizing_mode=DebtSizingMode.FROZEN_EXCEL_SCHEDULE)
    assert fp.resolved_debt_sizing_mode() == DebtSizingMode.FROZEN_EXCEL_SCHEDULE


def test_financing_params_with_minimum_dscr_mode_resolves():
    """V3-3: setting debt_sizing_mode=MINIMUM_DSCR_SCULPTED resolves cleanly."""
    fp = FinancingParams(debt_sizing_mode=DebtSizingMode.MINIMUM_DSCR_SCULPTED)
    assert fp.resolved_debt_sizing_mode() == DebtSizingMode.MINIMUM_DSCR_SCULPTED


# ─────────────────────────────────────────────────────────────────────────────
# 5. New fields on FinancingParams
# ─────────────────────────────────────────────────────────────────────────────

def test_financing_params_target_min_dscr_field():
    """target_min_dscr field exists and defaults to None."""
    fp = FinancingParams(target_min_dscr=1.45)
    assert fp.target_min_dscr == 1.45
    assert fp.debt_sizing_mode is None  # still None


def test_financing_params_flat_dscr_target_field():
    """flat_dscr_target field exists and defaults to None."""
    fp = FinancingParams(flat_dscr_target=1.15)
    assert fp.flat_dscr_target == 1.15


def test_financing_params_frozen_schedule_note_field():
    """frozen_schedule_note field exists and defaults to None."""
    fp = FinancingParams(frozen_schedule_note="Macro!R50 frozen per-period schedule")
    assert fp.frozen_schedule_note == "Macro!R50 frozen per-period schedule"


def test_sizing_mode_description_contains_frozen_schedule():
    """sizing_mode_description returns a string mentioning frozen_excel_schedule."""
    fp = FinancingParams(frozen_schedule_note="Macro!R50")
    desc = fp.sizing_mode_description
    assert "FROZEN_EXCEL_SCHEDULE" in desc
    assert "DSCR" in desc


def test_sizing_mode_description_contains_note():
    """sizing_mode_description includes frozen_schedule_note when set."""
    fp = FinancingParams(frozen_schedule_note="Macro!R50")
    desc = fp.sizing_mode_description
    assert "Macro!R50" in desc


# ─────────────────────────────────────────────────────────────────────────────
# 6. Project template documentation (not runtime checks)
# ─────────────────────────────────────────────────────────────────────────────

def test_tuho_factory_has_default_sizing_method():
    """TUHO factory sets a debt_sizing_method (string) — checked for presence."""
    tuho = create_default_tuho_wind1()
    assert tuho.financing.debt_sizing_method in ["dscr_sculpt", "gearing_cap", "fixed"]


def test_oborovo_factory_has_default_sizing_method():
    """Oborovo factory sets a debt_sizing_method (string)."""
    obor = create_default_oborovo()
    assert obor.financing.debt_sizing_method in ["dscr_sculpt", "gearing_cap", "fixed"]
