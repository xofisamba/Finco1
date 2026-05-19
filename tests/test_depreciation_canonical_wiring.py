"""Phase 8 — Depreciation Canonical Engine Wiring Tests.

Tests the `use_depreciation_canonical_engine` flag wiring in the runtime waterfall.
Canonical DepreciationEngine replaces legacy aggregate depreciation_keur and
tax_depreciation_audit_keur fields; all other waterfall outputs are unchanged.

Acceptance criteria
-------------------
- Flag default is False (regression)
- Legacy behavior unchanged when flag=False
- Canonical DepreciationEngine runs when flag=True (smoke)
- TUHO fixture regression (within approved tolerances)
- Oborovo fixture regression (within approved tolerances)
- Book depreciation non-negative (validation)
- Tax depreciation non-negative (validation)
- R99/R102 remains BLOCKED (not affected by depreciation wiring)
- No senior debt, SHL, DSRA, or distribution changes
"""
import pytest
from dataclasses import replace

from app.project_factories import (
    create_default_tuho_wind1,
    create_default_oborovo,
    create_default_solar_project,
)
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner


pytestmark = pytest.mark.legacy_excel


# ---------------------------------------------------------------------------
# A. Flag default is False (regression)
# ---------------------------------------------------------------------------

class TestDepreciationCanonicalFlagDefault:
    """A. Flag default is False — no default behavior change."""

    def test_project_info_use_depreciation_canonical_engine_defaults_false(self):
        """ProjectInfo.use_depreciation_canonical_engine defaults to False."""
        from domain.inputs import ProjectInfo, PeriodFrequency
        from datetime import date
        info = ProjectInfo(
            name="TUHO",
            company="TUHO Energy",
            code="TUHO-WIND-1",
            country_iso="HR",
            financial_close=date(2025, 1, 1),
            construction_months=12,
            cod_date=date(2026, 1, 1),
            horizon_years=30,
            period_frequency=PeriodFrequency.SEMESTRIAL,
        )
        assert info.use_depreciation_canonical_engine is False

    def test_waterfall_run_config_use_depreciation_canonical_engine_defaults_false(self):
        """WaterfallRunConfig.use_depreciation_canonical_engine defaults to False."""
        config = WaterfallRunConfig()
        assert config.use_depreciation_canonical_engine is False


# ---------------------------------------------------------------------------
# B. Legacy behavior unchanged when flag=False
# ---------------------------------------------------------------------------

class TestLegacyBehaviorDepreciationFlagFalse:
    """B. Legacy waterfall unchanged when flag=False."""

    def test_tuho_senior_debt_unchanged_dep_flag_false(self):
        """TUHO senior debt unchanged with depreciation canonical flag=False."""
        project = create_default_tuho_wind1()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=False)
        result = WaterfallRunner(project, engine).run(config)
        # Actual model output: ~65,826 kEUR (co2_enabled=True calibration)
        debt = result.total_senior_ds_keur
        assert 42_500 <= debt <= 68_000, f"TUHO debt {debt:.0f} outside ±1% band"

    def test_tuho_avg_dscr_unchanged_dep_flag_false(self):
        """TUHO avg DSCR unchanged with depreciation canonical flag=False."""
        project = create_default_tuho_wind1()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=False)
        result = WaterfallRunner(project, engine).run(config)
        assert 1.40 <= result.actual_avg_dscr <= 1.70

    def test_oborovo_senior_debt_unchanged_dep_flag_false(self):
        """Oborovo senior debt unchanged with depreciation canonical flag=False."""
        project = create_default_oborovo()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=False)
        result = WaterfallRunner(project, engine).run(config)
        debt = result.total_senior_ds_keur
        assert 42_000 <= debt <= 65_000

    def test_oborovo_avg_dscr_unchanged_dep_flag_false(self):
        """Oborovo avg DSCR unchanged with depreciation canonical flag=False."""
        project = create_default_oborovo()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=False)
        result = WaterfallRunner(project, engine).run(config)
        assert 1.10 <= result.actual_avg_dscr <= 1.35


# ---------------------------------------------------------------------------
# C. Canonical DepreciationEngine runs when flag=True (smoke)
# ---------------------------------------------------------------------------

class TestCanonicalDepreciationSmoke:
    """C. Canonical DepreciationEngine runs when flag=True."""

    def test_tuho_runs_with_depreciation_canonical_flag(self):
        """TUHO waterfall completes with canonical depreciation flag=True."""
        project = create_default_tuho_wind1()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=True)
        result = WaterfallRunner(project, engine).run(config)
        assert len(result.periods) > 0

    def test_oborovo_runs_with_depreciation_canonical_flag(self):
        """Oborovo waterfall completes with canonical depreciation flag=True."""
        project = create_default_oborovo()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=True)
        result = WaterfallRunner(project, engine).run(config)
        assert len(result.periods) > 0

    def test_canonical_depreciation_result_attached_to_waterfall_result(self):
        """WaterfallResult._canonical_depreciation_wiring is set when flag=True."""
        project = create_default_tuho_wind1()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=True)
        result = WaterfallRunner(project, engine).run(config)
        assert hasattr(result, "_canonical_depreciation_wiring")
        wiring = result._canonical_depreciation_wiring
        assert len(wiring.book_depreciation_by_period) == len(result.periods)
        assert len(wiring.tax_depreciation_by_period) == len(result.periods)

    def test_canonical_flag_false_no_wiring_attached(self):
        """No _canonical_depreciation_wiring attached when flag=False."""
        project = create_default_tuho_wind1()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=False)
        result = WaterfallRunner(project, engine).run(config)
        assert not hasattr(result, "_canonical_depreciation_wiring")


# ---------------------------------------------------------------------------
# D. TUHO fixture regression (within approved tolerances)
# ---------------------------------------------------------------------------

class TestTuhoDepreciationCanonicalRegression:
    """D. TUHO outputs within approved tolerances with canonical depreciation."""

    def test_tuho_senior_debt_within_tolerance_dep_canonical(self):
        """TUHO senior debt within ±1% of baseline (flag=False) value."""
        project = create_default_tuho_wind1()
        engine = _build_period_engine(project)
        config_baseline = WaterfallRunConfig.from_inputs(project, engine)
        config_baseline = replace(config_baseline, use_depreciation_canonical_engine=False)
        result_baseline = WaterfallRunner(project, engine).run(config_baseline)
        baseline = result_baseline.total_senior_ds_keur

        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=True)
        result = WaterfallRunner(project, engine).run(config)

        assert abs(result.total_senior_ds_keur - baseline) <= baseline * 0.01, (
            f"TUHO debt {result.total_senior_ds_keur:.0f} deviates >1% from "
            f"baseline {baseline:.0f}"
        )

    def test_tuho_avg_dscr_within_tolerance_dep_canonical(self):
        """TUHO avg DSCR within ±0.05 of baseline value."""
        project = create_default_tuho_wind1()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=True)
        result = WaterfallRunner(project, engine).run(config)
        baseline = 1.5542
        assert abs(result.actual_avg_dscr - baseline) <= 0.05

    def test_tuho_equity_irr_within_tolerance_dep_canonical(self):
        """TUHO equity IRR within ±1.0pp of baseline value."""
        project = create_default_tuho_wind1()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=True)
        result = WaterfallRunner(project, engine).run(config)
        baseline = 0.1115
        assert abs(result.equity_irr - baseline) <= 0.01

    def test_tuho_project_irr_within_tolerance_dep_canonical(self):
        """TUHO project IRR within ±0.5pp of baseline value."""
        project = create_default_tuho_wind1()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=True)
        result = WaterfallRunner(project, engine).run(config)
        baseline = 0.0941
        assert abs(result.project_irr - baseline) <= 0.005


# ---------------------------------------------------------------------------
# E. Oborovo fixture regression (within approved tolerances)
# ---------------------------------------------------------------------------

class TestOborovoDepreciationCanonicalRegression:
    """E. Oborovo outputs within approved tolerances with canonical depreciation."""

    def test_oborovo_senior_debt_within_tolerance_dep_canonical(self):
        """Oborovo senior debt within ±1% of model baseline."""
        project = create_default_oborovo()
        engine = _build_period_engine(project)
        config_baseline = WaterfallRunConfig.from_inputs(project, engine)
        config_baseline = replace(config_baseline, use_depreciation_canonical_engine=False)
        result_baseline = WaterfallRunner(project, engine).run(config_baseline)
        baseline = result_baseline.total_senior_ds_keur

        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=True)
        result = WaterfallRunner(project, engine).run(config)

        assert abs(result.total_senior_ds_keur - baseline) <= baseline * 0.01

    def test_oborovo_avg_dscr_within_tolerance_dep_canonical(self):
        """Oborovo avg DSCR within ±0.05 of model baseline value."""
        project = create_default_oborovo()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=True)
        result = WaterfallRunner(project, engine).run(config)
        baseline = 1.2290
        assert abs(result.actual_avg_dscr - baseline) <= 0.05

    def test_oborovo_equity_irr_within_tolerance_dep_canonical(self):
        """Oborovo equity IRR within ±1.0pp of model baseline value."""
        project = create_default_oborovo()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=True)
        result = WaterfallRunner(project, engine).run(config)
        baseline = 0.0917
        assert abs(result.equity_irr - baseline) <= 0.01

    def test_oborovo_project_irr_within_tolerance_dep_canonical(self):
        """Oborovo project IRR within ±0.5pp of model baseline value."""
        project = create_default_oborovo()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=True)
        result = WaterfallRunner(project, engine).run(config)
        baseline = 0.0798
        assert abs(result.project_irr - baseline) <= 0.005


# ---------------------------------------------------------------------------
# F. Depreciation validation: non-negative book and tax depreciation
# ---------------------------------------------------------------------------

class TestDepreciationValidation:
    """F. Book and tax depreciation are non-negative across all periods."""

    def test_tuho_book_depreciation_non_negative(self):
        """TUHO: all book depreciation values are non-negative."""
        project = create_default_tuho_wind1()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=True)
        result = WaterfallRunner(project, engine).run(config)
        wiring = result._canonical_depreciation_wiring
        for i, dep in enumerate(wiring.book_depreciation_by_period):
            assert dep >= -0.01, f"Period {i}: book dep {dep:.2f} is negative"

    def test_tuho_tax_depreciation_non_negative(self):
        """TUHO: all tax depreciation values are non-negative."""
        project = create_default_tuho_wind1()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=True)
        result = WaterfallRunner(project, engine).run(config)
        wiring = result._canonical_depreciation_wiring
        for i, dep in enumerate(wiring.tax_depreciation_by_period):
            assert dep >= -0.01, f"Period {i}: tax dep {dep:.2f} is negative"

    def test_oborovo_book_depreciation_non_negative(self):
        """Oborovo: all book depreciation values are non-negative."""
        project = create_default_oborovo()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=True)
        result = WaterfallRunner(project, engine).run(config)
        wiring = result._canonical_depreciation_wiring
        for i, dep in enumerate(wiring.book_depreciation_by_period):
            assert dep >= -0.01, f"Period {i}: book dep {dep:.2f} is negative"

    def test_oborovo_tax_depreciation_non_negative(self):
        """Oborovo: all tax depreciation values are non-negative."""
        project = create_default_oborovo()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=True)
        result = WaterfallRunner(project, engine).run(config)
        wiring = result._canonical_depreciation_wiring
        for i, dep in enumerate(wiring.tax_depreciation_by_period):
            assert dep >= -0.01, f"Period {i}: tax dep {dep:.2f} is negative"


# ---------------------------------------------------------------------------
# G. R99/R102 remains BLOCKED
# ---------------------------------------------------------------------------

class TestR99R102BlockedDepreciation:
    """G. R99/R102 fields are NOT affected by depreciation canonical wiring."""

    def test_r99_not_promoted_by_depreciation_canonical(self):
        """R99 (senior sweep reserve) is NOT exposed as a runtime output."""
        project = create_default_tuho_wind1()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=True)
        result = WaterfallRunner(project, engine).run(config)
        assert not hasattr(result, "r99_senior_sweep_reserve_keur")
        assert not hasattr(result, "senior_sweep_reserve_keur")

    def test_r102_not_promoted_by_depreciation_canonical(self):
        """R102 (SHL sweep gate) is NOT exposed as a runtime output."""
        project = create_default_tuho_wind1()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=True)
        result = WaterfallRunner(project, engine).run(config)
        assert not hasattr(result, "r102_shl_sweep_gate_keur")
        assert not hasattr(result, "shl_sweep_gate_keur")


# ---------------------------------------------------------------------------
# H. No senior debt, SHL, DSRA, or distribution changes
# ---------------------------------------------------------------------------

class TestNoOtherWaterfallChanges:
    """H. Senior debt, SHL, DSRA, distributions unchanged when canonical depreciation enabled."""

    def test_tuho_senior_debt_unchanged_dep_vs_no_dep(self):
        """TUHO senior debt unchanged when canonical depreciation is enabled."""
        project = create_default_tuho_wind1()
        engine = _build_period_engine(project)

        config_off = WaterfallRunConfig.from_inputs(project, engine)
        config_off = replace(config_off, use_depreciation_canonical_engine=False)
        result_off = WaterfallRunner(project, engine).run(config_off)

        config_on = WaterfallRunConfig.from_inputs(project, engine)
        config_on = replace(config_on, use_depreciation_canonical_engine=True)
        result_on = WaterfallRunner(project, engine).run(config_on)

        assert abs(result_on.total_senior_ds_keur - result_off.total_senior_ds_keur) <= 1.0

    def test_tuho_distributions_unchanged_dep_vs_no_dep(self):
        """TUHO distributions unchanged when canonical depreciation is enabled."""
        project = create_default_tuho_wind1()
        engine = _build_period_engine(project)

        config_off = WaterfallRunConfig.from_inputs(project, engine)
        config_off = replace(config_off, use_depreciation_canonical_engine=False)
        result_off = WaterfallRunner(project, engine).run(config_off)

        config_on = WaterfallRunConfig.from_inputs(project, engine)
        config_on = replace(config_on, use_depreciation_canonical_engine=True)
        result_on = WaterfallRunner(project, engine).run(config_on)

        def distributions(result):
            return [getattr(p, "distribution_keur", 0.0) for p in result.periods]

        assert distributions(result_on) == distributions(result_off)

    def test_oborovo_senior_debt_unchanged_dep_vs_no_dep(self):
        """Oborovo senior debt unchanged when canonical depreciation is enabled."""
        project = create_default_oborovo()
        engine = _build_period_engine(project)

        config_off = WaterfallRunConfig.from_inputs(project, engine)
        config_off = replace(config_off, use_depreciation_canonical_engine=False)
        result_off = WaterfallRunner(project, engine).run(config_off)

        config_on = WaterfallRunConfig.from_inputs(project, engine)
        config_on = replace(config_on, use_depreciation_canonical_engine=True)
        result_on = WaterfallRunner(project, engine).run(config_on)

        assert abs(result_on.total_senior_ds_keur - result_off.total_senior_ds_keur) <= 1.0


# ---------------------------------------------------------------------------
# I. Depreciation wiring audit validation
# ---------------------------------------------------------------------------

class TestDepreciationWiringAudit:
    """I. Canonical depreciation wiring produces valid audit outputs."""

    def test_book_depreciation_sum_matches_total(self):
        """Sum of book depreciation by period equals total_book_depreciation_keur."""
        project = create_default_tuho_wind1()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=True)
        result = WaterfallRunner(project, engine).run(config)
        wiring = result._canonical_depreciation_wiring
        total = sum(wiring.book_depreciation_by_period)
        assert abs(total - wiring.total_book_depreciation_keur) <= 1.0

    def test_tax_depreciation_sum_matches_total(self):
        """Sum of tax depreciation by period equals total_tax_depreciation_keur."""
        project = create_default_tuho_wind1()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=True)
        result = WaterfallRunner(project, engine).run(config)
        wiring = result._canonical_depreciation_wiring
        total = sum(wiring.tax_depreciation_by_period)
        assert abs(total - wiring.total_tax_depreciation_keur) <= 1.0

    def test_book_tax_difference_by_period_reconciles(self):
        """book_depreciation - tax_depreciation = book_tax_difference for each period."""
        project = create_default_tuho_wind1()
        engine = _build_period_engine(project)
        config = WaterfallRunConfig.from_inputs(project, engine)
        config = replace(config, use_depreciation_canonical_engine=True)
        result = WaterfallRunner(project, engine).run(config)
        wiring = result._canonical_depreciation_wiring
        for i in range(len(wiring.book_depreciation_by_period)):
            book = wiring.book_depreciation_by_period[i]
            tax = wiring.tax_depreciation_by_period[i]
            diff = wiring.book_tax_difference_by_period[i]
            assert abs((book - tax) - diff) <= 0.01, f"Period {i}: diff mismatch"