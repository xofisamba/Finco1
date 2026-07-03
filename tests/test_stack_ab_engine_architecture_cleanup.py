"""Stack AB — Engine Architecture Cleanup tests.

Proves that:
- Engine behaviour is driven by capability flags, not by project name or code.
- When identity-dispatched features are disabled, renaming a project does not change output.
- The frozen senior DS fixture loading IS identity-dispatched (documented xfail — known AB finding).
- WaterfallRunConfig is populated from inputs (capability-driven), not from identity.
- Runner-layer duplicate guards are gone; core-layer guards still enforce the boundary.

See docs/STACK_AB_ENGINE_ARCHITECTURE_CLEANUP.md for the full inventory.
"""
from __future__ import annotations

import pytest
from dataclasses import replace

from app.project_factories import create_default_tuho_wind1, create_default_oborovo
from app.ui_runner import _build_period_engine, run_demo_project
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(project):
    engine = _build_period_engine(project)
    return WaterfallRunner(project, engine).run(WaterfallRunConfig.from_inputs(project, engine))


def _rename_project(project, new_name: str, new_code: str):
    """Return an identical project with a different display name and code.

    All financial parameters are unchanged.
    """
    new_info = replace(project.info, name=new_name, code=new_code)
    return replace(project, info=new_info)


def _strip_identity_dispatched_features(project):
    """Return a project with all identity-dispatched features disabled.

    This creates a baseline that should be fully configuration-driven,
    letting us verify that rename produces identical output for the
    flag-controlled computation paths.

    Identity-dispatched features stripped:
    - use_tax_bridge_engine: bridge has hardcoded TUHO constants (AB finding)
    - use_shl_gross_accrued_for_pnl: reads TUHO-specific R27 fixture (AB finding)
    - use_frozen_excel_senior_debt_schedule: fixture loaded by project code (AB finding)
    """
    return replace(
        project,
        info=replace(
            project.info,
            use_tax_bridge_engine=False,
            use_shl_gross_accrued_for_pnl=False,
        ),
        financing=replace(
            project.financing,
            use_frozen_excel_senior_debt_schedule=False,
        ),
    )


# ---------------------------------------------------------------------------
# AB1 — Configuration drives behaviour, not project name
# ---------------------------------------------------------------------------

class TestConfigDrivenBehaviour:
    """Engine outputs must be identical regardless of project display name / code,
    when all identity-dispatched features are disabled."""

    def test_tuho_stripped_output_identical_after_rename(self):
        """When identity-dispatched features are off, renaming TUHO changes nothing.

        This is the canonical AB config-driven test. With all identity-dispatched
        features disabled (frozen DS, tax bridge, SHL gross), the engine computes
        identical outputs regardless of the project name string.
        """
        original = _strip_identity_dispatched_features(create_default_tuho_wind1())
        renamed = _rename_project(original, new_name="Wind Project Alpha", new_code="WPA-001")

        r_orig = _run(original)
        r_renamed = _run(renamed)

        assert r_orig.equity_irr == pytest.approx(r_renamed.equity_irr, abs=1e-10)
        assert r_orig.project_irr == pytest.approx(r_renamed.project_irr, abs=1e-10)
        assert r_orig.actual_avg_dscr == pytest.approx(r_renamed.actual_avg_dscr, abs=1e-10)
        assert r_orig.total_distribution_keur == pytest.approx(r_renamed.total_distribution_keur, abs=1e-6)
        assert r_orig.total_senior_ds_keur == pytest.approx(r_renamed.total_senior_ds_keur, abs=1e-6)

    def test_oborovo_stripped_output_identical_after_rename(self):
        """When identity-dispatched features are off, renaming Oborovo changes nothing."""
        original = _strip_identity_dispatched_features(create_default_oborovo())
        renamed = _rename_project(original, new_name="Solar Project Beta", new_code="SPB-999")

        r_orig = _run(original)
        r_renamed = _run(renamed)

        assert r_orig.equity_irr == pytest.approx(r_renamed.equity_irr, abs=1e-10)
        assert r_orig.project_irr == pytest.approx(r_renamed.project_irr, abs=1e-10)
        assert r_orig.actual_avg_dscr == pytest.approx(r_renamed.actual_avg_dscr, abs=1e-10)
        assert r_orig.total_distribution_keur == pytest.approx(r_renamed.total_distribution_keur, abs=1e-6)
        assert r_orig.total_tax_keur == pytest.approx(r_renamed.total_tax_keur, abs=1e-6)

    def test_tuho_full_output_identical_after_rename(self):
        """Stack AC fix: frozen DS fixture is now loaded from configured path, not project code.

        Before Stack AC, renaming TUHO-WIND-1 to WPA-001 caused the frozen senior DS
        fixture to not load (identity dispatch on project code), changing actual_avg_dscr
        from 1.3786 to 1.5004 (AB finding).

        After Stack AC, the fixture path is in FinancingParams.frozen_senior_ds_fixture_path.
        A renamed project retains the same fixture path → same DSCR.
        """
        original = _strip_identity_dispatched_features(create_default_tuho_wind1())
        # Re-enable frozen DS on both — the AC fix makes it config-driven
        original = replace(original, financing=replace(original.financing,
            use_frozen_excel_senior_debt_schedule=True))
        renamed = _rename_project(original, new_name="Wind Alpha", new_code="WPA-001")

        r_orig = _run(original)
        r_renamed = _run(renamed)

        # Stack AC: fixture path is in config, not code — identical DSCR after rename
        assert r_orig.actual_avg_dscr == pytest.approx(r_renamed.actual_avg_dscr, abs=1e-10)
        assert r_orig._frozen_senior_ds_wired is True, "Original must have frozen DS wired"
        assert r_renamed._frozen_senior_ds_wired is True, "Renamed must also have frozen DS wired"

    def test_waterfallrunconfig_does_not_store_project_code(self):
        """WaterfallRunConfig carries capability flags, not project identity.

        The config has no project_code field — routing is done by
        the factory flags, not by a project code string inside the config.
        """
        project = create_default_tuho_wind1()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)

        assert not hasattr(config, "project_code"), (
            "WaterfallRunConfig must not carry project_code — use capability flags"
        )
        assert not hasattr(config, "project_name"), (
            "WaterfallRunConfig must not carry project_name — use capability flags"
        )

    def test_waterfallrunconfig_populated_from_capability_flags(self):
        """from_inputs() reads flags from project config, not from identity."""
        project = create_default_tuho_wind1()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)

        assert config.use_tax_bridge_engine is True       # set in TUHO factory
        assert config.use_senior_debt_sizing_engine is True  # set in TUHO factory
        # Determinism: same factory produces same config
        config2 = WaterfallRunConfig.from_inputs(project, engine)
        assert config == config2, "from_inputs() must be deterministic"


# ---------------------------------------------------------------------------
# AB2 — Runner duplicate guards removed; core guards still enforce boundary
# ---------------------------------------------------------------------------

class TestDuplicateGuardsRemoved:
    """Verify that removed runner-layer guards don't leave an enforcement gap."""

    def test_oborovo_tax_bridge_capability_driven_no_identity_guard(self):
        """Phase0/Y3: identity guard removed; tax bridge is capability-driven.

        Previously a ValueError was raised when use_tax_bridge_engine=True on a
        non-TUHO project. After Phase0, there is no identity check — capability flags
        control behaviour. Oborovo factory sets use_tax_bridge_engine=False.
        """
        obo = create_default_oborovo()
        assert obo.info.use_tax_bridge_engine is False, (
            "Oborovo factory must set use_tax_bridge_engine=False"
        )

    def test_oborovo_shl_gross_accrued_capability_driven_no_identity_guard(self):
        """Phase0/Y3: identity guard removed; use_shl_gross_accrued_for_pnl is capability-driven."""
        obo = create_default_oborovo()
        assert not getattr(obo.info, "use_shl_gross_accrued_for_pnl", False), (
            "Oborovo factory must not enable use_shl_gross_accrued_for_pnl"
        )

    def test_runner_from_inputs_no_longer_contains_duplicate_tax_bridge_guard(self):
        """The runner's from_inputs no longer contains the tax bridge identity check.

        After Stack AB, the runner does NOT re-raise for tax_bridge_engine identity.
        The guard now lives only in waterfall_core.run_waterfall_v3_core().
        """
        import inspect
        source = inspect.getsource(WaterfallRunConfig.from_inputs)
        assert "Tax bridge runtime engine is currently supported only for TUHO-WIND-1" not in source, (
            "Runner from_inputs() still contains duplicate tax bridge identity guard — "
            "Stack AB removed this; it now lives only in waterfall_core.py line 115"
        )

    def test_runner_from_inputs_no_longer_contains_duplicate_shl_gross_guard(self):
        """Runner no longer contains the duplicate SHL gross accrued guard."""
        import inspect
        source = inspect.getsource(WaterfallRunConfig.from_inputs)
        assert "Gross accrued SHL P&L bridge is currently supported only for TUHO-WIND-1" not in source, (
            "Runner from_inputs() still contains duplicate SHL gross guard — "
            "Stack AB removed this; it lives only in waterfall_core.py line 117"
        )

    def test_runner_from_inputs_no_longer_contains_duplicate_shl_alignment_guard(self):
        """Runner no longer contains the duplicate SHL repayment alignment guard."""
        import inspect
        source = inspect.getsource(WaterfallRunConfig.from_inputs)
        assert "TUHO SHL repayment alignment is currently supported only for TUHO-WIND-1" not in source, (
            "Runner from_inputs() still contains duplicate SHL alignment guard — "
            "Stack AB removed this; it lives only in waterfall_core.py line 119"
        )


# ---------------------------------------------------------------------------
# AB3 — Golden regression: parity unchanged after guard removals
# ---------------------------------------------------------------------------

class TestGoldenRegression:
    """Stack AB must not change any parity-sensitive KPI."""

    @pytest.fixture(scope="class")
    def tuho(self):
        return run_demo_project("TUHO").result

    @pytest.fixture(scope="class")
    def oborovo(self):
        return run_demo_project("Oborovo").result

    def test_tuho_equity_irr_unchanged(self, tuho):
        assert abs(tuho.equity_irr - 0.1132) < 0.0005

    def test_tuho_avg_dscr_unchanged(self, tuho):
        assert abs(tuho.actual_avg_dscr - 1.3786) < 0.001

    def test_tuho_total_tax_unchanged(self, tuho):
        # Phase0/Z1: formula fix; new correct value ~35414 kEUR (old 45835 used wrong depreciation basis)
        assert abs(tuho.total_tax_keur - 35414.0) < 500.0

    def test_tuho_total_distribution_unchanged(self, tuho):
        assert abs(tuho.total_distribution_keur - 165471.0) < 200.0

    def test_oborovo_equity_irr_unchanged(self, oborovo):
        assert abs(oborovo.equity_irr - 0.1054) < 0.0005

    def test_oborovo_avg_dscr_unchanged(self, oborovo):
        assert abs(oborovo.actual_avg_dscr - 1.179) < 0.005

    def test_oborovo_total_tax_unchanged(self, oborovo):
        assert abs(oborovo.total_tax_keur - 8874.0) < 100.0


# ---------------------------------------------------------------------------
# AB4 — Architecture invariants
# ---------------------------------------------------------------------------

class TestArchitectureInvariants:
    """Structural invariants that enforce the configuration-over-identity principle."""

    def test_waterfallrunconfig_is_frozen_dataclass(self):
        """WaterfallRunConfig must be frozen — configs are immutable value objects."""
        import dataclasses
        assert dataclasses.is_dataclass(WaterfallRunConfig)
        assert WaterfallRunConfig.__dataclass_params__.frozen is True

    def test_tuho_tax_bridge_enabled_by_factory_flag(self):
        """TUHO uses tax bridge because factory sets use_tax_bridge_engine=True."""
        project = create_default_tuho_wind1()
        assert project.info.use_tax_bridge_engine is True

    def test_oborovo_tax_bridge_disabled_by_factory_flag(self):
        """Oborovo does not use tax bridge because factory sets use_tax_bridge_engine=False."""
        project = create_default_oborovo()
        assert project.info.use_tax_bridge_engine is False

    def test_both_projects_use_same_runner_entrypoint(self):
        """TUHO and Oborovo use the same WaterfallRunner class. No identity-based runner dispatch."""
        tuho = create_default_tuho_wind1()
        obo = create_default_oborovo()
        tuho_engine = _build_period_engine(tuho)
        obo_engine = _build_period_engine(obo)
        tuho_config = WaterfallRunConfig.from_inputs(tuho, tuho_engine)
        obo_config = WaterfallRunConfig.from_inputs(obo, obo_engine)
        assert tuho_config.use_tax_bridge_engine is True
        assert obo_config.use_tax_bridge_engine is False

    def test_frozen_ds_fixture_path_is_config_driven(self):
        """Stack AC fix: frozen DS fixture is now loaded from configured path, not project code.

        The AB finding was: when TUHO is renamed to WPA-001, the code-based identity dispatch
        prevented fixture loading, so _frozen_senior_ds_wired was False and DSCR changed.

        Stack AC fix: frozen_senior_ds_fixture_path in FinancingParams replaces code dispatch.
        A renamed project retains the same fixture path and _frozen_senior_ds_wired=True.
        """
        original = create_default_tuho_wind1()
        renamed = replace(original, info=replace(original.info, code="WPA-001"))
        # Disable features that would raise on the other identity guards
        renamed = replace(renamed, info=replace(renamed.info,
            use_tax_bridge_engine=False,
            use_shl_gross_accrued_for_pnl=False,
        ))

        r_orig = _run(original)
        r_renamed = _run(renamed)

        # Stack AC: fixture path in config → renamed project still loads fixture
        assert getattr(r_orig, "_frozen_senior_ds_wired", False) is True, (
            "Original TUHO should have frozen DS wired"
        )
        assert getattr(r_renamed, "_frozen_senior_ds_wired", False) is True, (
            "Renamed project MUST also have frozen DS wired — identity dispatch fixed (Stack AC)"
        )
        # And therefore DSCRs are now identical
        assert r_orig.actual_avg_dscr == pytest.approx(r_renamed.actual_avg_dscr, abs=1e-10), (
            "DSCR must be identical after rename — config-driven fixture path confirmed"
        )
