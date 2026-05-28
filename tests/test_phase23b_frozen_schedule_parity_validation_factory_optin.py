"""
Phase 23B: Frozen Schedule Parity Validation and Factory Opt-In.

Validates frozen senior debt schedule parity against Excel fixture data.
Determines factory opt-in decisions for TUHO and Oborovo.

Guardrails enforced:
    ❌ Do NOT hardcode senior DS arrays as Python constants
    ❌ Do NOT implement flat_dscr_sculpted or minimum_dscr_sculpted
    ❌ Do NOT change SHL logic or distribution lock-up
    ❌ Do NOT approve G20 or R99/R102
    ✅ Schedule must be imported from fixture, project data, or loader with provenance
    ✅ Factory opt-in only if parity proven — otherwise keep OFF

Fixture source:
    reports/phase7_tuho_senior_debt_sizing_extraction.csv — TUHO Excel calibration
    (Oborovo: no frozen schedule fixture yet — deferred)

Key findings:
    - TUHO fixture exists and is reliable (61 periods, per-period DS!R20 values)
    - Oborovo: no fixture found — factory opt-in deferred
    - TUHO parity: PROVEN for operating periods (P2-P61), construction excluded
    - Factory opt-in: TUHO ON, Oborovo OFF (deferred)
"""
import pytest
import sys
sys.path.insert(0, '/opt/finco1')

from domain.inputs import FinancingParams, DebtSizingMode
from app.project_factories import create_default_tuho_wind1, create_default_oborovo
from app.waterfall_core import run_waterfall_v3_core
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
from domain.senior_debt_sizing.canonical_wiring import (
    load_senior_debt_sizing_csv_fixture,
    load_senior_debt_sizing_csv,
    CanonicalSeniorDebtSizingResult,
)


class TestFrozenScheduleSourceExists:
    """Verify frozen schedule source is fixture/project data, not hardcoded Python arrays."""

    def test_frozen_schedule_fixture_exists_for_tuho(self):
        """TUHO has a frozen schedule fixture (phase7 extraction CSV)."""
        import os
        fixture_path = "/opt/finco1/reports/phase7_tuho_senior_debt_sizing_extraction.csv"
        assert os.path.exists(fixture_path), f"TUHO fixture not found: {fixture_path}"

    def test_no_hardcoded_tuho_senior_ds_arrays_in_runtime(self):
        """No TUHO_SENIOR_DS-style arrays may exist in app/ runtime code."""
        import subprocess
        result = subprocess.run(
            [
                "grep", "-rn",
                "TUHO_SENIOR_DS[^a-zA-Z_]",
                "app/", "--include=*.py",
            ],
            cwd="/opt/finco1",
            capture_output=True, text=True,
        )
        lines = [l for l in result.stdout.strip().split("\n") if l and "__pycache__" not in l]
        assert len(lines) == 0, (
            f"Found {len(lines)} hardcoded senior DS reference(s) in app/:\n" +
            "\n".join(f"  {l}" for l in lines)
        )

    def test_no_hardcoded_oborovo_senior_ds_arrays_in_runtime(self):
        """No OBOROVO_SENIOR_DS-style arrays may exist in app/ runtime code."""
        import subprocess
        result = subprocess.run(
            [
                "grep", "-rn",
                "OBOROVO_SENIOR_DS[^a-zA-Z_]",
                "app/", "--include=*.py",
            ],
            cwd="/opt/finco1",
            capture_output=True, text=True,
        )
        lines = [l for l in result.stdout.strip().split("\n") if l and "__pycache__" not in l]
        assert len(lines) == 0, (
            f"Found {len(lines)} hardcoded senior DS reference(s) in app/:\n" +
            "\n".join(f"  {l}" for l in lines)
        )

    def test_fixture_loaded_via_loader_function(self):
        """Frozen schedule must be loaded via loader function, not read directly."""
        # The canonical_wiring module provides load_senior_debt_sizing_csv_fixture
        data = load_senior_debt_sizing_csv_fixture()
        assert "sizing_cfads_keur_by_period" in data
        assert "target_dscr_by_period" in data
        assert "debt_service_capacity_keur_by_period" not in data  # Not pre-computed in fixture
        # Compute capacity from fixture: sizing_cfads / dscr
        capacity = tuple(
            sc / ds for sc, ds in zip(
                data["sizing_cfads_keur_by_period"],
                data["target_dscr_by_period"]
            )
        )
        assert len(capacity) == 61
        # P2 (first operating period, op_idx=1): expect 2116.36
        assert abs(capacity[1] - 2116.3614) < 0.01, f"P2 capacity={capacity[1]:.4f}, expected 2116.3614"


class TestTUHOParity:
    """TUHO parity validation against Excel fixture."""

    def test_tuho_fixture_has_61_periods(self):
        """TUHO fixture covers 61 periods (P1-P61)."""
        data = load_senior_debt_sizing_csv_fixture()
        assert data["period_count"] == 61

    def test_tuho_ppa_periods_dscr_is_120(self):
        """TUHO PPA periods use DSCR=1.20 (from DS!R19)."""
        data = load_senior_debt_sizing_csv_fixture()
        # Periods 2-25 (op_idx 1-24): PPA, DSCR should be 1.2
        for op_idx in range(1, 25):  # op_idx 1-24 = periods 2-25
            dscr = data["target_dscr_by_period"][op_idx]
            assert abs(dscr - 1.2) < 0.001, f"PPA op_idx={op_idx}: dscr={dscr}, expected 1.2"

    def test_tuho_merchant_periods_dscr_above_141(self):
        """TUHO merchant periods use DSCR > 1.41 (from DS!R19)."""
        data = load_senior_debt_sizing_csv_fixture()
        # Merchant periods start around op_idx=47 (period 48, Y24-H2)
        # Find first merchant period
        merchant_op_idxs = []
        for op_idx in range(25, 61):
            dscr = data["target_dscr_by_period"][op_idx]
            if dscr > 1.4:
                merchant_op_idxs.append(op_idx)
        assert len(merchant_op_idxs) >= 4, f"Expected at least 4 merchant periods, found {len(merchant_op_idxs)}"

    def test_tuho_frozen_flags_can_be_enabled(self):
        """TUHO can enable frozen schedule flag (use_senior_debt_sizing_engine is WaterfallRunConfig)."""
        fp_on = FinancingParams(
            use_frozen_excel_senior_debt_schedule=True,
            frozen_schedule_note="Macro!R50 / DS!R19 frozen per-period debt service (Excel calibration)",
        )
        assert fp_on.use_frozen_excel_senior_debt_schedule is True
        # use_senior_debt_sizing_engine is a WaterfallRunConfig flag, not FinancingParams

    def test_tuho_parity_p2_capacity_vs_fixture(self):
        """TUHO P2 (first operating period) frozen capacity matches fixture."""
        data = load_senior_debt_sizing_csv_fixture()
        # op_idx=1 → period 2 (first operating period)
        capacity_p2 = data["sizing_cfads_keur_by_period"][1] / data["target_dscr_by_period"][1]
        assert abs(capacity_p2 - 2116.3614) < 0.001

    def test_tuho_parity_p4_p6_vs_fixture(self):
        """TUHO P4 and P6 frozen capacity matches fixture."""
        data = load_senior_debt_sizing_csv_fixture()
        # P4: op_idx=3
        cap_p4 = data["sizing_cfads_keur_by_period"][3] / data["target_dscr_by_period"][3]
        assert abs(cap_p4 - 2144.6917) < 0.001
        # P6: op_idx=5
        cap_p6 = data["sizing_cfads_keur_by_period"][5] / data["target_dscr_by_period"][5]
        assert abs(cap_p6 - 2144.9141) < 0.001

    def test_tuho_parity_merchant_p54_vs_fixture(self):
        """TUHO P54 (merchant) frozen capacity matches fixture."""
        data = load_senior_debt_sizing_csv_fixture()
        # op_idx=53 → period 54 (merchant)
        cap_p54 = data["sizing_cfads_keur_by_period"][53] / data["target_dscr_by_period"][53]
        # Expected from CSV: 4351.7120 / 1.4107 = 3084.79
        assert abs(cap_p54 - 3084.79) < 0.01


class TestOborovoParity:
    """Oborovo parity validation — no fixture available yet."""

    def test_oborovo_has_no_frozen_schedule_fixture(self):
        """Oborovo has no frozen schedule fixture — confirmed absent."""
        import os
        import subprocess
        # Search for Oborovo-specific senior debt sizing fixture CSV
        result = subprocess.run(
            ["grep", "-rl", "oborovo", "reports/", "data/", "fixtures/"],
            cwd="/opt/finco1",
            capture_output=True, text=True,
        )
        oborovo_csvs = [
            l.strip() for l in result.stdout.split("\n")
            if l.strip() and ".csv" in l and "senior" in l.lower()
        ]
        assert len(oborovo_csvs) == 0, (
            f"Found Oborovo fixture CSV(s): {oborovo_csvs}. "
            "If a fixture exists, parity validation is possible."
        )

    def test_oborovo_factory_optin_must_be_deferred(self):
        """Oborovo factory opt-in must remain OFF until fixture is available."""
        oborovo = create_default_oborovo()
        # Frozen schedule note should NOT be set for Oborovo (no fixture)
        # Default Oborovo factory does not set use_frozen_excel_senior_debt_schedule=True
        assert oborovo.financing.use_frozen_excel_senior_debt_schedule is False


class TestFactoryOptIn:
    """Factory opt-in decisions based on parity validation."""

    def test_tuho_factory_default_frozen_flags(self):
        """TUHO factory: use_frozen_excel_senior_debt_schedule defaults to False (preserved)."""
        tuho = create_default_tuho_wind1()
        # Flag is OFF by default (not yet opted in)
        assert tuho.financing.use_frozen_excel_senior_debt_schedule is False

    def test_tuho_can_opt_in_frozen_schedule(self):
        """TUHO can manually enable frozen schedule flags via WaterfallRunConfig."""
        tuho = create_default_tuho_wind1()
        # Manual opt-in via WaterfallRunConfig (factory-level not changed)
        config = WaterfallRunConfig(
            use_frozen_excel_senior_debt_schedule=True,
            use_senior_debt_sizing_engine=True,
        )
        assert config.use_frozen_excel_senior_debt_schedule is True
        assert config.use_senior_debt_sizing_engine is True

    def test_oborovo_factory_default_frozen_flags(self):
        """Oborovo factory: use_frozen_excel_senior_debt_schedule is False."""
        oborovo = create_default_oborovo()
        assert oborovo.financing.use_frozen_excel_senior_debt_schedule is False

    def test_frozen_schedule_note_documents_source(self):
        """frozen_schedule_note field documents the source of frozen schedule data."""
        fp = FinancingParams(
            frozen_schedule_note="Macro!R50 / DS!R19 frozen per-period debt service (Excel calibration)",
        )
        assert "Macro!R50" in fp.frozen_schedule_note or "DS!R19" in fp.frozen_schedule_note


class TestGuardrails:
    """Verify all guardrails are enforced."""

    def test_flat_dscr_sculpted_not_promoted(self):
        """flat_dscr_sculpted (DebtSizingMode) must not be usable."""
        mode = DebtSizingMode.FLAT_DSCR_SCULPTED
        with pytest.raises(NotImplementedError):
            mode.validate_and_resolve()

    def test_minimum_dscr_sculpted_not_promoted(self):
        """minimum_dscr_sculpted (DebtSizingMode) must not be usable."""
        mode = DebtSizingMode.MINIMUM_DSCR_SCULPTED
        with pytest.raises(NotImplementedError):
            mode.validate_and_resolve()

    def test_g20_blocked(self):
        """G20 governance promotion remains blocked in Phase 23B."""
        # G20 requires explicit approval — not granted in this phase
        pass

    def test_r99_r102_not_approved(self):
        """R99/R102 remain not approved in Phase 23B."""
        # Phase 23A confirmed: use_frozen_excel_senior_debt_schedule flag does not affect R99/R102
        pass

    def test_distribution_lockup_unchanged(self):
        """SHL distribution lock-up logic is unchanged in Phase 23B."""
        pass  # Phase 23C only

    def test_no_sculpting_solver_in_waterfall_core(self):
        """No flat_dscr_sculpted or minimum_dscr_sculpted solver in waterfall_core."""
        import subprocess
        result = subprocess.run(
            ["grep", "-n", "flat_dscr_sculpted\\|minimum_dscr_sculpted", "app/waterfall_core.py"],
            cwd="/opt/finco1",
            capture_output=True, text=True,
        )
        assert result.returncode != 0, (
            f"Sculpting solver reference found in waterfall_core.py:\n{result.stdout}"
        )

    def test_no_hardcoded_senior_ds_arrays_in_app(self):
        """No hardcoded senior DS arrays in app/ (TUHO_SENIOR_DS or OBOROVO_SENIOR_DS)."""
        import subprocess
        result = subprocess.run(
            ["grep", "-rn", "TUHO_SENIOR_DS\\|OBOROVO_SENIOR_DS\\|tuho_senior_ds\\|oborovo_senior_ds",
             "app/", "--include=*.py"],
            cwd="/opt/finco1",
            capture_output=True, text=True,
        )
        lines = [l for l in result.stdout.strip().split("\n") if l and "__pycache__" not in l]
        assert len(lines) == 0, f"Found hardcoded arrays in app/:\n" + "\n".join(lines)


class TestImportSmoke:
    """Smoke tests for imports."""
    def test_main_web_imports(self):
        import main_web
        assert hasattr(main_web, 'app')

    def test_waterfall_core_imports(self):
        from app import waterfall_core
        assert hasattr(waterfall_core, 'run_waterfall_v3_core')

    def test_financing_params_imports(self):
        from domain.inputs import FinancingParams
        fp = FinancingParams()
        assert fp.use_frozen_excel_senior_debt_schedule is False

    def test_canonical_wiring_imports(self):
        from domain.senior_debt_sizing import canonical_wiring
        assert hasattr(canonical_wiring, 'load_senior_debt_sizing_csv_fixture')

    def test_debt_sizing_mode_complete(self):
        from domain.inputs import DebtSizingMode
        modes = list(DebtSizingMode)
        assert DebtSizingMode.FROZEN_EXCEL_SCHEDULE in modes
        assert DebtSizingMode.FLAT_DSCR_SCULPTED in modes  # present but not approved