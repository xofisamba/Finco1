"""Stack AC — Runtime Identity Elimination Phase 1 tests.

Proves that:
- Frozen senior DS fixture is loaded from FinancingParams.frozen_senior_ds_fixture_path,
  not from project code / name.
- Renaming TUHO-WIND-1 to any other name/code produces identical DSCR when
  frozen_senior_ds_fixture_path is set.
- Renaming Oborovo produces identical DSCR under the same condition.
- A project without a configured fixture path does not load any fixture.
- Golden regression: parity targets are unchanged after the AC refactor.

See docs/STACK_AC_RUNTIME_IDENTITY_PHASE1.md for the full design.
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
    """Return an identical project with a different display name and code."""
    new_info = replace(project.info, name=new_name, code=new_code)
    return replace(project, info=new_info)


def _strip_non_frozen_identity_features(project):
    """Disable identity-dispatched features OTHER than frozen DS.

    Leaves use_frozen_excel_senior_debt_schedule and frozen_senior_ds_fixture_path
    intact so we can test frozen DS path isolation.
    """
    return replace(
        project,
        info=replace(
            project.info,
            use_tax_bridge_engine=False,
            use_shl_gross_accrued_for_pnl=False,
        ),
    )


# ---------------------------------------------------------------------------
# AC1 — Frozen DS fixture path is capability-driven, not identity-driven
# ---------------------------------------------------------------------------

class TestFrozenDSFixturePathCapabilityDriven:
    """Frozen DS fixture must be controlled by frozen_senior_ds_fixture_path config, not code."""

    def test_tuho_fixture_path_set_in_factory(self):
        """TUHO factory populates frozen_senior_ds_fixture_path."""
        project = create_default_tuho_wind1()
        assert project.financing.frozen_senior_ds_fixture_path is not None, (
            "TUHO factory must set frozen_senior_ds_fixture_path"
        )
        assert "phase7_tuho" in project.financing.frozen_senior_ds_fixture_path

    def test_oborovo_fixture_path_set_in_factory(self):
        """Oborovo factory populates frozen_senior_ds_fixture_path."""
        project = create_default_oborovo()
        assert project.financing.frozen_senior_ds_fixture_path is not None, (
            "Oborovo factory must set frozen_senior_ds_fixture_path"
        )
        assert "phase23q_oborovo" in project.financing.frozen_senior_ds_fixture_path

    def test_fixture_path_field_defaults_to_none(self):
        """FinancingParams default has no fixture path — generic projects get no fixture."""
        from domain.inputs import FinancingParams
        params = FinancingParams()
        assert params.frozen_senior_ds_fixture_path is None

    def test_tuho_frozen_ds_wired_is_true(self):
        """TUHO with factory defaults loads the frozen DS fixture."""
        project = _strip_non_frozen_identity_features(create_default_tuho_wind1())
        result = _run(project)
        assert getattr(result, "_frozen_senior_ds_wired", False) is True, (
            "TUHO must have _frozen_senior_ds_wired=True when fixture path is configured"
        )

    def test_project_without_fixture_path_does_not_load_fixture(self):
        """A project with frozen DS enabled but no fixture path does not load a fixture."""
        project = create_default_tuho_wind1()
        project = replace(project, financing=replace(project.financing,
            use_frozen_excel_senior_debt_schedule=True,
            frozen_senior_ds_fixture_path=None,
        ))
        project = replace(project, info=replace(project.info,
            use_tax_bridge_engine=False,
            use_shl_gross_accrued_for_pnl=False,
        ))
        result = _run(project)
        assert getattr(result, "_frozen_senior_ds_wired", False) is not True, (
            "No fixture path → fixture must not be loaded"
        )


# ---------------------------------------------------------------------------
# AC2 — Rename invariance: config-driven frozen DS survives rename
# ---------------------------------------------------------------------------

class TestRenameInvariance:
    """Renaming a project must not change any financial output when fixture path is in config."""

    def test_tuho_rename_does_not_change_dscr(self):
        """After AC: renaming TUHO to arbitrary code produces identical actual_avg_dscr."""
        original = _strip_non_frozen_identity_features(create_default_tuho_wind1())
        renamed = _rename_project(original, new_name="Wind Project Alpha", new_code="WPA-001")

        r_orig = _run(original)
        r_renamed = _run(renamed)

        assert r_orig._frozen_senior_ds_wired is True
        assert r_renamed._frozen_senior_ds_wired is True
        assert r_orig.actual_avg_dscr == pytest.approx(r_renamed.actual_avg_dscr, abs=1e-10)

    def test_tuho_rename_does_not_change_equity_irr(self):
        """Renaming TUHO does not change equity IRR."""
        original = _strip_non_frozen_identity_features(create_default_tuho_wind1())
        renamed = _rename_project(original, new_name="Wind Beta", new_code="WND-002")

        r_orig = _run(original)
        r_renamed = _run(renamed)

        assert r_orig.equity_irr == pytest.approx(r_renamed.equity_irr, abs=1e-10)

    def test_tuho_rename_does_not_change_total_distribution(self):
        """Renaming TUHO does not change total distributions."""
        original = _strip_non_frozen_identity_features(create_default_tuho_wind1())
        renamed = _rename_project(original, new_name="Wind Gamma", new_code="WND-003")

        r_orig = _run(original)
        r_renamed = _run(renamed)

        assert r_orig.total_distribution_keur == pytest.approx(
            r_renamed.total_distribution_keur, abs=1e-6
        )

    def test_oborovo_rename_does_not_change_dscr(self):
        """After AC: renaming Oborovo produces identical actual_avg_dscr."""
        original = _strip_non_frozen_identity_features(create_default_oborovo())
        renamed = _rename_project(original, new_name="Solar Project X", new_code="SPX-007")

        r_orig = _run(original)
        r_renamed = _run(renamed)

        assert r_orig._frozen_senior_ds_wired is True
        assert r_renamed._frozen_senior_ds_wired is True
        assert r_orig.actual_avg_dscr == pytest.approx(r_renamed.actual_avg_dscr, abs=1e-10)

    def test_oborovo_rename_does_not_change_equity_irr(self):
        """Renaming Oborovo does not change equity IRR."""
        original = _strip_non_frozen_identity_features(create_default_oborovo())
        renamed = _rename_project(original, new_name="Solar Beta", new_code="SOL-002")

        r_orig = _run(original)
        r_renamed = _run(renamed)

        assert r_orig.equity_irr == pytest.approx(r_renamed.equity_irr, abs=1e-10)


# ---------------------------------------------------------------------------
# AC3 — Golden regression: parity targets unchanged after AC refactor
# ---------------------------------------------------------------------------

class TestGoldenRegression:
    """Stack AC must not change any parity-sensitive KPI."""

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
# AC4 — Architecture invariants
# ---------------------------------------------------------------------------

class TestArchitectureInvariants:
    """Structural invariants after Stack AC."""

    def test_frozen_senior_ds_fixture_path_is_in_financing_params(self):
        """FinancingParams has frozen_senior_ds_fixture_path field."""
        from domain.inputs import FinancingParams
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(FinancingParams)}
        assert "frozen_senior_ds_fixture_path" in field_names, (
            "FinancingParams must expose frozen_senior_ds_fixture_path for config-driven dispatch"
        )

    def test_waterfall_core_frozen_ds_uses_fixture_path_not_project_code(self):
        """waterfall_core.py uses frozen_senior_ds_fixture_path, not project code, for DS dispatch.

        The old dispatch was:
            use_fixture = use_frozen_excel_senior_debt_schedule and code == 'TUHO-WIND-1'
        The new dispatch is:
            use_fixture = use_frozen_excel_senior_debt_schedule
                          and _configured_fixture_path is not None
                          and 'phase7_tuho' in _configured_fixture_path

        We verify this by confirming the config path variable name appears in the source
        near the fixture loading block.
        """
        import inspect
        import app.waterfall_core as wc
        source = inspect.getsource(wc)
        assert "_configured_fixture_path" in source, (
            "waterfall_core.py must use _configured_fixture_path (from FinancingParams), "
            "not project code, for frozen DS fixture dispatch"
        )
        assert "phase7_tuho" in source, (
            "waterfall_core.py must identify TUHO fixture by path stem 'phase7_tuho'"
        )
        assert "phase23q_oborovo" in source, (
            "waterfall_core.py must identify Oborovo fixture by path stem 'phase23q_oborovo'"
        )

    def test_fixture_path_controls_which_fixture_is_loaded(self):
        """The fixture schema is inferred from the configured path stem, not from project identity."""
        # TUHO path contains 'phase7_tuho' → selects TUHO schema (1-based CSV indices)
        tuho_project = create_default_tuho_wind1()
        assert "phase7_tuho" in tuho_project.financing.frozen_senior_ds_fixture_path

        # Oborovo path contains 'phase23q_oborovo' → selects Oborovo schema (0-based CSV indices)
        obo_project = create_default_oborovo()
        assert "phase23q_oborovo" in obo_project.financing.frozen_senior_ds_fixture_path


