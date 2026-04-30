"""DSCR schedule policy tests.

These tests make the PPA-vs-merchant DSCR assumption explicit. TUHO already
uses 1.20 during PPA and 1.40 after PPA in the first-pass factory. Oborovo
first12 extracted Excel rows currently use 1.15, so Oborovo merchant-period
DSCR policy remains pending until later period rows are extracted.
"""
from __future__ import annotations

from app.calibration import build_run_config, load_project_inputs


def test_tuho_uses_dual_dscr_schedule_for_ppa_and_merchant_periods() -> None:
    inputs = load_project_inputs("tuho")
    config = build_run_config(inputs)

    assert config.target_dscr == 1.20
    assert config.dscr_schedule is not None
    assert config.dscr_schedule[:24] == [1.20] * 24
    assert config.dscr_schedule[24:64] == [1.40] * 40


def test_oborovo_first_pass_dscr_policy_is_single_115_until_more_excel_rows_are_mapped() -> None:
    inputs = load_project_inputs("oborovo")
    config = build_run_config(inputs)

    assert config.target_dscr == 1.15
    assert config.dscr_schedule is None
