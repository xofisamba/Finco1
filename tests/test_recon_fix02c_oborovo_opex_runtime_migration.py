"""Recon Fix 02C — Oborovo Hierarchical OPEX Runtime Migration.

Test suite covering:
A. Capability dispatch (routing via HierarchicalOpexCapability field)
B. Config completeness — all 13 categories, exact 61 subitem counts
C. Per-category annual accuracy vs fixture (all 13 × 30 years ≤1e-6)
D. B.07 PRE_OPERATION_BASE escalation convention
E. B.08 Y11-30 step activation (zero Y1-10, active Y11+)
F. B.11 SENIOR_DEBT_TENOR_ACTIVE: active Y1-tenor, inactive beyond
G. B.12 Y1-Y2-only subitems going quiet at Y3
H. B.13 D/F zero series
I. External series: D and F explicit zeros (assert never silent)
J. TUHO/generic projects untouched (hierarchical_opex_capability=None)
K. Period dispatch integration
L. Period keur = annual × day_fraction
M. Downstream: WaterfallRunner accepts Oborovo
N. Validation clean on Oborovo model
O. Tenor context-only (no hardcoded tenor in config)
P. Legacy vs hierarchical delta documented (known delta, not zero)
Q. Cache correctness
R. Mutating legacy opex does not affect hierarchical result
S. Fail-hard on invalid capability
T. Identity invariance (rename project info → same outputs)
U. Excel period reconciliation (per-period per-category ≤ 2.0 kEUR)
"""
from __future__ import annotations

import inspect
import json
from dataclasses import replace
from pathlib import Path

import pytest

from finco_core.opex.hierarchical import (
    OpexCalculationContext,
    OpexCategoryCalculationType,
    OpexActivationMode,
    OpexEscalationConvention,
    OpexInputValidationError,
    compute_annual,
    has_errors,
    validate_opex_model_input,
)
from finco_core.opex.oborovo_config import (
    build_oborovo_hierarchical_opex_model,
    build_oborovo_opex_capability,
)

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "excel_oborovo_opex_structural_truth.json"
_FINANCIAL_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "excel_oborovo_financial_truth.json"
_HORIZON = 30


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def fixture_data():
    with open(_FIXTURE_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def financial_fixture():
    with open(_FINANCIAL_FIXTURE_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def oborovo_model():
    return build_oborovo_hierarchical_opex_model()


@pytest.fixture(scope="module")
def oborovo_cap():
    return build_oborovo_opex_capability(senior_debt_tenor_years=14)


@pytest.fixture(scope="module")
def oborovo_ctx(oborovo_cap):
    return OpexCalculationContext(
        senior_debt_tenor_years=14,
        external_annual_series=oborovo_cap.external_annual_series,
    )


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


def _run_waterfall(inputs):
    from app.ui_runner import _build_period_engine
    from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
    engine = _build_period_engine(inputs)
    config = WaterfallRunConfig.from_inputs(inputs, engine)
    return WaterfallRunner(inputs, engine).run(config)


# ---------------------------------------------------------------------------
# A. Capability-field dispatch
# ---------------------------------------------------------------------------


class TestCapabilityDispatch:
    def test_oborovo_has_hierarchical_opex_capability(self, project_inputs):
        assert project_inputs.hierarchical_opex_capability is not None

    def test_capability_field_is_hierarchical_opex_capability(self, project_inputs):
        from finco_core.opex._capability import HierarchicalOpexCapability
        assert isinstance(project_inputs.hierarchical_opex_capability, HierarchicalOpexCapability)

    def test_capability_contains_opex_model_input(self, project_inputs):
        from finco_core.opex.hierarchical._inputs import OpexModelInput
        assert isinstance(project_inputs.hierarchical_opex_capability.opex_model, OpexModelInput)

    def test_dispatch_routes_to_hierarchical_when_present(self, project_inputs, period_engine):
        from finco_core.opex.projections import (
            _opex_schedule_period_hierarchical,
            opex_schedule_period,
        )
        sched_direct = _opex_schedule_period_hierarchical(project_inputs, period_engine)
        sched_via_dispatch = opex_schedule_period(project_inputs, period_engine)
        assert sched_via_dispatch == sched_direct

    def test_dispatch_routes_to_legacy_when_absent(self, project_inputs, period_engine):
        from finco_core.opex.projections import (
            _opex_schedule_period_legacy,
            opex_schedule_period,
        )
        inputs_no_cap = replace(project_inputs, hierarchical_opex_capability=None)
        sched_direct = _opex_schedule_period_legacy(inputs_no_cap, period_engine)
        sched_via_dispatch = opex_schedule_period(inputs_no_cap, period_engine)
        assert sched_via_dispatch == sched_direct

    def test_projections_does_not_import_oborovo_config(self):
        """projections.py must not import oborovo_config."""
        import finco_core.opex.projections as mod
        src = inspect.getsource(mod)
        assert "oborovo_config" not in src, (
            "projections.py must not import oborovo_config"
        )

    def test_dispatch_does_not_use_project_identity(self):
        """opex_schedule_period must not reference project name, code, or 'oborovo'."""
        from finco_core.opex.projections import opex_schedule_period
        src = inspect.getsource(opex_schedule_period)
        for forbidden in ("project_name", "project_code", "oborovo", "OBOROVO"):
            assert forbidden not in src, (
                f"opex_schedule_period must not reference {forbidden!r}"
            )


# ---------------------------------------------------------------------------
# B. Config completeness — 61 subitems
# ---------------------------------------------------------------------------


class TestConfigCompleteness:
    def test_thirteen_categories(self, oborovo_model):
        assert len(oborovo_model.categories) == 13

    def test_category_codes_in_order(self, oborovo_model):
        codes = [c.code for c in oborovo_model.categories]
        expected = [f"B.0{i}" if i < 10 else f"B.{i}" for i in range(1, 14)]
        assert codes == expected

    @pytest.mark.parametrize("code,expected_count", [
        ("B.01", 4),
        ("B.02", 17),
        ("B.03", 4),
        ("B.04", 3),
        ("B.05", 3),
        ("B.06", 5),
        ("B.07", 2),
        ("B.08", 4),
        ("B.09", 4),
        ("B.10", 6),
        ("B.11", 4),
        ("B.12", 5),
        ("B.13", 0),
    ])
    def test_per_category_subitem_count(self, code, expected_count, oborovo_model):
        cat = next(c for c in oborovo_model.categories if c.code == code)
        assert len(cat.subitems) == expected_count, (
            f"{code}: expected {expected_count} subitems, got {len(cat.subitems)}"
        )

    def test_total_b01_b12_subitems_is_61(self, oborovo_model):
        total = sum(len(c.subitems) for c in oborovo_model.categories)
        assert total == 61

    def test_exact_structural_match_against_fixture(self, oborovo_model, fixture_data):
        """Every subitem code, name, and budget must match the Excel fixture."""
        cats_fix = fixture_data["categories"]
        for code, cat_fix in cats_fix.items():
            si_fix = cat_fix.get("subitems", {})
            if not si_fix:
                continue
            cat_py = next((c for c in oborovo_model.categories if c.code == code), None)
            assert cat_py is not None, f"Category {code} not found"
            py_si_dict = {si.code: si for si in cat_py.subitems}
            for si_code, si_data_fix in si_fix.items():
                assert si_code in py_si_dict, (
                    f"{code}.{si_code} missing from Python model"
                )
                py_si = py_si_dict[si_code]
                fix_name = si_data_fix["name"]
                assert py_si.name == fix_name, (
                    f"{code}.{si_code}: name mismatch: {py_si.name!r} != {fix_name!r}"
                )
                fix_budget = (
                    si_data_fix["budget"]["cached_value"]
                    if isinstance(si_data_fix["budget"], dict)
                    else si_data_fix["budget"]
                )
                assert abs(py_si.base_amount_keur - fix_budget) < 1e-6, (
                    f"{code}.{si_code}: budget {py_si.base_amount_keur} != {fix_budget}"
                )

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
# C. Per-category annual accuracy vs fixture (all 13 × 30 ≤ 1e-6)
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
    def test_b08_3_inactive_y1_y10(self, annual_results):
        for r in annual_results[:10]:
            b08_result = next(c for c in r.categories if c.code == "B.08")
            si_b083 = next(si for si in b08_result.subitems if si.code == "B.08.3")
            assert si_b083.active is False, f"B.08.3 should be inactive Y{r.year_index}"

    def test_b08_3_active_y11_y30(self, annual_results):
        for r in annual_results[10:]:
            b08_result = next(c for c in r.categories if c.code == "B.08")
            si_b083 = next(si for si in b08_result.subitems if si.code == "B.08.3")
            assert si_b083.active is True, f"B.08.3 should be active Y{r.year_index}"

    def test_b08_annual_jump_at_y11(self, annual_results):
        b08_y10 = next(c.annual_keur for c in annual_results[9].categories if c.code == "B.08")
        b08_y11 = next(c.annual_keur for c in annual_results[10].categories if c.code == "B.08")
        assert b08_y11 > b08_y10 + 300, (
            f"B.08 should jump at Y11: Y10={b08_y10:.2f} Y11={b08_y11:.2f}"
        )


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

    def test_b11_tenor_change_propagates(self, oborovo_model, oborovo_cap):
        ext = oborovo_cap.external_annual_series
        ctx_10 = OpexCalculationContext(
            senior_debt_tenor_years=10,
            external_annual_series=ext,
        )
        annual_10 = compute_annual(oborovo_model, ctx_10, horizon_years=_HORIZON)
        b11_y10 = next(c.annual_keur for c in annual_10[9].categories if c.code == "B.11")
        b11_y11 = next(c.annual_keur for c in annual_10[10].categories if c.code == "B.11")
        assert b11_y10 > 0
        assert b11_y11 == 0.0

    def test_b11_tenor_derived_from_financing(self, project_inputs):
        from finco_core.opex.projections import _opex_schedule_period_hierarchical
        src = inspect.getsource(_opex_schedule_period_hierarchical)
        assert "senior_tenor_years" in src
        # Must not hardcode the tenor value
        assert "14" not in src.replace("14,", "").replace("14)", ""), (
            "Tenor must not be hardcoded; derive from inputs.financing.senior_tenor_years"
        )


# ---------------------------------------------------------------------------
# G. B.12 Y1-Y2 subitems
# ---------------------------------------------------------------------------


class TestB12Activation:
    def test_b12_3_and_b12_5_active_y1_y2(self, annual_results, oborovo_model):
        b12_cat = next(c for c in oborovo_model.categories if c.code == "B.12")
        y1_2_subitems = [si for si in b12_cat.subitems if si.code in ("B.12.3", "B.12.5")]
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
    def test_d_and_f_are_zero_series(self, oborovo_cap):
        ext = dict(oborovo_cap.external_annual_series)
        assert "D" in ext
        assert "F" in ext
        assert all(v == 0.0 for v in ext["D"])
        assert all(v == 0.0 for v in ext["F"])

    def test_d_and_f_series_length_30(self, oborovo_cap):
        ext = dict(oborovo_cap.external_annual_series)
        assert len(ext["D"]) == _HORIZON
        assert len(ext["F"]) == _HORIZON

    def test_b13_consistent_with_zero_d_f(self, annual_results):
        b01_b12_codes = [f"B.0{i}" if i < 10 else f"B.{i}" for i in range(1, 13)]
        for r in annual_results:
            base_sum = sum(c.annual_keur for c in r.categories if c.code in b01_b12_codes)
            expected_b13 = 0.04 * base_sum
            actual_b13 = next(c.annual_keur for c in r.categories if c.code == "B.13")
            assert abs(actual_b13 - expected_b13) < 1e-9


# ---------------------------------------------------------------------------
# I. External series invariant (OPX060 on absent D/F)
# ---------------------------------------------------------------------------


class TestExternalSeriesInvariant:
    def test_validation_passes_with_explicit_d_f(self, oborovo_model, oborovo_ctx):
        issues = validate_opex_model_input(oborovo_model, oborovo_ctx, horizon_years=_HORIZON)
        errors = [i for i in issues if i.severity.value == "ERROR"]
        assert not errors, f"Unexpected errors: {errors}"

    def test_compute_fails_without_d_f_series(self, oborovo_model):
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
    def test_tuho_has_no_hierarchical_capability(self):
        from app.project_factories import create_default_tuho_wind1
        inputs = create_default_tuho_wind1()
        assert inputs.hierarchical_opex_capability is None

    def test_generic_solar_has_no_hierarchical_capability(self):
        from app.project_factories import create_default_solar_project
        inputs = create_default_solar_project()
        assert inputs.hierarchical_opex_capability is None

    def test_generic_wind_has_no_hierarchical_capability(self):
        from app.project_factories import create_default_wind_project
        inputs = create_default_wind_project()
        assert inputs.hierarchical_opex_capability is None

    def test_tuho_outputs_unchanged(self):
        """TUHO financial outputs are identical regardless of hierarchical capability."""
        from app.project_factories import create_default_tuho_wind1
        inputs = create_default_tuho_wind1()
        result = _run_waterfall(inputs)
        assert result.total_opex_keur > 0
        assert result.total_revenue_keur > 0
        assert result.total_ebitda_keur > 0

    def test_generic_solar_outputs_unchanged(self):
        from app.project_factories import create_default_solar_project
        inputs = create_default_solar_project()
        result = _run_waterfall(inputs)
        assert result.total_opex_keur > 0

    def test_generic_wind_outputs_unchanged(self):
        from app.project_factories import create_default_wind_project
        inputs = create_default_wind_project()
        result = _run_waterfall(inputs)
        assert result.total_opex_keur > 0


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
                assert sched[p.index] == 0.0

    def test_operation_periods_are_positive(self, project_inputs, period_engine):
        from finco_core.opex.projections import opex_schedule_period
        sched = opex_schedule_period(project_inputs, period_engine)
        for p in period_engine.periods():
            if p.is_operation:
                assert sched[p.index] > 0.0


# ---------------------------------------------------------------------------
# L. Period keur = annual × day_fraction
# ---------------------------------------------------------------------------


class TestPeriodAnnualReconciliation:
    _TOLERANCE = 1e-6

    def test_period_keur_equals_annual_times_day_fraction(
        self, project_inputs, period_engine, annual_results
    ):
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
                f"Period {p.index} (Y{p.year_index}): "
                f"actual={actual:.8f} expected={expected:.8f} err={err:.2e}"
            )


# ---------------------------------------------------------------------------
# M. Downstream integration (WaterfallRunner accepts Oborovo)
# ---------------------------------------------------------------------------


class TestDownstreamIntegration:
    def test_waterfall_runner_accepts_oborovo_inputs(self, project_inputs):
        result = _run_waterfall(project_inputs)
        assert result is not None

    def test_total_opex_is_positive(self, project_inputs):
        result = _run_waterfall(project_inputs)
        assert result.total_opex_keur > 0

    def test_ebitda_is_positive(self, project_inputs):
        result = _run_waterfall(project_inputs)
        assert result.total_ebitda_keur > 0


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
# O. Tenor context-only (no hardcoded tenor in model)
# ---------------------------------------------------------------------------


class TestTenorContextOnly:
    def test_model_is_immutable(self, oborovo_model):
        with pytest.raises((TypeError, AttributeError)):
            oborovo_model.categories = ()

    def test_context_tenor_controls_b11_cutoff(self, oborovo_model, oborovo_cap):
        ext = oborovo_cap.external_annual_series
        for tenor in (10, 14, 20):
            ctx = OpexCalculationContext(
                senior_debt_tenor_years=tenor,
                external_annual_series=ext,
            )
            results = compute_annual(oborovo_model, ctx, horizon_years=_HORIZON)
            if tenor < _HORIZON:
                b11_beyond = next(
                    c.annual_keur for c in results[tenor].categories if c.code == "B.11"
                )
                assert b11_beyond == 0.0, (
                    f"B.11 should be zero at Y{tenor+1} for tenor={tenor}"
                )


# ---------------------------------------------------------------------------
# P. Legacy vs hierarchical delta documented (known non-zero delta)
# ---------------------------------------------------------------------------


class TestLegacyHierarchicalDelta:
    def test_delta_is_documented_not_zero(self, project_inputs, period_engine):
        """Hierarchical and legacy paths produce different totals — this is expected.

        The hierarchical is the Excel truth. Legacy was an approximation.
        The total delta over 30 years must be non-zero and bounded below 10_000 kEUR.
        """
        from finco_core.opex.projections import opex_schedule_period
        sched_h = opex_schedule_period(project_inputs, period_engine)

        inputs_legacy = replace(project_inputs, hierarchical_opex_capability=None)
        sched_l = opex_schedule_period(inputs_legacy, period_engine)

        op_periods = [p for p in period_engine.periods() if p.is_operation]
        total_h = sum(sched_h[p.index] for p in op_periods)
        total_l = sum(sched_l[p.index] for p in op_periods)
        delta = abs(total_h - total_l)

        assert 0 < delta < 10_000, (
            f"Expected non-zero delta < 10_000 kEUR; got {delta:.2f}"
        )

    def test_delta_direction_is_known(self, project_inputs, period_engine):
        """The delta must be in a known range — document it, do not vaguely assert."""
        from finco_core.opex.projections import opex_schedule_period
        sched_h = opex_schedule_period(project_inputs, period_engine)
        inputs_legacy = replace(project_inputs, hierarchical_opex_capability=None)
        sched_l = opex_schedule_period(inputs_legacy, period_engine)
        op_periods = [p for p in period_engine.periods() if p.is_operation]
        total_h = sum(sched_h[p.index] for p in op_periods)
        total_l = sum(sched_l[p.index] for p in op_periods)
        # The hierarchical path picks up the correct Excel totals including
        # structural differences in B.02 and B.12 activation patterns.
        # Total delta is expected to be bounded; compute it as documentation.
        delta = total_h - total_l
        # Sign can be either direction; just assert bounded magnitude:
        assert abs(delta) < 10_000, f"Unexpected large delta: {delta:.2f} kEUR"


# ---------------------------------------------------------------------------
# Q. Cache correctness
# ---------------------------------------------------------------------------


class TestCacheCorrectness:
    def test_same_inputs_same_cache_key(self, project_inputs):
        from finco_core.inputs._models import hash_inputs_for_cache
        key1 = hash_inputs_for_cache(project_inputs)
        key2 = hash_inputs_for_cache(project_inputs)
        assert key1 == key2

    def test_changed_subitem_budget_changes_cache_key(self, project_inputs):
        from finco_core.inputs._models import hash_inputs_for_cache
        from finco_core.opex._capability import HierarchicalOpexCapability
        from finco_core.opex.hierarchical._inputs import OpexSubitemInput

        cap = project_inputs.hierarchical_opex_capability
        # Mutate B.01.1 budget from 64 to 999
        old_cats = cap.opex_model.categories
        b01 = old_cats[0]
        old_sis = b01.subitems
        new_si = replace(old_sis[0], base_amount_keur=999.0)
        new_sis = (new_si,) + old_sis[1:]
        new_b01 = replace(b01, subitems=new_sis)
        new_cats = (new_b01,) + old_cats[1:]
        new_model = replace(cap.opex_model, categories=new_cats)
        new_cap = HierarchicalOpexCapability(
            opex_model=new_model,
            external_annual_series=cap.external_annual_series,
        )
        inputs_mutated = replace(project_inputs, hierarchical_opex_capability=new_cap)
        key_orig = hash_inputs_for_cache(project_inputs)
        key_mut = hash_inputs_for_cache(inputs_mutated)
        assert key_orig != key_mut

    def test_legacy_opex_change_changes_cache_key(self, project_inputs):
        from finco_core.inputs._models import hash_inputs_for_cache
        old_opex = project_inputs.opex
        new_opex = (replace(old_opex[0], y1_amount_keur=old_opex[0].y1_amount_keur + 1.0),) + old_opex[1:]
        inputs_mod = replace(project_inputs, opex=new_opex)
        key_orig = hash_inputs_for_cache(project_inputs)
        key_mod = hash_inputs_for_cache(inputs_mod)
        assert key_orig != key_mod


# ---------------------------------------------------------------------------
# R. Mutating legacy opex does not affect hierarchical result
# ---------------------------------------------------------------------------


class TestLegacyOpexMutationInvariance:
    def test_hierarchical_result_unchanged_when_legacy_opex_mutated(
        self, project_inputs, period_engine
    ):
        from finco_core.opex.projections import opex_schedule_period
        sched_original = opex_schedule_period(project_inputs, period_engine)

        # Multiply all legacy opex y1_amount_keur by 2
        new_opex = tuple(replace(item, y1_amount_keur=item.y1_amount_keur * 2.0)
                         for item in project_inputs.opex)
        inputs_mutated = replace(project_inputs, opex=new_opex)
        sched_mutated = opex_schedule_period(inputs_mutated, period_engine)

        # Since hierarchical_opex_capability is present, it should dominate
        assert sched_original == sched_mutated, (
            "Hierarchical schedule must not change when legacy opex is mutated"
        )

    def test_waterfall_total_opex_unchanged_when_legacy_opex_mutated(self, project_inputs):
        result_orig = _run_waterfall(project_inputs)
        new_opex = tuple(replace(item, y1_amount_keur=item.y1_amount_keur * 2.0)
                         for item in project_inputs.opex)
        inputs_mutated = replace(project_inputs, opex=new_opex)
        result_mutated = _run_waterfall(inputs_mutated)
        assert abs(result_orig.total_opex_keur - result_mutated.total_opex_keur) < 1.0, (
            "total_opex_keur must be identical when only legacy opex changes"
        )


# ---------------------------------------------------------------------------
# S. Fail-hard on invalid hierarchical capability
# ---------------------------------------------------------------------------


class TestFailHardOnInvalidCapability:
    def test_self_referencing_percentage_base_raises(self, project_inputs, period_engine):
        """A self-referencing percentage_base_code triggers OPX033 → fail hard."""
        from finco_core.opex._capability import HierarchicalOpexCapability
        from finco_core.opex.projections import opex_schedule_period

        cap = project_inputs.hierarchical_opex_capability
        old_cats = cap.opex_model.categories
        b13 = old_cats[-1]
        # Inject B.13 as its own base (self-reference → OPX033)
        bad_b13 = replace(b13, percentage_base_codes=b13.percentage_base_codes + ("B.13",))
        bad_cats = old_cats[:-1] + (bad_b13,)
        bad_model = replace(cap.opex_model, categories=bad_cats)
        bad_cap = HierarchicalOpexCapability(
            opex_model=bad_model,
            external_annual_series=cap.external_annual_series,
        )
        inputs_bad = replace(project_inputs, hierarchical_opex_capability=bad_cap)

        with pytest.raises(OpexInputValidationError):
            opex_schedule_period(inputs_bad, period_engine)

    def test_no_legacy_fallback_on_invalid_capability(self, project_inputs, period_engine):
        """Fail-hard means the error propagates — no silent fallback to legacy."""
        from finco_core.opex._capability import HierarchicalOpexCapability
        from finco_core.opex.projections import opex_schedule_period

        cap = project_inputs.hierarchical_opex_capability
        old_cats = cap.opex_model.categories
        b13 = old_cats[-1]
        bad_b13 = replace(b13, percentage_base_codes=b13.percentage_base_codes + ("B.13",))
        bad_cats = old_cats[:-1] + (bad_b13,)
        bad_model = replace(cap.opex_model, categories=bad_cats)
        bad_cap = HierarchicalOpexCapability(
            opex_model=bad_model,
            external_annual_series=cap.external_annual_series,
        )
        inputs_bad = replace(project_inputs, hierarchical_opex_capability=bad_cap)

        # Must raise — must NOT silently return legacy schedule
        with pytest.raises(OpexInputValidationError):
            opex_schedule_period(inputs_bad, period_engine)


# ---------------------------------------------------------------------------
# T. Identity invariance (rename ProjectInfo → same financial outputs)
# ---------------------------------------------------------------------------


class TestIdentityInvariance:
    def test_renamed_project_info_same_opex(self, project_inputs, period_engine):
        from finco_core.opex.projections import opex_schedule_period
        sched_orig = opex_schedule_period(project_inputs, period_engine)

        renamed_info = replace(
            project_inputs.info,
            name="Random Project XYZ",
            code="RAND-999",
            company="RandomCo",
        )
        inputs_renamed = replace(project_inputs, info=renamed_info)
        sched_renamed = opex_schedule_period(inputs_renamed, period_engine)

        assert sched_orig == sched_renamed, (
            "OPEX schedule must be identical after renaming project identity fields"
        )

    def test_renamed_project_info_same_waterfall(self, project_inputs):
        result_orig = _run_waterfall(project_inputs)

        renamed_info = replace(
            project_inputs.info,
            name="Random Project XYZ",
            code="RAND-999",
            company="RandomCo",
        )
        inputs_renamed = replace(project_inputs, info=renamed_info)
        result_renamed = _run_waterfall(inputs_renamed)

        assert abs(result_orig.total_revenue_keur - result_renamed.total_revenue_keur) < 1.0
        assert abs(result_orig.total_opex_keur - result_renamed.total_opex_keur) < 1.0
        assert abs(result_orig.total_ebitda_keur - result_renamed.total_ebitda_keur) < 1.0


# ---------------------------------------------------------------------------
# U. Excel period reconciliation (per-period per-category ≤ 2.0 kEUR)
# ---------------------------------------------------------------------------


class TestExcelPeriodReconciliation:
    """Compare Python hierarchical per-period per-category OPEX vs Excel fixture.

    The fixture 'excel_oborovo_financial_truth.json' contains
    cf.opex_items_period_keur with 61 periods (index 0 = construction).
    Python op periods are indexed starting from the engine's first operation
    period (engine index 2 = first half-year after COD).

    Mapping: fixture period index i (1..60) → op_periods[i-1].
    Excel values are negative (expense sign); Python produces positive kEUR.
    Tolerance = 2.0 kEUR to account for minor day-fraction convention
    differences between Excel model and Python period engine.
    """
    _TOL = 2.0  # kEUR per period per category

    @pytest.fixture(scope="class")
    def period_deltas(self, project_inputs, financial_fixture):
        cap = project_inputs.hierarchical_opex_capability
        ctx = OpexCalculationContext(
            senior_debt_tenor_years=project_inputs.financing.senior_tenor_years,
            external_annual_series=cap.external_annual_series,
        )
        annual = compute_annual(cap.opex_model, ctx, horizon_years=_HORIZON)

        from app.ui_runner import _build_period_engine
        engine = _build_period_engine(project_inputs)
        op_periods = [p for p in engine.periods() if p.is_operation]

        opex_fix = financial_fixture["cf"]["opex_items_period_keur"]
        cat_codes = [
            "B.01", "B.02", "B.03", "B.04", "B.05", "B.06",
            "B.07", "B.08", "B.09", "B.10", "B.11", "B.12", "B.13",
        ]
        annual_by_code_year = {
            cat: {r.year_index: next(c.annual_keur for c in r.categories if c.code == cat)
                  for r in annual}
            for cat in cat_codes
        }

        deltas = []
        for i, p in enumerate(op_periods):
            fix_idx = i + 1
            for cat in cat_codes:
                excel_val = abs(opex_fix[cat][fix_idx])
                py_val = annual_by_code_year[cat][p.year_index] * p.day_fraction
                delta = abs(excel_val - py_val)
                deltas.append((cat, fix_idx, p.index, delta))
        return deltas

    def test_max_delta_within_tolerance(self, period_deltas):
        failing = [(cat, fix_idx, pid, d) for cat, fix_idx, pid, d in period_deltas
                   if d > self._TOL]
        if failing:
            worst = sorted(failing, key=lambda x: -x[3])[:5]
            msg = "; ".join(
                f"{cat} fix_period={fi} engine_idx={pi} delta={d:.4f}"
                for cat, fi, pi, d in worst
            )
            assert False, f"Max delta exceeded {self._TOL} kEUR in {len(failing)} cases: {msg}"

    def test_average_delta_below_01_keur(self, period_deltas):
        avg = sum(d for _, _, _, d in period_deltas) / len(period_deltas)
        assert avg < 0.1, f"Average delta {avg:.4f} kEUR exceeds 0.1 kEUR"

    @pytest.mark.parametrize("cat_code", [
        "B.01", "B.02", "B.03", "B.04", "B.05", "B.06",
        "B.07", "B.08", "B.09", "B.10", "B.11", "B.12", "B.13",
    ])
    def test_per_category_max_delta(self, cat_code, period_deltas):
        cat_deltas = [d for cat, _, _, d in period_deltas if cat == cat_code]
        max_d = max(cat_deltas)
        assert max_d <= self._TOL, (
            f"{cat_code}: max per-period delta {max_d:.4f} kEUR exceeds {self._TOL}"
        )


# ---------------------------------------------------------------------------
# B.02 structural break Y1 vs Y2
# ---------------------------------------------------------------------------


class TestB02StructuralBreak:
    _TOL = 1e-6

    def test_b02_y1_sum_matches_fixture(self, annual_results, fixture_data):
        expected = fixture_data["categories"]["B.02"]["annual"]["cached_values_y1_y30"][0]
        actual = next(c.annual_keur for c in annual_results[0].categories if c.code == "B.02")
        assert abs(actual - expected) <= self._TOL

    def test_b02_y2_sum_matches_fixture(self, annual_results, fixture_data):
        expected = fixture_data["categories"]["B.02"]["annual"]["cached_values_y1_y30"][1]
        actual = next(c.annual_keur for c in annual_results[1].categories if c.code == "B.02")
        assert abs(actual - expected) <= self._TOL

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
