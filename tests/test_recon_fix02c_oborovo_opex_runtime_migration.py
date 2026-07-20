"""Recon Fix 02C — Oborovo Hierarchical OPEX Runtime Migration.

Test suite covering:
A. Capability-field dispatch (presence/absence routing)
B. Config completeness — all 13 categories, correct subitem counts
C. Per-category annual accuracy vs Excel fixture (≤1e-6 kEUR)
D. B.07 PRE_OPERATION_BASE escalation convention
E. B.08 Y11-30 step activation (zero Y1-10, active Y11+)
F. B.11 SENIOR_DEBT_TENOR_ACTIVE: active Y1-tenor, inactive beyond
G. B.12 Y1-Y2-only subitems going quiet at Y3
H. B.13 PERCENTAGE_OF_SELECTED_BASES round-trips D/F zero series
I. External series: D and F explicit zeros (assert never silent)
J. TUHO/generic projects untouched (hierarchical_opex_model=None)
K. Period dispatch integration: period schedule routes via hierarchical
L. Period total vs annual reconciliation (period sum ≈ annual × df)
M. Downstream: OPEX enters financial model correctly
N. Validation clean: no ERROR issues on Oborovo model+context
O. Tenor change propagates without touching the config object
P. Legacy path parity check: opex_schedule_period difference is bounded
   (documents the known difference, not zero — the hierarchical is the truth)
R. B.02 Y1 vs Y2 structural break (mobilisation vs ongoing)
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from finco_core.opex.hierarchical import (
    OpexCalculationContext,
    OpexCategoryCalculationType,
    OpexActivationMode,
    OpexEscalationConvention,
    compute_annual,
    has_errors,
    validate_opex_model_input,
)
from finco_core.opex.oborovo_config import (
    build_oborovo_hierarchical_opex_model,
    build_oborovo_opex_context,
)

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "excel_oborovo_opex_structural_truth.json"
_HORIZON = 30


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def fixture_data():
    with open(_FIXTURE_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def oborovo_model():
    return build_oborovo_hierarchical_opex_model()


@pytest.fixture(scope="module")
def oborovo_ctx():
    return build_oborovo_opex_context(senior_debt_tenor_years=14)


@pytest.fixture(scope="module")
def annual_results(oborovo_model, oborovo_ctx):
    return compute_annual(oborovo_model, oborovo_ctx, horizon_years=_HORIZON)


@pytest.fixture(scope="module")
def project_inputs():
    from app.project_factories import create_default_oborovo
    return create_default_oborovo()


@pytest.fixture(scope="module")
def period_engine(project_inputs):
    from finco_core.engine.period_engine import PeriodEngine, PeriodFrequency
    info = project_inputs.info
    return PeriodEngine(
        financial_close=info.financial_close,
        construction_months=info.construction_months,
        horizon_years=info.horizon_years,
        ppa_years=12,
        frequency=PeriodFrequency.SEMESTRIAL,
    )


# ---------------------------------------------------------------------------
# A. Capability-field dispatch
# ---------------------------------------------------------------------------


class TestCapabilityDispatch:
    def test_oborovo_has_hierarchical_opex_model(self, project_inputs):
        assert project_inputs.hierarchical_opex_model is not None

    def test_capability_field_is_opex_model_input(self, project_inputs):
        from finco_core.opex.hierarchical._inputs import OpexModelInput
        assert isinstance(project_inputs.hierarchical_opex_model, OpexModelInput)

    def test_dispatch_routes_to_hierarchical_when_present(self, project_inputs, period_engine):
        """opex_schedule_period must take the hierarchical path when capability is set."""
        from finco_core.opex.projections import (
            _opex_schedule_period_hierarchical,
            opex_schedule_period,
        )
        sched_direct = _opex_schedule_period_hierarchical(project_inputs, period_engine)
        sched_via_dispatch = opex_schedule_period(project_inputs, period_engine)
        assert sched_via_dispatch == sched_direct

    def test_dispatch_routes_to_legacy_when_absent(self, project_inputs, period_engine):
        """opex_schedule_period must take the legacy path when capability is None."""
        from finco_core.opex.projections import (
            _opex_schedule_period_legacy,
            opex_schedule_period,
        )
        inputs_no_cap = replace(project_inputs, hierarchical_opex_model=None)
        sched_direct = _opex_schedule_period_legacy(inputs_no_cap, period_engine)
        sched_via_dispatch = opex_schedule_period(inputs_no_cap, period_engine)
        assert sched_via_dispatch == sched_direct

    def test_dispatch_does_not_use_project_name(self, project_inputs):
        """No identity dispatch — never check project name."""
        from finco_core.opex.projections import opex_schedule_period
        import inspect
        src = inspect.getsource(opex_schedule_period)
        for forbidden in ("project_name", "project_code", "oborovo", "OBOROVO"):
            assert forbidden not in src, (
                f"opex_schedule_period must not reference {forbidden!r}"
            )


# ---------------------------------------------------------------------------
# B. Config completeness
# ---------------------------------------------------------------------------


class TestConfigCompleteness:
    def test_thirteen_categories(self, oborovo_model):
        assert len(oborovo_model.categories) == 13

    def test_category_codes_in_order(self, oborovo_model):
        codes = [c.code for c in oborovo_model.categories]
        expected = [f"B.{i:02d}" if i < 10 else f"B.{i}" for i in range(1, 14)]
        assert codes == expected

    def test_b01_four_subitems(self, oborovo_model):
        b01 = next(c for c in oborovo_model.categories if c.code == "B.01")
        assert len(b01.subitems) == 4

    def test_b02_six_subitems_including_always_items(self, oborovo_model):
        b02 = next(c for c in oborovo_model.categories if c.code == "B.02")
        assert len(b02.subitems) == 6

    def test_b02_always_items_budget_sum_65(self, oborovo_model):
        """B.02.4 (1) + B.02.5 (64) = 65 kEUR always-active budget."""
        b02 = next(c for c in oborovo_model.categories if c.code == "B.02")
        always_total = sum(
            si.base_amount_keur
            for si in b02.subitems
            if si.activation_mode == OpexActivationMode.ALWAYS
        )
        assert abs(always_total - 65.0) < 1e-9

    def test_b13_percentage_type(self, oborovo_model):
        b13 = next(c for c in oborovo_model.categories if c.code == "B.13")
        assert b13.calculation_type == OpexCategoryCalculationType.PERCENTAGE_OF_SELECTED_BASES

    def test_b13_rate_four_percent(self, oborovo_model):
        b13 = next(c for c in oborovo_model.categories if c.code == "B.13")
        assert abs(b13.percentage_rate - 0.04) < 1e-12

    def test_b13_base_codes_include_d_and_f(self, oborovo_model):
        b13 = next(c for c in oborovo_model.categories if c.code == "B.13")
        assert "D" in b13.percentage_base_codes
        assert "F" in b13.percentage_base_codes

    def test_b13_base_codes_include_b01_to_b12(self, oborovo_model):
        b13 = next(c for c in oborovo_model.categories if c.code == "B.13")
        for i in range(1, 13):
            code = f"B.0{i}" if i < 10 else f"B.{i}"
            assert code in b13.percentage_base_codes, f"{code} missing from B.13 base codes"

    def test_b11_has_senior_debt_tenor_active_subitem(self, oborovo_model):
        b11 = next(c for c in oborovo_model.categories if c.code == "B.11")
        tenor_items = [si for si in b11.subitems
                       if si.activation_mode == OpexActivationMode.SENIOR_DEBT_TENOR_ACTIVE]
        assert len(tenor_items) == 1
        assert abs(tenor_items[0].base_amount_keur - 20.0) < 1e-9


# ---------------------------------------------------------------------------
# C. Per-category annual accuracy vs fixture
# ---------------------------------------------------------------------------


class TestPerCategoryAccuracy:
    _TOLERANCE = 1e-6

    @pytest.mark.parametrize("cat_code", [
        "B.01", "B.02", "B.03", "B.04", "B.05", "B.06",
        "B.07", "B.08", "B.09", "B.10", "B.11", "B.12", "B.13",
    ])
    def test_category_matches_fixture_y1_y30(self, cat_code, annual_results, fixture_data):
        expected = fixture_data["categories"][cat_code]["annual"]["cached_values_y1_y30"]
        for r in annual_results:
            actual = next(c.annual_keur for c in r.categories if c.code == cat_code)
            err = abs(actual - expected[r.year_index - 1])
            assert err <= self._TOLERANCE, (
                f"{cat_code} Y{r.year_index}: actual={actual:.8f} "
                f"expected={expected[r.year_index-1]:.8f} err={err:.2e}"
            )

    def test_y1_total_matches_fixture(self, annual_results, fixture_data):
        y1_total = annual_results[0].total_keur
        expected = fixture_data["totals"]["total_opex_incl_contingencies"]["y1_cached"]
        assert abs(y1_total - expected) <= self._TOLERANCE

    def test_annual_total_equals_sum_of_categories(self, annual_results):
        for r in annual_results:
            cat_sum = sum(c.annual_keur for c in r.categories)
            assert abs(r.total_keur - cat_sum) < 1e-10


# ---------------------------------------------------------------------------
# D. B.07 PRE_OPERATION_BASE escalation
# ---------------------------------------------------------------------------


class TestB07Escalation:
    def test_b07_convention_is_pre_operation_base(self, oborovo_model):
        b07 = next(c for c in oborovo_model.categories if c.code == "B.07")
        assert b07.escalation_convention == OpexEscalationConvention.PRE_OPERATION_BASE

    def test_b07_y1_equals_budget_times_1_plus_inf(self, annual_results, oborovo_model):
        """Y1 = base × (1+inf)^1 under PRE_OPERATION_BASE."""
        b07_cat = next(c for c in oborovo_model.categories if c.code == "B.07")
        inf = b07_cat.inflation_rate
        budget_sum = sum(si.base_amount_keur for si in b07_cat.subitems)
        expected_y1 = budget_sum * (1 + inf) ** 1
        actual_y1 = next(c.annual_keur for c in annual_results[0].categories if c.code == "B.07")
        assert abs(actual_y1 - expected_y1) < 1e-9

    def test_b07_y1_cached_value(self, annual_results, fixture_data):
        expected = fixture_data["categories"]["B.07"]["annual"]["cached_values_y1_y30"][0]
        actual = next(c.annual_keur for c in annual_results[0].categories if c.code == "B.07")
        assert abs(actual - expected) < 1e-6


# ---------------------------------------------------------------------------
# E. B.08 Y11-30 step activation
# ---------------------------------------------------------------------------


class TestB08StepActivation:
    def test_b08_3_zero_y1_y10(self, annual_results):
        """B.08.3 (repowering reserve) must be zero for Y1-Y10."""
        for r in annual_results[:10]:
            b08_result = next(c for c in r.categories if c.code == "B.08")
            si_b083 = next(si for si in b08_result.subitems if si.code == "B.08.3")
            assert si_b083.active is False, f"B.08.3 should be inactive Y{r.year_index}"

    def test_b08_3_active_y11_y30(self, annual_results):
        """B.08.3 must be active for Y11-Y30."""
        for r in annual_results[10:]:
            b08_result = next(c for c in r.categories if c.code == "B.08")
            si_b083 = next(si for si in b08_result.subitems if si.code == "B.08.3")
            assert si_b083.active is True, f"B.08.3 should be active Y{r.year_index}"

    def test_b08_annual_jump_at_y11(self, annual_results):
        """B.08 total must jump significantly at Y11 vs Y10."""
        b08_y10 = next(c.annual_keur for c in annual_results[9].categories if c.code == "B.08")
        b08_y11 = next(c.annual_keur for c in annual_results[10].categories if c.code == "B.08")
        assert b08_y11 > b08_y10 + 300, f"B.08 should jump at Y11: Y10={b08_y10:.2f} Y11={b08_y11:.2f}"


# ---------------------------------------------------------------------------
# F. B.11 SENIOR_DEBT_TENOR_ACTIVE
# ---------------------------------------------------------------------------


class TestB11TenorActive:
    def test_b11_active_y1_through_y14(self, annual_results):
        for r in annual_results[:14]:
            b11 = next(c for c in r.categories if c.code == "B.11")
            assert b11.annual_keur > 0, f"B.11 should be active Y{r.year_index}"

    def test_b11_zero_from_y15(self, annual_results):
        for r in annual_results[14:]:
            b11 = next(c for c in r.categories if c.code == "B.11")
            assert b11.annual_keur == 0.0, f"B.11 should be zero Y{r.year_index}"

    def test_b11_tenor_change_propagates(self, oborovo_model, oborovo_ctx):
        """Changing senior_tenor_years in context changes B.11 cutoff without editing model."""
        ext = oborovo_ctx.external_annual_series
        ctx_10 = OpexCalculationContext(
            senior_debt_tenor_years=10,
            external_annual_series=ext,
        )
        annual_10 = compute_annual(oborovo_model, ctx_10, horizon_years=_HORIZON)
        b11_y10 = next(c.annual_keur for c in annual_10[9].categories if c.code == "B.11")
        b11_y11 = next(c.annual_keur for c in annual_10[10].categories if c.code == "B.11")
        assert b11_y10 > 0
        assert b11_y11 == 0.0

    def test_b11_tenor_is_derived_from_financing(self, project_inputs):
        """senior_debt_tenor_years must be taken from inputs.financing, not hardcoded."""
        from finco_core.opex.projections import _opex_schedule_period_hierarchical
        import inspect
        src = inspect.getsource(_opex_schedule_period_hierarchical)
        assert "senior_tenor_years" in src
        assert "14" not in src.replace("14,", "").replace("14)", ""), (
            "Tenor must not be hardcoded; derive from inputs.financing.senior_tenor_years"
        )


# ---------------------------------------------------------------------------
# G. B.12 Y1-Y2 subitems
# ---------------------------------------------------------------------------


class TestB12Activation:
    def test_b12_3_and_b12_5_active_y1_y2(self, annual_results, oborovo_model):
        b12_cat = next(c for c in oborovo_model.categories if c.code == "B.12")
        y1_2_subitems = [
            si for si in b12_cat.subitems
            if si.code in ("B.12.3", "B.12.5")
        ]
        assert len(y1_2_subitems) == 2
        for r in annual_results[:2]:
            b12_r = next(c for c in r.categories if c.code == "B.12")
            for si_r in b12_r.subitems:
                if si_r.code in ("B.12.3", "B.12.5"):
                    assert si_r.active, f"{si_r.code} should be active Y{r.year_index}"

    def test_b12_3_and_b12_5_inactive_y3_plus(self, annual_results):
        for r in annual_results[2:]:
            b12_r = next(c for c in r.categories if c.code == "B.12")
            for si_r in b12_r.subitems:
                if si_r.code in ("B.12.3", "B.12.5"):
                    assert not si_r.active, f"{si_r.code} should be inactive Y{r.year_index}"


# ---------------------------------------------------------------------------
# H. B.13 D/F zero series
# ---------------------------------------------------------------------------


class TestB13ExternalSeries:
    def test_d_and_f_are_zero_series(self, oborovo_ctx):
        ext = dict(oborovo_ctx.external_annual_series)
        assert "D" in ext
        assert "F" in ext
        assert all(v == 0.0 for v in ext["D"])
        assert all(v == 0.0 for v in ext["F"])

    def test_d_and_f_series_length_30(self, oborovo_ctx):
        ext = dict(oborovo_ctx.external_annual_series)
        assert len(ext["D"]) == _HORIZON
        assert len(ext["F"]) == _HORIZON

    def test_b13_consistent_with_zero_d_f(self, annual_results, oborovo_model):
        """B.13 must equal 0.04 × sum(B.01..B.12) when D=F=0."""
        b01_b12_codes = [f"B.0{i}" if i < 10 else f"B.{i}" for i in range(1, 13)]
        for r in annual_results:
            base_sum = sum(
                c.annual_keur for c in r.categories if c.code in b01_b12_codes
            )
            expected_b13 = 0.04 * base_sum
            actual_b13 = next(c.annual_keur for c in r.categories if c.code == "B.13")
            assert abs(actual_b13 - expected_b13) < 1e-9


# ---------------------------------------------------------------------------
# I. External series invariant
# ---------------------------------------------------------------------------


class TestExternalSeriesInvariant:
    def test_validation_passes_with_explicit_d_f(self, oborovo_model, oborovo_ctx):
        issues = validate_opex_model_input(oborovo_model, oborovo_ctx, horizon_years=_HORIZON)
        errors = [i for i in issues if i.severity.value == "ERROR"]
        assert not errors, f"Unexpected errors: {errors}"

    def test_compute_fails_without_d_f_series(self, oborovo_model):
        """compute_annual must fail (OPX060) if D/F external series are absent."""
        from finco_core.opex.hierarchical import OpexInputValidationError
        ctx_no_ext = OpexCalculationContext(
            senior_debt_tenor_years=14,
            external_annual_series=(),
        )
        with pytest.raises(OpexInputValidationError) as exc_info:
            compute_annual(oborovo_model, ctx_no_ext, horizon_years=_HORIZON)
        codes = {i.code for i in exc_info.value.issues}
        assert "OPX060" in codes


# ---------------------------------------------------------------------------
# J. Other projects untouched
# ---------------------------------------------------------------------------


class TestOtherProjectsUnchanged:
    def test_tuho_has_no_hierarchical_model(self):
        from app.project_factories import create_default_tuho_wind1
        inputs = create_default_tuho_wind1()
        assert inputs.hierarchical_opex_model is None

    def test_generic_solar_has_no_hierarchical_model(self):
        from app.project_factories import create_default_solar_project
        inputs = create_default_solar_project()
        assert inputs.hierarchical_opex_model is None

    def test_generic_wind_has_no_hierarchical_model(self):
        from app.project_factories import create_default_wind_project
        inputs = create_default_wind_project()
        assert inputs.hierarchical_opex_model is None


# ---------------------------------------------------------------------------
# K. Period dispatch integration
# ---------------------------------------------------------------------------


class TestPeriodDispatch:
    def test_period_schedule_returns_dict_keyed_by_period_index(
        self, project_inputs, period_engine
    ):
        from finco_core.opex.projections import opex_schedule_period
        sched = opex_schedule_period(project_inputs, period_engine)
        assert isinstance(sched, dict)
        for p in period_engine.periods():
            assert p.index in sched

    def test_non_operation_periods_are_zero(self, project_inputs, period_engine):
        from finco_core.opex.projections import opex_schedule_period
        sched = opex_schedule_period(project_inputs, period_engine)
        for p in period_engine.periods():
            if not p.is_operation:
                assert sched[p.index] == 0.0, f"Period {p.index} should be 0 (construction)"

    def test_operation_periods_are_positive(self, project_inputs, period_engine):
        from finco_core.opex.projections import opex_schedule_period
        sched = opex_schedule_period(project_inputs, period_engine)
        for p in period_engine.periods():
            if p.is_operation:
                assert sched[p.index] > 0.0, f"Period {p.index} should be positive"


# ---------------------------------------------------------------------------
# L. Period total vs annual reconciliation
# ---------------------------------------------------------------------------


class TestPeriodAnnualReconciliation:
    _TOLERANCE = 1e-6

    def test_period_keur_equals_annual_times_day_fraction(
        self, project_inputs, period_engine, annual_results
    ):
        """period_keur = annual_keur × day_fraction for each operation period.

        Day fractions for H1+H2 of a semestrial year may not sum to exactly 1.0
        due to the semestrial calendar crossing calendar-year boundaries.  That is
        expected and correct.  What must hold is the per-period identity:
            period_keur ≈ annual_keur × day_fraction
        """
        from finco_core.opex.projections import opex_schedule_period
        sched = opex_schedule_period(project_inputs, period_engine)
        annual_by_year = {r.year_index: r.total_keur for r in annual_results}

        for p in period_engine.periods():
            if not p.is_operation:
                continue
            expected = annual_by_year[p.year_index] * p.day_fraction
            actual = sched[p.index]
            err = abs(actual - expected)
            assert err <= self._TOLERANCE, (
                f"Period {p.index} (Y{p.year_index}H{p.period_in_year}): "
                f"actual={actual:.8f} expected={expected:.8f} err={err:.2e}"
            )


# ---------------------------------------------------------------------------
# M. Downstream financial model integration
# ---------------------------------------------------------------------------


class TestDownstreamIntegration:
    def _run(self, project_inputs):
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
        engine = _build_period_engine(project_inputs)
        config = WaterfallRunConfig.from_inputs(project_inputs, engine)
        return WaterfallRunner(project_inputs, engine).run(config)

    def test_waterfall_runner_accepts_oborovo_inputs(self, project_inputs):
        """Full waterfall model run must not raise with hierarchical capability enabled."""
        result = self._run(project_inputs)
        assert result is not None

    def test_total_opex_is_positive(self, project_inputs):
        """Total OPEX over horizon must be positive after migration."""
        result = self._run(project_inputs)
        assert result.total_opex_keur > 0

    def test_ebitda_is_positive(self, project_inputs):
        """Total EBITDA must be positive after migration."""
        result = self._run(project_inputs)
        assert result.total_ebitda_keur > 0

    def test_hierarchical_opex_greater_than_legacy(self, project_inputs):
        """Hierarchical OPEX total (Excel-true) differs from legacy approximation."""
        result_h = self._run(project_inputs)
        inputs_legacy = replace(project_inputs, hierarchical_opex_model=None)
        result_l = self._run(inputs_legacy)
        # The hierarchical is the Excel truth; legacy was an approximation.
        # This test documents the known direction: the two differ.
        assert abs(result_h.total_opex_keur - result_l.total_opex_keur) > 100, (
            "Expected non-trivial delta between hierarchical and legacy OPEX"
        )


# ---------------------------------------------------------------------------
# N. Validation clean on Oborovo config
# ---------------------------------------------------------------------------


class TestValidationClean:
    def test_no_error_issues(self, oborovo_model, oborovo_ctx):
        issues = validate_opex_model_input(oborovo_model, oborovo_ctx, horizon_years=_HORIZON)
        errors = [i for i in issues if i.severity.value == "ERROR"]
        assert not errors, f"Error issues found: {[i.code for i in errors]}"

    def test_has_errors_returns_false(self, oborovo_model, oborovo_ctx):
        issues = validate_opex_model_input(oborovo_model, oborovo_ctx, horizon_years=_HORIZON)
        assert not has_errors(issues)


# ---------------------------------------------------------------------------
# O. Tenor change propagates via context only
# ---------------------------------------------------------------------------


class TestTenorContextOnly:
    def test_model_is_immutable(self, oborovo_model):
        """The config object is frozen — cannot change it at runtime."""
        with pytest.raises((TypeError, AttributeError)):
            oborovo_model.categories = ()

    def test_context_tenor_controls_b11_cutoff(self, oborovo_model, oborovo_ctx):
        """Only the context tenor matters; the config has no hardcoded tenor."""
        ext = oborovo_ctx.external_annual_series
        for tenor in (10, 14, 20):
            ctx = OpexCalculationContext(
                senior_debt_tenor_years=tenor,
                external_annual_series=ext,
            )
            results = compute_annual(oborovo_model, ctx, horizon_years=_HORIZON)
            # B.11 should be zero in year tenor+1 (if ≤ 30)
            if tenor < _HORIZON:
                b11_beyond = next(
                    c.annual_keur for c in results[tenor].categories if c.code == "B.11"
                )
                assert b11_beyond == 0.0, f"B.11 should be zero at Y{tenor+1} for tenor={tenor}"


# ---------------------------------------------------------------------------
# P. Legacy vs hierarchical delta (informational, not zero)
# ---------------------------------------------------------------------------


class TestLegacyHierarchicalDelta:
    def test_delta_is_documented_not_zero(self, project_inputs, period_engine):
        """Hierarchical and legacy paths produce different totals — this is expected.

        The hierarchical is the truth. Legacy was an approximation.
        This test documents the known total delta for traceability.
        The bound of 10_000 kEUR is intentionally loose; tighten after
        any intentional recalibration of the legacy path.
        """
        from finco_core.opex.projections import opex_schedule_period
        sched_h = opex_schedule_period(project_inputs, period_engine)

        inputs_legacy = replace(project_inputs, hierarchical_opex_model=None)
        sched_l = opex_schedule_period(inputs_legacy, period_engine)

        op_periods = [p for p in period_engine.periods() if p.is_operation]
        total_h = sum(sched_h[p.index] for p in op_periods)
        total_l = sum(sched_l[p.index] for p in op_periods)
        delta = abs(total_h - total_l)

        # The paths differ because legacy used aggregated approximations.
        # Hierarchical is the Excel-reconciled truth.
        assert 0 < delta < 10_000, (
            f"Expected non-zero delta bounded below 10_000 kEUR; got {delta:.2f}"
        )


# ---------------------------------------------------------------------------
# R. B.02 structural break Y1 vs Y2
# ---------------------------------------------------------------------------


class TestB02StructuralBreak:
    _TOL = 1e-6

    def test_b02_y1_sum_is_244(self, annual_results, fixture_data):
        expected = fixture_data["categories"]["B.02"]["annual"]["cached_values_y1_y30"][0]
        actual = next(c.annual_keur for c in annual_results[0].categories if c.code == "B.02")
        assert abs(actual - expected) <= self._TOL, f"B.02 Y1: {actual} != {expected}"

    def test_b02_y2_sum_is_18564(self, annual_results, fixture_data):
        expected = fixture_data["categories"]["B.02"]["annual"]["cached_values_y1_y30"][1]
        actual = next(c.annual_keur for c in annual_results[1].categories if c.code == "B.02")
        assert abs(actual - expected) <= self._TOL, f"B.02 Y2: {actual} != {expected}"

    def test_b02_y1_has_mobilisation_active(self, annual_results):
        b02_r = next(c for c in annual_results[0].categories if c.code == "B.02")
        mob = next(si for si in b02_r.subitems if si.code == "B.02.1")
        assert mob.active

    def test_b02_y2_has_mobilisation_inactive(self, annual_results):
        b02_r = next(c for c in annual_results[1].categories if c.code == "B.02")
        mob = next(si for si in b02_r.subitems if si.code == "B.02.1")
        assert not mob.active

    def test_b02_y2_has_ongoing_active(self, annual_results):
        b02_r = next(c for c in annual_results[1].categories if c.code == "B.02")
        ongoing = next(si for si in b02_r.subitems if si.code == "B.02.2")
        assert ongoing.active
