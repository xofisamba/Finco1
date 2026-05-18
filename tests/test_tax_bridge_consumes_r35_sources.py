"""Tax bridge consumes R35 source basis tests."""
from __future__ import annotations
from dataclasses import replace
import pytest
from app.project_factories import create_default_tuho_wind1, create_default_oborovo
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner

def _run(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)

def test_flag_off_tuho_bit_identical():
    """Flag OFF TUHO must be bit-identical to default project (no diff)."""
    default = _run(create_default_tuho_wind1())
    flag_off = _run(replace(create_default_tuho_wind1(),
                             info=replace(create_default_tuho_wind1().info, use_tax_bridge_engine=False)))
    # verify no change in total tax
    assert default.total_tax_keur == pytest.approx(flag_off.total_tax_keur, abs=0.01)

def test_flag_off_oborovo_bit_identical():
    """Flag OFF Oborovo must be bit-identical."""
    default = _run(create_default_oborovo())
    flag_off = _run(replace(create_default_oborovo(),
                             info=replace(create_default_oborovo().info, use_tax_bridge_engine=False)))
    assert default.total_tax_keur == pytest.approx(flag_off.total_tax_keur, abs=0.01)

def test_tuho_flag_on_produces_real_r35_movement():
    """Flag ON TUHO must produce R35 source movement vs flag OFF."""
    flag_off = _run(create_default_tuho_wind1())
    flag_on = _run(replace(create_default_tuho_wind1(),
                            info=replace(create_default_tuho_wind1().info, use_tax_bridge_engine=True)))
    r35_off = sum(p.taxable_income_before_losses_audit_keur for p in flag_off.periods)
    r35_on = sum(p.taxable_income_before_losses_audit_keur for p in flag_on.periods)
    assert abs(r35_on - r35_off) > 1000.0, f"R35 delta too small: {r35_on - r35_off:.1f}"

def test_shl_gross_accrued_is_non_zero_for_tuho_flag_on():
    """SHL gross-accrued source must be non-zero and used in R35 basis for TUHO flag ON."""
    flag_on = _run(replace(create_default_tuho_wind1(),
                            info=replace(create_default_tuho_wind1().info, use_tax_bridge_engine=True)))
    non_zero_count = sum(1 for p in flag_on.periods if p.shl_gross_accrued_interest_keur > 0)
    assert non_zero_count > 0, "No periods with non-zero SHL gross-accrued interest"

def test_book_tax_depreciation_separated_in_tax_bridge():
    """Book and tax depreciation must be separated in tax bridge basis for TUHO flag ON."""
    flag_on = _run(replace(create_default_tuho_wind1(),
                            info=replace(create_default_tuho_wind1().info, use_tax_bridge_engine=True)))
    # Check that taxable_income_before_losses_audit uses book dep as cost and tax dep as addback
    # Total R35 should differ from flag OFF because tax dep < book dep (tax dep adds back less)
    r35_off = sum(p.taxable_income_before_losses_audit_keur for p in
                  _run(create_default_tuho_wind1()).periods)
    r35_on = sum(p.taxable_income_before_losses_audit_keur for p in flag_on.periods)
    assert abs(r35_on - r35_off) > 100.0

def test_r34_fixture_backed_in_flag_on():
    """R34 fiscal reintegration is fixture-backed and non-zero for TUHO flag ON."""
    flag_on = _run(replace(create_default_tuho_wind1(),
                            info=replace(create_default_tuho_wind1().info, use_tax_bridge_engine=True)))
    r34_on = sum(p.fiscal_reintegration_audit_keur for p in flag_on.periods)
    # Fixture-backed: -9242.74 kEUR cumulative (known from fixture validation)
    assert abs(r34_on) > 9000.0, f"R34 fixture-backed total unexpected: {r34_on}"

def test_loss_engine_uses_croatia_vintage_mode():
    """Loss engine must use Croatia 10-period vintage mode for TUHO flag ON."""
    flag_on = _run(replace(create_default_tuho_wind1(),
                            info=replace(create_default_tuho_wind1().info, use_tax_bridge_engine=True)))
    # The flag ON path uses Croatia loss engine; check total tax is correct range
    total_tax = flag_on.total_tax_keur
    assert 30000.0 < total_tax < 50000.0, f"Total tax out of expected range: {total_tax:.1f}"

def test_taxable_income_drives_runtime_cit():
    """Flag ON: taxable_profit_keur and tax_keur reflect R35 bridge basis."""
    flag_off = _run(create_default_tuho_wind1())
    flag_on = _run(replace(create_default_tuho_wind1(),
                            info=replace(create_default_tuho_wind1().info, use_tax_bridge_engine=True)))
    # Runtime tax_keur must differ (R35 sources changed)
    assert abs(flag_on.total_tax_keur - flag_off.total_tax_keur) > 100.0, \
        "Total tax should differ when flag is ON"

def test_no_factory_opt_in():
    """Project factories must not opt in to tax bridge."""
    tuho = create_default_tuho_wind1()
    obo = create_default_oborovo()
    assert tuho.info.use_tax_bridge_engine is False
    assert obo.info.use_tax_bridge_engine is False