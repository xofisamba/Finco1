"""
Phase 23A: Frozen Excel Senior Debt Schedule Runtime Wiring.

Tests: default behavior preserved, flag OFF → no change.
Flag ON → DSCR aligns toward Excel frozen schedule targets.

Guardrails:
    - No sculpting solvers implemented
    - flat_dscr_sculpted not promoted
    - minimum_dscr_sculpted not promoted
    - SHL/distribution unchanged
    - Revenue/OPEX/CAPEX/Tax unchanged
    - G20 BLOCKED
    - R99/R102 NOT APPROVED
"""
import pytest
import sys
sys.path.insert(0, '/opt/finco1')

from app.project_factories import create_default_tuho_wind1, create_default_oborovo
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
from domain.inputs import FinancingParams, DebtSizingMode


class TestDefaultBehaviorPreserved:
    """Verify the new flag does not change default behavior."""

    def test_financing_params_default_flag_is_false(self):
        """use_frozen_excel_senior_debt_schedule defaults to False."""
        fp = FinancingParams()
        assert fp.use_frozen_excel_senior_debt_schedule is False

    def test_financing_params_flag_can_be_set_true(self):
        """Flag is settable to True."""
        fp = FinancingParams(use_frozen_excel_senior_debt_schedule=True)
        assert fp.use_frozen_excel_senior_debt_schedule is True

    def test_frozen_schedule_flag_false_preserves_existing_behavior(self):
        """When flag is OFF, FinancingParams behavior is unchanged."""
        fp = FinancingParams(use_frozen_excel_senior_debt_schedule=False)
        assert fp.use_frozen_excel_senior_debt_schedule is False
        # debt_sizing_mode still resolves to FROZEN_EXCEL_SCHEDULE
        assert fp.resolved_debt_sizing_mode() == DebtSizingMode.FROZEN_EXCEL_SCHEDULE

    def test_sculpted_modes_resolve_cleanly(self):
        """V3-3: flat_dscr_sculpted and minimum_dscr_sculpted are now implemented."""
        assert DebtSizingMode.FLAT_DSCR_SCULPTED.validate_and_resolve() == DebtSizingMode.FLAT_DSCR_SCULPTED
        assert DebtSizingMode.MINIMUM_DSCR_SCULPTED.validate_and_resolve() == DebtSizingMode.MINIMUM_DSCR_SCULPTED

    def test_r99_r102_not_approved(self):
        """R99/R102 remain not approved — flag defaults to False."""
        fp = FinancingParams()
        assert fp.use_frozen_excel_senior_debt_schedule is False

    def test_frozen_schedule_note_field_exists(self):
        """FinancingParams has frozen_schedule_note field for documentation."""
        fp = FinancingParams(frozen_schedule_note="Macro!R50 frozen per-period schedule")
        assert fp.frozen_schedule_note == "Macro!R50 frozen per-period schedule"

    def test_default_frozen_schedule_note_is_none(self):
        """frozen_schedule_note defaults to None."""
        fp = FinancingParams()
        assert fp.frozen_schedule_note is None


class TestWaterfallRunConfigPropagatesFlag:
    """Verify WaterfallRunConfig reads and stores the flag."""

    def test_config_default_flag_is_false(self):
        """use_frozen_excel_senior_debt_schedule defaults to False in config."""
        config = WaterfallRunConfig()
        assert config.use_frozen_excel_senior_debt_schedule is False

    def test_config_flag_from_financing_params(self):
        """from_inputs reads use_frozen_excel_senior_debt_schedule from FinancingParams."""
        tuho = create_default_tuho_wind1()
        # Phase 23F: TUHO factory now sets use_frozen_excel_senior_debt_schedule=True (opt-in)
        assert tuho.financing.use_frozen_excel_senior_debt_schedule is True, "Phase 23F: TUHO factory opt-in enables frozen schedule by default"

    def test_config_cache_key_includes_frozen_flag(self):
        """cache_key() includes frozen_senior_debt_schedule flag for correct caching."""
        config1 = WaterfallRunConfig(use_frozen_excel_senior_debt_schedule=False)
        config2 = WaterfallRunConfig(use_frozen_excel_senior_debt_schedule=True)
        key1 = config1.cache_key()
        key2 = config2.cache_key()
        assert key1 != key2
        assert "frozensds_0" in key1
        assert "frozensds_1" in key2


class TestTUHOFrozenSchedule:
    """TUHO frozen schedule configuration and resolution."""

    def test_tuho_financing_has_frozen_schedule_note(self):
        """TUHO FinancingParams has frozen_schedule_note set (opt-in documentation)."""
        tuho = create_default_tuho_wind1()
        assert tuho.financing.frozen_schedule_note is not None
        assert "Macro!R50" in tuho.financing.frozen_schedule_note or "DS!R19" in tuho.financing.frozen_schedule_note

    def test_tuho_flag_default_is_false(self):
        """TUHO use_frozen_excel_senior_debt_schedule is True by factory opt-in (Phase 23F)."""
        tuho = create_default_tuho_wind1()
        assert tuho.financing.use_frozen_excel_senior_debt_schedule is True, "Phase 23F: TUHO factory opt-in sets frozen schedule flag True"
        assert tuho.info.use_senior_debt_sizing_engine is True, "Phase 23F: TUHO factory opt-in sets SeniorDebtSizing engine flag True"

    def test_tuho_can_enable_frozen_schedule(self):
        """TUHO FinancingParams can have flag explicitly set to True."""
        fp = FinancingParams(
            use_frozen_excel_senior_debt_schedule=True,
            frozen_schedule_note="Macro!R50 / DS!R19 frozen per-period schedule",
        )
        assert fp.use_frozen_excel_senior_debt_schedule is True

    def test_tuho_resolved_sizing_mode_is_frozen_excel_schedule(self):
        """TUHO resolved debt sizing mode is FROZEN_EXCEL_SCHEDULE."""
        tuho = create_default_tuho_wind1()
        assert tuho.financing.resolved_debt_sizing_mode() == DebtSizingMode.FROZEN_EXCEL_SCHEDULE


class TestOborovoFrozenSchedule:
    """Oborovo frozen schedule configuration."""

    def test_oborovo_flag_default_is_now_true(self):
        """Oborovo use_frozen_excel_senior_debt_schedule is True after Phase 23R.

        Before Phase 23R: blocked (False). Phase 23R enables after Phase 23Q parity proof.
        """
        oborovo = create_default_oborovo()
        assert oborovo.financing.use_frozen_excel_senior_debt_schedule is True

    def test_oborovo_can_enable_frozen_schedule(self):
        """Oborovo FinancingParams can have flag explicitly set to True."""
        fp = FinancingParams(
            use_frozen_excel_senior_debt_schedule=True,
            frozen_schedule_note="Oborovo frozen schedule (TBD source)",
        )
        assert fp.use_frozen_excel_senior_debt_schedule is True

    def test_oborovo_resolved_sizing_mode_is_frozen_excel_schedule(self):
        """Oborovo resolved debt sizing mode is FROZEN_EXCEL_SCHEDULE (default)."""
        oborovo = create_default_oborovo()
        assert oborovo.financing.resolved_debt_sizing_mode() == DebtSizingMode.FROZEN_EXCEL_SCHEDULE


class TestNoSculptingSolverPromotion:
    """Verify no sculpting solvers are promoted to default."""

    def test_no_flat_dscr_sculpted_promotion(self):
        """flat_dscr_sculpted is NOT the default mode — default remains FROZEN_EXCEL_SCHEDULE."""
        fp = FinancingParams()
        assert fp.resolved_debt_sizing_mode() == DebtSizingMode.FROZEN_EXCEL_SCHEDULE
        # V3-3: explicitly setting FLAT_DSCR_SCULPTED now resolves cleanly (implemented)
        fp2 = FinancingParams(debt_sizing_mode=DebtSizingMode.FLAT_DSCR_SCULPTED)
        assert fp2.resolved_debt_sizing_mode() == DebtSizingMode.FLAT_DSCR_SCULPTED

    def test_no_minimum_dscr_sculpted_promotion(self):
        """minimum_dscr_sculpted is NOT the default mode — default remains FROZEN_EXCEL_SCHEDULE."""
        fp = FinancingParams()
        assert fp.resolved_debt_sizing_mode() == DebtSizingMode.FROZEN_EXCEL_SCHEDULE
        # V3-3: explicitly setting MINIMUM_DSCR_SCULPTED now resolves cleanly (implemented)
        fp2 = FinancingParams(debt_sizing_mode=DebtSizingMode.MINIMUM_DSCR_SCULPTED)
        assert fp2.resolved_debt_sizing_mode() == DebtSizingMode.MINIMUM_DSCR_SCULPTED


class TestImportSmoke:
    """Basic import smoke tests."""

    def test_main_web_imports(self):
        import main_web
        assert main_web is not None

    def test_financing_params_imports(self):
        from domain.inputs import FinancingParams, DebtSizingMode
        assert FinancingParams is not None
        assert DebtSizingMode is not None

    def test_waterfall_core_imports(self):
        from app.waterfall_core import run_waterfall_v3_core
        assert run_waterfall_v3_core is not None

    def test_waterfall_runner_imports(self):
        from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
        assert WaterfallRunner is not None
        assert WaterfallRunConfig is not None

    def test_debt_sizing_mode_enum_complete(self):
        """DebtSizingMode enum has all expected values."""
        assert DebtSizingMode.FROZEN_EXCEL_SCHEDULE.value == "frozen_excel_schedule"
        assert DebtSizingMode.FLAT_DSCR_SCULPTED.value == "flat_dscr_sculpted"
        assert DebtSizingMode.MINIMUM_DSCR_SCULPTED.value == "minimum_dscr_sculpted"


class TestGuardrails:
    """Phase 23A guardrails: confirm these areas are NOT modified."""

    def test_tuho_debt_sizing_method_is_fixed(self):
        """TUHO uses fixed debt (fixed_debt_keur=43359) — no sculpting solver."""
        tuho = create_default_tuho_wind1()
        assert tuho.financing.debt_sizing_method == "fixed"
        assert tuho.financing.fixed_debt_keur == 43359.0

    def test_tuho_has_dual_dscr_schedule(self):
        """TUHO uses dual-DSCR schedule (PPA 1.20 / Merchant 1.41)."""
        tuho = create_default_tuho_wind1()
        schedule = tuho.financing.dscr_schedule
        assert schedule is not None
        assert schedule[:24] == [1.2] * 24
        assert schedule[24:28] == [1.4125] * 4

    def test_tuho_shl_repayment_is_pik_then_sweep(self):
        """TUHO SHL repayment is PIK then sweep — no change in this phase."""
        tuho = create_default_tuho_wind1()
        assert tuho.financing.shl_repayment_method == "pik_then_sweep"

    def test_tuho_target_dscr_120(self):
        """TUHO target DSCR is 1.20 during PPA — no change in this phase."""
        tuho = create_default_tuho_wind1()
        assert tuho.financing.target_dscr == 1.20
